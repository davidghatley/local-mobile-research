# Round 1 Common Training Contract

Status: Round 0 closure artifact (preregistered). Delivered IDENTICALLY to
every Round 1 architecture team. It defines what is shared, what each
worker may and may not access, and the gate synthetic training data must
pass. No architecture-specific content belongs here: architecture code
lives under `experiments/<architecture>/` and is out of scope until this
gate.

## 0. What is common (delivered identically to every team)

| Item | Value / location |
| --- | --- |
| Core corpus | `corpus/corpus.jsonl`, revision `pilot-297-r1` (297 articles); byte-pinned by `corpus/build_manifest.json`, `corpus/input_manifest.json`, `corpus/partition_census.json` |
| Scale tier | `corpus/scale/` — 940 articles in `tier_1k.json` (830 substantive after redirect-stub exclusion; see `docs/scale-method.md`) |
| Worker-visible questions | `corpus/questions.json` — 206 items: train 60 / dev 59 / shadow_dev 87 |
| Query interface | `substrate.query.QueryInput` = `{question_id, text}` via `to_model_query` — the ONLY sanctioned model-facing surface (blocker 5) |
| Fixed generator + prompt | `substrate.generator.FIXED_GENERATION_PROMPT`, `PROMPT_HASH`, `GeneratorConfig` pin (`model_id`, `revision`, `quantization`, `runtime`, `sampling`). Round 1 is a retrieval/evidence tournament, NOT a generator tournament: no per-benchmark prompt or generator tuning |
| Evidence budget | target band 300–800 evidence tokens (`TARGET_EVIDENCE_TOKENS_MIN/MAX`); hard cap 1000 (`HARD_EVIDENCE_TOKEN_CAP`, pilot preregistered) — `substrate/evidence.py` |
| Telemetry schema | `substrate.telemetry` + `substrate.types.StageRecord` / `RetrievalOutcome` / `HopRecord`. `None` = EXPLICITLY NOT MEASURED, never silent |
| Scoring protocol | `docs/scoring-protocol.md` (PREREGISTERED / FROZEN; never modified after private results are visible); scale-tier adjudication per `docs/scale-evaluation-rule.md` |
| Dev sets | train (60), dev (59), shadow_dev (87) as declared in `corpus/split_map.json` |
| Seed policy | one master seed; per-component seeds via `substrate.manifest.derive_seed` / `derive_seeds`; the derivation is logged in the run manifest |
| Regime B worker exclusion | the public 21-document superset, `corpus/regime_b_excluded_articles.json` (§3) |

## 1. Model-facing query interface (binding)

- Every query handed to a model — sufficiency controller, retriever,
  generator, adapter — must be a `substrate.query.QueryInput` with exactly
  two fields: `question_id`, `text` (allowlist: `MODEL_FACING_FIELDS`).
- `to_model_query(entry)` is the ONLY sanctioned conversion from a stored
  partition entry. It copies `question_id` and `text` and nothing else.
- The following MUST NOT reach a model (`FORBIDDEN_MODEL_FIELDS`):
  `split`, `question_type`, `answerability`, source articles
  (`source_articles` / `group` / `evidence_groups`), Regime-B membership
  (`regime` / `regime_b` / `paired*`), `evidence`, `sufficient_sets`,
  `labels`, `hard_negatives` — plus the stored-entry containers `meta`
  and `provenance` in their entirety.
- Rationale: `question_type` is EVALUATION metadata. Handing
  `unanswerable` to a sufficiency controller hands it the desired
  decision; handing `group`/`source_articles` hands a retriever a 1–3
  article candidate set inside a 297-article corpus.
- `assert_no_label_metadata(payload)` raises `ForbiddenMetadataError`
  fail-closed if any forbidden field is present on a model-facing payload
  (dict keys at every nesting level, and QueryInput attributes, including
  ones smuggled via `object.__setattr__`). Pinned by
  `tests/test_query_contract.py`.
