# Round 0 Status — authoritative current state

**This file is the single authoritative "where are we now".** Every other doc in `docs/` is a
historical record of one decision, phase, or review. If a number or verdict here disagrees with an
older doc, this file wins and the older doc is stale (stale docs are listed in §9, not edited by the
steward).

Steward for this pass: `opencode/space-bunny-free` (explicit verified-free selection, never
inherited). No nested spawning. Files owned: `docs/STATUS.md`, `docs/progress-ledger.md`,
`docs/orchestration-log.md`. No source, test, corpus, staging, or other doc was modified.

---

## 1. HEAD and freeze verdict

| Field | Value |
|---|---|
| HEAD | `814dcc1` — "Phase 5a: dev expanded 10 -> 60; Phase 7 scale scaffolding started" |
| HEAD date | 2026-10-01 |
| Branch | `master` |
| Working tree | clean (no uncommitted changes) |
| Controlling spec | `master_orchestration_prompt.txt` |
| Worker policy | `AGENTS.md` |
| **FREEZE VERDICT** | **NOT FROZEN** |

### Exact reasons Round 0 is not frozen

`./scripts/verify_round0` (full mode) exits **1**: 5 stages PASS, 4 FAIL, 0 SKIP. The failures, in
the verifier's own words:

| Stage | Verdict | Reason (verbatim from the run) |
|---|---|---|
| 5 `qa-validation` | FAIL | `data_tools.validate_qa exited 1` — 120 drafts, 70 approved, **50 errors**, all of them by-design pending-review status on the new dev drafts |
| 6 `question-label-partition` | FAIL | `corpus/questions.json` and `corpus/heldout_labels.sealed.json` do not exist |
| 8 `freeze-manifest` | FAIL | `validate_freeze` returned 7 gaps (see below) |
| 9 `leakage-control-artifacts` | FAIL | `corpus/regime_b_excluded_articles.json` absent while regime B has 5 non-empty groups |

`validate_freeze` gap list (7 items):

1. missing required artifact: `corpus/questions.json`
2. missing required artifact: `corpus/heldout_labels.sealed.json`
3. `sealed_labels_sha256` unrecorded
4. `questions_sha256` unrecorded
5. `thresholds empty`: calibration policy unrecorded
6. regime metadata heldout groups not covered in manifest
7. `regime_b_document_heldout_groups is empty` but the split map has held-out groups

Additional reasons, independent of the verifier:

- **No held-out batch exists at all.** The `heldout` split count is **0**; all 120 staged drafts are
  train or dev. The controlled target is 60 train / 60 dev / 120 sealed held-out (240 total,
  `docs/qa-gate-decisions.md` §2); held-out authoring has not started.
- **The 50 new dev drafts are not independently verified.** They are authored and machine-checked
  only (see §7).
- **The scale layer is incomplete** (see §2, blocker 6, and §8).
- **No independent final freeze review has run** on the assembled substrate + corpus + question set
  (`docs/round0-review-criteria.md` Appendix B).
- **Procedural custody only.** One shared OS user; no kernel boundary. Recorded limitation, not a
  defect, but it is unclosed.

`./scripts/verify_round0 --code-only` also exits **1** (5 PASS / 1 FAIL / 1 SKIP). This is a change
from the expectation recorded in `docs/verify-round0.md` §7 ("code-level only, expected: exit 0")
and is caused entirely by stage 5 now failing. See §9.

**No architecture implementation, held-out benchmark run, or tournament conclusion is authorized.**

---

## 2. The 13 repair-agenda blockers and their status

Numbering as recorded in the repository. Blocker numbers 1–8, 10, 11 and 13 are named explicitly in
the commit message for `230e7d5` and in the three Phase 3 review reports. **Numbers 9 and 12 are not
named in any repository artifact**; the two agenda items that carry no number anywhere in the repo
are placed in those slots and marked unverified. That gap is itself a finding (§9).

