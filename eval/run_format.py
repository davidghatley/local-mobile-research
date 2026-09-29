"""Machine-readable run-trace format (JSONL per question + summary).

Presence validation is structural; ``validate_trace`` additionally enforces
SEMANTICS fail-closed: non-negative latencies, score-domain consistency
(calibrated scores must be finite [0, 1]; raw kinds finite), unified
threshold-policy validation (one implementation), prompt-hash pin,
stub-generator rejection, exact-token budgets for empirical runs, and
citation-audit consistency (unknown emitted citations permitted as recorded
model failures, never rejected). Telemetry that was not measured must be explicit
``None`` (not measured), never silently absent.

``validate_trace`` returns error strings; ``write_traces_jsonl`` raises on any
error. Infra-only tests opt in via ``allow_stub`` / ``allow_estimate`` flags
(never set for benchmark runs). ``allow_unknown_citations`` is retained as a
deprecated no-op: unknown emitted citations are permitted observations since
v0.3 (finding A), classified by the citation audit, never rejected.
"""

from __future__ import annotations

import json
import math

from substrate.evidence import find_unknown_citations
from substrate.generator import PROMPT_HASH, is_stub_generator
from substrate.types import SCORE_KINDS, ThresholdPolicy

TRACE_REQUIRED_FIELDS = (
  "question_id",
  "run_id",
  "architecture",
  "seed",
  "query",
  "score_kind",
  "stage_candidates",
  "stage_scores",
  "pruning_decisions",
  "thresholds",
  "adaptive_compute_decision",
  "evidence_packet",
  "evidence_token_count",
  "evidence_token_method",
  "retrieval_latency_ms",
  "per_stage_latency_ms",
  "model_loading_latency_ms",
  "inference_latency_ms",
  "peak_rss_mb",
  "storage_bytes",
  "generator_prompt_hash",
  "generator_id",
  "generator_response",
  "citations",
  "available_citations",
  "grader_result",
)

SUMMARY_REQUIRED_FIELDS = (
  "run_id",
  "corpus_hash",
  "generator_id",
  "prompt_hash",
  "seed",
  "n_questions",
)


