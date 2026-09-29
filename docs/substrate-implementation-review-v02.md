# Round 0 Substrate Implementation Review v0.2

**Reviewer**: `opencode/nemotron-3-ultra-free` (explicit, verified zero-cost catalog entry)
**Date**: 2026-09-28
**Verdict**: **REPAIR REQUIRED**

---

## Executive Summary

The v0.2 substrate passes all **88 infrastructure tests** and fixes most P0 issues from v0.1 (hash recomputation, stub rejection, prompt-hash pin, placeholder rejection, opaque seal verification, score-domain validation). However, **critical gaps remain** that would allow an invalid freeze to pass or produce misleading benchmark data.

**Blocking issues (must fix before freeze claim)**:
1. **Questions file content not hashed** — only split consistency validated; text changes undetected
2. **Generator disk comparison incomplete** — misses `generator_id`, `chat_template_sha256`, `context_window`, `download_url`, `license`, `verification`, `runtime_binaries`, `tokenizer_gguf` fields
3. **Group-map split method validates path only** — no content/hash/assignment logic or supervised article disjointness check
4. **Trace validation weaker than policy validation** — accepts threshold policies that `ThresholdPolicy.validate()` rejects (unknown interpretation, score_kind/interpretation mismatch, bare sigmoid claim)
5. **No runtime binary/library hashes in GeneratorConfig/manifest** — "everything verified" claim not met

**Non-blocking but significant**:
- Same-UID custodian bypass remains procedural (acknowledged, not a code defect)
- Missing actual corpus/QA is external, not code defect
- No generator smoke run yet (generator worker repairing concurrently)

---

## Detailed Findings

### 1. Questions File Content Not Hashed (CRITICAL)

**Location**: `substrate/manifest.py::validate_freeze` (lines 182-214), `RunManifest` lacks `questions_sha256` field

**Issue**: `validate_questions_file()` checks schema + split consistency, but the manifest does not store a content hash of `corpus/questions.json`. Changing question text while preserving `question_id` and declared split passes freeze.

**Reproduction**:
```python
# Initial freeze passes
# Change question text from "q?" to "CHANGED QUESTION TEXT" (same qid, same split)
# validate_freeze still passes — content change undetected
```

**Required fix**: Add `questions_sha256` to `RunManifest`, compute and compare in `validate_freeze` (like corpus/labels).

---

### 2. Generator Disk Comparison Incomplete (CRITICAL)

**Location**: `substrate/manifest.py::validate_freeze` (lines 216-253)

**Issue**: The comparison loop only checks these fields:
```python
for field_name in (
    "model_id", "revision", "prompt_hash", "quantization", "runtime",
    "file", "artifact_sha256", "artifact_bytes",
):
```
**Missing from comparison** (all present in `corpus/generator_config.json`):
- `generator_id` — identity of the generator instance
- `chat_template_sha256` — GGUF-embedded template hash (critical for prompt delivery)
- `context_window` / `context_window_pinned` — model context size
- `download_url` — provenance of artifact
- `license` / `license_evidence` — license compliance
- `verification` — HF header/ETag/size match records
- `runtime_binaries` — llama-server + all .so hashes (the "everything" claim)
- `runtime_full` — build compiler, git commit, source tree
- `tokenizer` / `tokenizer_gguf` — full tokenizer identity
- `runtime_threads_measured` — thread count used

**Reproduction**:
```python
# Change generator_id on disk to "different-generator-id" → freeze passes
# Change chat_template_sha256 → freeze passes
# Change context_window → freeze passes
```

**Required fix**: Compare ALL fields from `GeneratorConfig.from_dict(disk)` against manifest `gen`. At minimum: add `generator_id`, `tokenizer_id`, `context_window`, `sampling`, `chat_template_sha256`, and recurse into `runtime_binaries` / `tokenizer_gguf`.

---

### 3. Group-Map Split Method Validates Path Only (CRITICAL)

**Location**: `substrate/manifest.py::validate_freeze` (lines 208-214)

**Issue**: For `split_method == "group-map"`, validation only checks:
```python
if not manifest.split_map_path or not os.path.isfile(...):
    gaps.append("group-map split method without a pinned split_map_path artifact")
```
**No validation of**:
- Split map content structure (groups, articles, assigned splits)
- Hash of split map content vs manifest
- Supervised article disjointness (train/dev/heldout articles must not overlap)
- Group integrity (confusable sets kept together)

