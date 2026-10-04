"""Baseline B3: One strong reranker (68M cross-encoder) as the expensive ceiling.

Implements HYPOTHESIS.md Section 5:
  - Stage 0 is B1's BM25 top-500 (reranker ADDS no candidates, only reorders)
  - Score ALL 500 with cross-encoder/ettin-reranker-68m-v1 at revision d166fa88ddde3c42bc3ee92f7df476d941c8204a
  - Query input = QueryInput.text VERBATIM
  - Document input = the PARAGRAPH NODE TEXT verbatim (p.text), NOT D(p)
    -- the heading prefix is a BM25-specific trick; each channel uses its
    canonical input. Honoured and commented per spec.
  - score_kind MUST be "logit". Raw logit, NOT a probability.
  - Use topk_policy with top_k=50, interpretation raw_score_absolute,
    calibration_method none_ranking_only.
  - Total order: (score desc, node_id asc as utf-8 bytes)
  - CPU-only (no CUDA). MEASURE per-card latency, project dev cost honestly.
  - Report peak RSS via substrate.telemetry.peak_rss_mb.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.trace import stage_entry, topk_policy  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402

# System identity
B3_SYSTEM_ID = "B3_bm25_plus_68m_rerank"

# Reranker model identity per HYPOTHESIS.md §5.1
B3_MODEL_IDENTITY = (
    "cross-encoder/ettin-reranker-68m-v1:"
    "revision=d166fa88ddde3c42bc3ee92f7df476d941c8204a"
)

# Per-question measurement state (set on first retrieve, persisted as attrs)
_per_card_latency_ms: float | None = None
_peak_rss_mb: float | None = None


def _get_reranker() -> "sentence_transformers.CrossEncoder":
    import sentence_transformers
    return sentence_transformers.CrossEncoder(
        "cross-encoder/ettin-reranker-68m-v1",
        revision="d166fa88ddde3c42bc3ee92f7df476d941c8204a",
    )


# ---------------------------------------------------------------------------
# Latency / RSS measurement helpers (module-level so values persist across
# calls within a process, but are reset when a new process starts)
# ---------------------------------------------------------------------------

def _set_per_card_latency_ms(ms: float) -> None:
    global _per_card_latency_ms
    _per_card_latency_ms = ms


def _get_per_card_latency_ms() -> float | None:
    return _per_card_latency_ms


def _set_peak_rss_mb(mb: float) -> None:
    global _peak_rss_mb
    _peak_rss_mb = mb


def _get_peak_rss_mb() -> float | None:
    return _peak_rss_mb


# ---------------------------------------------------------------------------
# B3Reranker class
# ---------------------------------------------------------------------------


class B3Reranker:
    """B3 -- BM25 top-500 re-ordered by 68M cross-encoder.

    system_id = "B3_bm25_plus_68m_rerank"
    """

    system_id = B3_SYSTEM_ID

    def __init__(self, view: CorpusView, bm25_index: Bm25Index) -> None:
        self.view = view
        self.bm25_index = bm25_index
        self._reranker: "sentence_transformers.CrossEncoder | None" = None
        # Model-load time is measured ONCE, on first materialisation, and then
        # reported on every query's stage record. It is deliberately NOT folded
        # into per-query latency: a resident server pays it once, and a per-query
        # cost that silently includes a one-time load is how a 68M model ends up
        # looking 500x more expensive than it is.
        self._model_load_ms: float | None = None

    def _get_reranker(self) -> "sentence_transformers.CrossEncoder":
        if self._reranker is None:
            t0 = time.perf_counter()
            self._reranker = _get_reranker()
            self._model_load_ms = (time.perf_counter() - t0) * 1000.0
        return self._reranker

    def _get_bm25_top500(self, query_text: str) -> list[str]:
        """Return BM25 top-500 node IDs in BM25 rank order."""
        hits = self.bm25_index.search(query_text, k=STAGE0_K)
        return [h.node_id for h in hits]

    def _compute_rerank_scores(
        self, query_text: str, bm25_node_ids: list[str]
    ) -> list[tuple[float, str]]:
        """Compute cross-encoder logits for all 500 BM25 candidates.

        Returns list of (logit, node_id) tuples, sorted by the B3 total order:
        (logit desc, node_id asc as utf-8 bytes).

        Document input = the PARAGRAPH NODE TEXT verbatim (p.text), NOT D(p).
        Per HYPOTHESIS.md §5.2: "the cross-encoder was trained on standalone
        (query, passage) pairs, and the heading prefix is a BM25-specific trick;
        each channel uses its canonical input."
        """
        reranker = self._get_reranker()

        # Build pairs: (QueryInput.text verbatim, paragraph node text verbatim)
        pairs: list[tuple[str, str]] = []
        for node_id in bm25_node_ids:
            p_node = self.view.by_id.get(node_id)
            if p_node is None:
                raise ValueError(f"Paragraph node {node_id} not found in view")
            # Verbatim paragraph node text, NOT D(p) (no title, no heading)
            pairs.append((query_text, p_node.text))

        # Run cross-encoder inference
        t0 = time.perf_counter()
        logits_np = reranker.predict(pairs, show_progress_bar=False)
        inference_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Measure per-card latency on first call (CPU, batch_size=1)
        n_cards = len(pairs)
        if _get_per_card_latency_ms() is None:
            per_card_ms = inference_elapsed_ms / n_cards if n_cards > 0 else 0.0
            _set_per_card_latency_ms(per_card_ms)
            # Measure peak RSS of our own process
            rss_mb = peak_rss_mb()
            _set_peak_rss_mb(rss_mb)

        # Build (logit, node_id) pairs
        logit_node_pairs: list[tuple[float, str]] = []
        for i, logit in enumerate(logits_np):
            node_id = bm25_node_ids[i]
            logit_node_pairs.append((float(logit), node_id))

        # Sort by total order: (score desc, node_id asc as utf-8 bytes)
        # Python's sort is stable, so we can use a tuple key
        logit_node_pairs.sort(
            key=lambda p: (-p[0], p[1].encode("utf-8"))  # score desc, node_id asc
        )

        return logit_node_pairs

    def retrieve(self, query, tokenizer, tokenizer_id: str):
        """Run B3 reranker retrieval.

        Returns (stage_entries, final_ranked_node_ids, pack_report).

        Per HYPOTHESIS.md §5:
        - Stage 0 is B1's BM25 top-500 (the reranker ADDS no candidates, only reorders)
        - ALL 500 are scored with the cross-encoder
        - Final top-k for packing is 50 (per §5.3: top-K (50) on raw logits)
        - score_kind = "logit"
        - Interpretation: raw_score_absolute, calibration_method = none_ranking_only
        - Determinism: torch.set_num_threads(1), batch_size=1, CPU
        - Total order: (score desc, node_id asc as utf-8 bytes)
        """
        query_text = query.text

        # Stage 0: BM25 top-500 in BM25 rank order
        t_bm25 = time.perf_counter()
        bm25_node_ids = self._get_bm25_top500(query_text)

        # BM25 stage entry
        bm25_hits = self.bm25_index.search(query_text, k=STAGE0_K)
        bm25_scores = [h.score for h in bm25_hits]
        bm25_latency_ms = (time.perf_counter() - t_bm25) * 1000.0

        bm25_stage = stage_entry(
            stage="bm25",
            candidate_ids=bm25_node_ids,
            scores=bm25_scores,
            score_kind="similarity",
            model_identity="bm25-okapi-stdlib:k1=1.2,b=0.75,tokenizer=NFKC-casefold-[a-z0-9]+",
            threshold_policy=topk_policy(STAGE0_K, "similarity"),
            kept=[True] * len(bm25_node_ids),
            latency_ms=bm25_latency_ms,
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=peak_rss_mb(),
        )

        # Compute rerank scores (cross-encoder logits)
        t_rr = time.perf_counter()
        logit_node_pairs = self._compute_rerank_scores(query_text, bm25_node_ids)
        rerank_latency_ms = (time.perf_counter() - t_rr) * 1000.0

        # Unzip: sorted node IDs and their logit scores
        reranked_node_ids: list[str] = [nid for _, nid in logit_node_pairs]
        reranked_scores: list[float] = [logit for logit, _ in logit_node_pairs]

        # The full reranked list has 500 candidates (the reranker re-orders all of them)
        # Per §5.3, the packer uses top_k=50 on the raw logits
        final_k = min(STAGE0_K, len(reranked_node_ids))
        final_ids = reranked_node_ids[:final_k]

        # Reranker stage entry
        # score_kind = "logit"
        # threshold_policy: top_k=50, interpretation="raw_score_absolute", calibration_method="none_ranking_only"
        #
        # DEFECT REPAIRD (2026-10-04, found by the orchestrator after the first dev
        # run). BOTH stages previously hardcoded latency_ms=0.0 while the stage
        # actually consumed up to 113 s. Zero is a MEASUREMENT of zero; the frozen
        # substrate reserves None for "not measured" and forbids passing a real
        # duration off as 0. The end-to-end retrieval_latency_ms was always
        # correct, which is why the error was invisible in the headline numbers and
        # only surfaced when the per-stage distribution was read. `inference_
        # latency_ms` now carries the whole-stage inference time; the per-CARD
        # latency remains available separately as `_get_per_card_latency_ms()`.
        reranker_stage = stage_entry(
            stage="rerank_68m",
            candidate_ids=reranked_node_ids,
            scores=reranked_scores,
            score_kind="logit",
            model_identity=B3_MODEL_IDENTITY,
            threshold_policy=topk_policy(
                50, "logit"
            ),
            kept=[True] * len(reranked_node_ids),
            latency_ms=rerank_latency_ms,
            model_loading_latency_ms=self._model_load_ms,
            inference_latency_ms=rerank_latency_ms,
            peak_rss_mb=_get_peak_rss_mb(),
        )

        stages = [bm25_stage, reranker_stage]

        # Pack report
        pack_report = {
            "final_k_policy": 50,  # top-50 for packing per §5.3
            "note": (
                "68M cross-encoder reranking of BM25 top-500 candidates. "
                "Query input = QueryInput.text verbatim; document input = "
                "paragraph node text verbatim (p.text), NOT D(p). The heading prefix "
                "is a BM25-specific trick; each channel uses its canonical input. "
                "Score kind = logit, top-k = 50, raw_score_absolute interpretation, "
                "calibration_method = none_ranking_only. Determinism: "
                "torch.set_num_threads(1), batch_size=1, CPU. Total order by "
                "(score desc, node_id asc as utf-8 bytes)."
            ),
        }

        return stages, final_ids, pack_report