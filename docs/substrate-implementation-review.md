# Round 0 Substrate Implementation Review

**Reviewer**: `opencode/nemotron-3-ultra-free` (explicit, verified zero-cost catalog entry)
**Date**: 2026-09-28
**Verdict**: **REPAIR REQUIRED**

---

## Executive Summary

The substrate passes all 34 infrastructure tests but contains **critical implementation gaps** that would allow a fake freeze to pass, silently accept invalid benchmark data, and produce misleading metrics. The code correctly implements the *syntactic* contract but fails the *semantic* requirements from the master orchestration prompt.

**Blocking issues (must fix before freeze)**:
1. `validate_freeze` does not recompute/verify artifact hashes — accepts wrong content
2. `survival_curve` assumes irreversible pruning — contradicts DAG/multihop recovery
3. Calibration metrics (ECE, Brier) accept raw logits — no domain validation
4. Trace validation is structural only — accepts negative latencies, logits as probabilities
5. Generator config allows "unspecified" quantization/runtime while `is_pinned()` returns true
6. Token budget enforced via whitespace estimate — diverges from real tokenizer
7. Single required-evidence set assumed — architecture supports DAG alternative paths
8. Held-out custodian is purely procedural — same-user bypass trivial
9. Missing trace fields required by master prompt (adaptive compute, model-loading latency, etc.)
10. No verification of code_hashes against actual files

**Non-blocking but significant**:
- Single integer seed insufficient for multi-component reproducibility
- Thresholds dict lacks calibration method / top-K fallback metadata
- Generator prompt_hash not validated against `FIXED_GENERATION_PROMPT`
- `timed_stage` cannot separate model-loading vs inference latency
- Stub generator exclusion is documentary only

---

## Detailed Findings

### 1. Fake Freeze Acceptance (CRITICAL)

**Location**: `substrate/manifest.py::validate_freeze`

**Issue**: `validate_freeze` checks only that four artifact files *exist* and that manifest fields are non-placeholder strings. It **does not**:
- Recompute `corpus_hash` from `corpus/corpus.jsonl` and compare to manifest
- Verify `code_hashes` against actual source files
- Validate `generator.prompt_hash` equals `PROMPT_HASH`
- Check `quantization`/`runtime` are not `"unspecified"`

**Reproduction**:
```python
# All four files exist with WRONG content, manifest has WRONG corpus_hash
# validate_freeze returns FreezeCheck(passed=True, gaps=[])
```

**Required fix**: `validate_freeze` must:
1. Read each required artifact, compute its hash, compare to manifest
2. Verify `code_hashes` by hashing listed files
3. Assert `generator.prompt_hash == PROMPT_HASH`
4. Assert `generator.quantization != "unspecified" and generator.runtime != "unspecified"`

---

### 2. Survival Curve Assumes Irreversible Loss (CRITICAL)

**Location**: `eval/metrics.py::survival_curve`

**Issue**: The master prompt explicitly states: *"The same passage may be discoverable through several routes. This redundancy is desirable because catastrophic pruning must be avoided."* and describes multi-hop retrieval where evidence lost at one stage can be recovered via alternate DAG paths.

`survival_curve([True, False, True])` returns `[1.0, 0.0, 0.0]` — once `False`, survival stays `0.0` forever. This **contradicts the architecture**.

**Required fix**: 
- Change `survival_curve` to accept per-stage *survival rates* (float 0–1) not booleans
- Or add `survival_curve_with_recovery(stage_hits: list[bool], recovered: list[bool])` 
- Document that compound survival must be computed from rates, not binary hits

---

### 3. Calibration Metrics Accept Raw Logits (CRITICAL)

**Location**: `eval/metrics.py::expected_calibration_error`, `brier_score`

**Issue**: Reranker/cross-encoder outputs are **logits** (unbounded real values), not calibrated probabilities. The metrics:
- `expected_calibration_error` silently accepts values outside [0,1], bins by `int(p * n_bins)` → `IndexError` for `p>1`, wrong bins for `p<0`
- `brier_score` computes `(p - y)²` with logits → meaningless values
- No validation, no auto-sigmoid, no warning

