#!/usr/bin/env python3
"""Emit a draft scaffold for one group (human authors the Q/A text).

Usage:
  python3 -m data_tools.scaffold --corpus corpus/corpus.jsonl \\
      --split-map corpus/split_map.json --group mercury --n 0 --out /tmp/scaffold.json

Refuses heldout groups unless --allow-heldout + custodian env are set.
Prints node counts/ids only, never corpus text excerpts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .derive import (evidence_units_for_group, group_articles, load_jsonl_nodes,
                     load_split_map, make_scaffold, scaffold_id)
from .verify import CUSTODIAN_ENV_VAR


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--corpus", required=True)
  ap.add_argument("--split-map", required=True)
  ap.add_argument("--group", required=True)
  ap.add_argument("--n", type=int, default=0)
  ap.add_argument("--out", required=True)
  ap.add_argument("--allow-heldout", action="store_true", default=False)
  args = ap.parse_args(argv)
  nodes = load_jsonl_nodes(args.corpus)
  split_map = load_split_map(args.split_map)
  try:
    titles, split = group_articles(split_map, args.group)
  except ValueError:
    print("unknown/invalid group", file=sys.stderr)
    return 2
  if split == "heldout" and not (
      args.allow_heldout and os.environ.get(CUSTODIAN_ENV_VAR) == "benchmark"):
    print("refused: heldout scaffold needs custodian path", file=sys.stderr)
    return 2
  try:
    units = evidence_units_for_group(nodes, titles)
  except ValueError:
    print("scaffold article unresolvable against corpus", file=sys.stderr)
    return 2
  qid = scaffold_id(args.group, args.n, split)
  scaf = make_scaffold(qid, args.group, split, units)
  with open(args.out, "w", encoding="utf-8") as fh:
    json.dump(scaf, fh, ensure_ascii=False, indent=2, sort_keys=True)
    fh.write("\n")
  print(json.dumps({"question_id": qid, "group": args.group, "split": split,
                    "articles": len(titles),
                    "candidate_units": len(units)}, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
