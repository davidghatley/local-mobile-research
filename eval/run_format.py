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

NEW (Round 0 repair): Per-stage score kinds. The legacy flat trace schema
(``score_kind``, ``stage_scores``, ``thresholds``, ``stage_candidates``,
``pruning_decisions``, ``per_stage_latency_ms`` at top level) is DEPRECATED.
New traces MUST use an ordered ``stages`` array where each entry carries its own
``score_kind``, ``threshold_policy``, and ``model_identity``. A legacy trace is
accepted ONLY via an explicit call to ``migrate_legacy_trace`` (which fails
closed if model identity cannot be established); ``validate_trace`` does NOT
perform silent migration.
"""

from __future__ import annotations

import json
import math

from substrate.evidence import find_unknown_citations
from substrate.generator import PROMPT_HASH, is_stub_generator
from substrate.types import (
    SCORE_KINDS,
    THRESHOLD_INTERPRETATIONS,
    CALIBRATION_METHODS,
    FITTED_CALIBRATION_METHODS,
    ThresholdPolicy,
    validate_score_value,
)

# New per-stage trace schema (required fields for WIRE traces)
TRACE_REQUIRED_FIELDS = (
    "question_id",
    "run_id",
    "architecture",
    "seed",
    "query",
    "stages",                    # ordered list of per-stage records (REPLACES flat fields)
    "adaptive_compute_decision",
    "evidence_packet",
    "evidence_token_count",
    "evidence_token_method",
    "retrieval_latency_ms",
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

# Legacy flat-field names (for migration reference; not required in new traces)
_LEGACY_FLAT_FIELDS = (
    "score_kind",
    "stage_scores",
    "stage_candidates",
    "pruning_decisions",
    "thresholds",
    "per_stage_latency_ms",
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


def _validate_stage_array(trace: dict, errors: list[str]) -> None:
    """Validate the new per-stage `stages` array."""
    stages = trace.get("stages")
    if not isinstance(stages, list):
        errors.append("stages: must be a non-empty list")
        return
    if not stages:
        errors.append("stages: must contain at least one stage")
        return

    seen_stages = set()
    for i, stage in enumerate(stages):
        if not isinstance(stage, dict):
            errors.append(f"stages[{i}]: must be an object")
            continue

        stage_name = stage.get("stage")
        if not isinstance(stage_name, str) or not stage_name:
            errors.append(f"stages[{i}].stage: must be a non-empty string")
        elif stage_name in seen_stages:
            errors.append(f"stages[{i}].stage: duplicate stage name {stage_name!r}")
        else:
            seen_stages.add(stage_name)

        # candidate_ids
        candidate_ids = stage.get("candidate_ids")
        if not isinstance(candidate_ids, list):
            errors.append(f"stages[{i}].candidate_ids: must be a list")
            candidate_ids = []
        elif not all(isinstance(c, str) for c in candidate_ids):
            errors.append(f"stages[{i}].candidate_ids: all entries must be strings")

        # scores
        scores = stage.get("scores")
        if not isinstance(scores, list):
            errors.append(f"stages[{i}].scores: must be a list")
            scores = []
        elif not all(isinstance(s, (int, float)) and math.isfinite(s) for s in scores):
            errors.append(f"stages[{i}].scores: all entries must be finite numbers")

        # pruning_decisions
        pruning_decisions = stage.get("pruning_decisions")
        if not isinstance(pruning_decisions, list):
            errors.append(f"stages[{i}].pruning_decisions: must be a list")
            pruning_decisions = []
        elif not all(isinstance(d, bool) for d in pruning_decisions):
            errors.append(f"stages[{i}].pruning_decisions: all entries must be booleans")

        # Array alignment invariant
        n_cand = len(candidate_ids)
        n_scores = len(scores)
        n_decisions = len(pruning_decisions)
        if not (n_cand == n_scores == n_decisions):
            errors.append(
                f"stages[{i}]: array length mismatch — "
                f"candidate_ids={n_cand}, scores={n_scores}, pruning_decisions={n_decisions}"
            )

        # score_kind (per-stage, required)
        score_kind = stage.get("score_kind")
        if score_kind not in SCORE_KINDS:
            errors.append(f"stages[{i}].score_kind: unknown or missing {score_kind!r}")
        else:
            # Score-domain consistency: validate each score against THIS stage's score_kind
            for s in scores:
                try:
                    validate_score_value(s, score_kind)
                except ValueError as exc:
                    errors.append(f"stages[{i}].scores: {exc}")

        # threshold_policy (per-stage, required)
        threshold_policy = stage.get("threshold_policy")
        if not isinstance(threshold_policy, dict):
            errors.append(f"stages[{i}].threshold_policy: must be an object")
        else:
            try:
                policy = ThresholdPolicy.from_dict(threshold_policy)
            except (ValueError, TypeError, AttributeError) as exc:
                errors.append(f"stages[{i}].threshold_policy: malformed policy ({exc})")
            else:
                # INVARIANT: policy.score_kind MUST equal stage.score_kind
                if policy.score_kind != score_kind:
                    errors.append(
                        f"stages[{i}].threshold_policy: policy score_kind {policy.score_kind!r} "
                        f"!= stage score_kind {score_kind!r}"
                    )
                errors.extend(
                    f"stages[{i}].threshold_policy: {e}" for e in policy.validate()
                )

        # latency_ms (required, non-negative)
        latency_ms = stage.get("latency_ms")
        if not _is_nonneg_number(latency_ms):
            errors.append(f"stages[{i}].latency_ms: must be a non-negative number, got {latency_ms!r}")

        # model_loading_latency_ms (required field, None = explicitly not measured)
        mll = stage.get("model_loading_latency_ms")
        if mll is not None and not _is_nonneg_number(mll):
            errors.append(f"stages[{i}].model_loading_latency_ms: must be >= 0 or null, got {mll!r}")

        # inference_latency_ms (required field, None = explicitly not measured)
        ill = stage.get("inference_latency_ms")
        if ill is not None and not _is_nonneg_number(ill):
            errors.append(f"stages[{i}].inference_latency_ms: must be >= 0 or null, got {ill!r}")

        # peak_rss_mb (required field, None = explicitly not measured)
        prss = stage.get("peak_rss_mb")
        if prss is not None and not _is_nonneg_number(prss):
            errors.append(f"stages[{i}].peak_rss_mb: must be >= 0 or null, got {prss!r}")

        # model_identity (REQUIRED in WIRE trace, non-empty string)
        model_identity = stage.get("model_identity")
        if not isinstance(model_identity, str) or not model_identity:
            errors.append(
                f"stages[{i}].model_identity: must be a non-empty string (wire trace requirement)"
            )


def validate_trace(
    trace: dict,
    *,
    allow_stub: bool = False,
    allow_estimate: bool = False,
    allow_unknown_citations: bool = False,
) -> list[str]:
    """Validate a trace against the NEW per-stage schema.

    Legacy flat traces are NOT accepted here. Callers MUST explicitly invoke
    ``migrate_legacy_trace`` first (which fails closed if model identity cannot
    be established). This function only validates the new schema.
    """
    errors = []

    # Check for legacy flat fields — reject explicitly to avoid silent confusion
    legacy_present = [f for f in _LEGACY_FLAT_FIELDS if f in trace]
    if legacy_present:
        errors.append(
            "legacy flat trace fields detected (score_kind, stage_scores, etc.); "
            "use migrate_legacy_trace() explicitly before validation"
        )
        # Continue validation to report all issues, but legacy traces will fail

    # Required fields (new schema)
    for f in TRACE_REQUIRED_FIELDS:
        if f not in trace:
            errors.append(f"missing trace field: {f}")
    if errors:
        return errors

    # Validate per-stage array
    _validate_stage_array(trace, errors)
    if errors:
        return errors

    # Top-level latencies: non-negative numbers or explicit None (not measured)
    for field_name in (
        "retrieval_latency_ms",
        "model_loading_latency_ms",
        "inference_latency_ms",
        "peak_rss_mb",
    ):
        value = trace[field_name]
        if value is not None and not _is_nonneg_number(value):
            errors.append(f"{field_name}: must be >= 0 or null (not measured), got {value!r}")

    storage = trace["storage_bytes"]
    if storage is not None and not (isinstance(storage, int) and storage >= 0):
        errors.append(f"storage_bytes: must be a non-negative int or null, got {storage!r}")

    # Generator pin: prompt hash fixed, stubs rejected unless infra opt-in
    if trace["generator_prompt_hash"] != PROMPT_HASH:
        errors.append("generator_prompt_hash does not match the fixed Round 0 prompt")
    if is_stub_generator(trace["generator_id"]) and not allow_stub:
        errors.append(f"stub generator {trace['generator_id']!r} disallowed (infra-only)")

    # Token budget honesty: empirical runs need exact tokenizer counts
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
    # inconsistent or malformed audit.
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


def migrate_legacy_trace(legacy_trace: dict, model_identity_map: dict[str, str]) -> dict:
    """Explicitly migrate a legacy flat trace to the new per-stage schema.

    This is a RECORDED TRANSFORM, not a silent fallback. Callers must invoke it
    deliberately and record the migration in their pipeline metadata.

    Args:
        legacy_trace: A trace dict with the old flat fields (score_kind,
            stage_scores, stage_candidates, pruning_decisions, thresholds,
            per_stage_latency_ms).
        model_identity_map: Mapping from stage name -> model identity string.
            EVERY stage in the legacy trace MUST have an entry. If a stage is
            missing, this function fails closed (raises ValueError) rather than
            assigning a placeholder. This enforces the "no fabricated provenance"
            ruling.

    Returns:
        A new trace dict with the `stages` array and all other required fields
        preserved. The legacy flat fields are NOT included in the output.

    Raises:
        ValueError: If the legacy trace is malformed, missing required flat
            fields, or if any stage lacks a model_identity in the provided map.
    """
    # Verify legacy flat fields exist
    missing_flat = [f for f in _LEGACY_FLAT_FIELDS if f not in legacy_trace]
    if missing_flat:
        raise ValueError(f"not a legacy trace: missing flat fields {missing_flat}")

    score_kind = legacy_trace["score_kind"]
    if score_kind not in SCORE_KINDS:
        raise ValueError(f"legacy trace has unknown score_kind: {score_kind!r}")

    stage_scores = legacy_trace["stage_scores"]
    stage_candidates = legacy_trace["stage_candidates"]
    pruning_decisions = legacy_trace["pruning_decisions"]
    thresholds = legacy_trace["thresholds"]
    per_stage_latency = legacy_trace.get("per_stage_latency_ms", {})

    if not isinstance(stage_scores, dict) or not isinstance(stage_candidates, dict):
        raise ValueError("legacy trace stage_scores/stage_candidates must be mappings")
    if not isinstance(pruning_decisions, dict):
        raise ValueError("legacy trace pruning_decisions must be a mapping")
    if not isinstance(thresholds, dict):
        raise ValueError("legacy trace thresholds must be a mapping")
    if not isinstance(per_stage_latency, dict):
        raise ValueError("legacy trace per_stage_latency_ms must be a mapping")

    # All stage names must be consistent across the flat mappings
    stage_names = set(stage_scores.keys())
    if set(stage_candidates.keys()) != stage_names:
        raise ValueError("stage_scores and stage_candidates have different stage names")
    if set(pruning_decisions.keys()) != stage_names:
        raise ValueError("stage_scores and pruning_decisions have different stage names")
    if set(thresholds.keys()) != stage_names:
        raise ValueError("stage_scores and thresholds have different stage names")

    # Build ordered stages list (sorted for determinism)
    stages = []
    for stage_name in sorted(stage_names):
        scores = stage_scores[stage_name]
        candidate_ids = stage_candidates[stage_name]
        decisions = pruning_decisions[stage_name]
        thr = thresholds[stage_name]
        latency_ms = per_stage_latency.get(stage_name)

        if not isinstance(scores, list) or not isinstance(candidate_ids, list) or not isinstance(decisions, list):
            raise ValueError(f"stage {stage_name!r}: scores/candidates/decisions must be lists")
        if len(scores) != len(candidate_ids) or len(scores) != len(decisions):
            raise ValueError(f"stage {stage_name!r}: array length mismatch")

        # Model identity: MUST be provided explicitly; no placeholder
        if stage_name not in model_identity_map:
            raise ValueError(
                f"stage {stage_name!r}: no model_identity provided in model_identity_map; "
                "legacy migration fails closed (no fabricated provenance)"
            )
        model_identity = model_identity_map[stage_name]
        if not isinstance(model_identity, str) or not model_identity:
            raise ValueError(f"stage {stage_name!r}: model_identity must be a non-empty string")

        # Parse threshold policy
        try:
            policy = ThresholdPolicy.from_dict(thr)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"stage {stage_name!r}: malformed threshold policy ({exc})")

        # Validate policy against global score_kind (legacy invariant)
        if policy.score_kind != score_kind:
            raise ValueError(
                f"stage {stage_name!r}: policy score_kind {policy.score_kind!r} "
                f"!= trace score_kind {score_kind!r}"
            )

        # Build new stage record
        stage_record = {
            "stage": stage_name,
            "candidate_ids": candidate_ids,
            "scores": scores,
            "score_kind": score_kind,
            "threshold_policy": policy.to_dict(),
            "pruning_decisions": decisions,
            "latency_ms": latency_ms if _is_nonneg_number(latency_ms) else 0.0,
            "model_loading_latency_ms": legacy_trace.get("model_loading_latency_ms"),
            "inference_latency_ms": legacy_trace.get("inference_latency_ms"),
            "peak_rss_mb": legacy_trace.get("peak_rss_mb"),
            "model_identity": model_identity,
        }
        stages.append(stage_record)

    # Construct new trace (copy all other fields, drop legacy flat fields)
    new_trace = {k: v for k, v in legacy_trace.items() if k not in _LEGACY_FLAT_FIELDS}
    new_trace["stages"] = stages

    # Ensure all required new fields are present (some may be missing from legacy)
    for f in TRACE_REQUIRED_FIELDS:
        if f not in new_trace:
            # These should have been in the legacy trace under different names or as top-level
            if f in ("model_loading_latency_ms", "inference_latency_ms", "peak_rss_mb"):
                # These were top-level in legacy; they're now also per-stage but top-level kept for totals
                pass  # already copied above
            else:
                raise ValueError(f"migrated trace missing required field: {f}")

    return new_trace