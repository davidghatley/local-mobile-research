# Per-Stage Score Kind / Threshold Policy Semantics

## Overview

Round 0 repair replaces the legacy flat trace schema (one global `score_kind` with
`stage_scores`, `thresholds`, `stage_candidates`, `pruning_decisions` at the top
level) with an **ordered `stages` array** where each stage carries its own
`score_kind`, `threshold_policy`, and `model_identity`.

This document specifies the per-stage schema, the cross-field invariants, and the
exact semantic rules for each `score_kind` / `threshold interpretation` combination.

---

## Per-Stage Wire Trace Schema

Each entry in the `stages` array (ordered, non-empty, unique stage names) MUST
contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stage` | string | yes | Stage identifier (e.g., "bm25", "ettin", "kalm", "calibrator") |
| `candidate_ids` | string[] | yes | Canonical passage node IDs in score order |
| `scores` | number[] | yes | Raw scores as emitted by the model (NEVER coerced or rescaled) |
| `score_kind` | string | yes | One of `SCORE_KINDS` — declares the domain of `scores` |
| `threshold_policy` | object | yes | `ThresholdPolicy` dict (see below) |
| `pruning_decisions` | boolean[] | yes | `kept` decision per candidate (aligned with `scores`) |
| `latency_ms` | number | yes | Wall-clock latency for this stage (≥ 0) |
| `model_loading_latency_ms` | number \| null | yes | Model load time for this stage (null = explicitly not measured) |
| `inference_latency_ms` | number \| null | yes | Inference time for this stage (null = explicitly not measured) |
| `peak_rss_mb` | number \| null | yes | Peak RSS for this stage (null = explicitly not measured) |
| `model_identity` | string | yes | **Non-empty string** identifying the model (WIRE trace only; no placeholder) |

**Invariant (array alignment):**
```
len(candidate_ids) == len(scores) == len(pruning_decisions)
```
for every stage. Violation is a hard validation error.

---

## ThresholdPolicy Per Stage

Each stage's `threshold_policy` is a `ThresholdPolicy` with these fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `threshold` | number \| null | null | Threshold value (if used) |
| `interpretation` | string | "unspecified" | One of `THRESHOLD_INTERPRETATIONS` |
| `top_k` | integer \| null | null | Keep top-K regardless of threshold |
| `min_breadth` | integer | 0 | Minimum candidates to preserve |
| `calibration_method` | string | "unspecified" | One of `CALIBRATION_METHODS` |
| `score_kind` | string | "calibrated_probability" | **MUST equal the stage's `score_kind`** |
| `calibration_partition` | string | "" | Provenance hash for fitted calibration claims |

**Critical Invariant:** `threshold_policy.score_kind == stage.score_kind` for every stage.
This is enforced at validation time (fail closed).

---

## SCORE_KINDS Semantics

| `score_kind` | Domain | Valid for ECE/Brier? | Valid for probability threshold? | Notes |
|--------------|--------|----------------------|----------------------------------|-------|
| `calibrated_probability` | [0, 1] finite | **YES** (certified) | **YES** (with `calibration_method` ≠ `none_ranking_only`, `unspecified`) | Requires fitted calibration + provenance OR `model_probability` (see below) |
| `model_probability` | [0, 1] finite | **YES** (evaluable) | **YES** (dev-selected threshold, no fitted calibration required) | Model natively emits P(yes); sigmoid alone is NOT this |
| `logit` | (-∞, +∞) finite | **NO** | **NO** (probability threshold on logit = FAIL) | Raw absolute / percentile thresholds OK |
| `similarity` | (-∞, +∞) finite | **NO** | **NO** | Typically cosine similarity; ranking only |
| `distance` | [0, +∞) finite | **NO** | **NO** | Lower = better; ranking only |
| `rank` | {1, 2, …} integer | **NO** | **NO** | Ordinal ranks only |

**Key semantic rules (enforced by `ThresholdPolicy.validate`):**

1. **`interpretation == "calibrated_probability"`** requires:
   - `score_kind` ∈ {`calibrated_probability`, `model_probability`}
   - `calibration_method` ∉ {`none_ranking_only`, `unspecified`}
   - If `calibration_method` ∈ `FITTED_CALIBRATION_METHODS` → `calibration_partition` non-empty

2. **`interpretation == "raw_score_absolute"` or `"raw_score_percentile"`** — legal with ANY `score_kind`, no calibration claim needed.

3. **`interpretation == "unspecified"`** — always FAIL (fail closed).

4. **`calibration_method == "model_probability"`** — accepted for `calibrated_probability` scores that are natively probabilistic (e.g., P(yes) from a classifier head). These are ECE/Brier-evaluable and dev-thresholdable WITHOUT fitted calibration. They are NOT certified calibrated.

5. **`calibration_method == "none_ranking_only"`** — scores used for ranking (top-K / percentile) only. MUST NOT be thresholded as probabilities.

---

## Semantic Decision Table

| Stage `score_kind` | Policy `interpretation` | Policy `calibration_method` | Policy `score_kind` | VALID? | Reason |
|--------------------|-------------------------|----------------------------|---------------------|--------|--------|
| `calibrated_probability` | `calibrated_probability` | `temperature_scaling` | `calibrated_probability` | ✅ | Fitted + provenance required |
| `calibrated_probability` | `calibrated_probability` | `platt` | `calibrated_probability` | ✅ | Fitted + provenance required |
| `calibrated_probability` | `calibrated_probability` | `isotonic` | `calibrated_probability` | ✅ | Fitted + provenance required |
| `calibrated_probability` | `calibrated_probability` | `model_probability` | `calibrated_probability` | ✅ | Native prob, ECE-evaluable, dev-thresholdable |
| `calibrated_probability` | `calibrated_probability` | `none_ranking_only` | `calibrated_probability` | ❌ | Probability threshold on ranking-only = FAIL |
| `calibrated_probability` | `calibrated_probability` | `unspecified` | `calibrated_probability` | ❌ | Unspecified = FAIL |
| `model_probability` | `calibrated_probability` | `model_probability` | `model_probability` | ✅ | Native prob, ECE-evaluable |
| `model_probability` | `raw_score_absolute` | `none_ranking_only` | `model_probability` | ✅ | Raw threshold on native prob OK |
| `logit` | `raw_score_absolute` | `none_ranking_only` | `logit` | ✅ | Raw absolute threshold on logits |
| `logit` | `raw_score_percentile` | `none_ranking_only` | `logit` | ✅ | Raw percentile threshold on logits |
| `logit` | `calibrated_probability` | `none_ranking_only` | `logit` | ❌ | Probability threshold on logit = FAIL |
| `logit` | `calibrated_probability` | `platt` | `logit` | ❌ | Policy score_kind != stage score_kind |
| `similarity` | `raw_score_absolute` | `none_ranking_only` | `similarity` | ✅ | Raw threshold on similarity |
| `similarity` | `raw_score_percentile` | `none_ranking_only` | `similarity` | ✅ | Percentile threshold on similarity |
| `similarity` | `calibrated_probability` | *any* | `similarity` | ❌ | Probability interpretation on similarity = FAIL |
| `distance` | `raw_score_absolute` | `none_ranking_only` | `distance` | ✅ | Raw threshold on distance |
| `distance` | `calibrated_probability` | *any* | `distance` | ❌ | Probability interpretation on distance = FAIL |
| `rank` | `raw_score_absolute` | `none_ranking_only` | `rank` | ✅ | Rank threshold (e.g., top-K) |
| `rank` | `calibrated_probability` | *any* | `rank` | ❌ | Probability interpretation on ranks = FAIL |
| *any* | *any* | *any* | *mismatched* | ❌ | **Policy score_kind MUST equal stage score_kind** |

---

## Calibration Methods

| Method | Category | Certifies Calibration? | Requires Provenance? | Notes |
|--------|----------|------------------------|----------------------|-------|
| `none_ranking_only` | Ranking only | ❌ | ❌ | Scores used for ordering only |
| `model_probability` | Native | ❌ (evaluable) | ❌ | Model emits P(yes); ECE/Brier OK; dev threshold OK |
| `temperature_scaling` | Fitted | ✅ | ✅ | Single temperature parameter |
| `platt` | Fitted | ✅ | ✅ | Logistic regression on logits |
| `isotonic` | Fitted | ✅ | ✅ | Non-parametric monotonic |
| `beta` | Fitted | ✅ | ✅ | Beta calibration |
| `other_fitted` | Fitted | ✅ | ✅ | Other fitted method (documented) |
| `unspecified` | — | ❌ | ❌ | FAIL closed |

**Fitted calibration claim (`calibration_method` ∈ `FITTED_CALIBRATION_METHODS`) is ONLY valid when:**
1. `score_kind == "calibrated_probability"`
2. `calibration_partition` is a non-empty string (provenance hash/id of the calibration partition)
3. `interpretation == "calibrated_probability"`

---

## Legacy Migration

Legacy flat traces (with top-level `score_kind`, `stage_scores`, `thresholds`, etc.)
are **NOT** accepted by `validate_trace`. Callers MUST explicitly invoke:

```python
from eval.run_format import migrate_legacy_trace

