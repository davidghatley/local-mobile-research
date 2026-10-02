# Round 0 Independent Freeze Review — v5

**Verdict: REPAIR REQUIRED** — see PHASE D. The `IN PROGRESS` placeholder is retired.

| Field | Value |
|---|---|
| Reviewer role | Fresh independent freeze reviewer (implemented none of the work) |
| Reviewer endpoint | `opencode/space-bunny-free` (verified zero-cost) |
| Nested spawning | DISABLED — no subagents spawned |
| Repo | `/home/davidhatley/Projects/testing/local_mobile_research` |
| HEAD under review | `1853fbd3b50cac12295a70f0556b29849f9b9887` (`1853fbd`) |
| Working tree | clean (`git status --porcelain` empty at review start) |
| Review date | 2026-10-02 |
| Custody | I am NOT the private custodian reviewer. I did **not** open `questions.json`, `labels.json`, `counts.json`, `seal.sha256`, `authored/`, or `review/` under `LMR_PRIVATE_EVAL_DIR`. |
| Files written by me | this file only. No git write commands issued. |

## Scope

Decide whether the Round 0 freeze gate is genuinely met at `1853fbd`, after four
prior reviewers each returned REPAIR REQUIRED with a distinct class of finding.

Prior reviewer methods (per the task brief), so that this review uses a different one:

1. v1 — sampling the data.
2. v2 — a 4-digit-year heuristic.
3. v3 — a global-blob answer search.
4. v4 — per-stage vacuity-hunting on the DATA.

This review (v5) attacks three further surfaces: **vacuity on the pins themselves**,
**vacuity on the code**, and **vacuity on the scientific claims**.

---

## PHASE A — Reading the record

Read in full at `1853fbd`: `docs/STATUS.md` (251), review v1 (217), v2 (173),
v3 (437), v4 (237), `docs/progress-ledger.md` §8.1–§8.10 (lines 330–579),
`docs/qa-prestated-premise-sweep.md` (90), `staging/rejected/README.md` (18),
`docs/verify-round0.md` (238), `docs/private-eval-custody.md` (88),
`docs/regime-pairing.md` (71), `docs/scale-evaluation-rule.md` (69), plus
`corpus/partition_census.json`, `eval/scale_adjudication.py`,
`data_tools/build_public_partition.py`, and the census-enforcement code paths.

No custody-forbidden file was opened. I did not list or read `questions.json`,
`labels.json`, `counts.json`, `seal.sha256`, `authored/`, or `review/` under
`LMR_PRIVATE_EVAL_DIR`, and did not list any private subdirectory.

### A.1 The four prior findings, in one line each

| round | the hole only that round found | repair commit(s) |
|---|---|---|
| v1 | 84/86 pre-stated their own comparison; `derive.py` rejected every `shadow_dev` group; stage 10 printed MATCHES on an absent digest; `eval/scale_adjudication.py` documented but absent; stale docs; ledgers ended at `814dcc1`; `STATUS.md` uncommitted | `069a9fb`, `d17cb31` |
| v2 | a third pre-stated item — `qa-dev-24`, in **dev**, found by sweeping the whole set rather than sampling | `d17cb31` |
| v3 | the opaque private manifest was **git-ignored and never committed**; stage 6 passed on an **empty** partition; stage 9 passed while cross-checking **zero** pins | `58049dc` |
| v4 | a **consistent truncation** — staging drafts and partition entries deleted *together* — passed stages 5, 6 **and** 8 | `0ab498a`, `1853fbd` |

### A.2 First observation from the record (to be confirmed in Phase B)

`docs/progress-ledger.md:570-572` (§8.10, "Other v4 findings") states the
sweep-ledger census error was **"Corrected."** Reading
`docs/qa-prestated-premise-sweep.md` at HEAD, lines 66–67 still read
**"Factoid items (121)"** and **"Ambiguous/Unanswerable (26)"**, directly
underneath a CORRECTION block (lines 54–62) that itself says the correct
figures are 128 factoid and 15 ambiguous + 13 unanswerable = 28. The file's own
`git log` shows it was last touched at `58049dc`, i.e. **before** the v4 review
existed. Carried into Phase B for measurement.

---

## PHASE B — Did the prior repairs land? (measured, nothing trusted)

### B.0 Baseline measurements at `1853fbd`

| Command | Result |
|---|---|
| `LMR_PRIVATE_EVAL_DIR=…-private-eval ./scripts/verify_round0` | **10/10 PASS, exit 0** |
| `./scripts/verify_round0 --code-only` | exit 0, prints `NOT A FREEZE PASS` |
| `python3 -m unittest discover -s tests` | **Ran 411 tests, OK** |
| `… -s data_tools/tests` | 77 OK |
| `… -s corpus/tests` | 17 OK |
| `… -s corpus/scale/tests` | 38 OK |
| `python3 -m data_tools.validate_qa --staging staging …` | 206 drafts / 206 approved / **0 errors**; splits train 60 / dev 59 / shadow_dev 87; types factoid **128** / multihop 33 / comparison 17 / ambiguous **15** / unanswerable **13** |
| `git ls-files corpus/partition_census.json` | tracked; `git check-ignore` exit 1 (not ignored); introduced at `0ab498a` |
| `git ls-files corpus/private_test_manifest.json` | tracked; `git tag -l` / `git stash list` empty; only `master` + `origin/master` |
| `git clone . /tmp/opencode/v5clone` | clone contains **both** `corpus/private_test_manifest.json` (3807 B) and `corpus/partition_census.json` (1377 B) |
| `corpus/questions.json` | 206 entries, Counter `{shadow_dev: 87, train: 60, dev: 59}`; top-level keys exactly `meta, provenance, question_id, question_type, split, text` |

### B.1 Closure table — all four rounds

