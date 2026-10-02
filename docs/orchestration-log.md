# Orchestration log

## 2026-09-28 — Round 0 opened

Orchestrator: `openai/gpt-6-astra`.

The live OpenCode model catalog was queried before any worker spawn. These selected endpoints were listed active with input, output, cache-read and cache-write prices all zero:

| Role | Explicit endpoint | Status |
| --- | --- | --- |
| Substrate lead | `opencode/muse-spark-1.3-contributor-free` | Delegated |
| Reference audit | `opencode/nemotron-3.5-lightning-free` | Delegated |
| Independent reviewer | `opencode/nemotron-3-ultra-free` | Reserved; not yet spawned |

Catalog registration does not itself establish runtime reliability; worker execution will provide that evidence. No endpoint substitution has occurred. Local LM Studio registrations with unspecified costs were not treated as verified free endpoints.

Nested spawning is disabled. All worker assignments require explicit model selection by the orchestrator.

## Work allocation

- Substrate lead owns `substrate/`, `eval/`, `tests/`, `pyproject.toml`, and `docs/experimental-contract.md`.
- Reference researcher owns `references/` and `docs/reference-audit.md`; audits AndroidLM and boar-app source revisions, benchmark provenance, and corpus/generator feasibility.
- Orchestrator owns governance, task integration, gate decisions, and independent review assignment.

## Gate state

### Model-change notice and verification checkpoint (2026-09-29)

### Generator template residual closed (2026-09-29)

Live `/props` chat-template hash matches the pinned config value (`55b2f4a26…8674a`); server binary hash matches; ephemeral process reaped. Worker outputs: `scripts/generator_template_check.py`, `generator_runtime/template_check_20260929T130348.json`, `docs/generator-template-check.md`. Status queries only, no generation.

### QA batch progress and hash-serialization incident (2026-09-29)

Train batch authored: 60 drafts (`staging/qa-train-01..60`), validated with only pending-review errors. Independent second-reader (Ultra) verified in six passes of 10 plus two re-verification passes. Verdict ledger: most drafts APPROVE; content REJECTs found and repaired by the author, then re-verified and approved — answer-not-verbatim (T35, T50, T52–T55, T60), hard-negative answer leakage (T31, T37), a nonexistent-node claim (T17, unfounded) and NBSP-mismatch claim (T17, also unfounded — overturned by direct corpus check).

**Hash-serialization incident (recurring):** several second-reader passes recorded `draft_content_hash` values that do not match `data_tools.verify.draft_content_hash`, because those passes reimplemented the hash instead of calling the repo function (suspected `ensure_ascii` default). The binding step correctly STOPPED rather than binding stale approvals — the fail-closed design worked as intended. Orchestrator independently recomputed: T52–T55, T60 re-verification hashes MATCH current bytes; T31/35/37/50 do NOT (their earlier hashes are from the flawed serialization). Binding is blocked on a hash reissue for T31/35/37/50 using the exact repo function.

**Also recorded:** a hard-negative "reviewed" flag was initially bound with an incorrect verifier-model attribution (spark instead of ultra) and corrected metadata-only; content hashes are unaffected because `provenance` is excluded from the semantic hash.

**Root cause of the stale-hash class (orchestrator-confirmed):** `data_tools.verify.draft_content_hash` excludes only the top-level `provenance` key, so the `reviewed`/`reviewer` markers written *inside* each `hard_negatives` entry are part of the semantic hash. Any binding that writes those markers after capturing a hash invalidates it. Correct binding order is: write the review markers first, then compute and store the hash. All bindings now follow this order.

**Audit-trail correction completed:** 55 of 70 approval rationales asserted a superseded pre-approval hash; they were rewritten to state that approval binds to the current content hash, with all substantive verification findings preserved verbatim. The other 15 made no hash claim and were left byte-identical. All 70 files verified `draft_content_hash == provenance.content_hash`; validation still 70/70 approved, 0 errors, and the retriever-visible runtime projection hash is bit-identical (`f7679798…bee0`), proving question inputs were unaffected.

**Residual honesty note:** the correction makes the audit trail accurate going forward. It does not make the superseded pre-approval hash claims true, and the pre-binding byte state is not reconstructible from current bytes for five files. This is recorded as a known provenance limitation rather than papered over.

**Rate limits:** three subagents hit `Rate limit exceeded` (Muse, Ling, Mimo). Work was redistributed across four different verified free endpoints (Space Bunny, LongCat, Nemotron Ultra). No paid fallback.

### Train batch complete: 70/70 approved (2026-09-29)

Orchestrator independently reran `python3 -m data_tools.validate_qa`: drafts 70, approved 70, errors 0, exit 0. Splits train 60 / dev 10 / held-out 0. Types: 42 factoid, 10 multihop, 7 comparison, 6 ambiguous, 5 unanswerable. Runtime projection (hint-free question input) sha256 `f76797988f77a92d41f437eb16e45673d4f0e3a8b2cb9b3e12b7febf4abdbee0`.

