"""Baseline systems B0/B1 (lexical) and B4 (lexical + the fixed generator).

Numbering is NOT invented here. It follows `experiments/baselines/HYPOTHESIS.md`:
B1 is BM25/lexical only, B2 is lexical + static semantic, B3 is one strong
single reranker, B4 is deterministic retrieval + the fixed generator. This module
implements B1 and B4. B2 lives in `b2_static.py`, B3 in `b3_reranker.py`, and the
ORACLE-EVIDENCE condition -- which is not a retriever at all -- in
`oracle_condition.py`.

B4 is not a separate retriever. B4 = B1's stage-0 exactly + the shared packing
policy + ``decide_default`` + the fixed generator through the frozen path. It is
the true floor because it contains zero learned components: no weights at all,
only the pinned corpus, a stdlib index, and the shared fixed generator.

Regime A == Regime B BY CONSTRUCTION for every baseline. Nothing here trains,
adapts, or reads a synthetic example, so the 21-document Regime-B adaptation
exclusion is vacuously satisfied, and the 21 articles remain in the query-time
corpus. That is recorded rather than assumed.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.common.trace import stage_entry, topk_policy  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402

# B1 has no model. The identity string is still required by the wire schema and
# must be non-empty and non-placeholder, so it names the actual artefact.
BM25_MODEL_IDENTITY = "bm25-okapi-stdlib:k1=1.2,b=0.75,tokenizer=NFKC-casefold-[a-z0-9]+"


class B1Lexical:
  """B0/B1 -- BM25 stage-0 only, then straight to the shared packet budget.

  There is no learned component. The final ranked list handed to the packer is
  the BM25 total order itself, truncated to a declared ``final_k``. With
  ``final_k=None`` the whole positive-overlap set is handed over and the packer's
  1000-token cap does the truncating -- which is the honest reading of "B1 is
  BM25 and the budget is the contract". With an explicit ``final_k`` the cut is a
  DECLARED policy and is recorded in the trace as such.
  """

  system_id = "B1_bm25"

  def __init__(self, index: Bm25Index, stage0_k: int = STAGE0_K,
               final_k: int | None = None) -> None:
    self.index = index
    self.stage0_k = stage0_k
    self.final_k = final_k

  def retrieve(self, query, tokenizer, tokenizer_id: str):
    t0 = time.perf_counter()
    hits = self.index.search(query.text, k=self.stage0_k)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    ids = [h.node_id for h in hits]
    scores = [h.score for h in hits]
    stages = [
      stage_entry(
        stage="bm25",
        candidate_ids=ids,
        scores=scores,
        score_kind="similarity",
        model_identity=BM25_MODEL_IDENTITY,
        threshold_policy=topk_policy(self.stage0_k, "similarity"),
        kept=[True] * len(ids),
        latency_ms=latency_ms,
        model_loading_latency_ms=None,
        inference_latency_ms=None,
        peak_rss_mb=peak_rss_mb(),
      )
    ]
    final = ids if self.final_k is None else ids[: self.final_k]
    pack_report = {
      "final_k_policy": self.final_k,
      "note": (
        "final ranked list truncated to the 1000-token packet budget"
        if self.final_k is None
        else f"declared top-{self.final_k} cut, recorded as a policy"
      ),
    }
    return stages, final, pack_report


class B4DeterministicFloor(B1Lexical):
  """B4 -- B1's stage-0 + the shared budget + ``decide_default`` + the generator.

  Identical retrieval to B1. It is a distinct system id because the tournament
  compares it as the FLOOR: the configuration named in the kill condition of
  `experiments/baselines/HYPOTHESIS.md` §0. Its trace records that generation was
  driven by the frozen `substrate.evidence.run_question` gate and not by any
  adapter-local suppression.
  """

  system_id = "B4_bm25_fixed_generator"

  def __init__(self, index: Bm25Index, stage0_k: int = STAGE0_K,
               final_k: int | None = None) -> None:
    super().__init__(index, stage0_k=stage0_k, final_k=final_k)
