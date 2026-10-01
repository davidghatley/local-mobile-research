"""Evidence-packet assembly: canonical serialization, token counting, citations.

Canonical serialization ``serialize_evidence`` is the single deterministic
function mapping spans to generator input text; every architecture uses it so
token counts and generator behavior are comparable.

Packing policy (deterministic ranked-prefix):
- The budget is enforced on the FULL serialization ``serialize_evidence(kept +
  [span])`` at every step, never on summed per-span counts: separators and
  non-additive tokenization are counted as the model sees them.
- The cap is STRICT and never exceeded, including by the first span: packing
  stops before the first overflow and marks ``truncated=True``. A first span
  that alone overflows yields an EMPTY packet with ``truncated=True``.
- Source strings are never cut without exact offsets; there is no partial-span
  truncation. An empty/short packet is a valid abstention outcome.
- ``truncated=True`` records a PACKING outcome (budget stop), distinct from
  upstream retrieval survival (recorded in stage traces / survival metrics).
  ``truncated=False`` with zero spans means upstream supplied nothing.

Token units:
- EXACT model-tokenizer counts (``exact_evidence_tokens``, ``prompt_tokens``)
  govern empirical budgets. Empirical packet construction MUST pass
  ``exact=True`` with the pinned tokenizer callable; estimates are rejected.
- Whitespace estimates (``token_estimate``) are INFRA-ONLY (pipeline shape
  tests without the 1 GB artifact) and must never be reported as measurements.

Budget note: HARD_EVIDENCE_TOKEN_CAP = 1000 is the PILOT PREREGISTERED
protocol choice, not a universal requirement. Future tournaments may
re-preregister a different cap; the packing policy above is cap-agnostic.
"""

from __future__ import annotations

from collections.abc import Callable

import re

from .types import (
  EvidenceDecision, EvidencePacket, EvidenceSpan, GeneratedAnswer, Question,
  RetrievalOutcome)

# Budget targets from the master prompt. The unit that governs empirical runs
# is EXACT model tokens; the numbers below are therefore bounds on
# ``exact_evidence_tokens``, not on the whitespace estimate.
TARGET_EVIDENCE_TOKENS_MIN = 300
TARGET_EVIDENCE_TOKENS_MAX = 800
HARD_EVIDENCE_TOKEN_CAP = 1000

# Type of the pinned-tokenizer callable: exact model tokens for a string.
TokenizerFn = Callable[[str], int]


def estimate_tokens(text: str) -> int:
  """Whitespace token estimate. INFRA-ONLY; never report as measured."""
  return len(text.split())


def serialize_evidence(spans: list[EvidenceSpan] | tuple[EvidenceSpan, ...]) -> str:
  """Canonical evidence serialization shared by all architectures.

  Deterministic ``[node_id] text`` lines in span order. The generator prompt
  renderer and the exact tokenizer both consume this exact string.
  """
  return "\n".join(f"[{s.node_id}] {s.text}" for s in spans)


def _validate_cap(cap: int) -> None:
  # bool is a subclass of int: reject explicitly (True == 1 would silently pass).
  if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
    raise ValueError(f"cap must be a positive integer, got {cap!r}")


def _validate_token_count(value: object) -> int:
  # Tokenizer returns must be nonnegative integers: reject bool, float (incl.
  # nan), and negatives. A lying tokenizer fails closed here, not downstream.
  if isinstance(value, bool) or not isinstance(value, int) or value < 0:
    raise ValueError(f"tokenizer must return a nonnegative integer, got {value!r}")
  return value


def build_packet(
  question_id: str,
  spans: list[EvidenceSpan],
  hop_count: int = 0,
  cap: int = HARD_EVIDENCE_TOKEN_CAP,
  tokenizer: TokenizerFn | None = None,
  tokenizer_id: str | None = None,
  exact: bool = False,
) -> EvidencePacket:
  """Assemble an evidence packet under a token cap (ranked-prefix packing).

  Spans are considered in given rank order. At each step the FULL
  serialization ``serialize_evidence(kept + [span])`` is counted; the first
  span that would overflow the cap stops packing (``truncated=True``). A
  first span that alone overflows yields an empty packet with
  ``truncated=True`` (valid abstention outcome, not a retrieval claim).

  Args:
    cap: strict positive-integer token cap (pilot preregistered: 1000).
    exact: when True (REQUIRED for empirical runs), ``tokenizer`` must be
      given and budgets are enforced on exact model tokens. Raises
      ValueError otherwise. When False, the whitespace estimate is used and
      the packet is explicitly marked ``token_count_method:
      "whitespace-estimate"`` (infra-only).
  """
  if exact and tokenizer is None:
    raise ValueError(
      "exact=True requires the pinned tokenizer callable; "
      "whitespace estimates are rejected for empirical runs"
    )
  if tokenizer is not None and not tokenizer_id:
    raise ValueError("a tokenizer callable requires its tokenizer_id label")
  _validate_cap(cap)

  def count(text: str) -> int:
    if tokenizer is not None:
      return _validate_token_count(tokenizer(text))
    return estimate_tokens(text)

  method = f"tokenizer:{tokenizer_id}" if tokenizer is not None else "whitespace-estimate"
  citations: list[str] = []
  kept: list[EvidenceSpan] = []
  total = count(serialize_evidence(kept))
  truncated = False
  for span in spans:
    candidate_total = count(serialize_evidence(kept + [span]))
    if candidate_total > cap:
      truncated = True
      break
    kept.append(span)
    total = candidate_total
    if span.node_id not in citations:
      citations.append(span.node_id)
  exact_total = total if tokenizer is not None else None
  return EvidencePacket(
    question_id=question_id,
    spans=tuple(kept),
    citations=tuple(citations),
    token_estimate=total if tokenizer is None else estimate_tokens(serialize_evidence(kept)),
    hop_count=hop_count,
    truncated=truncated,
    token_count_method=method,
    exact_evidence_tokens=exact_total,
  )


