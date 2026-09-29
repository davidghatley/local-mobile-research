# Round 0 Substrate Implementation Review v0.3

**Reviewer**: `opencode/nemotron-3-ultra-free` (explicit, verified zero-cost catalog entry)
**Date**: 2026-09-28
**Verdict**: **REPAIR REQUIRED**

---

## Executive Summary

The v0.3 substrate passes all **147 infrastructure tests** and closes all five P0 freeze-bypass gaps identified in v0.2:

1. ✅ Questions content hash (`questions_sha256`) — detects text changes
2. ✅ Generator config raw hash (`generator_config_sha256`) — generic byte-pin covers all fields; semantic compare for acted-on fields
3. ✅ Group-map split method — path + content hash + structure + article resolution + QA consistency
4. ✅ Trace validation — delegates to single `ThresholdPolicy.validate()`; bare floats fail-closed; score_kind mismatch rejected
5. ✅ Runtime binary/library hashes — parsed from `runtime_binaries`, verified at declared paths (incl. absolute `external-*` roles), manifest `ArtifactPin` inventory must cover all declarations

**New concern (design decision, not code defect)**: `validate_qa_group_consistency` **skips** questions without `meta.group`/`source_articles` and unknown groups. For a controlled dataset requiring article-generalization, QA source group provenance should be **mandatory**, not optional. An article assigned to one split in the map does not constrain questions lacking metadata — they can declare any split. No "public reference exception" exists in code.

---

## Detailed Verification of Prior Freeze Bypasses (All Closed)

### 1. Questions Content Hash — CLOSED

**Location**: `manifest.py:330-337`, `RunManifest.questions_sha256`

**Probe**: Change question text, preserve `question_id`/`split` → freeze fails

```
[REVIEWER-v03] questions_sha256 mismatch: manifest does not match questions.json bytes
```

### 2. Generator Config Raw Hash — CLOSED

**Location**: `manifest.py:405-412`, `RunManifest.generator_config_sha256`

**Probe**: 
- Change `license` (not in `GENERATOR_SEMANTIC_FIELDS`) → caught by raw hash
- Change `quantization` (in semantic fields) → caught by both

```
[REVIEWER-v03] generator_config_sha256 mismatch: manifest does not match config bytes
[REVIEWER-v03] generator manifest/disk mismatch on quantization
```

### 3. Group-Map Split Method — CLOSED

**Location**: `manifest.py:365-392`, `splits.py:validate_group_map`, `validate_qa_group_consistency`

**Verified**:
- Empty groups rejected
- Duplicate articles across groups rejected (supervised disjointness)
- Article resolution vs corpus titles enforced
- Split map byte hash (`split_map_sha256`) verified
- QA consistency checked for questions WITH metadata

```
[REVIEWER-v03] split_map_sha256 mismatch: manifest does not match map bytes
[REVIEWER-v03] qa group: q1: declared split train != source group split dev
```

### 4. Trace Validation vs Policy — CLOSED

**Location**: `run_format.py:124-149` → `ThresholdPolicy.validate()`

**Verified**: Trace validation rejects what `ThresholdPolicy.validate()` rejects:

| Policy | `ThresholdPolicy.validate()` | `validate_trace()` |
|--------|------------------------------|---------------------|
| `calibrated_probability` + `none_ranking_only` | ✅ Rejects | ✅ Rejects |
| `interpretation="unknown"` | ✅ Rejects | ✅ Rejects |
| `score_kind="logit"` + `interpretation="calibrated_probability"` | ✅ Rejects | ✅ Rejects |
| `score_kind="calibrated_probability"` + `raw_score_absolute` threshold | ✅ Rejects | ✅ Rejects |
| `model_probability` + `calibrated_probability` | ✅ Accepts | ✅ Accepts |
| Bare float `0.7` | ✅ Rejects (unspecified) | ✅ Rejects |

### 5. Runtime Binary/Library Hashes — CLOSED

**Location**: `manifest.py:241-275` (`_runtime_declarations`), `444-459` (verification), `ArtifactPin` inventory

**Verified**:
- Parses `runtime_binaries.libs` (via `soname_target`) and `llama-server`
- Absolute paths get `external-runtime-*` roles
- Bytes verified at declared paths
- Manifest `inventory` must cover every declaration

