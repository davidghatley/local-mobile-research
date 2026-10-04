"""Baseline B2: Lexical (BM25) + static semantic retrieval.

Implements HYPOTHESIS.md Section 4:
  - Static embedding model: sentence-transformers/static-retrieval-mrl-en-v1
    at revision f60985c706f192d45d218078e49e5a8b6f15283a
  - Document strings D(p) identical to B1's BM25 index (title + heading + paragraph,
    with (lead) heading omitted)
  - Mean-pooled token embeddings, dim 1024, no L2 norm inside,
    cosine = inner product of L2-normalised vectors
  - Static top-500, then Borda fusion with BM25 top-500
  - Label-free proxy for static-disjoint recall (custodian labels not read)
"""

from __future__ import annotations

import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.trace import stage_entry, topk_policy  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402

# Model identity per HYPOTHESIS.md §4.1
B2_MODEL_IDENTITY = (
    "sentence-transformers/static-retrieval-mrl-en-v1:"
    "revision=f60985c706f192d45d218078e49e5a8b6f15283a"
)

# --- Static embedding model lazy loading and caching ---

_ARTIFACTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "artifacts"
)
_EMBEDDINGS_NPY = os.path.join(_ARTIFACTS_DIR, "b2_static_embeddings.npy")
_B2_MODEL = None
_EMBEDDING_TABLE_ASSERTED = False


def _ensure_artifacts_dir() -> None:
    os.makedirs(_ARTIFACTS_DIR, exist_ok=True)


def _get_b2_model() -> "sentence_transformers.SentenceTransformer":
    global _B2_MODEL
    if _B2_MODEL is None:
        import sentence_transformers
        _B2_MODEL = sentence_transformers.SentenceTransformer(
            "sentence-transformers/static-retrieval-mrl-en-v1",
            revision="f60985c706f192d45d218078e49e5a8b6f15283a",
        )
    return _B2_MODEL


def _assert_embedding_table_shape() -> None:
    global _EMBEDDING_TABLE_ASSERTED
    if _EMBEDDING_TABLE_ASSERTED:
        return
    model = _get_b2_model()
    # The StaticEmbedding module's weight table: 30522 x 1024 fp32
    # Verify by checking the model's first module embedding weight shape
    mod = model._modules["0"]
    w = mod.embedding.weight
    expected_shape = (30522, 1024)
    if w.shape != expected_shape:
        raise RuntimeError(
            f"StaticEmbedding weight table shape {w.shape} != expected "
            f"{expected_shape}. Aborting."
        )
    _EMBEDDING_TABLE_ASSERTED = True


def _embed_documents_lazy(view: CorpusView) -> np.ndarray:
    """Lazily embed all paragraph documents and cache to .npy.

    Returns array of shape (n_docs, 1024) fp32, mean-pooled token embeddings,
    NO L2 norm inside (normalize_embeddings=False).
    """
    _ensure_artifacts_dir()

    n_docs = view.n_docs

    # Check cache
    if os.path.isfile(_EMBEDDINGS_NPY):
        embeds = np.load(_EMBEDDINGS_NPY)
        if embeds.shape == (n_docs, 1024) and embeds.dtype == np.float32:
            # Re-assert shape integrity
            _assert_embedding_table_shape()
            return embeds
        else:
            # Cache miss / mismatch - delete and rebuild
            os.remove(_EMBEDDINGS_NPY)

    # Embed all doc_strings
    model = _get_b2_model()

    t0 = time.perf_counter()
    doc_texts = view.doc_strings
    embeds = model.encode(
        doc_texts,
        normalize_embeddings=False,  # NO L2 norm inside; cosine = inner product of L2-normalised vectors
        batch_size=32,
        show_progress_bar=False,
    )
    build_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    if embeds.shape != (n_docs, 1024) or embeds.dtype != np.float32:
        raise RuntimeError(
            f"Embedding table shape {embeds.shape} / dtype {embeds.dtype} "
            f"!= expected (n_docs={n_docs}, fp32)."
        )

    # Cache to disk
    np.save(_EMBEDDINGS_NPY, embeds)

    # Assert shape per HYPOTHESIS.md §4.1
    _assert_embedding_table_shape()

    cache_bytes = os.path.getsize(_EMBEDDINGS_NPY)
    print(
        f"[B2] Embed build time: {build_elapsed_ms:.1f} ms, "
        f"vector cache bytes on disk: {cache_bytes:,} "
        f"({cache_bytes / 1024 / 1024:.1f} MiB)"
    )
    return embeds


