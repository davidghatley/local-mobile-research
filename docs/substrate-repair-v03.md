# Substrate Repair Report v0.3

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested agents. Scope: `substrate/`, `eval/`,
`tests/`, `docs/experimental-contract.md` (v0.3), this file. Generator v3
stable and owned elsewhere — no generator_runtime/config edits (read-only
verification only). No QA generation, architecture code, or benchmark runs.
Manifest/trace/types edits here are the assigned v0.3 repair (re-review of
the result is the orchestrator's separate step).

Verdict under repair: `docs/substrate-implementation-review-v02.md`
(**REPAIR REQUIRED**) plus raw probes `docs/reviewer-v02-probe-outputs.txt`
(TESTS 1–19). Reviewer errata are NOT followed literally where orchestrator
clarifications govern (see Disposition). Claims below are exactly as broad as
the listed evidence.

Test result: `python3 -m unittest discover -s tests` → **147 tests, all
passing** (119 before; +28 new in `tests/test_freeze_v03.py`; updated
expectations in `test_metrics`, `test_contract`, `test_semantics_adversarial`,
`test_freeze_adversarial` fixture). Per-file: contract 14, corpus 6,
evidence_packing 25, evidence 4, freeze_adversarial 12, freeze_v03 28,
metrics 22, semantics_adversarial 29, splits 7. All fixtures synthetic,
labeled SYNTHETIC/infra-only.

## 1. Disposition of reviewer-v02 findings

| # | Finding | Disposition | Repair |
| --- | --- | --- | --- |
| 1 | Questions content unhashed | ACCEPTED, generic mechanism | `RunManifest.questions_sha256` raw-byte pin + recompute in freeze; text change with same ids/splits now fails (test) |
| 2 | Generator disk compare incomplete | ACCEPTED as designed, not as field list: FULL raw config byte pin (`generator_config_sha256`) covers every field generically (license, download_url, verification, tokenizer detail, runtime_full, threads...); semantic compare extended only for acted-on fields (+generator_id, tokenizer_id, chat_template_sha256, context_window, sampling) | `manifest.py` raw-hash check + `GENERATOR_SEMANTIC_FIELDS`; whitespace-only and license-only mutations proven detected |
| 3 | Group-map path-only | ACCEPTED | `split_map_sha256` pin + `validate_group_map` (structure, non-empty complete assignments, per-article uniqueness ⇒ supervised disjointness, resolution vs real corpus article nodes via pilot-aligned `norm_title`) + `validate_qa_group_consistency` (meta.group / meta.source_articles; metadata-less questions skipped, no invented schema) |
| 4 | Trace weaker than policy | ACCEPTED with orchestrator correction (below) | `validate_trace` delegates to the ONE `ThresholdPolicy.validate()`; bare floats migrate fail-closed; policy/trace score_kind mismatch rejected; ranking-only stages must declare explicit policies |
| 5 | No runtime binary hashes | ACCEPTED, explicit external roles | `_runtime_declarations` parses config `runtime_binaries` (libs via soname_target, llama-server path); bytes hash-verified at declared paths incl. absolute out-of-tree (`external-runtime-*` roles); manifest `ArtifactPin` inventory must cover every declaration. Verified live against v3 config read-only: 9/9 resolve and match |
| 6 | Legacy float in trace | ACCEPTED via unification | Covered by #4 delegation (test: bare `0.7` rejected as unspecified) |
| 7–9 | Custodian procedural / missing corpus-QA / smoke | ACKNOWLEDGED, not code defects | No change (custody stays procedural by design; corpus fetch ongoing, not polled) |

Reviewer §"Round 0 vs architecture" incorporated: `manifest.phase`
(`round0-substrate` enforced); Round 0 records threshold-policy
DECLARATIONS, never learned fits (unfitted `model_probability` /
ranking-only declarations pass freeze; test proves).

## 2. Orchestrator findings from raw probes

- **(A) Unknown citations**: trace rejection REMOVED. Optional
  `citation_audit` {available, emitted, unknown} must satisfy
  unknown == emitted − available and match top-level fields; inconsistent /
  malformed audits rejected, unknowns themselves permitted as recorded model
  failures; failed answers preserved raw (test: hallucinating trace validates,
  response text intact). `allow_unknown_citations` kept as deprecated no-op.
- **(B) Completion binary**: `sufficient_set_completion` returns binary
  `completion` (1.0 any set fully covered / 0.0 / None without ground truth)
  plus separate `best_fractional_coverage`, `best_set_index`,
  `per_set_coverage`, `complete_sets`. Ordinary `recall_at_k` unchanged.
- **(C) `model_probability`**: new calibration state for natively
  probabilistic outputs — ECE/Brier-evaluable, dev-thresholdable, NO forced
  fitted calibration, but NOT a certified calibrated claim. Fitted methods
  require `calibration_partition` provenance. `none_ranking_only` /
  `unspecified` with probability interpretation still rejected (sigmoid alone
  is not calibration). Raw absolute/percentile thresholds legal with any
  score_kind. No duplicated validator logic (single implementation).

## 3. Robustness properties (tested)

- Malformed JSON/artifacts (questions, split map, generator config) yield
  structured gaps, never crashes (4 tests).
- Gap text carries ids/counts/hashes only: seal-tamper with planted secret
  label asserts the secret appears in no gap (test).
- Real held-out labels never parsed: seal path is bytes-only; QA checks use
  question metadata, never labels.
- Prompt/hash and fixed generator settings preserved: no prompt edit this
  round (`PROMPT_HASH` unchanged v0.2 value); v3 disk config reads
  `is_pinned() == True` under the extended schema (incl. new
  `chat_template_sha256` requirement).

## 4. Changed API (v0.2 → v0.3)

Breaking only where compat hides invalid data: binary `completion` (+
`best_fractional_coverage`); unknowns permitted in traces; see contract §8.
Additive: `ArtifactPin` + manifest pins/phase/inventory, `ThresholdPolicy.
calibration_partition`, `GeneratorConfig.chat_template_sha256`,
`validate_group_map`, `validate_qa_group_consistency`, `norm_title`,
optional `citation_audit`.

## 5. Remaining blockers (freeze NOT granted)

1. No `corpus/corpus.jsonl` (pilot fetch ongoing; not polled).
2. No `corpus/questions.json` (later step; no substrate QA generation).
3. No `corpus/heldout_labels.sealed.json` (orchestrator custody; seal
   mechanics proven on synthetic tmp files only — never real labels).
4. Independent re-review of THESE v0.3 repairs (orchestrator decision).
5. Same-user sealing limitation stands (procedural; documented, not solved).