```
[REVIEWER-v03] Runtime inventory hashes match: True
[REVIEWER-v03] After tampering with library: False (sha256 mismatch)
[REVIEWER-v03] Inventory sha256 mismatch: False (unpinned + mismatch)
```

---

## New Concern: QA Group Consistency Optional by Design

### The Gap

**Location**: `splits.py:233-264` `validate_qa_group_consistency`

```python
# Only questions with meta.group or meta.source_articles are checked:
if isinstance(meta.get("group"), str) and isinstance(groups.get(meta["group"]), dict):
    # ... check group split
sources = meta.get("source_articles")
if isinstance(sources, list) and sources:
    # ... check source article splits
# Questions WITHOUT metadata: NO CHECK, NO GAP
```

**Behavior confirmed**:
- Questions without `meta.group`/`source_articles` → **skipped** (no gap)
- Questions with `meta.group="unknown_group"` → **skipped** (no gap)
- Questions with `meta.source_articles` spanning multiple splits → **error**
- Questions with `meta.source_articles` in one split, declared different → **error**

**Implication**: For a controlled dataset where article-generalization claims require QA source group provenance, the metadata is **optional**. An article assigned to `train` in the split map can be referenced by a question declared `dev`/`heldout` with no metadata — no validation error.

**Task requirement**: "claimed article-generalization needs QA source group provenance mandatory for this controlled dataset"

**No "public reference exception" exists** in code — all questions with metadata are checked equally.

### Reproduction

```python
# Article "Mercury (planet)" assigned to train group
# Question about it, declared dev, NO metadata → PASSES (skipped)
questions = [{"question_id": "q1", "text": "What is Mercury?", "split": "dev"}]
# validate_qa_group_consistency returns []

# Question WITH source_articles [Mercury (planet)], declared dev → ERROR
questions = [{"question_id": "q1", "text": "What is Mercury?", "split": "dev", 
              "meta": {"source_articles": ["Mercury (planet)"]}}]
# Returns: ["q1: declared split dev != source article split train"]
```

---

## Other Verified Behaviors

### Trace Hallucinated Citations / Audit Consistency

**Location**: `run_format.py:167-194`

- Hallucinated citations (`citations` contains ids not in `available_citations`) → **permitted** (recorded model failure)
- Optional `citation_audit` {available, emitted, unknown} → if present, must satisfy `unknown == emitted - available` and match top-level fields
- Inconsistent/malformed audit → **rejected**

```
[REVIEWER-v03] Hallucinated citation, no audit: []
[REVIEWER-v03] Hallucinated citation, consistent audit: []
[REVIEWER-v03] Hallucinated citation, inconsistent audit: ["citation_audit misclassifies unknowns..."]
[REVIEWER-v03] Hallucinated citation, audit available mismatch: ["citation_audit inconsistent..."]
```

### Binary Completion vs Fractional Coverage

**Location**: `metrics.py:56-87` `sufficient_set_completion`

- `completion`: binary 1.0 (any sufficient set fully covered) / 0.0 / None (no ground truth)
- `best_fractional_coverage`: max fractional coverage (diagnostic, NOT completion)
- Ordinary `recall_at_k` unchanged

```
[REVIEWER-v03] Full set covered: completion=1.0, best_fractional=1.0
[REVIEWER-v03] Partial coverage: completion=0.0, best_fractional=0.5
[REVIEWER-v03] No ground truth: completion=None, best_fractional=None
```

### Malformed Artifacts → Structured Gaps (No Crashes)

**Verified**: All malformed JSON/artifacts yield structured gap strings, never exceptions:

```
[REVIEWER-v03] Malformed questions (not a list): False, gaps=["questions file: questions file must be a JSON list", ...]
[REVIEWER-v03] Malformed split map: False, gaps=["split map: split map must have a 'groups' object", ...]
[REVIEWER-v03] Trace with NaN score: ["stage_scores[stage0]: non-finite score nan"]
[REVIEWER-v03] Trace with bare float threshold: ["thresholds[stage0]: policy score_kind 'calibrated_probability' != trace score_kind 'logit'", "thresholds[stage0]: threshold interpretation is unspecified (fail closed)"]
```

### Round 0 Phase Enforcement

**Location**: `manifest.py:7`, `302-303`