Remaining before freeze: dev remainder (20), held-out batch (30) under orchestrator custody, rationale-correction pass, then seal and final freeze review.

### Version control checkpoint (2026-09-29)

Repository initialized and pushed. Tracked: substrate, eval, tests, data_tools, generator_runtime code and traces, corpus manifests/provenance/split map, staging drafts, all docs and review artifacts. Gitignored with hash-pinned provenance preserved on disk: 986 MB generator weights, 42 MB corpus JSONL, 41 MB raw snapshots, 39 MB superseded pilot archive, and any sealed held-out labels.

### Dev pilot complete: 10/10 approved (2026-09-29)

Pilot workflow validated end to end: authoring → independent verification → binding. `python3 -m data_tools.validate_qa` independently rerun by orchestrator: approved 10, errors 0, exit 0. Incidents and fixes: verifier's false Q9 rejection overturned by direct corpus check (verifier hallucination — reviewer claims now require corpus-grounded evidence); verifier hash serialization mismatch corrected by reissue; binding step's verifier-model misattribution corrected to the true Ultra second-reader. All recorded above. Next: full train batch (60), then dev remainder (20) + held-out (30).

### Verifier rejection overturned on Q9 (2026-09-29)

Independent verifier rejected `qa-pilot-dev-09` claiming its chimpanzee node IDs don't exist. Author disputed with corpus evidence; orchestrator checked `corpus/corpus.jsonl` directly: `t:chimpanzee:00:000:06/07` EXIST with matching text, while the verifier's proposed `t:chimpanzee:00:001:00/01` do NOT exist. The rejection was a verifier hallucination — overturned, no draft change. Lesson recorded: verifier claims require corpus-grounded evidence, and orchestrator spot-checks reviewer findings before tasking repairs.

### Pilot verifier timeout, split retry (2026-09-29)

Independent pilot verifier (Ultra) hit a transient 504 with no deliverable. Retrying once on the same verified free endpoint with a split scope (high-risk drafts first, remainder second) to reduce timeout risk. Substitution to a different free endpoint follows if this fails.

### QA gate decisions (2026-09-29, orchestrator)

- Corpus: `pilot-297-r1` (297 articles; 205/44/48). Protocol doc must be refreshed from stale 247-article assumptions.
- Question volume: 60 train / 30 dev / 30 held-out; quotas ≥10% unanswerable-or-ambiguous, ≥20% multi-hop. Pilot first: 10 dev questions to shake out the workflow.
- Multi-hop rule: one-group restriction KEPT for Round 0 (limitation recorded; cross-group chains excluded, not silently allowed).
- Custodian: orchestrator-held procedural custody (same-user limitation documented); sealed file withheld from dev workers; dual gate `allow_heldout + HELDOUT_CUSTODIAN_MODE=benchmark`.
- Public questions: dev/reference only, pinned by exact file bytes + revision before import.

### Retry outcomes: corpus quality PASS, QA tooling PASS (2026-09-29)

Both retried workers completed on `opencode/nemotron-3-ultra-free`:
- Corpus quality review (`docs/corpus-quality-review-r1.md`): **PASS** — manifest byte/SHA match, canonical hash recomputation, zero hierarchy errors, offline-build evidence, clean debris sample, group/split integrity, sampled provenance metadata.
- QA tooling re-review (`docs/qa-tooling-independent-review-v02.md`): **PASS** — all 7 repair items verified with focused synthetic probes; 216 tests (41 + 175) passing.

Orchestrator verification and qualifications:
- All four rebuilt artifact hashes recomputed from disk and matched against `corpus/build_manifest.json` (note: an earlier orchestrator read showed a different provenance hash, so provenance was amended mid-session; current manifest and disk agree).
- Split map independently checked: 218 groups, 297 articles, train/dev/held-out 205/44/48.
- Corpus review accepted with one blemish: its group-by-split arithmetic in §6 is internally inconsistent (counts vs name lists), though the load-bearing checks (107/107 membership, no group split across splits) are consistent with worker claims and orchestrator checks.
- QA review accepted as code validation only. Its residual item citing “247 vs 500 articles” is stale — the corpus is now the 297-article rebuild; the protocol doc needs that update before QA authoring. Semantic annotation review (entailment, true unanswerability) remains future work.
- Still missing for freeze: controlled questions, sealed held-out labels, custodian assignment, final freeze review.

### Worker timeout failures and retry policy (2026-09-29)

Two workers failed with transient upstream errors (`[504] Upstream idle timeout exceeded`), not with verdicts:
- Corpus quality review (`ses_f14271dd1ffe224bATui9Lakai`, `opencode/nemotron-3-ultra-free`): no deliverable; `docs/corpus-quality-review-r1.md` absent.
- QA isolation re-review (`ses_f143b2bccffeSNKUyJM25CaIwW`, `opencode/nemotron-3-ultra-free`): no deliverable.

