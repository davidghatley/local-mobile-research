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
| 6 | `question-label-partition` | Requires `corpus/questions.json` and `corpus/heldout_labels.sealed.json` (legacy in-repo seal path; Phase 5 moves the private_test seal out-of-repo to `LMR_PRIVATE_EVAL_DIR`). Verifies: no question id appears in both the public file and the sealed set; no entry declares retired `split=heldout`; no entry declares `split=private_test` in-repo (rejected: private data lives outside the repo); the sealed artifact is byte-verifiable by opaque SHA-256 via `substrate.splits.verify_seal_opaque` without ever being opened for content; the sealed file is listed in `.gitignore`; and the dev-side read path is refused — `HeldoutCustodian.load_labels()` and `load_labels(allow_heldout=True, …)` both raise `HeldoutAccessDenied`. `shadow_dev` is dev-visible and never sealed (Issue 1). |
| 7 | `generator-pin` | Requires `corpus/generator_config.json` to be fully pinned: no `TBD`/`unspecified` fields, `is_pinned()` true, not an infrastructure stub, prompt hash equal to `substrate.generator.PROMPT_HASH`, tokenizer and chat-template hashes present as 64-hex, model artifact byte count and SHA-256 verified against the file on disk, and every declared runtime binary/library SHA-256 verified. |
| 8 | `freeze-manifest` | Runs `substrate.manifest.validate_freeze` against a `RunManifest` built from the **real** on-disk artifact set (recomputed corpus hash, real generator config, real code hashes, real inventory pins, real split map, derived seed log) and prints its explicit gap list verbatim. |
| 9 | `leakage-control-artifacts` | Requires `references/public_eval_pins.json` to be present and well formed (64-hex SHA-256, 40-hex revision, positive byte counts, matching `total_bytes`, empty `pin_mismatches`), cross-checks pin hashes byte-for-byte against `references/pins.json`, derives regime metadata from `corpus/split_map.json` via `substrate.regime_metadata`, verifies regime B is a strict subset of heldout/shadow_dev groups (legacy "heldout" accepted alongside forward "shadow_dev"; Phase 3 reworks regimes to paired conditions), and verifies the regime B excluded-article artifact is consistent with the split map when regime B is non-empty. |

### Artifacts the verifier expects but does not own

Stage 6 requires two files that no worker has produced yet:

- `corpus/heldout_seal.json` — the recorded `seal_sha256` for the sealed
  artifact. The verifier will **not** open the sealed file to compute one.
- `corpus/heldout_question_ids.json` — an id-only projection published at seal
  time. Question-id disjointness is proven from this list, so the sealed file
  never has to be read for content.

## 4. Modes

### Full mode (default)

Every load-bearing stage must PASS. A stage whose required artifact is absent
reports `SKIP`, and **in full mode a SKIP is a failure** — unverified is not
frozen.

### `--code-only`

Runs stages 1–5, 7, and 9. Stages 6 and 8 are skipped because they cannot pass
until the freeze artifacts exist. The run prints, in a boxed banner:

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

## 7. Current status (pre-freeze, expected)

At the time of writing the full run **FAILS with exit 1**. This is the
expected and desired state before freeze. Current failures:

| Stage | Status | Reason |
|-------|--------|--------|
| 1, 2, 3 | PASS | 282 / 77 / 17 tests. |
| 4 | PASS | Canonical hash, hierarchy, group map, and all four `build_manifest` artifact hashes verified. |
| 5 | PASS | 70 drafts, 70 approved, 0 errors (structural only). |
| **6** | **FAIL** | `corpus/questions.json` and `corpus/heldout_labels.sealed.json` **do not exist yet**. Real freeze blockers. |
| 7 | PASS | Generator contract fully pinned; GGUF bytes and SHA-256 verified; all 9 runtime binaries verified. |
| **8** | **FAIL** | `validate_freeze` gap list: missing `questions.json`, missing sealed labels, `sealed_labels_sha256` unrecorded, `questions_sha256` unrecorded, `thresholds` empty, regime-group coverage gaps. |
| **9** | **FAIL** | `corpus/regime_b_excluded_articles.json` absent while regime B has 5 non-empty groups. |

These are artifact-availability failures, not defects in the verifier. Each one
names exactly what must be produced.

Stage 8 also surfaces a defect **outside this role's ownership**: the regime
block in `substrate.manifest.validate_freeze` raises
`cannot access local variable 'groups_raw' where it is not associated with a
value`. That file belongs to the manifest/regimes owner (Phase 2 Lane E) and
was not modified here.

## 8. Reproducing

```bash
# Full verification (expected: exit 1 before freeze)
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