def _compute_bm25_rank(view: CorpusView, bm25_index: Bm25Index, query_text: str) -> dict[str, int]:
    """Return {node_id: 1-based rank} for BM25 top-500."""
    hits = bm25_index.search(query_text, k=STAGE0_K)
    rank: dict[str, int] = {}
    for i, hit in enumerate(hits):
        rank[hit.node_id] = i + 1  # 1-based rank
    return rank


def _compute_static_rank(view: CorpusView, embeds: np.ndarray, query_text: str) -> dict[str, int]:
    """Compute static channel rankings: cosine similarity = inner product of L2-normalised vectors.

    Returns {node_id: 1-based rank} for ALL documents, sorted by cosine similarity
    to the query vector, descending. Ties broken by node_id ascending (utf-8 bytes).
    """
    import torch
    import torch.nn.functional as fnf

    # Encode query (mean-pooled, no L2 norm inside)
    model = _get_b2_model()
    q_embed = model.encode(
        [query_text],
        normalize_embeddings=False,
        batch_size=1,
        show_progress_bar=False,
    )[0]  # shape (1024,)

    # L2-normalize query and doc embeddings; inner product = cosine similarity
    q_tensor = fnf.normalize(torch.from_numpy(q_embed).float().unsqueeze(0), p=2, dim=1)[0]  # (1, 1024)
    doc_tensor = fnf.normalize(torch.from_numpy(embeds).float(), p=2, dim=1)  # (n_docs, 1024)

    sims = (q_tensor * doc_tensor).sum(dim=1).cpu().numpy()  # (n_docs,)

    # Rank by score descending, then node_id ascending as tie-break
    ranked_indices = np.argsort(-sims)  # descending score

    rank: dict[str, int] = {}
    for rank_idx, doc_idx in enumerate(ranked_indices):
        nid = view.node_id(doc_idx)
        rank[nid] = rank_idx + 1  # 1-based rank

    return rank


def _borda_fuse(
    bm25_rank: dict[str, int],
    static_rank: dict[str, int],
    stage0_k: int = STAGE0_K,
) -> list[str]:
    """Borda fusion of BM25 and static rankings.

    r_bm25(c) = 1-based rank in BM25 order, or 501 if absent
    r_static(c) = 1-based rank in static order, or 501 if absent
    fused(c) = r_bm25(c) + r_static(c)
    rank by (fused ascending, node_id ascending as utf-8 bytes)
    """
    all_ids = set(bm25_rank.keys()) | set(static_rank.keys())
    fused: list[tuple[int, bytes, str]] = []  # (fused_score, node_id_bytes, node_id)

    for nid in all_ids:
        r_bm = bm25_rank.get(nid, stage0_k + 1)  # 501 if absent
        r_st = static_rank.get(nid, stage0_k + 1)  # 501 if absent
        fused_score = r_bm + r_st
        nid_bytes = nid.encode("utf-8")
        fused.append((fused_score, nid_bytes, nid))

    # Total order: (fused ascending, node_id ascending as utf-8 bytes)
    fused.sort(key=lambda x: (x[0], x[1]))
    return [fid for _, _, fid in fused]


