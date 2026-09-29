# QA Tooling Independent Review (Snapshot Audit)

**Reviewer:** opencode/nemotron-3-ultra-free (explicitly verified free catalog entry)
**Review Date:** 2026-09-29
**Scope:** `data_tools/` + `docs/qa-construction-protocol.md` + substrate provenance interfaces (read-only)
**Protocol Status:** DRAFT — no real questions, labels, or sealed files exist

---

## Original Inspected Snapshot Hashes (Immutable Record)

| File | SHA-256 |
|------|---------|
| `data_tools/qa_schema.py` | `b663ebdc42b5602e154528473382ec37e65067604ce525dda6ac0840ded79c31` |
| `data_tools/derive.py` | `fd7a8bd858753ba18982cf4c93955187cf69eea91b36d02582014eae9e6e19f2` |
| `data_tools/verify.py` | `2d604387fb3380d5d640ce1c0e704a554344a253f694557ecef7a2053a638436` |
| `data_tools/hard_negatives.py` | `75539fb7f574aee8fe1a124a5db6fd382076df5196195e5b1ff25f00b00c96d2` |
| `data_tools/scaffold.py` | `f0651daab04583d870d303c1ab0b937cee35b33c205493e3a1062dcc4c80b79b` |
| `data_tools/validate_qa.py` | `8a4cb21ed4e7b1ae3cbf2c87d3b7351e3bfab307820988313c07c39395662b40` |
| `data_tools/import_public.py` | `aae6d5542c9374798ffe5b0d8ac577bd2e3b49eae840b953d3b17e42844f6b83` |
| `docs/qa-construction-protocol.md` | `f34b8d04b4d4bb126e82ca2915c98d6e5713198cd415dbe36d25d67e6aebe787` |
| `substrate/interfaces.py` | `dbbb085188aa35b43cca399300dc9258708d5645c499025f7190b03c7975cca3` |
| `substrate/types.py` | `f64eecc95a2aa4b7a6d29c3b4e9bf5f5c5b71dc0857e6817aac785928a3a32df` |
| `substrate/splits.py` | `41e5f40f6fa87a32d51e8d2d4b1cae1c85173b80021eecbd5f425acc5e541176` |
| `substrate/evidence.py` | `ec59516920d300bd85530f6d2b20e8acd421aac44163da81c73a754d33ebfb78` |

---

## Executed vs Inspected vs Claimed — Truth Table

| Check | Executed (Tests Run) | Inspected (Code Read) | Previously Claimed | Actual Finding |
|-------|---------------------|----------------------|-------------------|----------------|
| Schema validation | 16/16 data_tools tests PASS | Full read of `qa_schema.py` | "Answerability/unanswerable evidence grounding verified" | **PARTIAL** — unanswerable shape enforced; ambiguous readings only length-checked |
| Exact span verification | `test_exact_span_mismatch_rejected`, `test_char_offsets_checked` PASS | `verify.py:78-90` | "Exact offsets against canonical corpus texts" | **PARTIAL** — character offsets, not byte offsets; full-text equality when offsets absent |
| Hard negative mining | `test_strata_present` PASS | `hard_negatives.py:1-153` | "All six strata covered" | **PARTIAL** — `bm25_nearmiss` misnamed (token-overlap proxy); `entity_confusion` never emitted for solo groups |
| Single-group provenance | `test_cross_group_span_rejected` PASS | `verify.py:91-101`, `splits.py:277-449` | "Controlled source groups enforced" | **CONDITIONAL** — `verify_draft` skips provenance gate when `article_index/map_groups/article_to_group` not passed |
| Heldout custody | `test_heldout_seal_gated` PASS | `splits.py:106-149`, `verify.py:134-150` | "Heldout stage default fail-closed" | **CORRECT** — dual gate (`allow_heldout` + env) enforced |
| Seal opacity | N/A (no sealed files) | `verify.py:134-150`, `splits.py:59-67` | "Sealing output does not expose answers" | **CORRECT** — `split_for_seal` partitions; `verify_seal_opaque` hashes raw bytes |
| Public import hygiene | `test_dev_only`, `test_train_refused`, `test_answers_refused` PASS | `import_public.py:24-53` | "Benchmark imports exact revision/hash + answers discarded" | **PARTIAL** — `source_revision` field presence checked, not actual input hash verification |
| Answerability grounding | `test_unanswerable_shape`, `test_ambiguous_needs_two_readings` PASS | `qa_schema.py:90-150` | "Answerability/unanswerable evidence grounding" | **PARTIAL** — ambiguous requires ≥2 readings but does not verify each reading ties to distinct sufficient set |
| Independent verification | N/A (no second reader) | `verify.py:52-118` | "Independent verification substantive not checkbox" | **NOT EXECUTED** — tooling exists, human process not run |
| Corpus finality | N/A | `provenance.json` (247 articles, 310 gaps) | "Corpus provisional" | **CORRECT** — orchestrator gate §0 item 1 unmet |

