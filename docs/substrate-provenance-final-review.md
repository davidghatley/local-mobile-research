# Substrate Provenance Gate Final Review

**Reviewer**: `opencode/nemotron-3-ultra-free` (explicit, verified zero-cost catalog entry)
**Date**: 2026-09-29
**Verdict**: **PASS** (provenance gate closed; Round 0 freeze still blocked by missing corpus/QA/labels artifacts)

---

## Executive Summary

The provenance gate repair (Decision A+B) is **implemented and verified**. All 175 tests pass including 28 new `test_provenance.py` tests covering the exact acceptance criteria. The freeze validation now rejects any question lacking explicit provenance metadata. No code defects found in the repair.

**Scope verified**:
- `validate_question_provenance` (splits.py:277-450) — strict QA source provenance
- `build_article_index` (splits.py:189-208) — article resolution index
- `validate_group_map` (splits.py:211-274) — now returns `article_to_group`
- `manifest.py:402-417` — QA provenance integration in `validate_freeze`
- `test_provenance.py` — 28 adversarial tests

---

## Source Hashes (Snapshot)

| File | SHA-256 |
|------|---------|
| substrate/splits.py | 41e5f40f6fa87a32d51e8d2d4b1cae1c85173b80021eecbd5f425acc5e541176 |
| substrate/manifest.py | 95b0df75b1a05154245f68804a66d6f7bd538ba4197f867e1b9389344d410b26 |
| substrate/types.py | f64eecc95a2aa4b7a6d29c3b4e9bf5f5c5b71dc0857e6817aac785928a3a32df |
| substrate/generator.py | 91dbca009140262148ce88a54549d0804123db29c04b5430cdba5fea52fd3da4 |
| eval/run_format.py | 1f0fbf1935346d9eab84029abae7caec3867bf331770a36fa1a05a2141f0913f |
| eval/metrics.py | e11f489bdfb9275dedc8122f0d865bf670f524fb26d002e2efb04098f755dbe8 |
| tests/test_provenance.py | bdc759fe6de5c703e10b2723d139add4810cd3a7533e03ed1648a7ab343600dd |

---

## Verified Acceptance Criteria (All Closed)

### 1. No-Provenance Bypass Closed (4 tests)
| Case | Result |
|------|--------|
| Missing `meta` entirely | ✅ Rejected: "controlled QA requires nonempty source_articles" |
| Empty `meta: {}` | ✅ Rejected: "controlled QA requires nonempty source_articles" |
| Group-only without sources | ✅ Rejected: "controlled QA requires nonempty source_articles" |
| Sources-only without group | ✅ Rejected: "controlled QA requires an explicit group" |

### 2. Invalid Types/Empty/Unknown/Ambiguous Sources Rejected (7 tests)
| Case | Result |
|------|--------|
| `source_articles` not a list | ✅ Rejected |
| Empty `source_articles: []` | ✅ Rejected |
| Empty string source | ✅ Rejected |
| Non-string source | ✅ Rejected |
| Unknown source title | ✅ Rejected: "unknown source article" |
| Ambiguous title (2+ matches) | ✅ Rejected: "ambiguous source article" |
| Canonical node ID accepted | ✅ Passes, resolves to correct node |

### 3. Valid Public Reference Dev-Only + Train/Heldout Rejected + Unknown Not Zero (7 tests)
| Case | Result |
|------|--------|
| Valid `public_reference` on dev | ✅ Accepted, `ground_truth: "unknown"` |
| `public_reference` on train | ✅ Rejected: "public_reference allowed only on dev, not train" |
| `public_reference` on heldout | ✅ Rejected: "public_reference allowed only on dev, not heldout" |
| Missing `source_benchmark`/`source_revision`/`original_question_id` | ✅ Rejected |
| No `source_articles` → `ground_truth: "unknown"` | ✅ Not zero |
| Unresolvable `source_articles` → `ground_truth: "unknown"` | ✅ Not zero |
| Resolvable `source_articles` → `ground_truth: "known"` | ✅ |
| Unknown category | ✅ Rejected |

### 4. Shared Corpus Multi-Split + Secrecy (2 tests)
- ✅ Same corpus article set validates train/dev/heldout QA alike
- ✅ Resolution never filters corpus by split
- ✅ Error text carries only question IDs/counts — never question text, group names, or label content

### 5. Seeded Derivation + Corroboration (2 tests)
- ✅ `assign_split(group_key, split_seed)` enforced; declared split must match
- ✅ Node `meta.split_group` corroboration in seeded-hash mode without map
- ✅ Explicit group claim stands; derived split decides pass/fail

### 6. Canonical ID + Inconsistency + Cross-Split + Wrong Split + Valid Heldout (6 tests)
| Case | Result |
|------|--------|
| Canonical node ID (`a2`) accepted | ✅ |
| Title alias (`Beta`) normalized to `a2` | ✅ |
| Inconsistent group metadata rejected | ✅ "inconsistent group metadata" |
| Cross-split multihop rejected | ✅ "source articles span multiple splits" |
| Wrong declared split rejected | ✅ "declared split X != source group split Y" |
| Valid controlled (heldout) accepted | ✅ `ground_truth: "known"` |

---

## Manifest Integration Verified

**`validate_freeze` → `validate_question_provenance` integration (manifest.py:402-417)**:
- Called after corpus load and split-map validation
- Receives `corpus_nodes` for `build_article_index`
- Receives `map_groups` / `article_to_group` from split-map validation
- Uses `split_seed` and `use_map_splits` from manifest
- Gaps prefixed with `"qa provenance: "` added to freeze gaps
- No real held-out labels ever parsed; seal mechanics synthetic-only

**Freeze test results**:
- ✅ Valid group-map provenance → QA provenance gaps empty
- ✅ Missing provenance → "qa provenance: q1: controlled QA requires nonempty source_articles"
- ✅ Malformed questions/split-map → structured gaps, never crashes

---

## Recorded Pilot Limitation

**Same-split multihop across different groups rejected by one-group restriction**:

```python
# Two articles in SAME split (train) but DIFFERENT groups (g-train-A, g-train-B)
# Question uses both sources, claims g-train-A
# Result: REJECTED — "source articles span multiple splits ['train']"
```

This is a **design tradeoff**, not a bug: the one-group restriction prevents cross-split leakage but also rejects legitimate same-split cross-group retrieval. Recorded as pilot limitation per orchestrator guidance; does not block freeze unless contract claims are made that require it.

---

## Distinction Maintained

| Aspect | Status |
|--------|--------|
| Provenance source assignment (QA metadata) | ✅ Enforced at freeze |
| Actual evidence-label correctness | ⏳ Later custodian responsibility (held-out labels) |
| Real sealed labels access | ❌ Never parsed (procedural custody) |
| Actual QA creation | ⏳ Later step (not substrate scope) |
| Generator reruns | ⏳ Generator v3 independent PASS captured separately |

---

## Round 0 Freeze Status

**NOT GRANTED** — provenance gate is closed, but blockers remain:
1. No `corpus/corpus.jsonl` (pilot fetch ongoing)
2. No `corpus/questions.json` (later QA worker step)
3. No `corpus/heldout_labels.sealed.json` (orchestrator custody)
4. Independent re-review of this repair (orchestrator decision)
5. Same-user procedural custody stands (documented, not solved)

The substrate code is **freeze-ready** for the provenance gate; artifacts are external dependencies.