**Reproduction**:
```python
# split_map.json with empty groups: {"groups": []} → freeze passes
# split_map.json with overlapping supervised articles → freeze passes
# No hash of split_map stored in manifest
```

**Required fix**: 
- Add `split_map_sha256` to `RunManifest`
- Parse and validate group structure, disjointness, article coverage
- Compare recomputed hash

---

### 4. Trace Validation Weaker Than Policy Validation (CRITICAL)

**Location**: `eval/run_format.py::validate_trace` (lines 120-136) vs `substrate/types.py::ThresholdPolicy.validate` (lines 171-203)

**Issue**: `validate_trace` does only basic threshold checks. It **does not** call `ThresholdPolicy.validate()`, so it misses:

| Policy Violation | `ThresholdPolicy.validate()` | `validate_trace()` |
|------------------|------------------------------|---------------------|
| `interpretation="calibrated_probability"` + `calibration_method="none_ranking_only"` | ✅ Rejects ("sigmoid alone is not calibration") | ❌ Accepts |
| `interpretation="unknown"` | ✅ Rejects | ❌ Accepts |
| `score_kind="logit"` + `interpretation="calibrated_probability"` | ✅ Rejects ("probability interpretation requires calibrated_probability scores") | ❌ Accepts |
| `score_kind="calibrated_probability"` + `interpretation="raw_score_absolute"` with threshold 2.5 | ✅ Rejects (threshold invalid for score_kind) | ❌ Accepts |

**Reproduction**:
```python
trace = dict(good_trace, 
    thresholds={'stage0': {'threshold': 0.5, 'interpretation': 'calibrated_probability', 'calibration_method': 'none_ranking_only', 'score_kind': 'calibrated_probability'}})
validate_trace(trace)  # Returns [] — ACCEPTS invalid policy
```

**Required fix**: In `validate_trace`, instantiate `ThresholdPolicy.from_dict(thr)` and call `.validate()` for each stage's threshold dict. Or duplicate the critical checks.

---

### 5. No Runtime Binary/Library Hashes in GeneratorConfig/Manifest (HIGH)

**Location**: `substrate/generator.py::GeneratorConfig`, `substrate/manifest.py::RunManifest`

