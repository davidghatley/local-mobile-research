"""WHICH policy dropped each lost paragraph: the per-article cap, or the token budget?

The headroom analysis found that 16 of 19 lost required paragraphs were inside
BM25's top-500, and 10 of them were at BM25 rank 2-31. A reranker cannot lift a
paragraph that the PACKER skipped, so before comparing rerankers the tournament
has to know which packer rule is doing the dropping.

The two candidate mechanisms are both mandated by
`experiments/baselines/HYPOTHESIS.md` §2.3:

  * PER-ARTICLE CAP = 3. A required paragraph whose article already contributed 3
    spans is skipped WITHOUT consuming budget and WITHOUT stopping packing.
  * 1000-TOKEN HARD CAP. `build_packet` stops at the first span that would
    overflow, so a required paragraph ranked below the cutoff simply never gets
    considered.

These have opposite architectural implications. The cap is a POLICY a smarter
ranker cannot evade -- and a ranker that concentrates harder on one article would
trigger MORE cap exclusions, so better ranking could make completion WORSE. The
token cap is a fixed resource that a better ranker allocates more efficiently.

This script attributes every loss to one of them, by replaying the packer.

CUSTODIAN SIDES ONLY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.custodian_truth import load_ground_truth  # noqa: E402
from experiments.common.packer import spans_from_ranked  # noqa: E402
from experiments.common.score_retrieval import (  # noqa: E402
  load_traces, required_host_paragraphs)
from experiments.common.tokenizer import TokenizerService  # noqa: E402
from substrate.evidence import HARD_EVIDENCE_TOKEN_CAP, build_packet  # noqa: E402


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--split", default="dev")
  ap.add_argument("--tier", default="core")
  ap.add_argument("--root", default=".")
  ap.add_argument("--system", default="B1_bm25")
  ap.add_argument("--per-article-cap", type=int, default=3)
  ap.add_argument("--out", default=os.path.join("experiments", "results", "retrieval"))
  args = ap.parse_args()

  view = CorpusView.load(args.root, tier=args.tier)
  gts = load_ground_truth(args.root, args.split)
  a2h = {n.node_id: (n.parent_id or "") for n in view.nodes if n.kind == "sentence"}
  known = set(view._id_to_i)
  node_text = {p.node_id: p.text for p in view.paragraphs}
  node_article = {p.node_id: a for p, a in zip(view.paragraphs, view.parent_article)}

  trace_path = os.path.join(args.out, f"{args.split}_{args.tier}",
                            f"traces_{args.system}_{args.split}_{args.tier}.jsonl")
  traces = load_traces(trace_path)

  tok = TokenizerService(args.root)
  tokenizer = tok.start()
  try:
    attribution: Counter = Counter()
    detail: list[dict] = []
    n_req = 0
    for tr in traces:
      qid = tr["question_id"]
      gt = gts.get(qid)
      if gt is None:
        continue
      req = [h for h in required_host_paragraphs(gt, a2h) if h in known]
      if not req:
        continue
      n_req += len(req)
      ranked = list(tr["stages"][0]["candidate_ids"])

      # Replay the packer with the cap DISABLED to get the uncapped ranked set
      # that would have been considered.
      uncapped, _ = spans_from_ranked(ranked, node_text, 0, node_article)
      uncapped_ids = [s.node_id for s in uncapped]

      packet = build_packet(
        question_id=qid, spans=uncapped, cap=HARD_EVIDENCE_TOKEN_CAP,
        tokenizer=tokenizer, tokenizer_id=tokenizer.tokenizer_id, exact=True)
      admitted_uncapped = {s.node_id for s in packet.spans}

      capped_spans, cap_info = spans_from_ranked(
        ranked, node_text, args.per_article_cap, node_article)
      capped_ids = [s.node_id for s in capped_spans]
      admitted_capped = {s.node_id for s in packet.spans} & set(capped_ids)

      for h in req:
        if h in admitted_capped:
          attribution["survived"] += 1
          continue
        # Not admitted. Which rule stopped it?
        if h not in uncapped_ids:
          why = "stage0_rank_below_top500"
        elif h not in capped_ids:
          why = "per_article_cap"
        elif h in admitted_uncapped:
          why = "per_article_cap_changed_what_fits"
        else:
          why = "token_budget_1000"
        attribution[why] += 1
        bm25_rank = ranked.index(h) + 1 if h in ranked else None
        detail.append({
          "question_id": qid,
          "node_id": h,
          "attribution": why,
          "bm25_rank": bm25_rank,
          "article": node_article.get(h),
          "spans_in_article_before_it": (
            sum(1 for c in capped_ids[: capped_ids.index(h)]
                if node_article.get(c) == node_article.get(h))
            if h in capped_ids else None),
          "exact_evidence_tokens_full_packet": packet.exact_evidence_tokens,
          "n_admitted_uncapped": len(admitted_uncapped),
        })
  finally:
    tok.close()

  payload = {
    "split": args.split,
    "tier": args.tier,
    "system": args.system,
    "per_article_cap_replayed": args.per_article_cap,
    "hard_token_cap": HARD_EVIDENCE_TOKEN_CAP,
    "n_required_paragraphs": n_req,
    "attribution": dict(attribution),
    "loss_rate": 1.0 - attribution["survived"] / n_req if n_req else None,
    "detail": detail,
    "reading": {
      "note": (
        "per_article_cap_changed_what_fitted means the cap did not remove this "
        "paragraph directly, but it removed an EARLIER span from the same article, "
        "which freed budget for a lower-ranked span and pushed this one past the "
        "token cutoff. That is still the cap's doing, and it is the case a smarter "
        "ranker cannot fix."
      ),
    },
  }
  path = os.path.join(args.out, f"{args.split}_{args.tier}",
                      f"loss_attribution_{args.system}_{args.split}_{args.tier}.json")
  with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)

  print(f"required paragraphs: {n_req}")
  for k, v in sorted(attribution.items(), key=lambda kv: -kv[1]):
    print(f"  {k:36s} {v:3d}  ({v/n_req:.4f})")
  print(f"-> {path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
