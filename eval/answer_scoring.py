"""Deterministic answer-correctness scoring (preregistered policy).

Implements the deterministic parts of docs/scoring-protocol.md. This module
takes already-extracted records (predicted strings, gold strings passed in by
the caller). It NEVER reads private files, NEVER touches the network, and
uses only the standard library. All functions are pure and deterministic:
identical inputs produce identical outputs.

CUSTODY: private item content (questions.json / labels.json) must never be
passed through here in bulk or logged; the private harness extracts
``answer_text`` / ``accepted_variants`` / ``answerability`` / reading counts
and calls these functions per record.
"""

from __future__ import annotations

import re
import unicodedata

_ARTICLES = {"a", "an", "the"}
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_answer(text: str) -> str:
  """Deterministic answer normalization (preregistered, frozen).

  Steps, in order:
  1. Unicode-normalize with NFKC (compatibility decomposition + composition,
     so full-width / ligature / composed-vs-decomposed forms compare equal).
  2. ``casefold`` (Unicode case-insensitive comparison; stronger than
     ``lower``, e.g. German sharp-s folds).
  3. Replace every punctuation / symbol character (anything that is not a
     word character or whitespace) with a space.
  4. Collapse all whitespace runs to a single space and strip ends.
  5. Remove English articles ``a`` / ``an`` / ``the`` as whole tokens
     wherever they occur (this subsumes "strip a leading 'the'").
  6. Re-collapse whitespace after article removal and strip ends.

  Non-string input raises ``TypeError``; this fails closed rather than
  scoring garbage as a mismatch.
  """
  if not isinstance(text, str):
    raise TypeError(f"normalize_answer expects str, got {type(text).__name__}")
  s = unicodedata.normalize("NFKC", text)
  s = s.casefold()
  s = _PUNCT_RE.sub(" ", s)
  s = _WS_RE.sub(" ", s).strip()
  tokens = [t for t in s.split(" ") if t and t not in _ARTICLES]
  return " ".join(tokens)


def exact_match(prediction: str, gold: str) -> bool:
  """True iff normalized prediction equals normalized gold (both non-empty).

  Empty-after-normalization never matches (an empty prediction is an
  abstention, scored by :func:`abstention_outcome`, not here).
  """
  p = normalize_answer(prediction)
  g = normalize_answer(gold)
  if not p or not g:
    return False
  return p == g


def match_any_variant(prediction: str, answer_text: str, accepted_variants: list[str] | tuple[str, ...] | None = None) -> dict:
  """Match a prediction against gold + accepted variants.

  Returns ``{"match": bool, "matched_variant": str | None,
  "normalized_prediction": str}``. ``matched_variant`` is the first variant
  (gold first, then variants in order) whose normalization equals the
  prediction's; None on mismatch. Deterministic: variant order is caller
  order, no sets, no hashing.
  """
  variants: list[str] = [answer_text] + list(accepted_variants or [])
  norm_pred = normalize_answer(prediction)
  if not norm_pred:
    return {"match": False, "matched_variant": None, "normalized_prediction": norm_pred}
  for v in variants:
    if not isinstance(v, str):
      raise TypeError(f"variants must be str, got {type(v).__name__}")
    if norm_pred and norm_pred == normalize_answer(v) and normalize_answer(v):
      return {"match": True, "matched_variant": v, "normalized_prediction": norm_pred}
  return {"match": False, "matched_variant": None, "normalized_prediction": norm_pred}


def score_answerable_question(
  prediction: str,
  answer_text: str,
  accepted_variants: list[str] | tuple[str, ...] | None = None,
  abstained: bool = False,
) -> dict:
  """Score one answerable question's generated answer (deterministic part).

  - Abstained predictions score ``{"outcome": "false_abstention",
    "correct": False}`` (failure: the question was answerable).
  - Otherwise correctness is ``match_any_variant``; outcome is
    ``"correct_answer"`` / ``"wrong_answer"``.
  - The record echoes ``normalized_prediction`` for audit.
  """
  if bool(abstained):
    return {
      "outcome": "false_abstention",
      "correct": False,
      "match": False,
      "matched_variant": None,
      "normalized_prediction": normalize_answer(prediction),
    }
  m = match_any_variant(prediction, answer_text, accepted_variants)
  return {
    "outcome": "correct_answer" if m["match"] else "wrong_answer",
    "correct": bool(m["match"]),
    "match": bool(m["match"]),
    "matched_variant": m["matched_variant"],
    "normalized_prediction": m["normalized_prediction"],
  }


