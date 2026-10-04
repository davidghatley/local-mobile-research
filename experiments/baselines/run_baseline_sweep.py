"""CLI sweep driver for Round 1 baselines.

Usage:
    python -m experiments.baselines.run_baseline_sweep \
        --system b1 --split dev --tier core --limit 5 --out /tmp/sweep_out

This builds CorpusView, Bm25Index, TokenizerService, runs run_split() with
generator=None (retrieval-only), writes raw traces via the substrate writer
and a run summary including index_stats and model_identity.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import Bm25Index, STAGE0_K  # noqa: E402
from experiments.common.corpus_view import CorpusView, load_questions  # noqa: E402
from experiments.common.runner import PackerContext, RunResult, run_split  # noqa: E402
from experiments.common.trace import write_traces  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402
from substrate.query import to_model_query  # noqa: E402


def _new_index(view: CorpusView) -> Bm25Index:
    """Build a BM25 index over the view's paragraph documents."""
    import time
    t0 = time.perf_counter()
    idx = Bm25Index(view)
    build_ms = (time.perf_counter() - t0) * 1000.0
    print(f"[index] BM25 build time: {build_ms:.1f} ms")
    return idx


def _new_packer_ctx(view: CorpusView, tokenizer, tokenizer_id: str, entries: list) -> PackerContext:
    return PackerContext.from_view(view, entries)


def _new_view(repo_root: str, tier: str = "core") -> CorpusView:
    return CorpusView.load(repo_root, tier=tier)


def _choose_system(system_id: str, view: CorpusView, bm25_index: Bm25Index):
    """Factory for baseline systems."""
    if system_id == "b1":
        from experiments.baselines.b1_lexical import B1Lexical
        return B1Lexical(index=bm25_index, stage0_k=STAGE0_K)
    elif system_id == "b2":
        from experiments.baselines.b2_static import B2Static
        return B2Static(view=view, bm25_index=bm25_index)
    elif system_id == "b3":
        from experiments.baselines.b3_reranker import B3Reranker
        return B3Reranker(view=view, bm25_index=bm25_index)
    elif system_id == "b4":
        from experiments.baselines.b1_lexical import B1Lexical
        return B1Lexical(index=bm25_index, stage0_k=STAGE0_K)
    else:
        raise ValueError(f"Unknown system: {system_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Round 1 baseline sweep")
    parser.add_argument(
        "--system",
        required=True,
        choices=["b1", "b2", "b3", "b4"],
        help="Baseline system to run",
    )
    parser.add_argument(
        "--split",
        required=True,
        choices=["dev", "shadow_dev"],
        help="Question split to run",
    )
    parser.add_argument(
        "--tier",
        required=True,
        choices=["core", "scale"],
        help="Corpus tier (core = 9,979 docs; scale = 36,609 docs)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max questions to process (None = all)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output directory for traces and summary",
    )
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 1. Build CorpusView
    print(f"[setup] Loading CorpusView (tier={args.tier})...")
    view = _new_view(repo_root, tier=args.tier)
    print(f"  n_docs={view.n_docs}, n_paragraphs={len(view.paragraphs)}")

    # 2. Build BM25 index
    print("[setup] Building BM25 index...")
    bm25_index = _new_index(view)

    # 3. Create TokenizerService
    print("[setup] Starting TokenizerService...")
    from experiments.common.tokenizer import TokenizerService
    tokenizer_service = TokenizerService(repo_root)
    tokenizer = tokenizer_service.tokenizer
    tokenizer_id = tokenizer.tokenizer_id
    print(f"  tokenizer_id={tokenizer_id}")

    # Load questions for the split
    print("[setup] Loading questions...")
    all_entries = load_questions(repo_root, args.split)
    if args.limit is not None:
        all_entries = all_entries[: args.limit]
    print(f"  {len(all_entries)} questions for {args.split} split")

    # 4. Create PackerContext
    packer_ctx = _new_packer_ctx(view, tokenizer, tokenizer_id, all_entries)

    # 5. Create system
    print(f"[setup] Creating system {args.system}...")
    system = _choose_system(args.system, view, bm25_index)

    # 6. Run split
    print(f"[run] Running split {args.split} (limit={args.limit})...")
    t0 = __import__("time").perf_counter()

    result: RunResult = run_split(
        system=system,
        split=args.split,
        tier=args.tier,
        tokenizer=tokenizer,
        tokenizer_id=tokenizer_id,
        packer_ctx=packer_ctx,
        run_id=f"baseline_{args.system}_{args.split}_{args.tier}",
        seed=42,
        out_dir=args.out,
        index_stats=bm25_index.stats(),
        model_identity={
            "system_id": system.system_id,
        },
        question_ids=[e["question_id"] for e in all_entries],
        limit=None,
        generator=None,  # retrieval-only: no generator invocation
    )

    wall_ms = (__import__("time").perf_counter() - t0) * 1000.0
    print(f"[wall] Total wall time: {wall_ms:.1f} ms")
    print(f"  n_ok={result.n_ok}, n_failed={result.n_failed}")

    # 7. Write run summary
    index_stats = result.index_stats
    if "n_docs" not in index_stats:
        index_stats["n_docs"] = view.n_docs
    if "n_terms" not in index_stats:
        index_stats["n_terms"] = bm25_index.n_docs  # approximate

    summary = {
        "system_id": system.system_id,
        "split": args.split,
        "tier": args.tier,
        "n_questions": result.n_ok + result.n_failed,
        "n_ok": result.n_ok,
        "n_failed": result.n_failed,
        "wall_ms": wall_ms,
        "index_stats": index_stats,
        "model_identity": result.model_identity,
    }

    os.makedirs(args.out, exist_ok=True)
    summary_path = os.path.join(args.out, "run_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True)

    print(f"[summary] Written to {summary_path}")
    print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    sys.exit(main())