new_trace = migrate_legacy_trace(legacy_trace, model_identity_map={
    "bm25": "bm25-index-v1",
    "ettin": "ettin-encoder-v3",
    "kalm": "kalm-reranker-v2",
    "calibrator": "platt-calibrator-v1",
})
```

**Migration rules:**
- Every stage in the legacy trace MUST have an entry in `model_identity_map`.
- Missing `model_identity` → **FAIL CLOSED** (ValueError). No placeholder `"legacy-unknown"`.
- The legacy trace's single `score_kind` is copied to every stage (preserving the
  original global assumption, but now explicit per-stage).
- Array alignment (`len(candidate_ids) == len(scores) == len(pruning_decisions)`)
  is verified during migration.
- Threshold policies are validated against the global `score_kind` (legacy
  invariant).
- The returned trace uses the new `stages` array; legacy flat fields are dropped.

---

## Validation Entry Points

- `validate_trace(trace, ...)` — validates **new schema only** (rejects legacy flat fields).
- `migrate_legacy_trace(legacy_trace, model_identity_map)` — explicit, tested, recorded transform.
- `write_traces_jsonl(path, traces, ...)` — calls `validate_trace` on each trace.
- `read_traces_jsonl(path)` — reads JSONL, no validation.

---

## Test Matrix (Implemented in `tests/test_stage_scores_semantics.py`)

| Scenario | Expected |
|----------|----------|
| Mixed pipeline: similarity → logit → model_probability → calibrated_probability, all correctly declared | PASS |
| Any stage: `stage.score_kind != policy.score_kind` | FAIL |
| Probability threshold (`interpretation=calibrated_probability`) on `logit` stage | FAIL |
| Ranking policy (`raw_score_percentile`, `none_ranking_only`) on `logit` with no probability claim | PASS |
| `model_probability` with dev-selected threshold, ECE/Brier evaluable | PASS |
| `calibrated_probability` claimed with `calibration_method=none_ranking_only` | FAIL |
| Fitted calibration (`platt`, `isotonic`, etc.) with empty `calibration_partition` | FAIL |
| Scores outside [0, 1] declared as `calibrated_probability` | FAIL |
| Array misalignment (`len(candidate_ids) != len(scores)`) | FAIL |
| Missing `model_identity` in a stage | FAIL |
| Legacy migration: explicit, all model identities provided | PASS |
| Legacy migration: unidentifiable stage (missing from `model_identity_map`) | FAIL CLOSED |

---

## Rationale

The per-stage schema enables **honest hybrid pipelines** (e.g., BM25 similarity →
Ettin logits → KaLM model probabilities → fitted calibrator) where each stage
truthfully declares its score domain and threshold semantics. The global
`score_kind` forced a single domain across all stages, which either required
silent coercion (losing raw scores) or mislabeling (invalidating downstream
metrics like ECE/Brier).

The `model_identity` requirement on the wire trace (but NOT on internal
`StageRecord`) ensures provenance is recorded where it matters for
reproducibility, without fabricating identities for legacy traces that cannot
supply them. The explicit `migrate_legacy_trace` function makes the transform
auditable and testable.