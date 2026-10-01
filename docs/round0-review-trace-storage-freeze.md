# Round 0 Independent Adversarial Review — Storage Honesty, Freeze Fail-Closed, Threshold Domain, Verifier

**Reviewer:** opencode/nemotron-3-ultra-free (free model, explicit selection)
**Repo:** /home/davidhatley/Projects/testing/local_mobile_research @ HEAD 230e7d5
**Date:** 2026-09-30

---

## Executive Summary

**PASS** — All probed defect classes pass their fail-closed checks. No blockers remain in the reviewed components. The substrate is ready for freeze gate.

---

## STORAGE HONESTY (BLOCKER 10) — PASS

### Probe: `measure_storage(["/nonexistent"])`
- **Observed:** `total_bytes=None, complete=False, known_bytes=0, missing=["/nonexistent"]`
- **Expected:** total_bytes=None, complete=False, known_bytes=0, missing lists the path
- **Result:** PASS — missing path yields None total, never 0

### Probe: `measure_storage([present, missing])`
- **Observed:** `total_bytes=None, complete=False, known_bytes=11, missing=[missing_path]`
- **Expected:** total_bytes=None, known_bytes == size of present
- **Result:** PASS — partial measurement cannot masquerade as complete

### Probe: `measure_storage([present])`
- **Observed:** `total_bytes=11, complete=True, known_bytes=11, missing=[]`
- **Expected:** total_bytes == exact bytes, complete=True, missing=[]
- **Result:** PASS — complete measurement yields exact integer total

### Probe: `storage_manifest` with missing required entry
- **Observed:** `total_bytes=None, complete=False, known_bytes=11, missing=[missing_path]`
- **Expected:** total_bytes=None + complete=False; no code path returns integer total when complete=False
- **Result:** PASS — `complete=false` paired with `integer total_bytes` is impossible

### Test Change Verification: `test_measure_storage_missing_path_is_zero`
- **Old test (b38a457):** `test_measure_storage_missing_path_is_zero` — asserted `total_bytes == 0` (enshrined BLOCKER 10 bug)
- **New test (230e7d5):** `test_measure_storage_missing_path_is_not_a_valid_total` — asserts `total_bytes is None` + `complete=False` + `known_bytes=0`
- **Additional test:** `test_measure_storage_total_only_when_all_measured` — validates partial vs complete behavior
- **Result:** PASS — test was CHANGED, not deleted-and-forgotten

---

## FREEZE FAIL-CLOSED (BLOCKER: corruption detection) — PASS

Each corruption probe executed in a temp root (never mutating repo). All produce explicit gap strings, never a pass.

| Probe | Corruption | Gap Produced | PASS |
|-------|------------|--------------|------|
| 1 | Manifest code hash (`substrate/manifest.py`) | `code hash mismatch (recomputed): substrate/manifest.py` | ✅ |
| 2 | Corpus hash | `corpus_hash mismatch: manifest does not match corpus.jsonl content` | ✅ |
| 3 | Generator config hash | `generator_config_sha256 mismatch: manifest does not match config bytes` | ✅ |
| 4 | Questions SHA-256 | `questions_sha256 mismatch: manifest does not match questions.json bytes` | ✅ |
| 5 | Sealed labels SHA-256 | `sealed labels hash mismatch: artifact changed since seal` | ✅ |
| 6 | Runtime binary hash (`llama-server`) | `inventory runtime-binary: sha256 mismatch (recomputed): llama-server` + `runtime binary unpinned in manifest inventory: llama-server` | ✅ |
| 7 | Split map SHA-256 | `split_map_sha256 mismatch: manifest does not match map bytes` | ✅ |

### Critical Regression: Regime Validation UnboundLocalError on `groups_raw`
- **Code locations:** `manifest.py:563` (regime B non-empty branch) and `manifest.py:577` (regime B empty branch)
- **Probe 8 (regime B non-empty):** `regime_b_document_heldout_groups=['test_group']` — no regime gaps, no UnboundLocalError
- **Probe 9 (regime B empty):** `regime_b_document_heldout_groups=[]` — explicit gap `regime_b_document_heldout_groups is empty but split map has heldout groups`, no UnboundLocalError
- **Result:** PASS — both branches exercise `groups_raw` without UnboundLocalError

---

## THRESHOLD DOMAIN (BLOCKER 2) — PASS

All domain consistency checks enforced by `validate_trace` and `ThresholdPolicy.validate()`.