Per policy (retry, then substitute, record, continue; never paid fallback): both are retried once on the same verified free endpoint with tightened scopes to reduce timeout risk. If either fails again, it will be reassigned to a different explicitly free endpoint. Progress ledger (`docs/progress-ledger.md`) delivered successfully by the documentation steward.

Model change acknowledged. The new orchestrator endpoint ID is not exposed in this runtime context, so no specific replacement model is asserted. Worker policy is unchanged: explicit free-model selection only, no inheritance, no paid fallback, no anonymous router for important work. Nested spawning remains disabled.

Independent verification just executed:
- `python3 -m unittest discover -s tests`: **175/175 PASS**.
- `python3 -m unittest discover -s data_tools/tests`: **41/41 PASS**.
- Corpus converter tests: **17/17 PASS** (only `ResourceWarning`s about unclosed test files; no failures).
- Build-manifest byte/SHA checks for all four rebuilt corpus artifacts: **match**.
- Rebuilt `corpus/corpus.jsonl` loads as **113,951 nodes** with **zero hierarchy errors**; canonical corpus hash recomputed as `08aa2c53…089d1`, matching rebuilt provenance.
- `references/model-catalog.json` and `corpus/split_map.json` parse successfully.

Status corrections:
- The provenance-gate PASS remains scoped to code/metadata enforcement. Its “Round 0 Freeze Status” artifact list is now stale: the filesystem contains a rebuilt `pilot-297-r1` corpus, while `corpus/questions.json` and sealed held-out labels still do not exist.
- The rebuilt corpus exists on disk but is **not accepted**: the corpus worker completion report and independent corpus quality review are still pending. Rebuild outputs preserve the prior 247-article snapshot under `corpus/archive/pilot-247-v0/`.
- Model feasibility is metadata-only evidence, not selection or advantage proof. Material gaps include unpinned model revisions, KaLM mobile/export uncertainty, unverified community runtime builds, and no experimental measurements.

### Dataset repair verification and shared model feasibility survey

Orchestrator independently reran repaired data-tool tests: **41/41 PASS**. Independent free Ultra re-review assigned for provenance, semantic-approval binding, ambiguity mappings, safe question projection, sealing, and public-import pins. Semantic review may be performed by an independent explicitly named free-model agent; no unrequested requirement for manual user annotation is imposed. Code checks cannot establish semantic truth alone.

While corpus rebuilding and gate review proceed, an explicit free Muse researcher is verifying model availability/cards/revisions/API capabilities using live Hub metadata under `docs/model-feasibility.md` and `references/model-catalog.json`. Metadata-only research is shared Round 0 feasibility work; no weights, architecture implementation, or experiment-team divergence is authorized.

### Corrected dataset review artifact received

`docs/qa-tooling-independent-review.md` now exists and supersedes the earlier conversational qualified PASS. Reviewer explicitly retracts claims that conditional provenance checks were enforced universally, that character-offset checks established semantic correctness, and that label partitioning constituted independent approval/sealing. Verdict: **REPAIR REQUIRED**, consistent with the already assigned dataset-tool repairs. No new acceptance or freeze follows from the corrected review.

### Corpus quality gate: original conversion rejected for QA

Completed corpus audit reported 2,936/21,353 paragraphs with markup debris (13.7%), 24 truncated paragraph tails, and 23/30 incomplete confusable groups. Fifty additional raw snapshots existed from an earlier paced resume and were excluded from the original converted snapshot. No QA labels exist, so corpus revision remains pre-freeze.

Orchestrator authorized **offline-only** rebuild from existing 297 raw snapshots using the repaired converter, preserving original 247 outputs/hashes under an archive and original seeded group assignments. No further network acquisition authorized. Required checks: exact raw-input/builder manifests, two-build deterministic reproduction, conversion regressions and manual source comparisons, honest removal/loss accounting, and independent quality review. Original 247 corpus is not accepted for QA authoring.

### Dataset review qualified PASS not accepted

Reviewer returned a qualified PASS focused on lexical-negative naming, but its assigned report file was absent. Orchestrator inspection of `data_tools/verify.py` and `qa_schema.py` found additional gaps: optional provenance context bypass, ambiguous-reading semantics not checked, sealing merely partitions without independent content-bound approval, and source-article hints present in evaluator question metadata. Exact code-point text matching is not semantic entailment verification or byte-offset validation.

Original free Muse dataset lead assigned repairs, including retriever-safe question projection, source coverage checks, explicit independent annotation review records, and exact public-import pins. Original free Ultra reviewer assigned a corrected written report for its original snapshot. No real QA creation or held-out release is authorized by the earlier qualified PASS.

### Corpus artifact available; bounded pilot scope

