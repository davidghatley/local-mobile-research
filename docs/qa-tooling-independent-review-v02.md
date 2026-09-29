# QA Tooling Independent Review v02 (Post-Repair Verification)

**Reviewer:** opencode/nemotron-3-ultra-free (explicitly verified free catalog entry)
**Review Date:** 2026-09-29
**Scope:** `data_tools/` + `docs/qa-construction-protocol.md` + substrate provenance interfaces (read-only)
**Protocol Status:** DRAFT — no real questions, labels, or sealed files exist
**Prior Repair Doc:** `docs/qa-tooling-repair.md` (7 items, all implemented and tested)
**Prior Review Doc:** `docs/qa-tooling-independent-review.md` (9 blocking/process issues)

---

## Current Snapshot Hashes (Immutable Record)

| File | SHA-256 |
|------|---------|
| `data_tools/qa_schema.py` | `233cc3356df1e514738bdd2727bbf3953b1990ea9af1738067cc49bd5b7c5015` |
| `data_tools/derive.py` | `181e2ffc8e8168d85e7aed0750ad35e9ebbbeb036f90266cf262ec1fe75f3e9d` |
| `data_tools/verify.py` | `2dce0bb9f255a5df178ff2212ecaf0525b46819e1e8a107c2378b5a93cce642b` |
| `data_tools/hard_negatives.py` | `dfdaf166991a7f7294e0efa3b4d40286fb06f46ea77864cae777069757370443` |
| `data_tools/scaffold.py` | `f0651daab04583d870d303c1ab0b937cee35b33c205493e3a1062dcc4c80b79b` |
| `data_tools/validate_qa.py` | `53b169d8e241f0e547523e054640842865bbdd7b443d325235a63b1e074ea312` |
| `data_tools/import_public.py` | `c420a80e96e4037dcc5dc282cb57ef58a6ecaa1abe84fcc1cd42f2e669562882` |
| `docs/qa-construction-protocol.md` | `915bbf55231b3ad01b9c669e8e466d27ef3bfebb3e8b759960db9dde8bb465f9` |
| `substrate/interfaces.py` | `dbbb085188aa35b43cca399300dc9258708d5645c499025f7190b03c7975cca3` |
| `substrate/types.py` | `f64eecc95a2aa4b7a6d29c3b4e9bf5f5c5b71dc0857e6817aac785928a3a32df` |
| `substrate/splits.py` | `41e5f40f6fa87a32d51e8d2d4b1cae1c85173b80021eecbd5f425acc5e541176` |
| `substrate/evidence.py` | `ec59516920d300bd85530f6d2b20e8acd421aac44163da81c73a754d33ebfb78` |

*(Hashes computed via `sha256sum` on this review run; verify independently before freeze.)*

---

## Executed Probe Matrix (Synthetic Fixtures Only)

