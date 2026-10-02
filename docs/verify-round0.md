# Round 0 Verification — One-Command Entry Point

**Owner:** Phase 2 verifier (free model: `opencode/space-bunny-free`).
**Files owned by this role:** `scripts/verify_round0`,
`.github/workflows/verify-round0.yml`, `tests/test_verify_round0_entrypoint.py`,
`docs/verify-round0.md` (this file). No other file was modified.

---

## 1. What this is

`scripts/verify_round0` is the single command that decides whether a Round 0
freeze candidate is **structurally** valid. It runs every load-bearing
code-level check in a fixed order, prints a PASS/FAIL verdict per stage, and
exits non-zero if any load-bearing stage failed or could not be verified.

```bash
./scripts/verify_round0                # full freeze verification
./scripts/verify_round0 --code-only    # code-level portion only
./scripts/verify_round0 --only 4,7     # specific stages (partial, never a freeze pass)
./scripts/verify_round0 --help         # usage; side-effect free
```

Exit codes:

| Code | Meaning |
|------|---------|
| `0`  | Every load-bearing stage this mode required passed. |
| `1`  | A load-bearing stage FAILED, or (full mode) was SKIPped because a required artifact is absent. |
| `2`  | Usage error or unusable environment. |

## 2. What a PASS does **not** mean

> **This tool verifies STRUCTURE, HASHES, SPLITS, PROVENANCE and PINS only.**
> It does **not** verify semantic QA correctness, and it **cannot**. Semantic
> QA review is a human/agent adjudication process that cannot be unit tested
> into correctness.

Specifically, no `PASS` from this tool certifies any of the following:

- whether a benchmark question is actually answerable from the corpus;
- whether the recorded support atoms are minimal (one proposition each);
- whether a multi-hop item is genuinely multi-hop;
- whether any recorded label is factually correct.

Those decisions belong to the two-independent-pass semantic audit described in
`docs/qa-semantic-audit-protocol.md`, with orchestrator adjudication. The
verifier prints this disclaimer on **every** run, in `--help`, and in
`--code-only`. `tests/test_verify_round0_entrypoint.py` asserts that no stage
name or output line can be read as a semantic QA verdict.

A structural PASS also does not grant the freeze. Per
`docs/round0-review-criteria.md` Appendix B, freeze additionally requires an
independent reviewer who did not build the substrate, who reads a sample of
traces and training examples, and who concludes the substrate actually enables
fair comparison. **Checklist completion is not freeze.**

## 3. Stages