- Verified storage fact (do not assume): in the committed
  `corpus/questions.json`, `meta` is `{}` for 119 of 206 entries; the 87
  shadow_dev reclassifications carry only `original_id` +
  `exposure_note`. No entry carries `group`/`evidence_groups`/
  `source_articles` in `meta` — the builder drops the answer's LOCATION in
  every entry — but the stored entry as a whole still carries
  `split`/`question_type`/`meta`/`provenance`, which is exactly why the
  model-facing boundary must be explicit.

## 2. What a worker team MAY access

- Question TEXT of the train / dev / shadow_dev items, via
  `corpus/questions.json` (the ONLY question file a worker may read).
- Public reference data (`public_reference` category; dev/reference use
  only, never training or heldout).
- Corpus text: the full shared core corpus AND the scale tier. Splits
  constrain QA declarations, never corpus access: all splits search the
  same global corpus files.
- The public 21-document Regime B exclusion list
  (`corpus/regime_b_excluded_articles.json`, via
  `substrate.query.worker_regime_b_exclusions`).
- The frozen substrate/eval/generator code and Round 0 documentation,
  including this contract, `docs/scoring-protocol.md`,
  `docs/regime-pairing.md`, and `docs/scale-evaluation-rule.md`.
- Custodian leakage-gate verdicts on synthetic data: PASS or REJECT plus
  the SYNTHETIC ids to remove — never the matched private id, text,
  answer, or evidence.

## 3. What a worker team may NOT access

- Private test question text, answers, support atoms, and labels (they
  live outside the repository at `LMR_PRIVATE_EVAL_DIR`; see
  `docs/private-eval-custody.md`).
- Private source ids, and Regime-B pair membership: WHICH of the 21 public
  articles are the private 13, and the 15 private paired question ids.
- Private results before the tournament lock.
- Any derivation of the worker exclusion list from private
  paired-regime metadata. The worker list is the public 21, derived from
  the public artifact only — invariant pinned by
  `tests/test_query_contract.py` (open-spy: only the public file is
  opened; source audit; the in-repo private manifest is opaque, counts
  and hashes only, and carries no article names to derive from).

## 4. Regime B operational protocol (public superset)

Preregistered in `docs/regime-pairing.md` ("Operational 21-document
superset protocol"):

- Model A: normal corpus-known adaptation — architecture-specific
  synthetic training/adaptation may use any corpus document.
- Model B: the identical procedure, but ALL 21 publicly declared
  Regime-B articles are excluded from architecture-specific synthetic
  training/adaptation data.
- Query-time corpus is IDENTICAL for A and B: the 21 REMAIN in the
  retrieval corpus (excluded from adaptation data only).
- Because the worker list (21) is a preregistered superset of the private
  exclusion set (13), scoring the 15 secret paired items never reveals
  which 13 of the 21 matter.

## 5. Synthetic training data and the custodian leakage gate

- Architectures may generate synthetic training/adaptation questions from
  the shared corpus. Public bounty questions are development/reference
  ONLY, never training examples.
- Before use, every synthetic batch MUST pass the custodian leakage gate
  (`data_tools.leakage_check` run against the sealed private set;
  `substrate.private_eval.check_training_overlap` is the custodian-side
  gate). The verdict is PASS or REJECT + the synthetic training ids to
  remove; it never discloses matched private ids/text/answers. It fails
  closed: with no seal it is REJECT, never PASS.
- Honest current limitation (carried from Round 0 status): the gate's
  hash-only comparison is not yet bound to the seal; until it is, the
  gate correctly refuses to issue PASS.
- Regime B teams must additionally exclude the public 21 articles from
  adaptation data (invariant: `verify_adaptation_exclusion` style
  manifests must show no excluded doc in the adaptation-data manifest).

## 6. Invariants and fail-closed behavior

- Substrate is frozen at Round 0; architecture-specific code lives under
  `experiments/<architecture>/` only.
- The model-facing boundary (§1) is enforced by construction
  (`to_model_query`) and by the fail-closed guard
  (`assert_no_label_metadata`); `tests/test_private_eval_tripwire.py`
  fails if private filenames/content/labels appear under the repository
  path.
- All measurements are desktop. No Android or on-device performance claim
  may be derived from any of this.
- Thresholds are selected on dev/shadow_dev and frozen in the run
  manifest BEFORE the private run; calibration claims require the
  `substrate.types` provenance fields.