def _is_nonneg_number(value: object) -> bool:
  return isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def validate_trace(
  trace: dict,
  *,
  allow_stub: bool = False,
  allow_estimate: bool = False,
  allow_unknown_citations: bool = False,
) -> list[str]:
  errors = []
  for f in TRACE_REQUIRED_FIELDS:
    if f not in trace:
      errors.append(f"missing trace field: {f}")
  if errors:
    return errors

  score_kind = trace["score_kind"]
  if score_kind not in SCORE_KINDS:
    errors.append(f"unknown score_kind {score_kind!r}")

  # Score-domain consistency across every reported stage.
  for stage, scores in trace["stage_scores"].items():
    if not isinstance(scores, list):
      errors.append(f"stage_scores[{stage}]: not a list")
      continue
    for s in scores:
      if not isinstance(s, (int, float)) or not math.isfinite(s):
        errors.append(f"stage_scores[{stage}]: non-finite score {s!r}")
      elif score_kind == "calibrated_probability" and not (0.0 <= s <= 1.0):
        errors.append(
          f"stage_scores[{stage}]: {s!r} outside [0, 1] for calibrated_probability "
          "(label raw scores with their score_kind)"
        )

  # Latencies: non-negative numbers or explicit None (not measured).
  for field_name in (
    "retrieval_latency_ms",
    "model_loading_latency_ms",
    "inference_latency_ms",
    "peak_rss_mb",
  ):
    value = trace[field_name]
    if value is not None and not _is_nonneg_number(value):
      errors.append(f"{field_name}: must be >= 0 or null (not measured), got {value!r}")
  per_stage = trace["per_stage_latency_ms"]
  if not isinstance(per_stage, dict):
    errors.append("per_stage_latency_ms: not a mapping")
  else:
    for stage, value in per_stage.items():
      if value is not None and not _is_nonneg_number(value):
        errors.append(f"per_stage_latency_ms[{stage}]: must be >= 0 or null, got {value!r}")
  storage = trace["storage_bytes"]
  if storage is not None and not (isinstance(storage, int) and storage >= 0):
    errors.append(f"storage_bytes: must be a non-negative int or null, got {storage!r}")

  # Threshold-domain consistency: ONE implementation — the shared
  # ThresholdPolicy validator. Bare floats migrate fail-closed; ranking-only
  # stages must declare an explicit policy (None is missing, not neutral).
  # The trace score_kind must match each policy's score_kind.
  thresholds = trace["thresholds"]
  if not isinstance(thresholds, dict):
    errors.append("thresholds: not a mapping")
  else:
    for stage, thr in thresholds.items():
      if thr is None:
        errors.append(
          f"thresholds[{stage}]: missing policy (declare an explicit "
          "ranking policy incl. top_k; None is not neutral)"
        )
        continue
      try:
        policy = ThresholdPolicy.from_dict(thr)
      except (ValueError, TypeError, AttributeError) as exc:
        errors.append(f"thresholds[{stage}]: malformed policy ({exc})")
        continue
      if policy.score_kind != score_kind:
        errors.append(
          f"thresholds[{stage}]: policy score_kind {policy.score_kind!r} "
          f"!= trace score_kind {score_kind!r}"
        )
      errors.extend(f"thresholds[{stage}]: {e}" for e in policy.validate())

  # Generator pin: prompt hash fixed, stubs rejected unless infra opt-in.
  if trace["generator_prompt_hash"] != PROMPT_HASH:
    errors.append("generator_prompt_hash does not match the fixed Round 0 prompt")
  if is_stub_generator(trace["generator_id"]) and not allow_stub:
    errors.append(f"stub generator {trace['generator_id']!r} disallowed (infra-only)")

  # Token budget honesty: empirical runs need exact tokenizer counts.
  method = trace["evidence_token_method"]
  if not isinstance(method, str) or not method:
    errors.append("evidence_token_method: must be a non-empty method label")
  elif method == "whitespace-estimate" and not allow_estimate:
    errors.append("whitespace-estimate token budget rejected for empirical runs")
  count = trace["evidence_token_count"]
  if not (isinstance(count, int) and count >= 0):
    errors.append(f"evidence_token_count: must be a non-negative int, got {count!r}")

  # Citations: unknown/hallucinated emitted citations are a VALID model
  # failure observation, NOT a trace rejection. What IS rejected is an
  # inconsistent or malformed audit. An optional explicit `citation_audit`
  # {available, emitted, unknown} must match the top-level fields and satisfy
  # unknown == emitted - available; without it, unknowns are permitted as
  # recorded. Failed answers are preserved raw (never filtered here).
  emitted = trace["citations"]
  available = trace["available_citations"]
  if not isinstance(emitted, list) or not isinstance(available, list):
    errors.append("citations/available_citations: must be lists")
  else:
    audit = trace.get("citation_audit")
    if audit is not None:
      if not isinstance(audit, dict) or not all(
        isinstance(audit.get(k), list) for k in ("available", "emitted", "unknown")
      ):
        errors.append("citation_audit: must map available/emitted/unknown to lists")
      else:
        if set(audit["available"]) != set(available) or set(audit["emitted"]) != set(
          emitted
        ):
          errors.append("citation_audit inconsistent with citations/available_citations")
        expected_unknown = find_unknown_citations(audit["emitted"], audit["available"])
        if set(audit["unknown"]) != set(expected_unknown):
          errors.append(
            f"citation_audit misclassifies unknowns: declared {audit['unknown'][:5]} "
            f"vs recomputed {expected_unknown[:5]}"
          )

  return errors


def validate_summary(summary: dict) -> list[str]:
  errors = []
  for f in SUMMARY_REQUIRED_FIELDS:
    if f not in summary:
      errors.append(f"missing summary field: {f}")
  return errors


def write_traces_jsonl(
  path: str,
  traces: list[dict],
  *,
  allow_stub: bool = False,
  allow_estimate: bool = False,
  allow_unknown_citations: bool = False,
) -> None:
  with open(path, "w", encoding="utf-8") as fh:
    for trace in traces:
      errors = validate_trace(
        trace,
        allow_stub=allow_stub,
        allow_estimate=allow_estimate,
        allow_unknown_citations=allow_unknown_citations,
      )
      if errors:
        raise ValueError(f"invalid trace for {trace.get('question_id')}: {errors}")
      fh.write(json.dumps(trace, sort_keys=True, ensure_ascii=False) + "\n")


def read_traces_jsonl(path: str) -> list[dict]:
  out = []
  with open(path, "r", encoding="utf-8") as fh:
    for line in fh:
      line = line.strip()
      if line:
        out.append(json.loads(line))
  return out