- `RunManifest.phase` defaults to `"round0-substrate"`
- Freeze rejects unknown phases
- Threshold policies recorded as **declarations** (presence + validity); learned/fitted thresholds produced by architecture teams in Round 1
- Unfitted `model_probability` / `none_ranking_only` declarations pass freeze (test proves)

---

## Raw Probe Outputs (Reviewer-Prefixed)

```
[REVIEWER-v03] questions_sha256 detects text change: DETECTED
[REVIEWER-v03] generator_config_sha256 detects license change: DETECTED
[REVIEWER-v03] generator_config_sha256 detects quantization change: DETECTED (raw + semantic)
[REVIEWER-v03] split_map_sha256 detects tampering: DETECTED
[REVIEWER-v03] validate_group_map empty groups: REJECTED
[REVIEWER-v03] validate_group_map duplicate articles: REJECTED
[REVIEWER-v03] validate_group_map unresolved articles: REJECTED
[REVIEWER-v03] validate_qa_group_consistency no metadata: SKIPPED
[REVIEWER-v03] validate_qa_group_consistency unknown group: SKIPPED
[REVIEWER-v03] validate_qa_group_consistency known group wrong split: ERROR
[REVIEWER-v03] validate_qa_group_consistency source_articles multi-split: ERROR
[REVIEWER-v03] validate_qa_group_consistency source_articles wrong declared split: ERROR
[REVIEWER-v03] Runtime inventory hashes match: VERIFIED
[REVIEWER-v03] Runtime inventory tamper detected: DETECTED
[REVIEWER-v03] Runtime inventory unpinned declaration: DETECTED
[REVIEWER-v03] Hallucinated citation no audit: PERMITTED
[REVIEWER-v03] Hallucinated citation consistent audit: PERMITTED
[REVIEWER-v03] Hallucinated citation inconsistent audit: REJECTED
[REVIEWER-v03] Binary completion 1.0/0.0/None: WORKING
[REVIEWER-v03] best_fractional_coverage separate: EXPOSED
[REVIEWER-v03] Malformed artifacts: STRUCTURED GAPS
[REVIEWER-v03] Trace validation delegates to ThresholdPolicy.validate: CONFIRMED
[REVIEWER-v03] model_probability accepted: CONFIRMED
[REVIEWER-v03] model_probability + logit rejected: CONFIRMED
[REVIEWER-v03] fitted without calibration_partition rejected: CONFIRMED
[REVIEWER-v03] none_ranking_only + probability rejected: CONFIRMED
[REVIEWER-v03] raw_score_absolute + logit accepted: CONFIRMED
[REVIEWER-v03] Phase round0-substrate enforced: CONFIRMED
```

---

## Distinction: Data Not Yet Present vs Code Issues

| Item | Status | Owner |
|------|--------|-------|
| `corpus/corpus.jsonl` | Missing (pilot fetch ongoing) | Corpus worker |
| `corpus/questions.json` | Missing (later step) | QA worker |
| `corpus/heldout_labels.sealed.json` | Missing (orchestrator custody) | Orchestrator |
| Generator v3 smoke run | Independent PASS captured separately | Generator worker |
| Real sealed labels access | Never parsed (procedural custody) | By design |

---

## Recommended Repair Priority

1. **P0 (design decision required)**: QA group provenance mandatory vs optional for controlled dataset
   - Option A: Make `meta.group` or `meta.source_articles` required for all questions (gap if missing)
   - Option B: Add explicit "public reference" exception flag in question metadata
   - Option C: Document as known limitation; architecture teams must handle in Round 1

2. **P1 (before freeze claim)**: None — all code-level freeze bypasses closed

---

## Conclusion

The v0.3 substrate **code is freeze-ready** — all 5 P0 freeze bypasses from v0.2 are closed with verified hash recomputation, semantic validation, and fail-closed error handling. The 147 tests pass including 28 new v0.3 regression tests.

**One design decision remains**: Whether QA source group provenance should be mandatory (fail if question lacks `meta.group`/`source_articles`) for the controlled dataset. Current behavior skips such questions. This is a **policy choice**, not a code defect.

**Action required**: Orchestrator decides on QA provenance mandate. If mandatory, substrate worker adds gap for missing metadata; if optional, document limitation and proceed to independent review.