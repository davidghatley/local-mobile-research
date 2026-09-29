# QA Tooling Repair (orchestrator-directed, 7 items)

Status: **REPAIR IMPLEMENTED, TESTED — NOT APPROVED.** This document records
the disposition of each directed fix with exact code locations and test
evidence. Reviewer acceptance is a separate, later step. No real questions,
labels, or sealed files were created. Corpus remains provisional (247/500,
awaiting owner audit).

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested spawning. Stdlib only — no new
dependencies. Scope: `data_tools/`, this document,
`docs/qa-construction-protocol.md`. No other paths modified.

## 1. token_overlap_nearmiss rename (no BM25 claim)

- `NEGATIVE_TYPES` in `data_tools/qa_schema.py:24-31` uses
  `token_overlap_nearmiss`; `bm25_nearmiss` is rejected as
  `bad negative_type` (tested).
- `data_tools/hard_negatives.py:8-10,123-124` documents the miner output as
  a stdlib token-overlap lexical proxy with an explicit "NOT BM25 — no
  index, no IDF, no ranking model" statement.
- Protocol §2.6 repeats the non-BM25 status. Other owners' docs
  (`round0-review-criteria.md`, `reference-audit.md`) still mention BM25 in
  their own scope and were NOT touched.

## 2. Required verification context (no provenance bypass)

- `verify_draft` (`data_tools/verify.py`) takes `article_index`,
  `map_groups`, `article_to_group` as REQUIRED keyword arguments: omission
  raises `TypeError` (tested). Empty/malformed context (missing `by_id` /
  `by_title`, empty map or group table, empty seed in seeded mode) returns
  explicit `incomplete verification context (...)` errors — fail closed,
  never skipped (tested: 4 tests).
- All synthetic tests pass explicit context via the `ctx()` helper; the
  no-context call is itself a test asserting `TypeError`.

## 3. Readings, consistency, bool offsets

- Ambiguous readings (`data_tools/qa_schema.py`): each reading requires
  nonempty `reading_text`, nonempty `answer`, and an int `sufficient_set`
  index that is in range and DISTINCT across readings (all referenced sets
  pass the same span/provenance checks in `verify_draft`). Single/empty/
  malformed/out-of-range/reused-index/bool-index readings rejected (tested).
- Consistency: `question_type` unanswerable ⟺ `labels.answerability`
  unanswerable, and ambiguous ⟺ ambiguous; mismatches rejected in both
  directions (tested).
- Bool offsets: `char_start`/`char_end` (and reading `sufficient_set`)
  reject `bool` explicitly (`True == 1` would otherwise pass `isinstance`
  int checks), in schema AND in `verify_draft` (tested).

## 4. Source coverage, overlap, candidate vs reviewed

- Source coverage (`data_tools/verify.py:_resolve_source` + check):
  declared sources resolve to canonical article ids (direct id or unique
  title match; unknown/ambiguous rejected); EVERY evidence span's article
  must be in the declared set — same group alone fails (tested:
  same-group-but-undeclared Beta article rejected).
- Negative overlap: identity OR ancestor (negative contains evidence) OR
  descendant (negative contained in evidence) via parent-chain comparison;
  all three rejected (tested: parent-paragraph and child-sentence cases).
- Candidates vs reviewed: miner emits `reviewed=False` candidates;
  schema requires the `reviewed` bool; verification requires `True`
  (human-confirmed non-answering). Unreviewed negatives fail (tested).
  Non-answering status is a recorded human claim, documented as such in
  protocol §9 — lexical mining never establishes it.

## 5. Code-point equality, identity, content-bound approval

- Offsets documented and tested as Python-str code points (NOT bytes):
  a `Café` test proves `text[0:4] == "Café"` (byte slicing would split
  é). Docs state equality is quotation-exactness, never semantic
  entailment (protocol §2.1, §9).
- Drafts carry `provenance{author, author_model, verifier, verifier_model,
  decision, rationale, content_hash}` (schema-required shape).
- `draft_content_hash` binds approvals to semantic contents (scaffolding
  and the approval block itself excluded). `verify_draft` requires
  `decision=approve` + `verifier != author` + nonempty rationale + hash
  match; pending/self/stale/rationale-free approvals fail (tested: 4
  tests). No approval is fabricated anywhere: scaffolds start
  `decision=pending` with empty identities.
- `validate_qa.py` manifest reports an `approved` tally (content-hash
  rechecked, ids only).

## 6. Retriever input projection

- `to_retriever_input()` (`data_tools/qa_schema.py`) returns qid+text ONLY
  and raises on any unexpected field. `validate_qa.py` emits
  `runtime_projection_sha256` over the hint-free projection.
- Tests assert the runtime projection contains exactly
  `{question_id, text}` and that no group/source/type/answerability string
  appears in its serialization.
- Evaluator-private entries retain `meta` solely for the substrate
  provenance check; protocol §3–§4 forbid passing raw meta to
  architectures and forbid exposing held-out question/provenance files to
  dev builders.

## 7. Seal path + importer pins

- `split_for_seal` REMOVED; replaced by `seal_records()` which verifies
  EVERY record at its current hash before partitioning: duplicate ids
  fail, any verification error fails (missing/stale approvals,
  reviewer==author included), empty lists fail; heldout additionally needs
  `allow_heldout=True` + custodian env (tested: 5 tests). Returns a content
  manifest (ids/counts/per-record hashes) alongside the partition. There is
  no unchecked dict-splitting seal path.
- Custody honesty restated in `verify.py` docstring and protocol §3: same
  OS user ⇒ procedural custody only, no kernel boundary; true isolation =
  orchestrator withholds the sealed file.
- Importer (`data_tools/import_public.py`): `source_revision` must be a
  full 40-hex commit SHA; `source_file_sha256` must be 64-hex and is stored
  in entry meta; `check_import_pin` verifies exact input bytes against the
  pin (mismatch raises); `convert_public_file` optionally verifies bytes
  at conversion time (tested: short-SHA, bad-SHA, pin-mismatch, train,
  answers-carrying refusals).

## Test evidence

- `python3 -m unittest discover -s data_tools/tests` → **41 tests, all passing**.
- `python3 -m unittest discover -s tests` → **175 tests, all passing** (shared suite untouched).
- All fixtures synthetic; no corpus text, no real QA, no labels created.

## Unresolved logical limits (not claimed as solved)

See protocol §9: code proves quotation-exactness and gate behavior, not
answer correctness, sufficiency, true absence, undiscovered readings, or
reviewer diligence. `reviewed=True` and approvals are attributable human
claims (identity + rationale + content hash) designed for future audit,
not machine certificates of correctness.
