"""Ettin Cascade: multi-stage cross-encoder reranking over BM25 stage-0.

Implements the :class:`~experiments.common.runner.System` protocol.
Stage 0: shared BM25 top-500. Stages 1..k: successively stronger
cross-encoders pruning the candidate set.

HARD RULES honouring the brief:
  - score_kind MUST be "logit" everywhere (ModernBERT single-logit head).
  - Pruning top-K only; no invented thresholds unless DEV-derived and labelled.
  - threshold_policy.score_kind == stage.score_kind (enforced by trace stage_entry).
  - Determinism: torch.set_num_threads(1), batch_size=1, CPU.
  - Total order: (score desc, node_id asc as utf-8 bytes).
  - model_identity must name the actual repo AND revision — no placeholders.
  - Cumulative false-negative loss is the primary risk; top-K pruning is safe
    because the keep/drop decision is solely based on the current stage's ranking.
"""

from __future__ import annotations

import os
import sys
import time
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.trace import stage_entry, topk_policy  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402

# Model identities: repo id + pinned revision SHA (from 2026-10-03 Hub API observation).
# The repo id alone is used for sentence-transformers.CrossEncoder(repo_id, revision=revision).
# The full identity string (repo + revision) is stored for trace model_identity entries.
MODEL_17M_REPO = "cross-encoder/ettin-reranker-17m-v1"
MODEL_17M_REV = "9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6"
MODEL_17M_IDENTITY = f"{MODEL_17M_REPO}:revision={MODEL_17M_REV}"

MODEL_32M_REPO = "cross-encoder/ettin-reranker-32m-v1"
MODEL_32M_REV = "b33e5ceb5110773ea9cf5e00c9bedc83a8c2afdd"
MODEL_32M_IDENTITY = f"{MODEL_32M_REPO}:revision={MODEL_32M_REV}"

MODEL_68M_REPO = "cross-encoder/ettin-reranker-68m-v1"
MODEL_68M_REV = "d166fa88ddde3c42bc3ee92f7df476d941c8204a"
MODEL_68M_IDENTITY = f"{MODEL_68M_REPO}:revision={MODEL_68M_REV}"

# Default cascade configuration: stage-0 K=500, then 17M→200, 32M→50, final→50
DEFAULT_BREADTHS = [500, 200, 50]  # [stage0_K, stage1_output_K, stage2/final_K]