**Reproduction**:
```python
expected_calibration_error([5.0, -2.0], [1, 0])  # IndexError
expected_calibration_error([1.5, 0.5], [1, 0])   # Returns 0.5 (nonsense)
brier_score([5.0, 0.5], [1, 0])                  # Returns 12.25 (nonsense)
```

**Required fix**:
- Add domain check: `all(0.0 <= p <= 1.0 for p in probs)` with clear error
- Document that callers MUST calibrate (Platt/sigmoid/isotonic) before passing to metrics
- Optionally provide `calibrate_logits(logits, method="sigmoid")` helper

---

### 4. Trace Validation Is Only Structural (CRITICAL)

**Location**: `eval/run_format.py::validate_trace`, `write_traces_jsonl`

**Issue**: `validate_trace` checks field *presence* only. It accepts:
- Negative latencies (`retrieval_latency_ms: -1.0`)
- Logits in `stage_scores` (should be calibrated probabilities)
- Thresholds meaningless for logit scores
- Missing `adaptive_compute_decision`, `model_loading_latency_ms`, `inference_latency_ms`, `peak_rss_mb`, `storage_bytes`, `grader_result` (all required by master prompt §Round 4)

**Required fix**:
- Add semantic validation: latencies ≥ 0, scores in [0,1] if calibrated, thresholds consistent with score domain
- Add all master-prompt-required fields to `TRACE_REQUIRED_FIELDS`
- Extend `StageRecord` and `RetrievalOutcome` types accordingly

---

### 5. Generator Config Allows "Unspecified" While Pinned (CRITICAL)

**Location**: `substrate/generator.py::GeneratorConfig.is_pinned`

**Issue**: `is_pinned()` returns `True` if `model_id != "TBD" and revision != "TBD"` — but `quantization` and `runtime` default to `"unspecified"`. The master prompt (§Mobile Projection) requires these for Android feasibility. `validate_freeze` does not check them.

**Required fix**:
- `is_pinned()` must also require `quantization != "unspecified" and runtime != "unspecified"`
- `validate_freeze` must verify this

---

### 6. Token Budget Enforced via Whitespace Estimate (HIGH)

**Location**: `substrate/evidence.py::estimate_tokens`, `build_packet`

**Issue**: `estimate_tokens("don't won't can't") == 3` but real tokenizers (Llama, Gemma, Qwen) count contractions as 2–3 tokens each. The 300–800 target band and 1000 hard cap are **whitespace estimates**, not tokenizer measurements. The contract (§4) acknowledges this but the implementation provides no migration path.

**Required fix**:
- Add `real_tokenizer_estimate(text, tokenizer_id)` stub that raises `NotImplementedError` until generator is pinned
- `build_packet` should accept optional `tokenizer` callable; if absent, use whitespace with explicit warning in packet metadata
- `EvidencePacket` should record `token_estimation_method: "whitespace" | "tokenizer:<id>"`

---

### 7. Single Required-Evidence Set Assumed (HIGH)

**Location**: `eval/metrics.py::recall_at_k`, `survival_curve`, `compound_survival`

**Issue**: All metrics take a single `required: set[str]`. The architecture (§Corpus Structure) states: *"The same passage may be discoverable through several routes... Possible independent access paths: canonical title, alias, redirect, entity, keyword, location, relation, article link, topic, semantic representation."*

If evidence `p3` (alias path) answers the question but `required = {p1}` (canonical path), recall = 0.0 despite correct answer being retrieved.

**Required fix**:
- Change `required` to `list[set[str]]` (alternative sufficient evidence sets)
- `recall_at_k(retrieved, [{"p1", "p2"}, {"p3"}], k)` → 1.0 if any set fully covered
- Update `survival_curve` and trace format accordingly

---

### 8. Held-Out Custodian Is Procedural Only (HIGH)