| # | Prior finding | Closed? | Command / file:line I used |
|---|---|---|---|
| **R1-v1** | `qa-shadow-dev-84` / `-86` pre-stated the years they compared | **YES** | `ls staging/qa-shadow-dev-84.json staging/qa-shadow-dev-86.json` → both "No such file"; `ls staging/rejected/` → both present + `README.md`; 206 drafts at top level (not 209) |
| **R2-v1** | `data_tools/derive.py:72` rejected every `shadow_dev` group | **YES** | `data_tools/derive.py:79` → `if split not in ("train", "dev", "shadow_dev", "heldout"):`; `tests/test_group_split_vocabulary.py` in the 77-test suite, OK |
| **R3-v1** | stage 10 printed `MATCHES` on an **absent** recorded digest | **YES** | `scripts/verify_round0:1521-1544` — `if not rec_q: … mark_fail()` / `if not rec_l: … mark_fail()`; `tests/test_private_eval_custody_failclosed.py` (8) pass |
| **R4-v1** | `eval/scale_adjudication.py` documented but absent | **YES (file) / NO (wired)** | file exists (220 L); but `grep -rn "scale_adjudication\|needs_adjudication\|adjudicate("` excluding the module and `tests/` → **zero non-test consumers**. Honestly declared as an HONEST GAP at `docs/STATUS.md:159-163`. |
| **R5-v1** | verifier header/`--help`/`docs/verify-round0.md` stale | **YES** | `CODE_ONLY_IDS="1 2 3 4 5 7 9 10"`; `docs/verify-round0.md:67` now states 60/59/87 + location/prose checks; §7 stage-5 row says "206 approved" |
| **R6-v1** | ledgers ended at `814dcc1` | **YES** | `docs/progress-ledger.md` §8.1–§8.10 covers `937b3c5`…`1853fbd`; `docs/orchestration-log.md` appended |
| **R7-v1** | `docs/STATUS.md` uncommitted while HEAD said NOT FROZEN | **YES** | `git status --porcelain` empty at review start (only my review file is new) |
| **R1-v2** | `qa-dev-24` pre-stated both compared magnitudes | **YES** | `ls staging/qa-dev-24.json` → absent; `staging/rejected/qa-dev-24.json` present; `validate_qa` dev = 59 |
| **R2-v2** | counts must read 206, not 207 | **YES** | measured 206/206/0; `questions.json` 206; `docs/STATUS.md:47,105`, `verify-round0.md:77,199` all say 206 |
| **R3-v2** | `questions.json` must stop publishing `meta.group` / `evidence_groups` / `source_articles` / `rationale` | **YES — proven live** | built a leaky file in a throwaway copy injecting `meta.group`, `meta.source_articles`, `provenance.rationale` → `STAGE 6 … FAIL` with three named diagnostics: `entry qa-dev-21 publishes meta.group`, `entry qa-dev-22 publishes provenance.rationale`, `entry qa-dev-23 publishes meta.source_articles`. Also `ALLOWED_FIELDS` at `build_public_partition.py:33` omits all four. |
| **R1-v3** | private manifest git-ignored **and** never committed | **YES** | `git ls-files` → tracked; `git check-ignore` exit 1; `.gitignore:29` `!corpus/private_test_manifest.json`; fresh clone contains the 3807 B file |
| **R2-v3** | stage 6 passed on an **empty** partition | **YES — proven live** | `echo '[]' > corpus/questions.json` → `STAGE 6 … FAIL`, `partition is EMPTY: 0 ids cannot pass a freeze check` |
| **R3-v3** | `docs/verify-round0.md` documented the removed leak as present | **YES** | `verify-round0.md:67,77` now enumerate the leak checks and the real field set; no `209` / `60-50-89` remains |
| **R4-v3** | sweep-ledger census 197 / 121 / 14 / 12 was wrong | **PARTIAL — see §C.5 NEW-1** | headline corrected at `qa-prestated-premise-sweep.md:54-62` (206 = 128/33/17/15/13), but **lines 66–67 still read "(121)" and "(26)"** |
| **R10-v3** | stage 9 passed while cross-checking **zero** pins | **YES** | `scripts/verify_round0:1306-1338` — `if cross == 0: … mark_fail()` and an absent `references/pins.json` → `mark_fail()`; measured: `2 pin(s) cross-checked byte-for-byte` |
| **V4-R1** | a **consistent truncation** passed stages 5, 6 and 8 | **YES — reproduced and confirmed closed** | see §B.2 |
| **V4-R2** | sweep-ledger breakdown still `(121)` / `(26)` | **NO** | see §C.5 NEW-1 |
| **V4-R3** | stale `389` test counts; one commit unnamed in the ledger | **YES** | measured **411**; `docs/STATUS.md:43` says `(411)`; `progress-ledger.md:352-354` ends `**411 OK** after the census pin` |
| **V4-R4/R5** | gutted-suite and forged-corpus probes (recommended hardening) | **not repaired (recommended, non-blocking)** | v4 C.1 recorded both as `VACUOUS`; I did not re-probe the gutted-suite case because the census pin is now the load-bearing integrity check and V4-R4/R5 were explicitly "recommended", not blocking. Noted in §C.6. |
| **V4-R6** | `build_public_partition.py:4` docstring sync | **not repaired (cosmetic)** | docstring at line 4 still says "This file is the ONLY question set Round 1 architecture workers may read", while `verify-round0.md:98-100` carries the honest "not an enforced one; `staging/` still carries answers" note |
| **carried R5** | partition publishes `question_type` ≡ gold `answerability` | **still open, non-blocking** | `data_tools/qa_schema.py:233-236` keeps the equivalence; `ALLOWED_FIELDS` still carries `question_type`. Bounded: all 206 published items are dev-visible and `staging/` already ships `answer_text` + `answerability` for every one. |
| **carried gate-gap** | `check_training_overlap` can never return PASS | **still open, honestly disclosed** | `substrate/private_eval.py:209-228`: seal-absent → REJECT; seal-present → REJECT ("hash-only comparison not yet bound to a seal"). Disclosed at `docs/STATUS.md:213-215`. Pre-Round-1 blocker, not a freeze blocker. |

### B.2 Reproducing v4's C.2 truncation myself — stages 5, 6, 8 now FAIL

Throwaway copy at `/tmp/opencode/v5work/repo2` (no `.git`). Deleted exactly 106
staging drafts **and** the matching `corpus/questions.json` entries:

```
removed 106 drafts; partition 206 -> 100
      drafts: 100, approved: 100, errors: 0
      approved-draft census mismatch: 100 approved, census pins 206. A consistent truncation must not pass.
      approved-draft census mismatch: split dev has 0, census pins 59
      approved-draft census mismatch: split shadow_dev has 40, census pins 87
STAGE 5 qa-validation: FAIL
      questions: partition has 100 id(s), pinned census says 206. A consistent truncation must not pass.
STAGE 6 question-label-partition: FAIL
      gap: partition census mismatch: 100 published id(s), census pins 206. A consistent truncation must not pass.
      gap: approved-draft census mismatch: 100 approved draft(s), census pins 206
STAGE 8 freeze-manifest: FAIL
 RESULT: FAIL (3 load-bearing stage(s) failed or unverified).
```

Also measured a second truncation shape (49 dev drafts removed): stages 5, 6
and 8 FAIL with the same census diagnostics. **V4-R1 is genuinely closed**, and
`tests/test_partition_census.py` additionally covers the missing pin, the
inflated pin (9999), and a quarantined id reappearing.

### B.3 Phase B verdict

**31 of 33 closure items are genuinely closed in code and in behaviour.** Two are
open: V4-R2 (a documentation arithmetic false claim that the ledger asserts was
fixed) and the two explicitly-recommended/cosmetic v4 items. Both open items are
documentation, not behaviour. The behavioural repair record is clean.

That is not the same as saying the gate is met. Phase C attacks the surfaces no
prior reviewer attacked.

---

## PHASE C — Fresh attacks

Prior methods, for contrast: sampling the data; a 4-digit-year heuristic; a
global-blob answer search; per-stage vacuity-hunting **on the data**. All four
probe the *contents* of the freeze. This review probes three things none of them
touched: **the pins themselves**, **the code (by mutation, not by reading)**, and
**the scientific claims**.

### C.1 VACUITY ON THE PINS — can the census be defeated?

`corpus/partition_census.json` is now the single artifact that carries the
freeze-integrity burden for the whole QA side. Its own `purpose` field says:

> "This file exists so a CONSISTENT truncation cannot pass … so only an external
> pin can detect it."

**Probe.** Truncate exactly as v4 did (106 drafts + matching partition entries),
then **edit the census to match the truncation** and re-run:

```python
cen["expected"]        = {"total": 100, "by_split": {"shadow_dev": 40, "train": 60}}
cen["approved_drafts"] = {"total": 100, "by_split": {"shadow_dev": 40, "train": 60}}
cen["authored_total"]  = 103
```

```
truncated to 100; census edited to match
      drafts: 100, approved: 100, errors: 0
      approved-draft census matches pin (100)
STAGE 5 qa-validation: PASS
      questions: partition census matches pin (100 ids)
STAGE 6 question-label-partition: PASS
STAGE 8 freeze-manifest: PASS
 RESULT: code-level checks completed (NOT a freeze pass).
```

**All three stages PASS on a freeze missing 106 of 206 questions, with the pin
edited to agree.** Stages 1, 2, 3, 4, 7, 9 and 10 are QA-count-independent, so a
full run prints 10/10 on this tree. This is v4's C.2 defect class re-created one
level up — and it is a defect class no prior review can be blamed for, because
the pin is the product of v4's own finding.

#### What the trust root actually is

| Question | Measured answer |
|---|---|
| Is the census inside the system it checks? | **Yes.** It is a file in the same repository, committed at `0ab498a` in the same series of commits as the data it pins. |
| Is it external to the *artifacts* it checks? | **Yes, and that is a real and sufficient property for what it does catch** — `staging/*.json` and `corpus/questions.json` are different files, so a change to one is not automatically a change to the other. |
| Is anything hashed or recorded **outside** the repo? | **No.** `grep -rn "partition_census"` finds 12 references, all in-repo code and prose. No `census_sha256` field exists anywhere. `git tag -l` is **empty**. No freeze tag, no signed tag, no out-of-repo ledger of any hash. |
| Is there a persisted freeze manifest? | **No.** `RunManifest.write()` exists at `substrate/manifest.py:194` but nothing in the verification path calls it. Stage 8 builds and validates the manifest **in memory** and prints the verdict; nothing durable is produced. The only durable freeze record is the census itself — i.e. the one file that is editable. |
| Would CI catch a co-edited census? | **No.** The workflow runs `--code-only`, whose stages all read the census from the same checkout as the data. A commit that changes both passes CI. |
| Does the test suite cover the co-edit? | **No.** `tests/test_partition_census.py` has `test_inflated_census_fails_closed` (pin = 9999 against data = 206 — a pin that *disagrees*), and four truncation tests that leave the pin alone. **There is no test for a pin edited down to match.** |

