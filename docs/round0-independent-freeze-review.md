# Round 0 Independent Freeze Review

- **Reviewer:** fresh independent freeze reviewer, free endpoint `openrouter/qwen/qwen3.8-27b:free`
  (recorded substitution: assigned `gemma-4-31b-it:free` failed at task pickup). No nested
  spawning was used.
- **Date:** 2026-10-02
- **Claim under review:** "Round 0 repair run is complete and the substrate can be frozen so
  Round 1 may begin" (as stated in the working-tree `docs/STATUS.md`).
- **Method:** every reproducible claim was re-executed on this host; no orchestrator-reported
  result was accepted without re-running it where artifacts exist. Measured results are marked
  as such; claims that could not be re-verified are listed in §4.

## 1. Verdict

**REPAIR REQUIRED.**

The verifier machinery itself is sound and honest: I re-ran `./scripts/verify_round0` and it
passes 10/10 (exit 0), `--code-only` passes 8/8 (exit 0), and all test suites, hashes,
regenerations, and protocol probes I executed matched the claims in `docs/STATUS.md`.

However, the claim "the repair run is complete" is **false as recorded** for two reasons that
are load-bearing, plus one functional regression and a set of documentation/provenance gaps:

1. **Two shadow-dev comparison items are defective and were approved on flawed reasoning.**
   `staging/qa-shadow-dev-84.json` and `staging/qa-shadow-dev-86.json` both pre-state the
   comparison facts (years) inside the question text, making the recorded sufficient sets
   unnecessary and every recorded `leave_one_out_answerable: "no"` false. Both are in the
   8-item mandated independent sample; 86 is additionally in the Regime B `washington` paired
   group. This is the same pre-stated-premise defect class Phase 4 eliminated from the
   original 70 items, reintroduced in the shadow-dev batch and passed by both the Phase 2
   BATCH-C semantic audit and the space-bunny-free re-approval pass.
2. **Functional regression in the shared derivation tooling.** After the Phase 3 split-map
   migration, `data_tools/derive.py:72` rejects every `shadow_dev` group with
   `ValueError: group has invalid split: 'shadow_dev'` (probed directly; no test covers it).
3. Documentation, ledger, and provenance gaps (stale `docs/verify-round0.md`, stale verifier
   header comment, ledgers ending at `814dcc1` with no entries for the six repair commits,
   and the claim document `docs/STATUS.md` existing only uncommitted in the working tree while
   HEAD says "NOT FROZEN").

A freeze built on this state would institutionalize two protocol-violating items in the
dev-visible evaluation set and ship a broken shared tool. Repairs §5.1–5.7 are required before
a PASS can be claimed.

## 2. Per-area findings

