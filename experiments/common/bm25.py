"""The pinned BM25 lexical index.

A direct, stdlib-only implementation of `experiments/baselines/HYPOTHESIS.md`
§3.2-§3.4. Every parameter is pinned by that document and is NOT a tunable of
this module. A deviation is a recorded ablation, never a silent substitution.

Pinned, and not negotiable without an amendment:

    tokenizer   NFKC -> casefold -> [a-z0-9]+ matches
    stemming    NONE
    stopwords   NONE  (the IDF does the stopping)
    k1          1.2
    b           0.75
    query side  UNIQUE terms in FIRST-OCCURRENCE order; multiplicity counts once
    idf         ln((N - df + 0.5) / (df + 0.5))
    stage-0 K   500
    tie-break   (score descending, node_id ascending as UTF-8 bytes)

Bit-exactness, and why this module is fussier than it looks
-----------------------------------------------------------
§3.3 prescribes the per-document score as the sum over UNIQUE query terms *in
first-occurrence order*, each summand ``idf(t) * (tf*(k1+1)) / (tf + k1*(1-b+b*dl/avgdl))``
with the denominator evaluated left-to-right. IEEE-754 addition is not
associative, so accumulating a document's score while walking the terms in a
different order can change the last bit and, at a tie, change the ranking. So
this implementation collects each document's summands into a slot indexed by the
term's position in the first-occurrence order, and then sums each document's
slots strictly in ascending slot order. That is the specified order, exactly.

Documents with no overlap with the query score 0 and are NOT ranked -- they are
outside the positive set, not "ties at zero". That distinction is what makes
recall@500 over 9,979 documents mean anything.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import unicodedata
from array import array
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.corpus_view import CorpusView  # noqa: E402

# --- pinned parameters (HYPOTHESIS.md §3) --------------------------------
K1 = 1.2
B = 0.75
STAGE0_K = 500

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
  """The pinned tokenizer. NFKC -> casefold -> [a-z0-9]+ matches.

  No stemming, no stopwords, stdlib only. Two implementations that follow this
  produce byte-identical token streams, which is the whole point.
  """
  u = unicodedata.normalize("NFKC", text)
  c = u.casefold()
  return _TOKEN_RE.findall(c)


def unique_terms_in_order(tokens: list[str]) -> list[str]:
  """Unique terms in first-occurrence order (query-side collapse, §3.3)."""
  seen: set[str] = set()
  out: list[str] = []
  for t in tokens:
    if t not in seen:
      seen.add(t)
      out.append(t)
  return out


@dataclass(frozen=True)
class Bm25Hit:
  doc_index: int
  node_id: str
  score: float


class Bm25Index:
  """BM25 index over a :class:`CorpusView`'s paragraph documents."""

  def __init__(self, view: CorpusView) -> None:
    self.view = view
    self.n_docs = view.n_docs
    # term -> (df, postings array of interleaved (doc_index, tf))
    self._postings: dict[str, tuple[int, array]] = {}
    self._dl: list[int] = [0] * self.n_docs
    self._total_len = 0
    self.build_ms: float = 0.0
    self._build()

  # -- build ---------------------------------------------------------------

  def _build(self) -> None:
    """Single pass over documents. O(total tokens), not O(terms x docs).

    Postings are emitted in doc-index order because the spec requires that
    order for the packed binary and it makes query-time access sequential.
    """
    t0 = time.perf_counter()
    # term -> list of (doc_index, tf), appended in doc-index order
    acc: dict[str, list[tuple[int, int]]] = {}
    for i, doc in enumerate(self.view.doc_strings):
      toks = tokenize(doc)
      self._dl[i] = len(toks)
      self._total_len += len(toks)
      tf: dict[str, int] = {}
      for t in toks:
        tf[t] = tf.get(t, 0) + 1
      for t, c in tf.items():
        lst = acc.get(t)
        if lst is None:
          acc[t] = [(i, c)]
        else:
          lst.append((i, c))
    for term, lst in acc.items():
      flat = array("I")
      for i, c in lst:
        flat.append(i)
        flat.append(c)
      self._postings[term] = (len(lst), flat)
    self.avgdl = (self._total_len / self.n_docs) if self.n_docs else 0.0
    self.build_ms = (time.perf_counter() - t0) * 1000.0

  # -- query ---------------------------------------------------------------

  def score_all(self, query_text: str) -> list[tuple[int, float]]:
    """Score every document with positive overlap, in the §3.3 total order.

    Returns a list of ``(doc_index, score)``. Zero-overlap documents are omitted
    rather than returned as 0.0.
    """
    terms = unique_terms_in_order(tokenize(query_text))
    n = self.n_docs
    if n == 0 or not terms:
      return []
    # slots[doc_index] -> list of (slot_position, summand), summed in slot order.
    slots: dict[int, list[tuple[int, float]]] = {}
    avgdl = self.avgdl
    dl = self._dl
    for pos, t in enumerate(terms):
      entry = self._postings.get(t)
      if entry is None:
        continue
      df, flat = entry
      idf = math.log((n - df + 0.5) / (df + 0.5))
      for k in range(0, len(flat), 2):
        i = flat[k]
        tf = flat[k + 1]
        num = tf * (K1 + 1.0)
        # denominator evaluated left-to-right exactly as written in §3.3
        den = tf + K1 * (1.0 - B + B * (dl[i] / avgdl))
        lst = slots.get(i)
        if lst is None:
          slots[i] = [(pos, idf * (num / den))]
        else:
          lst.append((pos, idf * (num / den)))
    out: list[tuple[int, float]] = []
    for i, lst in slots.items():
      lst.sort(key=lambda pc: pc[0])
      total = 0.0
      for _, summand in lst:
        total += summand
      out.append((i, total))
    out.sort(
      key=lambda kv: (-kv[1], self.view.node_id(kv[0]).encode("utf-8"))
    )
    return out

  def search(self, query_text: str, k: int = STAGE0_K) -> list[Bm25Hit]:
    """Top-k by the §3.3 total order. If fewer than k docs overlap, all of them."""
    return [
      Bm25Hit(doc_index=i, node_id=self.view.node_id(i), score=s)
      for i, s in self.score_all(query_text)[:k]
    ]

  # -- artifact / accounting ----------------------------------------------

  def export_json(self, path: str) -> dict:
    """Audit export. The packed binary would be the artifact; this is for review."""
    doc = {
      "spec": {
        "k1": K1,
        "b": B,
        "stage0_k": STAGE0_K,
        "tokenizer": "NFKC -> casefold -> [a-z0-9]+",
        "stemming": None,
        "stopwords": None,
        "idf": "ln((N - df + 0.5) / (df + 0.5))",
        "query_collapse": "unique terms, first-occurrence order",
        "accumulation_order": "unique query terms in first-occurrence order",
        "tie_break": "score desc, node_id asc (utf-8 bytes)",
      },
      "n_docs": self.n_docs,
      "avgdl": self.avgdl,
      "n_terms": len(self._postings),
      "n_postings": sum(len(p) // 2 for _, p in self._postings.values()),
      "index_manifest": self.view.index_manifest(),
    }
    with open(path, "w", encoding="utf-8") as fh:
      json.dump(doc, fh, indent=2, sort_keys=True)
    return doc

  def stats(self) -> dict:
    return {
      "n_docs": self.n_docs,
      "avgdl": self.avgdl,
      "n_terms": len(self._postings),
      "n_postings": sum(len(p) // 2 for _, p in self._postings.values()),
      "build_ms": self.build_ms,
      "posting_array_bytes": self.posting_array_bytes(),
    }

  def posting_array_bytes(self) -> int:
    """MEASURED bytes of the postings arrays themselves (sum of buffer sizes).

    This is the deployable index payload: the interleaved postings arrays plus
    one df per term. It excludes Python object overhead, which is reported
    separately as peak RSS. Both are reported because a mobile claim needs the
    payload and a desktop claim needs the RSS, and conflating them is how
    storage numbers get inflated.
    """
    arrays = sum(p.buffer_info()[1] * p.itemsize for _, p in self._postings.values())
    return arrays + len(self._postings) * 8