| # | Blocker | Repair of record | Status |
|---|---|---|---|
| 1 | Evidence granularity: support atoms vs ancestors | `substrate/support_index.py` (derived leaf-set index), `eval/support.py`; parent paragraph satisfies **support** but is separately penalized on **precision** and **tokens**; no ancestry expansion into precision inputs. `CorpusNode` schema untouched; offsets derived | **REPAIRED** — Phase 3 review `docs/round0-review-evidence-semantics.md`, 8 executed attacks, verdict PASS |
| 2 | One score kind per trace | Per-stage `score_kind` / `threshold_policy` / model identity; `model_probability` promoted to a first-class kind; legacy migration is an explicit transform that **refuses to invent** a model identity; required `model_identity` deliberately **not** added to internal `StageRecord` with a fabricated default | **REPAIRED** — Phase 3 review `docs/round0-review-trace-storage-freeze.md` §THRESHOLD DOMAIN, 9 executed probes, PASS |
| 3 | QA semantic-audit provenance must be structural only | `validate_semantic_audit` checks structure, closed decision vocabulary, `reviewer != author`, `corpus_revision` present. Code never decides sufficiency, minimality, or answerability | **REPAIRED** — Phase 3 review `docs/round0-review-abstention-split-custody.md` §5, PASS (executed: `"looks-good"` rejected, self-review rejected) |
| 4 | Genuine multi-hop labels | Single-atom answerability test; `relabel-multihop` decision token; `hop_glosses` structural requirement | **REPAIRED for the 70 audited drafts** (Phase 4). **OPEN for the 50 new dev drafts** — machine-checked only, no independent reader |
| 5 | Split policy: one-group rule relaxed to same-split | `data_tools/verify.py` re-enforced to a same-split check; authoritative gate stays in `substrate/splits.py` | **REPAIRED in code** — Phase 3 review §4, PASS; relaxation proven not to weaken cross-split leakage prevention. **One stale artifact remains**: `data_tools/derive.py` docstring (lines 21–23) still states the superseded one-group rule (§9) |
| 6 | Distractor-scale corpus (`corpus/scale/`) | Separate path, disjoint node-id namespace, predeclared candidate list | **PARTIALLY DONE / NOT BUILT.** Declared 960 candidates (target 700); `fetch_distractors.py` written and run → **940 fetched, 20 not_found**; 940 raw snapshots on disk; `scale_build.py` written. **Missing: no tier manifests, no `scale_build_manifest.json`, no `corpus/scale/distractor.jsonl`, and `corpus/scale/tests/` is empty (0 tests).** No de-duplication check has run |
| 7 | Regimes + custody + leakage check | Regime A (`query_heldout_corpus_known`, primary) / Regime B (`document_heldout`) derived without touching the pinned split map; cross-regime aggregation refused; append-only custody audit with seal hashes; `data_tools/leakage_check.py` returns PASS/REJECT and non-revealing statistics only | **REPAIRED in code** — Phase 3 review §§6–7, PASS. **OPEN on artifacts**: regime A = 27 groups, regime B = 5 groups derived, but `corpus/regime_b_excluded_articles.json` does not exist → verifier stage 9 FAIL |
| 8 | Abstention | First-class `EvidenceDecision` with fail-closed `sufficient`/`insufficient` iff `generate`/`abstain`; shared `run_question` gate that never invokes the generator on abstain; zero-span safe floor; `zero-spans` vs `over-budget-empty` reason codes kept distinct | **REPAIRED** — Phase 3 review §§1–3, PASS (executed: generator call count 0 on abstain) |
| 9 | *(number unverified)* Freeze fail-closed corruption detection — the one agenda category in the Phase 3 storage/freeze review that carries no number | 7 corruption probes each produce an explicit gap string, never a pass | **REPAIRED in code** (7/7 probes produce gaps). **OPEN on artifacts**: `validate_freeze` still returns 7 real gaps |
| 10 | Storage honesty: a missing required artifact contributed `0` | `total_bytes` is `None` when incomplete; `known_bytes` carries only what was measured; the bug-enshrining test was **changed, not deleted** (`test_measure_storage_missing_path_is_zero` → `..._is_not_a_valid_total`) | **REPAIRED** — Phase 3 review §STORAGE HONESTY, 4 probes + test-change verification, PASS |
| 11 | Memory telemetry conflated point and peak RSS | `VmRSS` (point) and `VmHWM` (peak) are distinct readings with distinct sources; `ru_maxrss` magnitude heuristic replaced with explicit `sys.platform` dispatch | **REPAIRED** — Phase 3 review §8, PASS (live process: point 20.30 MB, peak 20.36 MB) |
| 12 | *(number unverified)* No agenda item in the repository is numbered 12; the only remaining un-numbered Phase 3 category is already recorded at slot 9 | — | **UNRESOLVED — cannot be adjudicated from repository evidence.** The orchestrator must supply the text of agenda items 9 and 12 before this row can be closed or retired |
| 13 | One-command verifier + CI | `scripts/verify_round0` (9 stages, 3 modes, exit 0/1/2) + `.github/workflows/verify-round0.yml` that downloads nothing; `--help` handled before root resolution; sealed labels only ever hashed, never opened; deterministic (two `--code-only` runs byte-identical) | **REPAIRED as a tool** — Phase 3 review §VERIFIER, PASS. **Never a freeze pass**: full mode exits 1, `--code-only` exits 1, `--help` exits 0 without running any stage |

---

## 3. What is MEASURED, what is ESTIMATED, what is HYPOTHESIZED

**Governing rule: test counts are infrastructure signal only. They are never evidence that semantic
QA is correct.** `321 tests pass` says the code runs the checks it was written to run. It says
nothing about whether a benchmark question is answerable, whether an atom is minimal, or whether a
multi-hop label is honest. The verifier prints this disclaimer on every run and a test
(`tests/test_verify_round0_entrypoint.py`) asserts no stage line can be read as a semantic verdict.

### MEASURED — rerun by the orchestrator, and independently reproduced by the steward this pass

- `tests` 321 OK, `data_tools/tests` 77 OK, `corpus/tests` 17 OK.
- `validate_qa`: 120 drafts / 70 approved / 50 errors / exit 1. Splits dev 60 / train 60 / heldout 0.
  Types: factoid 76, multihop 16, comparison 11, ambiguous 9, unanswerable 8.