def packet_within_budget(packet: EvidencePacket) -> bool:
  """Budget check on the GOVERNING unit: exact tokens when measured."""
  total = packet.exact_evidence_tokens
  if total is None:
    total = packet.token_estimate
  return total <= HARD_EVIDENCE_TOKEN_CAP


def packet_in_target_band(packet: EvidencePacket) -> bool:
  total = packet.exact_evidence_tokens
  if total is None:
    total = packet.token_estimate
  return TARGET_EVIDENCE_TOKENS_MIN <= total <= TARGET_EVIDENCE_TOKENS_MAX


def decide_default(packet: EvidencePacket) -> EvidenceDecision:
  """Safe-floor sufficiency gate: interface minimum, NOT a tuned model.

  - Zero spans with ``truncated=False`` (upstream supplied nothing) ->
    insufficient/abstain, reason "zero-spans".
  - Zero spans with ``truncated=True`` (first span alone overflowed the
    cap: a PACKING failure) -> insufficient/abstain, reason
    "over-budget-empty". This DISTINCT code keeps a packing failure from
    ever being misread as a retrieval decision.
  - Any nonempty packet -> sufficient/generate, reason "nonempty-packet".

  No score is computed (score None, kind "unspecified", policy None).
  Architectures MUST supply their own sufficiency_policy for real
  sufficiency judgments; this floor only guarantees fail-closed plumbing.
  """

  if len(packet.spans) == 0:
    if packet.truncated:
      return EvidenceDecision(
        decision="insufficient",
        generation_action="abstain",
        sufficiency_score=None,
        sufficiency_score_kind="unspecified",
        sufficiency_policy=None,
        reason="over-budget-empty",
      )
    return EvidenceDecision(
      decision="insufficient",
      generation_action="abstain",
      sufficiency_score=None,
      sufficiency_score_kind="unspecified",
      sufficiency_policy=None,
      reason="zero-spans",
    )
  return EvidenceDecision(
    decision="sufficient",
    generation_action="generate",
    sufficiency_score=None,
    sufficiency_score_kind="unspecified",
    sufficiency_policy=None,
    reason="nonempty-packet",
  )


def run_question(
  retriever, generator, question: Question, decide=decide_default
) -> tuple[RetrievalOutcome, EvidenceDecision, GeneratedAnswer | None]:
  """Shared retrieval-to-generation gate: the ONLY path to the generator.

  Calls ``retriever.retrieve(question)``, decides sufficiency via ``decide``
  (default: the safe floor), and returns
  ``(outcome, decision, response)`` where ``response`` is the
  ``GeneratedAnswer`` — or None on abstain. When
  ``decision.generation_action == "abstain"`` the generator is NEVER
  touched (not even instantiated lazily: ``generator.generate`` is not
  called). Callers MUST record ``decision`` and whether the generator was
  invoked in the trace (see docs/abstention-and-telemetry-notes.md).
  """
  outcome = retriever.retrieve(question)
  decision = decide(outcome.packet)
  if decision.generation_action == "abstain":
    return (outcome, decision, None)
  return (outcome, decision, generator.generate(question, outcome.packet))


def find_unknown_citations(
  emitted: list[str] | tuple[str, ...], available: list[str] | tuple[str, ...]
) -> list[str]:
  """Emitted citation ids with no backing evidence node (order-preserving)."""
  avail = set(available)
  return [c for c in emitted if c not in avail]


_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")


def parse_citations(text: str) -> list[str]:
  """Parse emitted bracketed citation candidates from generator output text.

  Returns deduplicated contents of ``[...]`` spans in order of first
  appearance, stripped of surrounding whitespace; empty contents are skipped.
  Brackets are NOT necessarily sources: callers must pass the result through
  ``find_unknown_citations`` against the packet's available citations. A
  bracketed string with no backing evidence is UNKNOWN, never auto-credited.
  """
  seen: list[str] = []
  for match in _BRACKET_RE.finditer(text):
    candidate = match.group(1).strip()
    if candidate and candidate not in seen:
      seen.append(candidate)
  return seen