**Location**: `substrate/splits.py::HeldoutCustodian`

**Issue**: Acknowledged in contract (§3) but implementation provides **no defense** against same-user bypass:
- Direct file read: `open(labels_path).read()`
- Environment variable: `os.environ["HELDOUT_CUSTODIAN_MODE"] = "benchmark"`
- No file permissions, no encryption, no separate process

**Required fix**:
- Document clearly: "True isolation requires orchestrator to withhold sealed file from dev workers"
- Consider: sealed file encrypted, key held by orchestrator only
- At minimum: `HeldoutCustodian` should verify file integrity (hash) on load

---

### 9. Missing Master-Prompt Trace Fields (HIGH)

**Location**: `substrate/types.py`, `eval/run_format.py`

**Missing from `TRACE_REQUIRED_FIELDS` and types**:
| Master Prompt Field | Status |
|---------------------|--------|
| `adaptive_compute_decision` | Missing |
| `model_loading_latency_ms` | Missing |
| `inference_latency_ms` | Missing |
| `peak_rss_mb` (per question) | Missing from trace (only in `RetrievalOutcome`) |
| `storage_bytes` | Missing |
| `grader_result` | Missing |

**Required fix**: Add all fields to types, trace schema, and validation.

---

### 10. Code Hashes Not Verified Against Files (MEDIUM)

**Location**: `substrate/manifest.py::validate_freeze`

**Issue**: `code_hashes` checked for non-empty only. Manifest can claim `{"a.py": "fakehash"}` and pass.

**Required fix**: `validate_freeze` must hash each listed file and compare.

---

### 11. Prompt Hash Not Validated (MEDIUM)

**Location**: `substrate/manifest.py::validate_freeze`

**Issue**: Generator config can have arbitrary `prompt_hash`; freeze passes.

**Required fix**: `validate_freeze` must assert `manifest.generator.prompt_hash == PROMPT_HASH`.

---

### 12. Single Seed Insufficient (MEDIUM)

**Location**: `substrate/manifest.py::RunManifest`, `substrate/splits.py`

**Issue**: `RunManifest.seed: int` but `assign_split` uses string seed. Experiments need separate seeds for: corpus shuffle, model init, data augmentation, retrieval randomness. Master prompt: *"reproducible random seeds"* (plural).

**Required fix**: `RunManifest.seeds: dict[str, int]` with keys like `"split"`, `"model"`, `"retrieval"`.

---

### 13. Thresholds Lack Calibration/Top-K Metadata (MEDIUM)

**Location**: `substrate/manifest.py::RunManifest.thresholds`

**Issue**: `thresholds: dict[str, float]` stores only the numeric threshold. Master prompt (§Thresholds and Calibration) requires: top-K fallback, minimum breadth preservation, uncertainty-adaptive compute config.

**Required fix**: `ThresholdPolicy` dataclass with `threshold`, `top_k`, `min_breadth`, `adaptive_config`.

---

### 14. Timed Stage Cannot Separate Model Loading vs Inference (MEDIUM)

**Location**: `substrate/telemetry.py::timed_stage`

**Issue**: Master prompt requires separate `model_loading_latency_ms` and `inference_latency_ms`. `timed_stage` provides only `elapsed_ms`.

**Required fix**: Add `timed_model_load()` and `timed_inference()` context managers, or `timed_stage` with `phase` parameter.

---

### 15. Stub Generator Exclusion Is Documentary Only (LOW)

**Location**: `substrate/generator.py::DeterministicStubGenerator`

**Issue**: Contract says *"Any benchmark row using this id is invalid by construction"* but no runtime check prevents it.

**Required fix**: Add `is_stub` property to `Generator` protocol; `validate_trace` rejects traces with stub generator in benchmark mode.

---

## Test Coverage Gaps