- Corpus: 297 articles, 113,951 nodes, 43,876,251 bytes, canonical hash `08aa2c53…089d1` recomputed
  and MATCHING `provenance.json`; node kinds article 297 / cluster 9 / corpus 1 / paragraph 9,979 /
  section 8,146 / sentence 95,519; all four `build_manifest` artifact hashes and byte counts verified
  against disk; 218 groups / 297 articles / splits train 205, dev 44, heldout 48.
- `verify_round0` full: exit 1 (5 PASS, 4 FAIL). `--code-only`: exit 1 (5 PASS, 1 FAIL, 1 SKIP).
- QA projection hashes at 120 drafts: `runtime_projection_sha256 6adafe9c…c861`,
  `public_projection_ids_sha256 983ebec9…20c0`.
- All 16 `is_multi_hop` drafts draw their source articles from **exactly one** split-map group.
  Zero cross-group multi-hop items exist. (Steward computation, §7 method.)
- Group composition: 158 train / 28 dev / 32 heldout groups; single-article (`solo:`) groups
  142 train / 22 dev / 27 heldout.
- Scale fetch log: 960 attempts, **940 fetched, 20 not_found**; 940 raw snapshots on disk.

### MEASURED — reported by a worker/reviewer, NOT independently rerun by the orchestrator or steward

- Every semantic verdict in the Phase 4 audit (59 approve / 11 repaired) and the independent
  re-verification of all 11 repairs. Both are reviewer-asserted and evidence-cited, but no second
  party has re-executed the leave-one-out judgments.
- The 9 of 11 stored content hashes that "reproduced the reviewer's reported hashes byte-for-byte".
- Every generator timing, RSS figure, and load measurement (§ below).
- The corpus-quality-review and QA-tooling-review probe results from 2026-09-29.

### ESTIMATES / PROXIES — not measurements, not mobile claims

- Every latency, RAM, and decode-speed number in this project is a **desktop x86-64 CPU proxy**
  (i7-8700 class). No Android, ARM, or on-device number exists. No Android claim is permitted.
- The template-check load time is a fresh-process wall time with **uncontrolled page cache**; it is
  not a cache-cold measurement.
- Server RSS ~1.4–1.6 GB, client ~28 MB — reported, not reproduced here.
- Corpus removal accounting (26,784 templates, 6,854 rescues, etc.) and link counts (1,748 total
  edges, 775 cross-split) are worker-reported.

### HYPOTHESIZED — untested Round 1 questions

Tiny-Ettin sufficiency, KaLM compression retention, heads-vs-LoRA, GLiNER/Laya utility, adaptive
breadth, multi-hop frequency. None decided. `docs/model-feasibility.md` statuses are
`VERIFIED_EXISTS` / `ADVERTISED_NOT_VERIFIED`, never `EXPERIMENTALLY_VERIFIED`.

### INTERPRETATIONS — labeled judgements, not measurements

- The Q9 and T17 reviewer rejections read as reviewer hallucination rather than draft defects, on
  the strength of direct corpus checks by the orchestrator.
- "The fail-closed design worked as intended" (hash-serialization incident) is a judgement about the
  binding mechanism, evidenced only by the stopped bind and the subsequent reissue.
- The corpus review's §6 group-by-split arithmetic is read as a non-load-bearing display defect
  because the load-bearing membership checks hold.
- The Phase 4 finding that 8 of 10 multi-hop labels were inflated is a **reviewer judgment applied
  to 10 items**, now ratified by re-approval. It is not a machine-checked property of the corpus.

---

## 4. Test and artifact counts, with the exact commands that produce them

All commands run from the repository root, read-only. Python 3.14.7.

```bash
# Suites
python3 -m unittest discover -s tests                 # -> Ran 321 tests, OK
python3 -m unittest discover -s data_tools/tests      # -> Ran 77 tests, OK
python3 -m unittest discover -s corpus/tests          # -> Ran 17 tests, OK

# QA content gate
python3 -m data_tools.validate_qa \
  --staging staging \
  --corpus corpus/corpus.jsonl \
  --split-map corpus/split_map.json                   # -> exit 1; drafts 120, approved 70, errors 50

# Freeze verdict
./scripts/verify_round0                               # -> exit 1; 5 PASS / 4 FAIL / 0 SKIP
./scripts/verify_round0 --code-only                   # -> exit 1; 5 PASS / 1 FAIL / 1 SKIP
./scripts/verify_round0 --help                        # -> exit 0; no stage runs
```

**Why the verifier reports 282 tests for stage 1 and the same command reports 321.** Not a
discrepancy and not missing tests. `scripts/verify_round0` exports `VERIFY_ROUND0_IN_VERIFIER=1` to
its children; `tests/test_verify_round0_entrypoint.py` raises `SkipTest` from `setUpModule` when it
sees that marker, which skips the whole 39-test module and breaks the recursion. 321 − 39 = 282.

### Artifact counts

