"""Custodian driver: run retrieval-only baselines and score them on the primary metric.

Retrieval-only is the right default here. The generator's own weakness is a
PROPERTY OF THE GENERATOR, and letting it into a retrieval sweep would mean a
generator regression silently changed a retrieval number. So these sweeps carry
no generation at all, and the answer metric stays quarantined in the floor probe
where it can be studied properly.

    python3 -m experiments.common.run_dev_retrieval --systems b1,b4 --split dev

Writes, under experiments/results/retrieval/:

    traces_<system>_<split>_<tier>.jsonl   raw per-question traces
    report_<system>_<split>_<tier>.json     survival, completion, precision, tokens

CUSTODIAN SIDES ONLY: it reads staging/ ground truth to compute required-evidence
survival. No worker retrieval module imports it, and no answer is ever read.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView, load_questions  # noqa: E402
from experiments.common.custodian_truth import (  # noqa: E402
  atom_to_host_paragraph, load_ground_truth)
from experiments.common.runner import PackerContext, run_split  # noqa: E402
from experiments.common.score_retrieval import load_traces, score_traces  # noqa: E402
from experiments.common.tokenizer import TokenizerService  # noqa: E402

RESULTS_DIR = os.path.join("experiments", "results", "retrieval")

SYSTEMS = {
  "b1": ("experiments.baselines.b1_lexical", "B1Lexical", "B1_bm25"),
  "b4": ("experiments.baselines.b1_lexical", "B4DeterministicFloor", "B4_bm25_fixed_generator"),
}


def build_system(key: str, view: CorpusView, index: Bm25Index, stage0_k: int):
  mod_name, cls_name, sys_id = SYSTEMS[key]
  import importlib

  mod = importlib.import_module(mod_name)
  cls = getattr(mod, cls_name)
  obj = cls(index, stage0_k=stage0_k)
  if obj.system_id != sys_id:
    raise ValueError(f"{key}: system_id drift {obj.system_id!r} != {sys_id!r}")
  return obj


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--systems", default="b1,b4")
  ap.add_argument("--split", default="dev")
  ap.add_argument("--tier", default="core")
  ap.add_argument("--root", default=".")
  ap.add_argument("--limit", type=int, default=None)
  ap.add_argument("--stage0-k", type=int, default=500)
  ap.add_argument("--per-article-cap", type=int, default=3,
                  help="shared packing policy; 0 disables it (recorded ABLATION per "
                       "experiments/baselines/HYPOTHESIS.md 2.3, never a substitution)")
  ap.add_argument("--out", default=RESULTS_DIR)
  args = ap.parse_args()

  root = args.root
  suffix = "" if args.per_article_cap == 3 else f"_cap{args.per_article_cap}"
  out = os.path.join(args.out, f"{args.split}_{args.tier}{suffix}")
  os.makedirs(out, exist_ok=True)

  t0 = time.perf_counter()
  view = CorpusView.load(root, tier=args.tier)
  index = Bm25Index(view)
  print(f"[setup] view+index {time.perf_counter()-t0:.1f}s  n_docs={view.n_docs}")
  print(f"[setup] {view.index_manifest()}")

  entries = load_questions(root, args.split)
  if args.limit:
    entries = entries[: args.limit]
  ctx = PackerContext.from_view(view, entries, per_article_cap=args.per_article_cap)
  gts = load_ground_truth(root, args.split)
  a2h = atom_to_host_paragraph(view)
  known = set(view._id_to_i)

  tok = TokenizerService(root)
  tokenizer = tok.start()
  try:
    for key in args.systems.split(","):
      key = key.strip()
      if not key:
        continue
      system = build_system(key, view, index, args.stage0_k)
      res = run_split(
        system=system,
        split=args.split,
        tier=args.tier,
        tokenizer=tokenizer,
        tokenizer_id=tokenizer.tokenizer_id,
        packer_ctx=ctx,
        run_id=f"r1-{key}-{args.split}-{args.tier}{suffix}",
        seed=20261004,
        out_dir=out,
        index_stats=index.stats(),
        model_identity={"system_id": system.system_id, "stage0_k": args.stage0_k,
                        "per_article_cap": args.per_article_cap,
                        "policy": ("PREREGISTERED baseline cap=3"
                                  if args.per_article_cap == 3
                                  else f"RECORDED ABLATION cap={args.per_article_cap}")},
        generator=None,
        log=print,
      )
      rep = score_traces(
        traces=res.traces,
        system_id=system.system_id,
        tier=args.tier,
        split=args.split,
        ground_truth=gts,
        atom_to_host=a2h,
        known_paragraphs=known,
      )
      payload = {
        "run": res.summary(),
        "primary_metrics": rep.to_dict(),
        "preregistered_threshold_register": {
          "source": "experiments/comparability/CONTRACT.md §4 via R1_CONTRACT_ERRATUM.md E-1b",
          "dev": {"mmd_items": 13, "mmd_pp": 22.0},
          "dev+shadow_dev": {"mmd_items": 18, "mmd_pp": 12.3},
        },
        "judge_used": False,
        "generator_used": False,
      }
      path = os.path.join(out, f"report_{key}_{args.split}_{args.tier}.json")
      with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
      fp = rep.final_packet_rows
      st = rep.stage_rows
      print(f"\n=== {system.system_id} on {args.split}/{args.tier} ===")
      print(f"  items={rep.n_items} analysable={rep.n_items_with_required_evidence} "
            f"failed={res.n_failed}")
      for name, row in st.items():
        print(f"  stage {name:22s} survival {row['survived']}/{row['required_paragraphs']}"
              f" = {row['survival']:.4f}" if row["survival"] is not None else f"  stage {name}: no data")
      if fp:
        print(f"  final packet completion   {fp['completed']}/{fp['required_paragraphs']}"
              f" = {fp['completion']:.4f}")
        print(f"  item-level completion     {fp['item_level_completion']:.4f}")
        if "context_precision_leaf" in fp:
          print(f"  leaf context precision     {fp['context_precision_leaf']['leaf_precision']:.4f}")
      if rep.token_rows:
        t = rep.token_rows
        print(f"  evidence tokens mean={t['mean']:.0f} median={t['median']} "
              f"p95={t['p95']} max={t['max']} over-800={t['n_over_target_band_800']}")
      print(f"  report -> {path}")
  finally:
    tok.close()
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
