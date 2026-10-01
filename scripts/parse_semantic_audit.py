#!/usr/bin/env python3
"""Parse the two semantic audit reports into a repair ledger (infra tool)."""
import re
import sys

TOKENS = ("repair-minimality", "repair-alternatives", "relabel-multihop",
          "reject-replace", "approve")


def parse(path):
  items = {}
  cur = None
  for line in open(path, encoding="utf-8").read().splitlines():
    m = re.match(r"###\s*\d+\.\s*(qa-[a-z0-9-]+)", line)
    if m:
      cur = m.group(1)
      items.setdefault(cur, [])
    if cur:
      # Formats seen in practice: "**Decision:** <token>",
      # "**Decision:** ... **<token>.**", and a heading "— **<token>**".
      d = re.search(r"\*\*Decision:\*\*.*?\*\*(" + "|".join(TOKENS) + r")",
                    line)
      if not d:
        d = re.search(r"\*\*(" + "|".join(TOKENS) + r")", line)
      if d:
        items[cur].append(d.group(1))
  return items


def main():
  needs = []
  for path in ("docs/qa-semantic-audit-pass1.md", "docs/qa-semantic-audit-pass2.md"):
    items = parse(path)
    tag = path.split("pass")[-1].split(".")[0]
    print(f"--- {path}: {len(items)} drafts parsed")
    for qid, decs in sorted(items.items()):
      if "approve" not in decs:
        print(f"  NEEDS-REPAIR [{tag}] {qid}: {sorted(set(decs))}")
        needs.append(qid)
  print(f"\nTOTAL NEEDS REPAIR: {len(needs)}")
  print(sorted(needs))
  return 0


if __name__ == "__main__":
  sys.exit(main())