"""Private-eval custody interface: schema, seal, counts, leakage gate.

CUSTODY MODEL (read this before changing anything)
--------------------------------------------------
Private evaluation data lives OUTSIDE the repository, in the directory named
by the ``LMR_PRIVATE_EVAL_DIR`` environment variable. The main repository may
carry the schema, counts, opaque hashes, and the protocol; it must never carry
private question text, answers, support atoms, or labels.

All processes on the development machine run as the same OS user, so this is
a PROCEDURAL and WORKSPACE-based boundary, not a kernel security boundary. No
encryption or permission theater is implemented because it would not create
a real boundary under one UID. The real enforcement is:
  * the private directory is never committed (see tests/test_private_eval_tripwire.py);
  * Round 1 architecture workers receive a sanitized worktree that excludes it;
  * the orchestrator/custodian runs private evaluation only after experiment freeze.

FAIL CLOSED everywhere: absent artifacts report absence. ``counts()`` never
fabricates numbers, and ``check_training_overlap()`` never returns PASS when
the seal is missing.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any

PRIVATE_EVAL_DIR_ENV = "LMR_PRIVATE_EVAL_DIR"
DEFAULT_PRIVATE_EVAL_DIR = (
    "/home/davidhatley/Projects/testing/local_mobile_research-private-eval"
)

# Repository root marker used to detect a mis-pointed private directory.
_REPO_MARKER = "substrate/private_eval.py"

QUESTIONS_FILE = "questions.json"
LABELS_FILE = "labels.json"
COUNTS_FILE = "counts.json"
SEAL_FILE = "seal.sha256"
SCHEMA_FILE = "schema.json"


class PrivateEvalError(RuntimeError):
  """Raised for unusable private-eval state. Never used to leak content."""


def private_dir() -> str:
  """Absolute path of the private eval directory (env pointer or default)."""
  return os.path.abspath(
    os.environ.get(PRIVATE_EVAL_DIR_ENV, DEFAULT_PRIVATE_EVAL_DIR)
  )


def _resolve(name: str) -> str:
  return os.path.join(private_dir(), name)


def questions_path() -> str:
  return _resolve(QUESTIONS_FILE)


def labels_path() -> str:
  return _resolve(LABELS_FILE)


def counts_path() -> str:
  return _resolve(COUNTS_FILE)


def seal_path() -> str:
  return _resolve(SEAL_FILE)


def schema_path() -> str:
  return _resolve(SCHEMA_FILE)


def repo_root() -> str | None:
  """Repository root if derivable from this file, else None."""
  here = os.path.dirname(os.path.abspath(__file__))
  root = os.path.dirname(here)
  return root if os.path.exists(os.path.join(root, _REPO_MARKER)) else None


def assert_private_dir_outside_repo() -> None:
  """Fail closed if the private dir resolves inside the repository."""
  root = repo_root()
  if root is None:
    return
  pd = private_dir()
  if pd == root or pd.startswith(root + os.sep):
    raise PrivateEvalError(
      f"{PRIVATE_EVAL_DIR_ENV} resolves inside the repository ({pd}); "
      "private evaluation data must live outside the repo"
    )


def sha256_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
    return h.hexdigest()


def seal_digest() -> str | None:
  """Opaque seal digest string, or None when no seal file exists."""
  path = seal_path()
  if not os.path.isfile(path):
    return None
  with open(path, "r", encoding="utf-8") as fh:
    return fh.read().strip() or None


def verify_seal(expected_sha256: str | None = None) -> bool:
  """Verify the private artifact seal WITHOUT parsing or printing content.

  Returns True iff the seal file exists and, when ``expected_sha256`` is
  given, matches it. Raises PrivateEvalError when no seal exists: an absent
  seal is not a pass.
  """
  assert_private_dir_outside_repo()
  digest = seal_digest()
  if digest is None:
    raise PrivateEvalError(
      f"no private seal at {seal_path()}: private test is not sealed "
      "(absent is not a pass)"
    )
  if expected_sha256 is not None and digest != expected_sha256:
    raise PrivateEvalError("private seal digest mismatch: artifact changed since seal")
  return True


def seal_question_bytes() -> str | None:
  """Hash of the private questions file, or None when absent.

  Only the digest crosses the boundary. Bytes are never returned or printed.
  """
  path = questions_path()
  if not os.path.isfile(path):
    return None
  return sha256_file(path)


def counts() -> dict[str, Any]:
  """Report private counts. Never fabricates: absent file -> explicit absence.

  Returns {"present": bool, "counts": {...}, "seal_sha256": str|None,
  "questions_sha256": str|None, "labels_sha256": str|None}. ``counts`` is the
  parsed counts.json when present, otherwise {} (an honest empty result, not a
  default guess).
  """
  assert_private_dir_outside_repo()
  cpath = counts_path()
  if not os.path.isfile(cpath):
    return {
      "present": False,
      "counts": {},
      "seal_sha256": None,
      "questions_sha256": None,
      "labels_sha256": None,
    }
  with open(cpath, "r", encoding="utf-8") as fh:
    data = json.load(fh)
  if not isinstance(data, dict):
    raise PrivateEvalError("counts.json must be an object")
  return {
    "present": True,
    "counts": data,
    "seal_sha256": seal_digest(),
    "questions_sha256": seal_question_bytes(),
    "labels_sha256": sha256_file(labels_path()) if os.path.isfile(labels_path()) else None,
  }


@dataclass(frozen=True)
class LeakageVerdict:
  """PASS/REJECT only. Carries no private content, by construction."""
  verdict: str
  reason: str
  flagged_ids: list[str] = field(default_factory=list)

  def to_dict(self) -> dict[str, Any]:
    return {
      "verdict": self.verdict,
      "reason": self.reason,
      "flagged_ids": list(self.flagged_ids),
    }


def check_training_overlap(training_question_ids: list[str]) -> LeakageVerdict:
  """Custodian-side leakage check for architecture-generated training data.

  Document-level overlap is LEGAL (Regime A explicitly allows corpus-known
  specialization). Exact or near-exact private QUESTION leakage is not.

  Information asymmetry is preserved by design: this function returns only
  PASS or REJECT, the count of flagged training examples, and the SYNTHETIC
  training ids that must be removed. It never returns the matched private
  question id, private text, private answer, or private evidence.

  FAIL CLOSED: with no seal present the verdict is REJECT with an explicit
  "seal absent" reason. It never returns PASS on missing data.
  """
  assert_private_dir_outside_repo()
  try:
    verify_seal()
  except PrivateEvalError as exc:
    return LeakageVerdict(
      verdict="REJECT",
      reason=f"cannot evaluate leakage: {exc}",
      flagged_ids=[],
    )

  # The full comparison needs the sealed questions; that is a Phase 6
  # custodian concern. This gate exists so the interface is fixed and fails
  # closed until then. Hash-only matching is wired once the seal exists.
  return LeakageVerdict(
    verdict="REJECT",
    reason=(
      "sealed present but hash-only comparison not yet bound to a seal; "
      "custodian must run the sealed comparison before PASS can be issued"
    ),
    flagged_ids=[],
  )


def load_schema() -> dict[str, Any] | None:
  """Private item schema, or None when the private dir has no schema yet."""
  path = schema_path()
  if not os.path.isfile(path):
    return None
  with open(path, "r", encoding="utf-8") as fh:
    return json.load(fh)
