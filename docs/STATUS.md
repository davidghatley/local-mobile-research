# Round 0 Status

**Status captured at the benchmark-boundary repair run (through `069a9fb` plus the pre-stated-premise sweep that followed it).** This file describes the state at that
commit. It is not a live view; re-run `scripts/verify_round0` for the current
answer.

Supersedes the pre-repair status claims. See `docs/progress-ledger.md` and
`docs/orchestration-log.md` for the full history including the mistakes that
produced the previous `NOT FROZEN` verdict.

## ACCEPTED RISKS — recorded, not resolved

Seven independent reviews have run. A green verifier is **necessary and not
sufficient**: it proves structure, hashes, splits, provenance, custody and pins,
and it says so on every run. It cannot prove semantic QA correctness. The
following are accepted, dated risks of freezing anyway. Each was raised by an
independent reviewer and none is hidden by the PASS.

| # | Risk | Consequence | Owner |
|---|---|---|---|
| 1 | **Semantic QA rests on LLM reviewers.** 206 approved items carry reviewer-asserted labels. No unit test can establish answerability, atom minimality, multi-hop genuineness or label correctness. | Round 1 measures retrieval against a benchmark whose labels are judgments, not facts. | review ledgers |
| 2 | **Private test power is QUANTIFIED, and it is low.** 116 items, 62 groups, 15 paired Regime-B items, against a 297-article corpus and an ~83% recall target. Computed 2026-10-03 (`experiments/comparability/CONTRACT.md` §4, cross-checked by two-proportion z-test at 80% power): two architectures are separable only at gaps of **~22 pp on dev (13 items), ~12 pp on dev+shadow_dev (18 items), ~10 pp on all 206 worker-visible items (21 items), and ~14 pp on the sealed private set (16 items)**. | Round 1 can only distinguish architectures that differ by roughly 10 percentage points overall. Most architecture pairs are NOT separable on this corpus. A gap smaller than the threshold must be reported as a null result, never as a win. | Round 1 leads, before the tournament |
| 3 | **The fixed generator may floor.** Qwen2.5-1.5B-Instruct at Q4_K_M is weak enough that it might not express differences between good and poor evidence packets. | If generation floors, the retrieval tournament measures nothing above the floor. Check the floor explicitly on the first dev run. | Round 1 baseline worker |
| 4 | **The answer judge is not digest-pinned.** `google/flan-t5-large` is a floating tag. Judge metrics are ABSENT until a digest is resolved. | Secondary generated-answer metrics unavailable until pinned. Deterministic primary metrics are unaffected. | custodian, BLOCKING-FOR-ROUND-1 |
| 5 | **The leakage gate is procedural, not a security boundary.** One-shot sessions are enforced by a ledger in the private directory; all processes share one OS user. | A worker who reached the private directory could reset the ledger. The gate stops mistakes, not a determined adversary. | custody rules |
| 6 | **Scale adjudication is specified but only lightly wired.** `eval/scale_analysis.py` consumes it; the metrics layer does not yet. | Scale-tier precision figures must be read with their `unjudged_top_k` and `limitations`. | Round 1 scale worker |
| 7 | **The freeze tag and durable record are a custodian attestation, not a signature.** A custodian who controls the private directory can forge both. | The freeze proves procedural discipline, not authorship. | — |

## ROUND 0 FROZEN

```
Tag             round0-freeze-r1
Frozen commit   (git rev-parse round0-freeze-r1^{commit})

Durable record  <LMR_PRIVATE_EVAL_DIR>/freeze_manifest_<frozen-commit-sha>.json
Tag binding     <LMR_PRIVATE_EVAL_DIR>/freeze_tag_binding.json
Stable digests  census   4925d84a40c8416f4188c8ad48a4109866b263542b60db6f8af939b7691587fa
                private seal  c6e1e98d843eaf1eb962a9ec2f89026af2d532f9b963c5d0a78d45056293c54c

Verification    ./scripts/verify_round0 -> 10/10 PASS, exit 0, on a CLEAN tree
Probes          ./docs/probes_round0.sh -> 11 probes, 18/18 checks PASS
CI              GitHub Actions GREEN
```

The manifest digest is deliberately NOT quoted here. It embeds the commit SHA,
the verifier hash and the verification timestamp, so any commit that changes
this line changes the digest — a self-referential figure that can never be
correct. The authoritative digest set lives in the tag-binding record; a
consumer selects the record whose `commit_sha` matches the tag, and verifies it
against the manifest it names.

The manifest is named for the commit it binds, so there is nothing to keep in
sync here. `git rev-parse round0-freeze-r1^{commit}` gives the frozen commit, and
`<LMR_PRIVATE_EVAL_DIR>/freeze_manifest_<that-sha>.json` is its record. Every
exact SHA is in `<LMR_PRIVATE_EVAL_DIR>/freeze_tag_binding.json`.