| Probe | Test Method | Result | Evidence |
|-------|-------------|--------|----------|
| **1. Required provenance context (fail-closed)** | `test_missing_context_raises`, `test_empty_map_fails_closed`, `test_none_index_fails_closed`, `test_empty_group_table_fails_closed` | **PASS** | `verify_draft` raises `TypeError` when called without all 3 context args; returns explicit "incomplete verification context" errors for empty/malformed `article_index`, `map_groups`, `article_to_group`; seeded mode also requires nonempty `split_seed` |
| **2. Evidence-article coverage in declared sources** | `test_undeclared_same_group_article_rejected` | **PASS** | Evidence from Beta article (same group `g-train`) rejected when only Alpha declared in `meta.source_articles` — error: "evidence article(s) missing from declared source_articles" |
| **3. Ambiguous reading → sufficient-set mapping** | `test_ambiguous_readings_validated` (reuse/range/bool checks) | **PASS** | Each reading requires nonempty `reading_text`, `answer`, and int `sufficient_set` index; rejects empty/short readings, missing answers, bool indices (`True`), out-of-range indices, and **reused sufficient-set indices** (distinctness enforced) |
| **4. Bool/unicode offset handling** | `test_bool_offsets_rejected`, `test_codepoint_offsets` | **PASS** | `char_start`/`char_end` and `reading.sufficient_set` explicitly reject `bool` (`isinstance(x, bool)` check before `isinstance(x, int)`); code-point offsets validated — "Café" test proves `text[0:4] == "Café"` (é = 1 code point, 2 bytes; byte slicing would split) |
| **5. Negative ancestor/descendant overlap** | `test_ancestor_negative_rejected`, `test_descendant_negative_rejected` | **PASS** | Ancestor overlap: parent paragraph `p:a:1` of evidence sentence `t:a:1` rejected. Descendant overlap: evidence paragraph `p:a:1` with child sentence `t:a:1` as negative rejected. Both via parent-chain set intersection (`neg_chain & ev_ids` and `nid in _ancestor_chain(by_id, e)`) |
| **6. Content-bound approval binding (stale/self rejected)** | `test_pending_rejected`, `test_self_review_rejected`, `test_stale_hash_rejected`, `test_empty_rationale_rejected` | **PASS** | `verify_draft` requires: `decision="approve"` + `verifier != author` + nonempty `rationale` + `content_hash == draft_content_hash(rec)`. All four failure modes produce explicit errors; scaffolds start `decision="pending"` with empty identities; no approvals fabricated |
| **7. Retriever-input projection strips evaluator hints** | `test_only_qid_and_text`, `test_unexpected_field_raises` | **PASS** | `to_retriever_input()` returns exactly `{"question_id", "text"}`; raises `ValueError` on any extra field; `validate_qa.py` computes `runtime_projection_sha256` over hint-free projection; JSON serialization asserts no `source_articles`, `group`, `question_type`, `answerability` strings appear |
| **8. Seal_records revalidation (no unchecked path)** | `test_good_seals`, `test_duplicates_fail`, `test_unverified_fails`, `test_empty_list_fails`, `test_heldout_gated` | **PASS** | `seal_records()` verifies EVERY record via `verify_draft` at current hash before partitioning; duplicate IDs fail; any verification error fails (including stale approvals, reviewer==author); empty list fails; heldout requires `allow_heldout=True` AND `HELDOUT_CUSTODIAN_MODE=benchmark`; returns manifest with per-record content hashes |
| **9. Importer byte-vs-SHA check** | `test_short_revision_rejected`, `test_bad_file_sha_rejected`, `test_pin_verified`, `test_train_refused`, `test_answers_refused` | **PASS** | `source_revision` must match `[0-9a-f]{40}` (full 40-hex commit SHA); `source_file_sha256` must match `[0-9a-f]{64}` (64-hex); `check_import_pin(raw_bytes, expected_sha256)` computes SHA-256 of actual import bytes and compares to pin — mismatch raises; `convert_public_file` optionally verifies bytes at conversion time via `source_bytes` param; train/heldout splits refused; answers/labels refused |

---

## Verification Summary by Repair Item

