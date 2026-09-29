"""Pinned public-reference import (dev/reference ONLY, never training).

Converts entries from a PINNED import file of public bounty questions
(AndroidLM / boar-app eval sets) to substrate public_reference questions:
  split=dev (forced), meta.category=public_reference,
  meta.source_benchmark + meta.source_revision (full 40-hex commit SHA) +
  meta.original_question_id + meta.source_file_sha256 (64-hex SHA-256 of the
  exact import-file bytes) — all required and format-validated, not merely
  present. meta.source_articles optional (absent => ground truth UNKNOWN).

Refusals (fail closed): any entry requesting train/heldout; any entry
missing benchmark provenance; malformed revision or file-hash pins; import
bytes whose SHA-256 mismatches the pin (see check_import_pin); any attempt
to attach controlled evidence spans or labels to a public entry. Output
contains NO answers — public benchmark answers are never imported.

The import file itself is NOT created here (a later step pins exact bytes
from the audited repos at their pinned HEADs). This helper only converts
and verifies pins.
"""

from __future__ import annotations

import hashlib
import re

REQUIRED_IMPORT_FIELDS = ("original_question_id", "text")

_REVISION_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def check_import_pin(raw_bytes: bytes, expected_sha256: str) -> None:
  """Verify exact import-file bytes against the pinned SHA-256. Raises."""
  if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
    raise ValueError("source_file_sha256 must be a 64-char lowercase hex digest")
  actual = hashlib.sha256(raw_bytes).hexdigest()
  if actual != expected_sha256:
    raise ValueError("import file bytes mismatch pinned source_file_sha256")


def convert_public_entry(entry: dict, *, source_benchmark: str,
                         source_revision: str,
                         source_file_sha256: str) -> dict:
  qid = entry.get("question_id") or entry.get("original_question_id") or "?"
  if entry.get("split", "dev") != "dev":
    raise ValueError(f"{qid}: public_reference forced to dev")
  for f in REQUIRED_IMPORT_FIELDS:
    if not isinstance(entry.get(f), str) or not entry[f].strip():
      raise ValueError(f"{qid}: import entry missing {f}")
  if not isinstance(source_benchmark, str) or not source_benchmark.strip():
    raise ValueError(f"{qid}: source_benchmark required")
  if not isinstance(source_revision, str) or not _REVISION_RE.fullmatch(source_revision):
    raise ValueError(f"{qid}: source_revision must be a full 40-hex commit SHA")
  if not isinstance(source_file_sha256, str) or not _SHA256_RE.fullmatch(
      source_file_sha256):
    raise ValueError(f"{qid}: source_file_sha256 must be a 64-hex digest")
  if "answer" in entry or "labels" in entry or "sufficient_sets" in entry:
    raise ValueError(f"{qid}: public import must not carry answers/labels")
  meta: dict = {
    "category": "public_reference",
    "source_benchmark": source_benchmark,
    "source_revision": source_revision,
    "source_file_sha256": source_file_sha256,
    "original_question_id": entry["original_question_id"],
  }
  srcs = entry.get("source_articles", [])
  if srcs:
    if (not isinstance(srcs, list) or not all(
        isinstance(s, str) and s.strip() for s in srcs)):
      raise ValueError(f"{qid}: source_articles malformed")
    meta["source_articles"] = list(srcs)
  return {
    "question_id": entry.get("question_id", entry["original_question_id"]),
    "text": entry["text"],
    "split": "dev",
    "meta": meta,
  }


def convert_public_file(entries: list[dict], *, source_benchmark: str,
                        source_revision: str, source_file_sha256: str,
                        source_bytes: bytes | None = None) -> list[dict]:
  if source_bytes is not None:
    check_import_pin(source_bytes, source_file_sha256)
  out = []
  seen: set[str] = set()
  for e in entries:
    q = convert_public_entry(e, source_benchmark=source_benchmark,
                             source_revision=source_revision,
                             source_file_sha256=source_file_sha256)
    if q["question_id"] in seen:
      raise ValueError("duplicate public question id (count only)")
    seen.add(q["question_id"])
    out.append(q)
  return out