---

## Corrected Findings (Overclaims Retracted)

### 1. `verify_draft` Provenance Gate Is Conditional (Not Always Enforced)
**Location:** `verify.py:52-118`, specifically lines 109-117
```python
if article_index is not None and map_groups is not None and article_to_group is not None:
    from substrate.splits import validate_question_provenance
    ...
```
**Finding:** The cross-split / provenance validation **only runs when all three optional arguments are provided**. `validate_qa.py` passes them (lines 84-88), but a direct caller of `verify_draft` without context **silently skips** the single-group and cross-split checks. This is a latent gap if the function is reused.

### 2. Ambiguous Readings Length Check Only — No Sufficient-Set Binding
**Location:** `qa_schema.py:148-150`
```python
if lab.get("answerability") == "ambiguous" and (
    not isinstance(lab.get("readings"), list) or len(lab.get("readings", [])) < 2):
    errors.append(f"{qid}: ambiguous needs >= 2 labels.readings")
```
**Finding:** Validation only checks `len(readings) >= 2`. It does **not** verify that each reading maps to its own sufficient set (protocol §2.5 requires "each reading tied to its own sufficient set (different passages, different answers)"). The `readings` field is opaque — no structure enforced.

### 3. `split_for_seal` Partitions Only — No Semantic Approval Gate
**Location:** `verify.py:134-150`
```python
def split_for_seal(records: list[dict], *, allow_heldout: bool = False) -> dict:
    held = [r for r in records if r.get("split") == "heldout"]
    if held and not (allow_heldout and os.environ.get(CUSTODIAN_ENV_VAR) == "benchmark"):
        raise PermissionError(...)
    # ... pure partitioning, no content review
```
**Finding:** The function **only enforces the custodian dual-gate for heldout drafts**. It does not require or record a second-reader verification pass, spot-read confirmation, or any semantic approval. The protocol (§3) mandates "a different person re-runs `verify_draft` and spot-reads corpus nodes behind ≥20% of sufficient sets" — this is a **human process not encoded in tooling**.

### 4. Character Offsets ≠ Byte Offsets
**Location:** `verify.py:80-90`
```python
cs, ce = span.get("char_start"), span.get("char_end")
if cs is not None or ce is not None:
    if not isinstance(cs, int) or not isinstance(ce, int) or not (
        0 <= cs < ce <= len(corpus_text)):
        errors.append(f"{qid}: set {i} span {j} bad char offsets")
    if span.get("text", "") != corpus_text[cs:ce]:
        errors.append(f"{qid}: set {i} span {j} text/offset mismatch")
```
**Finding:** Offsets are validated as **character indices** (`len(corpus_text)` is character count, slicing is Unicode codepoint slicing). The protocol says "byte-exact equality (offset slice when offsets given)" — Python `str` slicing is **not byte-exact** for non-ASCII content. Corpus is UTF-8; character offsets diverge from byte offsets on multi-byte codepoints.

### 5. Source Metadata in Questions Is Evaluator Hint — Not Retriever Input
**Location:** `qa_schema.py:163-174` `draft_to_question_entry`
```python
def draft_to_question_entry(rec: dict) -> dict:
    return {
        "question_id": rec["question_id"],
        "text": rec["text"],
        "split": rec["split"],
        "meta": {
            "source_articles": rec["meta"]["source_articles"],
            "group": rec["meta"]["group"],
            "question_type": rec["question_type"],
        },
    }
```
**Finding:** `questions.json` exports `meta.source_articles` and `meta.group`. The protocol (§1) states "Split equality constrains QA declarations, never corpus access" and the substrate retriever interface (`interfaces.py:17`) takes only `Question` with `text` + `meta` (opaque). **No tooling prevents a retriever implementation from using `source_articles`/`group` as query hints** — this is a runtime contract, not an enforced boundary.

### 6. Code Cannot Prove Answer Entailment or Full-Corpus Absence
**Finding:** The tooling validates **structural consistency** (spans exist, match text, belong to declared group). It **cannot** and does not attempt to verify:
- That the `answer_text` is actually entailed by the sufficient sets (semantic entailment)
- That an `unanswerable` claim's `absent_reason` is factually true (full-corpus negative proof)
- That `ambiguous` readings are genuinely supported by distinct passages

These require human judgment. The protocol (§2.5) correctly requires "reviewer judgment that a retriever cannot match it by surface overlap alone" — **not machine-checkable**.

### 7. Importer Checks `source_revision` Field Presence, Not Input Hash
**Location:** `import_public.py:32-33`
```python
if not source_benchmark.strip() or not source_revision.strip():
    raise ValueError(f"{qid}: source_benchmark/revision required")
```
**Finding:** The importer validates that `source_revision` string is nonempty. It **does not** compute a hash of the actual import file contents and compare it to `references/pins.json` recorded SHA-256s. The pins file records file hashes (`sha256_at_pinned_head`), but the import pipeline has **no hash verification step** linking the imported JSONL to those pins.