| Artifact | Value | Command / source |
|---|---|---|
| `staging/*.json` drafts | **120** | `ls staging/*.json \| wc -l` |
| decisions | 70 `approve`, 50 `pending` | `validate_qa` output |
| distinct primary groups used | 56 | count of `meta.group` over `staging/*.json` |
| held-out drafts | **0** | `validate_qa` `splits` |
| corpus articles / nodes / bytes | 297 / 113,951 / 43,876,251 | `verify_round0` stage 4 |
| corpus canonical hash | `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1` | stage 4, MATCHES provenance |
| corpus file SHA-256 | `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64` | `corpus/build_manifest.json` |
| split-map groups | 218 (train 158 / dev 28 / heldout 32) | `corpus/split_map.json` |
| article split | 205 / 44 / 48 | stage 4 |
| regime metadata | regime A 27 groups, regime B 5 groups | `verify_round0` stage 9 |
| scale candidates declared | 960 (target 700) | `corpus/scale/distractor_candidates.json` |
| scale fetch result | 940 fetched / 20 not_found | `corpus/scale/fetch_log.jsonl` |
| scale raw snapshots on disk | 940 | `ls corpus/scale/raw \| wc -l` |
| scale tier manifests / built DAG / tests | **0 / 0 / 0** | `ls corpus/scale/tier_*.json`, `corpus/scale/tests` |

### Pins that are now STALE and must never be reused

- Hint-free runtime projection `f7679798…bee0` was the **70-draft** projection. At 120 drafts the
  projection is `6adafe9c…c861`. The old value is a correct historical record of a smaller set and a
  wrong pin for the current tree.
- The 247-article `pilot-247-v0` hashes, the pre-amendment corpus provenance value, and the
  superseded pre-approval hash claims in the 55 rewritten rationales are all historical, not pins.
- Still-valid candidate pins, all pending freeze: corpus canonical `08aa2c53…089d1`, corpus file
  `98e1237e…d5f64`, prompt `d8580509…`, model sha `1adf0b11…6c3370`, chat template `55b2f4a26…8674a`.

---

## 5. Every recorded failure and overturned claim

Nothing below is erased. Each entry states what was claimed, what the evidence was, and what
survives.

### 5.1 Nemotron Lightning silent failure (2026-09-28)

The reference-audit worker `ses_f1484beefffe7jGqjeeYimmbWx` on `opencode/nemotron-3.5-lightning-free`
completed with **no text response**. On completion, neither `references/` nor
`docs/reference-audit.md` existed. Recorded as an **execution failure, cause unknown** — never as a
completed audit. Scope was reassigned to `opencode/muse-spark-1.3-contributor-free`, session
`ses_f1481686cffeP0E4dkP2k8JHjU`. No paid fallback.

### 5.2 Reviewer Q9 hallucination — OVERTURNED by direct corpus check (2026-09-29)

The independent verifier REJECTed `qa-pilot-dev-09`, claiming its chimpanzee node IDs did not exist
and proposing `t:chimpanzee:00:001:00/01`. The orchestrator read `corpus/corpus.jsonl` directly:
`t:chimpanzee:00:000:06/07` **exist** with matching text; the verifier's proposed IDs **do not
exist**. The rejection was overturned, no draft changed. Standing rule adopted: **reviewer claims
require corpus-grounded evidence, and the orchestrator spot-checks reviewer findings before tasking
repairs.** A reviewer is a check, not an authority.

### 5.3 Mis-serialized `draft_content_hash` — recurring incident (2026-09-29)

Several second-reader passes recorded `draft_content_hash` values that do **not** match
`data_tools.verify.draft_content_hash`, because those passes reimplemented the hash instead of
calling the repo function (suspected `ensure_ascii` default).

- The binding step **correctly STOPPED** rather than binding stale approvals. This is the fail-closed
  design working, and it is the reason the defect was caught.
- Orchestrator recompute: T52–T55 and T60 matched current bytes; **T31/35/37/50 did not**. Binding was
  blocked pending a reissue computed with the exact repo function.
- **Root cause:** `draft_content_hash` excludes only the top-level `provenance` key, so the
  `reviewed`/`reviewer` markers written *inside* each `hard_negatives` entry are part of the semantic
  hash. Any binding that writes those markers after capturing a hash invalidates it. Correct order:
  write review markers first, then compute and store the hash. All bindings now follow that order.
- **Consequence:** 55 of 70 approval rationales asserted a superseded pre-approval hash and were
  rewritten to bind approval to the current content hash, with all substantive verification findings
  preserved verbatim. The other 15 made no hash claim and were left byte-identical.
- **Residual honesty note, not papered over:** the correction makes the audit trail accurate going
  forward. It does **not** make the superseded pre-approval hash claims true, and the pre-binding
  byte state is **not reconstructible from current bytes for 5 files**.

### 5.4 Verifier worker found the manifest `groups_raw` `UnboundLocalError` (Phase 2, `230e7d5`)

While building the one-command verifier, the verifier worker found a real defect outside its own
ownership: the regime block in `substrate/manifest.py` raised
`cannot access local variable 'groups_raw' where it is not associated with a value` — on the
regime-B non-empty branch (`manifest.py:563`) and again on the regime-B empty branch
(`manifest.py:577`). `docs/verify-round0.md` §7 recorded it as outside that role's scope rather than
patching another worker's file. The orchestrator independently confirmed and fixed it. Phase 3 then
probed **both** branches explicitly (probes 8 and 9) and both now produce correct output with no
`UnboundLocalError`.