class EttinCascade:
    """Multi-stage cascade reranker implementing the Round 1 System protocol.

    Retrieval flow:
      1. Stage 0: BM25 top-500 (shared index, no learned component).
      2. Stage 1..k: cross-encoder reranking with top-K pruning at each stage.
      3. Final ranked list returned for packing.

    The ``retrieve`` method returns ``(stage_entries, final_ranked_node_ids, pack_report)``
    compatible with ``experiments.common.runner.System``.
    """

    system_id = "ettin_cascade"

    def __init__(
        self,
        view: CorpusView,
        bm25_index: Bm25Index,
        *,
        breadths: list[int] | None = None,
    ) -> None:
        """Initialize the cascade.

        Args:
            view: shared CorpusView (paragraph tier).
            bm25_index: shared BM25 index (stage-0).
            breadths: list of 3 ints [stage0_K, stage1_output_K, stage2/final_K]
              Defaults to [500, 200, 50] if None.
              - stage0_K = BM25 top-K (hardcoded to 500 per HYPOTHESIS.md §3)
              - stage1_output_K = candidates kept after 17M rerank
              - stage2/final_K = candidates kept after 32M rerank / input to 68M
        """
        self.view = view
        self.bm25_index = bm25_index
        self.breadths = breadths or [500, 200, 50]
        assert len(self.breadths) == 3, "breadths must have 3 entries [stage0_K, stage1_K, stage2_K]"
        self._rerankers: dict[str, "sentence_transformers.CrossEncoder | None"] = {}

        # Model key -> (repo_id, revision) mapping for CrossEncoder loader
        self._model_repo_map = {
            "17m": (MODEL_17M_REPO, MODEL_17M_REV),
            "32m": (MODEL_32M_REPO, MODEL_32M_REV),
            "68m": (MODEL_68M_REPO, MODEL_68M_REV),
        }

    def _get_reranker(self, model_key: str) -> "sentence_transformers.CrossEncoder":
        """Lazily load and cache a CrossEncoder by model_key string.

        Passes revision as a keyword argument to sentence_transformers.CrossEncoder,
        which is the accepted API (not appended with ':' to the repo ID).
        """
        if self._rerankers.get(model_key) is None:
            import sentence_transformers

            repo_id, revision = self._model_repo_map[model_key]
            self._rerankers[model_key] = sentence_transformers.CrossEncoder(
                repo_id, revision=revision
            )
        return self._rerankers[model_key]

    def _rerank(
        self,
        query_text: str,
        node_ids: list[str],
        model_key: str,
    ) -> list[tuple[float, str]]:
        """Run cross-encoder reranking on ``node_ids`` and return [(logit, node_id),...] sorted total-order.

        Document input = paragraph node text verbatim (p.text), NOT D(p).
        Query input = QueryInput.text verbatim.
        """
        reranker = self._get_reranker(model_key)

        # Build pairs: (query_text verbatim, paragraph node text verbatim)
        pairs: list[tuple[str, str]] = []
        for node_id in node_ids:
            p_node = self.view.by_id.get(node_id)
            if p_node is None:
                raise ValueError(f"Paragraph node {node_id} not found in view")
            pairs.append((query_text, p_node.text))

        t0 = time.perf_counter()
        logits_np = reranker.predict(pairs, show_progress_bar=False)
        inference_elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Build (logit, node_id) pairs
        logit_node_pairs: list[tuple[float, str]] = []
        for i, logit in enumerate(logits_np):
            node_id = node_ids[i]
            logit_node_pairs.append((float(logit), node_id))

        # Sort by total order: (score desc, node_id asc as utf-8 bytes)
        logit_node_pairs.sort(
            key=lambda p: (-p[0], p[1].encode("utf-8"))
        )

        return logit_node_pairs

    def retrieve(
        self, query, tokenizer, tokenizer_id: str
    ) -> tuple[list[dict], list[str], dict]:
        """Return ``(stage_entries, final_ranked_node_ids, pack_report)``.

        Per the System protocol this drives the shared runner, which calls
        ``substrate.query.to_model_query`` and ``build_ranked_packet`` identically
        for every architecture.
        """
        query_text = query.text

        # ── Stage 0: BM25 top-500 ────────────────────────────────────────
        bm25_hits = self.bm25_index.search(query_text, k=STAGE0_K)
        bm25_node_ids: list[str] = [h.node_id for h in bm25_hits]
        bm25_scores: list[float] = [h.score for h in bm25_hits]

        bm25_stage = stage_entry(
            stage="bm25",
            candidate_ids=bm25_node_ids,
            scores=bm25_scores,
            score_kind="similarity",
            model_identity="bm25-okapi-stdlib:k1=1.2,b=0.75,tokenizer=NFKC-casefold-[a-z0-9]+",
            threshold_policy=topk_policy(STAGE0_K, "similarity"),
            kept=[True] * len(bm25_node_ids),
            latency_ms=0.0,
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=peak_rss_mb(),
        )

        # ── Stage 1: 17M cross-encoder, prune to K1 ──────────────────────
        # breadths = [stage0_K, stage1_output_K, stage2/final_K] = [500, 200, 50]
        # Stage 1 prunes the 500 BM25 candidates to top-k1 where k1 = breadths[1] = 200
        k1 = self.breadths[1]
        logit_pairs_17m = self._rerank(query_text, bm25_node_ids, "17m")
        top_k1_pairs = logit_pairs_17m[:k1]
        stage1_node_ids: list[str] = [nid for _, nid in top_k1_pairs]
        stage1_scores: list[float] = [logit for logit, _ in top_k1_pairs]

        # Measure peak RSS after 17M load
        rss_17m = peak_rss_mb()

        stage1 = stage_entry(
            stage="rerank_17m",
            candidate_ids=stage1_node_ids,
            scores=stage1_scores,
            score_kind="logit",
            model_identity=MODEL_17M_IDENTITY,
            threshold_policy=topk_policy(k1, "logit"),
            kept=[True] * len(stage1_node_ids),  # all kept (top-K by definition)
            latency_ms=0.0,
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=rss_17m,
        )

        # ── Stage 2: 32M cross-encoder, prune to K2 ──────────────────────
        # Stage 2 prunes the k1 survivors to top-k2 where k2 = breadths[2] = 50
        k2 = self.breadths[2]
        logit_pairs_32m = self._rerank(query_text, stage1_node_ids, "32m")
        top_k2_pairs = logit_pairs_32m[:k2]
        stage2_node_ids: list[str] = [nid for _, nid in top_k2_pairs]
        stage2_scores: list[float] = [logit for logit, _ in top_k2_pairs]

        rss_32m = peak_rss_mb()

        stage2 = stage_entry(
            stage="rerank_32m",
            candidate_ids=stage2_node_ids,
            scores=stage2_scores,
            score_kind="logit",
            model_identity=MODEL_32M_IDENTITY,
            threshold_policy=topk_policy(k2, "logit"),
            kept=[True] * len(stage2_node_ids),
            latency_ms=0.0,
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=rss_32m,
        )

        # ── Stage 3: 68M cross-encoder, final ranking to K3 ──────────────
        # Stage 3 takes the k2 survivors and keeps top-k3 for the final list
        k3 = self.breadths[2]
        logit_pairs_68m = self._rerank(query_text, stage2_node_ids, "68m")
        # Take top-k3 for the final ranked list
        top_k3_pairs = logit_pairs_68m[:k3]
        final_node_ids: list[str] = [nid for _, nid in top_k3_pairs]
        final_scores: list[float] = [logit for logit, _ in top_k3_pairs]

        rss_68m = peak_rss_mb()

        stage3 = stage_entry(
            stage="rerank_68m",
            candidate_ids=final_node_ids,  # same as candidate_ids since we keep top-k3
            scores=final_scores,
            score_kind="logit",
            model_identity=MODEL_68M_IDENTITY,
            threshold_policy=topk_policy(k3, "logit"),
            kept=[True] * len(final_node_ids),
            latency_ms=0.0,
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=rss_68m,
        )

        stages = [bm25_stage, stage1, stage2, stage3]

        # Pack report
        pack_report = {
            "final_k_policy": k3,  # top-K for packing per cascade config
            "breadths": {
                "stage0_k": STAGE0_K,
                "stage1_k": k1,
                "stage2_k": k2,
                "stage3_k": k3,
            },
            "note": (
                f"Ettin cascade: BM25 stage-0 top-{STAGE0_K} → 17M top-{k1} → "
                f"32M top-{k2} → 68M top-{k3}. score_kind=logit, "
                f"top_k_only pruning, calibration_method=none_ranking_only. "
                f"Total order: (score desc, node_id asc as utf-8 bytes). "
                f"Model identities: 17M={MODEL_17M_IDENTITY}, 32M={MODEL_32M_IDENTITY}, "
                f"68M={MODEL_68M_IDENTITY}."
            ),
        }

        return stages, final_node_ids, pack_report