Dataset lead delivered preparatory `data_tools/` and reported corpus artifact availability. Orchestrator independently ran data-tool tests: **16/16 PASS**, then inspected `corpus/provenance.json`: 247 articles (174 train-source / 37 dev-source / 36 held-out-source), 21,353 paragraphs, 81,232 sentences, 39,622,343-byte JSONL, zero recorded hierarchy errors, 310 acquisition gaps including HTTP 429. Corpus hash reported `ead3d771122c05e1499b06ca1393bfa4e5963bc7f532a5639554337b2d5a64f0` awaits final independent corpus validation.

Orchestrator chose provisional bounded 247-article pilot rather than more network fetching. Original free corpus worker resumed for completed conversion/coverage audit and accurate acquisition-limit reporting, with further network disabled. Independent free Ultra dataset-tool review assigned before real QA creation. No real QA/labels were created by preparatory tooling assignment; its claimed corpus compatibility does not establish corpus acceptance.

### Provenance repair verified; dataset workflow preparation

Orchestrator independently reran the suite after mandatory QA provenance repair: **175/175 PASS**. Independent free Ultra reviewer assigned a narrow final provenance check; no overall freeze claim follows from unit-test success.

A separate explicit free Muse dataset lead is preparing import/validation tooling and the QA construction/custody protocol under `data_tools/`. Actual questions and held-out labels must wait for validated corpus and group assignments. The lead may not inspect/poll acquisition, alter corpus files, or create evaluation labels during this preparatory assignment.

### v0.3 review disposition: mandatory supervised provenance

Independent review confirms the five prior freeze bypasses closed, but controlled QA without source metadata still bypasses source-group validation. Orchestrator chose mandatory nonempty source-article provenance for controlled QA, plus an explicit provenance-backed `public_reference` category allowed only in development/reference use. Public questions with unavailable evidence labels must retain unknown ground truth, not receive zero recall. Assigned narrow repair/tests to original explicit free Muse lead. Full freeze remains blocked until this check and real artifacts are accepted.

### Generator adapter PASS; substrate v0.3 review opened

Independent generator reviewer issued **PASS scoped to captured v3 adapter snapshot**, with commands/hashes in `docs/generator-independent-review-v03.md`. It is not a model-quality PASS or a Round 0 freeze. Reviewer notes actual runtime `/props` template hash is not independently compared; pinned model/runtime bytes and actual template token accounting cover the reviewed configuration, and the residual limitation remains documented.

Orchestrator independently reran v0.3 substrate tests: **147/147 PASS**. New independent substrate review assigned to explicit free Ultra. Focus includes optional QA source metadata: checking group-map article uniqueness alone cannot establish article-disjoint supervised QA when questions omit their source provenance. Missing actual corpus/questions/sealed labels still prevents freeze independently of code review.

### Empty-evidence diagnostic result

Worker raw result `generator_runtime/empty_probe_20260928T232340.json` records seven identical unsupported `0.5` answers across fresh, evidence-first, and empty-first synthetic conditions. Orchestrator inspected the stored empty prompt and pinned configuration. Interpretation: the failure occurs without preceding session evidence and no tested order effect was observed; this supports model/prompt behavior rather than dependence on previous evidence. It does not rule out every possible session/cache defect. Orchestrator corrected the analysis report's stronger causal wording and process-count typo; raw traces remain unchanged. No generator or prompt tuning followed this result.

### Second substrate review: freeze bypasses reproduced

Independent reviewer delivered `docs/substrate-implementation-review-v02.md` and raw probe outputs. Changed question text, changed generator sampling/context/tokenizer fields, and empty/overlapping group maps still passed freeze checks. Orchestrator assigned artifact-inventory/full-config pinning, group-assignment validation, runtime byte verification, and common trace-policy validation to the original explicit free Muse lead.

Two additional scientific corrections were included: hallucinated citations must remain valid recorded model failures, not cause trace rejection and selection bias; sufficient-set completion must be binary (with best fractional coverage separately named). Round 0 substrate freeze must not require learned architecture thresholds before architecture work starts. Missing actual corpus and QA remain separate external readiness gaps.

### Integrated generator verification and adverse observation

Generator v3 delivered with synchronized prompt, one thread, shared parser, and CLI help guards. Orchestrator independently executed `python3 scripts/generator_adversarial.py`: **14/14 PASS**. These establish checked infrastructure behavior only.

Orchestrator read `generator_runtime/smoke_trace_v3_20260928T231945.json`: with evidence, output answered 5 units but emitted no bracketed citations; with empty evidence, output invented a threshold of 0.5. Both are retained failures, not successful abstention/citation outcomes. A narrow paired fresh-process versus reused-session empty-evidence probe was delegated to the same explicit free Muse worker to investigate session-state contamination without changing the fixed generator or prompt. Worker-reported fresh-process repeats and timings remain synthetic scoped observations.

