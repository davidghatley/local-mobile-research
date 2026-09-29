# Substrate Repair Report (Round 0 v0.2)

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested spawning. Scope: `substrate/`, `eval/`,
`tests/`, `pyproject.toml`, `docs/experimental-contract.md` (v0.2), this file.
No corpus QA/heldout creation, no architecture code, no other-worker files
modified.

Verdict under repair: `docs/substrate-implementation-review.md`
(**REPAIR REQUIRED**, reviewer `opencode/nemotron-3-ultra-free`). Reviewer
reproductions were re-verified against the v0.1 code before repair (all
confirmed: fake freeze passed, logits crashed/misled ECE, negative latencies
accepted, `is_pinned()` true with unspecified quantization). Reviewer
recommendations containing errors were NOT followed literally; orchestrator
clarifications govern (see Disposition column).

Test result: `python3 -m unittest discover -s tests` → **88 tests, all
passing** (34 carried over incl. updates, 54 new). All fixtures synthetic,
labeled SYNTHETIC/infra-only. Full per-test output preserved in §5.

## 1. Disposition of reviewer findings

| # | Finding | Disposition | Repair (file) |
| --- | --- | --- | --- |
| 1 | Fake freeze acceptance | ACCEPTED | `manifest.validate_freeze` recomputes corpus hash from content (+ hierarchy), per-file code hashes, generator artifact bytes + sha256 from disk, manifest↔disk config equality, prompt-hash pin, placeholder/stub rejection |
| 2 | Survival assumes irreversibility | QUALIFIED (orchestrator): lineage stays uninterrupted AND recovery tracked separately | `survival_curve` kept with lineage docstring; added `stage_coverage`, `conditional_retention` (numerator/denominator, None when undefined), `lost_and_recovered`; reviewer-proposed float-rate `survival_curve` rejected (would conflate lineage with recovery) |
| 3 | ECE/Brier accept logits | ACCEPTED + QUALIFIED: strict [0,1]+binary validation; NO sigmoid helper (sigmoid alone is not calibration); raw logits legal elsewhere iff `score_kind` explicit | `metrics._validate_prob_inputs`; `types.validate_score_value`, `SCORE_KINDS`; `Candidate.score_kind`, `StageRecord.score_kind` |
| 4 | Trace validation structural only | ACCEPTED | 26-field schema + semantic checks (non-neg latencies, score-domain, threshold-domain, prompt pin, stub/estimate/unknown-citation rejection); unmeasured = explicit null |
| 5 | `is_pinned()` allows unspecified | ACCEPTED | Full-contract `GeneratorConfig` (file, artifact bytes/sha256, tokenizer_id, sampling, runtime, quantization); `unpinned_fields()`; freeze enforces |
| 6 | Whitespace token budgets | ACCEPTED + QUALIFIED (orchestrator): exact-tokenizer callable governs empirical runs; estimates retained labeled infra-only | `serialize_evidence` canonical; `build_packet(..., tokenizer, tokenizer_id, exact)`; `exact=True` raises without tokenizer; packet carries method + exact/whole-prompt counts |
| 7 | Single required set | QUALIFIED (orchestrator): recall PRESERVED; separate completion metric; canonical ids across routes | `recall_at_k` unchanged; new `sufficient_set_completion` (never named recall); canonical-id rule in types docstring |
| 8 | Custodian procedural only | QUALIFIED (orchestrator): stays procedural, no pretend isolation; + opaque integrity | `verify_seal_opaque` / `seal_hash` (bytes hashed, never parsed/printed); expected-hash check on load; limitation restated |
| 9 | Missing trace fields | ACCEPTED (master-prompt fields, not draft-criteria extras) | run_id/architecture/seed/score_kind/adaptive/model-load/inference/RSS/storage/grader/available-citations/token-method |
| 10 | Code hashes unverified | ACCEPTED | Per-file recompute; missing = gap |
| 11 | Prompt hash unvalidated | ACCEPTED | Freeze asserts `prompt_hash == PROMPT_HASH` |
| 12 | Single seed | OVERRIDDEN (orchestrator): one master seed OK | `derive_seed`/`derive_seeds` + manifest log + consistency check; no invented multi-seed table |
| 13 | Thresholds lack metadata | ACCEPTED (as ThresholdPolicy) | `ThresholdPolicy{threshold, interpretation, top_k, min_breadth, calibration_method, score_kind}` + `validate()`; probability thresholds require fitted calibration |
| 14 | No load/inference split | ACCEPTED (caller-side phases) | `timed_phase(phase)`; `timed_stage` kept as labeled wrapper; schema fields per stage + outcome |
| 15 | Stub exclusion documentary | ACCEPTED | `STUB_GENERATOR_IDS` + `is_stub_generator`; trace + freeze reject (infra opt-in flags) |
| — | `compound_survival` product | REMOVED (orchestrator: never product of unconditional marginals) | Deleted; direct cumulative coverage instead; breaking change documented in contract §8 |
| — | `hash_paths` silent skip | Fail-closed | Raises FileNotFoundError on missing |
| — | Telemetry scope/units | Clarified | `MemoryReading` scope/unit/source; `proc_rss_mb(pid)` for server subprocess, distinct from client; `storage_manifest` roles |