### 5.5 Three upstream worker failures in the 2026-09-30/10-01 repair run — ORCHESTRATOR-REPORTED

One **504** upstream idle timeout, one **503**, and one **502** killed three workers mid-task with no
deliverable. Per `AGENTS.md` the policy is retry → substitute to another explicitly free endpoint →
record → continue; never a paid fallback. **No paid endpoint was used at any point in this project.**
Caveat: these three failures were reported to the documentation steward by the orchestrator; no
repository artifact records session ids or endpoints for them, so they are recorded here as
orchestrator-reported and are **not** independently verifiable from the tree.

### 5.6 The abandoned one-group-rule relaxation check — ORCHESTRATOR-REPORTED

A check intended to demonstrate the one-group → same-split relaxation was started and **abandoned**;
it produced no verdict. It is recorded as an abandoned check, not as a pass and not as a failure of
the relaxation. The relaxation itself was instead verified by executed probes in the Phase 3
abstention/split/custody review §4 (train→train multi-group ALLOWED; train→heldout, train→dev,
dev→heldout, and declared-split mismatch all REJECT; empty `source_articles` REJECT). Caveat: like
5.5, this is orchestrator-reported; the abandoned check left no artifact in the tree.

### 5.7 Earlier recorded failures, still live

- **Substrate v0.1, v0.2, v0.3 — REPAIR REQUIRED each round.** Reviewer-reproduced freeze bypasses
  (changed question text, changed sampling/context/tokenizer fields, empty or overlapping group maps
  all passed freeze checks; `is_pinned()` allowed `unspecified`; whitespace token budgeting; ECE/Brier
  accepted logits; structural-only trace validation; procedure-only custodian). Never accepted from
  test counts.
- **QA tooling qualified PASS NOT ACCEPTED.** The reviewer retracted claims that conditional
  provenance checks were enforced universally, that character-offset checks established semantic
  correctness, and that label partitioning constituted independent approval/sealing. Its report file
  was also absent.
- **Generator v1/v2 — REPAIR REQUIRED** (settings overrides bypassed the fixed config, prompt tokens
  mislabeled as evidence tokens, available citations copied into emitted-citation fields, `--help`
  had side effects, config prompt hash stale, thread count drift). Old FAIL traces preserved, not
  overwritten.
- **The fixed generator does not reliably abstain.** 7/7 fresh processes produced an unsupported
  `"0.5"` on empty evidence; the v3 evidence-bearing output answered 5 units while emitting **no**
  bracketed citations. Retained as model behavior for upstream gating, not an adapter defect.
- **Corpus `pilot-247-v0` rejected for QA**: 2,936/21,353 paragraphs with markup debris (13.7%), 24
  truncated tails, 23/30 confusable groups incomplete, 310 × HTTP 429. Superseded by the offline
  `pilot-297-r1` rebuild.
- **T17 reviewer claims overturned**: a nonexistent-node claim and an NBSP-mismatch claim, both
  refuted by direct code-point comparison against `p:london_bridge:05:002` (NBSP present at both
  positions). No draft change.
- **Nine content REJECTs in the train batch**: hard-negative answer leakage T31/T37; answer-not-
  verbatim T35/T50/T52–T55/T60. All repaired by the author and re-verified as APPROVE.
- **Wrong verifier-model attribution** (spark recorded where ultra verified) on one hard-negative
  `reviewed` flag; corrected metadata-only, semantic hash unaffected by design.
- **Rate limits**: three subagents hit `Rate limit exceeded` (Muse, Ling, Mimo). Work was
  redistributed across four verified free endpoints (Space Bunny, LongCat, Nemotron Ultra). No paid
  fallback.
- **Prior `[504] Upstream idle timeout exceeded` ×3** on 2026-09-29 (corpus review `ses_f14271dd…`,
  QA isolation re-review `ses_f143b2bc…`, one pilot verifier pass). Each was retried once on the
  same verified free endpoint with tightened or split scope, then completed.
- **Corpus review §6 arithmetic blemish**: declared confusable-group counts 12/6/6 versus name lists
  of 16/6/5. Accepted because the load-bearing checks (107/107 article membership, no group split
  across splits) are consistent with orchestrator counts. Recorded, not silently fixed.

---

## 6. Phase 4 semantic audit — full result

Protocol: `docs/qa-semantic-audit-protocol.md`. Two independent second-reader passes over **all 70**
approved drafts. Parser: `scripts/parse_semantic_audit.py`. Adjudication ledger:
`docs/qa-semantic-audit-ledger.md`. Reports: `docs/qa-semantic-audit-pass1.md` (17 multihop +
comparison, plus explicit audit of `qa-train-42` and `qa-pilot-dev-05`),
`docs/qa-semantic-audit-pass2.md` (53 factoid + unanswerable + ambiguous),
`docs/qa-semantic-audit-reverify.md` (independent re-verification of the 11 repairs).

| Outcome | Count |
|---|---|
| Drafts audited | **70 of 70** |
| approve, unchanged | **59** |
| needs repair | **11** |
| reject-replace | **0** |