Eight independent reviews ran. Seven returned REPAIR REQUIRED, each finding a
real defect the previous rounds missed. The eighth
(`docs/round0-independent-freeze-review-v8.md`) returned **PASS**.

**A freeze is not a claim of scientific validity.** It records that the
substrate is structurally sound, the custody boundary holds, and the accepted
risks below are owned and dated. Read those risks before trusting any Round 1
result.

## Verdict (superseded by the freeze above)

**Five independent reviews have run. All five returned `REPAIR REQUIRED`. No
reviewer has returned PASS, so no freeze tag exists and Round 1 must not begin.**
A sixth review is required to confirm the v5 repairs landed.

The four load-bearing issues from the external review of `f819d9b` are
repaired, and the private test boundary exists outside git and is sealed.

**Two independent freeze reviews returned `REPAIR REQUIRED`, not `PASS`.** The
first review's seven findings are closed (`docs/round0-independent-freeze-review.md`).
A re-review confirmed all seven and then swept the whole approved set for the
same defect class, finding `qa-dev-24` in the **dev** split: a comparison
question that stated both compared magnitudes, so its single atom was not
needed. It was rejected and quarantined (`docs/qa-prestated-premise-sweep.md`).

The sweep also exposed a defect nobody had looked for: the worker-visible
`corpus/questions.json` was publishing `meta.group`, `meta.evidence_groups`,
`meta.source_articles` and auditor `rationale`. Those name **the answer's
location** and, in prose, **the answer itself** — a retriever reading them gets
a 1–3 article candidate set inside a 297-article corpus. The partition is now
generated by `data_tools/build_public_partition.py` from a narrow allowlist, and
17 tests pin the contract including a prose-leak check.

Round 0 must not be tagged frozen until a fresh reviewer confirms these repairs
landed. See `docs/round0-independent-freeze-review-v2.md` and
`docs/progress-ledger.md` §8.

```
LMR_PRIVATE_EVAL_DIR=/home/davidhatley/Projects/testing/local_mobile_research-private-eval \
  ./scripts/verify_round0             → 10/10 stages PASS, exit 0
./scripts/verify_round0 --code-only   → 8/8 stages PASS, exit 0
```

| Stage | What it proves | Result |
|---|---|---|
| 1 | shared substrate tests (422) | PASS |
| 2 | data-tools tests (77) | PASS |
| 3 | corpus converter tests (17) | PASS |
| 4 | corpus structure + hash | PASS |
| 5 | QA validation (`validate_qa`: 0 errors, 206 approved, census-matched) | PASS |
| 6 | question/label partition: public-only file + out-of-repo opaque seal | PASS |
| 7 | generator pin | PASS |
| 8 | freeze manifest incl. paired regime fields, census digest, and a durable out-of-repo freeze record | PASS |
| 9 | leakage-control artifacts (paired Regime A/B, exclusions) | PASS |
| 10 | private test exists outside repo, seal matches, labels stay outside | PASS |

Three independent review rounds have each returned `REPAIR REQUIRED`, and each
found something the others missed:

| round | what only that round found |
|---|---|
| v1 | two items whose questions pre-stated their own comparison; a functional regression; a stage that printed MATCHES while comparing nothing |
| v2 | a **third** such item in the dev split, found only by sweeping the whole set instead of sampling |
| v3 | the opaque private manifest was **git-ignored and never committed**; stage 6 **passed on an empty partition**; stage 9 passed while cross-checking **zero** pins |
| v4 | a **consistent truncation** — deleting staging drafts and the matching partition entries *together* — passed stages 5, 6 **and** 8, because every internal cross-check stayed self-consistent |
| v5 | the fix for v4 was itself defeatable: the census lives in git, so editing the data **and** the census together passed everything again. Also found `RunManifest.write()` never called — the freeze left a verdict, not an artifact |

All are repaired. The truncation hole is closed by `corpus/partition_census.json`
— a pin held outside the artifacts it checks — plus its digest recorded **outside
git** in `<LMR_PRIVATE_EVAL_DIR>/freeze_census_pin.json`, which is the actual trust
root: an in-repo pin alone is defeated by editing the data and the pin in the same
commit, and review v5 demonstrated exactly that. Stages 5, 6 and 8 require the
pin; stage 8 additionally fails closed when the out-of-repo digest is absent or
disagrees, and `tests/test_census_trust_root.py` reproduces the co-edit. See
`docs/round0-independent-freeze-review-v{,2,3,4}.md` and `docs/progress-ledger.md`
§8.5–§8.10.

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

### Honest counts: 206 usable, 209 authored, 3 rejected

Three items were **rejected** and quarantined in `staging/rejected/` rather than
deleted, because their questions stated the very fact their evidence was
supposed to supply:

| item | split | defect |
|---|---|---|
| `qa-shadow-dev-84` | shadow_dev | stated both years it compared (1991 / 2012) |
| `qa-shadow-dev-86` | shadow_dev | stated both years (1790 / 1889); answer text was the question's own descriptor |
| `qa-dev-24` | dev | stated both compared magnitudes (300M vs 800M hectares) |

Usable: **train 60, dev 59, shadow_dev 87, total 206**. No count anywhere claims
209 usable. Ledgers: `docs/qa-shadow-dev-84-86-repair-ledger.md`,
`docs/qa-prestated-premise-sweep.md`.

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
- retrieved scale passages do **not** auto-count as false positives; the rule is
  implemented in `eval/scale_adjudication.py` and documented in
  `docs/scale-evaluation-rule.md`
- **HONEST GAP**: nothing in the current scoring path *consumes* that rule yet.
  `eval/metrics.py` and `eval/support.py` do not mention scale, adjudication, or
  false positives. The rule exists and is tested, but no evaluation currently
  applies it, so the claim "scale retrievals are adjudicated" is not yet true of
  any measurement. Wiring it into the metric layer is Round 1 work.
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
4. **Ambiguity and unanswerability are not scorable as recorded.** Of the 15
   ambiguous items, 10 put a prose disjunction in `answer_text` and 5 have an
   EMPTY `answer_text`; the 13 unanswerable items also carry an empty
   `answer_text` plus an `absent_reason`. No scorer exists, so nothing is
   silently wrong yet, but any exact-match scorer would score all of them wrong.
   The orchestrator must define how ambiguity and abstention are graded before
   that split is used for anything quantitative.
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

MET as of tag `round0-freeze-r1`. Round 1 may begin at MISE-EN-PLACE only. Round 1 workers must receive a sanitized worktree excluding the
private directory, and must not receive private results until every frozen
system has completed the private run.

---

## ROUND 1 — MISE-EN-PLACE (reports only; no implementation, no private run)

Six readiness reports exist. Each states a falsifiable hypothesis, its kill
condition, model identities with revision commits, and what is MEASURED versus
ASSUMED. None has implemented anything. None has touched private data.

| Team | Report | Headline finding |
| --- | --- | --- |
| Baselines | `experiments/baselines/` | BM25 pinned to implementation level (k1=1.2, b=0.75, no stemming, no stopwords, paragraph-node index, top-K=500, ties by `(score, node_id)`). Argues a genuinely static semantic stage adds **0–2 points**, inside noise, and says so *before* a neural team is finished. |
| Ettin cascade | `experiments/ettin-cascade/` | 17M/32M/68M recall-first cascade. Biggest risk is compound evidence loss: 0.97 per-stage retention over four stages ≈ 0.885. |
| KaLM cascade | `experiments/kalm-cascade/` | **Runtime does not survive export.** The model card supports only the PyTorch backend; no R2 GGUF exists. Also: "progressive decompression" is a misnomer — mean-pooling is lossy, so fine states cannot be derived from cached coarse states. |
| Adapter / PEFT | `experiments/adapter-peft/` | Adapters **must be merged** to be exportable; llama.cpp LoRA is llama-decoder-only and BERT/ModernBERT retrievers have no llama.cpp path at all. The advantage survives only as "small-model runtime at large-model quality", never as shipping the adapter. |
| Hybrid fusion | `experiments/hybrid-fusion/` | *(pending)* |
| Comparability | `experiments/comparability/` | Shared Stage 0 recommended; token-budget enforcement verified real; kill-condition recording protocol preregistered. |

### Two findings from mise-en-place that outrank any architecture result

**1. The corpus can only separate architectures that differ by about 10
percentage points.** Computed 2026-10-03 and now cross-checked two ways
(`experiments/comparability/CONTRACT.md` §4): 13 items / 22.0 pp on dev, 18 items
/ 12.3 pp on dev+shadow_dev, 21 items / 10.2 pp across all 206 worker-visible
items, 16 items / 13.8 pp on the sealed private set. Accepted risk #2 is no
longer "unquantified" — it is quantified, and it is worse than "underpowered for
close architectures". It is underpowered for **most** architecture pairs. Any
reported gap below the threshold is noise and must be recorded as a **null
result, never as a win**.

**2. Two of five architecture families may be blocked at the runtime layer, not
the quality layer.** KaLM's does not export to any mobile-viable backend;
adapters cannot be applied at runtime to a quantised base and must be merged,
which removes the storage argument. Neither is a retrieval-result finding. Both
are findings about whether the family can exist on a phone at all.

### Not yet done

No architecture is implemented. No synthetic training data has been cleared. No
dev run has happened. The generator floor has **not** been probed — and per
§4 of the comparability contract it must be probed before the tournament, because
if the fixed 1.5B Q4 generator floors, the whole retrieval tournament measures
nothing above the floor.