**Issue**: The `corpus/generator_config.json` contains a detailed `runtime_binaries` section with 8 library hashes + `llama-server` binary hash. But:
- `GeneratorConfig` has no fields for these
- `RunManifest` has no fields for these
- `validate_freeze` does not verify them (the generator adapter `qwen25_adapter.py::prepare()` does, but freeze validation doesn't)

**Required fix**: Add `runtime_binaries_sha256` (or full structure) to `GeneratorConfig` and `RunManifest`, verify in `validate_freeze`.

---

### 6. ThresholdPolicy Legacy Float Migration Silent in Trace (MEDIUM)

**Location**: `substrate/types.py::ThresholdPolicy.from_dict` (lines 209-221), `eval/run_format.py`

**Issue**: Legacy float threshold (e.g., `0.7`) migrates to `ThresholdPolicy(threshold=0.7, interpretation="unspecified")` which `validate()` rejects. But trace validation accepts bare floats without checking `interpretation`.

**Required fix**: Trace validation should reject bare-float thresholds or require explicit `interpretation`.

---

### 7. Custodian Bypass Procedural (ACKNOWLEDGED, NOT CODE DEFECT)

**Location**: `substrate/splits.py::HeldoutCustodian`

**Status**: Module doc explicitly states: *"HONEST LIMITATION: all agents run as the same OS user, so file permissions cannot truly seal labels and no encryption theater is implemented... True isolation requires the orchestrator to withhold the sealed file from development workers."*

**Verification**: Direct file read bypasses custodian; `HELDOUT_CUSTODIAN_MODE=benchmark` env var settable by any process. This is by design, not a bug.

---

### 8. Missing Actual Corpus/QA — External, Not Code Defect

The absence of `corpus/corpus.jsonl`, `corpus/questions.json`, `corpus/heldout_labels.sealed.json` is a **data availability** issue (reference audit worker / orchestrator scope), not a substrate code defect. Freeze correctly blocks on these.

---

### 9. Generator Smoke Run — Generator Worker Scope

The `generator_runtime/qwen25_adapter.py` exists and produces smoke traces (`smoke_trace_v2_*.json`). The "config_pinned_compat": false in the trace indicates the generator worker is still aligning the adapter with the contract. This is concurrent work, not a substrate blocker.

---

## Distinction: Round 0 Freeze vs Architecture-Specific Requirements

| Requirement | Round 0 Freeze | Architecture Teams (Round 1) |
|-------------|----------------|------------------------------|
| Corpus pinned + hashed | ✅ Required | — |
| Questions pinned + hashed | ❌ Missing (fix #1) | — |
| Generator fully pinned + verified | ❌ Missing (fix #2, #5) | — |
| Split method validated (both modes) | ❌ group-map incomplete (fix #3) | — |
| Threshold policies recorded | ✅ In manifest | Teams provide calibrated policies |
| **Learned thresholds** | **NOT required** | Teams produce during Round 1 |
| Trace schema complete | ❌ Missing policy validation (fix #4) | Must emit valid traces |
| Seal opacity verified | ✅ | — |
| Stub/estimate rejection | ✅ | — |

**Do not require learned thresholds before teams exist** — the substrate must accept `"unspecified"` in `calibration_method` and `"calibrated_probability"` in `score_kind` as valid *declarations* (freeze checks presence, not that calibration is already fitted). Teams fit calibration during Round 1 dev.

---

## Raw Probe Outputs (Reviewer-Prefixed)

All probes executed with `opencode/nemotron-3-ultra-free`.

```
[REVIEWER-v02] Questions content hash not in manifest: CHANGE UNDETECTED
[REVIEWER-v02] Generator disk compare misses generator_id: PASSES
[REVIEWER-v02] Generator disk compare misses chat_template_sha256: PASSES
[REVIEWER-v02] Generator disk compare misses context_window: PASSES
[REVIEWER-v02] Generator disk compare misses runtime_binaries: PASSES
[REVIEWER-v02] Generator disk compare misses tokenizer_gguf: PASSES
[REVIEWER-v02] Group-map empty groups accepted: PASSES
[REVIEWER-v02] Group-map overlapping supervised articles: PASSES
[REVIEWER-v02] Trace accepts none_ranking_only for probability: ACCEPTS (policy rejects)
[REVIEWER-v02] Trace accepts unknown interpretation: ACCEPTS (policy rejects)
[REVIEWER-v02] Trace accepts logit + probability interp: ACCEPTS (policy rejects)
[REVIEWER-v02] Trace accepts calibrated + raw_score_absolute: ACCEPTS (policy rejects)
[REVIEWER-v02] Corpus hash recomputation works: DETECTS mismatch
[REVIEWER-v02] Seal tamper detected without reading labels: DETECTS
[REVIEWER-v02] Split inconsistency detected: DETECTS
[REVIEWER-v02] Code hash verification works: DETECTS mismatch
[REVIEWER-v02] Seed derivation log verified: DETECTS mismatch
[REVIEWER-v02] Stub generator rejected: REJECTED
[REVIEWER-v02] Whitespace estimate rejected for empirical: REJECTED
[REVIEWER-v02] Negative latencies rejected: REJECTED
[REVIEWER-v02] Unknown citations rejected: REJECTED
[REVIEWER-v02] Logit scores legal when score_kind=logit: ACCEPTED
[REVIEWER-v02] ECE/Brier reject logits/out-of-range: REJECTED
[REVIEWER-v02] Sufficient set completion distinct from recall: WORKING
[REVIEWER-v02] Survival vocabulary (lineage/coverage/recovery): WORKING
[REVIEWER-v02] Custodian same-UID bypass: CONFIRMED (by design)
```

---

## Recommended Repair Priority

1. **P0 (block freeze claim)**: #1, #2, #3, #4, #5
2. **P1 (before Round 1)**: #6

---

## Conclusion

The v0.2 substrate is **substantially improved** over v0.1 — hash recomputation, opaque seal verification, score-domain typing, and fail-closed validation are now working. However, the five P0 gaps above mean a freeze claim could be made with:
- Wrong question text
- Wrong generator configuration (template, binaries, tokenizer)
- Invalid group-map split assignments
- Invalid threshold policies in traces
- Unverified runtime binaries

**Action required**: Substrate worker must implement P0 repairs and re-run full adversarial test suite before independent review can PASS.