No draft was rejected outright. Every defect was repairable in place; no item was deleted.

### The central finding: only 2 of 10 multi-hop labels were genuine

| Draft | Genuine? | Why |
|---|---|---|
| `qa-train-05` | **yes** | Jobs → Pixar → Apple entity chain |
| `qa-train-32` | **yes** | cross-article Guido → Monty Python chain |
| the other 8 | **no** | the question **pre-states the bridging premise**, so a single support atom already determines the answer |

The 8 inflated labels are `qa-pilot-dev-03`, `qa-train-09`, `qa-train-14`, `qa-train-21`,
`qa-train-24`, `qa-train-36`, `qa-train-42`, `qa-train-44`. Their multi-hop label had degenerated
into meaning "quoted more than one passage" — precisely the failure mode BLOCKER 4 names. They were
**relabelled to factoid** with `is_multi_hop` dropped and `reference_hop_chains` cleared, not quietly
retained.

### The 11 repairs, by category (a draft may need two)

| Category | Drafts |
|---|---|
| `relabel-multihop` (6) | `qa-pilot-dev-03`, `qa-train-09`, `qa-train-14`, `qa-train-24`, `qa-train-36`, `qa-train-44` |
| `repair-minimality` (2) | `qa-train-21` (drop redundant `t:mars_bar:00:000:01`), `qa-train-42` (drop `p:seashell:11:000`) |
| combined minimality + relabel (2) | `qa-train-21`, `qa-train-42` |
| `repair-alternatives` (3) | `qa-train-28`, `qa-pilot-dev-09`, `qa-train-02` |

Named minimality case: `qa-train-42`'s hermit-crab atom is a **verbatim restatement of the question's
own first clause**, and the conchology atom alone names the answer.

Named alternative-set cases (alternatives are **encouraged**, never collapsed):

- `qa-train-28`: `{t:k2:03:000:00}` — the **sentence** atom, deliberately **not** the parent
  `p:k2:03:000`, whose continuation cites a conflicting 8609.02 m figure.
- `qa-pilot-dev-09`: `{p:gorilla:08:000}` for reading 0, `{p:chimpanzee:10:000}` for reading 1.
- `qa-train-02`: `{p:amazon_company:00:000}` for reading 0. The descendant
  `t:amazon_company:00:000:01` was correctly **not** recorded — a descendant is not a distinct set.

### Approval integrity after the audit

Semantic repairs legitimately invalidate approvals. Each repaired draft had its content changed only
as the audit specified, failed its stale-approval check, and received a **fresh** approval bound to
the **new** content hash, with the audit provenance recorded in `provenance.semantic_audit`. No bulk
re-approval and no weakened content-hash machinery. An independent reviewer who did **not** make the
edits re-verified all 11 before reissue, fetching live corpus text by `node_id` and applying
leave-one-out to the remaining sets. All 11 were APPROVE. **9 of 11** stored hashes reproduced the
reviewer's reported hashes byte-for-byte.

### Approved without change (59), and two non-blocking findings

All 5 unanswerable (absence claims verified **corpus-wide, not by sampling**), 4 of 6 ambiguous,
41 of 42 factoid, 7 comparison, 2 multihop.

- `qa-train-30`: one immaterial gloss imprecision in `absent_reason` (an AMS study mislabeled). The
  absence claim itself is verified correct.
- `qa-pilot-dev-05`: `meta.group=java` with sources spanning borneo + java is **VALID** under the new
  same-split cross-group rule — both articles carry `split_group="java"`, and both atoms are
  genuinely necessary. Approved without change. This was the finding Lane D flagged in Phase 1 as a
  real question to adjudicate, not a defect to paper over.

---

## 7. Phase 5a — dev expansion, 10 → 60

`qa-dev-11..60`: **50 new controlled dev drafts**, authored by an explicitly selected free Muse
worker and spread across the 24 previously unused dev groups.

| Property | Value |
|---|---|
| New drafts | 50 |
| Type mix of the new 50 | 26 factoid, 14 multihop, 4 comparison, 3 ambiguous, 3 unanswerable |
| Ambiguous-or-unanswerable | 12% (quota ≥ 10%) — **met** |
| Multi-hop | 28% (target ~25%) — **met on paper only**, see below |
| Approvals | **0 fabricated.** All 50 are `decision=pending` |

The author **machine-checked** every multi-hop item against the single-atom answerability test and
relabelled single-atom candidates as factoid rather than forcing them into multi-hop — the exact
defect class Phase 4 found in 8 of 10 pre-existing labels. That is the right instinct, but a
machine check by the author is **not** the two-independent-pass protocol the audit requires.

### The reported corpus limitation: no genuine same-split cross-group multi-hop chain exists

Recorded by the author rather than papered over: **no genuine same-split cross-group (dev→dev)
multi-hop chain exists in this corpus.** The 22 single-article `solo:` dev groups are topically
isolated with no real shared-entity chains, and manufacturing one would violate the
no-manufactured-hops rule. Cross-article representation is therefore **intra-group only**.

