# Round 0 Status

**Status captured at commit `49047f9`.** This file describes the state at that
commit. It is not a live view; re-run `scripts/verify_round0` for the current
answer.

Supersedes the pre-repair status claims. See `docs/progress-ledger.md` and
`docs/orchestration-log.md` for the full history including the mistakes that
produced the previous `NOT FROZEN` verdict.

## Verdict: code-level verification PASSES (10/10); freeze gate NOT yet satisfied

The four load-bearing issues from the external review of `f819d9b` are
repaired, and the private test boundary exists outside git and is sealed.

**The independent freeze review returned `REPAIR REQUIRED`, not `PASS`.** Its
seven findings have been addressed (two shadow-dev items rejected, a functional
regression in `data_tools/derive.py` fixed, a vacuous pass in stage 10 closed,
`eval/scale_adjudication.py` written, verifier docs corrected, ledger updated).
Round 0 must not be tagged frozen until a fresh reviewer confirms the repairs
landed. See `docs/round0-independent-freeze-review.md` and
`docs/progress-ledger.md` §8.

```
LMR_PRIVATE_EVAL_DIR=/home/davidhatley/Projects/testing/local_mobile_research-private-eval \
  ./scripts/verify_round0             → 10/10 stages PASS, exit 0
./scripts/verify_round0 --code-only   → 8/8 stages PASS, exit 0
```

| Stage | What it proves | Result |
|---|---|---|
| 1 | shared substrate tests (372) | PASS |
| 2 | data-tools tests (77) | PASS |
| 3 | corpus converter tests (17) | PASS |
| 4 | corpus structure + hash | PASS |
| 5 | QA validation (`validate_qa`: 0 errors, 207 approved) | PASS |
| 6 | question/label partition: public-only file + out-of-repo opaque seal | PASS |
| 7 | generator pin | PASS |
| 8 | freeze manifest incl. paired regime fields | PASS |
| 9 | leakage-control artifacts (paired Regime A/B, exclusions) | PASS |
| 10 | private test exists outside repo, seal matches, labels stay outside | PASS |

A PASS here proves **structure, hashes, splits, provenance, custody and pins**.
It does not prove semantic QA correctness, and the verifier says so on every run.

## Issue 1 — exposed held-out reclassified to SHADOW-DEV

The 89 items committed as `qa-heldout-*` through `f819d9b` can never be a
sealed benchmark: git history retains their text, answers, sufficient evidence,
hard negatives and sources. They were **not** scrubbed and history was **not**
rewritten.

- 89 items renamed `qa-heldout-NN` → `qa-shadow-dev-NN` (`git mv`, history preserved)
  — of which **87 remain usable**; 2 were later rejected (see below)
- `SPLITS = ("train", "dev", "shadow_dev", "private_test")`; `heldout` is retired
  legacy, still accepted by validators for backward compatibility only
- each item carries `meta.original_id`, `meta.exposure_note`, and a
  `provenance.reclassification` record
- `qa-shadow-dev-60` is genuinely **absent** (an author deleted it and a
  garbled re-author produced nothing). The count is honestly 89, not 90.

They are dev-visible forever. **Never call them held-out, sealed, secret, or
proof of generalization.**

### Honest count: 87 usable, 89 reclassified, 2 rejected

The independent freeze review found `qa-shadow-dev-84` and `qa-shadow-dev-86`
unsound: both questions pre-stated the years they were comparing (1991/2012 and
1790/1889), so the recorded evidence was not required. Both were **rejected**,
moved to `staging/rejected/`, and kept rather than deleted
(`docs/qa-shadow-dev-84-86-repair-ledger.md`). The usable shadow-dev set is
therefore **87**, and no count anywhere claims 89 usable.

## Issue 2 — sufficient-set semantics audited and repaired

The error pattern was real: conjunctive hops encoded as alternative singleton
sets (`[[A],[B]]` for a question needing both). Full audit of all 89, in three
independent batches plus a fresh re-approval pass.

| Outcome | Count |
|---|---|
| unchanged / approved as-is | 88 |
| hard negative that contained the answer, replaced (`qa-shadow-dev-36`) | 1 |
| sufficient sets merged (conjunctive singletons → one set) | 45, 46, 48, 61, 63, 84 and others |
| relabelled multihop → factoid (single atom determines the answer) | 24, 49, 53, 64, 67 |
| non-breaking-space atom text corruption, restored to corpus bytes | 48 |

Ledgers: `docs/qa-shadow-dev-audit-ledger-BATCH-{A,B,C}.md`,
`docs/qa-shadow-dev-reapproval-ledger.md`.

Verified after repair: every evidence atom is byte-equal to its corpus node;
**all 31 multi-atom sets across 25 items are single conjunctive sets** — no
conjunctive `[[A],[B]]` split remains anywhere; the 13 multi-singleton items
are genuinely independent routes.

## Issue 3 — Regime A / B are now PAILED conditions

`substrate/regime_metadata.py` derives Regime B as a tagged paired condition
over the same questions, not a disjoint population.

- `corpus/split_map.json` migrated `heldout` → `shadow_dev`
  (`b80a774d…` → `d0879ac4…`, 25219 → 25315 bytes)
- 56 shadow-dev questions form the paired subset across 5 groups
  (cambridge, corona, jaguar, lincoln, washington)
- `corpus/regime_b_paired.json`, `corpus/regime_b_excluded_articles.json`
  (21 articles excluded from **adaptation** only; the query-time corpus is
  unchanged — asserted against the real corpus, 0 violations)
