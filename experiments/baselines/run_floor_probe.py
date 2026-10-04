"""Driver for the generator-floor probe. Run this; it decides nothing by itself.

    LMR_CUSTODIAN_ORACLE_TOKEN=custodian-only-oracle-packet-v1 \
    python3 -m experiments.baselines.run_floor_probe --split dev

Emits, under `experiments/results/floor_probe/`:

  <split>_arms.json      per-item, per-arm answer + token + latency record
  <split>_report.json    paired McNemar tables, arm summaries, the verdict
  <split>_packets/       the exact packet text each arm handed the generator

The packet text is preserved because the probe's whole claim is "the only
difference between arms is which spans were selected". A reviewer must be able to
read both packets for one item and confirm that, so they are written out verbatim
rather than summarised.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.answer_scoring import exact_match, normalize_answer  # noqa: E402
from experiments.baselines import generator_floor as gf  # noqa: E402
from experiments.common import oracle as oracle_mod  # noqa: E402
from experiments.common.bm25 import Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView, load_questions  # noqa: E402
from experiments.common.custodian_truth import (  # noqa: E402
  atom_to_host_paragraph, load_ground_truth)
from experiments.common.packer import build_ranked_packet  # noqa: E402
from experiments.common.tokenizer import TokenizerService  # noqa: E402
from substrate.evidence import decide_default, serialize_evidence  # noqa: E402
from substrate.types import Question  # noqa: E402

RESULTS_DIR = os.path.join("experiments", "results", "floor_probe")


def a2h_host(atom_to_host: dict[str, str], atom: str) -> str:
  """Host paragraph of a required atom; falls back to the atom id itself when
  the atom is ALREADY a paragraph (sufficient sets legitimately mix granularities:
  some sets cite a whole paragraph, others cite leaf sentences)."""
  return atom_to_host.get(atom, atom)


def build_arms_for_item(
  *,
  gt,
  view,
  index,
  bm25_scored,
  atom_to_host,
) -> dict[str, list[str]]:
  """The three arms' ranked node id lists for one item."""
  oracle_mod.assert_custodian_context(f"floor probe oracle packet for {gt.question_id}")

  # ARM oracle: distinct host paragraphs of the required atoms. An atom whose
  # host is not a retrievable paragraph in this tier cannot enter a packet, so
  # it is skipped rather than smuggled in as an unindexed id.
  retrievable = view._id_to_i
  hosts: list[str] = []
  seen: set[str] = set()
  for atom in gt.required_atom_ids:
    host = a2h_host(atom_to_host, atom)
    if host and host not in seen and host in retrievable:
      seen.add(host)
      hosts.append(host)

  # ARM B4: BM25 top-500 in the pinned total order.
  b4 = [view.node_id(i) for i, _ in bm25_scored[:500]]

  # ARM oracle_size_matched: BM25's best paragraphs, TRUNCATED TO THE SAME NUMBER
  # OF SPANS AS THE ORACLE ARM.
  #
  # This arm exists to separate two effects the oracle-vs-B4 comparison confounds.
  # The oracle arm is both more relevant AND smaller (it carries only the minimal
  # sufficient set), and a smaller packet makes the fixed-prompt generator answer
  # tersely, which raises the strict exact_match score with no relevance gain at
  # all. Comparing oracle against a size-matched BM25 packet holds the span count
  # fixed and varies only WHICH paragraphs are present, which is the comparison
  # that actually isolates evidence quality.
  #
  # When the oracle arm has no spans (an item whose atoms have no retrievable
  # host paragraph) this arm is empty too, and the item contributes no
  # discriminating pair -- recorded, never back-filled.
  oracle_size_matched = b4[: len(hosts)]

  # ARM degraded: BM25's worst-ranked paragraphs, no required host present.
  exclude = set(hosts)
  tail = [view.node_id(i) for i, _ in reversed(bm25_scored) if view.node_id(i) not in exclude]
  degraded = tail[:4]

  return {
    "oracle": hosts,
    "B4": b4,
    "oracle_size_matched": oracle_size_matched,
    "degraded": degraded,
  }


