"""Where does required evidence actually get lost? The headroom diagnostic.

The first DEV numbers said something that reframes the whole tournament: BM25
stage-0 recall@500 keeps 95.9% of required evidence, and final packet completion
is 74.0%. So roughly 22 points of required evidence die between "the retriever
found it" and "the generator was shown it".

That gap has exactly two possible causes, and they imply opposite architectures:

  A. BUDGET. The required paragraph was ranked inside the top-500 but fell below
     the ~1000-token / 3-per-article packet cutoff. Fixing it means changing the
     PACKING policy, not the ranker.
  B. RANK. The required paragraph sat deep in the top-500 (or outside it). Fixing
     it means a better RANKER.

A reranker can only help with (B). So this script measures the BM25 rank
distribution of every required paragraph that did NOT reach the packet, which
turns "22 points are lost somewhere" into a number that says whether any reranker
in the tournament can possibly recover them.

CUSTODIAN SIDES ONLY (it reads required-evidence ground truth).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView, load_questions  # noqa: E402
from experiments.common.custodian_truth import (  # noqa: E402
  atom_to_host_paragraph, load_ground_truth)
from experiments.common.score_retrieval import required_host_paragraphs  # noqa: E402

# Rank buckets. Chosen to straddle the packet's effective depth: the 1000-token
# budget holds roughly 3-7 paragraphs depending on their length, so everything
# beyond rank ~10 is where a reranker's work would have to land.
BUCKETS = [(1, 1), (2, 3), (4, 7), (8, 15), (16, 31), (32, 63),
           (64, 127), (128, 255), (256, 500), (501, 10 ** 9)]


def bucket(rank: int | None) -> str:
  if rank is None:
    return "not_in_top500"
  for lo, hi in BUCKETS:
    if lo <= rank <= hi:
      return f"{lo}-{hi}" if lo != hi else str(lo)
  return "other"


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--split", default="dev")
  ap.add_argument("--tier", default="core")
  ap.add_argument("--root", default=".")
  ap.add_argument("--stage0-k", type=int, default=500)
  ap.add_argument("--out", default=os.path.join("experiments", "results", "retrieval"))
  args = ap.parse_args()

  view = CorpusView.load(args.root, tier=args.tier)
  index = Bm25Index(view)
  gts = load_ground_truth(args.root, args.split)
  a2h = atom_to_host_paragraph(view)
  known = set(view._id_to_i)
  id_to_i = view._id_to_i

  reached = Counter()
  lost = Counter()
  lost_detail: list[dict] = []
  n_req = 0
  n_lost = 0
  n_outside_top500 = 0
  # Per-item: how many required hosts, how many survived into the packet, and
  # the rank of the deepest surviving vs shallowest lost one.
  items = []

  entries = load_questions(args.root, args.split)
  for e in entries:
    qid = e["question_id"]
    gt = gts.get(qid)
    if gt is None:
      continue
    req = [h for h in required_host_paragraphs(gt, a2h) if h in known]
    if not req:
      continue
    hits = index.search(e["text"], k=args.stage0_k)
    rank_of = {h.node_id: r + 1 for r, h in enumerate(hits)}
    n_req += len(req)
    rec = {"question_id": qid, "n_required": len(req), "hosts": []}
    for h in req:
      r = rank_of.get(h)
      b = bucket(r)
      reached[b] += 1
      rec["hosts"].append({"node_id": h, "bm25_rank": r, "bucket": b,
                           "article": view.parent_article[id_to_i[h]]})
      if r is None:
        n_outside_top500 += 1
    items.append(rec)

  # Now read the actual packets B1 produced and classify what did not arrive.
  trace_path = os.path.join(
    args.out, f"{args.split}_{args.tier}",
    f"traces_B1_bm25_{args.split}_{args.tier}.jsonl")
  if not os.path.isfile(trace_path):
    print(f"no B1 traces at {trace_path}; run run_dev_retrieval first")
    return 1
  from experiments.common.score_retrieval import load_traces

  traces = {t["question_id"]: t for t in load_traces(trace_path)}
  for rec in items:
    tr = traces.get(rec["question_id"])
    if tr is None:
      continue
    in_packet = {s["node_id"] for s in (tr["evidence_packet"].get("spans") or [])}
    for h in rec["hosts"]:
      if h["node_id"] in in_packet:
        continue
      n_lost += 1
      b = h["bucket"]
      lost[b] += 1
      lost_detail.append({
        "question_id": rec["question_id"],
        "node_id": h["node_id"],
        "bm25_rank": h["bm25_rank"],
        "bucket": b,
        "in_top500": h["bm25_rank"] is not None,
        "n_packet_spans": len(in_packet),
        "exact_evidence_tokens": tr["evidence_token_count"],
        "truncated": tr["evidence_packet"].get("truncated"),
      })

  payload = {
    "split": args.split,
    "tier": args.tier,
    "stage0_k": args.stage0_k,
    "n_required_paragraphs_total": n_req,
    "n_lost_before_generator": n_lost,
    "loss_rate": n_lost / n_req if n_req else None,
    "n_required_outside_top500": n_outside_top500,
    "bm25_rank_buckets_all_required": dict(sorted(reached.items())),
    "bm25_rank_buckets_LOST": dict(sorted(lost.items())),
    "headroom_reading": {
      "recoverable_by_any_reranker": sum(
        c for b, c in lost.items() if b not in ("not_in_top500",)),
      "requires_stage0_recall_improvement": lost.get("not_in_top500", 0),
      "note": (
        "A reranker reorders WITHIN the stage-0 set. So only lost paragraphs whose "
        "BM25 rank is <= stage0_k can be recovered by reranking at all. Those "
        "ranked outside top-500 need a better STAGE 0, which is a different "
        "intervention (B2's static channel, or a denser lexical index)."
      ),
    },
    "lost_detail": lost_detail,
    "per_item": items,
  }
  os.makedirs(os.path.join(args.out, f"{args.split}_{args.tier}"), exist_ok=True)
  path = os.path.join(args.out, f"{args.split}_{args.tier}",
                      f"headroom_{args.split}_{args.tier}.json")
  with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)

  print(f"required paragraphs        : {n_req}")
  print(f"lost before the generator  : {n_lost}  ({payload['loss_rate']:.4f})")
  print(f"required outside top-{args.stage0_k}    : {n_outside_top500}")
  print()
  print("BM25 rank distribution of LOST required paragraphs:")
  for b, _ in BUCKETS + [(501, 10 ** 9)]:
    label = bucket(b)
    if lost.get(label):
      print(f"  rank {label:>10s} : {lost[label]:3d}")
  print()
  hr = payload["headroom_reading"]
  print(f"recoverable by ANY reranker (rank <= {args.stage0_k}) : "
        f"{hr['recoverable_by_any_reranker']}")
  print(f"needs a better STAGE 0 (outside top-{args.stage0_k})      : "
        f"{hr['requires_stage0_recall_improvement']}")
  print(f"-> {path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