### Shared evidence repair verified; generator integration assigned

Orchestrator independently reran the suite after the narrow evidence/prompt repair: **113/113 tests pass**. Common prompt hash is now `d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63`. Full-serialization budgeting, strict prefix cap behavior, and shared citation parsing were delivered.

Original explicit free Muse generator worker resumed to synchronize this prompt and parser, pin one thread, add side-effect-free CLI help/main guards, and run predeclared synthetic cross-process repetitions. Single-user-message delivery through the pinned embedded chat template is accepted as the common interface design, subject to implementation verification. Old smoke traces must be preserved with attribution caveats. No benchmark evaluation is authorized.

### Evidence/generator integration decisions

Substrate v0.2 passed 88 tests in an independent orchestrator rerun. Generator repair v2 was delivered with worker-reported runtime pinning and adversarial checks; independent free Ultra generator review assigned separately.

Orchestrator inspection found packet token counts summed per-span tokenization rather than measuring the complete serialized string, and first-span overflow was allowed. Assigned narrow shared evidence repair: strict ranked-prefix packing, exact complete-string counting, overflow marking, and honest empty-packet handling. This is a pilot cap policy, not an assertion that all future experiments must impose a 1000-token absolute limit.

Worker observed cross-process generation differences at six threads and identical outputs in a one-thread synthetic probe. Orchestrator chose one thread for the fixed Round 1 generator, pending integration/repeated verification. Common prompt will clarify copying actual bracketed source identifiers after a synthetic output used literal `[node_id]`; this is pre-freeze interface repair, not benchmark-based prompt tuning. Config synchronization waits for the new shared prompt hash.

### Criteria adjudication after second repair

Latest reviewer delivery still contradicted article-disjoint supervised QA and introduced unsupported fixed statistical/repeat counts. Orchestrator added an explicit controlling adjudication to `docs/round0-review-criteria.md`: global searchable corpus shared, supervised source groups disjoint for article-generalization pilot; uncertainty methods matched to outcomes/dependence; independently validated reproducibility tolerances; no mandatory second machine; process-cold timing not a conservative mobile projection. Remaining draft text is not automatically binding. Review completion is not acceptance.

### Implementation verdict and repair assignments

Independent implementation review returned **REPAIR REQUIRED**. Orchestrator accepted the need for artifact-integrity checks, semantic trace validation, exact-token budgeting, richer provenance, and explicit recovery metrics. Some suggested fixes were qualified: raw ranking logits are legitimate typed scores; sigmoid alone is not calibration; evidence-set completion must not replace standard recall under the same name. The original free Muse substrate lead was resumed for repairs and adversarial tests.

The generator worker delivered the 986,048,768-byte Qwen2.5-1.5B Q4_K_M artifact. Orchestrator independently ran `sha256sum` and confirmed `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370`. Adapter acceptance was withheld: settings overrides bypassed fixed configuration, prompt tokens were mislabeled as evidence tokens, and available citations were copied into emitted-citation fields. The same explicit free worker is repairing these and runtime pinning/lifecycle checks. Reported initial smoke timings remain worker measurements, not independently reproduced performance findings.

Corpus acquisition is still running asynchronously. Draft documentation is not a completed or validated corpus; no duplicate build was launched.

### Reference audit and acquisition assignments

Replacement audit delivered `docs/reference-audit.md` and `references/pins.json`. Source-reported device numbers and model hashes remain externally reported, not independently measured artifact properties. Audit recommendation of lead-only extracts was not accepted as sufficient to test hierarchical pruning. `df -h` measured 33 GB free on the workspace filesystem.

Two explicit free Muse workers were assigned: structured full-article pilot corpus acquisition (200 MB download / 500 MB initial artifact cap), and Qwen2.5-1.5B Q4_K_M generator/runtime verification (2 GB download / 4 GB disk cap). Neither may create held-out labels or run benchmark questions. Corpus is a bounded pilot; no full-corpus generalization claims are justified.

### Protocol criteria sent back for repair

Orchestrator inspection of `docs/round0-review-criteria.md` identified incorrect multiplication of unconditional survival rates, unsupported hard readiness cutoffs, conflation of shared corpus access with supervision leakage, incorrect directory-permission guidance, and overly restrictive multi-hop assumptions. The original independent critic was explicitly resumed on `opencode/nemotron-3-ultra-free` for correction. Criteria are a draft, not an accepted gate or implementation PASS. Poor measured survival is a valid negative result, not itself invalid science.

### Substrate delivery and orchestrator verification

Substrate lead delivered interfaces, schemas, evaluation helpers, telemetry, manifest validation, synthetic infrastructure tests, and `docs/experimental-contract.md`. The orchestrator independently ran `python3 -m unittest discover -s tests`: 34 tests passed. These are infrastructure checks, not retrieval quality measurements.