Draft `docs/round0-review-criteria.md` was read for context but treated as
non-binding per orchestrator (it is under separate correction).

## 2. Compatibility verification (not modified: generator worker scope)

- `import generator_runtime.qwen25_adapter` → clean (`import ok`).
- Generator worker's smoke script executed against this substrate during
  verification and produced a normal trace (their script ran a model-backed
  smoke; substrate API calls compatible: `build_packet`, `estimate_tokens`,
  `from_dict` superset tolerance, `render_prompt`, `PROMPT_HASH` all intact).
- One incidental side effect to disclose: probing their smoke script with
  `--help` executed a smoke run; a `generator_runtime/smoke_trace_v2_*` file
  stamped in that minute may be mine, not theirs. No content of theirs was
  edited.
- HANDOFF: on-disk `corpus/generator_config.json` lacks `tokenizer_id`, so
  `GeneratorConfig.from_dict(...).is_pinned()` now (correctly) returns False
  with `unpinned_fields() == ['tokenizer_id']`. Their concurrent repair is
  expected to add it (their adapter already measures exact tokens).

## 3. Repaired list (v0.2 deliverables)

- `substrate/types.py`: score-domain vocabulary, `ThresholdPolicy`,
  canonical-id rule, exact/whole-prompt token fields, available-vs-emitted
  citation model, `HopRecord`, phase latencies, `is_stub_generator`,
  strict `from_dict` required-field checks.
- `substrate/evidence.py`: canonical `serialize_evidence`, tokenizer-callable
  exact budgets (`exact=True` fail-closed), `find_unknown_citations`.
- `substrate/generator.py`: full-contract `GeneratorConfig` + strict
  `is_pinned()`/`unpinned_fields()` + superset-tolerant `from_dict`;
  `render_prompt` via canonical serializer.
- `substrate/manifest.py`: recomputing fail-closed `validate_freeze`;
  master-seed derivation + log; strict `hash_paths`.
- `substrate/splits.py`: opaque seal verification, question-file validation
  (no label contact), expected-hash load check.
- `substrate/corpus.py`: strict loaders (`load_corpus_file`,
  `hash_corpus_file`).
- `substrate/telemetry.py`: scoped memory readings, subprocess RSS,
  `timed_phase`, categorized storage manifest.
- `eval/metrics.py`: preserved recall family; new completion/coverage/
  retention/lost-recovered/Wilson vocabulary; hardened calibration;
  `compound_survival` removed.
- `eval/run_format.py`: 26-field semantic trace validation, fail-closed.
- `tests/`: 88 tests (updated `test_metrics`/`test_contract`; new
  `test_freeze_adversarial` 12 tests, `test_semantics_adversarial` 23 tests).
- `docs/experimental-contract.md` v0.2 (repairs, API-change table, gaps,
  freeze steps). `pyproject.toml` 0.2.0.

## 4. Unresolved blockers (external; freeze still NOT granted)

1. No `corpus/corpus.jsonl` (pilot build running; other worker).
2. No `corpus/questions.json` (later step).
3. No `corpus/heldout_labels.sealed.json` (orchestrator custody; never inspected here — this repair verified seal mechanics on SYNTHETIC tmp files only).
4. Generator disk config missing `tokenizer_id` (generator worker concurrent repair; §2 handoff).
5. Independent re-review of THESE repairs (orchestrator decision).
6. Same-user sealing limitation stands (procedural; documented, not solved).

## 5. Actual test output (verbatim tail; full list above in session)

```
Ran 88 tests in 0.020s

OK
```

Representative adversarial proofs (all `ok` above):
`test_wrong_manifest_corpus_hash_fails`, `test_fake_code_hash_fails`,
`test_tampered_artifact_fails`, `test_seal_tamper_fails_without_reading_labels`,
`test_logits_rejected_ece/brier`, `test_lineage_is_uninterrupted` +
`test_stage_coverage_recovers`, `test_conditional_retention_undefined_not_zero`,
`test_exact_requires_tokenizer`, `test_trace_rejects_unknown_citations`,
`test_probability_policy_needs_fitted_calibration`.
One self-caught failure during development (synthetic exact-token arithmetic
in a new test expectation, 2×600>1000 cap) was fixed in the test, not the
implementation; final run is green.
