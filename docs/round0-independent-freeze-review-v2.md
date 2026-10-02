# Round 0 Independent Freeze Review v2 (Post-Repair Verification)

**Reviewer:** fresh independent re-reviewer, free endpoint `opencode/nemotron-3-ultra-free` (verified zero-cost). No nested spawning. No paid fallback.

**Date:** 2026-10-02

**Claim under review:** "All seven findings from the prior independent freeze review have been addressed; the substrate can be frozen so Round 1 may begin" (as reflected in commit `069a9fb` and `docs/STATUS.md`).

**Method:** Every reproducible claim was re-executed on this host. Measured results are marked as such. I also performed a systematic adversarial sweep across ALL 207 approved QA items for the pre-stated-premise defect class that caused the rejection of `qa-shadow-dev-84` and `-86`.

---

## VERDICT: REPAIR REQUIRED

The seven prior findings **are closed** (see §1 table), and the code-level verification passes 10/10. However, my systematic sweep of **all 207 approved items** uncovered **one additional item (`qa-dev-24`) with the exact same pre-stated-premise defect class** that caused the rejection of `qa-shadow-dev-84` and `-86`. This item is in the `dev` split, currently approved, and was not caught by the prior review.

A freeze built on this state would institutionalize a known protocol-violating item in the dev-visible evaluation set.

---

## 1. Prior Findings — Closure Verification

| # | Prior Finding | Closed? | Evidence |
|---|---------------|---------|----------|
| 1 | `qa-shadow-dev-84` and `-86` pre-stated comparison years; approved on flawed reasoning | **YES** | Both rejected, moved to `staging/rejected/` with `provenance.decision=reject`, documented in `staging/rejected/README.md` and `docs/qa-shadow-dev-84-86-repair-ledger.md`. Usable shadow-dev = 87 (not 89). `validate_qa` scans only top-level `staging/`; rejected items excluded. |
| 2 | `data_tools/derive.py:72` rejected all `shadow_dev` groups (functional regression, untested) | **YES** | `group_articles` now accepts `shadow_dev` (line 79). 9 regression tests in `tests/test_group_split_vocabulary.py` exercise every live split-map group including all 32 `shadow_dev` groups and 5 Regime B groups. All 77 data-tools tests pass. |
| 3 | Stage 10 printed "MATCHES" when manifest recorded no hash (vacuous pass) | **YES** | Stage 10 now fails closed: `if not rec_q: mark_fail()` (lines 1378–1381). 8 tests in `tests/test_private_eval_custody_failclosed.py` verify fail-closed on missing `questions_json_sha256`, missing `labels_json_sha256`, missing `seal_sha256`, wrong hash, private content in manifest, absent manifest, and in-repo private dir. All pass. |
| 4 | `eval/scale_adjudication.py` documented but absent | **YES** | File created (220 lines) with `needs_adjudication()`, `adjudicate()`, `scale_class_for()`, `is_scale_node()`. Resolves title→slug collisions via tier manifest's authoritative node ids (fixes ABBA/Abba). 12 tests in `tests/test_scale_adjudication.py` pass. |
| 5 | Verifier header/`--help` and `docs/verify-round0.md` said "stages 1-5, 7, 9" and "exit 1" | **YES** | Header now lists 10 stages. `--help` shows `--code-only` runs stages 1-5, 7, 9, 10. `CODE_ONLY_IDS="1 2 3 4 5 7 9 10"` (line 77). `docs/verify-round0.md` §7 now states "full run now exits 0 with all 10 stages PASS" and shows 10-stage table. |
| 6 | Ledger and orchestration log ended at `814dcc1`; no entries for 6 repair commits | **YES** | `docs/progress-ledger.md` §8 added with full repair-run chronology (commits `937b3c5` through `069a9fb`). `docs/orchestration-log.md` appended with 2026-10-01→2026-10-02 benchmark-boundary repair run section. |
| 7 | `docs/STATUS.md` uncommitted; HEAD said "NOT FROZEN" | **YES** | `docs/STATUS.md` committed at `069a9fb`. Working tree clean. Verification commands match claimed results (10/10 full, 8/8 code-only). **Minor issue:** header still says "Status captured at commit `49047f9`" while describing post-repair state; should say `069a9fb` or "current". |

---

## 2. Fresh Adversarial Attack Results

### 2.1 Verification Re-runs (Measured)

