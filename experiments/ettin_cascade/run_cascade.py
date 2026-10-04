"""CLI for running the Ettin cascade retrieval on a corpus split.

Retrieval-only (generator=None). Reuses experiments/common/runner.py.

Usage:
    python -m experiments.ettin_cascade.run_cascade \
        --stages 17m,32m,68m --breadths 500,200,50 \
        --split dev --limit 3 --out /tmp/cascade_run
"""

from __future__ import annotations

import argparse
import json
import sys
import os

from experiments.common.runner import run_split  # noqa: E402
from experiments.common.corpus_view import load_questions, CorpusView  # noqa: E402
from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.ettin_cascade.cascade import EttinCascade  # noqa: E402
from experiments.common.tokenizer import pinned_tokenizer_callable  # noqa: E402


def _parse_models(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def _parse_breadths(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Ettin cascade retrieval on a split."
    )
    parser.add_argument(
        "--stages",
        type=_parse_models,
        default=["17m", "32m", "68m"],
        help="Comma-separated list of cross-encoder model sizes "
        "(e.g. 17m,32m,68m). Default: 17m,32m,68m",
    )
    parser.add_argument(
        "--breadths",
        type=_parse_breadths,
        default=[500, 200, 50],
        help="Comma-separated list of 3 ints: [stage0_K, stage1_output_K, "
        "stage2/final_K]. Default: 500,200,50",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="dev",
        help="Which split to run (dev, shadow_dev, train). Default: dev",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max questions to process (None = full split).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="/tmp/cascade_run",
        help="Output directory for traces and report.",
    )
    args = parser.parse_args(argv)

    # Validate breadths
    if len(args.breadths) != 3:
        print(
            f"Error: --breadths must have exactly 3 values [stage0_K, stage1_K, stage2_K], got {len(args.breadths)}",
            file=sys.stderr,
        )
        return 1

    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )

    # Load corpus view and BM25 index (core tier)
    view = CorpusView.load(repo_root, tier="core")
    bm25_index = Bm25Index(view)

    # Initialize cascade
    cascade = EttinCascade(view=view, bm25_index=bm25_index, breadths=args.breadths)

    # Load questions for the split
    questions = load_questions(repo_root, args.split)
    if args.limit is not None:
        questions = questions[: args.limit]

    # Prepare output directory
    os.makedirs(args.out, exist_ok=True)

    # Get pinned tokenizer callable (resident llama-server session)
    # This provides the exact generator tokenizer for evidence token counting
    # and the tokenizer_id string required by the runner protocol.
    with pinned_tokenizer_callable(repo_root) as tok_ctx:
        tokenizer = tok_ctx
        tokenizer_id = tokenizer.tokenizer_id

        # Build a minimal packer context from the view
        # The runner needs: node_text, node_article, entries, per_article_cap
        node_text: dict[str, str] = {}
        node_article: dict[str, str] = {}
        for i, para in enumerate(view.paragraphs):
            node_text[para.node_id] = para.text
            art_id = view.parent_article[i] if i < len(view.parent_article) else ""
            node_article[para.node_id] = art_id

        # Create a simple object with the needed attributes
        class _PackerCtx:
            __slots__ = (
                "node_text",
                "node_article",
                "entries",
                "per_article_cap",
            )

            def __init__(
                self,
                node_text: dict[str, str],
                node_article: dict[str, str],
                entries: list[dict],
                per_article_cap: int,
            ) -> None:
                self.node_text = node_text
                self.node_article = node_article
                self.entries = entries
                self.per_article_cap = per_article_cap

        packer_ctx = _PackerCtx(node_text, node_article, questions, per_article_cap=3)

        # Derive a run_id from the config
        run_id = f"ettin_cascade_{args.split}_{args.breadths[0]}_{args.breadths[1]}_{args.breadths[2]}"

        # Run the split using the shared runner
        # generator=None => retrieval-only; every generator_response is None
        result = run_split(
            system=cascade,
            split=args.split,
            tier="core",
            tokenizer=tokenizer,
            tokenizer_id=tokenizer_id,
            packer_ctx=packer_ctx,
            run_id=run_id,
            seed=42,
            out_dir=args.out,
            question_ids=None,
            limit=args.limit,
            generator=None,  # retrieval-only
            progress_every=10,
        )

        # Print summary
        print(json.dumps(result.summary(), indent=2, sort_keys=True))

        # List trace files
        safe = cascade.system_id.replace("/", "_")
        tier_tag = "core"  # we ran core tier
        traces_path = os.path.join(
            args.out, f"traces_{safe}_{args.split}_{tier_tag}.jsonl"
        )
        if os.path.exists(traces_path):
            print(f"\nTraces written to: {traces_path}")
            with open(traces_path, encoding="utf-8") as tf:
                n_lines = sum(1 for _ in tf)
            print(f"  {n_lines} traces")

            # Quick validation: check all traces pass eval.run_format.validate_trace
            from eval.run_format import validate_trace

            tf.seek(0)
            for line in tf:
                if line.strip():
                    tr = json.loads(line)
                    errors = validate_trace(tr, allow_estimate=False, allow_stub=False)
                    if errors:
                        print(
                            f"  VALIDATION ERROR for {tr.get('question_id')}: {errors[:200]}"
                        )
                    else:
                        print(f"  VALID: {tr.get('question_id')}")

        # Print per-item stage survival info via score_retrieval
        try:
            from experiments.common.score_retrieval import score_traces
            from substrate.query import load_ground_truth

            gt_path = os.path.join(repo_root, "corpus", "ground_truth.json")
            # Note: ground truth may not exist at this path; custodian-held
            print(
                "\n(ground-truth scoring skipped - custodian labels not accessible)"
            )
        except Exception as e:
            print(f"\nGround-truth import note: {e}")

        return 0


if __name__ == "__main__":
    sys.exit(main())