| Probe | Condition | Error Observed | PASS |
|-------|-----------|----------------|------|
| 1 | `stage.score_kind != policy.score_kind` | `policy score_kind 'logit' != stage score_kind 'calibrated_probability'` | ✅ |
| 2 | `calibrated_probability` stage with scores outside [0,1] | `calibrated_probability must be in [0, 1], got 1.5` | ✅ |
| 3 | `model_probability` stage with scores outside [0,1] | `calibrated_probability must be in [0, 1], got 1.5` (validate_score_value covers both) | ✅ |
| 4 | `model_probability` stage using `interpretation=calibrated_probability` | `probability interpretation requires calibrated_probability scores` | ✅ |
| 5 | `model_probability_dev_selected` on `logit` stage | `model_probability_dev_selected interpretation requires score_kind='model_probability'` | ✅ |
| 6 | Fitted `calibration_method` without `calibration_partition` | `fitted calibration claim requires provenance (calibration_partition)` | ✅ |

### Legacy Migration Fail-Closed
- **Probe 7:** `migrate_legacy_trace` with empty `model_identity_map` → raises `ValueError: stage 'stage0': no model_identity provided ... legacy migration fails closed (no fabricated provenance)`
- **Probe 8:** `migrate_legacy_trace` with `model_identity_map={'stage0': ''}` → raises `ValueError: model_identity must be a non-empty string`
- **Probe 9:** `migrate_legacy_trace` with caller-provided `'legacy-unknown'` → migration succeeds (caller responsibility), but migration function **never invents** the placeholder
- **Result:** PASS — no silent provenance fabrication; unidentifiable legacy traces fail closed

---

## VERIFIER (BLOCKER 13) — PASS

### `./scripts/verify_round0` (full mode) — Non-zero exit while artifacts missing
- **Exit code:** 1
- **Stages 6 & 8 fail** explicitly: missing `corpus/questions.json`, `corpus/heldout_labels.sealed.json`, unrecorded hashes, empty thresholds, regime metadata gaps
- **Result:** PASS — fails closed, no silent pass

### `./scripts/verify_round0 --code-only` — Exit 0 + NOT-A-FREEZE-PASS banner
- **Exit code:** 0
- **Banner printed:** 
  ```
  ###################################################################
  #  CODE-ONLY MODE -- THIS IS NOT A FREEZE PASS.                    #
  #  Stages 6 (question/label partition) and 8 (freeze manifest)     #
  #  were NOT run: they require freeze artifacts that do not exist.  #
  #  A 0 exit here means the code-level checks ran; it says NOTHING   #
  #  about whether Round 0 may be frozen.                            #
  ###################################################################
  ```
- **Final line:** `RESULT: code-level checks completed (NOT a freeze pass).`
- **Never prints** "all load-bearing stages PASS" or similar freeze-pass language
- **Result:** PASS

### `--help` — Side-effect-free and fast
- **Exit code:** 0
- **No stage runs**, no repository resolution, no scratch directory created, no file writes
- **Execution time:** <100ms
- **Result:** PASS

### Sealed Label Content — Never Opened
- Stage 6 uses `verify_seal_opaque` (raw-byte SHA-256 only)
- Explicit log: `sealed labels: content NOT read, NOT parsed, NOT printed`
- Custodian `load_labels` tested with `allow_heldout=True` but denied (dev-side refusal)
- Test `test_never_prints_sealed_label_content` in `test_verify_round0_entrypoint.py` asserts this
- **Result:** PASS

### Two `--code-only` Runs — Byte-Identical
```bash
./scripts/verify_round0 --code-only 2>&1 > /tmp/verify1.txt
./scripts/verify_round0 --code-only 2>&1 > /tmp/verify2.txt
diff /tmp/verify1.txt /tmp/verify2.txt  # no differences
```
- **Result:** PASS — deterministic output

### No Silent Stage Failures
- Each stage records PASS/FAIL/SKIP to `results.tsv`
- Summary table printed with explicit counts
- `NOT VERIFIED` list printed for skipped stages (not conflated with PASS)
- Final exit code reflects `N_FAIL > 0` correctly
- **Result:** PASS — no stage silently fails while tool reports success

---

## Additional Verification

### Full Test Suite
```bash
python3 -m unittest discover -s tests -v
# Ran 321 tests in 14.750s — OK
```

All substrate, contract, telemetry, corpus, data-tools, and verifier entrypoint tests pass.

---

## Conclusion

**All four BLOCKER categories pass their adversarial probes:**

1. **Storage Honesty (BLOCKER 10):** ✅ Fail-closed totals, no zero-masking, test properly changed
2. **Freeze Fail-Closed:** ✅ Every corruption produces explicit gap; UnboundLocalError regression fixed
3. **Threshold Domain (BLOCKER 2):** ✅ All domain mismatches caught; legacy migration fails closed
4. **Verifier (BLOCKER 13):** ✅ Full mode fails, code-only disclaims, --help safe, sealed labels opaque, deterministic

**Final Verdict: PASS** — The reviewed components are ready for the Round 0 freeze gate. No implementation fixes required from this review.