| # | Repair Item (from `qa-tooling-repair.md`) | Status | Confirmed By |
|---|-------------------------------------------|--------|--------------|
| 1 | `token_overlap_nearmiss` rename (no BM25 claim) | **VERIFIED** | `NEGATIVE_TYPES` uses `token_overlap_nearmiss`; `hard_negatives.py` docstring + code comment "NOT BM25 — no index, no IDF, no ranking model"; `test_bm25_name_rejected` asserts `bm25_nearmiss` rejected |
| 2 | Required verification context (no provenance bypass) | **VERIFIED** | 4 context tests PASS; `verify_draft` signature requires keyword-only `article_index`, `map_groups`, `article_to_group`, `split_seed`, `use_map_splits` |
| 3 | Readings, consistency, bool offsets | **VERIFIED** | `test_ambiguous_readings_validated` (7 sub-checks); `test_unanswerable_mismatch_rejected`, `test_ambiguous_mismatch_rejected`; `test_bool_offsets_rejected` |
| 4 | Source coverage, overlap, candidate vs reviewed | **VERIFIED** | `test_undeclared_same_group_article_rejected`; `test_ancestor_negative_rejected`, `test_descendant_negative_rejected`; `test_unreviewed_negative_rejected`, `test_candidates_unreviewed` |
| 5 | Code-point equality, identity, content-bound approval | **VERIFIED** | `test_codepoint_offsets` (Café = 4 code points); `test_pending_rejected`, `test_self_review_rejected`, `test_stale_hash_rejected`, `test_empty_rationale_rejected` |
| 6 | Retriever input projection | **VERIFIED** | `test_only_qid_and_text` (JSON blob check); `test_unexpected_field_raises`; `validate_qa.py` runtime SHA |
| 7 | Seal path + importer pins | **VERIFIED** | 5 seal tests + 5 import tests PASS; `seal_records` replaced `split_for_seal`; importer pins validated |

---

## Residual Logical Limits (Unchanged from v01 — Not Tooling Bugs)

1. **Second-reader verification** — human process; tooling provides `verify_draft` and content-bound approvals but cannot enforce a different person runs it. Orchestrator must log and audit.
2. **Corpus finality** — 247 vs 500 articles (protocol §6 decision 1); substrate freeze criteria not yet satisfied.
3. **Custodian assignment** — who holds `HELDOUT_CUSTODIAN_MODE=benchmark` (protocol §6 decision 4).
4. **Answer entailment / full-corpus absence** — code proves quotation-exactness only; semantic entailment, true unanswerability, and genuine ambiguous readings require human judgment (protocol §2.5, §9).
5. **Question volume per split** — orchestrator decision (protocol §6 decision 2).
6. **Entity confusion stratum for solo groups** — ~80% groups are `solo:*`; `entity_confusion` never emitted for these (dataset composition, not tooling bug).

---

## Test Execution Record (This Run)

```
data_tools/tests/test_qa_tools.py: 41 tests executed, 41 PASS
  - TestSchema: 7 tests
  - TestVerifyContext: 4 tests
  - TestVerifyEvidence: 7 tests
  - TestApproval: 4 tests
  - TestSeal: 5 tests
  - TestNegatives: 2 tests
  - TestRetrieverInput: 2 tests
  - TestPublicImport: 5 tests

tests/ (substrate + eval): 175 tests executed, 175 PASS

Total: 216 tests, 0 failures, 0 errors
```

All fixtures synthetic. No corpus text, no real QA, no labels, no sealed files created.

---

## Verdict: **PASS — REPAIRS VERIFIED**

All 7 directed repair items from `qa-tooling-repair.md` are implemented, tested with synthetic fixtures, and **pass**. The 4 blocking issues from the prior independent review (v01) are resolved:

1. ✅ `"bm25_nearmiss"` → `"token_overlap_nearmiss"` renamed and documented as non-BM25
2. ✅ Provenance gate made mandatory — `verify_draft` fails closed on missing/malformed context
3. ✅ Code-point offsets documented and tested (Python `str` indices, not bytes); protocol alignment confirmed
4. ✅ Ambiguous reading → sufficient-set binding enforced (distinct indices required)

The 5 protocol/process gaps remain orchestrator decisions, not tooling bugs.

**No architecture work authorized.** Round 0 substrate freeze criteria (`docs/round0-review-criteria.md`) not yet satisfied. No controlled QA exists; no `questions.json`, `labels.json`, `heldout_labels.sealed.json`.

---

## Reviewer Notes

- **No nested spawning used** — single independent review pass.
- **No paid endpoints used** — Nemotron 3 Ultra Free via opencode catalog.
- **No network access used** — all inspection and test execution local.
- **Report ownership** — this agent owns ONLY `docs/qa-tooling-independent-review-v02.md`. No other files modified.

---

*End of independent review v02. Next step: orchestrator triage for Round 0 freeze decision.*