def run(split: str, repo_root: str, limit: int | None, out_dir: str) -> dict:
  oracle_mod.assert_custodian_context(f"generator-floor probe over {split}")
  split_set = "dev" if split == "dev" else (
    "dev+shadow_dev" if split == "all" else "shadow_dev")

  view = CorpusView.load(repo_root, tier="core")
  index = Bm25Index(view)
  a2h = atom_to_host_paragraph(view)
  entries = load_questions(repo_root, split if split != "all" else "dev")
  if split == "all":
    entries = load_questions(repo_root, "dev") + load_questions(repo_root, "shadow_dev")
  if limit:
    entries = entries[:limit]
  gts = load_ground_truth(repo_root, split if split != "all" else "dev")
  if split == "all":
    gts = {**load_ground_truth(repo_root, "dev"),
           **load_ground_truth(repo_root, "shadow_dev")}

  node_text = {p.node_id: p.text for p in view.paragraphs}
  node_article = {p.node_id: a for p, a in zip(view.paragraphs, view.parent_article)}

  os.makedirs(out_dir, exist_ok=True)
  packets_dir = os.path.join(out_dir, f"{split}_packets")
  os.makedirs(packets_dir, exist_ok=True)

  from generator_runtime.qwen25_adapter import LlamaCppGenerator

  tok_svc = TokenizerService(repo_root)
  tokenizer = tok_svc.start()
  gen = LlamaCppGenerator(repo_root)
  gen.prepare()
  session = gen.start_session()

  arms: dict[str, list[gf.ArmResult]] = {
    "oracle": [], "B4": [], "oracle_size_matched": [], "degraded": []}
  per_item: list[dict] = []
  t_start = time.perf_counter()
  try:
    for n, e in enumerate(entries, 1):
      qid = e["question_id"]
      gt = gts.get(qid)
      if gt is None:
        continue
      q = Question(question_id=qid, text=e["text"], split=e["split"], meta={})
      bm25_scored = index.score_all(q.text)
      arm_ids = build_arms_for_item(
        gt=gt, view=view, index=index, bm25_scored=bm25_scored, atom_to_host=a2h)

      item_rec: dict = {"question_id": qid, "split": e["split"],
                        "question_type": gt.question_type,
                        "answerability": gt.answerability, "arms": {}}
      for arm in ("oracle", "B4", "oracle_size_matched", "degraded"):
        packet, pack = build_ranked_packet(
          question_id=qid,
          ranked_node_ids=arm_ids[arm],
          node_text=node_text,
          tokenizer=tokenizer,
          tokenizer_id=tokenizer.tokenizer_id,
          node_article=node_article,
        )
        decision = decide_default(packet)
        answer_text = None
        latency = 0.0
        if decision.generation_action == "generate":
          t0 = time.perf_counter()
          answer = gen.generate(q, packet, session=session)
          latency = (time.perf_counter() - t0) * 1000.0
          answer_text = answer.answer_text
        scored, correct, unscored_reason = gf.score_answer(answer_text, gt.answer_text)
        arms[arm].append(gf.ArmResult(
          question_id=qid, arm=arm, scored=scored, correct=correct,
          abstain_outcome=None,
          answer_text=answer_text,
          exact_evidence_tokens=packet.exact_evidence_tokens,
          n_spans=len(packet.spans),
          truncated=packet.truncated,
          latency_ms=latency,
          reason_unscored=unscored_reason,
        ))
        item_rec["arms"][arm] = {
          "n_ranked_considered": len(arm_ids[arm]),
          "n_spans_in_packet": len(packet.spans),
          "exact_evidence_tokens": packet.exact_evidence_tokens,
          "in_target_band_300_800": (
            300 <= (packet.exact_evidence_tokens or 0) <= 800
          ),
          "truncated": packet.truncated,
          "token_count_method": packet.token_count_method,
          "skipped_per_article_cap": pack.skipped_per_article_cap,
          "citations": list(packet.citations),
          "decision": decision.to_dict(),
          "answer_text": answer_text,
          "answer_chars": len(answer_text) if answer_text else None,
          "normalized_prediction": normalize_answer(answer_text) if answer_text else None,
          "gold_normalized": normalize_answer(gt.answer_text) if gt.answer_text else None,
          "correct": correct,
          "contains_gold_exploratory": gf.containment(answer_text, gt.answer_text),
          "scored": scored,
          "reason_unscored": unscored_reason,
          "latency_ms": latency,
        }
        with open(os.path.join(packets_dir, f"{qid}__{arm}.txt"), "w",
                  encoding="utf-8") as fh:
          fh.write(serialize_evidence(packet.spans))
      per_item.append(item_rec)
      if n % 5 == 0 or n == len(entries):
        el = time.perf_counter() - t_start
        print(f"  [{split}] {n}/{len(entries)}  elapsed {el:.0f}s", flush=True)
  finally:
    rep = session.close()
    tok_close = tok_svc.close()

  probe = gf.FloorProbe(split_set=split_set, arms=arms)
  stat_oracle_b4 = probe.mcnemar("oracle", "B4")
  stat_oracle_deg = probe.mcnemar("oracle", "degraded")
  stat_b4_deg = probe.mcnemar("B4", "degraded")
  stat_oracle_matched = probe.mcnemar("oracle", "oracle_size_matched")
  mmd = gf.MMD_BY_SPLIT_SET[split_set]
  verdict = gf.decide(stat_oracle_b4, mmd["mmd_items"], mmd["n"])

  # Exploratory containment, reported alongside the preregistered metric so the
  # verbosity confound is visible instead of silently deciding the result.
  contain_table = {}
  for arm in ("oracle", "B4", "oracle_size_matched", "degraded"):
    vals = [
      it["arms"][arm]["contains_gold_exploratory"]
      for it in per_item
      if it["arms"][arm]["contains_gold_exploratory"] is not None
    ]
    contain_table[arm] = {
      "n": len(vals),
      "n_contains": sum(1 for v in vals if v),
      "rate": (sum(1 for v in vals if v) / len(vals)) if vals else None,
    }
  paired_oracle_b4_contain = {
    "note": "EXPLORATORY / NOT PREREGISTERED -- see generator_floor.containment()",
    "oracle_better": sum(
      1 for it in per_item
      if it["arms"]["oracle"]["contains_gold_exploratory"]
      and not it["arms"]["B4"]["contains_gold_exploratory"]
    ),
    "B4_better": sum(
      1 for it in per_item
      if it["arms"]["B4"]["contains_gold_exploratory"]
      and not it["arms"]["oracle"]["contains_gold_exploratory"]
    ),
    "both": sum(
      1 for it in per_item
      if it["arms"]["oracle"]["contains_gold_exploratory"]
      and it["arms"]["B4"]["contains_gold_exploratory"]
    ),
    "neither": sum(
      1 for it in per_item
      if not it["arms"]["oracle"]["contains_gold_exploratory"]
      and not it["arms"]["B4"]["contains_gold_exploratory"]
    ),
  }

  payload = {
    "probe": "generator-floor",
    "split_set": split_set,
    "n_items_run": len(per_item),
    "registered_mmd": mmd,
    "mmd_source": "experiments/comparability/CONTRACT.md §4 via R1_CONTRACT_ERRATUM.md E-1b",
    "arm_summaries": gf.summarize_arms(arms),
    "paired_oracle_vs_B4": stat_oracle_b4,
    "paired_oracle_vs_degraded": stat_oracle_deg,
    "paired_B4_vs_degraded": stat_b4_deg,
    "paired_oracle_vs_oracle_size_matched": stat_oracle_matched,
    "verdict": verdict,
    "exploratory_containment": {
      "why": (
        "the fixed prompt makes answer verbosity grow with packet size, so "
        "exact_match under-credits verbose-but-correct answers. A smaller packet "
        "can raise the answer score with no relevance gain. Both numbers are "
        "reported; the preregistered exact_match stays primary."
      ),
      "per_arm": contain_table,
      "paired_oracle_vs_B4": paired_oracle_b4_contain,
    },
    "judge_used": False,
    "scoring": "eval/answer_scoring.exact_match (deterministic, stdlib, no judge)",
    "generator": {
      "generator_id": gen.generator_id,
      "prompt_hash": gen.prompt_hash,
      "settings": gen.settings,
    },
    "tokenizer_id": tokenizer.tokenizer_id,
    "corpus": view.index_manifest(),
    "bm25": index.stats(),
    "sessions": {"generator_close": rep, "tokenizer_close": tok_close},
    "wall_seconds": time.perf_counter() - t_start,
  }
  gf.write_report(os.path.join(out_dir, f"{split}_report.json"), payload)
  with open(os.path.join(out_dir, f"{split}_arms.json"), "w", encoding="utf-8") as fh:
    json.dump(per_item, fh, indent=2, sort_keys=True)
  return payload


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--split", default="dev", choices=["dev", "shadow_dev", "all"])
  ap.add_argument("--root", default=".")
  ap.add_argument("--limit", type=int, default=None)
  ap.add_argument("--out", default=RESULTS_DIR)
  args = ap.parse_args()
  payload = run(args.split, args.root, args.limit, args.out)
  print(json.dumps({
    "split_set": payload["split_set"],
    "n_items_run": payload["n_items_run"],
    "arm_summaries": payload["arm_summaries"],
    "paired_oracle_vs_B4": payload["paired_oracle_vs_B4"],
    "verdict": payload["verdict"],
  }, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