| # | Stage | What it verifies |
|---|-------|------------------|
| 1 | `substrate-tests` | `python3 -m unittest discover -s tests` |
| 2 | `data-tools-tests` | `python3 -m unittest discover -s data_tools/tests` |
| 3 | `corpus-tests` | `python3 -m unittest discover -s corpus/tests` |
| 4 | `corpus-hash` | Recomputes the canonical corpus hash from `corpus/corpus.jsonl` and compares it against `corpus/provenance.json` (`corpus_hash_sha256`, `canonical_text_sha256`); runs `substrate.corpus.validate_hierarchy`; runs `substrate.splits.validate_group_map` against the real corpus article titles; verifies **every** artifact hash and byte count in `corpus/build_manifest.json` against the bytes on disk, plus the `input_manifest_sha256` field. |
| 5 | `qa-validation` | Runs `python3 -m data_tools.validate_qa --staging staging --corpus corpus/corpus.jsonl --split-map corpus/split_map.json`, requires exit 0 and `errors == 0`, and reports draft/approved/split/type counts. Approved counts are content-hash bookkeeping, **not** a semantic verdict. |
| 6 | `question-label-partition` | Requires `corpus/questions.json` (public-only partition: 60 train, 59 dev, 87 shadow_dev) and `corpus/private_test_manifest.json` (in-repo opaque manifest carrying private seal digest). Verifies: the partition matches the **external census pin** in `corpus/partition_census.json` — exact total, exact per-split counts, no undeclared splits, no quarantined id reappearing, and `authored_total == published + rejected` (an empty, truncated, or consistently-truncated partition is a failure, not a pass); public questions carry NO evidence atoms, NO hard negatives, NO answer text, NO `split=heldout` (retired), NO `split=private_test` (out-of-repo); **no answer LOCATION** (`meta.group` / `meta.evidence_groups` / `meta.source_articles` / `meta.paired_regime`) and **no answer text in prose** (`provenance.rationale`); private seal digest recorded in manifest is verified against the out-of-repo private eval dir via `substrate.private_eval.verify_seal` (opaque bytes only, never parsed); ID namespace separation — no `qa-private-` prefix appears in the public partition. `shadow_dev` is dev-visible and never sealed. |
| 7 | `generator-pin` | Requires `corpus/generator_config.json` to be fully pinned: no `TBD`/`unspecified` fields, `is_pinned()` true, not an infrastructure stub, prompt hash equal to `substrate.generator.PROMPT_HASH`, tokenizer and chat-template hashes present as 64-hex, model artifact byte count and SHA-256 verified against the file on disk, and every declared runtime binary/library SHA-256 verified. |
| 8 | `freeze-manifest` | Runs `substrate.manifest.validate_freeze` against a `RunManifest` built from the **real** on-disk artifact set (recomputed corpus hash, real generator config, real code hashes, real inventory pins, real split map, derived seed log, **calibration policy declarations**, **regime A/B group metadata derived from split map**, **partition census digest**). Cross-checks the census digest against the **out-of-repo trust root** at `<LMR_PRIVATE_EVAL_DIR>/freeze_census_pin.json` and **fails closed** when that pin is absent or disagrees. On success it **writes the freeze manifest durably** to `<LMR_PRIVATE_EVAL_DIR>/freeze_manifest.json` — never into the repository — so a freeze leaves a re-readable record rather than only a terminal verdict. A failing stage writes nothing. |
| 9 | `leakage-control-artifacts` | Requires `references/public_eval_pins.json` to be present and well formed (64-hex SHA-256, 40-hex revision, positive byte counts, matching `total_bytes`, empty `pin_mismatches`), cross-checks pin hashes byte-for-byte against `references/pins.json`, derives regime metadata from `corpus/split_map.json` via `substrate.regime_metadata`, verifies regime B paired-condition groups key on shadow_dev groups (legacy "heldout" accepted; B overlaps A by design — same questions, two conditions, never a disjoint population; see `docs/regime-pairing.md`), verifies the regime B excluded-article artifact is consistent with the split map when regime B is non-empty, and reports the paired-condition artifact (`corpus/regime_b_paired.json`) informationally. |
| 10 | `private-eval-custody` | Requires `corpus/private_test_manifest.json` to be present, content-free (no `qa-private-` id, no `answer_text`, no `sufficient_sets`), and to carry non-zero counts plus a `seal_sha256`. Then requires the private artifacts to exist **outside** the repository at `LMR_PRIVATE_EVAL_DIR` (`questions.json`, `labels.json`, `counts.json`), and **fails closed**: an *absent recorded digest* is a gap, not a match. Only opaque bytes are hashed; content is never parsed or printed. |

### Artifacts the verifier expects but does not own

Stage 6 requires these artifacts:

- `corpus/questions.json` — public-only question partition (**206 items: 60 train,
  59 dev, 87 shadow_dev**). Generated from staging/ after QA approval by
  `python3 -m data_tools.build_public_partition`. It carries ONLY
  `question_id`, `text`, `split`, `question_type`, `meta.original_id`,
  `meta.exposure_note`, and who/which-model/decision provenance.

  It deliberately does **NOT** carry:

  - evidence atoms or sufficient sets (retrieval ground truth),
  - hard negatives (they hand over the distractors),
  - answer text,
  - `meta.group` / `meta.evidence_groups` / `meta.source_articles` /
    `meta.paired_regime` — these name **the answer's location**; publishing
    them would hand a retriever a 1–3 article candidate set inside a
    297-article corpus,
  - `provenance.rationale` — auditor prose that names the answer in free text.

  The builder refuses to write if a multi-word answer appears verbatim anywhere
  in the output. `tests/test_public_partition.py` pins all of this and asserts
  regeneration is byte-identical to the committed file.

  Note: `staging/` in the same repository still carries answers for all 206
  items. The partition is the *intended* worker-visible surface, not an enforced
  one; a sanitized worktree that omits staging/ is the real control.