Initial source inspection found freeze validation does not recompute artifact hashes, and the survival helper's irreversible-loss assumption needs qualification for alternate retrieval routes and multi-hop recovery. Independent implementation review assigned to `opencode/nemotron-3-ultra-free`, session `ses_f148098b8ffejzMV67nLpsS0s9`, with explicit free-model selection and nested spawning disabled. Review outcome pending; no acceptance inferred from test count.

### Worker execution failure and substitution

The reference-audit worker `ses_f1484beefffe7jGqjeeYimmbWx` using `opencode/nemotron-3.5-lightning-free` completed without a text response. On completion, neither `references/` nor `docs/reference-audit.md` existed. This is an execution failure, not a completed audit; its cause is unknown.

Reassigned the same scoped audit to the previously verified zero-cost endpoint `opencode/muse-spark-1.3-contributor-free`, session `ses_f1481686cffeP0E4dkP2k8JHjU`. No paid fallback was used.

**ROUND 0 IN PROGRESS — NOT FROZEN.** No architecture implementations, held-out benchmark runs, or tournament conclusions are authorized by this state.

Freeze requires actual pinned corpus and generator artifacts, split provenance and isolation, executable measurement/evaluation interfaces, meaningful verification, and independent review. A design document alone is insufficient.

---

## 2026-09-30 / 2026-10-01 — Round 0 repair run (Phases 1–7) and documentation steward pass

Authoritative current status: **`docs/STATUS.md`**. This section is the chronological record of the
repair run; where the two disagree, `docs/STATUS.md` wins.

Repository: `local_mobile-research`, branch `master`, HEAD at the start of the documentation pass
`814dcc1`. Commits produced by the repair run, in order: `230e7d5` (Phases 1–2), `3e82aa2` (Phase 3),
`9756649` (Phase 4), `814dcc1` (Phase 5a + Phase 7 start).

### Free models used in this run — all explicitly selected, none inherited

| Role | Endpoint | Note |
|---|---|---|
| Phase 1 design lanes A, C, D, F | `opencode/muse-spark-1.3-contributor-free` | design only |
| Phase 1 design lanes B, E | `opencode/nemotron-3-ultra-free` | design only |
| Phase 2 implementation lanes A–E + verifier | explicitly free endpoints, per-lane selection | no lane inherited a model |
| Phase 3 independent adversarial reviews ×3 | `opencode/nemotron-3-ultra-free` | reviewer did not write the code reviewed |
| Phase 4 audit pass 1 (multihop + comparison, 17 drafts) | `opencode/nemotron-3-ultra-free` | |
| Phase 4 audit pass 2 (factoid + unanswerable + ambiguous, 53 drafts) | `opencode/muse-spark-1.3-contributor-free` | |
| Phase 4 re-verification of the 11 repairs | `opencode/nemotron-3-ultra-free` | did not author the repairs |
| Phase 5a dev authoring (50 drafts) | explicitly free Muse endpoint | zero approvals fabricated |
| Phase 7 scale candidates/fetcher/build script | explicitly free Muse endpoint | |
| Phase 2 one-command verifier | `opencode/space-bunny-free` | |
| Documentation steward (this pass) | `opencode/space-bunny-free` | owns `docs/STATUS.md`, `docs/progress-ledger.md`, appended section here |

Nested spawning was disabled for the whole run. No paid endpoint was used at any point in this
project, in this run or any previous one. Endpoint zero-cost status was verified at selection time
in the sessions named above; it was **not** re-verified during the documentation pass, and catalog
absence of pricing is not itself proof.

### Phase gates

| Phase | Gate | Outcome |
|---|---|---|
| 1 | Design adjudication, six independent lanes | **Accepted with rulings.** `docs/round0-repair-plan.md`. Design only — no implementation. Five shortcuts explicitly rejected: char offsets on `CorpusNode`; a fabricated `"legacy-unknown"` `model_identity`; automated `p:`→minimal `t:` atom selection; collapsing alternative sufficient sets; externally-pinned embedding-similarity thresholds. In-place `corpus/split_map.json` edits also rejected. |
| 2 | Five implementation lanes + one-command verifier | **Delivered at `230e7d5`.** Blockers 1–8, 10, 11, 13 addressed. The bug-catching storage test was *changed with the fix*, not deleted, by explicit ruling. |
| 3 | Three independent adversarial reviews | **All PASS** (`3e82aa2`). Executed probes, not code reading. Component verdicts only — none is a freeze, none certifies a semantic QA label. Two non-blocking advisories recorded (leakage-check calibration minimum-dev-sample guard; custody audit-log id hygiene). |
| 4 | Semantic audit of all 70 drafts | **Executed for the first time** (`9756649`). 70 audited, 59 approve unchanged, 11 repaired, 0 rejected. Largest finding: only **2 of 10** multi-hop labels genuine. Independent re-verification of all 11 repairs by a reviewer who did not author them; 9 of 11 stored hashes reproduced byte-for-byte. |
| 5a | Dev expansion 10 → 60 | **50 new drafts, 0 approvals.** All `pending`; the author machine-checked the single-atom answerability test rather than forcing single-atom items into multi-hop. **Not independently verified** — this is the largest open risk. |
| 5b | Atomization migration | **NOT STARTED.** Deliberately sequenced after the audit, per the Phase 1 cross-lane ruling, so the audit runs on paragraph spans first. |
| 6 | Held-out authoring + sealing | **NOT STARTED.** `heldout` = 0 of a 120-item target. |
| 7 | Distractor-scale corpus | **Started, not built.** 960 predeclared candidates, 940 fetched, 20 `not_found`, 940 raw snapshots on disk, fetcher and build script written — but **no tier manifests, no `scale_build_manifest.json`, no `distractor.jsonl`, and `corpus/scale/tests/` is empty (0 tests).** The de-duplication against the core 297 has never run. Per the Lane F ruling, scale must not block the repairs or the freeze. |
| Freeze | `validate_freeze` on a real manifest | **Never passed.** Returns 7 gaps. |

