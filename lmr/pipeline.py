"""The assistant: BM25 -> small cross-encoder rerank -> budgeted packet -> local LLM.

This is the round-1 winner ("C", one 17M encoder) assembled as a usable tool.
Retrieval, packing and the prompt are the frozen research components, imported
unchanged; only the glue lives here. The one deliberate change is that the
reranker scores BM25's top ``rerank_k`` (default 100) instead of all 500: the
research found 96% of needed paragraphs already inside BM25's top 500, and the
losses that mattered happened after retrieval, so rescoring the long tail
cost 40 s per question for little gain. `lmr bench` measures what this trades.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from experiments.common.bm25 import Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.packer import build_ranked_packet  # noqa: E402
from substrate.evidence import find_unknown_citations, parse_citations  # noqa: E402
from substrate.generator import render_prompt  # noqa: E402
from substrate.types import Question  # noqa: E402

from . import fetch, runtime  # noqa: E402

RERANKER_ID = "cross-encoder/ettin-reranker-17m-v1"
RERANKER_REVISION = "9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6"


@dataclass
class Answer:
  question: str
  text: str
  citations: list[str]
  unknown_citations: list[str]
  candidates: list[dict]
  packet: list[dict]
  budget: dict
  timings_ms: dict
  usage: dict = field(default_factory=dict)

  def to_dict(self) -> dict:
    return dict(self.__dict__)


class Assistant:
  def __init__(self, rerank_k: int = 100, use_reranker: bool = True, log=print):
    fetch.ensure_corpus(log)
    t = time.perf_counter()
    self.view = CorpusView.load(ROOT, "core")
    self.index = Bm25Index(self.view)
    self.load_ms = {"index": (time.perf_counter() - t) * 1000}
    self.node_article = {p.node_id: self.view.parent_article[i]
                         for i, p in enumerate(self.view.paragraphs)}
    self.node_text = {p.node_id: p.text for p in self.view.paragraphs}
    self.rerank_k = rerank_k
    self.reranker = None
    if use_reranker:
      t = time.perf_counter()
      from sentence_transformers import CrossEncoder
      self.reranker = CrossEncoder(RERANKER_ID, revision=RERANKER_REVISION, device="cpu")
      self.load_ms["reranker"] = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    self.llm = runtime.LlamaServer()
    self.load_ms["llm"] = (time.perf_counter() - t) * 1000

  def close(self) -> None:
    self.llm.close()

  def _describe(self, nid: str) -> dict:
    i = self.view.index_of(nid)
    return {"id": nid, "title": self.view.title_of(i), "heading": self.view.heading_of(i),
            "text": self.node_text[nid],
            "url": self.view.by_id[self.node_article[nid]].meta.get("source_url", "")}

  def retrieve(self, text: str) -> tuple[list[str], list[dict], dict]:
    timings = {}
    t = time.perf_counter()
    hits = self.index.search(text)
    timings["bm25"] = (time.perf_counter() - t) * 1000
    bm25_ids = [h.node_id for h in hits]
    bm25_rank = {nid: r for r, nid in enumerate(bm25_ids)}
    ranked = list(bm25_ids)
    scores = {}
    if self.reranker is not None and ranked:
      head = ranked[:self.rerank_k]
      t = time.perf_counter()
      logits = self.reranker.predict([(text, self.node_text[n]) for n in head],
                                     batch_size=32, show_progress_bar=False)
      timings["rerank"] = (time.perf_counter() - t) * 1000
      scores = {n: float(s) for n, s in zip(head, logits)}
      head = sorted(head, key=lambda n: (-scores[n], n.encode("utf-8")))
      ranked = head + ranked[self.rerank_k:]
    cands = []
    for r, nid in enumerate(ranked[:20]):
      d = self._describe(nid)
      d.update(rank=r, bm25_rank=bm25_rank[nid], score=scores.get(nid))
      cands.append(d)
    return ranked, cands, timings

  def ask(self, text: str, max_tokens: int = 256) -> Answer:
    q = Question(question_id="ask", text=text)
    ranked, cands, timings = self.retrieve(text)
    t = time.perf_counter()
    packet, report = build_ranked_packet(
      "ask", ranked, self.node_text, self.llm.count_tokens, "qwen25-1.5b-gguf",
      node_article=self.node_article)
    timings["pack"] = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    out = self.llm.chat(render_prompt(q, packet), max_tokens=max_tokens)
    timings["generate"] = (time.perf_counter() - t) * 1000
    answer = out["choices"][0]["message"]["content"].strip()
    cited = parse_citations(answer)
    unknown = find_unknown_citations(cited, packet.citations)
    spans = []
    for s in packet.spans:
      d = self._describe(s.node_id)
      d["tokens"] = self.llm.count_tokens(f"[{s.node_id}] {s.text}")
      d["cited"] = s.node_id in cited
      spans.append(d)
    budget = {"cap": 1000, "used": packet.exact_evidence_tokens,
              "skipped_per_article_cap": report.skipped_per_article_cap,
              "truncated": packet.truncated}
    return Answer(text, answer, [c for c in cited if c not in unknown], unknown,
                  cands, spans, budget, timings, out.get("usage", {}))
