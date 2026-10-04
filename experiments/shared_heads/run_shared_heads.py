"""CLI driver for family C (shared encoder + multiple heads).

Usage:
    python -m experiments.shared_heads.run_shared_heads \
        --split dev --limit 5 --heads coarse,fine,sufficiency --out DIR

Retrieval-only (generator=None). Reuses experiments/common/runner.py, the
shared Bm25Index (STAGE0_K=500), PackerContext, and the exact-tokenizer
service, so token counting is identical to every other arm.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView, load_questions  # noqa: E402
from experiments.common.runner import PackerContext, run_split  # noqa: E402
from experiments.shared_heads.shared_heads import (  # noqa: E402
  BACKBONE_BATCH, MODEL_ID, MODEL_REVISION, SharedHeads, VALID_HEADS)


def parse_args(argv=None):
  ap = argparse.ArgumentParser(description="Shared-heads retrieval run")
  ap.add_argument("--split", required=True, choices=["dev", "shadow_dev"])
  ap.add_argument("--limit", type=int, default=None)
  ap.add_argument("--heads", default="coarse,fine,sufficiency",
                  help="comma-separated subset of coarse,fine,sufficiency")
  ap.add_argument("--out", required=True)
  ap.add_argument("--tier", default="core", choices=["core", "scale"])
  ap.add_argument("--seed", type=int, default=20261004)
  ap.add_argument("--root", default=".")
  return ap.parse_args(argv)


def main(argv=None) -> int:
  args = parse_args(argv)
  heads = tuple(h.strip() for h in args.heads.split(",") if h.strip())
  unknown = [h for h in heads if h not in VALID_HEADS]
  if unknown:
    raise SystemExit(f"unknown heads {unknown!r}; valid: {VALID_HEADS}")
  if not heads:
    raise SystemExit("at least one head required")

  root = args.root
  repo_root = os.path.abspath(root)

  import torch
  print(f"[setup] torch={torch.__version__} threads={torch.get_num_threads()}"
        f"/interop={torch.get_num_interop_threads()} "
        f"(expect 1/1 for the determinism reference)")
  import transformers, sentence_transformers
  print(f"[setup] transformers={transformers.__version__} "
        f"sentence-transformers={sentence_transformers.__version__}")

  t0 = time.perf_counter()
  view = CorpusView.load(repo_root, tier=args.tier)
  index = Bm25Index(view)
  print(f"[setup] view+index {time.perf_counter() - t0:.1f}s "
        f"n_docs={view.n_docs}")

  entries = load_questions(repo_root, args.split)
  ctx = PackerContext.from_view(view, entries)

  from experiments.common.tokenizer import TokenizerService
  tok = TokenizerService(repo_root)
  tokenizer = tok.start()
  try:
    system = SharedHeads(view=view, bm25_index=index, heads=heads,
                         stage0_k=STAGE0_K)
    # Force model load now so load_ms and weight accounting are measured
    # once, outside per-question latency.
    acct = system.weight_accounting
    load_ms = system.load_ms
    print(f"[setup] backbone {MODEL_ID}@{MODEL_REVISION} load_ms={load_ms:.1f}")
    print(f"[setup] resident params MEASURED: {acct}")

    run_id = f"r1-shared-heads-{args.split}-{args.tier}"
    res = run_split(
      system=system,
      split=args.split,
      tier=args.tier,
      tokenizer=tokenizer,
      tokenizer_id=tokenizer.tokenizer_id,
      packer_ctx=ctx,
      run_id=run_id,
      seed=args.seed,
      out_dir=args.out,
      index_stats=index.stats(),
      model_identity={
        "system_id": system.system_id,
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "heads": list(heads),
        "stage0_k": STAGE0_K,
        "backbone_batch": BACKBONE_BATCH,
        "torch_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(),
        "weight_accounting_measured": acct,
        "model_load_ms_measured": load_ms,
        "transformers": transformers.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "torch": torch.__version__,
        "preregistered_threshold_register": {
          "source": ("experiments/comparability/CONTRACT.md §4 via "
                     "R1_CONTRACT_ERRATUM.md E-1b"),
          "dev": {"mmd_items": 13, "mmd_pp": 22.0},
          "dev+shadow_dev": {"mmd_items": 18, "mmd_pp": 12.3},
        },
      },
      question_ids=None,
      limit=args.limit,
      generator=None,  # retrieval-only: no generator invocation
      log=print,
    )
    print(f"[run] ok={res.n_ok} failed={res.n_failed} "
          f"wall_ms={res.wall_ms:.1f}")
    summary = res.summary()
    summary["weight_accounting_measured"] = acct
    summary["model_load_ms_measured"] = load_ms
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "run_summary.json"), "w",
              encoding="utf-8") as fh:
      json.dump(summary, fh, indent=2, sort_keys=True)
    print(f"[summary] -> {os.path.join(args.out, 'run_summary.json')}")
    return 0 if res.n_failed == 0 else 1
  finally:
    tok.close()


if __name__ == "__main__":
  raise SystemExit(main())
