"""Consolidated DEV/shadow_dev scorer: ONE report per trace file, always on disk.

This exists because an independent review of this run returned REPAIR REQUIRED
with "B2 ran but was never scored" as a BLOCKER: the score existed only in a
terminal transcript, so the artifact set was incomplete and a reader could not
tell an unmeasured system from an unrecorded one. That is exactly the failure this
repository keeps re-learning -- an internal consistency check that was never
persisted is not a check.

So: every trace file under a results directory gets a report, whether or not
anyone looked at it. Systems with no traces get an explicit NOT-RUN entry, because
the difference between "measured and null" and "not measured" is the whole point.

    python3 -m experiments.common.score_all --dir experiments/results/retrieval/dev_core --split dev
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.custodian_truth import (  # noqa: E402
  atom_to_host_paragraph, load_ground_truth)
from experiments.common.score_retrieval import load_traces, score_traces  # noqa: E402
from experiments.common.storage_accounting import measure_system_storage  # noqa: E402

# The registered threshold register. Quoted, never recomputed, never a tunable.
MMD = {
  "dev": {"n": 59, "mmd_items": 13, "mmd_pp": 22.0},
  "shadow_dev": {"n": 87, "mmd_items": 15, "mmd_pp": 17.2},
  "dev+shadow_dev": {"n": 146, "mmd_items": 18, "mmd_pp": 12.3},
}


def latency_stats(traces: list[dict]) -> dict:
  """MEASURED latency distribution per stage and end-to-end, from the raw traces.

  Added because an independent review found a baseline reporting latency as a
  single estimated RANGE with no distribution, which is not a measurement. The
  traces already carry per-stage and end-to-end `perf_counter` deltas, so the
  honest distribution is recoverable without re-running anything.

  Note what this is and is not: these are DESKTOP latencies measured while other
  jobs shared the host, so they carry contention noise. They are comparable
  BETWEEN systems only when both were measured under the same load, which the
  per-stage split makes checkable.
  """
  import statistics

  per_stage: dict[str, list[float]] = {}
  total: list[float] = []
  for t in traces:
    for st in t.get("stages", []):
      v = st.get("latency_ms")
      if isinstance(v, (int, float)):
        per_stage.setdefault(st["stage"], []).append(float(v))
    v = t.get("retrieval_latency_ms")
    if isinstance(v, (int, float)):
      total.append(float(v))

  def dist(vals: list[float]) -> dict | None:
    if not vals:
      return None
    s = sorted(vals)
    return {
      "n": len(s),
      "min_ms": s[0],
      "median_ms": statistics.median(s),
      "mean_ms": statistics.fsum(s) / len(s),
      "p95_ms": s[min(len(s) - 1, int(0.95 * len(s)))],
      "max_ms": s[-1],
      "stdev_ms": statistics.stdev(s) if len(s) > 1 else 0.0,
    }

  return {
    "end_to_end_retrieval": dist(total),
    "per_stage": {k: dist(v) for k, v in sorted(per_stage.items())},
    "caveat": (
      "DESKTOP CPU measurements, threads=1 for the model path, on a shared host. "
      "Not an Android or on-device figure. Contention noise is present when "
      "concurrent jobs were running; compare systems only under equal load."
    ),
  }


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--dir", required=True)
  ap.add_argument("--split", required=True)
  ap.add_argument("--tier", default="core")
  ap.add_argument("--root", default=".")
  args = ap.parse_args()

  view = CorpusView.load(args.root, tier=args.tier)
  gts = load_ground_truth(args.root, args.split)
  a2h = atom_to_host_paragraph(view)
  known = set(view._id_to_i)

  paths = sorted(glob.glob(os.path.join(args.dir, "traces_*.jsonl")))
  summary = []
  for d in paths:
    traces = load_traces(d)
    name = os.path.basename(d)[len("traces_"):-len(".jsonl")]
    if not traces:
      summary.append({"system": name, "status": "EMPTY_TRACE_FILE", "n": 0})
      continue
    rep = score_traces(
      traces=traces, system_id=traces[0]["architecture"], tier=args.tier,
      split=args.split, ground_truth=gts, atom_to_host=a2h, known_paragraphs=known)
    payload = {
      "system_id": traces[0]["architecture"],
      "trace_file": os.path.relpath(d, args.root),
      "n_traces": len(traces),
      "n_analysable": rep.n_items_with_required_evidence,
      "stage_survival": rep.stage_rows,
      "final_packet": rep.final_packet_rows,
      "evidence_tokens": rep.token_rows,
      "latency": latency_stats(traces),
      "storage": measure_system_storage(args.root, traces[0]["architecture"]),
      "notes": rep.notes,
      "stage_names": [s["stage"] for s in traces[0]["stages"]],
      "judge_used": False,
      "generator_used": False,
      "registered_mmd": MMD[args.split],
      "interpretation_rule": (
        "A gap below the registered MMD is a NULL RESULT and must never be "
        "reported as a win. MMD is a property of the split, not a tunable."
      ),
    }
    out = os.path.join(args.dir, f"report_{name}.json")
    with open(out, "w", encoding="utf-8") as fh:
      json.dump(payload, fh, indent=2, sort_keys=True)
    st = rep.stage_rows
    first = st.get(payload["stage_names"][0]) or (list(st.values())[0] if st else {})
    fp = rep.final_packet_rows
    summary.append({
      "system": traces[0]["architecture"],
      "status": "SCORED",
      "report": os.path.relpath(out, args.root),
      "n": len(traces),
      "n_analysable": rep.n_items_with_required_evidence,
      "stage0": payload["stage_names"][0],
      "stage0_survival": first.get("survival"),
      "stage0_hits": first.get("survived"),
      "stage0_required": first.get("required_paragraphs"),
      "completion": fp.get("completion"),
      "completion_hits": fp.get("completed"),
      "completion_required": fp.get("required_paragraphs"),
      "item_level_completion": fp.get("item_level_completion"),
      "mean_tokens": rep.token_rows.get("mean") if rep.token_rows else None,
      "median_tokens": rep.token_rows.get("median") if rep.token_rows else None,
      "max_tokens": rep.token_rows.get("max") if rep.token_rows else None,
    })

  cmp_path = os.path.join(args.dir, f"COMPARISON_{args.split}_{args.tier}.json")
  with open(cmp_path, "w", encoding="utf-8") as fh:
    json.dump({
      "split": args.split,
      "tier": args.tier,
      "registered_mmd": MMD[args.split],
      "systems": summary,
      "systems_expected_but_absent": sorted(
        set(["B1_bm25", "B2_bm25_static_union", "B3_bm25_plus_68m_rerank",
             "B4_bm25_fixed_generator"]) - {s["system"] for s in summary}
      ),
    }, fh, indent=2, sort_keys=True)

  print(f"{'system':32s} {'n':>4s} {'stage0':16s} {'survival':>9s} {'completion':>11s} {'item-lvl':>9s} {'tokmean':>8s}")
  for s in sorted([x for x in summary if x["status"] == "SCORED"],
                  key=lambda x: -(x["completion"] or 0)):
    if s["stage0_survival"] is None:
      continue
    print(f"{s['system']:32s} {s['n']:4d} {s['stage0'][:16]:16s} "
          f"{s['stage0_survival']:.4f}   {s['completion']:.4f}    "
          f"{s['item_level_completion']:.4f}  {s['mean_tokens']:8.0f}")
  missing = [s for s in summary if s["status"] != "SCORED"]
  for s in missing:
    print(f"{s['system']:32s} {s['n']:4d}  *** {s['status']} ***")
  print(f"\n-> {cmp_path}")
  print(f"registered MMD ({args.split}) = {MMD[args.split]['mmd_items']} items "
        f"= {MMD[args.split]['mmd_pp']} pp. Gaps below it are NULL RESULTS.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