- report A-on-paired, B-on-same-paired, and the delta. `aggregate_across_regimes`
  still refuses to pool unpaired metrics; `aggregate_paired_delta` computes the
  paired delta; a masquerade (mismatched id sets) is refused.

Design: `docs/regime-pairing.md`.

## Issue 4 — scale tier is not purely irrelevant

The 940 scale articles include deliberate confusables (Roman Empire, Nile, WWI,
WWII, Lion, Tiger, …), so "carries no evidence" was not defensible.

- `corpus/scale/scale_classification.json`: 815 background, 15
  confusable_adversarial, 110 redirect_stub, 0 unknown
- retrieved scale passages do **not** auto-count as false positives; top
  confusable retrievals are adjudicated (`docs/scale-evaluation-rule.md`)
- **provenance timeline corrected**: the 960-title candidate list was added in
  `814dcc1` (2026-10-01), *after* question work began in `4d924c5` (2026-09-29).
  Selection independence is procedural curation, **not** pre-question
  independence. Recorded in `corpus/scale/PROVENANCE-CORRECTION.md`; the pinned
  JSON was not rewritten.
- scale provenance was re-pinned by regenerating from existing snapshots after
  the split-map change rotated the core build manifest hash

## Private test boundary (new)

| Property | Value |
|---|---|
| Location | outside the repository, `LMR_PRIVATE_EVAL_DIR` |
| Items | **116** |
| Type mix | factoid 59, multihop 19, comparison 15, unanswerable 12, ambiguous 11 |
| Ambiguous + unanswerable | 19.8% (target ≥ 10%) |
| Paired Regime B items | 15 (13 excluded adaptation articles) |
| Distinct corpus groups | 62 |
| Seal | `c6e1e98d843eaf1eb962a9ec2f89026af2d532f9b963c5d0a78d45056293c54c` |
| In-repo artifact | `corpus/private_test_manifest.json` (counts + hashes + custody only) |
| Authored | 5 free-model batches, 4 replacements, 1 paired batch |
| Reviewed | 5 independent free-model reviewers, none an author |
| Repairs applied | 64 |
| Rejected | 3 (unsound premises, no conforming repair) |
| Removed | 1 (exact duplicate of public `qa-train-38`) |

`corpus/questions.json` is the **worker-visible** partition: 209 in-repo items
with `question_id`, `text`, `split`, `meta` only — no atoms, no answers, no hard
negatives, no private ids.

The boundary is **procedural and workspace-based, not a kernel security
boundary**: all processes share one OS user, so no permission or encryption
theater is implemented. Round 1 workers get a sanitized worktree that excludes
the private directory. `tests/test_private_eval_tripwire.py` (10 tests) fails if
private filenames, content, or labels appear under the repository path, and it
asserts the in-repo manifest is content-free.

The leakage gate returns **PASS or REJECT + the synthetic training ids to
remove**, never the matched private id, text, answer, or evidence. It fails
closed: with no seal it is REJECT, never PASS.

## Honest limitations

1. **The 89 shadow-dev items were seen by every worker that touched them.** They
   are dev data. Any threshold tuned on them is not a held-out claim.
2. **The private test was authored and reviewed by free LLMs**, not humans. The
   independent review caught real defects — 64 repairs, 3 rejections, 1 exact
   duplicate — which is evidence the process works, and also evidence that
   unreviewed LLM-authored data is not trustworthy.
3. **The leakage gate's hash-only comparison is not yet bound to the seal.** It
   correctly refuses to issue PASS, but a real sealed comparison must be
   implemented before Round 1 teams can receive a meaningful verdict.
4. **Six ambiguous shadow-dev items put a prose disjunction in `answer_text`.**
   Any scorer comparing `answer_text` to model output will score all six wrong.
   The orchestrator must decide how ambiguity is scored before that split is
   used for anything quantitative.
5. **Calibration thresholds are declared, not fitted.** The freeze manifest
   records the policy; Round 1 must select thresholds on dev/shadow-dev and
   freeze them before its own private run.
6. **Everything here is a desktop measurement.** No Android or on-device
   performance claim may be derived from any of it.
7. **All scale and corpus results are single-tier.** One scale point does not
   produce a scaling curve.

## Preserved process failures (recorded, not hidden)

- `nemotron-3.5-lightning-free` produced garbled output on the private-author
  batch-B assignment and wrote zero files; substituted `longcat-2.5-preview-free`
  then `fledge-alpha-free`. No paid fallback.
- `gemma-4-31b-it:free` returned a provider error on two review assignments;
  substituted `space-bunny-free`. No paid fallback.
- Batch-B's ledger claimed provenance fields were added to items 31–59 when
  none were. The repairs landed; only the record was missing. Caught by the
  re-approval pass.
- `apply_repairs.py` initially resolved backup files as live items after the
  first repair pass, so provenance was written to `_pre_repair/`. Fixed by
  excluding `_`-prefixed directories; the affected items were re-recorded.
- A hard negative in `qa-shadow-dev-36` contained the answer in a **one-letter
  spelling variant** (`urbs Gyddannyzc` vs gold `urbs Gyddanyzc`). A lexical
  answer-string check can never catch this. Only reading the paragraph did.

## Round 1 entry conditions

Not yet met. Before the tournament starts, the independent freeze review must
return PASS. Round 1 workers must receive a sanitized worktree excluding the
private directory, and must not receive private results until every frozen
system has completed the private run.