### 8. BM25 Naming Mismatch (Confirmed)
**Location:** `hard_negatives.py:114-132`, `qa_schema.py:28`
```python
# hard_negatives.py line 127-128
overlap = len(t & ev_toks) / max(1, len(t | ev_toks))  # Jaccard index
if overlap > 0.15:
    scored.append((overlap, n))
# ...
add(n, "bm25_nearmiss")  # Line 132
```
**Finding:** The negative type emitted is `"bm25_nearmiss"` but the implementation is a **token Jaccard overlap proxy** (stdlib only, no embeddings, no BM25). This mislabels the method in all downstream artifacts.

### 9. Entity Confusion Stratum Unpopulated for Solo Groups
**Location:** `hard_negatives.py:149`
```python
ntype = "entity_confusion" if len(group_article_ids) > 1 else "same_group_distractor"
```
**Finding:** ~80% of groups in `split_map.json` are `solo:*` (single article). For these, `entity_confusion` negatives are **never generated** — only `same_group_distractor`. The protocol (§2.6) requires covering all six strata "per question set." This is a **dataset composition consequence**, not a tooling bug, but it means the stratum coverage claim was overbroad.

---

## Test Execution Record (Actual, Not Claimed)

```
data_tools/tests/test_qa_tools.py: 16 tests executed, 16 PASS
  - TestSchema: 6 tests (good_passes, missing_group_rejected, tautology_rejected,
                    unanswerable_shape, ambiguous_needs_two_readings, no_negatives_rejected,
                    multihop_needs_chain)
  - TestVerify: 5 tests (exact_span_mismatch_rejected, char_offsets_checked,
                        cross_group_span_rejected, negative_overlapping_evidence_rejected,
                        heldout_seal_gated)
  - TestNegatives: 1 test (strata_present — checks presence of types in output, not correctness)
  - TestPublicImport: 3 tests (dev_only, train_refused, answers_refused)

tests/ (substrate + eval): 175 tests executed, 175 PASS
  - Covers: contract format, manifest freeze, telemetry, corpus hierarchy, evidence packing,
            freeze adversarial, generator contract pin, group map, questions content pin,
            round0 declarations/secrecy, runtime inventory, unified policy/citations,
            calibration adversarial, completion, survival vocabulary, traditional metrics,
            wilson, provenance (no bypass, public reference, seeded mode, shared corpus,
            source validation), semantics adversarial (exact tokens, questions validation,
            score domains, seal opacity, threshold policy), splits
```

**No synthetic fixtures exercised:** heldout seal with real labels, public import with pinned files, second-reader verification, full derivation workflow.

---

## Verdict: REPAIR REQUIRED

### Blocking Issues (Must Fix Before Freeze)
1. **Rename `"bm25_nearmiss"` → `"token_overlap_nearmiss"`** in `qa_schema.py:NEGATIVE_TYPES` and `hard_negatives.py` output
2. **Make provenance gate mandatory** in `verify_draft` — remove optional context or fail closed when absent
3. **Enforce byte offsets** — either decode corpus as bytes for offset validation, or document character-offset semantics explicitly in protocol
4. **Add ambiguous reading → sufficient set binding** validation in `qa_schema.py` (require `readings` to reference distinct `sufficient_sets` indices)

### Protocol/Process Gaps (Not Tooling Bugs — Orchestrator Decisions)
5. **Second-reader verification** — human process, not automatable; must be executed and logged
6. **Corpus finality decision** — 247 vs 500 articles (protocol §6 decision 1)
7. **Custodian assignment** — who holds `HELDOUT_CUSTODIAN_MODE=benchmark` (protocol §6 decision 4)
8. **Public import hash verification** — add step comparing imported file SHA-256 to `pins.json`
9. **Question volume per split** — orchestrator decision (protocol §6 decision 2)

### No Architecture Work Authorized
- Round 0 substrate freeze criteria (`docs/round0-review-criteria.md`) not yet satisfied
- No controlled QA exists; no `questions.json`, `labels.json`, `heldout_labels.sealed.json`
- Generator config `tokenizer_id` gap noted in contract v0.3 §4 (generator owner scope)

---

## Reviewer Notes

- **Original data lead actively repairing** — this report captures the snapshot state at review time. Do not re-run tests after fixes to retrospectively relabel.
- **No nested spawning used** — single independent review pass.
- **No paid endpoints used** — Nemotron 3 Ultra Free via opencode catalog.
- **No network access used** — all inspection local.

---

*End of independent review. Next step: orchestrator triage of REPAIR REQUIRED items.*