#### Is it honest about being a trust root?

**Partly, and it is the specific part that matters.** The word doing the work is
**"external"**, and it is used six times to describe a file that is inside the
repository:

- `corpus/partition_census.json` → `"purpose": "…so only an external pin can detect it."`
- `docs/STATUS.md:64` → "the truncation hole is **closed** by `corpus/partition_census.json`, **a pin held outside the artifacts it checks**"
- `docs/verify-round0.md:102` → "the **external pin** on partition size"
- `docs/verify-round0.md:67` → "the partition matches the **external census pin**"
- `tests/test_partition_census.py:6-7` → "a pin held **OUTSIDE** the artifacts it checks"
- `tests/test_partition_census.py:112` → "the only **external** pin against a consistent truncation"

"Outside the artifacts it checks" is true and is the accurate phrase. "External
pin" reads as a trust root and is not one. The sharpest instance is the ledger's
own reasoning, `docs/progress-ledger.md:546-548`:

> "**a set of internal consistency checks cannot detect a consistent corruption.**
> … The gap was that no check compared the system to anything *outside* it."

and then §8.10's own fix is a file **inside** the system. The principle stated at
`progress-ledger.md:546` is not met by the fix shipped at `progress-ledger.md:550`.
That is not a pedantic objection — it is the same reasoning failure in a new place,
and this project's entire record shows it is the failure mode that keeps recurring.

#### Does anything prevent a future commit from silently changing the census and the data together?

**No.** Version control is the only defence, and it is a *reviewer-visible* defence
rather than a *mechanical* one: the diff shows two files changed in one commit, and
the census change is exactly the kind of change a reviewer looking at a census file
is least likely to scrutinise, because the census is a counts file — it "obviously"
has to track the data.

#### Should the census be committed at a freeze TAG with a hash recorded outside the repo?

**Yes, and that is missing and material.** Not because the project needs a security
boundary — it correctly disclaims one, and under a single OS user any actor who can
edit the census can also delete the verifier, so no in-repo mechanism can defend
against a determined editor. The reason is narrower and it is about what "frozen"
*means*:

The freeze gate's output is a verdict printed in a terminal. For the word "frozen"
to carry any meaning, some artifact outside the mutable tree must commit to the
tree's contents. The project already knows how to do this — it did it for the
private test (out-of-repo directory, opaque seal digest, in-repo manifest binding
the two) — and it is the discipline the ledger itself names at
`progress-ledger.md:546`. Today the QA side has no equivalent. So:

- **Severity: real, but bounded.** Not a vulnerability (no adversary is in the
  threat model). It is a **missing commitment step** in the procedure the gate is
  supposed to certify, and it is the exact step whose absence would make "Round 0
  is frozen" an unverifiable sentence.
- **Materiality: yes, because it is cheap and the project holds itself to this
  standard elsewhere.** One tag, one recorded hash, one corrected sentence in four
  documents.
- **What would make it right:** tag the freeze; record
  `sha256(corpus/partition_census.json)` (and the corpus hash, already
  reproducible) in the tag message **and** in a file outside the repository, or in
  the ledger with the tag's tree hash; and add the co-edit regression test
  (edit census *and* data together → the gate must still object, because the
  recorded external hash no longer matches).

### C.2 VACUITY ON THE CODES — mutation testing, not reading

Method: inject a **deliberate wrong-result bug** into a load-bearing module, then
run all three suites and ask whether *any* test detects it. A surviving mutation
means "the behaviour is load-bearing but nothing catches a wrong result". A test
that only catches a crash does not count. 26 real mutations, all in throwaway
copies, repo never modified.

| # | Mutation (wrong RESULT, not a crash) | Module | Verdict |
|---|---|---|---|
| M1 | `survival_curve`: break the lineage latch so a re-discovered passage resurrects a pruned lineage | `eval/metrics.py` | **KILLED** |
| M2 | `recall_at_k`: `retrieved[:k]` → `retrieved[:k+1]` | `eval/metrics.py` | **KILLED** |
| M3 | `sufficient_set_completion`: `c == 1.0` → `c >= 0.5` (partial credit as completion) | `eval/metrics.py` | **KILLED** |
| M7 | `brier_score`: divide by `len(probs)` → no division | `eval/metrics.py` | **KILLED** |
| M12 | `conditional_retention`: `None` rate on a zero denominator → `0.0` (undefined becomes false) | `eval/metrics.py` | **KILLED** |
| M13 | `wilson_ci`: halve the confidence interval | `eval/metrics.py` | **KILLED** |
| M4 | `covers`: disable the ancestry/`leaf_set` check entirely | `eval/support.py` | **KILLED** |
| M5b | `context_precision_report`: `leaf_precision` = exact_hits/n → **misses**/n | `eval/support.py` | **KILLED** |
| M23 | `context_precision_report`: `overshoot_tokens` → constant `0` | `eval/support.py` | **KILLED** |
| M6 | telemetry: read `VmRSS` where `VmHWM` is documented (peak vs point sample conflated) | `substrate/telemetry.py` | **KILLED** |
| M8 | `splits`: disable the cross-split source-chain rejection | `substrate/splits.py` | **KILLED** |
| M9 | `decide_default`: over-budget-empty reason → `zero-spans` (a packing failure misread as a retrieval decision) | `substrate/evidence.py` | **KILLED** |
| M10 | `decide_default`: zero-spans reason → `over-budget-empty` (the converse) | `substrate/evidence.py` | **KILLED** |
| M11 | `run_leakage_check`: `status = "REJECT" if flagged_ids else "PASS"` → `status = "PASS"` | `data_tools/leakage_check.py` | **KILLED** |
| M14 | `pair_conditions`: accept mismatched A/B populations (the masquerade the design doc calls "masquerade-proof") | `substrate/regime_metadata.py` | **KILLED** |
| M15 | `build_public_partition`: drop `evidence`/`sufficient_sets`/`hard_negatives`/`answer_text` from `FORBIDDEN_KEYS` | `data_tools/build_public_partition.py` | **KILLED** |
| M16 | `build_public_partition`: add `labels` to `ALLOWED_FIELDS` | `data_tools/build_public_partition.py` | **KILLED** |
| M17 | `needs_adjudication`: `return cls in ADJUDICATED_CLASSES` → `return False` | `eval/scale_adjudication.py` | **KILLED** |
| M18 | `validate_freeze`: drop the `sealed_labels_sha256 unrecorded` gap | `substrate/manifest.py` | **KILLED** |
| M19 | `validate_freeze`: make `require_partition_census` a no-op | `substrate/manifest.py` | **KILLED** |
| M20 | `validate_freeze`: drop the "generator is an infrastructure stub" gap | `substrate/manifest.py` | **KILLED** |
| M21 | `validate_freeze`: drop the `questions_sha256 mismatch` gap | `substrate/manifest.py` | **KILLED** |
| M22 | `validate_freeze`: drop the `prompt_hash` gap | `substrate/manifest.py` | **KILLED** |
| M25 | `assert_private_dir_outside_repo`: disable the inside-the-repo rejection | `substrate/private_eval.py` | **KILLED** |
| M26 | `SupportIndex.leaf_set`: cache `{node_id}` instead of transitive leaves | `substrate/support_index.py` | **KILLED** |
| M27 | `validate_score_value`: disable the `[0, 1]` bound on probabilities | `substrate/types.py` | **KILLED** |
| M28 | `migrate_legacy_trace`: short-circuit to `dict(legacy_trace)` | `eval/run_format.py` | **KILLED** |

**26/26 killed. There is no load-bearing behaviour I could find that has only a
"does it run" check.** This is the strongest part of the substrate and it is
genuinely strong — the four prior reviews each assumed the code was merely
"structurally sound", and that assumption is now measured rather than believed.

Two honest caveats on this result:

1. **Mutation coverage is not proof of correctness.** It shows the tests are
   *sensitive* — they bite on a wrong answer, not only on a crash. It does not
   show the tests encode the *right* answer. A test suite and an implementation
   that share a mistaken premise survive together.
2. **Two modules are near-certainly under-probed and I did not prove it either
   way**, because I found no anchor that produced a surviving mutation:
   `substrate/corpus.py` (96 L, corpus hash + hierarchy) and
   `data_tools/hard_negatives.py` (162 L). Recorded as UNVERIFIED, not as findings.

### C.3 VACUITY ON THE SCIENTIFIC CLAIMS — implemented, or plausible stubs?

The project asserts it can measure required-evidence survival, context precision,
calibration and compound recall. I read the implementations rather than the docs.

| Claimed measurement | Where | What it actually computes | Stub? | Wrong-result caught? |
|---|---|---|---|---|
| required-evidence survival | `eval/metrics.py::survival_curve` | latched per-lineage 1/0 survival; a pruned lineage stays dead even if a later hop re-discovers the passage | **no** | M1 KILLED |
| — direct per-stage coverage | `::stage_coverage` | `\|E ∩ C_s\| / \|E\|` | no | via M8 family |
| — conditional retention | `::conditional_retention` | numerator/denominator, `None` when the denominator is 0 | no | M12 KILLED |
| — loss/recovery | `::lost_and_recovered` | sorted lost vs reintroduced evidence spans | no | — |
| context precision | `eval/support.py::context_precision_report` | per-retrieved `exact`/`imprecise`/`miss` **without** ancestry expansion, `leaf_precision`, `minimal_tokens`, `overshoot_tokens` | no | M5b, M23 KILLED |
| support satisfaction | `::covers`, `::atom_satisfaction`, `::sufficient_set_completion_support` | upward-closed leaf containment; subspan atoms additionally require exact text containment | no | M4 KILLED |
| calibration | `eval/metrics.py::brier_score`, `::expected_calibration_error` | real ECE/Brier; logits rejected; non-finite rejected; non-binary labels rejected | no | M7 KILLED |
| **compound recall** | — | **Deliberately not implemented.** `docs/experimental-contract.md:150,196,213`: `compound_survival` was **REMOVED** because a product of unconditional marginal recalls has wrong denominators; the contract says compound claims must use direct cumulative coverage | n/a | n/a |

These are **real implementations with real semantics, not interface stubs with
plausible names.** I went looking specifically for the shape "a function that
returns a plausible float" and did not find it in the metric layer.

Three corrections to the brief's framing, stated because they change the
conclusion:

1. **The brief's "compound recall" claim is not a claim the project makes.** It
   refuses that metric on stated statistical grounds and documents the removal in
   three places. Scoring it as an omission would be wrong.
2. **There is no answer-correctness scorer anywhere in `eval/`** — no exact match,
   no token F1, no judge wrapper. `docs/experimental-contract.md:216` says so:
   "No LLM judge in substrate; judge model + prompt pinned separately at
   benchmark time." That is consistent with the project being a **retrieval**
   tournament (System-1 retrieval, evidence survival, abstention) and with the
   abstention/confidence metrics being the answer-adjacent surface it actually
   owns. **But** it means every metric in the substrate scores the *retrieval and
   abstention* side, and **none scores whether the generated answer was right**.
   A reader of `docs/STATUS.md` could easily come away believing answer accuracy
   is measurable today. It is not. See §C.6-N4.
3. **The metric layer does not consume the scale-adjudication rule.** `grep` for a
   non-test consumer of `scale_adjudication` returns nothing. This is the R9 gap
   from v3 and it remains open — but `docs/STATUS.md:159-163` now labels it
   "**HONEST GAP**" and says "no evaluation currently applies it", which is the
   opposite of v3's complaint (v3 objected to a *present-indicative* claim in the
   doc). **The disclosure is now honest; the gap is still real.**

### C.4 What I attacked and found CLEAN (recorded so it is not re-litigated)

- The census pin closes v4's C.2 **exactly** as claimed, with three independent
  stages and a dedicated regression test file.
- Stage 6 is non-vacuous (`[]` → FAIL), census-aware (absent pin → FAIL,
  wrong pin → FAIL, quarantined id → FAIL), and **leak-detecting with named
  diagnostics** for location *and* prose leaks — the v3 R2/R3 pair is genuinely
  fixed in the verifier, not only in the builder and the unit tests.
- Stage 10 is fail-closed on an absent recorded digest.
- Stage 9 is fail-closed on zero cross-checks and on an absent `pins.json`.
- `corpus/private_test_manifest.json` is tracked, un-ignored, in a fresh clone,
  content-free, and bound to the out-of-repo artifacts by opaque byte hash.
- 26/26 wrong-result mutations killed. No test-only-that-it-runs behaviour found.
- The four metric families are implemented and mutation-verified.
- Custody: I opened no private file and listed no private subdirectory. Every
  destructive probe ran in `/tmp/opencode/v5work/`.
- Documentation counts: `STATUS.md:43` "(411)" matches my 411; the ledger
  chronology ends at 411; no `209`/`207`/`197` approved-count claim survives
  outside the two correctly-labelled historical quotes.

### C.5 NEW findings from this review

**NEW-1 — BLOCKING (documentation): V4-R2 was not repaired, and the ledger says
it was.**
`docs/qa-prestated-premise-sweep.md:66-67` still reads:

```
- **Factoid items (121)**: No answer text appears in the question.
- **Ambiguous/Unanswerable (26)**: By design; not this defect class.
```

Measured `validate_qa` output: factoid **128**, ambiguous **15**, unanswerable
**13** (15 + 13 = **28**). So both figures are wrong, and both sit four lines
below a CORRECTION block that itself states the correct ones. Meanwhile
`docs/progress-ledger.md:570-572` (§8.10) states: *"The sweep-ledger census
correction was incomplete: the headline count was fixed but the per-type
breakdown still read 121 factoid / 26 comparison against a measured 128 / 28.
**Corrected.**"* — **it was not corrected.** `git log -- docs/qa-prestated-premise-sweep.md`
shows the file's last commit is `58049dc`, which predates the v4 review.
This is the *identical* defect v3's R4 and v4's V4-R2 each caught, and the
project has now produced a ledger entry asserting the fix landed when it did not.
That is the third occurrence of "a repair ledger claims a repair that was never
made", and it is the reason I do not pass on the strength of the closure table.

**NEW-2 — BLOCKING (freeze integrity): the census pin is the load-bearing pin
and has no trust root; the hole it was built to close is re-openable by editing
it.** Full analysis in §C.1. Demonstrated by execution, not by reading. The
specific defects: the pin is committed in-repo with no tag, no out-of-repo hash,
no persisted freeze manifest; CI cannot catch a co-edit; no test covers a co-edit;
and six documents plus the pin's own `purpose` field describe an in-repo file as
an "external pin" that closes the hole.

**NEW-3 — REQUIRED (documentation): `docs/STATUS.md:64` says the truncation hole
is "closed".** Per §C.1 it is narrowed to *unintentional* truncation and remains
open against a co-edit. A freeze-gate status document must not overstate the
integrity property that the gate's own new pin provides. Pair this with the
"external pin" wording at `STATUS.md:64`, `verify-round0.md:67`, `verify-round0.md:102`,
`progress-ledger.md:550`, `test_partition_census.py:6-7`, `:112`, and the census
file's own `purpose`.

**NEW-4 — REQUIRED (documentation): `docs/STATUS.md:216-220` (limitation 4)
mis-attributes a property to 15 items that only 10 have.** Measured over the 15
`answerability == "ambiguous"` staging drafts: **10** carry the prose
`"Ambiguous between X and Y readings - see labels.readings"` in `answer_text`;
**5** (`qa-train-02/08/20/26/38`) have a completely **empty** `answer_text`. The
sentence reads "15 ambiguous items put a prose disjunction in `answer_text`, and
5 of them have an EMPTY `answer_text`" — which literally claims 15 disjunction-bearing
items, 5 of which are empty, i.e. an impossible set. v3's R7 was *half* fixed: the
count moved 6 → 15 and the empty-`answer_text` fact was added, but the disjunction
attribute was carried across all 15. Small, but it is the third repair in a row
whose ledger entry overstates what landed.