**Steward verification of that claim** (read-only, this pass): for all 16 `is_multi_hop` drafts in
`staging/`, the set of distinct split-map groups covered by `meta.source_articles` has size **1**.
Cross-group multi-hop items: **0**. The 16 items are `qa-dev-11, -14, -19, -21, -23, -25, -27, -35,
-41, -43, -47, -49, -53, -57` and `qa-train-05`, `qa-train-32`; only 2 of the 16 use more than one
source article at all.

**Consequence for accounting:** results under-**represent** cross-group multi-hop difficulty. The
"28% multi-hop" figure is a label count on single-group items and **must not** be read as 28% genuine
multi-hop. This must be stated in any final target-vs-actual accounting.

### Phase 7 scale layer — started, incomplete

`corpus/scale/` is a separate path with a disjoint node-id namespace, one-directional cross-
referencing (tier manifest cites the core hash; the core cites nothing about scale), and a stopping
rule that makes 50k non-blocking. **Scale work is explicitly not allowed to block the semantic
repairs or the freeze.**

Done: predeclared candidate list (960 titles, target 700, seed `scale-v1`, excludes the core 297);
`fetch_distractors.py` written and run; 940 snapshots fetched, 20 `not_found`; `scale_build.py`
written.

**Not done: the layer is not built.** No tier manifests, no `scale_build_manifest.json`, no
`corpus/scale/distractor.jsonl`, and `corpus/scale/tests/` is **empty**. The mechanical
de-duplication against the 297 core by pageid / title / content hash has therefore **never run**, so
it is unproven that the 940 fetched titles are disjoint from the core. `.gitignore` already declares
rules for `corpus/scale/tier_*.json` and `scale_build_manifest.json` — files that do not exist yet.

---

## 8. Known limitations and open risks

1. **The 50 new dev drafts are NOT independently verified.** This is the largest open risk. They
   carry an author-run machine check and nothing else. No second reader, no leave-one-out
   adjudication, no `provenance.semantic_audit` record, no approval. They cannot be counted toward
   the 60/60/120 controlled target, and `validate_qa` correctly reports 50 errors for them.
2. **The scale layer is incomplete** (blocker 6, §7). Unbuilt, untested, and its disjointness from
   the core 297 is unproven.
3. **Zero held-out drafts exist.** `heldout` = 0. The 120-item sealed held-out target has not
   started, and the 30 held-out groups (27 of them single-article) are entirely unexercised.
4. **No cross-group multi-hop exists in the corpus at all** (§7). The tournament cannot measure
   cross-group multi-hop on this corpus without new acquisition, which is halted.
5. **~80% of groups are single-article** (142 train / 22 dev / 27 heldout of 218), so
   `entity_confusion` hard negatives are rarely emitted. This is a dataset-composition consequence,
   not a tooling bug, and it means the hard-negative stratum-coverage claim is overbroad.
6. **Corpus removals are wholesale**: infoboxes removed from 206 articles, wikitables removed
   wholesale, `{{chem}}` unrescued, no intra-parent offsets. Absence claims are scoped to this
   snapshot, which is an offline rebuild with network acquisition halted.
7. **Semantic automation is forbidden by design, so code checks can never close the semantic gap.**
   `docs/qa-construction-protocol.md` §9: exact-span equality does not prove a span answers the
   question, entails the answer, or suffices alone or in combination. A `reviewed=True` negative is
   a recorded human claim, not a proof. Content-hash binding proves the approved bytes are unchanged,
   not that the approval was careful.
8. **The fixed generator is unreliable in exactly the way the tournament needs to measure**: 7/7
   empty-evidence runs fabricated `"0.5"`, and evidence-bearing output emitted no citations. Carried
   into Round 1 as a gating concern, not an adapter defect.
9. **Procedural custody, not enforcement.** One shared OS user; no kernel boundary. Separation rests
   on withholding the sealed file, the `HELDOUT_CUSTODIAN_MODE=benchmark` + `--allow-heldout` dual
   gate, the opaque SHA-256 record, and the append-only audit log. Two non-blocking advisories from
   Phase 3 remain open: a minimum-dev-sample guard for leakage-check calibration, and audit-log
   question-id hygiene.
10. **Test-count inflation is not evidence.** 321 + 77 + 17 tests are infrastructure signal. The
    governing rule is §3.
11. **Blocker numbers 9 and 12 cannot be adjudicated** from the repository (§2, §9).

---

## 9. Documentation inconsistencies found this pass (recorded, not edited)

The steward owns three files. Everything below is reported to the orchestrator for the owning role
to correct. No other doc was touched.

