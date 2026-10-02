# Round 0 Independent Freeze Review — v3

**Verdict: REPAIR REQUIRED** — see §PHASE D and the remaining repair list.
*Updated after completion of Phases A–D; the `IN PROGRESS` placeholder is retired.*

| Field | Value |
|---|---|
| Reviewer | Fresh independent freeze reviewer (subagent, implemented none of the work) |
| Endpoint | `opencode/space-bunny-free` (verified zero-cost) |
| Repo | `/home/davidhatley/Projects/testing/local_mobile_research` |
| HEAD under review | `d17cb31` |
| Prior repair commits | `069a9fb`, `d17cb31` |
| Date | 2026-10-02 |
| Scope | Round 0 freeze gate re-review after two REPAIR REQUIRED rounds |

## Endpoint substitution record

Two endpoints failed on this assignment before this reviewer was reached:
1. `qwen3.8-27b:free` — provider error.
2. `nemotron-3.5-lightning-free` — garbled output, wrote nothing.

This reviewer is the **second recorded substitution** and runs as
`opencode/space-bunny-free`, which is verified zero-cost. No paid fallback was
attempted. Nested spawning was disabled for this assignment; no subagents were
spawned.

## Custody declaration

This reviewer is **not** the private custodian reviewer. The private test tree at
`/home/davidhatley/Projects/testing/local_mobile_research-private-eval/` was not
opened: `questions.json`, `labels.json`, `counts.json`, `seal.sha256`,
`authored/`, and `review/` were not read. Only the repo itself, including the
opaque `corpus/private_test_manifest.json`, was read.

The only file written by this reviewer is
`docs/round0-independent-freeze-review-v3.md`. No git write commands were run.

---

## PHASE A — documents read

Read in full: `docs/STATUS.md` (227 lines), `docs/round0-independent-freeze-review.md`
(217), `docs/round0-independent-freeze-review-v2.md` (172), `docs/progress-ledger.md`
§8 (lines 330–458), `docs/qa-prestated-premise-sweep.md` (77),
`docs/verify-round0.md` (214), `docs/private-eval-custody.md` (88),
`docs/regime-pairing.md` (71), `docs/scale-method.md` (1–60 plus §1.1 by grep),
`docs/scale-evaluation-rule.md` (68), `staging/rejected/README.md` (18).

No custody-forbidden file was opened.

---

## PHASE B — did the prior repairs actually land?

Every claim below was re-measured on this host; none was taken on trust.

### B.1 Review 1's seven findings

| # | Review 1 finding | Closed? | My evidence |
|---|---|---|---|
| 1 | `qa-shadow-dev-84` / `-86` pre-stated the years they compared | **YES** | `staging/rejected/` contains exactly `qa-shadow-dev-84.json`, `qa-shadow-dev-86.json`, `qa-dev-24.json`, `README.md`. Both shadow-dev ids are absent from `staging/*.json` and from `corpus/questions.json`. `staging/rejected/README.md` documents both with defect text and states the honest consequence (dev 59, shadow_dev 87). Measured approved census: `train 60 / dev 59 / shadow_dev 87 = 206`. Consistent. |
| 2 | `data_tools/derive.py:72` rejected every `shadow_dev` group | **YES** | `data_tools/derive.py:79` now reads `if split not in ("train", "dev", "shadow_dev", "heldout")`. `tests/test_group_split_vocabulary.py` — 9 tests, all pass. |
| 3 | stage 10 printed "MATCHES" on an **absent** recorded digest | **YES** | `scripts/verify_round0:1378–1391` now has explicit `if not rec_q: mark_fail()` / `if not rec_l: mark_fail()` branches before any comparison. `tests/test_private_eval_custody_failclosed.py` — 8 tests, all pass, including `test_missing_recorded_questions_hash_fails` and `test_missing_recorded_labels_hash_fails`. I also probed it directly: zeroing `counts.total` in the manifest drives stage 10 to FAIL. Fail-closed confirmed in code and in behaviour. |
| 4 | `eval/scale_adjudication.py` documented but absent | **YES** | File exists, 220 lines. `tests/test_scale_adjudication.py` — 12 tests, all pass. |
| 5 | verifier header / `--help` / `docs/verify-round0.md` stale | **PARTIAL** | The header/`--help`/`CODE_ONLY_IDS` are fixed. But `docs/verify-round0.md` was **not** updated for the `d17cb31` public-partition fix and still carries three stale/false claims — see finding **R3**. |
| 6 | ledgers ended at `814dcc1` | **YES** | `docs/progress-ledger.md` §8.1/§8.5/§8.7 exist and cover `937b3c5`…`069a9fb` and the second review. `docs/qa-prestated-premise-sweep.md` exists. Minor count staleness — see **R4**. |
| 7 | `docs/STATUS.md` uncommitted while HEAD said "NOT FROZEN" | **YES, with defects** | `git log -1 -- docs/STATUS.md` → `d17cb31`; tracked and committed. But its *content* now overstates/misstates — see **R3**, **R5**. |