def abstention_outcome(*, answerable: bool | None, abstained: bool) -> str | None:
  """Classify one sufficiency decision (mirrors eval.metrics semantics).

  Returns ``"correct_abstention"`` (unanswerable + abstained: success),
  ``"unsupported_generation"`` (unanswerable + generated: failure),
  ``"answered_answerable"`` (answerable + generated: success — the answer
  text itself is scored separately by :func:`score_answerable_question`),
  or ``"false_abstention"`` (answerable + abstained: failure).
  Returns None when ``answerable`` is None (unlabeled: never invent truth).
  """
  if answerable is None:
    return None
  if not isinstance(answerable, bool):
    raise ValueError(f"answerable must be True, False, or None; got {answerable!r}")
  abstained = bool(abstained)
  if abstained:
    return "correct_abstention" if not answerable else "false_abstention"
  return "answered_answerable" if answerable else "unsupported_generation"


def score_unanswerable_response(*, abstained: bool, produced_answer_text: bool) -> dict:
  """Score one unanswerable question's response.

  Primary success is correct abstention / insufficient-evidence decision.
  A fabricated answer (generated text on an unanswerable question) is
  failure. ``produced_answer_text`` should be True when the system emitted
  any substantive answer string (after normalization, non-empty).

  Returns ``{"outcome": str, "correct": bool}`` where outcome is one of
  ``"correct_abstention"`` / ``"unsupported_generation"`` /
  ``"empty_generation"`` (claimed to answer but emitted nothing: failure,
  distinct from a clean abstention so harness telemetry stays honest).
  """
  abstained = bool(abstained)
  produced = bool(produced_answer_text)
  if abstained and not produced:
    return {"outcome": "correct_abstention", "correct": True}
  if not abstained and produced:
    return {"outcome": "unsupported_generation", "correct": False}
  if not abstained and not produced:
    return {"outcome": "empty_generation", "correct": False}
  # abstained=True yet answer text present: contradictory trace — failure.
  return {"outcome": "unsupported_generation", "correct": False}


def score_ambiguous_response(
  *,
  claimed_ambiguity: bool,
  n_gold_readings: int,
  n_grounded_readings: int,
  min_grounded_to_succeed: int = 2,
) -> dict:
  """Score one ambiguous question's response without touching reading text.

  Inputs are counts / flags extracted by the private harness (which holds
  the privately recorded readings); this module never sees reading content.
  Success = recognizing ambiguity AND grounding the valid readings in
  evidence (each grounded reading must cite at least one retrieved evidence
  node; the harness counts them and passes ``n_grounded_readings``).

  - ``claimed_ambiguity``: the response explicitly states the question is
    ambiguous / has multiple valid readings.
  - ``n_gold_readings``: privately recorded reading count (>= 2 for a real
    ambiguous item; validated here).
  - ``n_grounded_readings``: response readings backed by cited evidence.
  - ``min_grounded_to_succeed``: required grounded readings (default 2;
    capped at ``n_gold_readings`` so over-demanding configs fail closed
    honestly instead of silently lowering the bar).

  A single-answer-only response (``claimed_ambiguity`` False) is failure
  (``"single_answer_only"``). Claimed ambiguity with too few grounded
  readings is failure (``"ungrounded_ambiguity"``). Success outcome is
  ``"grounded_ambiguity"``.
  """
  if not isinstance(claimed_ambiguity, bool):
    raise ValueError(f"claimed_ambiguity must be bool, got {claimed_ambiguity!r}")
  for name, v in (("n_gold_readings", n_gold_readings), ("n_grounded_readings", n_grounded_readings)):
    if not isinstance(v, int) or isinstance(v, bool) or v < 0:
      raise ValueError(f"{name} must be a non-negative int, got {v!r}")
  if n_gold_readings < 2:
    raise ValueError(f"ambiguous scoring needs >= 2 gold readings, got {n_gold_readings}")
  if not isinstance(min_grounded_to_succeed, int) or min_grounded_to_succeed < 2:
    raise ValueError("min_grounded_to_succeed must be an int >= 2")
  required = min(min_grounded_to_succeed, n_gold_readings)
  if not claimed_ambiguity:
    return {"outcome": "single_answer_only", "correct": False, "required_grounded": required}
  if n_grounded_readings >= required:
    return {"outcome": "grounded_ambiguity", "correct": True, "required_grounded": required}
  return {"outcome": "ungrounded_ambiguity", "correct": False, "required_grounded": required}
