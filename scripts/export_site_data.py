#!/usr/bin/env python3
"""Record the data behind the Pages "packing explorer".

Runs the real pipeline (BM25 -> 17M reranker -> packer -> local LLM) on a fixed
set of public dev questions and writes site/data/explorer.json:

  * BM25 top-100 with scores and the reranker score of every one of them;
  * the exact generator-token cost of each paragraph;
  * the real packed set (built by the research packer) at a grid of (k, budget);
  * the recorded answer and timings at the default k=100, budget 1000.

The browser recomputes the pack from the stored scores and token counts. This
script checks that recomputation (`repack`, below, mirrors site/explorer.js)
against the real packer on the whole grid and records how many cells agree
(token merging across line breaks can move a cell by one paragraph).

Needs `lmr setup` done and the [rerank] extra. CPU only. Paragraph text is stored
as short excerpts (Wikipedia, CC BY-SA 4.0; see NOTICE).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEPTH = 100                      # BM25 candidates stored per question
KS = [0, 5, 10, 20, 30, 50, 75, 100]
BUDGETS = [200, 300, 400, 500, 600, 800, 1000, 1500, 2000]
PER_ARTICLE_CAP = 3
EXCERPT_CHARS = 360
MIX = {"factoid": 12, "multihop": 6, "ambiguous": 2, "comparison": 2, "unanswerable": 2}
EXTRA = [("demo-mercury", "factoid", "Which planet is closest to the Sun, and how long is its year?")]


def rank_for_k(bm25_ids, scores, k):
  """BM25 order, with the first k re-sorted by reranker score (desc, id asc)."""
  head = sorted(bm25_ids[:k], key=lambda n: (-scores[n], n.encode("utf-8")))
  return head + bm25_ids[k:]


def repack(ranked, tokens, article, budget, cap=PER_ARTICLE_CAP):
  """Mirror of the packer: <=3 per article (skip), then strict ranked prefix.

  tokens[n] = (first, later): the paragraph's exact token cost as the first line
  of the evidence block, and as a later line (the "\n[" join can merge into one
  token, so the cost of a later line is measured after a "." and a newline).
  """
  per, kept, total = {}, [], 0
  for nid in ranked:
    a = article[nid]
    if per.get(a, 0) >= cap:
      continue
    per[a] = per.get(a, 0) + 1
    cost = tokens[nid][1 if kept else 0]
    if total + cost > budget:
      break
    kept.append(nid)
    total += cost
  return kept, total


def pick_questions():
  qs = [q for q in json.load(open(os.path.join(ROOT, "corpus", "questions.json")))
        if q["split"] == "dev"]
  qs.sort(key=lambda q: q["question_id"])
  out = [{"question_id": i, "question_type": t, "text": x} for i, t, x in EXTRA]
  for typ, n in MIX.items():
    out += [q for q in qs if q["question_type"] == typ][:n]
  return out


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--out", default=os.path.join(ROOT, "site", "data", "explorer.json"))
  args = ap.parse_args()

  from experiments.common.packer import build_ranked_packet
  from lmr.pipeline import RERANKER_ID, RERANKER_REVISION, Assistant
  from substrate.generator import render_prompt
  from substrate.types import Question
  from substrate.evidence import parse_citations, find_unknown_citations

  a = Assistant(rerank_k=DEPTH, log=lambda m: None)
  count = a.llm.count_tokens
  try:
    paragraphs, questions = {}, []
    mism, cells = 0, 0
    for qd in pick_questions():
      text = qd["text"]
      hits = a.index.search(text)[:DEPTH]
      ids = [h.node_id for h in hits]
      import time
      t = time.perf_counter()
      logits = a.reranker.predict([(text, a.node_text[n]) for n in ids], batch_size=32,
                                  show_progress_bar=False)
      rerank_ms = (time.perf_counter() - t) * 1000
      scores = {n: float(s) for n, s in zip(ids, logits)}
      for n in ids:
        if n not in paragraphs:
          d = a._describe(n)
          x = " ".join(d["text"].split())
          paragraphs[n] = {"t": d["title"], "h": d["heading"], "a": a.node_article[n],
                           "u": d["url"],
                           "x": x if len(x) <= EXCERPT_CHARS else x[:EXCERPT_CHARS].rsplit(" ", 1)[0] + " ...",
                           "n": count(f"[{n}] {a.node_text[n]}"),
                           "m": count(f".\n[{n}] {a.node_text[n]}") - count(".")}
      tokens = {n: (paragraphs[n]["n"], paragraphs[n]["m"]) for n in ids}
      article = {n: paragraphs[n]["a"] for n in ids}
      grid = {}
      for k in KS:
        ranked = rank_for_k(ids, scores, k)
        for b in BUDGETS:
          packet, _ = build_ranked_packet("x", ranked, a.node_text, count,
                                          "qwen25-1.5b-gguf", node_article=a.node_article, cap=b)
          real = [s.node_id for s in packet.spans]
          mine, _tot = repack(ranked, tokens, article, b)
          cells += 1
          if real != mine:
            mism += 1
            print(f"MISMATCH {qd['question_id']} k={k} b={b}: {len(real)} vs {len(mine)}")
          grid[f"{k}:{b}"] = real
      ans = a.ask(text)
      questions.append({
        "id": qd["question_id"], "type": qd["question_type"], "text": text,
        "bm25": [[h.node_id, round(h.score, 4)] for h in hits],
        "rr": {n: round(s, 4) for n, s in scores.items()},
        "grid": grid,
        "answer": ans.text, "cited": ans.citations,
        "recorded_pack": [s["id"] for s in ans.packet],
        "recorded_tokens": ans.budget["used"],
        "timings_ms": {k: round(v) for k, v in ans.timings_ms.items()},
      })
      print(f"{qd['question_id']}: {ans.text[:70]!r}", flush=True)
  finally:
    a.close()
  print(f"repack() vs real packer: {cells - mism}/{cells} grid cells identical")
  if mism > max(3, cells // 200):  # token merging across line breaks can move a cell by 1 paragraph
    print("too many grid cells differ between repack() and the real packer", file=sys.stderr)
    return 1

  meta = {
    "recorded_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "machine": f"{platform.machine()} desktop CPU, {os.cpu_count()} threads, no GPU",
    "reranker": f"{RERANKER_ID}@{RERANKER_REVISION[:7]}",
    "generator": "Qwen2.5-1.5B-Instruct Q4_K_M via llama.cpp (CPU)",
    "depth": DEPTH, "ks": KS, "budgets": BUDGETS, "per_article_cap": PER_ARTICLE_CAP,
    "default_k": DEPTH, "default_budget": 1000,
    "excerpt_chars": EXCERPT_CHARS,
    "repack_cells_checked": cells, "repack_cells_identical": cells - mism,
  }
  os.makedirs(os.path.dirname(args.out), exist_ok=True)
  with open(args.out, "w", encoding="utf-8") as fh:
    json.dump({"meta": meta, "paragraphs": paragraphs, "questions": questions},
              fh, ensure_ascii=False, separators=(",", ":"))
  print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.2f} MB)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
