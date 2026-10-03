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

LEAKAGE-GATE ALGORITHM (PREREGISTERED BEFORE any Round 1 training data exists)
-----------------------------------------------------------------------------
Frozen at Round 0 closure. The layered rule below and its thresholds are
preregistered NOW, before any architecture team generates training questions,
so that nobody can tune thresholds after seeing a REJECT. Changing any
threshold after Round 1 training data exists requires a recorded protocol
amendment, not a silent edit.

Normalization: ``casefold`` + collapse every run of non-alphanumeric
characters to a single space + strip. Deliberately simple and documented so
both sides can reproduce it by hand.

A synthetic record is FLAGGED when ANY layer fires against ANY private
question:

  Layer 1 -- normalized exact match. The normalized synthetic text equals a
      normalized private question. Catches verbatim copies modulo
      case/punctuation/whitespace.
  Layer 2 -- high token-set (Jaccard) similarity on normalized tokens.
      ``OVERLAP_JACCARD_THRESHOLD = 0.80``. Jaccard is order-insensitive, so
      this layer catches reworded duplicates that reuse most of the private
      question's vocabulary. 0.80 means at least four-fifths of the combined
      vocabulary is shared: deliberately conservative, because a false
      positive costs the team only a rewrite while a false negative leaks a
      held-out question into training.
  Layer 3 -- character-level similarity as an independent, order-sensitive
      signal: ``difflib.SequenceMatcher`` ratio on normalized strings,
      ``OVERLAP_CHAR_RATIO_THRESHOLD = 0.80``. Catches lightly edited copies
      (small insertions/deletions/duplications) that token sets underweight.

      The threshold was set from a MEASURED separation, not a guess. Normalized
      ``max(jaccard, char_ratio)`` on a fixed probe set:

          exact duplicate ................................. 1.000   flagged
          case/punctuation/whitespace variant ........... 1.000   flagged
          "Which river flows through the city of Cairo?"
              vs "Which river flows through Cairo?" ...... 0.838   flagged
          unrelated ("How many legs does a spider have?") . 0.222   clean
          unrelated ("When was the Berlin Wall built?") .. 0.361   clean

      0.85 missed the 0.838 insertion case. 0.80 catches it while sitting well
      clear of the unrelated cluster (0.361) and above the 0.625 paraphrase
      score, which is missed at any threshold in this family.

  KNOWN LIMITATION, stated rather than papered over: token and character
  similarity do not measure meaning. A genuine semantic paraphrase scores LOW
      ("Cairo does the Nile flow through?" = 0.508; "The Nile flows through
      which city?" = 0.625) and is NOT caught. Layer 3 is deliberately set
      above that band so it cannot fire on unrelated vocabulary. The gate's
      scope is therefore NEAR-EXACT leakage -- a copied or lightly edited
      question, which is the realistic failure mode, since no team would
      knowingly paraphrase a sealed question into training data. Catching
      deliberate semantic paraphrase would require an embedding model, which
      would make the threshold un-auditable and un-reproducible. If a future
      threat model includes paraphrase leakage, this gate must be replaced, not
      re-tuned, and the replacement must be preregistered.

Deterministic and reproducible: stdlib only, no network, fixed iteration
order (input order x stored private order), no randomness, no wall-clock.

INFORMATION BOUNDARY: the verdict carries exactly three fields -- a verdict,
a generic non-revealing reason, and the SYNTHETIC ids to remove. It never
carries a private id, text, answer, evidence, or source. See LeakageVerdict.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
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


# --- Leakage-gate preregistered constants (see module docstring) ---
# Token-set Jaccard flag threshold. Deliberately conservative: a false
# positive costs the team only a rewrite, while a false negative leaks a
# held-out question into training. Order-insensitive, so reworded duplicates
# that reuse the private question's vocabulary are caught.
OVERLAP_JACCARD_THRESHOLD = 0.80
# Character-level SequenceMatcher flag threshold on normalized strings.
# Order-sensitive second signal for lightly edited copies (small insertions,
# deletions, duplications) that token sets underweight. Set higher than the
# Jaccard threshold because raw character ratio is the noisier signal; 0.85
# still requires a near-identical character sequence.
OVERLAP_CHAR_RATIO_THRESHOLD = 0.80

# Private question-text keys, in lookup order. The sealed private items and
# the public questions both carry "text"; the alternates tolerate minor
# schema drift without ever changing what crosses the boundary (verdicts
# only -- text never leaves this module).
_PRIVATE_TEXT_KEYS = ("text", "question", "question_text", "prompt")


def _normalize_question_text(s: str) -> str:
  """casefold + collapse non-alphanumeric runs to one space + strip."""
  return re.sub(r"[^a-z0-9]+", " ", s.casefold()).strip()


def _jaccard(a: set[str], b: set[str]) -> float:
  if not a and not b:
    return 1.0
  if not a or not b:
    return 0.0
  return len(a & b) / len(a | b)


def _record_overlaps(
  norm: str,
  tokens: set[str],
  priv_norm: str,
  priv_tokens: set[str],
) -> bool:
  """True when ANY preregistered layer fires for one synthetic/private pair."""
  if norm == priv_norm:
    return True
  if _jaccard(tokens, priv_tokens) >= OVERLAP_JACCARD_THRESHOLD:
    return True
  if difflib.SequenceMatcher(None, norm, priv_norm).ratio() >= OVERLAP_CHAR_RATIO_THRESHOLD:
    return True
  return False


def _validate_training_records(records: Any) -> tuple[list[dict[str, str]] | None, str | None]:
  """Validate record input. Returns (valid, None) or (None, error_reason)."""
  if not isinstance(records, list) or not records:
    return None, "malformed training input"
  valid: list[dict[str, str]] = []
  for rec in records:
    if not isinstance(rec, dict):
      return None, "malformed training input"
    sid = rec.get("synthetic_id")
    text = rec.get("text")
    if not isinstance(sid, str) or not sid.strip():
      return None, "malformed training input"
    if not isinstance(text, str) or not text.strip():
      return None, "malformed training input"
    valid.append({"synthetic_id": sid, "text": text})
  return valid, None


def _extract_private_text(item: Any) -> str | None:
  if isinstance(item, str):
    return item if item.strip() else None
  if isinstance(item, dict):
    for key in _PRIVATE_TEXT_KEYS:
      val = item.get(key)
      if isinstance(val, str) and val.strip():
        return val
  return None


def _load_private_question_texts() -> list[tuple[str, set[str]]]:
  """Load sealed private question texts as (normalized, token-set) pairs.

  Custodian-side only: normalized text never leaves this module except
  through similarity comparisons. Raises PrivateEvalError when the questions
  are absent, unparsable, structurally wrong, or yield no usable text --
  every one of those is a fail-closed REJECT at the caller.
  """
  path = questions_path()
  try:
    with open(path, "r", encoding="utf-8") as fh:
      data = json.load(fh)
  except (OSError, ValueError) as exc:
    raise PrivateEvalError("private questions unreadable") from exc
  if isinstance(data, dict):
    # Tolerate a wrapped mapping with an items/questions list.
    for key in ("items", "questions"):
      if isinstance(data.get(key), list):
        data = data[key]
        break
  if not isinstance(data, list) or not data:
    raise PrivateEvalError("private questions malformed")
  out: list[tuple[str, set[str]]] = []
  for item in data:
    text = _extract_private_text(item)
    if text is None:
      continue
    norm = _normalize_question_text(text)
    if not norm:
      continue
    out.append((norm, set(norm.split())))
  if not out:
    raise PrivateEvalError("private questions malformed")
  return out


def check_training_overlap(records: list[Any]) -> LeakageVerdict:
  """Custodian-side leakage check for architecture-generated training data.

  ``records`` is a list of ``{"synthetic_id": str, "text": str}`` dicts.
  A legacy list of bare id strings is accepted for backward compatibility
  and ALWAYS yields REJECT: bare ids carry no question text, so no text
  comparison is possible and clearance cannot be issued (fail closed).

  Document-level overlap is LEGAL (Regime A explicitly allows corpus-known
  specialization). Exact or near-exact private QUESTION leakage is not.

  Information asymmetry is preserved by design: this function returns only
  PASS or REJECT, a generic non-revealing reason, and the SYNTHETIC training
  ids that must be removed. It never returns the matched private question
  id, private text, private answer, or private evidence.

  FAIL CLOSED: REJECT (never PASS) when the private dir resolves inside the
  repo, the seal is absent/invalid, the private questions are
  unreadable/malformed, the training input is malformed or empty, or the
  comparison could not be executed. Every PASS return below has executed the
  full text comparison over all records; there is no PASS path that skips it.
  """
  try:
    assert_private_dir_outside_repo()
  except PrivateEvalError as exc:
    return LeakageVerdict(
      verdict="REJECT",
      reason=f"cannot evaluate leakage: {exc}",
      flagged_ids=[],
    )
  try:
    verify_seal()
  except PrivateEvalError as exc:
    return LeakageVerdict(
      verdict="REJECT",
      reason=f"cannot evaluate leakage: {exc}",
      flagged_ids=[],
    )

  # Legacy bare-id calls carry no text to compare: fail closed, never PASS.
  if isinstance(records, list) and records and all(isinstance(r, str) for r in records):
    return LeakageVerdict(
      verdict="REJECT",
      reason=(
        "cannot evaluate leakage: training ids carry no question text; "
        "resubmit as records with synthetic_id and text"
      ),
      flagged_ids=[],
    )

  valid, error = _validate_training_records(records)
  if error is not None or valid is None:
    return LeakageVerdict(
      verdict="REJECT",
      reason=f"cannot evaluate leakage: {error}",
      flagged_ids=[],
    )

  try:
    private_texts = _load_private_question_texts()
  except PrivateEvalError:
    # Generic reason on purpose: the detail could otherwise name private
    # file layout. The custodian sees the exception; the team sees only this.
    return LeakageVerdict(
      verdict="REJECT",
      reason="cannot evaluate leakage: private questions unreadable or malformed",
      flagged_ids=[],
    )

  flagged: list[str] = []
  for rec in valid:
    norm = _normalize_question_text(rec["text"])
    tokens = set(norm.split())
    for priv_norm, priv_tokens in private_texts:
      if _record_overlaps(norm, tokens, priv_norm, priv_tokens):
        flagged.append(rec["synthetic_id"])
        break

  if flagged:
    return LeakageVerdict(
      verdict="REJECT",
      reason=(
        f"{len(flagged)} record(s) flagged by question-overlap rule"
      ),
      flagged_ids=flagged,
    )
  return LeakageVerdict(
    verdict="PASS",
    reason="no question-level overlap detected",
    flagged_ids=[],
  )


def check_training_file(path: str) -> LeakageVerdict:
  """Leakage check over a training file: a JSON list or a JSONL file.

  Each element/line must be a ``{"synthetic_id": str, "text": str}``
  record. Malformed files (missing file, invalid JSON, a top-level JSON
  object instead of a list, an unparsable JSONL line, an empty file)
  yield REJECT, never PASS.
  """
  try:
    with open(path, "r", encoding="utf-8") as fh:
      raw = fh.read()
  except OSError:
    return LeakageVerdict(
      verdict="REJECT",
      reason="cannot evaluate leakage: training file unreadable or missing",
      flagged_ids=[],
    )
  if not raw.strip():
    return LeakageVerdict(
      verdict="REJECT",
      reason="cannot evaluate leakage: malformed training input",
      flagged_ids=[],
    )
  try:
    top = json.loads(raw)
  except ValueError:
    top = None
  records: Any = None
  if isinstance(top, list):
    records = top
  elif top is None:
    # Not whole-file JSON: try JSONL, one record per non-blank line.
    records = []
    try:
      for line in raw.splitlines():
        if not line.strip():
          continue
        obj = json.loads(line)
        records.append(obj)
    except ValueError:
      return LeakageVerdict(
        verdict="REJECT",
        reason="cannot evaluate leakage: malformed training input",
        flagged_ids=[],
      )
  else:
    return LeakageVerdict(
      verdict="REJECT",
      reason="cannot evaluate leakage: malformed training input",
      flagged_ids=[],
    )
  return check_training_overlap(records)


def load_schema() -> dict[str, Any] | None:
  """Private item schema, or None when the private dir has no schema yet."""
  path = schema_path()
  if not os.path.isfile(path):
    return None
  with open(path, "r", encoding="utf-8") as fh:
    return json.load(fh)