**NEW-5 — NON-BLOCKING, pre-Round-1 (carried, honestly disclosed):**
`substrate/private_eval.py:209-228` — `check_training_overlap` returns `REJECT` on
both branches (seal-absent and seal-present). Round 1 training clearance is
unimplemented. `docs/STATUS.md:213-215` says so. Correctly disclosed; must land
before Round 1 teams generate synthetic training data.

**NEW-6 — NON-BLOCKING (carried, honestly disclosed):** `eval/scale_adjudication.py`
has zero non-test consumers. No scale-tier number can yet be reported under the
documented rule. `docs/STATUS.md:159-163` says so.

**NEW-7 — NON-BLOCKING: no answer-correctness scorer exists.** See §C.3 note 2.
Not a Round 0 gate failure (the substrate is explicitly retrieval-side and says so
at `experimental-contract.md:216`), but a Round 1 *entry condition* that is not
currently on any checklist: someone must decide, before the tournament, how a
generated answer is scored at all, given 5 ambiguous items have no `answer_text`
and 10 carry a non-answer string in that field.

**NEW-8 — NON-BLOCKING, `UNVERIFIED` for me:** `substrate/corpus.py` (96 L) and
`data_tools/hard_negatives.py` (162 L) — I could not construct a surviving
mutation, which means "no mutant found", **not** "well tested". I did not
read both modules line-by-line. Recorded as UNVERIFIED rather than as a finding.

### C.6 What remains unproven (UNVERIFIED, with reasons)

1. Semantic quality of the 116 private items — **custody-forbidden.** Never opened
   `questions.json`, `labels.json`, `counts.json`, `seal.sha256`, `authored/`,
   `review/`; never listed a private subdirectory. All private-hash verification
   was done by the verifier itself (stage 10, opaque bytes).
2. The in-repo manifest's counts (116, type mix) against the actual private files
   — counting requires parsing, forbidden to me. Seal binding checked by the verifier.
3. Whether the private manifest is the artifact the custodian intends to freeze.
4. Reviewer/author independence for the private test beyond recorded identities
   (v1 recorded the batch-c author / reviewer-68–100 endpoint overlap; still recorded,
   still unaddressed, still not a freeze blocker).