### Failures and incidents in this run — none erased

- **Three upstream worker failures.** One **504** upstream idle timeout, one **503**, one **502**; each killed a worker with no deliverable. Policy applied per `AGENTS.md`: retry, then substitute to another explicitly free endpoint, record, continue. No paid fallback. *Recorded from the orchestrator's report; no repository artifact records session ids or endpoints, so these are not independently verifiable from the tree.*
- **Abandoned check.** A check intended to demonstrate the one-group → same-split relaxation was started and **abandoned with no verdict**. Recorded as abandoned — not as a pass, and not as a failure of the relaxation. The relaxation was instead verified by executed probes in the Phase 3 abstention/split/custody review §4: train→train multi-group ALLOWED; train→heldout, train→dev, dev→heldout, declared-split mismatch and empty `source_articles` all REJECT; the retriever projection returns exactly `{question_id, text}` and raises on any extra key. *Also orchestrator-reported; the abandoned check left no artifact.*
- **Real defect found by the verifier worker outside its own ownership:** `substrate/manifest.py` raised `cannot access local variable 'groups_raw' where it is not associated with a value` on the regime-B non-empty branch and again on the regime-B empty branch. The verifier recorded it rather than patching another worker's file; the orchestrator independently confirmed and fixed it; Phase 3 then probed **both** branches explicitly.
- **Carried forward from earlier rounds, still live:** the Nemotron 3.5 Lightning Free silent non-response (no output, no files — an execution failure, not a completed audit); the Q9 reviewer hallucination overturned by direct corpus check; the T17 nonexistent-node and NBSP-mismatch claims, both unfounded; the recurring mis-serialized `draft_content_hash` incident whose root cause is that the semantic hash excludes only top-level `provenance`, so `hard_negatives[].reviewed`/`.reviewer` markers are hashed and any marker write after hash capture invalidates it; the 55 rewritten approval rationales and the unreconstructible pre-binding byte state for 5 files; the corpus review §6 arithmetic blemish; the fixed generator's 7/7 empty-evidence `"0.5"` fabrication and missing citations. Full inventory in `docs/STATUS.md` §5.

### Current gate state, re-measured by the steward (read-only, 2026-10-01)

`./scripts/verify_round0` → **exit 1**; 5 stages PASS, **4 FAIL**, 0 SKIP. Failing stages: 5
`qa-validation` (`validate_qa` exits 1), 6 `question-label-partition` (`corpus/questions.json` and
`corpus/heldout_labels.sealed.json` absent), 8 `freeze-manifest` (7 `validate_freeze` gaps), 9
`leakage-control-artifacts` (`corpus/regime_b_excluded_articles.json` absent while regime B has 5
non-empty groups).

`./scripts/verify_round0 --code-only` → **exit 1**; 5 PASS / 1 FAIL / 1 SKIP. This contradicts the
expectation recorded in `docs/verify-round0.md` §7 ("code-level only, expected: exit 0") and is
caused entirely by stage 5 now failing with 50 pending-review dev drafts. Flagged for the verifier
owner; not edited by the steward.

Independently reproduced this pass: `tests` 321 OK, `data_tools/tests` 77 OK, `corpus/tests` 17 OK;
`validate_qa` 120 drafts / 70 approved / 50 errors / exit 1, splits dev 60 / train 60 / **heldout 0**,
runtime projection `6adafe9c…c861`; corpus 297 articles / 113,951 nodes / canonical hash
`08aa2c53…089d1` MATCHING provenance / 218 groups / 205-44-48. The verifier's stage 1 reports 282
tests rather than 321 because it exports `VERIFY_ROUND0_IN_VERIFIER=1` and
`tests/test_verify_round0_entrypoint.py` then skips its own 39-test module to break the recursion
cycle; 321 − 39 = 282. Not missing tests.