### B.2 Review 2's three findings

| # | Review 2 finding | Closed? | My evidence |
|---|---|---|---|
| 1 | `qa-dev-24` pre-stated both compared magnitudes | **YES** | `staging/qa-dev-24.json` no longer exists at the staging top level; `staging/rejected/qa-dev-24.json` exists and is excluded from `corpus/questions.json`. |
| 2 | counts must read 206, not 207 | **PARTIAL** | The **verifier** is correct: stage 5 prints `drafts: 206, approved: 206` and `{"dev": 59, "heldout": 0, "private_test": 0, "shadow_dev": 87, "train": 60}`. `docs/STATUS.md:47,76,88` is correct (206). **But** `docs/verify-round0.md:176` still says "207 approved drafts", and `docs/verify-round0.md:67,77` still say "209 items / 60 train, 50 dev, 89 shadow_dev". See **R3**. |
| 3 | `corpus/questions.json` must stop publishing `meta.group`, `meta.evidence_groups`, `meta.source_articles`, `provenance.rationale` | **YES — verified clean** | Measured on the committed file: top-level keys are exactly `question_id, text, split, question_type, meta, provenance`; `meta` keys are exactly `original_id, exposure_note`; `provenance` keys are exactly `author, author_model, decision, verifier, verifier_model, audit_decision, reclassification`. No `group`, no `evidence_groups`, no `source_articles`, no `paired_regime`, no `rationale`. Re-ran my own per-entry adversarial audit: **0** answer-text occurrences, **0** evidence-atom texts, **0** hard-negative texts, **0** `absent_reason` texts anywhere in the file. |

**B verdict: 8 of 9 prior findings are genuinely closed. The answer/location leak fix is real
and effective — this is the strongest repair in the two rounds.** One documentation
cluster (R3) and one count claim (R4) remain open, and Phase C produced new findings.

---

---

## PHASE C — fresh adversarial attack

Everything in this section was executed, not reasoned about. All destructive probes
were run against a throwaway copy at `/tmp/opencode/v3copy` (an `rsync` copy with
`generator_runtime/`, `corpus/raw/` and `.git` excluded). The real repository was
never modified except for this review file.

### C.1 Verifier re-runs (measured)

| Command | Result |
|---|---|
| `LMR_PRIVATE_EVAL_DIR=… ./scripts/verify_round0` | **10/10 PASS**, exit 0 |
| `./scripts/verify_round0 --code-only` | **8/8 PASS** (stages 1,2,3,4,5,7,9,10), exit 0 |
| `python3 -m unittest discover -s tests` | **389 tests OK** (direct; verifier reports 350 — the 39 entrypoint tests are skipped in-verifier) |
| `python3 -m unittest discover -s data_tools/tests` | 77 OK |
| `python3 -m unittest discover -s corpus/tests` | 17 OK |
| `python3 -m unittest discover -s corpus/scale/tests` | 38 OK |
| `python3 -m unittest tests.test_private_eval_custody_failclosed` | 8 OK |
| `python3 -m unittest tests.test_group_split_vocabulary` | 9 OK |
| `python3 -m unittest tests.test_scale_adjudication` | 12 OK |
| `python3 -m unittest tests.test_public_partition` | 17 OK |
| stage 5 `validate_qa` | `drafts: 206, approved: 206, errors: 0`; splits `train 60 / dev 59 / shadow_dev 87` |

`docs/STATUS.md`'s "shared substrate tests (389)" is **correct** (direct run).
Corpus hash reproduced: `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1`.

### C.2 Do the 17 new tests actually bite? — YES (proven, not asserted)

I built a deliberately leaky `corpus/questions.json` in the temp copy:
injected `meta.group` + `meta.source_articles` into `qa-dev-11`, a `labels.answer_text`
block into `qa-dev-12`, and an answer-naming `provenance.rationale` into `qa-dev-13`.

```
python3 -m unittest tests.test_public_partition
FAIL: test_no_forbidden_fields        AssertionError: '"labels"' unexpectedly found … qa-dev-12
FAIL: test_no_answer_location         AssertionError: 'group' unexpectedly found … qa-dev-11
Ran 17 tests … FAILED (failures=3)
```

Three tests fail; the tests are **not** vacuous. Stage 6 of the verifier also FAILs
on the `labels` leak (`entry qa-dev-12 contains forbidden field(s) ['labels']`).

**But** stage 6 reported **nothing** about the injected `meta.group` /
`source_articles` / `rationale` leak — see R3.