def _compute_label_free_proxy(
    dev_entries: list[dict],
    bm25_index: Bm25Index,
    view: CorpusView,
    static_rank_func,
) -> dict:
    """Compute the label-free proxy for static-disjoint recall.

    Jaccard distance between static top-500 and BM25 top-500 sets,
    plus count of documents in static-top-500 but not BM25-top-500.

    Note: the true arbiter (requiring custodian labels) is NOT YET MEASURED.
    """
    from experiments.common.bm25 import STAGE0_K as SK

    jaccard_distances: list[float] = []
    only_static_count_total = 0

    for entry in dev_entries:
        qid = entry.get("question_id", "")
        query_text = entry.get("text", "")

        # BM25 top-500
        bm25_rank = _compute_bm25_rank(view, bm25_index, query_text)
        bm25_top500_set = set(bm25_rank.keys())

        # Static top-500
        static_rank = static_rank_func(view, query_text)
        static_top500_set = set(static_rank.keys())

        # Jaccard distance
        intersection = len(bm25_top500_set & static_top500_set)
        union = len(bm25_top500_set | static_top500_set)
        jaccard_sim = intersection / union if union > 0 else 0.0
        jaccard_dist = 1.0 - jaccard_sim
        jaccard_distances.append(jaccard_dist)

        # Documents in static-top-500 but not BM25-top-500
        only_static = static_top500_set - bm25_top500_set
        only_static_count_total += len(only_static)

    mean_jaccard = float(np.mean(jaccard_distances)) if jaccard_distances else 0.0
    return {
        "mean_jaccard_distance": mean_jaccard,
        "n_questions": len(jaccard_distances),
        "only_static_count_total": only_static_count_total,
        "true_arbiter_needs_labels": True,  # explicitly NOT YET MEASURED
    }


class B2Static:
    """B2 -- BM25 + static semantic channel, Borda-fused stage-0 set.

    system_id = "B2_bm25_static_union"
    """

    system_id = "B2_bm25_static_union"

    def __init__(self, view: CorpusView, bm25_index: Bm25Index | None = None) -> None:
        self.view = view
        self.bm25_index = bm25_index
        self.embeds: np.ndarray | None = None
        self._static_rank_cache: dict[str, dict[str, int]] | None = None

    def _get_static_rank(self, query_text: str) -> dict[str, int]:
        """Compute static channel rankings, lazily embedding on first use."""
        if self._static_rank_cache is not None and query_text in self._static_rank_cache:
            return self._static_rank_cache[query_text]

        embeds = _embed_documents_lazy(self.view)
        rank = _compute_static_rank(self.view, embeds, query_text)
        return rank

    def retrieve(self, query, tokenizer, tokenizer_id: str):
        """Run B2 retrieval.

        Returns (stage_entries, final_ranked_node_ids, pack_report).
        """
        query_text = query.text

        # BM25 top-500
        bm25_rank = _compute_bm25_rank(self.view, self.bm25_index, query_text)

        # Static top-500 (lazily embeds documents on first use)
        static_rank = self._get_static_rank(query_text)

        # Borda fusion
        fused_list = _borda_fuse(bm25_rank, static_rank)
        final_k = min(STAGE0_K, len(fused_list))
        final_ids = fused_list[:final_k]

        # --- Stage entries ---

        # BM25 stage
        bm25_hits = self.bm25_index.search(query_text, k=STAGE0_K)
        bm25_ids = [h.node_id for h in bm25_hits]
        bm25_scores = [h.score for h in bm25_hits]

        bm25_stage = stage_entry(
            stage="bm25",
            candidate_ids=bm25_ids,
            scores=bm25_scores,
            score_kind="similarity",
            model_identity="bm25-okapi-stdlib:k1=1.2,b=0.75,tokenizer=NFKC-casefold-[a-z0-9]+",
            threshold_policy=topk_policy(STAGE0_K, "similarity"),
            kept=[True] * len(bm25_ids),
            latency_ms=0.0,
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=peak_rss_mb(),
        )

        # Static channel stage
        static_stage = stage_entry(
            stage="static_union",
            candidate_ids=final_ids,
            scores=[0.0] * len(final_ids),  # fusion ranks; raw scores not applicable
            score_kind="similarity",
            model_identity=B2_MODEL_IDENTITY,
            threshold_policy=topk_policy(STAGE0_K, "similarity"),
            kept=[True] * len(final_ids),
            latency_ms=0.0,  # query latency measured separately
            model_loading_latency_ms=None,
            inference_latency_ms=None,
            peak_rss_mb=peak_rss_mb(),
        )

        stages = [bm25_stage, static_stage]

        # --- Pack report ---
        pack_report = {
            "final_k_policy": STAGE0_K,
            "note": (
                "Borda fusion of BM25 top-500 and static top-500 "
                "(fused rank = r_bm25 + r_static, absent=501, "
                "rank by fused asc, node_id asc)"
            ),
        }

        return stages, final_ids, pack_report