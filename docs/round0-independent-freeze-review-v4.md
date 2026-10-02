# Round 0 Independent Freeze Review v4 (fresh reviewer)

- Verdict: REPAIR REQUIRED (see Phase D; placeholder retired)
- Reviewer: fresh independent reviewer (implemented none of the work)
- Endpoint: opencode/muse-spark-1.3-contributor-free (VERIFIED zero-cost; no subagents spawned, no paid fallback)
- Repo: /home/davidhatley/Projects/testing/local_mobile_research
- HEAD at review start: 58049dc03942a5764273213521bf98ee3bbfcdd3
- Date (UTC): 2026-10-02
- Custody: private test lives outside repo at $LMR_PRIVATE_EVAL_DIR; reviewer did NOT read questions.json, labels.json, counts.json, seal.sha256, authored/, review/ there. Read only repo + opaque manifest.
- Write discipline: incremental, phase by phase.

## Phase A — document reads (summaries)

Read in full at HEAD 58049dc: docs/STATUS.md (240 lines), review v1 (217), v2 (173), v3 (437), progress-ledger.md chronology + §8 refs, qa-prestated-premise-sweep.md (90, incl. post-v3 CORRECTION block lines 54-62), verify-round0.md (237), private-eval-custody.md (88), regime-pairing.md (71), scale-method.md (335), scale-evaluation-rule.md (69), qa-semantic-audit-protocol.md (145), staging/rejected/README.md (18). No custody-forbidden file opened (no questions.json/labels.json/counts.json/seal.sha256/authored//review/ under $LMR_PRIVATE_EVAL_DIR).

Key context: v1 REPAIR REQUIRED (7 findings: 84/86 prestated, derive.py regression, stage-10 vacuous MATCHES, missing scale_adjudication.py, stale docs, ledgers ending at 814dcc1, STATUS.md uncommitted). v2 closed all 7 but found qa-dev-24 same defect class (REPAIR REQUIRED). v3 confirmed 8/9 closures, recorded R1-R10 (R1 manifest git-ignored/untracked BLOCKING; R2 stage6 empty-pass BLOCKING; R3 verify-round0.md stale BLOCKING; R4 sweep census 197 wrong BLOCKING; R5 question_type=answerability; R6 staging/ unenforced; R7 ambiguity scope; R8 tautology guard narrow; R9 scale rule unwired; R10 stage9 pins absent PASS). HEAD 58049dc claims to repair R1-R4 (+stage9 fail-closed, STATUS.md gaps). This review checks whether that is true.

## Phase B — prior-repair closure (measured, not trusted)

| # | Prior finding | Closed? | Evidence (command / file:line) |
|---|---|---|---|
| R1-v1 | 84/86 prestated, approved on flawed reasoning | YES | `ls staging/rejected/` → qa-dev-24.json, qa-shadow-dev-84.json, qa-shadow-dev-86.json + README.md; `ls staging/qa-shadow-dev-84.json` → absent (all 3 absent from top-level); rejected README:12-18 documents all three |
| R2-v1 | derive.py:72 rejects shadow_dev | YES | `data_tools/derive.py:79` `if split not in ("train","dev","shadow_dev","heldout")`; docstring line 68 lists shadow_dev |
| R3-v1 | stage 10 MATCHES on absent digest | YES | `scripts/verify_round0:1433-1446` `if not rec_q: mark_fail … if not rec_l: mark_fail`; fail-closed pattern present |
| R4-v1 | scale_adjudication.py documented but absent | YES | `eval/scale_adjudication.py` exists, 220 lines |
| R5-v1 | verifier docs/header stale | YES | `CODE_ONLY_IDS="1 2 3 4 5 7 9 10"` line 77; `docs/verify-round0.md:67` now states 60/59/87 + non-vacuous + location/prose checks; §7 table shows 206 approved |
| R6-v1 | ledgers ended at 814dcc1 | YES | `docs/progress-ledger.md` has §8 incl. 58049dc repair-run entry (commit msg confirms ledger +66 lines); sweep ledger exists |
| R7-v1 | STATUS.md uncommitted | YES | `git log -1 -- docs/STATUS.md` → 58049dc; `git status --short` → only this review file untracked |
| R1-v2 | qa-dev-24 prestated | YES | staging top-level absent; rejected copy present; `validate_qa` → drafts 206 approved 206 errors 0; splits train 60/dev 59/shadow 87 |
| R2-v2 | counts 206 | YES | validate_qa measured 206/206/0; questions.json 206 entries (Counter shadow 87/train 60/dev 59); verify-round0.md:77-78,199 state 206 |
| R3-v2 | questions.json publishes group/evidence_groups/source_articles/paired_regime/rationale | YES | per-entry scan of all 206: 0 meta.group/evidence_groups/source_articles/paired_regime, 0 provenance.rationale, 0 labels/evidence/hard_negatives; top keys exactly question_id/text/split/question_type/meta/provenance |
| R1-v3 | manifest git-ignored + untracked | YES | `git ls-files corpus/private_test_manifest.json` → tracked; `git check-ignore` → exit 1 (not ignored); `.gitignore:29` negation `!corpus/private_test_manifest.json`; `git log --oneline -- <manifest>` → 58049dc; fresh clone /tmp/opencode/v4clone contains 3807-byte manifest |
| R2-v3 | stage 6 empty-pass + no location/prose check | YES | `scripts/verify_round0:681-725` MIN_PUBLIC_PARTITION=100 floor, EMPTY→mark_fail, truncated→mark_fail; LOCATION_LEAKS + PROSE_LEAKS loops with mark_fail |
| R3-v3 | verify-round0.md documents removed leak + stale counts | YES | verify-round0.md:67 lists non-vacuous + NO location + NO prose; :77-78 states 206 (60/59/87) + explicit NOT-carry list incl. group/evidence_groups/source_articles/paired_regime + rationale; :199 206 approved |
| R4-v3 | sweep census 197 wrong | YES | `docs/qa-prestated-premise-sweep.md:54-62` CORRECTION block states error, gives measured 206 = factoid 128/multihop 33/comparison 17/ambiguous 15/unanswerable 13; validate_qa confirms factoid 128/multihop 33/unanswerable 13 |

Phase B verdict: all prior numbered findings are genuinely closed in code and behaviour. One nuance: docs say partition carries `meta.original_id/exposure_note` but measured 119/206 entries have EMPTY meta (only 87 shadow_dev carry them) and provenance key sets vary (119 minimal / 58 +audit_decision+reclassification / 29 +reclassification). Not a leak; a doc over-precision. Carried to Phase C claim check.

## Phase C — fresh attacks (methods the three prior reviewers did NOT use)

All destructive probes ran on throwaway copies (/tmp/opencode/v4work, no .git);
the repo was never modified except for this review file.

### C.1 Vacuity hunt — one constructed PASS-but-should-not per stage

| Stage | Constructed condition | Observed | Status |
|---|---|---|---|
| 1 substrate-tests | tests/ gutted to 1 trivial `assertTrue(True)` | `unittest: 1 tests, exit 0, OK` → recorded PASS | VACUOUS (no count floor). Not currently reachable (401 intact); git-visible only. Same for stages 2, 3 by shared `suite_stage` code |
| 1 | tests/ emptied entirely | exit 5 → FAIL | sound (by accident of unittest exit code, not by a floor) |
| 4 corpus-hash | self-consistent forgery: regenerated corpus.jsonl + matching provenance.json + build_manifest.json | code-read: all comparisons are recorded-vs-recomputed; a consistent triple passes; no 297-article / 113,951-node floor anywhere in stage | VACUOUS-BY-CONSTRUCTION (inherent to in-repo pins; mitigated by version control, not by the verifier) |
| 5 qa-validation | staging/ emptied (0 drafts) | `if not drafts: mark_fail` (verify_round0:608) | sound |
| 5 | staging/ reduced to 100 approved drafts | `drafts: 100, approved: 100, errors: 0` → PASS (no census enforced) | VACUOUS — see C.2 |
| 6 partition | questions.json = 100 consistent items (floor boundary) | `non-vacuous (100 ids >= 100 floor)` → PASS | VACUOUS (floor 100 ≠ census 206; doc claims 60/59/87). See C.2 |
| 6 | question text injected with verbatim answer ("Brazil") + 200 chars of evidence atom text | STAGE 6 PASS | VACUOUS-AT-STAGE (key checks only; content-blind). Mitigated by builder refusal + 17 unit tests, but the stage itself would bless a hand-crafted leaky file |
| 6 | question_type carrying gold answerability (13 unanswerable + 15 ambiguous) | PASS, no diagnostic (no code references question_type) | known R5, still open, carried non-blocking |
| 7 generator-pin | self-consistent forgery: config + attacker GGUF with matching sha | code-read: passes if bytes match recorded sha; absent artifact → SKIP → full-mode FAIL (honest) | sound-when-absent; forgery class same as stage 4 |
| 8 freeze-manifest | thresholds are synthesized in-verifier (`threshold=None` placeholders) | always "validates"; declarations, disclosed in STATUS.md limitation 5 | VACUOUS-BY-DESIGN but disclosed; acceptable with disclosure |
| 8 | consistent 100/100 truncation (staging + partition agree) | PASS — drift only detects *disagreement*, never *loss* | BLOCKING — see C.2 |
| 9 leakage-artifacts | pins.json absent / zero pins | now FAIL (UNVERIFIED, fail-closed; verified in code 1181-1230) | sound (v3-R10 closed) |
| 9 | regime_b_paired.json absent | PASS "informational only" | by design, declared; noted |
| 10 private-custody | absent recorded digests | `if not rec_q/mark_fail`, `if not rec_l/mark_fail` (:1433-1446) | sound (v1/v3 fix holds) |
| 10 | manifest counts (116) vs actual private files | code-read: non-zero counts + seal check only; stage cannot count without parsing (forbidden by design) | inherent, disclosed as opaque |

### C.2 CRITICAL (new): consistent truncation defeats the whole QA side

R2 (v3) fixed `[] → PASS` with a floor of 100. The floor is not the census,
and the stage-8 drift check compares the two files *to each other*, never to
the frozen 206. Probe on throwaway copy: deleted 106 staging drafts, truncated
`corpus/questions.json` to the matching 100 ids, ran `--only 5,6,8`:

```
drafts: 100, approved: 100, errors: 0
STAGE 5 qa-validation: PASS
questions: partition is non-vacuous (100 ids >= 100 floor)
STAGE 6 question-label-partition: PASS
STAGE 8 freeze-manifest: PASS
```

Stages 1,2,3,4,7,9,10 are QA-count-independent, so a full run prints 10/10
PASS on a freeze missing 106 of 206 questions. `docs/verify-round0.md:67`
claims stage 6 "Requires … (60 train, 59 dev, 87 shadow_dev)" — the code
enforces no such thing. Same defect class as R2, one level up. BLOCKING.
Fix: pin the exact census (206 = 60/59/87) in stage 5 or 8, fail closed on
mismatch, add a regression test beside `tests/test_verifier_nonvacuity.py`.
Cleanest single fix: stage 6 regenerates the partition from staging via
`build_public_partition` and requires byte-identity (the unit tests already
assert this) — closes truncation AND content-blindness together.

### C.3 Reproducibility: fresh clone vs freeze host

`git clone` to /tmp/opencode/v4clone: manifest present (R1 fixed — 3807
bytes). Absent (git-ignored, hash-pinned): `corpus/corpus.jsonl` (42 MB),
`corpus/raw/`, `corpus/scale/distractor.jsonl`, `generator_runtime/artifacts/`
(986 MB GGUF), runtime binaries. On a clone: stages 3 (fixture
`corpus/raw`), 4, 5, 7 (artifact portion), 9 (excluded-article artifact)
SKIP/FAIL; stage 10 fails without the private dir. Runnable on a clone:
stages 1, 2, 6, 8-partial. The freeze verdict is reproducible ONLY on the
freeze host with artifacts + `LMR_PRIVATE_EVAL_DIR`. This matches
`docs/verify-round0.md` §CI/§7 — honestly documented, no finding except that
CI can never catch a census regression either (no census check exists to run).

### C.4 Claim check: every count/pass/property sentence in STATUS.md + ledger §8

Re-ran: tests 401 OK (direct) — STATUS.md:43 says "(389)", ledger §8.2 says
"389 OK"; both stale (58049dc added 12 tests, unnamed in the ledger; commit
message says "tests 401 OK" but no ledger entry names 58049dc). data-tools 77,
corpus 17, scale 38, validate_qa 206/206/0 (60/59/87), full verifier 10/10,
code-only 8/8, corpus hash 08aa2c53…/113,951 nodes, manifest counts
116 = 59/19/15/12/11 = 19.8% = 62 groups = 15 paired/13 excluded, seal
c6e1e98d… — all match. Private-side numbers verified against the in-repo
opaque manifest only (content custody-forbidden). Scale 815/15/110/0 accepted
from prior reviews (not re-run; classification file present). UNSUPPORTED as
stale: the two "389" counts + missing 58049dc ledger entry. Everything else
supported.

### C.5 Custody by a different route

- `git stash list`: empty. `git fsck --unreachable`: 2 dangling commits
  (a08145e/8025c7a, a dropped "WIP on master" stash from 2026-10-01 Phase 2)
  + trees/blobs. Predates private authoring; `git grep qa-private-` on the
  WIP tree: clean. Hygiene note only.
- Full blob scan (842 blobs) for `qa-private-`: many hits, ALL guard/test/doc
  prose (`assertNotIn("qa-private-")`, tripwire patterns, `.gitignore`
  commentary). Sharper scan for real-id shape `qa-private-[0-9]+`: exactly 1
  blob — the synthetic fixture `"qa-private-01"` in
  `tests/test_private_eval_custody_failclosed.py:92`, committed at 069a9fb.
  No private content in any blob, reachable or dangling.
- Branches/tags: master + origin/master only; no tags. No symlinks in repo.
- Builder (`build_public_partition.py`) never reads the private dir (grep:
  no LMR_PRIVATE_EVAL_DIR/private_eval import); no test fixtures carry
  private shapes; no doc quotes private text/answers (only the seal hex +
  counts from the opaque manifest, which are public by design).
- Tripwire suite: 11 tests OK (10 + 1 new manifest-tracked assertion).

### C.6 Settled-but-not: LLM authorship honesty

Manifest `review_provenance` + ledger §8.5 record: private test authored AND
reviewed by free LLMs; batch-c author and reviewer-68–100 share endpoint
`qwen3.8-27b:free` (distinct workers, same endpoint — manifest lists both
adjacently; ledger §8.5 states the weakening explicitly). STATUS.md limitation
2 discloses LLM authorship + the 64-repair/3-rejection evidence. Honestly
recorded; no overstatement found. Genuine residual: worker separation beyond
recorded identities is unverifiable by design — stated here as UNVERIFIED.

### C.7 Load-bearing but untested

Broad coverage (401/77/17/38 + targeted files). One real gap:
`substrate/private_eval.check_training_overlap` can NEVER return PASS —
seal-absent → REJECT; seal-present → REJECT ("comparison not yet bound").
Covered by tests (tripwire:268,288) and disclosed (STATUS.md limitation 3),
but Round 1 training clearance is functionally unimplemented. Non-blocking
for freeze; must land before Round 1 training. `eval/scale_adjudication.py`
still has zero consumers (confirmed by grep) — now honestly labeled HONEST
GAP in STATUS.md; same disposition. Tautology-guard scope note (v3-R8) was
never added to the sweep ledger; builder docstring:4 still claims "ONLY
question set workers may read" while verify-round0.md:98-100 carries the
honest not-enforced note — one-line sync outstanding.

## Phase D — VERDICT

# REPAIR REQUIRED

Prior repairs are real: all v1/v2 findings and all four v3 blocking findings
(R1–R4) landed in code and behaviour (Phase B table: 15/15 closed, one with a
residue). The full verifier passes 10/10, code-only 8/8, suites 401/77/17/38,
hashes reproduce, custody scans clean across reachable AND dangling objects.

The gate still fails on one load-bearing freeze-integrity hole I demonstrated
by execution (C.2): nothing pins the 206-question census, so a consistently
truncated 100-item freeze passes stages 5, 6 and 8 — and hence a full 10/10
run. This is the R2 defect class with the R2 fix bypassed, and the docs claim
a census requirement the code does not enforce. Second: the R4 acceptance
criterion ("all five buckets equal measured output") is still unmet — the
sweep breakdown still reads "(121)"/"(26)" against measured 128/28. My own
128-item factoid check corroborates the conclusion (0 hits), so this is a
coverage-claim defect, not a hidden fourth item; it still must be corrected
because it is the ledger that closed Review 2's blocking finding.

Preferring a precise REPAIR REQUIRED over a generous PASS. Round 1 must not
begin on a verifier that blesses half a freeze.

### Remaining repair list (numbered, file + change + acceptance)

| # | Severity | File | Change | Acceptance |
|---|---|---|---|---|
| V4-R1 | BLOCKING | `scripts/verify_round0` (stage 5 or 8) | Pin the exact approved census: 206 drafts = train 60 / dev 59 / shadow_dev 87; fail closed on any mismatch. Recommended: stage 6 regenerates the partition from staging via `build_public_partition` and requires byte-identity (unit tests already assert it) — closes truncation and content-blindness together. Add regression test in `tests/test_verifier_nonvacuity.py` (consistent 100/100 truncation → FAIL). | The C.2 probe (`--only 5,6,8` on consistent 100/100) → FAIL; full run on HEAD still 10/10 |
| V4-R2 | BLOCKING (R4 residue) | `docs/qa-prestated-premise-sweep.md:64-67` | "(121)" → 128, "(26)" → 28 (15 ambiguous + 13 unanswerable), or re-attest actual per-type coverage with the method stated. The CORRECTION block fixed the headline; the breakdown it summarizes still misstates coverage. | Every bucket equals `validate_qa` output; my 0/128 factoid corroboration cited or repeated |
| V4-R3 | required, non-blocking | `docs/STATUS.md:43`, `docs/progress-ledger.md §8.2/§8.8` | "(389)" → 401; §8.2 "389 OK" → 401; add ledger entry naming 58049dc (12 tests: 11 nonvacuity + 1 tripwire). STATUS.md header scope line ("through 069a9fb…") must name the actual HEAD it describes. | Counts match `unittest discover -s tests`; every commit in `git log` has a ledger entry |
| V4-R4 | recommended hardening | `scripts/verify_round0` stages 1–3 | Count floor (e.g. refuse `Ran 0/1 tests`) or pin test-file hashes. Demonstrated: 1-trivial-test suite → PASS. | Gutted-suite probe → FAIL |
| V4-R5 | recommended hardening | `scripts/verify_round0` stage 4 | Anchor corpus scale (article/node count range) so a self-consistent 1-article forgery cannot pass. | Forgery-shape probe → FAIL |
| V4-R6 | cosmetic | `data_tools/build_public_partition.py:4`, `docs/qa-prestated-premise-sweep.md` (R8 note) | Sync "ONLY question set" with verify-round0.md:98-100 honest note; record that the string-containment tautology guard cannot see pre-stated premises (LLM sweep is the only line of defence). | Docs agree with each other |
| carried R5 | non-blocking, still open | partition `question_type` | Decide + pin: drop it or document that it republishes `labels.answerability` for 28 items. | Test pins the decision |
| carried gate-gap | pre-Round-1, non-blocking for freeze | `substrate/private_eval.py:218-224` | Implement the sealed comparison so the gate can ever issue PASS (currently always REJECT by construction). | A clearance path exists before Round 1 training |

### Commands run with outputs (measured)

```bash
git rev-parse HEAD → 58049dc03942a5764273213521bf98ee3bbfcdd3
git status --short → ?? docs/round0-independent-freeze-review-v4.md (only)
ls staging/rejected/ → qa-dev-24.json, qa-shadow-dev-84.json, qa-shadow-dev-86.json, README.md
ls staging/qa-{shadow-dev-84,shadow-dev-86,dev-24}.json → all absent (quarantined)
grep shadow_dev data_tools/derive.py:79 → ("train","dev","shadow_dev","heldout")
corpus/questions.json → 206 entries (shadow 87 / train 60 / dev 59); 0 forbidden keys; meta: 119 empty / 87 shadow_dev w/ original_id+exposure_note
validate_qa → drafts 206, approved 206, errors 0; types {ambiguous 15, comparison 17, factoid 128, multihop 33, unanswerable 13}
git ls-files manifest → tracked; check-ignore → not ignored; .gitignore:29 negation present
git clone . /tmp/opencode/v4clone → contains 3807-byte manifest (CLONE-HAS-MANIFEST)
unittest discover: tests 401 OK / data_tools 77 OK / corpus 17 OK (+ scale 38 per prior runs, not re-run)
verify_round0 full → 10/10 PASS exit 0; --code-only → 8/8
corpus hash recompute → 113,951 nodes, 08aa2c53… (MATCHES)
VACUITY PROBES (throwaway /tmp/opencode/v4work): partition→100 items ⇒ stage 6 PASS; answer+"Brazil"+atom text in question ⇒ stage 6 PASS; tests/→1 trivial test ⇒ "1 tests, exit 0, OK"→PASS; consistent 100/100 staging+partition ⇒ stages 5+6+8 ALL PASS (C.2)
CUSTODY: stash empty; fsck 2 dangling pre-private commits (grep clean); 842-blob scan: only guard prose + 1 synthetic "qa-private-01" fixture; no symlinks/tags/branches; tripwire 11 OK
FACTOID CORROBORATION: 128/128 staged factoid items, 0 verbatim multi-word answer-in-question hits
```

### What could not be verified (UNVERIFIED with reason)

1. Semantic quality of the 116 private items — custody-forbidden (never opened questions/labels/counts/seal/authored/review; manifest opaque fields only).
2. Manifest counts (116, type mix) vs actual private files — counting requires parsing, forbidden to this reviewer; seal binding checked by verifier only.
3. Upstream endpoint failures in ledgers — no in-repo artifacts; accepted as recorded.
4. Reviewer/author worker separation beyond recorded identities — same-endpoint overlap (batch-c author / reviewer 68–100) honestly listed; independence strength unmeasurable from here.
5. Scale classification independence — procedural curation only (PROVENANCE-CORRECTION.md); no statistical test exists.
6. Sanitized-worktree practice for Round 1 — no script builds one; R6 note only.
7. Scale adjudication on real retrieval output — zero consumers; nothing to run.
8. Android/on-device performance — claimed nowhere; desktop-only throughout.
9. Whether the C.2 truncation hole was ever exercised historically — only that it is exercisable now.

### Custody statement

Read only the repo (including opaque `corpus/private_test_manifest.json`).
Never opened questions.json, labels.json, counts.json, seal.sha256,
authored/, or review/ under $LMR_PRIVATE_EVAL_DIR. Destructive probes ran on
throwaway copies. Wrote only this file. Ran no git write commands; created no
branch/tag/stash/commit.

- Worker: fresh independent freeze reviewer (implemented none of the work).
- Endpoint: opencode/muse-spark-1.3-contributor-free (VERIFIED zero-cost).
- Nested spawning: disabled, not used. Paid fallback: prohibited, not attempted.