| # | Area | Holds? | Evidence |
|---|------|--------|----------|
| 1 | shadow-dev reclassification (Issue 1) | YES | 89 files `staging/qa-shadow-dev-*.json` (ids 1–90, 60 absent); every file carries `split=shadow_dev`, `meta.original_id`, `meta.exposure_note`, `provenance.reclassification`; no secrecy/generalization claims; residual "heldout" strings are legacy-compat code (`substrate/splits.py` `SPLITS`, `DEPRECATED_HELDOUT_SPLIT`), historical logs, or provenance fields. |
| 2 | Custody & sealing | YES (one latent hole) | `substrate/private_eval.py` fail-closed (REJECTs both with no seal and with an unbound hash comparison); 370 unique files ever committed (`git log --all --diff-filter=A`), none with private-eval content; no tags/stashes/extra branches; no symlinks; 10-test tripwire `tests/test_private_eval_tripwire.py` present and passing. Hole: `scripts/verify_round0:1361-1372` prints "MATCHES" when a recorded manifest hash is missing (vacuous pass) — latent, not triggered in the current run. |
| 3 | Sufficient sets / multi-hop protocol | **NO** | `staging/qa-shadow-dev-84.json` and `qa-shadow-dev-86.json`: questions pre-state the comparison facts; every recorded leave-one-out record is false; both approved under "both required" reasoning by Phase 2 BATCH-C audit (`round0-semantic-auditor-batchC`) and re-approval (`opencode/space-bunny-free`; ledger lines 155/157). All other sampled items sound (14-item sample; atom texts byte-exact vs corpus for all 14; 31 multi-atom sets across 25 items reproduced exactly; items 18, 19, 24, 27, 36, 45, 46, 48, 62, 78, 85, 88 adjudicated sound). |
| 4 | Paired regime (Regime B) | YES | 14 regime tests pass; `substrate/regime_metadata.py` `pair_conditions` refuses mismatched id sets (masquerade-proof); 56 pairings regenerate deterministically and equal `corpus/regime_b_paired.json` in ids, order, and conditions; 21 excluded articles = B-group union, `scope` states adaptation-only; `verify_query_corpus_unchanged` vs the real corpus: 0 violations. Split-map migration verified as a pure token swap (old `b80a774dc9…` 25,219 B → new `d0879ac480…` 25,315 B; structure identical after the swap). |
| 5 | Scale classification | YES (missing hook file) | Classification 815/15/110/0 reproduced against `corpus/scale/scale_classification.json`; provenance timeline consistent with git (`4d924c5` 2026-09-29 predates `814dcc1` 2026-10-01, which added `distractor_candidates.json`); `PROVENANCE-CORRECTION.md` accurate; disclosed weaknesses (single scale point, null revid, empty outlinks, 110 redirect stubs). `eval/scale_adjudication.py` is documented in `docs/scale-evaluation-rule.md` but absent from `eval/`. |
| 6 | Trace schema / telemetry | YES | 51 tests across `test_stage_scores_semantics` / `test_telemetry_storage_memory` / `test_support_semantics` pass; `validate_score_value` rejects -0.1 and 1.5 for `model_probability`, accepts 0/0.5/1; logit-with-probability-interpretation probe fails as required; VmHWM vs VmRSS distinct with distinct sources; ancestry-aware support tests present. |
| 7 | Abstention / shared gate | YES | `run_question` is the sole generator path; counting mock proves 0 generator calls on the abstain path; zero-spans vs over-budget-empty distinguished; `EvidenceDecision` constructor enforces sufficient↔generate / insufficient↔abstain. |
| 8 | Freeze manifest | YES (with notes) | `substrate/manifest.py:304-682` `validate_freeze` recomputes the corpus hash, byte-hashes questions, verifies the out-of-repo seal, split-map bytes + QA provenance, generator bytes/semantics/runtime binaries, code hashes, and regime exact set-equality; stage 8 is not vacuous. Notes: calibration thresholds are synthesized inside the verifier (disclosed as STATUS.md limitation #5 — acceptable with note); stage 6 custodian sub-check passes vacuously when the legacy labels file is absent (documented "expected"); stage 9 skips the `pins.json` cross-check silently if the file is absent (file present, so not vacuous in this run). |
| 9 | Provenance | YES | Reproduced: `tests` 343 OK (304 run in-verifier + 39 skipped entrypoint module); `data_tools/tests` 77 OK; `corpus/tests` 17 OK; `validate_qa` → 209 drafts / 209 approved / 0 errors, all `decision=approve` with `content_hash` matching recomputed `draft_content_hash` (0 issues), author ≠ verifier on every item; 5-item spot check clean. |
| 10 | Honesty of claims | PARTIAL | STATUS.md claims match my measurements (10/10 full, 8/8 code-only, split/type counts, seal `c6e1e98d…`); the limitations section is honest and matches findings. But: `docs/STATUS.md` is uncommitted (HEAD `49047f9` says "NOT FROZEN"); `docs/progress-ledger.md` and `docs/orchestration-log.md` end at `814dcc1` with no entries for repair commits `937b3c5`, `182b583`, `e62de3e`, `908dcaa`, `9253655`, `49047f9`; `docs/verify-round0.md` §4/§7 stale; verifier header comment stale. |

### 2.1 Area 3 defect detail (load-bearing)

**`staging/qa-shadow-dev-84.json`** (comparison, `is_multi_hop=true`, group `solo:virtual
reality`, sample item):

- Question (line 3): "Which consumer headset effort came first: **the 1991 headset** for the
  Mega Drive home console, or the headset first presented at the E3 video game trade show
  **in 2012**?"
- The question pre-states both comparison years and identifies the 1991 side by console. The
  ordering is resolvable from the question text alone; and atom `p:virtual_reality:06:000`
  alone ("In 1991, Sega announced the Sega VR headset for the Mega Drive home console", line
  22) supplies the recorded answer text "Sega VR" together with the question's own ordering.
- Recorded `leave_one_out_answerable: "no"` for **both** atoms (lines 84, 95) is false:
  removing either atom leaves the question answerable.
- Approval chain: Phase 2 BATCH-C audit (auditor `round0-semantic-auditor-batchC`,
  `openrouter/qwen/qwen3.8-27b:free`, `audit_rationale` line 79: "…both required… 1991 precedes
  2012") and the re-approval pass (`opencode/space-bunny-free`; ledger line 155 repeats "both
  required and 1991 precedes 2012"). Both ratifications checked the atoms without noticing
  that the question text already contained the comparison years.

**`staging/qa-shadow-dev-86.json`** (comparison, `is_multi_hop=true`, group `washington` —
Regime B paired group; source articles `a:washington_d_c`, `a:washington_state`):

- Question (line 3): "Which was established first: the federal capital district created by the
  **1790** Residence Act, or the 42nd state admitted in **1889**?"
- The question pre-states both establishment years; 1790 < 1889, and the recorded answer text
  ("the capital district", line 77) is literally the question's own side-A descriptor. **Zero
  atoms are required**; all six recorded atoms (lines 105–166) fail leave-one-out; all six
  recorded `"no"` values are false.
- Same flawed approval chain: Phase 2 BATCH-C (lines 97–100, 104–167) and ledger line 157
  ("in every pairing both atoms are required and 1790 precedes 1889").

These are new instances of the pre-stated-premise defect class that Phase 4 eliminated from
the original 70 items ("8 of 10 inflated multi-hop labels"). The defect is visible to any
reader of the question text; the audit protocol's single-atom answerability test would catch
both items if it had been applied to the question, not just to the atom pairs.

## 3. Commands run (measured results)

| # | Command / probe | Result |
|---|-----------------|--------|
| 1 | `./scripts/verify_round0` | exit 0; STAGE 1–10 all PASS (10/10), incl. stage 6 partition, stage 8 freeze manifest, stage 10 private eval |
| 2 | `./scripts/verify_round0 --code-only` | exit 0; stages 1,2,3,4,5,7,9,10 PASS (8/8) |
| 3 | `python3 -m unittest discover -s tests` (full suite, direct) | 343 tests, OK |
| 4 | `python3 -m unittest discover -s data_tools/tests` | 77 tests, OK |
| 5 | `python3 -m unittest discover -s corpus/tests` | 17 tests, OK |
| 6 | `data_tools.validate_qa` | 209 drafts / 209 approved / 0 errors; splits train 60 / dev 60 / shadow_dev 89; types factoid 128 / multihop 33 / comparison 20 / ambiguous 15 / unanswerable 13 |
| 7 | Probe: `derive.group_articles(split_map, "cambridge")` (a `shadow_dev` group) | `ValueError: group has invalid split: 'shadow_dev'`; a `train` group returns normally — regression confirmed at `data_tools/derive.py:72` |
| 8 | 14-item sample: byte-exact atom text check vs corpus JSONL | all 14 items' atom texts match the corpus exactly |
| 9 | Reproduce multi-atom set census | 31 multi-atom sets across 25 items (matches claim exactly); 13 multi-singleton items consistent |
| 10 | Regenerate regime pairings via `substrate.regime_metadata` | 56 pairings, equal to `corpus/regime_b_paired.json` in ids, order, and conditions; 21 excluded = B-group union |
| 11 | `verify_query_corpus_unchanged` against the real corpus | 0 violations |
| 12 | Split-map migration diff (old `b80a774dc9…` 25,219 B vs new `d0879ac480…` 25,315 B) | pure token swap; structure otherwise identical |
| 13 | Scale classification census | 815/15/110/0, matches `corpus/scale/scale_classification.json` |
| 14 | `validate_score_value` probes | rejects -0.1 and 1.5; accepts 0, 0.5, 1; logit/Probability confusion probe fails as required |
| 15 | VmHWM vs VmRSS probe | distinct values, distinct sources |
| 16 | `EvidenceDecision` constructor probes | sufficient↔generate and insufficient↔abstain enforced |
| 17 | Counting mock on the abstention path | 0 generator calls |
| 18 | Build-manifest artifact hash verification | all artifact hashes match, incl. the 986 MB GGUF and 9 runtime binaries |
| 19 | Corpus canonical hash reproduction | `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1` |
| 20 | `git log --all --diff-filter=A` (all files ever committed) | 370 unique files; none containing private-eval content; no tags, stashes, or extra branches |
| 21 | `git status` / `git diff` | only uncommitted change at review time: ` M docs/STATUS.md` |
| 22 | Private eval directory top-level listing (existence check only) | directory exists outside the repo; no private file contents read |

## 4. What could not be verified

1. **Semantic quality of the 116 private test items** — custody-forbidden (no `questions.json`,
   `labels.json`, `counts.json`, `seal.sha256`, `review/`, or `authored/` content read). Only
   the verifier's opaque seal/hash check (stage 10) and the in-repo opaque manifest
   metadata were examined.
2. **Three orchestrator-reported upstream failures** recorded in the ledgers — no artifacts
   exist in-repo to re-run against; accepted as recorded.
3. **The 38-test `corpus/scale/tests` suite** was not re-executed in this review (the 17-test
   `corpus/tests` suite was; the classification census was re-computed independently).
4. **No Android performance measurements** were claimed or examined — the substrate is
   desktop-only by design and STATUS.md makes no Android claims (consistent; noted so that a
   future reviewer does not infer Android validity from these results).
5. The private-test "none an author" property is recorded as identity separation only; worker
   separation beyond recorded identities was not independently verifiable. Observation: the
   batch-c author and reviewers 68–100 both list `openrouter/qwen/qwen3.8-27b:free` — distinct
   workers, same endpoint. Recorded, not a defect.

## 5. Required repairs

1. **Repair or replace `staging/qa-shadow-dev-84.json`.** The question pre-states the
   comparison (both years in the text; "the 1991 headset for the Mega Drive home console").
   Rewrite the question so the question text does not itself resolve the comparison (remove
   pre-stated years/descriptors that fix the ordering), or reject and replace the item. Then
   re-adjudicate under `docs/qa-semantic-audit-protocol.md`: after a correct rewrite both
   atoms should be genuinely required, `leave_one_out_answerable` must be re-recorded and be
   verifiably true, a new `content_hash` and a new independent approval (author ≠ verifier,
   verifier ≠ the original ratifiers) must be recorded, and `docs/qa-shadow-dev-reapproval-ledger.md`
   line 155 updated. As recorded, this item fails the protocol's single-atom answerability test.
2. **Repair or replace `staging/qa-shadow-dev-86.json`.** The question pre-states both
   establishment years (1790, 1889); the answer is determinable from the question text alone
   (zero atoms needed), and all six recorded leave-one-out records are false. Same procedure
   as item 1 (rewrite-or-reject, re-adjudicate, re-approve, ledger line 157). Note this item
   is in the Regime B `washington` paired group — any replacement must be re-paired through
   `substrate.regime_metadata` and the regenerated `corpus/regime_b_paired.json` re-verified.
3. **Fix `data_tools/derive.py:72`** (`group_articles`): accept `shadow_dev` in the split
   vocabulary (currently `("train", "dev", "heldout")`, which rejects all 32 `shadow_dev`
   groups post-migration — a functional regression; probed, and uncovereded by any of the 77
   `data_tools/tests`). Also update the module docstring (lines 5–6, 21–27 reference the
   heldout-era workflow) and add a regression test that runs `group_articles` on a
   `shadow_dev` group. Acceptance: the §3 probe #7 returns `(articles, "shadow_dev")` and the
   full `data_tools/tests` suite passes.
4. **Fix stage 10 of `scripts/verify_round0` (lines ~1361–1372).** When
   `questions_json_sha256` / `labels_json_sha256` are missing from the in-repo manifest, the
   current `if rec_q and rec_q != qh: fail else: "MATCHES"` branch prints MATCHES — a vacuous
   pass. Fail-closed: `mark_fail()` on a missing recorded hash; only print MATCHES when a
   recorded hash is present and equal. Add a test that removes a recorded hash and expects
   failure.
5. **Resolve the `eval/scale_adjudication.py` discrepancy.** `docs/scale-evaluation-rule.md`
   documents the file; it does not exist under `eval/`. Either implement the hook per the
   documented rule, or correct the doc (scale is classification-only at this freeze; if the
   doc is corrected, say so explicitly). Acceptance: doc and filesystem agree.
6. **Update stale documentation and comments.** (a) `docs/verify-round0.md` §4/§7: code-only
   now runs stages 1–5, 7, 9, 10 (8 stages, per `CODE_ONLY_IDS="1 2 3 4 5 7 9 10"` at
   `scripts/verify_round0:65`), and the full run now exits 0 — §7 still claims "full run FAILS
   with exit 1"; the "343 tests total" row conflates the 304-test in-verifier run with the 343
   direct full-suite run. (b) `scripts/verify_round0` header comment (line 29) and `--help`
   text (line 80) still say "stages 1-5, 7, 9" for code-only. Acceptance: docs match the
   implemented stage sets and exit behavior.
7. **Complete the ledgers and commit the claim document.** (a)
   `docs/progress-ledger.md` and `docs/orchestration-log.md` end at `814dcc1`; add entries for
   the six repair commits `937b3c5`, `182b583`, `e62de3e`, `908dcaa`, `9253655`, `49047f9`.
   Acceptance: every Round 0 commit in `git log` has a ledger entry. (b) `docs/STATUS.md` is
   the only uncommitted change; the claim document currently exists only in the working tree
   while the committed version at HEAD `49047f9` says "NOT FROZEN". Commit it after the other
   repairs land. Acceptance: `git status` clean and claim == HEAD.

## 6. Non-blocking notes (recorded, no repair required)

- Stage 8 calibration thresholds are synthesized inside the verifier; disclosed as STATUS.md
  limitation #5. Acceptable with disclosure.
- Stage 6 custodian sub-check passes vacuously when the legacy labels file is absent
  (documented "expected"); stage 9 silently skips the `pins.json` cross-check when the file is
  absent (`references/public_eval_pins.json` is present, so neither was vacuous in this run).
- Reviewer endpoint substitution: `gemma-4-31b-it:free` failed at task pickup; this review ran
  on `openrouter/qwen/qwen3.8-27b:free`. The same endpoint appears in the private manifest as
  author batch-c and reviewers 68–100 (distinct workers). Recorded for the provenance record.
- `staging/_pre_repair/` does not exist; the apply_repairs.py backup bug is historical with no
  residue.

## 7. Custody statement

The reviewer listed the private eval directory top-level only (existence check) and read no
private file contents; no `review/` or `authored/` subdirectory listing was made; no
`questions.json`, `labels.json`, `counts.json`, or `seal.sha256` was read directly. All
private-hash verification was performed by the verifier itself (stage 10 opaque byte
comparison; seal verification against the in-repo digest). No custody violation on the
reviewer's side.

## 8. Reviewer identity and endpoint

- Worker: fresh independent Round 0 freeze reviewer (no nested spawning; all work performed in
  the top-level session).
- Endpoint: `openrouter/qwen/qwen3.8-27b:free` (verified free; recorded substitution for the
  failed assignment endpoint `gemma-4-31b-it:free`).