| # | Artifact | Stale or inconsistent claim | Reality at HEAD |
|---|---|---|---|
| 1 | `docs/verify-round0.md` §7 + §8 | "Code-level only (expected: exit 0)" and the stage table showing stage 5 `PASS` (70 drafts, 70 approved) | `--code-only` now exits **1**; stage 5 is **FAIL** (120 drafts, 70 approved, 50 pending). Cause: 50 new pending dev drafts. The doc's "pre-freeze, expected" framing no longer holds. |
| 2 | `data_tools/derive.py` lines 21–23 (source) | Docstring states "One-group multi-hop: every sufficient-set span must resolve to the SAME group. Cross-group multi-hop is rejected" | Superseded by the Lane D same-split ruling (`docs/qa-gate-decisions.md` §3). `verify.py` and `substrate/splits.py` now enforce same-split. A source file, so **not** steward-editable. |
| 3 | commit `814dcc1` message | "the fetcher, build script, tier manifest and tests are NOT yet written" | The fetcher (`corpus/scale/fetch_distractors.py`) and build script (`corpus/scale/scale_build.py`) are **committed in that same commit**, and the fetch has run (940 fetched). Tier manifest and tests are genuinely absent. The commit message contradicts its own contents. |
| 4 | `docs/qa-semantic-audit-pass1.md` title / `pass2.md` title | "Pass 1 of 4", "Pass 2 of 4" | Two passes were run, plus one independent re-verification. The "of 4" denominator does not correspond to any recorded plan; the protocol specifies two passes. |
| 5 | `docs/qa-semantic-audit-ledger.md` §"Repair list (11)" | Buckets labelled 6 / 3 / 3 = 12 rows for 11 drafts; `qa-train-44` appears under both `relabel-multihop` and `repair-minimality` | `pass1.md` §§342–344 records 6 relabel + 2 minimality + 2 combined, with an explicit note that `qa-train-44`'s atom drop "is covered by its relabel-multihop repair". The ledger is not wrong but its mutually-exclusive framing double-counts. |
| 6 | `docs/qa-gate-decisions.md` header + §1 | "70 controlled drafts exist in staging (60 train, 10 dev)"; "independent quality review of pilot-297-r1 is still pending" | 120 drafts (60 train, 60 dev). The corpus quality review returned **PASS** on 2026-09-29. |
| 7 | `docs/qa-construction-protocol.md` §8 | "Corpus revision `pilot-297-r1` ... awaits independent quality review" | That review is PASS. The underlying facts it also lists (no questions, no labels, no sealed files, `tokenizer_id` gap) remain true. |
| 8 | blocker numbering | The repair agenda's items **9 and 12** are not numbered anywhere in the repository | Only 1–8, 10, 11, 13 are named (commit `230e7d5` + the three Phase 3 reviews). The orchestrator must supply the text of items 9 and 12. |
| 9 | `docs/progress-ledger.md` §5 (pre-existing) | Already recorded two stale neighbor headers (`qa-gate-decisions.md`, `qa-construction-protocol.md`) | Confirmed still stale; rows 6 and 7 above extend that list. |
| 10 | `docs/qa-semantic-audit-protocol.md` header | "**NOT EXECUTED.** No draft has been audited under this protocol yet." | Phase 4 executed it over all 70 drafts and re-verified all 11 repairs. |
| 11 | `docs/qa-semantic-audit-protocol.md` lines 3–8 | "The 70 staging drafts predate it and validate under migration grace ... they will be audited in Phase 4" | Audited. Now 120 staging drafts, 50 of which are new and unaudited. |
| 12 | `docs/verify-round0.md` §7 stage 1 | Reports 282 tests without explaining the recursion guard | 321 minus the 39-test self-referential entrypoint module. Not a defect; worth a one-line note so the two numbers are not read as missing tests. |

---

## 10. Who measured what

| Claim class | Attributed to | Independently rerun? |
|---|---|---|
| Test counts 321 / 77 / 17 | orchestrator, then steward | **Yes** — steward reproduced all three this pass |
| `validate_qa` 120 / 70 / 50 / exit 1 | worker reported in commit `814dcc1` | **Yes** — steward reproduced exactly, including the projection hashes |
| `verify_round0` exit 1, 4 failing stages | verifier worker at `230e7d5`, then orchestrator | **Yes** — steward reproduced full and `--code-only` this pass |
| Corpus hashes, node counts, group counts | orchestrator | **Yes** — steward reproduced this pass |
| Phase 4 audit: 59 approve / 11 repaired | two independent second readers + orchestrator adjudication | **No** — reviewer-asserted, evidence-cited, not re-executed by a third party |
| Phase 4 re-verification of the 11 repairs | one independent reviewer (did not author the repairs) | **No** |
| The 50 new dev drafts | one free Muse author, machine-checked only | **No, and this is the gap** |
| Scale fetch result 940/20 | worker | **No** — steward counted `fetch_log.jsonl` and the raw directory only |
| Generator timings, RSS, decode rates | workers | **No** — desktop proxies, never reproduced |
| 504/503/502 failures; abandoned relaxation check | orchestrator, verbally this run | **No** — no repository artifact records them |
| Model endpoints for this repair run | orchestrator selections, recorded in the commit and review headers | Endpoints are named in the review docs; their zero-cost status was verified at selection time in earlier sessions, **not** re-verified this pass |

Free models used in the 2026-09-30/10-01 repair run, all explicitly selected, none inherited:
`opencode/muse-spark-1.3-contributor-free` (Phase 1 design lanes A/C/D/F, audit pass 2, dev
authoring), `opencode/nemotron-3-ultra-free` (Phase 1 lane B/E, audit pass 1, repair re-verification,
all three Phase 3 adversarial reviews), `opencode/space-bunny-free` (one-command verifier; this
documentation pass). Nested spawning was disabled throughout. No paid endpoint was used at any point
in this project.
