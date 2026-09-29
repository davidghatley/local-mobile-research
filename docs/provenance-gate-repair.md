# Provenance Gate Repair (Decision A+B)

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested agents. Scope: `substrate/splits.py`
(`validate_question_provenance`, `build_article_index`, category constants;
`validate_group_map` gains `article_to_group`), necessary types/manifest
question-validation integration (manifest calls the new validator; no
generator/prompt changes), `tests/test_provenance.py` (new, 28 tests) +
updated fixtures (`FixtureRoot` explicit provenance, `align_questions`
pool-search, group-map question fixtures), `docs/experimental-contract.md`
§3, this file. No real questions/labels created; corpus owned separately;
no architecture implementation.

Verdict under repair: `docs/substrate-implementation-review-v03.md`
(REPAIR REQUIRED on one design point only — prior P0s verified closed).
Decision A+B implemented literally:

- Controlled train/dev/heldout QA MUST carry nonempty explicit
  `meta.source_articles` (canonical node ids, or pilot titles with
  unambiguous resolution) AND `meta.group`. Group-only is insufficient:
  every source resolves to a real corpus article node and must belong to the
  claimed group. Unknown/ambiguous sources, unknown groups, missing sources,
  missing groups, inconsistent group metadata, cross-split source sets, and
  declared/group split mismatches are all rejected. No implicit exemption:
  absent meta fails in both split modes.
- Group resolution: split-map membership (group-map mode) or corpus node
  `meta.split_group` corroboration with deterministic `assign_split`
  derivation (seeded-hash mode); unresolvable groups fail. Seeded mode
  without map or node metadata still requires explicit sources + group;
  sources must resolve to real nodes (no dangling references).
- `public_reference` (`meta.category`): dev only (train/heldout rejected);
  requires `source_benchmark` + `source_revision` + `original_question_id`;
  `source_articles` optional and best-effort — absent/unresolvable means
  ground truth UNKNOWN (`results[qid].ground_truth`), never zero
  (`sufficient_set_completion` already returns None for empty sets).
- Corpus shared across splits: resolution never filters by split (test:
  train/dev/heldout QA validate against one article set).
- Result interface preserves separation:
  `results[qid] = {category, group, split, sources, ground_truth}`.
- Synthetic fixtures carry explicit provenance (no broad bypass):
  `FixtureRoot.align_questions` pool-searches group keys so derived group
  splits match declared splits; group-map fixtures declare map-consistent
  questions; `qb` exercises canonical node-id resolution.
- Removed `validate_qa_group_consistency` (lenient skip semantics contradict
  the mandate); breaking change recorded here. Error text: question ids and
  counts only (test asserts planted question text appears in no error).

Test result: `python3 -m unittest discover -s tests` → **175 tests, all
passing** (147 before; +28 `test_provenance.py`). Acceptance mapping:
no-provenance/group-only bypass closed (4 tests), invalid
types/empty/unknown/ambiguous sources rejected (7 tests), valid public dev
accepted + train/heldout/missing-fields rejected + unknown-not-zero (7
tests), shared-corpus multi-split + secrecy (2 tests), seeded derivation +
corroboration (2 tests), canonical-id + inconsistency + cross-split +
wrong-split + valid-heldout (6 tests).

Remaining blockers (freeze NOT granted): no `corpus/corpus.jsonl` (fetch
ongoing, not polled), no `corpus/questions.json`, no sealed labels
(orchestrator custody; seal mechanics synthetic-only), independent re-review
of this repair (orchestrator), same-user procedural custody stands.
Generator/prompt untouched.