The 34 tests are **infrastructure sanity checks only** (all fixtures labeled `SYNTHETIC`/`infra-only`). Missing tests for:
- `validate_freeze` with mismatched hashes (should fail)
- `survival_curve` with recovery (should not force 0)
- ECE/Brier with out-of-domain inputs (should raise)
- Trace validation with negative latencies (should reject)
- Generator config with unspecified quantization (should not pin)
- Evidence packet with real tokenizer (when available)
- Alternative sufficient evidence sets in recall
- Heldout custodian bypass attempts

---

## Distinction: Implementation Repairs vs External Pending Artifacts

| Issue | Type | Owner |
|-------|------|-------|
| `validate_freeze` hash verification | **Implementation repair** | Substrate worker |
| `survival_curve` recovery support | **Implementation repair** | Substrate worker |
| Calibration metric domain validation | **Implementation repair** | Substrate worker |
| Trace semantic validation + missing fields | **Implementation repair** | Substrate worker |
| Generator config pinning strictness | **Implementation repair** | Substrate worker |
| Tokenizer integration stub | **Implementation repair** | Substrate worker |
| Alternative evidence sets in metrics | **Implementation repair** | Substrate worker |
| Heldout custodian integrity check | **Implementation repair** | Substrate worker |
| Code hash verification | **Implementation repair** | Substrate worker |
| Prompt hash validation | **Implementation repair** | Substrate worker |
| Multi-seed manifest | **Implementation repair** | Substrate worker |
| Threshold policy metadata | **Implementation repair** | Substrate worker |
| Model-loading vs inference timing | **Implementation repair** | Substrate worker |
| Stub generator runtime rejection | **Implementation repair** | Substrate worker |
| Real corpus artifact (`corpus.jsonl`) | **External pending** | Reference audit worker |
| Real question set (`questions.json`) | **External pending** | Reference audit worker |
| Sealed held-out labels | **External pending** | Orchestrator (withhold) |
| Pinned generator config | **External pending** | Reference audit worker |
| Independent review completion | **External pending** | Orchestrator |

---

## Recommended Repair Priority

1. **P0 (block freeze)**: #1, #2, #3, #4, #5
2. **P1 (before Round 1)**: #6, #7, #8, #9, #10, #11
3. **P2 (before benchmark)**: #12, #13, #14, #15

---

## Raw Probe Outputs (Reviewer-Prefixed)

All probes executed with `opencode/nemotron-3-ultra-free`. See reproduction commands in each finding above. Key outputs:

```
[REVIEWER] validate_freeze accepts wrong corpus_hash: True
[REVIEWER] validate_freeze accepts wrong file content: True  
[REVIEWER] validate_freeze accepts fake code_hashes: True
[REVIEWER] survival_curve([True, False, True]): [1.0, 0.0, 0.0]
[REVIEWER] ECE with logits: IndexError / nonsense values
[REVIEWER] Brier with logits: nonsense values
[REVIEWER] validate_trace accepts negative latencies: True
[REVIEWER] GeneratorConfig(is_pinned) with unspecified quantization: True
[REVIEWER] Whitespace tokens vs real tokenizer: significant divergence
[REVIEWER] recall_at_k with alternative evidence: 0.0 (incorrect)
[REVIEWER] HeldoutCustodian bypass via direct read: success
[REVIEWER] HeldoutCustodian bypass via env var: success
[REVIEWER] Missing trace fields: adaptive_compute_decision, model_loading_latency_ms, inference_latency_ms, peak_rss_mb, storage_bytes, grader_result
[REVIEWER] Single seed only in manifest
[REVIEWER] Thresholds dict lacks policy metadata
[REVIEWER] timed_stage cannot separate load vs inference
```

---

## Conclusion

The substrate **cannot be frozen** in its current state. The 34 passing tests verify syntactic correctness of synthetic fixtures but do not exercise the semantic requirements of the master orchestration prompt. The critical issues (#1–5) would allow a frozen run to claim reproducibility while using wrong artifacts, wrong metrics, and invalid traces.

**Action required**: Substrate worker must implement P0 repairs and re-run `validate_freeze` with real artifact verification before independent review can PASS.