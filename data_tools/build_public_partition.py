#!/usr/bin/env python3
"""Emit the worker-visible public question partition: corpus/questions.json.

This file is the ONLY question set Round 1 architecture workers may read. It
carries question_id, text, split, and provenance. It must NOT carry:

  * evidence atoms or sufficient sets   (those are the retrieval ground truth)
  * hard negatives                      (they hand the system the distractors)
  * answer text                         (they hand over the answer)
  * private_test entries                (private data lives outside the repo)
  * retired `heldout` entries           (the vocabulary is retired)
  * rejected/quarantined items          (see staging/rejected/)

Regenerate with:

    python3 -m data_tools.build_public_partition --staging staging \\
        --out corpus/questions.json

The verifier checks the resulting file against this contract, so a drift that
leaks an answer is a load-bearing failure, not a style nit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Any

# Fields copied from a staging draft into the public partition.
ALLOWED_FIELDS = ("question_id", "text", "split", "question_type")
# Provenance fields that describe WHO did what, never WHAT the answer is.
#
# ``rationale`` is deliberately EXCLUDED. Auditor rationales are written prose
# that routinely names the answer ("single atom states the 209 acre size"), and
# this file is the worker-visible partition: a rationale that hands over the
# answer is an answer leak even though no field is called "answer". Measured on
# the current set, 70 of 76 verbatim answer mentions came from rationales.
# Worker-visible provenance is who/which-model/decision; the reasoning stays in
# the staging drafts and the ledgers.
ALLOWED_PROVENANCE = (
  "author", "author_model", "verifier", "verifier_model", "decision",
  "reclassification", "audit_decision", "independent_review",
)
# Never permitted anywhere in the emitted file.
FORBIDDEN_KEYS = (
  "evidence", "sufficient_sets", "hard_negatives", "labels",
  "answer_text", "absent_reason", "answerability", "readings",
)
RETIRED_SPLIT = "heldout"
PRIVATE_SPLIT = "private_test"


def _project(draft: dict[str, Any]) -> dict[str, Any]:
  out: dict[str, Any] = {}
  for f in ALLOWED_FIELDS:
    if f in draft:
      out[f] = draft[f]
  meta = draft.get("meta")
  if isinstance(meta, dict):
    # group / evidence_groups / source_articles are the answer's LOCATION.
    # Publishing them in the worker-visible partition would hand every
    # retriever a 1-3 article candidate set inside a 297-article corpus, which
    # destroys the measurement the whole tournament exists to make. They stay
    # in the staging drafts and the ledgers. paired_regime is dropped for the
    # same reason: it echoes the source articles.
    #
    # original_id and exposure_note are safe and load-bearing: they record that
    # this item was exposed in git history and is dev-visible, which is the
    # whole point of the reclassification.
    keep = ("original_id", "exposure_note")
    out["meta"] = {k: meta[k] for k in keep if k in meta}
  prov = draft.get("provenance")
  if isinstance(prov, dict):
    out["provenance"] = {k: prov[k] for k in ALLOWED_PROVENANCE if k in prov}
  return out


def _assert_clean(entry: dict[str, Any], qid: str,
                  draft: dict[str, Any] | None = None) -> None:
  blob = json.dumps(entry, sort_keys=True)
  for bad in FORBIDDEN_KEYS:
    if f'"{bad}"' in blob:
      raise SystemExit(f"{qid}: forbidden field {bad!r} in the public partition")
  if entry.get("split") in (PRIVATE_SPLIT, RETIRED_SPLIT):
    raise SystemExit(f"{qid}: split {entry.get('split')!r} is not publishable")
  if "qa-private-" in blob:
    raise SystemExit(f"{qid}: private question id in the public partition")

  # Prose leak check: a multi-word answer appearing verbatim anywhere in the
  # emitted entry is an answer leak, whatever field hides it. Short answers are
  # exempt because group and source-article names legitimately coincide with a
  # one- or two-word answer.
  if draft is not None:
    ans = str((draft.get("labels") or {}).get("answer_text") or "").strip()
    if len(ans) > 8 and ans.lower() in blob.lower():
      raise SystemExit(
        f"{qid}: answer text {ans[:40]!r} appears verbatim in the public "
        f"partition (a prose leak, not a field leak)"
      )
  # A retired-split mention in PROVENANCE (the reclassification record says
  # "from_split: heldout") is history and is deliberately preserved. A
  # retired split used as this item's own partition is the defect, and is
  # rejected above.


def main(argv: list[str] | None = None, *, quiet: bool = False) -> int:
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--staging", default="staging")
  ap.add_argument("--out", default="corpus/questions.json")
  ap.add_argument("--require-approved", action="store_true", default=True)
  args = ap.parse_args(argv)

  drafts = []
  for name in sorted(os.listdir(args.staging)):
    if not name.endswith(".json"):
      continue
    path = os.path.join(args.staging, name)
    if not os.path.isfile(path):
      continue
    with open(path, "r", encoding="utf-8") as fh:
      rec = json.load(fh)
    if args.require_approved:
      prov = rec.get("provenance") or {}
      if prov.get("decision") != "approve":
        print(f"skip {rec.get('question_id')}: decision={prov.get('decision')!r}",
              file=sys.stderr)
        continue
    drafts.append(rec)

  drafts.sort(key=lambda d: d["question_id"])
  out = []
  seen: set[str] = set()
  for d in drafts:
    qid = d["question_id"]
    if qid in seen:
      raise SystemExit(f"duplicate question_id: {qid}")
    seen.add(qid)
    entry = _project(d)
    _assert_clean(entry, qid, d)
    out.append(entry)

  payload = json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
  tmp = args.out + ".tmp"
  with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(payload)
  os.replace(tmp, args.out)

  splits: dict[str, int] = {}
  for e in out:
    splits[e.get("split", "?")] = splits.get(e.get("split", "?"), 0) + 1
  digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
  if not quiet:
    print(f"wrote {args.out}: {len(out)} items, splits={dict(sorted(splits.items()))}")
    print(f"sha256={digest}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