| Command | Result |
|---------|--------|
| `LMR_PRIVATE_EVAL_DIR=... ./scripts/verify_round0` | **10/10 PASS**, exit 0 |
| `./scripts/verify_round0 --code-only` | **8/8 PASS**, exit 0 |
| `python3 -m unittest discover -s tests` | **372 tests OK** |
| `python3 -m unittest discover -s data_tools/tests` | **77 tests OK** |
| `python3 -m unittest discover -s corpus/tests` | **17 tests OK** |
| `python3 -m unittest discover -s corpus/scale/tests` | **38 tests OK** |
| `data_tools.validate_qa` | 207 drafts, 207 approved, 0 errors (60 train / 60 dev / 87 shadow_dev) |

No stage passes vacuously. Stage 10 fails closed on missing digests (tested). Stage 6 custodian sub-check correctly reports legacy labels absent (expected). Stage 9 `pins.json` cross-check runs (file present).

### 2.2 Test Suite Integrity

- **No tests weakened or deleted.** `git diff 49047f9..069a9fb -- tests/` shows only **additions**: 3 new test files (`test_group_split_vocabulary.py` 96 lines, `test_private_eval_custody_failclosed.py` 114 lines, `test_scale_adjudication.py` 143 lines) and updates to `test_shadow_dev.py` correcting counts (89→87 usable, 2 rejected). All 372 tests are genuine probes, not tautologies.

### 2.3 Systematic Sweep for Pre-Stated-Premise Defect (Across ALL 207 Approved Items)

The prior reviewer found the defect in two `shadow_dev` comparison items (`-84`, `-86`): **the question text contains both comparison values, making the evidence unnecessary**. I re-adjudicated every comparison and multihop item across **all 207 approved items** (train 60 + dev 60 + shadow_dev 87).

**Results:**

| Item | Split | Type | Defect? | Reason |
|------|-------|------|---------|--------|
| `qa-shadow-dev-84` | shadow_dev | comparison | **YES** (rejected) | Both years (1991, 2012) in question; ordering resolvable without evidence |
| `qa-shadow-dev-86` | shadow_dev | comparison | **YES** (rejected) | Both years (1790, 1889) in question; answer text is question's own side-A descriptor |
| **`qa-dev-24`** | **dev** | **comparison** | **YES (NEW — currently APPROVED)** | **Both quantities (300M ha, 800M ha) in question; "which is larger?" → 800M > 300M directly answerable. Evidence only names the second forest (Amazon).** |
| `qa-pilot-dev-05` | dev | comparison | NO | Two quantities (56%, 159.2M) are different metrics (share vs absolute); target population requires evidence to match descriptor |
| `qa-shadow-dev-85` | shadow_dev | comparison | NO | Only one year (1636) given as Harvard identifier; comparison is campus land area, not founding date |
| All other 15 comparison items | various | comparison | NO | At most one comparison value in question text |
| All 33 multihop items | various | multihop | NO (for this defect class) | Bridge entities described but not named; evidence required to link description to answer |

**The defect in `qa-dev-24` is identical in class to the rejected items:**

- Question: "The Congo Basin rainforest covers **300 million hectares** compared to **800 million hectares** in another forest; which forest is larger?"
- Both comparison values explicitly stated → "which is larger?" resolves to "the 800M hectare forest" without any evidence.
- Single sufficient set: `[t:congo_basin:00:000:04]` which confirms the second forest is Amazon.
- Leave-one-out at set level fails: removing the only set leaves the comparative answer ("the other forest") determinable from question text alone.
- This item passed `validate_qa` and was included in the 207 approved count.

### 2.4 Custody Boundary — No New Holes

- `tests/test_private_eval_tripwire.py` (10 tests) passes: no private filenames/content in repo, private dir outside repo, in-repo manifest content-free.
- Private eval directory at `/home/davidhatley/Projects/testing/local_mobile_research-private-eval` (sibling, outside git).
- Stage 10 verifies seal against out-of-repo artifacts; never parses content.
- No repair-pass changes introduced any path for private content to enter the repo.

### 2.5 Quarantine Honesty

- `staging/rejected/` contains exactly 2 items: `qa-shadow-dev-84.json`, `qa-shadow-dev-86.json`.
- `staging/rejected/README.md` documents both rejections with reasons.
- `validate_qa` scans only top-level `staging/` → rejected items excluded from all counts and partitions.
- `corpus/questions.json` (public partition) carries 209 IDs (60 train / 50 dev / 89 shadow_dev per manifest) — rejected items not included.
- Shadow-dev usable count honestly reported as **87** in `STATUS.md`, `progress-ledger.md`, and `test_shadow_dev.py`.