- `corpus/private_test_manifest.json` — in-repo opaque manifest (revision `private-test-r1`, total=116). Carries counts, hashes (questions_json_sha256, labels_json_sha256, aggregate_content_sha256), seal_sha256, paired Regime B metadata. NO private content. **Must be tracked by git** and explicitly un-ignored: it is the only thing binding the out-of-repo private test to this repository, so a clone without it cannot verify the private boundary. A test asserts both properties.
- `corpus/partition_census.json` — the pin on partition size, holding the approved/public counts per split, the quarantined ids, and the accounting identity. It sits **outside the artifacts it checks** (drafts, partition) but **inside the repository**, which is a weaker guarantee and must be named accurately: deleting staging drafts and the matching partition entries *together* leaves every internal cross-check self-satisfied, so stages 5, 6 and 8 would pass on half a freeze. The real trust root is the census digest recorded **outside git** in `<LMR_PRIVATE_EVAL_DIR>/freeze_census_pin.json`; stage 8 compares the live census against it and fails closed if the pin is absent or disagrees. Without that out-of-repo digest, a commit that edits the data and the census together defeats the whole check.

The private sealed labels live OUTSIDE the repo at `LMR_PRIVATE_EVAL_DIR` (never committed). The verifier uses `substrate.private_eval.verify_seal()` to confirm the seal digest matches the out-of-repo artifact.

## 4. Modes

### Full mode (default)

Every load-bearing stage must PASS. A stage whose required artifact is absent
reports `SKIP`, and **in full mode a SKIP is a failure** — unverified is not
frozen.

### `--code-only`

Runs stages 1–5, 7, 9, and 10. Stages 6 and 8 are the freeze-gated pair and
are skipped. The run prints, in a boxed banner:

```
CODE-ONLY MODE -- THIS IS NOT A FREEZE PASS.
```

and again in the closing reminder. A code-only exit of `0` means only that the
code-level checks ran. It says nothing about whether Round 0 may be frozen.

In `--code-only`, a check that could not run because a git-ignored artifact is
absent is reported as `SKIP` **and enumerated in a `NOT VERIFIED` section**.
A skip is never reported as a pass.

### `--only IDS`

Runs only the listed stages and prints a `PARTIAL VERIFICATION` banner. Useful
for reproducing one check in isolation. Never a freeze pass.

## 5. Guarantees

| Property | How it is enforced | How it is tested |
|----------|--------------------|------------------|
| Deterministic | No clock, no randomness, no network. Fixed stage order. | Implicit in repeated runs. |
| Read-only | Never writes to the repo. `PYTHONDONTWRITEBYTECODE=1` so no `.pyc` is written. Scratch files live in a `mktemp -d` outside the repo and are removed by an `EXIT` trap. | `test_verifier_does_not_mutate_the_repository_tree` compares a full size+mtime fingerprint of a temp copy before and after. |
| No network at verification time | Static check: no `socket`/`urllib`/`requests`/`curl`/`wget` references. Upstream pinned bytes are reported as *claims, not measurements*, never re-fetched. | `test_no_network_imports_in_the_entry_point`. |
| Never prints sealed label content | The sealed file is only ever hashed with `verify_seal_opaque`. It is never opened for content. | `test_never_prints_sealed_label_content`. |
| Refuses label-read authority | Exits 2 if `HELDOUT_CUSTODIAN_MODE` is set in full mode. | `test_refuses_to_run_under_custodian_mode`. |
| `--help` is side-effect free | `--help` returns before root resolution, before scratch creation, before any `python3` spawn. | Seven assertions, including a timing bound (< 5 s) and a scratch-directory emptiness check. See below. |

### The `--help` regression

A `--help` that ran the whole suite has broken this project **twice**. The
fix here is structural: `--help` is handled in the argument-parsing loop and
returns immediately, before the root is resolved and before any subprocess is
spawned. The test asserts nine properties, the strongest being:

- `--help --root /nonexistent/definitely/not/a/repo` still exits `0` — proof
  that the root is never resolved;
- `--help` under `HELDOUT_CUSTODIAN_MODE=benchmark` still exits `0` — proof
  that the environment guard runs after argument parsing;
- `--help` creates no scratch file under a controlled `TMPDIR`;
- `--help` writes nothing into its working directory;
- `--help` completes in under 5 seconds (the real suite takes seconds).

## 6. CI

`.github/workflows/verify-round0.yml` runs on every `push` and `pull_request`.

It runs `./scripts/verify_round0 --code-only` and then **asserts**:

1. the entry point exists and is executable;
2. `--help` prints no stage banner and no `STAGE …: VERDICT` line;
3. the log states explicitly whether the generator artifact was **VERIFIED** or
   **SKIPPED** — a CI run must never silently pass a check it could not run;
4. a `NOT VERIFIED` section enumerates everything skipped;
5. the run carries its not-a-freeze-pass banner and never emits
   `RESULT: all load-bearing stages PASS.`

The workflow downloads **nothing**. It performs no model download and no
weight fetch, because the 986 MB GGUF, the 42 MB `corpus/corpus.jsonl`, and the
41 MB `corpus/raw/` snapshot directory are all git-ignored.

### Known CI limitation (stated, not hidden)

Because the pinned artifacts are git-ignored, a CI run **cannot** verify
stages 3, 4, 5, 7 (artifact portion) or 9 (regime B excluded-article
artifact). Those checks report `SKIP` with an explicit reason. If a future
change made CI *silently pass* a check it never ran, the workflow would not
catch it — assertions 3 and 4 are the mitigation, and the artifact-complete
verification happens on the freeze host.

## 7. Current status

The full run now **exits 0 with all 10 stages PASS** on a complete local
checkout, with `LMR_PRIVATE_EVAL_DIR` pointing at the out-of-repo private
directory. This is a **structural** result only.

| Stage | Status | Notes |
|-------|--------|-------|
| 1 | PASS | Shared substrate tests. |
| 2 | PASS | Data-tools tests. |
| 3 | PASS | Corpus converter tests. |
| 4 | PASS | Canonical hash, hierarchy, group map, `build_manifest` artifact hashes. |
| 5 | PASS | 206 approved drafts, 0 errors (structural only), counts matching the census pin. 3 further items are rejected and quarantined in `staging/rejected/`. |
| 6 | PASS | Public-only partition + out-of-repo opaque seal verified. |
| 7 | PASS | Generator contract pinned; GGUF bytes/SHA-256 and all runtime binaries verified. |
| 8 | PASS | `validate_freeze` with real hashes, calibration-policy declarations, paired regime groups. |
| 9 | PASS | Public pins, regime metadata, excluded-article artifact, paired-condition artifact. |
| 10 | PASS | Private artifacts exist outside the repo; digests match; manifest is content-free. |

**This is not the freeze.** A structural PASS never certifies semantic QA
correctness (see §2), and freeze additionally requires an independent reviewer
who implemented none of it.

### CI is still weaker than the local run

Because the pinned artifacts are git-ignored and the private directory is
outside the repository, a CI run **cannot** verify stages 3, 4, 5, 7
(artifact portion) or 10 (private boundary). Those report `SKIP` with an
explicit reason. Local artifact-complete verification remains authoritative.

## 8. Reproducing

```bash
# Full verification (expected: exit 0 on a complete local checkout)
LMR_PRIVATE_EVAL_DIR=/home/davidhatley/Projects/testing/local_mobile_research-private-eval \
  ./scripts/verify_round0; echo "exit=$?"

# Code-level only (expected: exit 0)
./scripts/verify_round0 --code-only; echo "exit=$?"

# Entry-point harness tests
python3 -m unittest discover -s tests -p 'test_verify_round0_entrypoint.py' -v

# All three suites, as the verifier runs them
python3 -m unittest discover -s tests
python3 -m unittest discover -s data_tools/tests
python3 -m unittest discover -s corpus/tests
```

`tests/test_verify_round0_entrypoint.py` never mutates the real repository: it
copies the tree to a temp directory and corrupts only the copy.