`git diff 069a9fb..d17cb31 --stat` shows `tests/` gained only
`tests/test_public_partition.py` (+225). **No test was weakened, deleted, or made
tautological** by the new work.

### C.3 Vacuous-pass hunt (probed, not reasoned)

Every probe below was run against the temp copy and the stage verdict read off the
real verifier.

| Probe | Mutation | Observed | Verdict |
|---|---|---|---|
| **A** | `corpus/questions.json` = `[]` | `questions: 0 ids, 0 structural error(s)` → `STAGE 6 … PASS` | **VACUOUS PASS — see R2** |
| A3 | same, stages 5,6,8 | stage 8 → `gap: partition drift: 206 approved draft(s) are not published` → FAIL | full run does catch it |
| **B** | leaky partition (`labels`, `meta.group`, `rationale`) | stage 6 FAIL (on `labels` only) | partial — location leak not seen by stage 6 |
| **C** | delete `references/pins.json` | `references/pins.json absent: no local cross-check available` → `STAGE 9 … PASS` | **vacuous degradation — R10** |
| **D** | delete `corpus/regime_b_paired.json` | `absent (informational only)` → `STAGE 9 … PASS` | declared informational by design |
| F | empty `regime_b_excluded_articles.articles` | `INCONSISTENT (0 recorded vs 21 derived)` → FAIL | sound |
| G | zero `private_test_manifest.counts.total` | `carries no counts` → `STAGE 10 … FAIL` | sound |
| G2 | remove recorded `questions_json_sha256` | fail-closed (8 dedicated tests) | sound |
| I | inject answer string into a staging question | `qa-dev-11: question contains answer verbatim (tautological)`, errors 1; restored → 0 | schema guard is genuine |
| J | `labels.answerability` / `question_type` coupling | `qa_schema.py:233-236` enforces equivalence | see R5 |

### C.4 Public-partition adversarial audit (what Round 1 workers actually see)

Measured on the committed `corpus/questions.json` (206 entries):

| Probe | Result |
|---|---|
| top-level keys | exactly `question_id, text, split, question_type, meta, provenance` |
| `meta` keys | exactly `original_id, exposure_note` |
| `provenance` keys | `author, author_model, decision, verifier, verifier_model, audit_decision, reclassification` |
| `meta.group` / `evidence_groups` / `source_articles` / `paired_regime` | **absent** |
| `provenance.rationale` | **absent** |
| answer text in own entry (long answers, >8 chars) | **0** |
| answer text in own entry (short answers ≤8 chars — the exempt class) | **0** |
| evidence atom texts (first 80 chars) | **0** |
| hard-negative texts | **0** |
| `absent_reason` texts | **0** |
| `qa-private-` ids | 0 |
| `split=heldout` / `split=private_test` | 0 |

**Self-correction, recorded deliberately.** My first pass searched the *whole file
as one blob* and reported 22 apparent answer leaks (8 of them "long"). That method is
wrong: it matches an answer against an unrelated item's question text. Re-run
**per entry** — the correct semantics, and what the shipped checks do — the count is
**0**. I am recording my own error so the next reviewer does not reproduce it.

**The leak the allowlist misses: `question_type` (R5).** The partition publishes
`question_type` for all 206 items, including `unanswerable` (13) and `ambiguous` (15).
`data_tools/qa_schema.py:233-236` makes `question_type == "unanswerable"` **equivalent**
to `labels.answerability == "unanswerable"` (same for `ambiguous`). So the published
field *is* the gold abstention/hedging label, under a name that is not on
`FORBIDDEN_KEYS`. A system reading the partition knows in advance exactly which 13
items to abstain on. See R5 for the honest severity calibration.

### C.5 Pre-stated-premise sweep — a different method than the year heuristic

Four orthogonal probes over all 206 approved items (`/tmp/opencode/sweep3.py`):