---

## 3. What Could Not Be Verified (Same as Prior Review)

1. **Semantic quality of 116 private test items** — custody-forbidden; only opaque seal/hash verified.
2. **Three orchestrator-reported upstream failures** — no repository artifacts to re-run.
3. **Scale classification independence** — procedural curation only; 960-title list created after question work began (recorded in `PROVENANCE-CORRECTION.md`).
4. **Android/on-device performance** — not claimed; desktop-only acknowledged.

---

## 4. Repair List (Blocking)

| # | File | Change Required |
|---|------|-----------------|
| 1 | `staging/qa-dev-24.json` | **REJECT** (move to `staging/rejected/`). Question pre-states both comparison quantities (300M / 800M hectares); "which is larger?" answerable without evidence. Same defect class as `qa-shadow-dev-84`/`-86`. Update `staging/rejected/README.md` and `docs/qa-shadow-dev-84-86-repair-ledger.md` (or new ledger) to account for 3 total rejections. Usable dev = 59 (not 60). |
| 2 | `docs/STATUS.md` | Update header from "Status captured at commit `49047f9`" to `069a9fb` (or "current HEAD"). Update dev count from 60 to 59 and shadow-dev usable from 87 to 87 (unchanged) but note total approved 206 (not 207). Re-run `validate_qa` and update stage 5 line. |

---

## 5. Non-Blocking Notes (For Orchestrator)

- **Ambiguous `answer_text` in shadow-dev:** 6 items still put prose disjunctions in `answer_text`; any exact-match scorer will mark all six wrong. Needs orchestrator decision before quantitative use.
- **Calibration thresholds declared, not fitted:** `ThresholdPolicy` in freeze manifest records policy only; Round 1 must select on dev/shadow-dev and freeze.
- **Leakage gate hash-only comparison not bound to seal:** correctly refuses PASS, but real sealed comparison needed before Round 1 verdicts.
- **Scale single-tier only:** 940 articles, no scaling curve possible.
- **No cross-group multihop in corpus:** 44.3% article-level cross-split edges but 0 genuine cross-group multihop chains in dev/shadow-dev; multi-hop difficulty under-represented.

---

## 6. Commands Run (Measured)

```bash
# Full verification
LMR_PRIVATE_EVAL_DIR=/home/davidhatley/Projects/testing/local_mobile_research-private-eval \
  ./scripts/verify_round0
# → 10/10 PASS, exit 0

# Code-only
./scripts/verify_round0 --code-only
# → 8/8 PASS, exit 0

# Test suites
python3 -m unittest discover -s tests           # 372 OK
python3 -m unittest discover -s data_tools/tests # 77 OK
python3 -m unittest discover -s corpus/tests    # 17 OK
python3 -m unittest discover -s corpus/scale/tests # 38 OK

# New regression tests
python3 -m unittest tests.test_group_split_vocabulary          # 9 OK
python3 -m unittest tests.test_private_eval_custody_failclosed # 8 OK
python3 -m unittest tests.test_scale_adjudication              # 12 OK

# QA validation
python3 -m data_tools.validate_qa --staging staging \
  --corpus corpus/corpus.jsonl --split-map corpus/split_map.json
# → 207 drafts, 207 approved, 0 errors

# Systematic defect sweep (custom script across all 207 items)
# → Found 1 new defect: qa-dev-24
```

---

## 7. Custody Statement

I read **only** the repository at `/home/davidhatley/Projects/testing/local_mobile_research`. I did **not** read `questions.json`, `labels.json`, `counts.json`, `seal.sha256`, `authored/`, or `review/` in the private eval directory. I listed the private directory top-level only to confirm existence. All private-hash verification was performed by the verifier itself (stage 10). No custody violation.

---

## 8. Reviewer Identity

- Worker: fresh independent Round 0 freeze re-reviewer (no nested spawning; top-level session only).
- Endpoint: `opencode/nemotron-3-ultra-free` (verified free; zero-cost catalog entry).

---

**Bottom line:** The seven prior repairs landed correctly and the code substrate is structurally sound. **However, the semantic QA audit is incomplete** — the same defect class that triggered two rejections in shadow-dev exists in one approved dev item (`qa-dev-24`). Until this item is rejected and the counts updated, the freeze gate is **not met**.

**Required before PASS:** Reject `qa-dev-24`, update rejected quarantine and counts, re-run verification, commit updated `STATUS.md`.