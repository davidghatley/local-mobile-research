#!/usr/bin/env python3
"""Validate a staging dir of QA drafts against corpus + split map.

Defaults to train/dev ONLY: heldout drafts are refused unless BOTH
--allow-heldout is passed AND HELDOUT_CUSTODIAN_MODE=benchmark is set
(custodian seal path). Emits a manifest with hashes/counts/ids only —
never question/answer/label text.

NOTE (Issue 1, Phase 1): "heldout" is retired; the exposed set is now
dev-visible shadow_dev (no custodian gate needed for shadow_dev itself —
the legacy heldout gate below is retained for backward compat). private_test
drafts are ALWAYS refused in-repo (private data lives OUTSIDE the repo at
LMR_PRIVATE_EVAL_DIR, Phase 5).

Usage:
  python3 -m data_tools.validate_qa --staging <dir> --corpus corpus/corpus.jsonl \\
      --split-map corpus/split_map.json [--allow-heldout]

Exit nonzero on any validation failure. No LLM, no network, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from .derive import load_jsonl_nodes, load_split_map
from .qa_schema import to_retriever_input, validate_draft_record
from .verify import CUSTODIAN_ENV_VAR, draft_content_hash, verify_draft


def sha256_text(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--staging", required=True)
  ap.add_argument("--corpus", required=True)
  ap.add_argument("--split-map", required=True)
  ap.add_argument("--allow-heldout", action="store_true", default=False)
  args = ap.parse_args(argv)

  nodes = load_jsonl_nodes(args.corpus)
  split_map = load_split_map(args.split_map)
  try:
    from substrate.splits import (build_article_index, validate_group_map,
                                  validate_question_provenance)
    from substrate.types import CorpusNode
  except ImportError as exc:
    print(f"substrate import failed: {exc}", file=sys.stderr)
    return 2
  corpus_nodes = []
  for n in nodes:
    try:
      corpus_nodes.append(CorpusNode.from_dict(n))
    except ValueError:
      pass
  article_index = build_article_index(corpus_nodes)
  corpus_titles = {k for k in article_index.get("by_title", {})}
  gm = validate_group_map(split_map, corpus_articles=corpus_titles)
  if gm["errors"]:
    print(f"split map invalid: {len(gm['errors'])} error(s)", file=sys.stderr)
    return 2
  map_groups = {g: r["split"] for g, r in split_map["groups"].items()}

  try:
    staged = sorted(f for f in os.listdir(args.staging) if f.endswith(".json"))
  except FileNotFoundError:
    print("staging dir missing", file=sys.stderr)
    return 2
  records = []
  for f in staged:
    with open(os.path.join(args.staging, f), "r", encoding="utf-8") as fh:
      records.append(json.load(fh))
  held = sum(1 for r in records if r.get("split") == "heldout")
  if held and not (args.allow_heldout and os.environ.get(CUSTODIAN_ENV_VAR) == "benchmark"):
    print(f"refused: {held} heldout draft(s); custodian seal path required",
          file=sys.stderr)
    return 2
  priv = sum(1 for r in records if r.get("split") == "private_test")
  if priv:
    print(f"refused: {priv} private_test draft(s) in-repo; private data lives "
          f"outside the repo (LMR_PRIVATE_EVAL_DIR, Phase 5)",
          file=sys.stderr)
    return 2
  ids = [r.get("question_id", "?") for r in records]
  if len(set(ids)) != len(ids):
    print("duplicate question ids", file=sys.stderr)
    return 2
  all_errors: list[str] = []
  for r in records:
    errs = verify_draft(r, nodes, article_index=article_index,
                        map_groups=map_groups,
                        article_to_group=gm["article_to_group"],
                        split_seed=split_map.get("seed", ""),
                        use_map_splits=True)
    # verify_draft includes schema + provenance; keep id/count-only errors.
    all_errors.extend(errs)
  # Substrate question-file shape check on the evaluator-private projection,
  # plus the CANONICAL retriever runtime projection (qid+text only): the hash
  # below must be computable with zero hint fields, proving the runtime input
  # carries no source/group/type leakage.
  from .qa_schema import draft_to_question_entry
  pub = [draft_to_question_entry(r) for r in records
         if isinstance(r, dict) and validate_draft_record(r) == []]
  runtime = []
  for r in records:
    if isinstance(r, dict) and validate_draft_record(r) == []:
      try:
        runtime.append(to_retriever_input(draft_to_question_entry(r)))
      except ValueError as exc:
        all_errors.append(f"{r.get('question_id', '?')}: {exc}")
  manifest = {
    "drafts": len(records),
    "question_ids": sorted(str(i) for i in ids),
    "splits": {s: sum(1 for r in records if r.get("split") == s)
               for s in ("train", "dev", "heldout", "shadow_dev", "private_test")},
    "types": {},
    "approved": sum(1 for r in records
                    if isinstance(r, dict) and r.get("provenance", {}).get(
                      "decision") == "approve" and r.get("provenance", {}).get(
                      "content_hash") == draft_content_hash(r)),
    "errors": len(all_errors),
    "error_list": all_errors[:50],
    "public_projection_ids_sha256": sha256_text(json.dumps(pub, sort_keys=True)),
    "runtime_projection_sha256": sha256_text(json.dumps(runtime, sort_keys=True)),
  }
  for r in records:
    t = r.get("question_type", "?")
    manifest["types"][t] = manifest["types"].get(t, 0) + 1
  print(json.dumps(manifest, indent=2, sort_keys=True))
  return 1 if all_errors else 0


if __name__ == "__main__":
  raise SystemExit(main())