**S1 — answer-token coverage (token overlap, not substring).** Three items have
100% of their answer's content tokens present in the question; all three are generic-word
false positives: `qa-train-14` ("eclipse season" ← "lunar eclipse … which recurring
season"), `qa-shadow-dev-56` ("University District" ← "The **university** … which
**district** of Seattle"). `qa-shadow-dev-19` is borderline — see the design note below.

**S2 — decisive measures for BOTH compared sides (adjectives/nouns vs. dates, as
asked).** Extracted numerals/units and years from all 17 comparison items. Five state
two or more measures: `qa-pilot-dev-05` (56% / 159.2M), `qa-shadow-dev-47` (2 g),
`qa-shadow-dev-85` (1636), `qa-train-03` (12.8%), `qa-train-18` (1066). I adjudicated
each by hand: in every case **only one side's** decisive measure is stated, and the
question asks for the other side's value. **None is pre-stated.** This corroborates
Review 2's adjudication of `qa-pilot-dev-05` and `qa-shadow-dev-85`.

**S3 — unanswerable items whose `absent_reason` reveals the answer.** All 13 examined.
No `absent_reason` names an answer; several cite the node id holding the near-answer
(`qa-dev-20`: "only the year 1866"), but that is the *justification* for unanswerability
and lives in `staging/` (dev-visible), not in the published partition — where
`absent_reason` is on `FORBIDDEN_KEYS` and measured absent.

**S4 — items where the question names the entity the evidence must identify.**
123 hits, but every one is a topic word or a named entity the question legitimately
uses (`qa-train-13` "solar eclipse" ← article `a:solar_eclipse`; `qa-shadow-dev-07`
group word "jaguar" ← an Atari-Jaguar question). Naming the subject of a question is
not the pre-stated-premise class. Recorded instead as a **design risk** below.

**Conclusion: no fourth instance of the pre-stated-premise defect class exists in the
206 approved items.** The sweep's own coverage claim is nevertheless wrong — R4.

### C.6 Custody — can private content reach the repository?

| Probe | Result |
|---|---|
| `git log --all --diff-filter=A --name-only` | 381 paths ever added. The only private-sounding ones are `docs/private-eval-custody.md`, `substrate/private_eval.py`, the two custody test files, and the 89 historical `staging/qa-heldout-*.json` (already documented Issue 1). |
| content scan of **every git blob** for `qa-private-` / sealed-label shapes | only 3 hits, all benign text in `.github/workflows/verify-round0.yml`, `docs/progress-ledger.md`, `docs/substrate-implementation-review-v03.md` (tripwire/guard prose). **No private content in any blob.** |
| branches / tags / stash | `master` + `origin/master` only; **no tags, no stash** |
| `.gitignore` private patterns | `corpus/labels.json`, `corpus/heldout_labels.sealed.json`, `*private*label*`, `qa-private-*.json`, `*.seal`, `seal.sha256`, `*private_eval_dir*` — all correct **except** the over-broad `*private_test*.json` (R1) |
| in-repo manifest content | stage 10 verifies it is content-free (no `qa-private-`, no `answer_text`, no `sufficient_sets`) — reproduced |
| public partition ids | no `qa-private-` prefix |
| private dir resolution | `assert_private_dir_outside_repo()` passes |

**However — see R1. The custody boundary has a hole that is not about private content
leaking *in*. It is about the artifact that *binds* the private test never being in
the repository at all.**

---

## PHASE D — VERDICT

# REPAIR REQUIRED

The two repair rounds did real work. The `d17cb31` public-partition fix is the
strongest repair in this project so far: I attacked it specifically, constructed a
deliberately leaky file, and confirmed the new tests are genuine probes rather than
decoration. Eight of nine prior findings are genuinely closed. **None of my blocking
findings is a semantic-QA defect** — the approved set survives an orthogonal
pre-stated-premise sweep with no new instance.

The gate still fails on **freeze integrity and on documentation that now asserts
things the repository does not do.** One previously-undetected defect (R1) means the
private test is bound to a file that is not in version control, so nothing in the
freeze actually pins it. That alone is disqualifying: a freeze that does not contain
the artifact carrying the private seal is not a freeze of the thing being claimed.

I prefer a precise REPAIR REQUIRED over a generous PASS. Round 1 should not begin.

---

## Verdict table

| Gate element | Holds? | Basis |
|---|---|---|
| Shared substrate code correctness | **YES** | 389 + 77 + 17 + 38 tests OK; 8/8 code-only, 10/10 full |
| Structural verification machinery is honest | **PARTIAL** | Stage 10 now fails closed (code + 8 tests + probe). **Stage 6 passes vacuously on an empty partition (R2)**; stage 9 silently degrades when `references/pins.json` is absent (R10) |
| Corpus / splits / hashes / pins | **YES** | corpus hash reproduced; 297 articles / 113,951 nodes; 218 groups |
| QA approval bookkeeping | **YES** | 206 drafts / 206 approved / 0 errors; 3 rejected and quarantined |
| Pre-stated-premise defect class eradicated | **YES (corroborated)** | 4 orthogonal probes; no 4th instance |
| Public partition carries no answer / answer location | **YES** | per-entry audit: 0 answer, 0 atom, 0 hard-negative, 0 `absent_reason` occurrences |
| Public partition carries no reading labels | **NO (R5)** | `question_type` == gold `answerability` for 28 items |
| Leak control is *enforced* | **NO (R6)** | nothing excludes `staging/` (full answers for all 206) from a worker worktree |
| Private test is bound to **this repository** in **version control** | **NO (R1)** | `corpus/private_test_manifest.json` is untracked **and** git-ignored; absent from a clone |
| Private content cannot reach the repo | **YES** | 381 paths, full blob scan, no tags/stash, tripwire passes |
| Scale adjudication is implemented in the measurement path | **NO (R9)** | `eval/scale_adjudication.py` has **no consumer**; neither `eval/metrics.py` nor `eval/support.py` mentions scale, distractor, false positives, or adjudication |
| Documentation matches behaviour | **NO (R3, R4, R9)** | `docs/verify-round0.md` documents the removed leak as present; three stale counts; the sweep ledger claims "all 197" when there are 206 |
| **Round 0 freeze gate** | **NOT MET** | R1, R2, R3, R4 |

---

## Fresh-attack results — summary

| # | Finding | Severity |
|---|---|---|
| **R1** | `corpus/private_test_manifest.json` is untracked **and** git-ignored (`.gitignore:18`). Never committed; absent from a fresh clone. The private seal is therefore bound to a file with no version-control history, and three documents assert the opposite. | **BLOCKING** |
| **R2** | Stage 6 passes **vacuously** on an empty `corpus/questions.json` (`questions: 0 ids, 0 structural error(s)` → PASS). `docs/verify-round0.md:67` claims stage 6 "Requires" a 60/50/89 partition; it enforces no count, no non-emptiness, no census. Full-run mitigation: stage 8's drift check fails. | **BLOCKING** (doc + stage) |
| **R3** | `docs/verify-round0.md` was not updated for `d17cb31` and now documents the removed leak as present: line 77 says the partition carries `meta (source_articles, group)`. Plus stale/incorrect counts at lines 67, 77 (209 / 60-50-89, sum 199≠209) and 176 (207 approved). Line 67 also claims stage 6 verifies "NO answer text" and implies location checking — measured: stage 6 catches a `labels` key but **not** `meta.group`/`source_articles`/`rationale`. | **BLOCKING** |
| **R4** | `docs/qa-prestated-premise-sweep.md:50` claims a manual review of "all **197** approved items (17 comparison, 33 multihop, **121** factoid, **14** ambiguous, **12** unanswerable)". Measured: **206** approved = 17 comparison, 33 multihop, **128** factoid, **15** ambiguous, **13** unanswerable. The total is 9 short and 3 of 5 buckets are wrong, so the claim "all" is false on its face. This is the ledger that closed Review 2's blocking finding. Also `docs/progress-ledger.md:355` "209 drafts" (measured 206). | **BLOCKING** |
| **R5** | `corpus/questions.json` publishes `question_type`, which `data_tools/qa_schema.py:233-236` makes **equivalent** to the gold `labels.answerability`. 13 `unanswerable` + 15 `ambiguous` labels are republished under a name absent from `FORBIDDEN_KEYS`. Severity is bounded — not a held-out leak, since all 206 published items are dev-visible and `staging/` already ships `answer_text`, `answerability` and full `evidence` for every one of them. | Non-blocking, fix |
| **R6** | `data_tools/build_public_partition.py:4` and `docs/verify-round0.md:77` assert `corpus/questions.json` is the only question set workers may read. Nothing enforces it: `staging/` (206 drafts with answers, atoms and hard negatives) is committed and is excluded only from *private* worktrees per `docs/STATUS.md:173`. No test asserts the policy. | Non-blocking, fix |
| **R7** | `docs/STATUS.md:193-196` (limitation 4) says "**Six** ambiguous **shadow-dev** items put a prose disjunction in `answer_text`". Measured: 6 shadow_dev is right for that split, but **10** across all splits have a disjunction and **5** (`qa-train-02/08/20/26/38`) have a completely **EMPTY** `answer_text` with 2–3 `readings` each — a different hazard, not mentioned. Also, no `answer_text` exact-match scorer exists today (`eval/metrics.py` scores sufficiency / false- / over-abstention), so the sentence describes a hazard for a scorer not yet written. | Non-blocking, fix |
| **R8** | The shipped tautology guard (`qa_schema.py:340-348`) is genuine — I proved it fires — but it is **narrower than the defect class**: it checks answer-*string* containment for `answerable` records only, so all three rejected items passed it (they stated the decisive *facts*, not the answer string). A string-containment guard structurally cannot see pre-stated premises; only the LLM sweep caught them, and per R4 that sweep's coverage claim is wrong. | Non-blocking, harden |
| **R9** | `docs/STATUS.md:138-139` states in the present indicative that "retrieved scale passages do **not** auto-count as false positives; top confusable retrievals are adjudicated". Measured: `eval/scale_adjudication.py` has **no consumer outside its own unit test**, and neither `eval/metrics.py` nor `eval/support.py` contains the strings `scale`, `distractor`, `false_positive`, or `adjudicat`. The rule is specified and unit-tested; it is not wired into any measurement path. | Non-blocking, fix or reword |
| **R10** | Stage 9 prints `references/pins.json absent: no local cross-check available` and still reports PASS. Review 1 flagged this as a latent hole; it was not repaired. `docs/verify-round0.md:70` states stage 9 "cross-checks pin hashes byte-for-byte against `references/pins.json`". | Non-blocking, fix |

### Things I attacked and found CLEAN (recorded so they are not re-litigated)

- **The 17 new tests are not vacuous.** 3 fail against a deliberately leaky committed file.
- **No test was weakened, deleted, or made tautological** by `069a9fb` or `d17cb31`.
- **Stage 10 fails closed** on absent digests — code, 8 dedicated tests, and my own probe.
- **The `d17cb31` answer/location leak fix is real and effective**: 0 answer, 0 evidence-atom, 0 hard-negative, 0 `absent_reason` occurrences in the public partition, per entry.
- **No pre-stated-premise instance beyond the 3 rejected items**, under four probes orthogonal to the year heuristic.
- **No private content in any git blob**; 381 paths audited; no tags, stash, or extra branches.
- Stage 9 fails closed on an emptied excluded-article list and on zeroed manifest counts.
- The `qa_schema` tautology guard fires (probe: errors 1 → restored → 0).

### Design risks NOT recorded anywhere in the project (for the orchestrator, not blockers)

1. **~123 of 206 items name their source entity or group topic word verbatim in the question text.** A title-matching retriever will score very high; the retrieval task is closer to entity linking than open retrieval. `docs/verify-round0.md` §2 disclaims answerability-from-corpus but says nothing about this.
2. **Memorization confound.** Several items are plausibly closed-book answerable from an LLM's parametric knowledge — e.g. `qa-shadow-dev-19` ("the collegiate public research university in Cambridge, England" → *University of Cambridge*). For a RAG tournament this is an unmeasured retrieval-vs-memory confound. No document acknowledges it.
3. Scale is a single point; no scaling curve is possible (already disclosed).
4. Ambiguity scoring is undecided and now blocks 15 items rather than 6 (R7).

---

## Commands run (measured)

```bash
# --- Phase A: reads (no custody-forbidden file opened) ---
git log --oneline -12; git rev-parse HEAD            # d17cb3191cf7c769b6c529969a8c3b488e486e6d
git status --porcelain                                # only ?? docs/round0-independent-freeze-review-v3.md
(read docs/STATUS.md, both prior reviews, progress-ledger.md §8,
 docs/qa-prestated-premise-sweep.md, docs/verify-round0.md,
 docs/private-eval-custody.md, docs/regime-pairing.md,
 docs/scale-method.md, docs/scale-evaluation-rule.md,
 staging/rejected/README.md)

# --- Phase B: verifier re-runs ---
LMR_PRIVATE_EVAL_DIR=…-private-eval ./scripts/verify_round0   → 10/10 PASS, exit 0
./scripts/verify_round0 --code-only                          → 8/8 PASS, exit 0
#   stages: 1 PASS 350 | 2 PASS 77 | 3 PASS 17 | 4 PASS | 5 PASS | 7 PASS | 9 PASS | 10 PASS
python3 -m unittest discover -s tests                        → Ran 389 tests OK
python3 -m unittest discover -s data_tools/tests             → 77 OK
python3 -m unittest discover -s corpus/tests                 → 17 OK
python3 -m unittest discover -s corpus/scale/tests           → 38 OK
python3 -m unittest tests.test_private_eval_custody_failclosed → 8 OK
python3 -m unittest tests.test_group_split_vocabulary          → 9 OK
python3 -m unittest tests.test_scale_adjudication             → 12 OK
python3 -m unittest tests.test_public_partition               → 17 OK
git diff --stat 069a9fb..d17cb31                             → tests/ +225 only, no deletions

# --- Phase C: custody ---
git log --all --diff-filter=A --name-only --format= | sort -u | wc -l      → 381
git branch -a; git tag; git stash list              → master, origin/master; no tags; no stash
git rev-list --objects --all | git cat-file --batch-check=…  → full blob content scan, 0 private hits
git check-ignore -v corpus/private_test_manifest.json        → .gitignore:18:*private_test*.json
git ls-files --error-unmatch corpus/private_test_manifest.json
        → error: pathspec … did not match any file(s) known to git
git log --all --oneline -- corpus/private_test_manifest.json  → (empty; never committed)
git status --porcelain --ignored=matching | grep private     → !! corpus/private_test_manifest.json
git clone -q . /tmp/opencode/clone && ls …/private_test_manifest.json
        → ls: cannot access …: No such file or directory     *** R1 ***

# --- Phase C: vacuous-pass probes (all on /tmp/opencode/v3copy) ---
echo '[]' > corpus/questions.json;  ./scripts/verify_round0 --only 6
        → questions: 0 ids, 0 structural error(s) / STAGE 6 … PASS   *** R2 ***
./scripts/verify_round0 --only 5,6,8   (same state)
        → STAGE 5 PASS; STAGE 6 PASS; STAGE 8 FAIL
          gap: partition drift: 206 approved draft(s) are not published
python3 (inject meta.group + labels.answer_text + provenance.rationale); --only 6
        → STAGE 6 FAIL: entry qa-dev-12 contains forbidden field(s) ['labels']
          (no diagnostic for the group / rationale leak)                *** R3 ***
python3 -m unittest tests.test_public_partition   (leaky file)
        → Ran 17 tests … FAILED (failures=3)                          NOT vacuous
mv references/pins.json away;       --only 9 → STAGE 9 PASS ("no local cross-check available")  *** R10 ***
mv corpus/regime_b_paired.json away;--only 9 → STAGE 9 PASS ("absent (informational only)")
empty regime_b_excluded_articles.articles;  --only 9 → STAGE 9 FAIL (0 vs 21)  OK
private_test_manifest.counts.total = 0;     --only 10 → STAGE 10 FAIL          OK
inject answer string into staging question text; validate_qa
        → "qa-dev-11: question contains answer verbatim (tautological)", errors 1
        → restored: errors 0                                              OK

# --- Phase C: sweeps ---
python3 /tmp/opencode/sweep3.py    → S1/S2/S3/S4/S5 (full output in §C.5, §C.4)
```

---

## What I could not verify (UNVERIFIED, with reasons)

1. **Semantic quality of the 116 private test items.** Custody-forbidden. I did not
   read `questions.json`, `labels.json`, `counts.json`, `seal.sha256`, `authored/`, or
   `review/` in the private directory, and did not list any private subdirectory. All
   private-hash verification was performed by the verifier itself (stage 10, opaque
   bytes only).
2. **Whether the private manifest is the artifact the custodian intends to freeze**,
   or whether the project deliberately keeps it untracked. Nothing in the repository
   says so; the documentation says the opposite (R1). I report the measured state.
3. **Upstream endpoint failures recorded in the ledgers** (2 on this assignment, plus
   3 upstream). No in-repo artifacts to re-run; accepted as recorded.
4. **Reviewer/author independence for the private test.** Recorded identities only. The
   endpoint overlap Review 1 noted (batch-c author and the 68–100 reviewer share
   `qwen3.8-27b:free`) remains recorded and unaddressed.
5. **That `eval/scale_adjudication.py` was ever exercised on real retrieval output.**
   No consumer exists, so there is nothing to run (R9).
6. **Whether a Round 1 sanitized worktree in practice excludes `staging/`.** No script
   in the repository builds one; I could only observe that no policy or test says so (R6).
7. **Android / on-device performance.** Not claimed anywhere; substrate is desktop-only,
   consistent with AGENTS.md and STATUS.md limitation 6.

---

## Remaining repair list

| # | File | Required change | Acceptance |
|---|---|---|---|
| **R1** | `.gitignore`; `corpus/private_test_manifest.json`; `docs/STATUS.md:160`; `docs/verify-round0.md:78`; `docs/private-eval-custody.md:23,55` | Narrow `.gitignore:18` from `*private_test*.json` to the private *content* patterns only (e.g. keep `qa-private-*.json`, add an explicit negation `!corpus/private_test_manifest.json`), then `git add corpus/private_test_manifest.json` so the opaque manifest is **in version control**. Confirm its content stays content-free. | `git ls-files corpus/private_test_manifest.json` returns the path; `git log --oneline -- corpus/private_test_manifest.json` is non-empty; a fresh clone contains it; stage 10 still PASSes. Then correct the three documents that assert the artifact is in-repo — or, if untracked-by-design is the intent, say so explicitly and rewrite the custody table. |
| **R2** | `scripts/verify_round0` (stage 6) | Make stage 6 fail closed on a degenerate partition: require a non-zero id count and require the recorded split census to match the drafts (mirroring the stage-10 `if not rec_q: mark_fail()` pattern and the stage-8 drift check). | Probe: `corpus/questions.json` = `[]` → `STAGE 6 … FAIL`. Add a regression test beside `tests/test_private_eval_custody_failclosed.py`. |
| **R3** | `docs/verify-round0.md:67,77,176` | Line 77: delete `meta (source_articles, group)` — those fields are **no longer** published (that was the `d17cb31` fix); state the actual field set (`question_id, text, split, question_type, meta{original_id, exposure_note}, provenance{who/which-model/decision}`). Lines 67 & 77: replace "209 items: 60 train, 50 dev, 89 shadow_dev" with the measured **206 items: 60 train, 59 dev, 87 shadow_dev** and stop claiming stage 6 *requires* a census it does not check (see R2). Line 176: 207 → **206**. Also state that stage 6 does **not** check answer *location*; that check lives only in the stage-1 test suite. | Every number in the file matches a measured run; the field list matches `corpus/questions.json`. |
| **R4** | `docs/qa-prestated-premise-sweep.md:50`; `docs/progress-ledger.md:355` | Correct the census to the measured approved set (**206 = 17 comparison, 33 multihop, 128 factoid, 15 ambiguous, 13 unanswerable**) and either state plainly that 9 items were not manually adjudicated, or adjudicate them and record the result. Change "209 drafts" → "206 drafts". | The ledger's total and all five per-type buckets equal the measured `validate_qa` output; the word "all" is either true or explicitly qualified. |
| **R5** | `data_tools/build_public_partition.py:33`; `tests/test_public_partition.py`; `docs/STATUS.md:167` | Decide whether `question_type` may be published. If not, drop it from `ALLOWED_FIELDS` and add `unanswerable`/`ambiguous` type fields to the forbidden set. If it may (defensible only if the partition is declared dev-visible *including its labels*), document that explicitly and state that it republishes `labels.answerability`. Either way fix `docs/STATUS.md:167`, which misdescribes the file as "`question_id`, `text`, `split`, `meta` only" — it also carries `question_type` and `provenance`. | `corpus/questions.json` either carries no answerability-equivalent field, or `docs/STATUS.md` states that it does and why. Add a test pinning the decision. |
| **R6** | `docs/verify-round0.md:77`; `data_tools/build_public_partition.py:4`; `docs/STATUS.md:173` | Either add `staging/` to the excluded set in the Round 1 sanitized-worktree procedure and assert it with a test, or drop the claim that `corpus/questions.json` is "the ONLY question set workers may read" and record instead that `staging/` ships full answers for all 206 dev-visible items. | A reader can tell from the docs alone whether a worker holding the repo can see the answers. |
| **R7** | `docs/STATUS.md:193-196` | Restate limitation 4 with the measured scope: 15 ambiguous items (6 shadow_dev with a disjunction, 10 overall), including **5 `train` items with an empty `answer_text`**, and note that no `answer_text` exact-match scorer exists in the repo today. | The limitation matches `validate_qa` output for any run. |
| **R8** | `data_tools/qa_schema.py:340-348` | Note in `docs/qa-prestated-premise-sweep.md` that the string-containment tautology guard cannot detect the pre-stated-premise class, so LLM adjudication is the only line of defence — and that the only reason the class is believed eradicated is a sweep whose coverage claim is itself wrong (R4). Consider a structural check (e.g. flag comparison items whose question carries a measure for both compared sides). | The guard's stated scope matches its actual scope. |
| **R9** | `docs/STATUS.md:138-139`; `eval/metrics.py` | Either wire `eval/scale_adjudication.needs_adjudication()` into the retrieval-metric path before any scale-tier number is reported, or reword the bullet from the present indicative to "specified in `docs/scale-evaluation-rule.md`, implemented in `eval/scale_adjudication.py`, unit-tested, and **not yet consumed by any measurement code**". | A grep for a consumer returns non-empty, or the doc says plainly that there is none. |
| **R10** | `scripts/verify_round0` (stage 9) | Treat an absent `references/pins.json` as a gap rather than a PASS (or state in `docs/verify-round0.md:70` that the cross-check is best-effort and degrades silently). | `mv references/pins.json away` → stage 9 SKIP/FAIL, matching the doc. |

**Minimum set to convert this verdict to PASS: R1, R2, R3, R4.** R5–R10 should be
fixed or explicitly reworded before Round 1 begins, because each is a place where a
Round 1 worker or reviewer would be told something the repository does not do.

---

## Custody statement

I read only the repository at `/home/davidhatley/Projects/testing/local_mobile_research`,
including the opaque `corpus/private_test_manifest.json`. I did **not** read
`questions.json`, `labels.json`, `counts.json`, `seal.sha256`, `authored/`, or
`review/` in the private eval directory, and I did not list any private subdirectory.
All destructive probes ran against a throwaway copy at `/tmp/opencode/v3copy`. The
only file I wrote in the repository is this review. No git write commands were run; no
branch, tag, stash, or commit was created or modified.

## Reviewer identity

- Worker: fresh independent Round 0 freeze reviewer. **Implemented none of the work.**
- Endpoint: `opencode/space-bunny-free` (verified zero-cost).
- Recorded substitution: this is the **second** recorded substitution on this
  assignment. `qwen3.8-27b:free` returned a provider error; `nemotron-3.5-lightning-free`
  produced garbled output and wrote nothing. **No paid fallback was attempted.**
- **Nested spawning: disabled and not used.** No subagents were spawned.