5. `check_training_overlap` on real training data — no reachable PASS path.
6. Scale adjudication on real retrieval output — zero consumers, nothing to run.
7. Whether a Round 1 sanitized worktree in practice excludes `staging/` and
   `corpus/`. No script builds one; `build_public_partition.py:4` still claims
   the partition is the *only* question set, and `verify-round0.md:98-100` correctly
   says it is not enforced. The two documents disagree (v4's V4-R6, unrepaired).
8. Android / on-device performance — claimed nowhere. Desktop-only throughout,
   consistent with `AGENTS.md` and `docs/STATUS.md` limitation 6.
9. V4's V4-R4/V4-R5 hardening probes (gutted suite; self-consistent corpus forgery)
   — recommended, non-blocking, not re-probed by me.
10. Mutation coverage of `substrate/corpus.py` and `data_tools/hard_negatives.py`
    (NEW-8).
11. Whether the repair loop's *process* generalises — four rounds, each finding real,
    each repair real, each new round finding a class the others missed. Whether a
    fifth class exists is exactly the question a PASS asserts is closed.

### C.7 THE DECISIVE QUESTION — argue both ways

The gate requires an independent reviewer to say the substrate is ready. This is
not purely code review; it is a judgement about whether Round 1 can begin.

#### The case FOR passing, stated at its strongest

- **The behavioural repair record is clean and I measured it, not trusted it.**
  31 of 33 closure items closed in code and behaviour. The four prior rounds'
  blocking findings — the pre-stated premises, the uncommitted manifest, the
  empty-partition pass, the zero-cross-check pass, the consistent truncation — are
  all demonstrably fixed at HEAD. Every one of them was re-run by me, not read.
- **The code is not vacuous, and this is the first review to establish that.**
  26 of 26 wrong-result mutations killed. Four prior reviews all wrote that the
  verifier "is sound" or "is not vacuous" as an *inference* from stage behaviour;
  none tested sensitivity to a wrong answer. I did, and the answer is that this
  test suite bites. That is a materially different and stronger claim.
- **The scientific layer is real.** Survival, precision, support, calibration and
  abstention are implemented with careful, correct semantics (latched lineage,
  `None`-not-`0.0` undefined rates, no ancestry leakage into precision, logits
  rejected from ECE/Brier) and are mutation-verified. No stubs with plausible
  names. The one metric the brief expected to find stubbed — compound recall — was
  removed on correct statistical grounds and is documented in three places.
- **Custody is sound and consistently re-verified.** The manifest is tracked,
  un-ignored, in a fresh clone, content-free, and bound by opaque byte hash. I
  found no path by which private content enters the repo, and I did not need to
  read private content to establish that.
- **The project's honesty is genuinely above average for this stage.** Two real
  gaps (`check_training_overlap` unreachable PASS; scale rule unwired) are
  declared as gaps with reasons rather than presented as working. The verifier
  prints a disclaimer on every run and refuses to be read as a semantic verdict.
- **The remaining blockers are small and mechanical.** NEW-1 is a two-number edit.
  NEW-3/NEW-4 are wording. NEW-2 is a tag, a recorded hash, one regression test,
  and four sentences. None of them is a research-judgement question; none requires
  re-authoring, re-auditing, or re-splitting anything.

#### The case AGAINST passing, stated at its strongest

- **NEW-2 is not a wording problem. It is the gate's own load-bearing pin with no
  trust root, and I demonstrated the re-open by execution.** Every other check in
  the project is an internal consistency check. The census was introduced
  specifically to be the one check that is not — and it is inside the system. Six
  documents and the pin's own `purpose` field call it "external". The ledger at
  `progress-ledger.md:546` states the correct principle and then ships a fix that
  does not satisfy it. The project has just demonstrated, four times, that its
  instinct for where holes are is unreliable. I found this one. What guarantees
  there is not a fifth?
- **NEW-1 is the most alarming finding in this review, and it is not about
  arithmetic.** The ledger states a repair landed that did not land. That is the
  third time a repair ledger has asserted a correction (v3 R4 → corrected only in
  the headline; v4 V4-R2 → not corrected at all; now claimed corrected in §8.10 and
  still not). If I accept a closure table whose entries include at least one
  demonstrably false "repaired", then **the closure table itself is not a reliable
  instrument**, and the 31 "YES" entries inherit that uncertainty. I verified the
  behaviour directly, so I have independent grounds for those 31 — but the
  instrument that produced the claim is shown to be unsound, and the project has
  no mechanism that would have caught the false entry.
- **There is no freeze tag, no persisted freeze manifest, and no out-of-repo
  commitment of any kind.** "Round 0 is frozen" is currently a sentence with no
  referent. `RunManifest.write()` is never called. This is not the same defect as
  v3's R1 (the binding artifact was untracked) — R1 was fixed — but it is the same
  *family*: the thing that makes the freeze verifiable is not in the freeze.
- **Five consecutive reviewers have now each found a real hole, and each found a
  different class.** Sampling → year heuristic → blob search → data vacuity →
  pin vacuity. The methods were escalating in scope, not in luck. The reason each
  round found something is that the previous round's method was bounded. There is
  no reason to think a sixth bounded method finds nothing; the honest expectation
  is that it finds something.
- **The aggregate risk of passing now is asymmetric.** If I pass and NEW-2 turns
  out to matter, the failure mode is a frozen substrate whose QA-side census can be
  and has been silently halved with a green verifier — precisely the hole that has
  now recurred in three consecutive forms. If I hold for a tag, a hash, one
  regression test and two sentence edits, the cost is hours and the project loses
  nothing it has not already lost four times.

#### My decision

**The repair loop is converging, and it is not converged.**

The *code* has converged — 26/26 mutations killed, every prior behavioural hole
closed and independently re-verified, custody sound. That part I would sign today.

The *integrity procedure* has not, and it is the part the freeze gate actually
certifies. NEW-2 is the specific instance: the last repair added a pin, called it
external, documented it in six places, and shipped it without a trust root — and
the one sentence in the ledger that states the correct principle
(`progress-ledger.md:546`) is contradicted by the fix two sections below it. NEW-1
is the corroborating evidence about the project's own instrumentation: a repair
ledger asserted a repair that does not exist in the tree.

I want to be precise about what I am *not* saying. I am not saying the project is
in disarray, that the corpus or the QA set is unsound, that any semantic work
needs redoing, or that the reviewers before me were wrong. I am saying that the
freeze gate's last act was to introduce a new load-bearing artifact without
anchoring it, and to describe that act in language stronger than the artifact
warrants, and that the documentation record of that act contains at least one
provably false statement about a repair.

That combination — a new unanchored trust anchor, plus a demonstrably false repair
claim — is what I am unwilling to sign, and it is a small enough set of fixes that
holding is cheap.

**What would convince me.** Concretely, and in this order:

1. A freeze **tag**, and `sha256(corpus/partition_census.json)` plus the tag's
   commit recorded in a file **outside** this repository (the project already has
   the pattern: out-of-repo private dir + in-repo manifest + seal).
2. `tests/test_partition_census.py` gains the co-edit regression test: edit the
   census *and* the data together, and assert the gate still objects against the
   recorded external hash. This is the test whose absence let my probe through.
3. `corpus/partition_census.json.purpose`, `docs/STATUS.md:64`,
   `docs/verify-round0.md:67`, `docs/verify-round0.md:102`,
   `docs/progress-ledger.md:550`, and `tests/test_partition_census.py:6-7`/`:112`
   all say **"in-repo pin, external to the artifacts it checks"** instead of
   "external pin", and `STATUS.md:64` says the hole is *narrowed* rather than
   "closed". A pin that does not know what it is will be over-trusted again.
4. `docs/qa-prestated-premise-sweep.md:66-67` corrected to `128` and `28`
   (15 ambiguous + 13 unanswerable), and `docs/progress-ledger.md:570-572`
   corrected from "Corrected." to what is actually true.
5. `docs/STATUS.md:216-220` limitation 4 restated to the measured scope
   (15 ambiguous; **10** with a prose disjunction; **5** with empty `answer_text`).
6. Persist the freeze manifest (`RunManifest.write()` is implemented and never
   called) so the freeze produces a durable artifact rather than a terminal
   verdict.

Items 1–3 are the gate. Items 4–6 are cheap and should land with them. With 1–6
in place I expect to be able to PASS on the next review, and I would want to see
the co-edit probe fail rather than be told it does.
---

## PHASE D — Final verdict

# REPAIR REQUIRED

Two blocking findings, one of them demonstrated by execution rather than by
reading. Round 1 must not begin.

I want the shape of this verdict stated plainly, because it is not the shape of the
previous four. **The behavioural repair record is clean: 31 of 33 closure items are
genuinely closed and I re-ran every one.** The code is not vacuous — 26 of 26
wrong-result mutations were killed, which is a stronger claim than any prior review
made. The custody boundary is sound. The metric layer is real code, not stubs.
None of the semantic work needs redoing.

What I am refusing to sign is narrower and I want to be exact about it: the freeze
gate's **last act** was to introduce a new load-bearing pin, describe it in six
places as an "external pin", and ship it inside the repository with no tag, no
out-of-repo hash, and no persisted freeze manifest — and the ledger entry claiming
the most recent documentation repair landed contains a **provably false statement
about that repair**. I demonstrated by execution that editing the census to match a
truncation returns stages 5, 6 and 8 to PASS. A verifier that certifies half a
freeze with a green result is the same hole that has now appeared in three
consecutive forms, and the freeze gate exists precisely to prevent it.

**The repair loop is converging, and it is not converged.** The code has converged.
The integrity procedure has not.

### Blocking repair list

| # | Severity | File | Change | Acceptance |
|---|---|---|---|---|
| **V5-R1** | **BLOCKING** | freeze procedure + `docs/` + `tests/` | **Anchor the census pin outside the repository.** Tag the freeze; record `sha256(corpus/partition_census.json)` and the tagged commit **in a file outside this repo**. The project already owns the pattern (out-of-repo private dir + in-repo manifest + seal) and `substrate/private_eval.py` is the template. Add the **co-edit regression test** to `tests/test_partition_census.py`: edit `corpus/partition_census.json` *and* the data together, assert the gate still objects against the recorded external hash. Then correct the wording in `corpus/partition_census.json` (`purpose`), `docs/STATUS.md:64`, `docs/verify-round0.md:67`, `docs/verify-round0.md:102`, `docs/progress-ledger.md:550`, `tests/test_partition_census.py:6-7` and `:112` — say **"in-repo pin, external to the artifacts it checks"**, not "external pin" — and change `STATUS.md:64` "the truncation hole is closed" to "narrowed to unintentional truncation". | My §C.1 co-edit probe now FAILs. `git tag -l` non-empty. The six quoted locations read "in-repo pin, external to the artifacts it checks". `tests/test_partition_census.py` contains a co-edit test that fails on a co-edited tree. |
| **V5-R2** | **BLOCKING** | `docs/qa-prestated-premise-sweep.md:66-67`; `docs/progress-ledger.md:570-572` | `"(121)"` → **128**; `"(26)"` → **28** (15 ambiguous + 13 unanswerable). Then change `progress-ledger.md:572` from "**Corrected.**" to what is actually true. | Measured `validate_qa` output equals every bucket in the ledger. The §8.10 sentence matches `git log -- docs/qa-prestated-premise-sweep.md`. |

### Required, non-blocking (must land before Round 1 entry, not before freeze)

| # | File | Change | Acceptance |
|---|---|---|---|
| **V5-R3** | `docs/STATUS.md:216-220` (limitation 4) | Measured: 15 ambiguous; **10** carry the prose disjunction; **5** (`qa-train-02/08/20/26/38`) have **empty** `answer_text`. The current sentence attributes the disjunction to all 15 and is literally unsatisfiable. | The sentence matches a measured run. |
| **V5-R4** | `substrate/private_eval.py:209-228` (carried) | Implement the sealed comparison so `check_training_overlap` can ever return PASS. Currently REJECT on both branches. Disclosed at `STATUS.md:213-215` — keep the disclosure until it is true. | A clearance path exists before Round 1 training. |
| **V5-R5** | `eval/` scale wiring (carried) | `eval/scale_adjudication.py` has zero non-test consumers; no scale-tier number can yet be reported under `docs/scale-evaluation-rule.md`. Honest disclosure at `STATUS.md:159-163` — keep it, or wire `needs_adjudication()` into the retrieval-metric path. | `grep` for a non-test consumer returns non-empty, **or** the disclosure stays. |
| **V5-R6** | `data_tools/build_public_partition.py:4`; `docs/verify-round0.md:98-100` (v4's V4-R6, unrepaired) | Sync the two. The docstring claims the partition is the ONLY question set workers may read; `verify-round0.md` correctly says `staging/` also ships answers for all 206 and that the control is procedural. | A reader can tell from the docs alone whether a worker holding the repo can see the answers. |
| **V5-R7** | partition `question_type` (carried v3 R5, v4 "carried R5") | `data_tools/qa_schema.py:233-236` keeps `question_type` ≡ gold `answerability`; the field is published. Decide and pin: drop it, or document that it republishes `labels.answerability` for 28 items. Bounded (all 206 are dev-visible; `staging/` ships `answer_text` for every one) — not a held-out leak. | A test pins the decision. |
| **V5-R8** | `substrate/manifest.py:194` | `RunManifest.write()` is implemented and **never called**. Persist the freeze manifest so the freeze produces a durable artifact rather than a terminal verdict. | A freeze run writes a manifest; the tag references it. |
| **V5-R9** | answer scoring | No answer-correctness scorer exists anywhere in `eval/` (no exact match, no token F1, no judge wrapper — `experimental-contract.md:216`). Consistent with a retrieval-side substrate, but it is on no Round 1 checklist. Someone must decide how a generated answer is scored, given 5 ambiguous items have **no** `answer_text` at all. | Decision recorded before the tournament. |

### Recorded, not a finding (UNVERIFIED)

- **NEW-8:** `substrate/corpus.py` (96 L) and `data_tools/hard_negatives.py` (162 L) — no surviving mutant found, which is **not** the same as "well tested". I did not read both line-by-line.
- **V4-R4/R5** (recommended hardening: gutted-suite floor, self-consistent corpus-forgery anchor) — not repaired, explicitly non-blocking; not re-probed by me.

---

## Closure table — all four prior rounds, consolidated

| Round | Finding | Closed at `1853fbd`? | Evidence I used |
|---|---|---|---|
| v1 | `qa-shadow-dev-84`/`-86` pre-stated their own comparison | **YES** | both absent from `staging/`, both in `staging/rejected/`; 206 drafts at top level |
| v1 | `derive.py` rejected every `shadow_dev` group | **YES** | `data_tools/derive.py:79`; `test_group_split_vocabulary.py` in the 77 OK |
| v1 | stage 10 printed `MATCHES` on an **absent** digest | **YES** | `scripts/verify_round0:1521-1544`; 8 fail-closed tests pass |
| v1 | `eval/scale_adjudication.py` documented but absent | **file YES / wiring NO** | exists (220 L); zero non-test consumers — disclosed as HONEST GAP |
| v1 | stale verifier docs / header | **YES** | `CODE_ONLY_IDS`; `verify-round0.md:67,77,199` all say 206 / 60-59-87 |
| v1 | ledgers ended at `814dcc1`; `STATUS.md` uncommitted | **YES** | ledger §8.1–§8.10 covers `937b3c5`…`1853fbd`; `git status` clean |
| v2 | `qa-dev-24` pre-stated both magnitudes (in **dev**) | **YES** | absent from `staging/`; in `staging/rejected/`; measured dev = 59 |
| v2 | counts must read 206 | **YES** | measured 206/206/0; `questions.json` 206; `STATUS.md:47,105` say 206 |
| v2 | `questions.json` published answer **location** + **prose** | **YES — proven live** | injected `meta.group` + `meta.source_articles` + `provenance.rationale` → `STAGE 6 FAIL` with all three named |
| v3 | private manifest git-ignored **and** untracked | **YES** | tracked; `check-ignore` exit 1; fresh clone has the 3807 B file |
| v3 | stage 6 passed on an **empty** partition | **YES — proven live** | `[]` → FAIL, "partition is EMPTY" |
| v3 | `verify-round0.md` documented the removed leak as present | **YES** | `:67`/`:77` now enumerate the real checks and field set |
| v3 | sweep-ledger census 197/121/14/12 wrong | **PARTIAL** | headline corrected to 206/128/33/17/15/13; **`:66-67` still `(121)` / `(26)`** → **V5-R2** |
| v3 | stage 9 passed cross-checking **zero** pins | **YES** | `:1306-1338` `if cross == 0: mark_fail()`; measured 2 cross-checked |
| **v4** | a **consistent truncation** passed stages 5/6/8 | **YES** | reproduced exactly (106 drafts + matching entries) → stages 5, 6, 8 **all FAIL** with census diagnostics |
| v4 | sweep-ledger breakdown `(121)` / `(26)` | **NO** | `git log` shows the file last touched at `58049dc`, before v4 existed → **V5-R2** |
| v4 | stale `389` test counts; unnamed commit | **YES** | measured **411**; `STATUS.md:43` and ledger both say 411 |
| v4 | gutted-suite / forged-corpus hardening | not repaired (recommended) | recorded, UNVERIFIED |
| v4 | docstring "ONLY question set" sync | not repaired (cosmetic) | → V5-R6 |
| carried | `check_training_overlap` unreachable PASS | **open, disclosed** | `private_eval.py:209-228` → V5-R4 |
| carried | partition publishes `question_type` ≡ answerability | **open, bounded** | `qa_schema.py:233-236` → V5-R7 |

---

## Commands run, with outputs (measured)

```bash
# ---- orientation ----
git rev-parse HEAD                      → 1853fbd3b50cac12295a70f0556b29849f9b9887
git status --porcelain                  → empty (clean) at review start
git tag -l                              → EMPTY. No freeze tag exists.
git branch -a                           → master, remotes/origin/master
git stash list                          → empty

# ---- baseline ----
LMR_PRIVATE_EVAL_DIR=…-private-eval ./scripts/verify_round0
    → stages 1-10 PASS, "RESULT: all load-bearing stages PASS.", exit 0
      stage 1 reports "372 tests" in-verifier (39 entrypoint tests skipped);
      direct `unittest discover -s tests` reports 411
./scripts/verify_round0 --code-only       → exit 0, "NOT A FREEZE PASS" banner present
python3 -m unittest discover -s tests                    → Ran 411 tests OK
python3 -m unittest discover -s data_tools/tests         → 77 OK
python3 -m unittest discover -s corpus/tests             → 17 OK
python3 -m unittest discover -s corpus/scale/tests       → 38 OK
python3 -m data_tools.validate_qa --staging staging --corpus corpus/corpus.jsonl \
    --split-map corpus/split_map.json
    → splits {dev:59, heldout:0, private_test:0, shadow_dev:87, train:60}
      types  {ambiguous:15, comparison:17, factoid:128, multihop:33, unanswerable:13}
      206 drafts / 206 approved / 0 errors

# ---- custody / tracking ----
git ls-files corpus/partition_census.json          → corpus/partition_census.json (tracked)
git check-ignore -v corpus/partition_census.json   → exit 1 (NOT ignored)
git log --oneline -- corpus/partition_census.json  → 0ab498a Pin the partition census…
git ls-files corpus/private_test_manifest.json     → tracked
git check-ignore -v corpus/private_test_manifest.json → exit 1
git clone -q . /tmp/opencode/v5clone
    → corpus/private_test_manifest.json  3807 B
      corpus/partition_census.json        1377 B
grep -rn "partition_census" .   → 12 hits, all in-repo code + prose. No out-of-repo hash.
grep -rn "census_sha256|partition_census_sha256" substrate/ scripts/  → no hits
git ls-files | grep -i "manifest|freeze" → build_manifest, input_manifest,
    private_test_manifest, scale_build_manifest, scale_input_manifest (+ review docs).
    NO persisted freeze-manifest artifact.
grep -n "def write" substrate/manifest.py:194 → RunManifest.write exists;
    grep the verification path → NEVER CALLED.

# ---- the decisive probe: co-edit the pin (throwaway /tmp/opencode/v5work/trustroot) ----
# delete 106 staging drafts + matching questions.json entries, THEN edit
# partition_census.json so expected/approved_drafts/authored_total match the truncation
./scripts/verify_round0 --only 5,6,8
    → truncated to 100; census edited to match: {'total': 100,
      'by_split': {'shadow_dev': 40, 'train': 60}}
      drafts: 100, approved: 100, errors: 0
      approved-draft census matches pin (100)
      STAGE 5 qa-validation: PASS
      questions: partition census matches pin (100 ids)
      STAGE 6 question-label-partition: PASS
      STAGE 8 freeze-manifest: PASS
    *** THE PIN IS DEFEATED BY EDITING IT. ***

# ---- v4's C.2 reproduced WITHOUT touching the pin (throwaway repo2) ----
# delete exactly 106 drafts + matching partition entries
./scripts/verify_round0 --only 5,6,8
    → removed 106 drafts; partition 206 -> 100
      approved-draft census mismatch: 100 approved, census pins 206.
        A consistent truncation must not pass.
      STAGE 5 qa-validation: FAIL
      questions: partition has 100 id(s), pinned census says 206.
        A consistent truncation must not pass.
      STAGE 6 question-label-partition: FAIL
      gap: partition census mismatch: 100 published id(s), census pins 206.
      gap: approved-draft census mismatch: 100 approved draft(s), census pins 206
      STAGE 8 freeze-manifest: FAIL
      RESULT: FAIL (3 load-bearing stage(s) failed or unverified).
    *** v4's C.2 IS GENUINELY CLOSED. ***

# ---- stage 6 non-vacuity and leak detection (throwaway s6) ----
echo '[]' > corpus/questions.json        → STAGE 6 FAIL "partition is EMPTY: 0 ids
                                         cannot pass a freeze check"
inject meta.group / meta.source_articles / provenance.rationale
    → STAGE 6 FAIL with three named diagnostics:
        entry qa-dev-21 publishes meta.group (answer location; …)
        entry qa-dev-22 publishes provenance.rationale (answer text in prose)
        entry qa-dev-23 publishes meta.source_articles (answer location; …)
rm corpus/partition_census.json         → STAGE 6 FAIL "absent: … it is required"
append a quarantined id to the partition→ STAGE 6 FAIL "rejected id(s) present"
# stage 10, stage 9 read directly; fail-closed patterns confirmed in code
#   verify_round0:1521-1544 (absent digest → mark_fail)
#   verify_round0:1306-1338 (cross == 0 → mark_fail; absent pins.json → mark_fail)

# ---- mutation sweep: 26 wrong-result bugs, all three suites each time ----
# harness: rsync to /tmp/opencode/v5work/mut-<name>, patch one anchor, run
#   `unittest discover -s tests`, `-s data_tools/tests`, `-s corpus/tests`
# KILLED: M1 survival_curve lineage latch        eval/metrics.py
# KILLED: M2 recall_at_k k+1                    eval/metrics.py
# KILLED: M3 completion >= 0.5 (partial credit)  eval/metrics.py
# KILLED: M4 covers ancestry disabled            eval/support.py
# KILLED: M5b leaf_precision = misses/n          eval/support.py
# KILLED: M6 VmHWM→VmRSS conflation              substrate/telemetry.py
# KILLED: M7 brier sum vs mean                  eval/metrics.py
# KILLED: M8 cross-split chain rejection off     substrate/splits.py
# KILLED: M9/M10 zero-spans ↔ over-budget-empty substrate/evidence.py
# KILLED: M11 leakage status forced to PASS      data_tools/leakage_check.py
# KILLED: M12 conditional_retention None→0.0     eval/metrics.py
# KILLED: M13 wilson interval halved             eval/metrics.py
# KILLED: M14 pair_conditions accepts mismatched substrate/regime_metadata.py
# KILLED: M15/M16 FORBIDDEN_KEYS trimmed /
#         labels added to ALLOWED_FIELDS         data_tools/build_public_partition.py
# KILLED: M17 needs_adjudication → False         eval/scale_adjudication.py
# KILLED: M18 seal-unrecorded gap dropped        substrate/manifest.py
# KILLED: M19 require_partition_census no-op      substrate/manifest.py
# KILLED: M20 stub-generator gap dropped         substrate/manifest.py
# KILLED: M21 questions_sha256 gap dropped       substrate/manifest.py
# KILLED: M22 prompt_hash gap dropped            substrate/manifest.py
# KILLED: M23 overshoot_tokens → 0               eval/support.py
# KILLED: M25 private-dir-inside-repo allowed    substrate/private_eval.py
# KILLED: M26 leaf_set cache = {node_id}          substrate/support_index.py
# KILLED: M27 score [0,1] bound disabled          substrate/types.py
# KILLED: M28 migrate_legacy_trace short-circuit eval/run_format.py
# (M24 was a no-op mutation — x→x — and is discarded; 26 real mutants, 26 killed)

# ---- scientific claims: read, not grepped ----
# eval/metrics.py  285 L, 16 defs — real implementations, not stubs
# eval/support.py  209 L,  5 defs — real implementations, not stubs
# grep "exact_match|def score_answer|answer_accuracy|token_f1|f1_score" --include=*.py
#   → NO answer-correctness scorer anywhere (matches experimental-contract.md:216)
# grep "compound" --include=*.py --include=*.md
#   → compound_survival was REMOVED by design (experimental-contract.md:150,196,213)
# grep -rn "scale_adjudication|needs_adjudication|adjudicate(" excluding the module
#   and tests/ → ZERO non-test consumers

# ---- ambiguity claim check ----
# measured over the 15 answerability=="ambiguous" staging drafts:
#   10 carry "Ambiguous between X and Y readings - see labels.readings"
#   5  have a COMPLETELY EMPTY answer_text:
#      qa-train-02, qa-train-08, qa-train-20, qa-train-26, qa-train-38
# STATUS.md:216-220 attributes the disjunction to all 15 → unsatisfiable as written

# ---- stale-claim sweep ----
sed -n '60,70p' docs/qa-prestated-premise-sweep.md
    → "- **Factoid items (121)**"  /  "- **Ambiguous/Unanswerable (26)**"
      directly under a CORRECTION block stating 128 and 28.
git log --oneline -- docs/qa-prestated-premise-sweep.md
    → 58049dc, d17cb31   (last touched BEFORE the v4 review existed)
grep -rn "209 approved|207 approved|197 approved|9/10" docs/ scripts/
    → only correctly-labelled historical quotes and the CORRECTION block itself
grep -rn "389|401 OK|411 OK" docs/
    → STATUS.md:43 "(411)" ✓ measured 411; ledger chronology ends "**411 OK**"
```

---

## What I could not verify (UNVERIFIED, with reasons)

1. **Semantic quality of the 116 private test items** — custody-forbidden. Never
   opened `questions.json`, `labels.json`, `counts.json`, `seal.sha256`,
   `authored/`, or `review/` in the private directory; never listed a private
   subdirectory. All private-hash verification was performed by the verifier
   itself (stage 10, opaque bytes only).
2. **The in-repo manifest's counts (116, type mix) against the actual private
   files** — counting requires parsing, forbidden to me. Seal binding was checked
   by the verifier, not by me.
3. **Whether the private manifest is the artifact the custodian intends to freeze**,
   or whether untracked-by-design was ever intended. Nothing in the repo says so;
   the docs said the opposite and were corrected.
4. **Private-test reviewer/author independence beyond recorded identities.** v1
   recorded the batch-c author / reviewer-68–100 endpoint overlap
   (`qwen3.8-27b:free`); still recorded, still unaddressed, not a freeze blocker.
5. **`check_training_overlap` on real training data** — no reachable PASS path.
6. **Scale adjudication on real retrieval output** — zero consumers, nothing to run.
7. **Whether a Round 1 sanitized worktree in practice excludes `staging/` and
   `corpus/`.** No script builds one; `build_public_partition.py:4` and
   `verify-round0.md:98-100` disagree (V5-R6).
8. **Android / on-device performance** — claimed nowhere in the repo. Desktop-only
   throughout, consistent with `AGENTS.md` and `docs/STATUS.md` limitation 6.
   Recorded so a future reader does not infer device validity from any of this.
9. **V4-R4 / V4-R5 hardening probes** (gutted suite → PASS; self-consistent
   1-article corpus forgery → PASS) — recommended and non-blocking; not re-probed.
10. **Mutation coverage of `substrate/corpus.py` and `data_tools/hard_negatives.py`** —
    no surviving mutant found, which is not the same as "well tested" (NEW-8).
11. **Whether a fifth class of hole exists.** Five consecutive reviewers have each
    found a real hole by using a method the previous four had not, and each round's
    method was bounded rather than lucky. My own method was bounded too: I attacked
    the pins, the codes and the claims, and I did not read
    `data_tools/hard_negatives.py` line by line. A PASS asserts that this sequence
    has converged; I do not think a single round can establish that, which is part
    of why I am holding for a concrete, mechanically checkable commitment (V5-R1)
    rather than for more review rounds.

---

## Custody statement

I read only the repository at `/home/davidhatley/Projects/testing/local_mobile_research`,
including the opaque `corpus/private_test_manifest.json` and
`corpus/partition_census.json`. I did **not** read `questions.json`, `labels.json`,
`counts.json`, `seal.sha256`, `authored/`, or `review/` in the private eval
directory, and I did not list any private subdirectory. Private-hash and seal
verification were performed by the verifier itself (stage 10, opaque bytes only,
never parsed or printed by me).

Every destructive probe ran against a throwaway copy under
`/tmp/opencode/v5work/` (`repo`, `repo2`, `s6`, `trustroot`, `mut-*`). The
repository was never modified except for this review file. I ran no git write
commands; no branch, tag, stash, or commit was created or modified.

## Reviewer identity

- **Worker:** fresh independent Round 0 freeze reviewer. **Implemented none of the
  work.**
- **Endpoint:** `opencode/space-bunny-free` (verified zero-cost).
- **Nested spawning: DISABLED and not used.** No subagents were spawned.
- **Paid fallback: PROHIBITED and not attempted.**
- **Write discipline:** incremental, phase by phase (Phase A header → §A → §B → §C →
  §D). Nothing was composed at the end.
- **Only file written:** `docs/round0-independent-freeze-review-v5.md`.