**Stale pin warning.** The hint-free runtime projection `f7679798…bee0` is the **70-draft** projection
and must never be reused. At 120 drafts the projection is `6adafe9c…c861`. Still-valid candidate
pins, all pending freeze: corpus canonical `08aa2c53…089d1`, corpus file `98e1237e…d5f64`, prompt
`d8580509…`, model sha `1adf0b11…6c3370`, chat template `55b2f4a26…8674a`.

**REPAIR-ROUND COMPONENT GATES: CLOSED ON EXECUTED PROBES** (evidence semantics; trace / storage /
freeze / threshold / verifier; abstention / split / custody / memory). **EVERYTHING ELSE REMAINS
OPEN.** Corpus gate closed (`pilot-297-r1`); QA tooling gate closed for code validation only; QA
content gate open; freeze artifacts absent.

**ROUND 0 NOT FROZEN.** `corpus/questions.json` absent; sealed held-out labels absent and the
held-out batch unstarted; `regime_b_excluded_articles.json` absent; `thresholds` empty; 7
`validate_freeze` gaps open; 50 dev drafts unverified; scale layer unbuilt; no independent final
freeze review; custody procedural only. No architecture implementations, held-out benchmark runs, or
tournament conclusions are authorized by this state.

### Open item the orchestrator must close

The repair agenda's **blocker numbers 9 and 12 are not recorded in any repository artifact.** Only
1–8, 10, 11 and 13 are named, in commit `230e7d5` and the three Phase 3 review reports. The steward
placed the only un-numbered Phase 3 category (freeze fail-closed corruption detection) in slot 9 and
left slot 12 explicitly unresolved rather than inventing text. The orchestrator must supply the
wording of agenda items 9 and 12. See `docs/STATUS.md` §2 and §9.

### Documentation steward pass — scope and findings

Owned and written: `docs/STATUS.md` (new, the single authoritative status file),
`docs/progress-ledger.md` (updated), and this appended section. Nothing else was modified — no
source file, test, `staging/`, `corpus/`, `data_tools/`, `substrate/`, `eval/`, or
`generator_runtime/`. Reruns were strictly read-only.

Twelve stale or internally inconsistent documentation claims were found and **recorded rather than
edited**, because each belongs to another role. They are tabulated in `docs/STATUS.md` §9. The three
that matter most:

1. `docs/verify-round0.md` §7/§8 — `--code-only` "expected: exit 0" and stage 5 `PASS` are both now
   wrong.
2. `data_tools/derive.py` lines 21–23 — the module docstring still states the **superseded one-group
   multi-hop rule**, while `verify.py` and `substrate/splits.py` enforce the same-split rule. A
   source file, so not steward-editable.
3. Commit `814dcc1`'s own message says the scale fetcher and build script "are NOT yet written", yet
   it commits both, and the fetch has already run. The commit message contradicts its own contents.

`docs/STATUS.md` is now the single authoritative current-status file. Where any other doc disagrees
with it, that doc is stale — and where this log's earlier 2026-09-28/29 sections disagree, the later
dated sections win.

---

## 2026-10-01 → 2026-10-02 — benchmark-boundary repair run

Orchestrator run. Premium orchestrator model only; every worker explicitly
selected a verified zero-cost endpoint, and nested spawning was disabled
throughout.

| Phase | Worker endpoint(s) |
|---|---|
| 1 reclassify | `muse-spark-1.3-contributor-free` |
| 2 audit batches A/B/C | `muse-spark-1.3-contributor-free`, `nemotron-3.5-lightning-free`, `qwen3.8-27b:free` |
| 3 paired regimes | `muse-spark-1.3-contributor-free` |
| 4 scale semantics | `nemotron-3.5-lightning-free` |
| 5 private custody | `nemotron-3-ultra-free` (aborted twice; implemented by orchestrator) |
| 6 private authors | `muse-spark-1.3-contributor-free` (batches a, e, f), `nemotron-3.5-lightning-free` (batch b — garbled, 0 files), `qwen3.8-27b:free` (batch c), `space-bunny-free` (batch d) |
| 6 private reviews | `nemotron-3-ultra-free` (1–34, 101–104), `gemma-4-31b-it:free` (35–67, 105–120 — provider error both times), `qwen3.8-27b:free` (68–100), `space-bunny-free` (35–67 and 105–120 substitutes) |
| 6 re-approval | `space-bunny-free` |
| 7 freeze gate | `nemotron-3-ultra-free` |
| 7 84/86 repair | `nemotron-3-ultra-free` |
| 8 independent review | `qwen3.8-27b:free` (substitute for the failed gemma) — verdict REPAIR REQUIRED |
| 8 freeze-review repairs | orchestrator |

Substitutions were recorded at the point they happened. No paid endpoint was
used at any point, and no worker inherited the orchestrator model.
