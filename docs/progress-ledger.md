# Round 0 Progress Ledger (steward-maintained)

> **The single authoritative current-status document is now `docs/STATUS.md`.** This ledger is the
> chronological record. Where the two disagree, `docs/STATUS.md` wins.

Steward model (current update pass): `opencode/space-bunny-free` (explicit verified free endpoint, selected by the orchestrator, never inherited). Previous steward passes: `opencode/muse-spark-1.3-contributor-free`. No nested spawning.
Scope: this pass owns `docs/STATUS.md` (new), `docs/progress-ledger.md` (this file), and an appended section of `docs/orchestration-log.md`. No source, test, staging, corpus, or other doc was edited.
Status: **ROUND 0 IN PROGRESS — NOT FROZEN.** 120 QA drafts exist (train 60 / dev 60), of which 70 are approved and **50 are pending independent review**. No held-out batch, no sealed labels, no `corpus/questions.json`, no `corpus/regime_b_excluded_articles.json`. `./scripts/verify_round0` exits 1 (4 failing stages). No architecture work, no benchmark runs, no tournament conclusions, no freeze claim authorized.
Controlling spec: `master_orchestration_prompt.txt`. Worker policy: `AGENTS.md`. Orchestrator record: `docs/orchestration-log.md`. Authoritative status: `docs/STATUS.md`.

Method: worker claims below are attributed and preserved as claims; orchestrator verification notes appear only where `docs/orchestration-log.md` records an independent orchestrator rerun. Read-only reruns executed by the steward in the 2026-09-29 update pass are labeled **steward-measured** and are limited to `python3 -m data_tools.validate_qa` plus file-presence checks. The 2026-09-30/10-01 update pass executed a wider read-only set — all three unittest suites, `validate_qa`, `verify_round0` in full and `--code-only` mode, and read-only counts over `staging/`, `corpus/split_map.json`, and `corpus/scale/` — and those are labeled **steward-measured (2026-10-01)**. Measured results, estimates, hypotheses, and interpretations are labeled. Nothing was re-executed beyond that read-only set.

Governing rule carried into this pass: **test counts are infrastructure signal only, never evidence that semantic QA is correct.** 321 + 77 + 17 passing tests establish that the code runs the checks it was written to run; they establish nothing about whether a question is answerable, an atom minimal, or a multi-hop label honest.

## 1. Chronology

### 2026-09-28 — Round 0 opened
- Orchestrator (`openai/gpt-6-astra` per log) verified free catalog endpoints before any spawn: substrate lead `opencode/muse-spark-1.3-contributor-free`, reference audit `opencode/nemotron-3.5-lightning-free`, reviewer `opencode/nemotron-3-ultra-free` reserved. Nested spawning disabled.
- Work allocation: substrate lead owns `substrate/`, `eval/`, `tests/`, `pyproject.toml`, `docs/experimental-contract.md`; reference researcher owns `references/`, `docs/reference-audit.md`; orchestrator owns governance/gates/reviews.

### 2026-09-28 — Substrate delivery (worker claim)
- Substrate lead (Muse Spark Free) delivered interfaces, schemas, eval helpers, telemetry, manifest validation, synthetic infra tests, `docs/experimental-contract.md`.
- Worker-reported: `python3 -m unittest discover -s tests` → 34 pass (infra checks only).
- Orchestrator verification (log): independently reran → 34 pass confirmed. Finding: freeze validation did not recompute artifact hashes; survival helper irreversible-loss assumption needed qualification. Assigned independent review (`opencode/nemotron-3-ultra-free`).

### 2026-09-28 — Reference-audit worker failure + substitution (measured by orchestrator)
- Worker `ses_f1484beefffe7jGqjeeYimmbWx` (Nemotron 3.5 Lightning Free) completed with no text response; `references/` and `docs/reference-audit.md` absent. Recorded as execution failure, cause unknown.
- Substitution: same scope reassigned to verified zero-cost `opencode/muse-spark-1.3-contributor-free`, session `ses_f1481686cffeP0E4dkP2k8JHjU`. No paid fallback.

### 2026-09-28 — Replacement reference audit delivered (worker claim)
- `docs/reference-audit.md` (Muse Spark Free): pinned AndroidLM `ed3d51a…95457` and boar-app `0dda83f…4144`; bounty bar verified via repo quotes only (live bounty page fetch returned JS shell, unverified). Eval analysis: AndroidLM 494 questions, Claude-judge, fixed sampling `temp 0.7/top_p 0.8/top_k 20/presence 1.5/seed 1234`, no calibration/survival/traces; boar-app 17 queries, manual grading, FTS5+cosine, per-row telemetry. Corpus: AndroidLM 21.3 GB wiki.db + 2.9 GB places + voyage/ethereum (CC BY-SA 4.0 / ODbL 1.0); boar ~300 summaries + Vital5 option. Generator recommendation: `bartowski/Qwen2.5-1.5B-Instruct-GGUF` Q4_K_M 986,048,768 B, sha `1adf0b11…6c3370`, Apache-2.0, via llama.cpp; no 35B/7–8B/MoE for Round 1. Split procedure: article-level 70/15/15 before derivation; public questions dev/reference only. Verified-vs-unknown table states manifest byte/sha claims, HF contents, device numbers NOT independently re-verified (no downloads). Handoff blockers listed as substrate-lead/orchestrator scope.

### 2026-09-28 — Corpus + generator assignments
- Two Muse Spark Free workers assigned under caps: pilot corpus acquisition (200 MB download / 500 MB artifact cap); Qwen2.5-1.5B Q4_K_M verification (2 GB / 4 GB). Neither may create held-out labels or run benchmarks. Bounded pilot; no full-corpus generalization claims.
- Workspace disk measured `df -h`: 33 GB free (orchestrator measurement).

### 2026-09-28 — Substrate review v0.1: REPAIR REQUIRED (independent reviewer, Nemotron 3 Ultra Free)
- `docs/substrate-implementation-review.md`: 34 tests pass but 10 blocking gaps — fake freeze acceptance (no hash recompute), irreversible-loss survival, ECE/Brier accepting logits, structural-only trace validation, `is_pinned()` allowing `unspecified` quant/runtime, whitespace token budget, single required-evidence set, procedural-only custodian, missing Round-4 trace fields, unverified code hashes. P0: items 1–5. Verdict: cannot freeze.

### 2026-09-28 — Generator artifact + repair v2 (worker claims)
- Generator worker (Muse Spark Free) delivered 986,048,768 B Qwen2.5-1.5B Q4_K_M. Orchestrator independently ran `sha256sum` → confirmed `1adf0b11…6c3370`.
- Adapter acceptance withheld: settings overrides bypassed fixed config, prompt tokens mislabeled as evidence tokens, available citations copied into emitted fields. Same worker assigned repair + runtime pinning/lifecycle checks. Smoke timings worker-measured only.
- Repair v2 delivered (worker claim, `docs/generator-readiness.md`): hardened settings, runtime hash checks, exact-vs-estimate token separation, parsed-not-copied citations, `max_tokens` cap, reaped shutdown. Adversarial 13/13 claimed. Cross-process finding: identical within-session at temp 0/seed 1234; 3 textually distinct outputs across processes at `-t 6` (factually identical "5 units") → orchestrator chose threads=1 for Round 1.

### 2026-09-28 — Substrate review v0.2: REPAIR REQUIRED (Ultra reviewer)
- `docs/substrate-implementation-review-v02.md`: 88 tests pass; P0s from v0.1 mostly fixed, but 5 new P0 gaps — questions content unhashed, generator disk compare incomplete, group-map path-only, trace weaker than policy, no runtime binary hashes in config/manifest. Withheld freeze; learned thresholds explicitly NOT required before Round 1.

### 2026-09-28 — Evidence/generator integration decisions (orchestrator)
- Orchestrator reran substrate suite → 88 pass (verified). Found packet token counts summed per-span, first-span overflow allowed. Assigned narrow shared repair: strict ranked-prefix packing, exact whole-string counting, overflow marking, honest empty-packet handling. Pilot 1000-token cap is policy, not universal limit. Prompt clarified to copy actual bracketed ids (pre-freeze repair, not benchmark tuning).
- Shared repair delivered (Muse Spark Free, `docs/evidence-token-repair.md`): full-serialization counting, strict cap incl. first span (overflow → empty + truncated), prompt v0.1→v0.2 (`PROMPT_HASH d8580509…`), shared `parse_citations`. Worker-reported 113/113 tests pass. Orchestrator independently reran → 113/113 confirmed (log).

### 2026-09-28 — Generator integration + v3 (worker claims, orchestrator checks)
- Generator worker synced prompt/parser, pinned 1 thread, CLI help guards, synthetic cross-process repetitions. Smoke v3 + adversarial 14/14 + repeat 3/3 byte-identical claimed (`docs/generator-readiness.md` §0b).
- Orchestrator independently executed `python3 scripts/generator_adversarial.py` → 14/14 PASS (infra behavior only). Read `generator_runtime/smoke_trace_v3_20260928T231945.json`: evidence-bearing output answered 5 units with no bracketed citations; empty-evidence output invented 0.5 threshold — retained failures, not successes.
- Empty-evidence probe (`generator_runtime/empty_probe_20260928T232340.json`, 7 identical unsupported `0.5` answers): orchestrator inspected stored prompt/config; interpretation corrected to model/prompt behavior without preceding-evidence dependence, not ruling out every session/cache defect; fixed analysis wording typo. No tuning followed.

### 2026-09-28 — Generator independent reviews
- v1 review (`docs/generator-independent-review.md`, Ultra): REPAIR REQUIRED — 4 blocking defects (both scripts `--help` side effect; config `prompt_hash` v0.1 vs substrate v0.2; `runtime_threads_measured` 6 vs ruled 1; `chat_template_sha256` naming ambiguity). Adversarial 13/13 executed by reviewer; preserved traces confirmed v0.1 provenance.
- v03 review (`docs/generator-independent-review-v03.md`, Ultra, stable snapshot with file hashes): **PASS scoped to captured v3 adapter snapshot** (prompt hash match, threads=1, `--help` clean, runtime/model pins, shared parser, exact cap, cleanup, output cap). Residual gap noted: runtime `/props` template hash not live-compared; pinned bytes + token accounting cover reviewed config. Model-behavior observations recorded (v0.2 kills literal `[node_id]` but cites descriptively with `cited_valid: []`; empty packet → unsupported "0.5"; no faithfulness guarantee). Orchestrator disposition (log): PASS is adapter-scoped, not model-quality or freeze.

### 2026-09-28 — Substrate v0.3 + review v0.3
- Substrate lead delivered v0.3 repairs (`docs/substrate-repair-v03.md`): questions/sha pins, raw config byte pin + semantic compare, group-map validation, unified `ThresholdPolicy.validate()`, runtime inventory, binary completion, unknown-citation permit, `model_probability` state. Worker-reported 147/147 pass. Orchestrator independently reran → 147/147 confirmed (log); assigned Ultra re-review.
- v0.3 review (`docs/substrate-implementation-review-v03.md`, Ultra): 147 tests pass, all 5 v0.2 P0 bypasses closed (verified probes). New concern is design policy, not code defect: `validate_qa_group_consistency` skips metadata-less questions — for controlled article-generalization, provenance should be mandatory. Verdict: REPAIR REQUIRED on that one design point.

### 2026-09-28/29 — Provenance mandate + repair + final review
- Orchestrator decision (log §"v0.3 review disposition"): mandatory nonempty `source_articles` + `group` for controlled QA, plus explicit `public_reference` dev-only category; public questions with unavailable evidence keep ground truth UNKNOWN, never zero. Narrow repair + tests to original Muse lead. Freeze still blocked pending check + real artifacts.
- Repair delivered (`docs/provenance-gate-repair.md`, Muse Spark Free): `validate_question_provenance`, `build_article_index`, mandatory provenance both split modes, `public_reference` dev-only with required fields, shared-corpus resolution, id/count-only errors. Worker-reported 175/175 pass. Orchestrator independently reran → 175/175 confirmed (log).
- Final provenance review (`docs/substrate-provenance-final-review.md`, Ultra, 2026-09-29): **PASS on provenance gate** (28 new tests, all acceptance criteria closed). Explicitly NOT a freeze: lists missing corpus/questions/sealed labels, pending re-review, procedural custody as remaining blockers. Notes same-split cross-group multihop rejected by one-group restriction as recorded pilot limitation.

### 2026-09-29 — Dataset tooling + corrected review + repairs
- Dataset lead (Muse Spark Free) delivered `data_tools/` + `docs/qa-construction-protocol.md` (protocol + tooling only, NOT executed; no questions/labels/sealed files). Worker-reported 16/16 data-tool tests pass; orchestrator reran → 16/16 confirmed at the time (log). Scoped: no corpus modification, no label creation.
- Independent QA tooling review, corrected (`docs/qa-tooling-independent-review.md`, Ultra): **REPAIR REQUIRED**, superseding earlier conversational qualified PASS. Retracts universal conditional-provenance enforcement, char-offset-as-semantic claims, and label-partition-as-approval claims. Blocking: `bm25_nearmiss` misname, conditional provenance gate, char-vs-byte offsets, ambiguous-reading→set binding. Process gaps: second-reader, corpus finality, custodian, import hash, volume — orchestrator decisions.
- Repairs delivered (`docs/qa-tooling-repair.md`, Muse Spark Free): `token_overlap_nearmiss` rename, required verification context (fail-closed), readings/consistency/bool-offset checks, source-coverage/overlap/candidate-vs-reviewed, code-point equality + content-bound approval, retriever-only projection + hash, `seal_records()` replacing `split_for_seal`, importer 40-hex/64-hex pins + `check_import_pin`. Worker-reported 41/41 data-tool + 175/175 shared pass. Orchestrator independently reran data-tool tests → 41/41 confirmed (log). Ultra re-review assigned for provenance binding, ambiguity mappings, safe projection, sealing, public-import pins.
- Orchestrator note (log): semantic review may use an independent named free-model agent; no unrequested manual user annotation imposed; code checks alone cannot establish semantic truth.

### 2026-09-29 — Corpus pilot v0 (worker claim) then rejection
- Corpus worker (Muse Spark Free) reported 247 articles (174 train-source / 37 dev-source / 36 heldout-source), 21,353 paragraphs, 81,232 sentences, 39,622,343 B, hash `ead3d771…d5a64f0`, 310 acquisition gaps (HTTP 429). Orchestrator ran data-tool tests 16/16 and inspected `corpus/provenance.json` but flagged hash as awaiting independent validation.
- Corpus audit (orchestrator-directed): 2,936/21,353 paragraphs markup debris (13.7%), 24 truncated tails, 23/30 confusable groups incomplete; 50 extra raw snapshots excluded from snapshot. No QA labels existed. Orchestrator rejected v0 for QA, authorized **offline-only** rebuild from 297 raws with repaired converter, archiving v0 under `corpus/archive/pilot-247-v0/`. No further network authorized.

### 2026-09-29 — Model feasibility survey (shared Round 0 work, worker claim)
- Researcher (explicit free Muse endpoint) delivered `docs/model-feasibility.md` + `references/model-catalog.json`, metadata-only, no weights. Claims: all 6 Ettin sizes VERIFIED (17M–1B; 1B no ONNX, desktop-only); KaLM Nano R2 VERIFIED (1.57 GB, custom loader, no ONNX — mobile blocked); static-retrieval MRL VERIFIED zero-transformer (125 MB, ONNX present); GLiNER2.5-small VERIFIED (73.9M; LoRA story unverified); Laya VERIFIED (421M non-autoregressive; runtime builds unverified); Qwen3 rerankers VERIFIED as teacher options; LoRA-vs-heads unmeasured; Engram as opaque memory (not citable) with transferable prefetch/addressing ideas. Material gaps: unpinned revisions, KaLM export/code-API unknowns, unverified community builds, no measurements. Orchestrator disposition (log): metadata-only evidence, not selection or advantage proof; no weights/architecture/experiment divergence authorized.

### 2026-09-29 — Corpus rebuild pilot-297-r1 (worker claim) + orchestrator checkpoint
- Corpus worker (Muse Spark Free) reports offline rebuild (`docs/corpus-pilot.md` §§0/9–11): 297 articles, 113,951 nodes, 43,876,251 B, canonical hash `08aa2c53…089d1`, splits 205/44/48, 1,748 article edges (44.3% cross-split by shared-DAG design), zero confirmed markup debris (3 LaTeX false positives/9,979 paras), two-build byte-identical determinism (excluding `built_utc`), 17/17 converter/offline tests claimed. Known removals documented: infoboxes wholesale (206 articles), wikitables wholesale, `{{chem}}` unrescued, no intra-parent offsets. No questions/labels/config created. Awaits independent quality review.
- Orchestrator verification checkpoint (log 2026-09-29): independently reran `tests` 175/175, `data_tools/tests` 41/41, converter tests 17/17 (ResourceWarnings only); build-manifest byte/SHA match; `corpus.jsonl` loads 113,951 nodes, zero hierarchy errors, hash recomputed `08aa2c53…089d1` matching rebuild provenance; `model-catalog.json` + `split_map.json` parse. Status corrections: provenance-gate PASS is code/metadata-scoped; prior "Round 0 Freeze Status" artifact list stale (`questions.json`/sealed labels still absent); rebuilt corpus exists but NOT accepted pending worker completion report + independent quality review; feasibility is metadata-only.

### 2026-09-29 — Generator live template check: MATCH (closes v03 residual)
- Generator worker (Muse Spark Free) delivered `scripts/generator_template_check.py`, `generator_runtime/template_check_20260929T130348.json`, `docs/generator-template-check.md`. Live `GET /props` `chat_template` SHA-256 `55b2f4a26…8674a` == config `tokenizer_gguf.chat_template_runtime_sha256` == top-level `chat_template_sha256`; live template 2506 bytes == `chat_template_bytes_runtime_props`; server binary SHA-256 `5a5aa40e…28f` matched expected; config snapshot `5f0975d6…a9fc`. Status queries only — no generation.
- Cleanup: ephemeral server terminated, reaped, port closed, process gone. Load timing is fresh-process wall time with page cache uncontrolled — not a cold-cache measurement, no mobile claim. Closes the v03 residual template gap; the adapter PASS still remains adapter-scoped, not a freeze.

### 2026-09-29 — Retried independent reviews: corpus quality PASS, QA tooling PASS
- Two review workers had already died on `[504] Upstream idle timeout exceeded` with no deliverable (corpus review `ses_f14271dd…`, QA isolation re-review `ses_f143b2bc…`, both on `opencode/nemotron-3-ultra-free`). Per policy: retry once on the same verified free endpoint with tightened scope, then substitute; no paid fallback. Retries completed.
- Corpus quality review (`docs/corpus-quality-review-r1.md`, Ultra): **PASS** — 4/4 artifact byte/SHA match vs `build_manifest.json`; canonical and canonical-text hashes recompute to `08aa2c53…089d1`; 0 hierarchy errors; offline-build evidence (13 converter + 4 offline-path determinism/network-blocking tests) with a source scan showing no network calls in executable code; 0/30 sampled paragraphs with markup debris; 28 confusable groups / 107 articles matching `split_map.json` exactly; splits 205/44/48 matching provenance; 30-article metadata sample complete; node-kind counts match.
- Orchestrator verification: recomputed all four artifact hashes from disk (match); independently counted 218 groups / 297 articles / 205-44-48. One blemish accepted and recorded: review §6 confusable-group-by-split arithmetic is internally inconsistent (declared counts 12/6/6 vs name lists of 16/6/5) while the load-bearing checks (107/107 membership, no group split across splits) are consistent with worker claims and orchestrator counts. `pilot-297-r1` accepted as the derivation substrate.
- QA tooling re-review (`docs/qa-tooling-independent-review-v02.md`, Ultra): **PASS** — 9 focused synthetic probes verify all 7 repair items (nearmiss rename, fail-closed verification context, readings/consistency/bool offsets, source coverage + ancestor/descendant negative rejection, code-point equality + content-bound approval, retriever projection exactly `{"question_id","text"}`, `seal_records()` revalidation with dual held-out gate, importer 40-hex/64-hex pins); 41 data-tool + 175 shared tests. Accepted as **code validation only**; its residual "247 vs 500 articles" text is stale (substrate is the 297-article rebuild). Semantic entailment and true unanswerability remain unverified.
- Orchestrator status correction: corpus provenance was amended mid-session after an earlier read showed a different value; manifest, provenance, and disk now agree. The earlier reading must not be reused as a pin.
- QA gate decisions recorded (`docs/qa-gate-decisions.md`): 60 train / 30 dev / 30 held-out with quotas ≥10% unanswerable-or-ambiguous and ≥20% multi-hop; one-group multi-hop KEPT (44.3% cross-split article-edge limitation stated, not silently generalized past); orchestrator-held procedural custody with dual gate; public questions dev/reference only via byte-pinned import. `corpus/questions.json` and any sealed file remained absent at that point.

### 2026-09-29 — Dev pilot complete: 10/10 approved, with two overturned/corrected incidents
- Pilot workflow validated end to end: authoring → independent second-reader verification → binding. Orchestrator reran `python3 -m data_tools.validate_qa`: approved 10, errors 0, exit 0.
- Incident A — **verifier rejection overturned**: `qa-pilot-dev-09` was REJECTed for allegedly nonexistent chimpanzee sufficient-set node IDs, proposing `t:chimpanzee:00:001:00/01`. Orchestrator checked `corpus/corpus.jsonl` directly: `t:chimpanzee:00:000:06/07` EXIST with matching text; the verifier's proposed IDs do NOT. Rejection was a verifier hallucination — overturned, no draft change. Lesson: reviewer claims require corpus-grounded evidence, and the orchestrator spot-checks reviewer findings before tasking repairs.
- Incident B — hash serialization mismatch in the pilot verifier pass, corrected by hash reissue from the repo function.
- Incident C — a hard-negative `reviewed` flag was bound with an incorrect verifier-model attribution (spark instead of ultra) and corrected metadata-only; content hashes unaffected because `provenance` is excluded from the semantic hash.
- One pilot verifier pass also hit a transient 504 with no deliverable; retried once on the same verified free endpoint with a split scope (high-risk drafts first).

### 2026-09-29 — Train batch: 60 drafts authored, 70/70 approved after repairs
- 60 train drafts authored (`staging/qa-train-01..60`); validation produced only pending-review errors. Independent second reader (Ultra) verified in six passes of 10 plus two re-verification passes (`docs/qa-train-verification.md`).
- Content REJECTs found, repaired by the author, re-verified, and approved: answer-not-verbatim T35, T50, T52, T53, T54, T55, T60; hard-negative answer leakage T31 ("Python" via Monty Python text) and T37 ("Saturn" via Saturn Corporation text). Re-verification confirmed each repair by exact-substring check.
- Reviewer claims that did **not** survive checking: T17 nonexistent-node claim and T17 NBSP-mismatch claim — both unfounded; direct code-point comparison against corpus node `p:london_bridge:05:002` showed NBSP present at both positions. Overturned, no draft change.
- Orchestrator rerun: `python3 -m data_tools.validate_qa` → drafts 70, approved 70, errors 0, exit 0; splits train 60 / dev 10 / held-out 0; types 42 factoid, 10 multihop, 7 comparison, 6 ambiguous, 5 unanswerable; hint-free runtime projection SHA-256 `f7679798…bee0`. Steward read-only rerun in this pass reproduced approved 70 / errors 0 / same projection hash.

### 2026-09-29 — Recurring hash-serialization incident: root cause, reissue, rationale correction
- Incident: several second-reader passes recorded `draft_content_hash` values that do NOT match `data_tools.verify.draft_content_hash`, because those passes reimplemented the hash instead of calling the repo function (suspected `ensure_ascii` default). The binding step correctly STOPPED rather than binding stale approvals — the fail-closed design worked as intended.
- Orchestrator recompute: T52–T55 and T60 re-verification hashes match current bytes; T31/35/37/50 do NOT (their earlier values came from the flawed serialization). Binding was blocked pending a reissue using the exact repo function; authoritative reissue values are recorded in `docs/qa-train-verification.md` (2026-09-29 reissue table).
- **Root cause of the stale-hash class (orchestrator-confirmed):** `data_tools.verify.draft_content_hash` excludes only the top-level `provenance` key, so the `reviewed`/`reviewer` markers written *inside* each `hard_negatives` entry are part of the semantic hash. Any binding that writes those markers after capturing a hash invalidates it. Correct order: write review markers first, then compute and store the hash. All bindings now follow that order.
- **Rationale correction:** 55 of 70 approval rationales asserted a superseded pre-approval hash; they were rewritten to state that approval binds to the current content hash, with all substantive verification findings preserved verbatim. The other 15 made no hash claim and were left byte-identical. All 70 files then verified `draft_content_hash == provenance.content_hash`; validation remained 70/70 approved, 0 errors; the runtime projection hash is bit-identical (`f7679798…bee0`), proving retriever-visible question inputs were unaffected.
- **Residual honesty note (recorded, not papered over):** the correction makes the audit trail accurate going forward. It does not make the superseded pre-approval hash claims true, and the pre-binding byte state is not reconstructible from current bytes for five files. This is a known provenance limitation.

### 2026-09-29 — Rate limits and endpoint redistribution
- Three subagents hit `Rate limit exceeded` (Muse, Ling, Mimo). Work was redistributed across four different verified free endpoints (Space Bunny, LongCat, Nemotron Ultra). No paid fallback at any point; substitutions and failures recorded per policy.

### 2026-09-29 — Version control checkpoint
- Repository initialized and pushed to a private GitHub remote (`github.com/davidghatley/local-mobile-research`), commit `4d924c5` "Round 0: experimental substrate, corpus, fixed generator, and QA tooling". Tracked: substrate, eval, tests, data_tools, generator_runtime code and traces, corpus manifests/provenance/split map, staging drafts, all docs and review artifacts.
- Gitignored but preserved on disk and hash-pinned: 986 MB generator weights (`generator_runtime/artifacts/`, pinned in `corpus/generator_config.json`), 42 MB `corpus/corpus.jsonl` (pinned in `corpus/build_manifest.json` + `provenance.json`), 41 MB `corpus/raw/` snapshots, 39 MB superseded `corpus/archive/` snapshot, and any sealed held-out labels. A missing artifact still blocks freeze even though git history is complete.

### 2026-09-30 — Round 0 REPAIR opened; Phase 1 design adjudication (six free design lanes)
- Orchestrator opened a Round 0 repair round against HEAD `b38a457` after thirteen agenda blockers were catalogued. Ruling recorded in `docs/round0-repair-plan.md`.
- Six independent free-model design lanes ran in parallel, no nested spawning: Lane A evidence semantics / support atoms (Muse Spark Free), Lane B per-stage score kinds (Nemotron Ultra Free), Lane C abstention / storage / memory (Muse Spark Free), Lane D QA semantic audit / minimality / genuine multi-hop / same-split (Muse Spark Free), Lane E regimes / custody / expansion (Nemotron Ultra Free), Lane F distractor-scale corpus (Muse Spark Free). **Design only — no implementation.**
- Accepted: ancestry-aware support satisfaction via a derived leaf-set index; per-stage `score_kind` + `threshold_policy`; first-class `EvidenceDecision` with a fail-closed abstain gate; two machine-readable regimes with an append-only custody audit and a custodian-run synthetic leakage check; leave-one-out minimality over atoms with a closed decision vocabulary and the single-atom answerability test; a separate `corpus/scale/` wrapper layer with a stopping rule that makes 50k non-blocking.
- Rejected, and the rejections matter: char offsets added to `CorpusNode` (derive them instead); a required `model_identity` on internal `StageRecord` with a fabricated `"legacy-unknown"` default (silent provenance fabrication is the exact failure class this project exists to prevent); any automated `p:` → minimal `t:` atom selection (an overlap heuristic leaks answer text into ground truth and biases the tournament toward lexical architectures); collapsing alternative sufficient sets; any bulk re-approval; pinned embedding-similarity thresholds asserted from an external default; in-place modification of `corpus/split_map.json`.
- Cross-lane conflicts resolved: Lane A "minimal atom" vs Lane D "minimal set" → Lane D wins, with Lane A's constraint attached (an atom that internally carries answer + setup is `repair-minimality` and must be re-atomized); Lane A rejecting `p:` atoms vs the existing 70 drafts → atomization migration deferred until AFTER the audit, so the audit runs on paragraph spans first; Lane B legacy migration vs Lane C fail-closed → legacy *traces* migrate via an explicit recorded transform, legacy *outcomes* missing a decision fail closed.
- Sequencing fixed: implement A/B/C/D/E in parallel on disjoint files → orchestrator reruns the full suite after each integration (no test-count inflation accepted as evidence) → Phase 3 adversarial review by a reviewer who did not write the code → Phase 4 audit of all 70 drafts → THEN atomization, expansion, regimes, scale, freeze.

### 2026-09-30 — Phase 2: five implementation lanes + one-command verifier (commit `230e7d5`)
- Five lanes implemented on disjoint files per the ownership map (`substrate/types.py` split: Lane A owns only `SupportAtom`, Lane C only `EvidenceDecision`; no worker edited another worker's rows). Plus a separate one-command verifier role.
- BLOCKER 1 evidence granularity: derived support index + ancestry-aware support; a parent containing a required leaf satisfies SUPPORT while being separately penalized on context precision and token cost; support and precision never conflated; ancestry expansion never enters a precision input; frozen `CorpusNode` schema untouched.
- BLOCKER 2 per-stage scores: per-stage `score_kind` / `threshold_policy` / model identity; `model_probability` promoted to a first-class kind with its own interpretation; probability thresholds on logits still fail; legacy migration is an explicit, tested, recorded transform that refuses to invent a model identity.
- BLOCKER 3–5 QA semantics: same-split cross-group chains allowed; structural validation of semantic-audit provenance and hop glosses; code validates structure only and never auto-decides sufficiency, minimality, or answerability.
- BLOCKER 6–7 regimes and custody: Regime A / Regime B derived without modifying the pinned split map; cross-regime aggregation refused; append-only custody audit carrying seal hashes; leakage check returns PASS/REJECT with non-revealing statistics only.
- BLOCKER 8 abstention: first-class `EvidenceDecision` with the fail-closed sufficient/insufficient iff generate/abstain invariant; a shared `run_question` gate that provably never invokes the generator on abstain; a zero-span safe floor; `zero-spans` vs `over-budget-empty` kept distinct so a packing failure is never misread as a retrieval decision.
- BLOCKER 10 storage honesty: a missing required artifact no longer contributes zero; `total_bytes` is `None` when incomplete and `known_bytes` carries only what was measured. The test that *enshrined* the bug was changed, not deleted — `test_measure_storage_missing_path_is_zero` → `test_measure_storage_missing_path_is_not_a_valid_total`, with a second test for partial-vs-complete. The bug-catching test changed with the fix, by ruling.
- BLOCKER 11 memory: point RSS (`VmRSS`) and peak/high-water RSS (`VmHWM`) are distinct readings with distinct sources; the `ru_maxrss` >1e9 magnitude heuristic replaced by explicit `sys.platform` dispatch (linux KiB / darwin bytes / unknown → `None`, fail closed rather than guess).
- BLOCKER 13 verifier: `scripts/verify_round0` (9 stages, 3 modes, exit 0/1/2) + `.github/workflows/verify-round0.yml` that downloads nothing. `--help` is handled before root resolution and before any subprocess spawn, because a `--help` that ran the whole suite had already broken this project twice. Sealed labels are only ever hashed with `verify_seal_opaque`, never opened for content. A skip is reported as a skip, never as a pass.
- **Real defect found by the verifier worker outside its own ownership:** the regime block in `substrate/manifest.py` raised `cannot access local variable 'groups_raw' where it is not associated with a value` (regime-B non-empty branch and again on the regime-B empty branch). The verifier recorded it rather than patching another worker's file; the orchestrator independently confirmed and fixed it. Failure preserved, not erased.
- **Three upstream worker failures this repair run (orchestrator-reported):** one 504 upstream idle timeout, one 503, one 502, each killing a worker with no deliverable. Policy applied: retry, then substitute to another explicitly free endpoint, record, continue. No paid fallback. No repository artifact records session ids or endpoints for these, so they are recorded here as orchestrator-reported and are not independently verifiable from the tree.
- **Abandoned check (orchestrator-reported):** a check intended to demonstrate the one-group → same-split relaxation was started and abandoned with no verdict. It is recorded as abandoned — not as a pass and not as a failure of the relaxation. The relaxation was instead verified by executed probes in Phase 3.
- Commit message state at `230e7d5`: "321 shared + 77 data-tools + 17 corpus tests pass. QA still 70/70 approved. NOT FROZEN: questions.json, sealed labels, and the regime-B artifact are still missing."

### 2026-09-30 — Phase 3: three independent adversarial reviews, all PASS (commit `3e82aa2`)
- Three reviewers, none of whom wrote the code under review, executed probes rather than reading code. Each is a scoped component verdict, **not** a freeze and **not** a semantic QA verdict.
- **Evidence semantics** (`docs/round0-review-evidence-semantics.md`): 8 attacks, all PASS. Sibling false positives blocked (an unrelated node containing the atom substring gets no credit, because the leaf-set gate fires first); true ancestors satisfy support by design but are always flagged `imprecise` and lose strictly on both precision and tokens; dual-metric gaming (`[leaf, parent]`) is dominated — support stays 1.0 while precision drops and token cost rises, so no system can claim exactness and support from one retrieval; ancestry-expanded ids are never fed into a precision input; the index fails closed on every corruption tried (missing child text, non-whitespace gap, out-of-order children, duplicate ids, parent cycles, self-parent, trailing text); and a diff against `b38a457` confirmed the pre-existing recall/MRR/nDCG/conditional-retention bodies are untouched — the only removed line in the whole diff *extends* validation.
- **Trace / storage / freeze** (`docs/round0-review-trace-storage-freeze.md`): all PASS. Fail-closed storage in both `measure_storage` and `storage_manifest`; `complete=false` paired with an integer `total_bytes` is impossible; all 7 freeze corruptions (code hash, corpus hash, generator config, questions SHA, sealed-labels SHA, runtime binary, split map) each produce an explicit gap and never a pass; the `groups_raw` `UnboundLocalError` regression is fixed on *both* branches and was probed on both; every threshold-domain violation is caught; legacy migration refuses to invent a model identity; the verifier exits non-zero, cannot be read as a freeze pass from `--code-only`, and never silently fails a stage.
- **Abstention / split / custody / memory** (`docs/round0-review-abstention-split-custody.md`): all PASS. The generator is provably not invoked on abstain (0 calls against a counting mock); `zero-spans` vs `over-budget-empty` holds; unlabeled rates are `None`, never an invented `0.0`; relaxing the one-group rule did **not** weaken cross-split leakage prevention (train→train multi-group ALLOWED; train→heldout, train→dev, dev→heldout, declared-split mismatch, empty `source_articles` all REJECT; the retriever projection returns exactly `{question_id, text}` and raises on any extra key); semantic auto-approval is impossible; the leakage check emits no held-out id, text, or answer.
- Two non-blocking advisories recorded, not blockers: a minimum-dev-sample guard for leakage-check calibration (a degenerate n=2 dev sample calibrates threshold 0.0 and flags everything), and custody audit-log question-id hygiene.

### 2026-09-30 — Phase 4: semantic audit of all 70 drafts, 11 repaired (commit `9756649`)
- Protocol `docs/qa-semantic-audit-protocol.md` executed for the first time. Two independent second readers over **all 70** approved drafts, against live corpus text fetched by `node_id`: pass 1 covered the 17 multihop + comparison drafts plus explicit audits of `qa-train-42` and `qa-pilot-dev-05`; pass 2 covered the 53 factoid + unanswerable + ambiguous. Absence claims for unanswerable items were tested corpus-wide, not by sampling. Parser: `scripts/parse_semantic_audit.py`.
- Outcome: **59 approve unchanged, 11 repaired, 0 rejected.** No draft was deleted; every defect was repairable in place. Adjudication ledger: `docs/qa-semantic-audit-ledger.md`.
- **Largest finding: only 2 of 10 multi-hop labels were genuine** (`qa-train-05` Jobs→Pixar→Apple; `qa-train-32` cross-article Guido→Monty Python). The other 8 pre-stated the bridging premise, so a single support atom already determined the answer — the label had degenerated into "quoted more than one passage", exactly the failure mode BLOCKER 4 names. Relabelled to factoid with `is_multi_hop` dropped and `reference_hop_chains` cleared, not quietly retained.
- 3 `repair-minimality` / 2 combined: `qa-train-42`'s hermit-crab atom is a verbatim restatement of the question's own first clause and the conchology atom alone names the answer; `qa-train-21` kept only `p:mars_bar:01:000`. 3 `repair-alternatives`: `qa-train-28` gained `{t:k2:03:000:00}` — the SENTENCE atom, deliberately not the parent `p:k2:03:000` whose continuation cites a conflicting 8609.02 m figure; `qa-pilot-dev-09` gained the gorilla and chimpanzee community paragraphs; `qa-train-02` gained the Amazon company lead, with the descendant `t:amazon_company:00:000:01` correctly NOT recorded because a descendant is not a distinct set. Alternatives are encouraged, never collapsed.
- Approval integrity preserved: every repair invalidated its own approval, and an independent reviewer who did NOT make the edits re-verified all 11 against live corpus text with leave-one-out before reissue, binding each fresh approval to the NEW content hash with audit provenance in `provenance.semantic_audit`. All 11 APPROVE. 9 of 11 stored hashes reproduced the reviewer's reported hashes byte-for-byte.
- Two non-blocking findings recorded without a draft change: `qa-train-30`'s `absent_reason` gloss mislabels an AMS study (the absence claim itself is correct); `qa-pilot-dev-05`'s `meta.group=java` with borneo + java sources is VALID under the new same-split rule and both atoms are genuinely necessary — the inconsistency Lane D flagged in Phase 1 was adjudicated as a finding, not papered over.
- Verification (orchestrator rerun, reproduced by the steward this pass): 70 drafts / 70 approved / 0 errors; runtime projection hash unchanged at `f7679798…bee0`, proving retriever-visible input never moved across the repairs; shared 321 and data-tools 77 suites pass.

### 2026-10-01 — Phase 5a: dev expanded 10 → 60, 50 new drafts pending (commit `814dcc1`)
- 50 new controlled dev drafts (`qa-dev-11..60`) authored by an explicitly selected free Muse worker, spread across the 24 previously unused dev groups. Type mix 26 factoid, 14 multihop, 4 comparison, 3 ambiguous, 3 unanswerable. Ambiguous-or-unanswerable 12% (quota ≥10% met); multihop 28% (target ~25% met on paper only — see below).
- **No approvals were fabricated.** All 50 are `decision=pending`, and `validate_qa` reports 50 errors for exactly that reason with zero content or schema errors. The author's machine check against the single-atom answerability test, and its relabelling of single-atom candidates as factoid rather than forcing them into multi-hop, is the right instinct and the exact defect class Phase 4 found — but a machine check by the author is not the two-independent-pass protocol.
- **Reported corpus limitation, recorded rather than papered over:** no genuine same-split cross-group (dev→dev) multi-hop chain exists in this corpus. The 22 single-article dev groups are topically isolated with no real shared-entity chains, and manufacturing one would violate the no-manufactured-hops rule. Cross-article representation is therefore intra-group only.
- **Steward verification of that claim (read-only, 2026-10-01 pass):** for all 16 `is_multi_hop` drafts in `staging/`, the number of distinct split-map groups covered by `meta.source_articles` is exactly 1. Cross-group multi-hop items: 0. Only 2 of the 16 use more than one source article at all. So the 28% multi-hop figure is a label count on single-group items and must not be read as 28% genuine multi-hop.
- Phase 7 scale scaffolding started under the Lane F ruling (separate path, disjoint node-id namespace, one-directional cross-referencing, stopping rule that makes 50k non-blocking, scale must not block the repairs or the freeze): 960 predeclared candidate titles (target 700, seed `scale-v1`, core 297 excluded), `fetch_distractors.py` written and run → **940 fetched / 20 not_found**, 940 raw snapshots on disk, `scale_build.py` written. **The layer is not built**: no tier manifests, no `scale_build_manifest.json`, no `corpus/scale/distractor.jsonl`, and `corpus/scale/tests/` is empty (0 tests). The mechanical de-duplication against the core 297 by pageid / title / content hash has never run, so disjointness is unproven.
- Validation as committed: 120 drafts, 70 approved, 50 errors, shared 321 and data-tools 77 pass. **Independently reproduced by the steward this pass**, together with the projection hashes `runtime_projection_sha256 6adafe9c…c861` and `public_projection_ids_sha256 983ebec9…20c0`. The historical `f7679798…bee0` was the 70-draft projection and is now a stale pin.

### 2026-10-01 — Gate state re-measured by the steward (read-only)
- `python3 -m unittest discover -s tests` → **321 OK**; `data_tools/tests` → **77 OK**; `corpus/tests` → **17 OK**.
- `python3 -m data_tools.validate_qa --staging staging --corpus corpus/corpus.jsonl --split-map corpus/split_map.json` → **exit 1**; drafts 120, approved 70, errors 50; splits dev 60 / train 60 / **heldout 0**; types factoid 76 / multihop 16 / comparison 11 / ambiguous 9 / unanswerable 8.
- `./scripts/verify_round0` → **exit 1**; 5 PASS / 4 FAIL / 0 SKIP. Failing stages: 5 qa-validation, 6 question-label-partition, 8 freeze-manifest (7 gaps), 9 leakage-control-artifacts.
- `./scripts/verify_round0 --code-only` → **exit 1**; 5 PASS / 1 FAIL / 1 SKIP. This is a change from the expectation recorded in `docs/verify-round0.md` §7 and is caused entirely by stage 5 now failing; see §9 of `docs/STATUS.md`.
- Corpus re-verified: 297 articles, 113,951 nodes, 43,876,251 bytes, canonical hash `08aa2c53…089d1` MATCHING provenance, all four `build_manifest` artifact hashes and byte counts verified against disk, 218 groups / 205-44-48.
- The verifier's stage 1 reports 282 tests while the same command reports 321. This is the documented recursion guard, not missing tests: the verifier exports `VERIFY_ROUND0_IN_VERIFIER=1` and `tests/test_verify_round0_entrypoint.py` skips its whole 39-test module when it sees that marker. 321 − 39 = 282.
- Twelve stale or internally inconsistent documentation claims were found and recorded, not edited, because they belong to other roles — including a superseded one-group rule still stated in the `data_tools/derive.py` docstring, the commit `814dcc1` message claiming the fetcher and build script do not exist when it commits both, and `docs/verify-round0.md` §7's now-wrong "code-only expected exit 0". Full table in `docs/STATUS.md` §9.
- **Blocker numbering gap:** the repair agenda's items **9 and 12** are not numbered in any repository artifact. Only 1–8, 10, 11 and 13 are named, in commit `230e7d5` and the three Phase 3 review reports. The orchestrator must supply the text of items 9 and 12 before that row of the blocker table can be closed or retired.

## 2. What was tried → worked / failed (with evidence)

Worked (orchestrator-verified where noted):
- Free-endpoint discipline held: every spawn used an explicit verified zero-cost endpoint, selected rather than inherited; failures were substituted or redistributed (Nemotron Lightning→Muse; 504 retries; rate-limit redistribution across Space Bunny/LongCat/Nemotron Ultra), with no paid fallback at any point (log §§allocation, substitution, worker-timeouts, rate-limits).
- Substrate contract iterated v0.1→v0.3 + provenance gate: reviewer-reproduced bypasses closed and re-verified by probes (v03 review §verification; provenance final review §§acceptance/integration). Orchestrator reruns: 34→88→113→147→175 pass at successive stages (log).
- Generator adapter brought to scoped PASS: 14/14 adversarial (orchestrator-executed), 3/3 fresh-process repeats byte-identical, smoke v3 PASS (v03 review §§runs/sign-off).
- Shared evidence repair (full-serialization cap, prompt v0.2, shared parser) integrated without generator/config edits outside owner scope (repair doc §scope; 113/113).
- QA tooling repaired to 41/41 + 175/175 with fail-closed context, content-bound approval shape, hint-free projection, `seal_records()`, importer pins (repair doc §§1–7; orchestrator reran 41/41).
- Corpus rebuild reproduced deterministically from bytes with matching hashes and hierarchy-clean load (worker §§9–10; orchestrator checkpoint recompute).
- Generator live template cross-check MATCH: `/props` `chat_template` hash equals the pinned config value on a real server process, with clean reaping (template-check §§Result/Provenance). Closes the v03 residual.
- Corpus `pilot-297-r1` accepted after independent quality PASS; orchestrator recomputed all four artifact hashes and recounted the split map independently (quality review §§1–8; log §retry-outcomes).
- QA tooling re-review PASS with 9 focused probes against all 7 repair items; accepted as code validation only, with the stale 247-article residual corrected rather than carried forward (v02 review §§probe-matrix/items; log).
- QA pipeline exercised end to end twice: dev pilot 10/10 and train 60, total 70/70 approved, 0 errors, with an independent second reader actually rejecting content (9 content REJECTs) and the author repairing and re-verifying them (qa-train-verification §§passes 4/6 + both re-verifications; log).
- Fail-closed content-bound approval caught the hash-serialization incident instead of binding stale approvals — the mechanism designed for this class of error worked under adversarial conditions (log §hash-serialization).
- Endpoint discipline held under stress: after three rate-limit failures, work was redistributed across four verified free endpoints with no paid fallback (log §rate-limits).
- Version control initialized and pushed to a private remote, with large artifacts gitignored and hash-pinned on disk rather than committed (log §version-control).
- **Phase 1 design adjudication:** six free lanes produced designs only, and the orchestrator's rulings rejected five tempting shortcuts — char offsets on `CorpusNode`, a fabricated `"legacy-unknown"` model identity, automated minimal-atom selection, collapsed alternatives, bulk re-approval, externally-pinned embedding thresholds, in-place split-map edits. Recorded because the rejections are the substance of the phase, not its bookkeeping (repair plan Lane rulings).
- **Phase 2 five implementation lanes on disjoint files** delivered blockers 1–8, 10, 11 and 13, plus the one-command verifier. The bug-catching test was *changed with the fix* (`test_measure_storage_missing_path_is_zero` → `..._is_not_a_valid_total`) rather than deleted, by explicit ruling (repair plan Lane C; trace/storage review §test-change).
- **Phase 3 three independent adversarial reviews, all PASS**, each by a reviewer who did not write the code under review and each executing probes rather than reading code. Component verdicts only — none is a freeze and none is a semantic QA verdict (the three `docs/round0-review-*.md`).
- **Relaxing the one-group multi-hop rule did not weaken leakage prevention** — demonstrated by executed probes, not assertion: train→train multi-group ALLOWED; train→heldout, train→dev, dev→heldout, declared-split mismatch, and empty `source_articles` all REJECT; the retriever projection returns exactly `{question_id, text}` and raises on any extra key (abstention/split/custody review §4).
- **Phase 4 semantic audit ran on all 70 drafts for the first time**, with the decisive finding that only 2 of 10 multi-hop labels were genuine. The 8 inflated ones were relabelled and their redundant setup atoms dropped, not quietly retained (audit ledger; commit `9756649`).
- **Approval integrity survived the audit:** every repair invalidated its own approval and an independent reviewer who did not make the edits re-verified all 11 against live corpus text with leave-one-out before reissue, each fresh approval bound to the NEW content hash. 9 of 11 stored hashes reproduced the reviewer's reported hashes byte-for-byte (reverify report).
- **Phase 5a dev expansion 10 → 60 with zero fabricated approvals.** All 50 new drafts are `pending`; `validate_qa` reports 50 errors for exactly that reason with zero content or schema errors (commit `814dcc1`; steward reproduced).
- **A corpus limitation was reported rather than papered over:** no genuine same-split cross-group multi-hop chain exists, and manufacturing one would violate the no-manufactured-hops rule. Steward read-only verification: all 16 `is_multi_hop` drafts span exactly 1 split-map group; 0 cross-group items (commit `814dcc1`; STATUS.md §7).
- **Documentation steward pass (2026-10-01):** `docs/STATUS.md` created as the single authoritative status file; this ledger and `docs/orchestration-log.md` updated. Twelve stale or self-contradictory documentation claims were found and **recorded, not edited**, because they belong to other roles. Twelve table rows in STATUS.md §9, not a silent fix.

Failed / rejected (evidence preserved):
- Nemotron reference worker silent failure (no output, no files) → substitution, not completion (log §failure).
- Substrate v0.1, v0.2, v0.3(initial): REPAIR REQUIRED each round with reviewer-reproduced bypasses (reviews §§verdict/probes). Not accepted from test counts.
- Generator v1/v2: REPAIR REQUIRED (config drift, `--help` side effects, citation copying, token mislabeling); old FAIL traces preserved, not overwritten (generator review §§defects/traces; readiness §history).
- Fixed generator does NOT reliably abstain: 7/7 fresh PIDs assert unsupported "0.5" on empty evidence; v3 evidence-bearing output cites descriptively with `cited_valid: []` (v03 review §§runs/observations; empty-evidence analysis §§observation/limits). Recorded as model behavior for upstream gating / generator tournament, not adapter defect.
- Corpus pilot-247-v0 rejected for QA: 13.7% debris, 24 truncations, 23/30 groups incomplete, 310× HTTP 429 (log §gate; pilot §§6–8 superseded record).
- QA tooling qualified PASS not accepted: report file absent + gaps found on inspection (optional provenance bypass, ambiguous semantics unchecked, partition≠approval, evaluator hint leakage, code-point≠semantic) → directed repairs + corrected REPAIR REQUIRED review (log §§qualified-PASS/corrected-artifact).
- Criteria draft sent back: incorrect survival-product math, hard cutoffs, corpus-vs-supervision conflation, permission guidance, restrictive multihop assumptions → resumed to Ultra critic with controlling adjudication (log; criteria §adjudication).
- Two independent reviews first attempt failed with `[504] Upstream idle timeout exceeded` and produced no deliverable (corpus quality `ses_f14271dd…`, QA isolation `ses_f143b2bc…`); one pilot verifier pass also 504'd. Retried once on the same verified free endpoint with tightened/split scope, then completed (log §worker-timeouts, §pilot-verifier-timeout). Timeouts are execution failures, not verdicts.
- Verifier hallucination overturned: pilot Q9 chimpanzee node IDs were asserted missing; direct corpus check showed the draft's IDs exist and the verifier's proposed replacements do not. Reviewer now requires corpus-grounded evidence (log §verifier-rejection-overturned; pilot verification pass 1 §Q9).
- Two more unfounded reviewer claims: T17 nonexistent-node and T17 NBSP-mismatch. Code-point comparison against `p:london_bridge:05:002` refuted both; no draft change made (train verification pass 4 §summary).
- 9 content REJECTs in the train batch: hard-negative answer leakage T31/T37, answer-not-verbatim T35/T50/T52–T55/T60. All repaired by the author and re-verified as APPROVE (train verification passes 4/6 + re-verification sections). Approval was not granted from a clean validator alone.
- Recurring hash-serialization incident: reimplemented hashes in several second-reader passes did not match `data_tools.verify.draft_content_hash`; binding STOPPED (fail-closed) and 4 hashes (T31/35/37/50) required reissue. Root cause: the semantic hash excludes only top-level `provenance`, so `hard_negatives[].reviewed`/`reviewer` markers are hashed — any marker write after hash capture invalidates it (log §hash-serialization §root-cause).
- 55 of 70 approval rationales asserted superseded pre-approval hashes → rewritten to bind approval to the current content hash with findings preserved verbatim; pre-binding byte state is unreconstructible for 5 files and is recorded as a known provenance limitation, not silently repaired (log §audit-trail-correction, §residual-honesty).
- One hard-negative `reviewed` flag bound with the wrong verifier-model attribution (spark instead of ultra) → corrected metadata-only; semantic hash unaffected by design.
- Three subagents hit `Rate limit exceeded` (Muse, Ling, Mimo) mid-batch; work redistributed across Space Bunny, LongCat, and Nemotron Ultra (log §rate-limits).
- Two documentation artifacts carry stale status headers discovered by the steward this pass; recorded under §5 blockers rather than edited, since the steward owns only this ledger.
- **Three upstream worker failures in the 2026-09-30/10-01 repair run** (orchestrator-reported): one **504** upstream idle timeout, one **503**, one **502**; each killed a worker with no deliverable. Retried, then substituted to another explicitly free endpoint, then continued. No paid fallback. No repository artifact records session ids or endpoints, so these are recorded as orchestrator-reported and are not independently verifiable from the tree.
- **Abandoned check in the same run** (orchestrator-reported): a check intended to demonstrate the one-group → same-split relaxation was started and abandoned with no verdict. Recorded as abandoned — **not** as a pass and **not** as a failure of the relaxation, which was separately verified by executed probes in Phase 3.
- **Real defect found by the verifier worker outside its own file scope:** `substrate/manifest.py` regime validation raised `UnboundLocalError` on `groups_raw` on both the regime-B non-empty and empty branches. The worker recorded it instead of patching another worker's file; the orchestrator confirmed and fixed it; Phase 3 then probed both branches.
- **The multi-hop label class was defective, not just incomplete:** 8 of 10 pre-existing multi-hop labels were inflated — the question pre-stated the bridging premise, so a single atom already determined the answer. Relabelled and their redundant setup atoms dropped rather than quietly retained. The same defect class is what the 50 new dev drafts were machine-checked against; they are not independently verified.
- **A corpus limitation that cannot be repaired by authoring:** no genuine same-split cross-group multi-hop chain exists in this corpus. Steward read-only verification: all 16 `is_multi_hop` drafts span exactly 1 split-map group; 0 cross-group items. Reported rather than papered over; manufacturing a hop would violate the no-manufactured-hops rule.
- **The scale layer is unbuilt.** 960 candidates declared and 940 fetched, but no tier manifests, no built DAG, and 0 tests; the de-duplication against the core 297 has never run, so disjointness is unproven.
- **Twelve stale or self-contradictory documentation claims** found in the 2026-10-01 steward pass, including the superseded one-group rule still stated in a source docstring and a commit message that contradicts its own contents. Recorded in `docs/STATUS.md` §9 and §5, not edited, because they belong to other roles.

## 3. Key orchestrator decisions and why

- Bounded 247-article pilot over more fetching: 33 GB free disk made 21 GB wiki.db infeasible; boar pattern favored small local corpus (log §reference/audit; audit §7).
- Threads=1 for fixed Round 1 generator: cross-process variance at `-t 6` vs identical at `-t 1` in synthetic probes; reproducibility over ~28→~11 tok/s decode (readiness §0/§0b; log §integration).
- Prompt v0.2 + shared parser + strict full-serialization cap: per-span summation + first-span overflow + literal `[node_id]` emission observed; fixed as pre-freeze interface repair, not benchmark tuning (log §§integration/empty-diagnostic; evidence repair §§1–3).
- Hallucinated citations permitted as recorded failures (not trace rejection); completion binary with separate fractional diagnostic; `model_probability` as evaluable-uncalibrated state; Round 0 records declarations not learned fits: avoid selection bias, naming confusion, and demanding architecture thresholds pre-teams (v03 repair §2; log §v02-disposition).
- Mandatory nonempty source provenance + `public_reference` dev-only + UNKNOWN-not-zero: v0.3 optional-metadata skip contradicted article-generalization; controlled QA without sources bypassed group validation (log §v0.3-disposition; provenance repair §§verdict/scope).
- Offline-only rebuild from 297 raws, archive v0, no further network: v0 debris/truncation/group-breakage confounded evidence work; 50 extra raws already on disk made rebuild possible without new fetching (log §quality-gate; pilot §§0/9).
- Feasibility survey allowed as shared metadata-only work; no weights/architecture/divergence: unblocks Round 1 design info without breaking freeze sequencing (log §repair-verification).
- No Android claims from desktop; no second-machine / cache-cold mandates; no fixed survival %: desktop numbers are proxies; poor survival is valid negative result (criteria adjudication; contract §§6–7; log §adjudication).
- Accept `pilot-297-r1` despite the corpus review's §6 arithmetic blemish: the load-bearing checks (107/107 confusable-article membership, no group split across splits) are consistent with worker claims and orchestrator counts, and the disagreement is confined to a non-load-bearing display inconsistency. Recorded rather than silently fixed.
- Accept the QA tooling PASS as **code validation only**: it verifies procedure, not semantics. The review's stale "247 vs 500 articles" residual is corrected against the 297-article rebuild rather than propagated, and entailment / true-unanswerability verification stays on the open list.
- Overturn the Q9 and T17 reviewer claims rather than editing correct drafts to satisfy an incorrect reviewer: an independent reader is a check, not an authority. Consequence recorded as a standing rule — reviewer claims require corpus-grounded evidence, and the orchestrator spot-checks them before tasking repairs.
- Enforce markers-before-hash binding order (`hard_negatives` review markers written, then hash computed and stored). A stopped bind is the correct outcome when hashes disagree; the alternative — binding anyway — would have silently sealed unverifiable approvals.
- Rewrite 55 approval rationales to bind approval to the current content hash, preserving all substantive findings verbatim and leaving the 15 hash-free rationales byte-identical. This corrects the audit trail going forward; it does not retroactively make the superseded hash claims true, and the unreconstructible pre-binding state for 5 files is recorded as a limitation.
- Private GitHub remote with large artifacts gitignored and hash-pinned on disk rather than committed: git supplies history for code and review artifacts; manifest hashes remain the source of truth for the 986 MB weights and 42 MB corpus. A missing artifact therefore blocks freeze regardless of git state.
- Do not promote 70 approved drafts toward a freeze: the dev remainder (20) and the held-out batch (30) are unsealed, `corpus/questions.json` does not exist, and no `validate_freeze` has run on a real manifest. Freeze remains blocked on artifacts, not on throughput.
- Audit on paragraph spans first, atomize second (Phase 1 cross-lane ruling): Lane A rejects `p:` atoms in sealed sufficient sets, but migrating the existing 70 drafts before knowing which atoms are actually necessary would have been expensive work in the wrong order.
- Keep the one-group relaxation *scoped* — `substrate/splits.py` stays the authoritative gate and only `data_tools/verify.py`'s stricter duplicate check was relaxed to a same-split check. Leakage prevention must not weaken, and Phase 3 probed that it did not.
- Run the two-independent-pass audit with orchestrator adjudication by direct corpus inspection for any questionable item, never by re-running a heuristic and never by majority vote of model outputs (repair plan Lane D ruling).
- Fabricate no approvals for the 50 new dev drafts. A pending draft is an honest state; a fabricated approval is the failure class the whole content-hash machinery exists to prevent.
- Report the no-cross-group-multi-hop corpus limitation instead of manufacturing hops to hit the 28% figure.
- Do not let the scale layer block the semantic repairs or the freeze (Lane F ruling), and do not record the 940 fetched titles as a built distractor corpus — the de-duplication against the core 297 has never run.
- Make `docs/STATUS.md` the single authoritative status file, and record stale neighbor claims rather than editing files the steward does not own.

## 4. Current gate state

**NOT FROZEN.** No architecture implementations, held-out runs, or tournament conclusions authorized.

Provenance/code gate: substrate code PASS on provenance scope (final review §§verdict/integration); v0.3 P0 bypasses closed (v03 review §verification); generator adapter PASS on captured v3 snapshot, now including the live `/props` template cross-check (v03 generator review §sign-off; template-check §Result). These are scoped passes, not a Round 0 freeze.

Corpus gate: **closed.** `pilot-297-r1` (297 articles, 113,951 nodes, canonical hash `08aa2c53…089d1`, file SHA-256 `98e1237e…d5f64`, splits 205/44/48) accepted after independent quality PASS and orchestrator hash recomputation, with the §6 arithmetic blemish recorded (quality review §§1–8; log §retry-outcomes).

QA tooling gate: **closed for code validation only** — v02 re-review PASS on all 7 repair items, and the Phase 2/3 repair round added the semantic-audit structural validation, the same-split relaxation, and the semantic-automation prohibition (321 + 77 + 17 tests; the three Phase 3 reviews). Semantic entailment, true unanswerability, and genuine ambiguity remain unverified by design of the tooling.

Repair-round component gates: **closed on executed probes, in three scoped areas** — evidence semantics, trace/storage/freeze/threshold/verifier, and abstention/split/custody/memory (the three `docs/round0-review-*.md`, all PASS). Each is a *component* verdict. None is a freeze, and none certifies a semantic QA label.

QA content gate: **open.** 120 drafts exist (train 60 / dev 60, **held-out 0**); 70 approved, **50 pending independent review**. Unsealed and unpublished as a release artifact; `staging/` drafts are working files, not a frozen question set.

Freeze still requires (per contract §9, final-review §status, log checkpoint, and the 2026-10-01 `verify_round0` run):
1. `corpus/questions.json` — absent. 120 drafts exist in `staging/`, but no frozen question set has been produced from them.
2. `corpus/heldout_labels.sealed.json` and the recorded `sealed_labels_sha256` — absent. The held-out batch has not been authored at all (0 of a 120-item target).
3. `corpus/regime_b_excluded_articles.json` — absent while regime B has 5 non-empty groups. This alone fails verifier stage 9.
4. `thresholds` non-empty (calibration policy recorded) and regime-group coverage recorded — 7 `validate_freeze` gaps open.
5. The 50 new dev drafts independently verified and approved under the two-pass protocol.
6. Final freeze review of the complete substrate + corpus + question set + sealed labels, by a reviewer who did not build it.
7. Procedural custodian separation acknowledged as a limitation (same OS user; true isolation = the orchestrator withholds the sealed file).
8. Contracted volume/quotas reconciled against the *approved* set: 70 of 240 drafted and approved, 50 pending, 0 held-out; type mix at 120 drafts is 76 factoid / 16 multihop / 11 comparison / 9 ambiguous / 8 unanswerable. Note that the revised controlled total is 240 (60/60/120), superseding the earlier 120 (qa-gate-decisions §2).

## 5. Outstanding blockers

- **The 50 new dev drafts are not independently verified.** Largest open risk. Author machine-check only; no second reader, no leave-one-out adjudication, no `provenance.semantic_audit` record, no approval. They cannot count toward the 60/60/120 target.
- **Held-out batch: 0 of 120 authored.** All 30 held-out groups (27 single-article) are unexercised. Sealing must follow authoring under the dual gate. Held-out labels must never reach dev workers.
- **The scale layer is incomplete.** `corpus/scale/` has 960 predeclared candidates and 940 fetched raw snapshots, but no tier manifests, no `scale_build_manifest.json`, no `distractor.jsonl`, and `corpus/scale/tests/` is empty. The de-duplication against the core 297 has never run, so disjointness is unproven. Scale must not block the repairs or the freeze (Lane F ruling).
- **No genuine cross-group multi-hop exists in this corpus.** Steward read-only verification: all 16 `is_multi_hop` drafts span exactly 1 split-map group; 0 cross-group items. The 28% multi-hop figure is a label count on single-group items. Results under-represent cross-group multi-hop difficulty and that must be stated with any multi-hop claim.
- `validate_freeze` on a real manifest, plus the final freeze review — owner: orchestrator with an independent free reviewer.
- Semantic annotation review: entailment of answers, true corpus absence for unanswerable items, genuine ambiguity for ambiguous items. Code checks prove quotation-exactness only (v02 review §residual 4; protocol §9).
- Generator residuals: `tokenizer_id` config gap (generator-owner repair), empty-packet accounting adversarial path, single-fixture/seed generality; plus the fixed generator's non-abstention recorded as a Round 1 gating concern, not an adapter defect (qa-gate-decisions §6; v03 generator review §§gaps; empty-evidence analysis).
- Documented limitations to carry into any multi-hop claim: 775/1,748 (44.3%) article-level cross-split links mean confusable-group chaining is excluded from the controlled set; 191 of 218 groups (142 train / 22 dev / 27 heldout) are single-article, so `entity_confusion` negatives are rarely emitted and the hard-negative stratum-coverage claim is overbroad; corpus removals (infoboxes from 206 articles, wikitables wholesale, `{{chem}}` unrescued, no intra-parent offsets); corpus is an offline rebuild with no further acquisition, so absence claims are scoped to this snapshot (qa-gate-decisions §3; v02 review §residual 6; corpus-pilot §§9–11).
- Two open non-blocking advisories from Phase 3, to close before the freeze checklist: a minimum-dev-sample guard for leakage-check calibration, and custody audit-log question-id hygiene.
- **Repair-agenda blocker numbers 9 and 12 are not recorded anywhere in the repository.** The orchestrator must supply their text before the blocker table can be closed. See `docs/STATUS.md` §2.
- Stale artifact risk, expanded: prior "freeze status" lists, the pre-amendment corpus provenance value, the 247-article v0 hashes, the superseded pre-approval hash claims in 55 now-rewritten rationales, and **the hint-free runtime projection `f7679798…bee0`, which was the 70-draft projection and is now stale** — at 120 drafts the projection is `6adafe9c…c861`. Current candidate pins: corpus canonical `08aa2c53…089d1` / file `98e1237e…d5f64`, prompt `d8580509…`, model sha `1adf0b11…6c3370`, template `55b2f4a26…8674a`, runtime projection `6adafe9c…c861` — all still pending freeze.
- Stale headers in neighboring artifacts (recorded by the steward, not owned, not edited): `docs/qa-gate-decisions.md` and `docs/qa-construction-protocol.md` still declare that no controlled questions exist, and both still describe the corpus quality review as pending. `docs/qa-semantic-audit-protocol.md` still says "NOT EXECUTED". `docs/verify-round0.md` §7 still says `--code-only` should exit 0. The superseded one-group rule is still stated in the `data_tools/derive.py` docstring. Twelve rows total in `docs/STATUS.md` §9. The underlying facts (no `questions.json`, no sealed file) remain true.

## 6. Measured vs estimates vs hypotheses

- MEASURED (steward, read-only rerun 2026-10-01 pass): `tests` **321 OK**, `data_tools/tests` **77 OK**, `corpus/tests` **17 OK**; `validate_qa` → **exit 1**, `drafts 120, approved 70, errors 50`; splits dev 60 / train 60 / **heldout 0**; types 76 factoid / 16 multihop / 11 comparison / 9 ambiguous / 8 unanswerable; `runtime_projection_sha256 6adafe9c…c861`; `public_projection_ids_sha256 983ebec9…20c0`; `./scripts/verify_round0` → **exit 1** (5 PASS / 4 FAIL / 0 SKIP) with `validate_freeze` returning 7 gaps; `./scripts/verify_round0 --code-only` → **exit 1** (5 PASS / 1 FAIL / 1 SKIP); corpus 297 articles / 113,951 nodes / 43,876,251 B / canonical hash `08aa2c53…089d1` MATCHING provenance / all four `build_manifest` hashes verified / 218 groups / 205-44-48; node kinds article 297, cluster 9, corpus 1, paragraph 9,979, section 8,146, sentence 95,519; groups per split 158/28/32 with single-article groups 142/22/27; all 16 `is_multi_hop` drafts span exactly 1 split-map group (0 cross-group); 960 scale fetch attempts → 940 fetched / 20 not_found, 940 raw snapshots on disk, 0 tier manifests, 0 scale tests; `corpus/questions.json`, `corpus/regime_b_excluded_articles.json` and every `*sealed.json` confirmed absent. This reproduces the orchestrator's recorded results; it is **not** an independent semantic verification.
- MEASURED (orchestrator reran, in earlier sessions): tests 34, 88, 113, 147, 175, then 321 shared + 77 data-tools + 17 corpus; converter 17/17; corpus load 113,951 nodes / 0 hierarchy errors; corpus hash recompute match; manifest byte/SHA match for all four rebuilt artifacts; generator adversarial 14/14; model sha match; pilot validate_qa 10/10 and train validate_qa 70/70 with 0 errors; direct corpus check refuting the Q9 verifier claim; independent recompute of draft hashes (`f7679798…bee0` unchanged across the rationale rewrite and across the Phase 4 repairs).
- MEASURED (worker-reported, reviewer-executed, not orchestrator- or steward-rerun): the live `/props` template hash `55b2f4a26…8674a` and server-binary hash match with clean reaping; all three Phase 3 adversarial review probe sets (8 evidence-semantics attacks, 7 corruption + 9 threshold + 4 storage probes, 8 abstention/split/custody/memory attack lines); **every Phase 4 semantic verdict** (59 approve / 11 repaired) and the independent re-verification of all 11 repairs, including the 9-of-11 hash reproduction; the semantic verdicts for 70 drafts from 2026-09-29 and both re-verification rounds; token ratio ~1.49× whitespace on one fixture; load/prompt/decode timings on i7-8700 (process-cold, page-cache uncontrolled); debris re-scan 3/9,979 (LaTeX FPs) and 0/30 in the quality-review sample; removal counts (26,784 templates, 6,854 rescues, etc.); link counts (1,748 total, 775 cross-split).
- ORCHESTRATOR-REPORTED ONLY (not verifiable from the repository): the three upstream worker failures this repair run (one 504 upstream idle timeout, one 503, one 502, each with no deliverable) and the abandoned one-group-rule relaxation check. Recorded as failures/abandonment, never as passes. No session ids or endpoints exist in the tree for them.
- ESTIMATES / PROXIES (not mobile claims): all latency/RAM/disk figures are desktop-CPU proxies; server RSS ~1.4–1.6 GB, client ~28 MB; the template-check load time is a fresh-process wall time with uncontrolled page cache; page-cache effects reported as observed/unknown; no cache-cold or Android measurement. **No Android, ARM, or on-device number exists anywhere in this project.**
- HYPOTHESES (untested): tiny-Ettin sufficiency, KaLM compression retention, heads-vs-LoRA, GLiNER/Laya utility, adaptive breadth, multihop frequency — all Round 1 questions, none decided. Feasibility doc statuses are VERIFIED_EXISTS / ADVERTISED_NOT_VERIFIED, never EXPERIMENTALLY_VERIFIED. **QA approval counts (70/70, or 321 tests) say nothing about whether these drafts measure retrieval or architecture quality.** Test counts are infrastructure signal only.
- INTERPRETATIONS (labeled, not measurements): the Q9 and T17 rejections read as reviewer hallucination rather than draft defects, on the strength of direct corpus checks; "fail-closed design worked as intended" is a judgement about the binding mechanism, evidenced only by the stopped bind and the subsequent reissue; the corpus review §6 arithmetic is read as a non-load-bearing display defect because the membership checks hold; the Phase 4 "8 of 10 multi-hop labels were inflated" finding is a reviewer judgment applied to 10 items and ratified by re-approval, not a machine-checked property of the corpus.

## 7. Attribution log (worker claims preserved)

- Substrate leads/repairs: Muse Spark Free — contract v0.3, evidence-token repair, v0.3 repair, provenance-gate repair; test claims 34/88/113/147/175 at respective stages.
- Reference audit: Muse Spark Free (replacement) — pins, eval/corpus/generator analysis, §7 recommendations.
- Corpus: Muse Spark Free — pilot-247-v0 then pilot-297-r1 rebuild, §§9–11 measurements.
- Generator: Muse Spark Free — artifact pin, adapter v1→v3, smoke/adversarial/repeat/empty-probe traces, readiness report.
- Dataset/QA tooling: Muse Spark Free — `data_tools/`, protocol, 7-item repair, 41-test claim.
- Model feasibility: explicit free Muse researcher — Hub metadata survey, catalog JSON.
- Independent reviews: Nemotron 3 Ultra Free — substrate v0.1/v0.2/v0.3, generator v1/v03, QA tooling corrected review, provenance final review. No review is a freeze.
- Corpus quality review r1 and QA tooling re-review v02: Nemotron 3 Ultra Free, after first attempts failed on 504 upstream idle timeouts.
- QA pilot/train second-reader verification: Nemotron 3 Ultra Free, in six passes of 10 plus two re-verification passes; QA author and bind steps ran on other verified free endpoints after rate limits.
- Generator live template check: Muse Spark Free — `scripts/generator_template_check.py`, trace, `docs/generator-template-check.md`.
- **Round 0 repair, Phase 1 design lanes:** Muse Spark Free — Lane A evidence semantics/support atoms, Lane C abstention/storage/memory, Lane D QA semantic audit/minimality/genuine multi-hop/same-split, Lane F distractor-scale corpus. Nemotron 3 Ultra Free — Lane B per-stage score kinds, Lane E regimes/custody/expansion. Design only; no implementation.
- **Round 0 repair, Phase 2 implementation lanes:** five owners on disjoint files per the Phase 1 ownership map, plus a separate one-command verifier role. Free endpoints explicitly selected per lane; `substrate/types.py` was split so no worker edited another worker's rows.
- **Round 0 repair, Phase 3 adversarial reviews:** three independent reviewers, none of whom wrote the code they reviewed, all PASS — evidence semantics, trace/storage/freeze/threshold/verifier, abstention/split/custody/memory. Component verdicts only; none is a freeze and none certifies a semantic QA label.
- **Round 0 repair, Phase 4 semantic audit:** audit pass 1 (17 multihop + comparison) by Nemotron 3 Ultra Free; audit pass 2 (53 factoid + unanswerable + ambiguous) by `opencode/muse-spark-1.3-contributor-free`; independent re-verification of all 11 repairs by Nemotron 3 Ultra Free, which did not author the repairs. Orchestrator adjudicated. Verdicts are reviewer-asserted and evidence-cited; **no third party has re-executed the leave-one-out judgments.**
- **Round 0 repair, Phase 5a dev expansion:** 50 new dev drafts authored by an explicitly selected free Muse worker, machine-checked against the single-atom answerability test, **zero approvals fabricated**. Not independently verified.
- **Round 0 repair, Phase 7 scale:** free Muse worker — predeclared candidate list, `fetch_distractors.py`, `scale_build.py`, fetch log. Layer not built.
- Documentation steward: Muse Spark Free (initial ledger and earlier updates), `opencode/space-bunny-free` (2026-09-29 pass, and the 2026-10-01 pass that created `docs/STATUS.md` and updated this ledger plus `docs/orchestration-log.md`) — read-only reruns, no source/test/data file edited.
- Endpoint failures recorded: Nemotron 3.5 Lightning Free silent non-response; `[504] Upstream idle timeout exceeded` ×3 (two reviews + one pilot pass); `Rate limit exceeded` on Muse, Ling, and Mimo, triggering redistribution across Space Bunny, LongCat, and Nemotron Ultra free endpoints. **Plus, in the 2026-09-30/10-01 repair run, one 504, one 503 and one 502 upstream failure and one abandoned check — orchestrator-reported, with no repository artifact recording session ids or endpoints.** No paid fallback at any point in this project; no endpoint inherited rather than explicitly selected; nested spawning disabled throughout.
- Repository: private GitHub remote `davidghatley/local-mobile-research`, commits `4d924c5` → `b38a457` → `230e7d5` → `3e82aa2` → `9756649` → `814dcc1` (HEAD); large artifacts gitignored and hash-pinned on disk.

---

## 8. Round 0 benchmark-boundary repair run (2026-10-01 → 2026-10-02)

Continuation of the ledger above. The externally reviewed HEAD at the start of
this run was `f819d9b`, which matched the working tree; no newer legitimate work
was reset.

### 8.1 What this run changed

| Phase | Commit | Substance |
|---|---|---|
| 1 reclassify exposed held-out | `937b3c5` | 89 `qa-heldout-*` → `qa-shadow-dev-*` via `git mv`; `SPLITS=(train,dev,shadow_dev,private_test)`; 6 tripwire tests |
| 2 semantic audit | `182b583` | 89 items audited in 3 batches; conjunctive singletons merged (45,46,48,61,63,84,…); inflated multihop relabelled (24,49,53,64,67) |
| 3 paired regimes | `e62de3e` | `split_map` `heldout`→`shadow_dev`; Regime B became a paired condition over the same 56 questions; 13 paired tests |
| 4 scale semantics | `908dcaa` | classification 815/15/110/0; `PROVENANCE-CORRECTION.md`; scale provenance re-pinned by regeneration |
| 5 private-eval custody | `9253655` | out-of-repo private dir; `substrate/private_eval.py`; 9 tripwire tests |
| 6–7 private test + gate | `49047f9` | 116 private items authored/reviewed/sealed; shadow-dev re-approved 89/89; full verifier 10/10 |
| 8 freeze review + repairs | see §8.5, §8.7 | 7 review repairs; 3 items rejected (2 shadow_dev, 1 dev); 2 functional regressions fixed; public-partition answer/location leak closed |

### 8.2 Measured (orchestrator rerun, this run)

- `tests` 343 OK → 372 OK after the freeze-review repairs → 389 OK after the
  pre-stated-premise sweep and the public-partition leak fix → 401 OK after
  review v3 → **411 OK** after the census pin
- `data_tools/tests` 77 OK; `corpus/tests` 17 OK; `corpus/scale/tests` 38 OK
- `validate_qa`: 311 → 91 → **0 errors**; 209 drafts, **206 approved**
  (60 train, 59 dev, 87 shadow_dev) — 3 rejected and quarantined
- partition census: 209 authored = 206 published + 3 rejected, pinned in
  `corpus/partition_census.json` and enforced by stages 5, 6 and 8
- `./scripts/verify_round0 --code-only` → exit 0, 8/8
- `./scripts/verify_round0` → exit 0, **10/10**
- core corpus 297 articles / 113,951 nodes; corpus hash `08aa2c53…089d1` unchanged
- scale tier 940 articles / 300,041 nodes; classification 815 background /
  15 confusable / 110 redirect_stub / 0 unknown
- private test: 116 items — factoid 59, multihop 19, comparison 15,
  unanswerable 12, ambiguous 11; 19.8% ambiguous+unanswerable; 62 distinct
  groups; 15 paired Regime B items over 13 excluded articles
- private seal `c6e1e98d843eaf1eb962a9ec2f89026af2d532f9b963c5d0a78d45056293c54c`

### 8.3 Reviewer-reported (not orchestrator-rerun)

- Phase 2 batch verdicts and the 89/89 re-approval verdicts
- the 64 private-test repairs, 3 rejections, 1 duplicate removal
- private-item absence claims (corpus-wide scans) for the 10 unanswerable items
- `corpus/scale/tests` full 38-test run

### 8.4 ORCHESTRATOR-REPORTED ONLY (no repository artifact)

Upstream endpoint failures this run, all with a recorded substitution and **no
paid fallback**: `nemotron-3.5-lightning-free` garbled output (private author
batch B, 0 files written); `gemma-4-31b-it:free` provider error ×3 (private
review 35–67, private review 105–120, independent freeze review); one rate
limit on `longcat-2.5-preview-free`. No session ids or endpoints are recorded in
the tree for these.

### 8.5 Independent freeze review and its repairs

A fresh reviewer (`openrouter/qwen/qwen3.8-27b:free`, substituted after the
gemma failure) returned **REPAIR REQUIRED**, not PASS. Its load-bearing findings
and what was done:

| Finding | Resolution |
|---|---|
| `qa-shadow-dev-84` and `-86` pre-stated the years they compared, so the questions were answerable without evidence | Both **rejected**, moved to `staging/rejected/`, documented in `staging/rejected/README.md` and `docs/qa-shadow-dev-84-86-repair-ledger.md`. Shadow-dev is honestly **87**, not 89. |
| `data_tools/derive.py` rejected all 32 `shadow_dev` groups after the split-map migration (functional regression, untested) | `group_articles` accepts `shadow_dev`; 9 regression tests in `tests/test_group_split_vocabulary.py` |
| stage 10 printed "MATCHES" when the manifest recorded no hash (vacuous pass) | stage 10 fails closed on an absent digest; 8 tests in `tests/test_private_eval_custody_failclosed.py` |
| `eval/scale_adjudication.py` documented but absent | created, with 12 tests; the title→slug collision between `ABBA` and `Abba` was found and fixed by resolving titles through the tier manifest's authoritative node ids |
| `docs/verify-round0.md` §4/§7 and the verifier header/--help said "stages 1-5, 7, 9" and "exit 1" | updated; a 10-stage table is in the script header |
| ledger ended at `814dcc1`; `docs/STATUS.md` uncommitted | this section and §8.1 added; `docs/STATUS.md` committed |

The reviewer also recorded an endpoint overlap: the batch-c private author and
the 68–100 private reviewer share `qwen3.8-27b:free`. They are distinct workers
and verdicts were independent, but the independence is weaker than a
cross-provider split and is recorded rather than glossed.

### 8.6 What remains unproven after this run

- Semantic QA correctness. Every approval is review-provenance. The freeze
  reviewer's own verdict was REPAIR REQUIRED, so the freeze gate is **not yet
  satisfied** and no freeze tag exists.
- The leakage gate's hash-only comparison is not bound to the seal. It refuses
  to issue PASS, which is correct, but a real sealed comparison is still needed
  before Round 1 teams can get a meaningful verdict.
- 6 ambiguous shadow-dev items put a prose disjunction in `answer_text`; any
  scorer comparing `answer_text` to model output scores all six wrong. Needs an
  orchestrator decision.
- Calibration thresholds are declared, not fitted.
- Nothing here is an Android or on-device measurement, and none may be claimed.

### 8.7 Second freeze review and the pre-stated-premise sweep

A second fresh reviewer (`opencode/nemotron-3-ultra-free`) confirmed all seven
findings from the first review were closed, then did something the first did
not: it swept the **whole** approved set instead of sampling. That found
`qa-dev-24` — a **dev**-split comparison question stating both compared
magnitudes, so its single atom was unnecessary. Verdict: REPAIR REQUIRED.

A dedicated sweep then adjudicated all 22 machine-flagged candidates plus a
manual sweep of every approved item (`docs/qa-prestated-premise-sweep.md`):

- 22 candidates: **all sound**. A year appearing in both question and evidence
  is normal context, not a defect. Over-rejection was explicitly avoided.
- `qa-dev-24`: **rejected** and quarantined.
- 0 additional unsound items found.
- Defect class is 3 items out of 209: comparison questions embedding both
  compared values or dates in the question text.

#### A leak nobody was looking for

Fixing the count exposed a separate problem. `corpus/questions.json` — the
file Round 1 workers read — was publishing `meta.group`,
`meta.evidence_groups`, `meta.source_articles`, and auditor `rationale`.

- **Answer location**: those three fields name the articles the answer lives
  in. A retriever reading them gets a 1–3 article candidate set inside a
  297-article corpus, which destroys the measurement the project exists to make.
- **Answer text**: 70 of 76 verbatim answer mentions in the partition came from
  `rationale` prose ("single atom states the 209 acre size"). No field was called
  "answer"; the answer was simply written into a free-text justification.

`data_tools/build_public_partition.py` now generates the file from a narrow
allowlist (`question_id`, `text`, `split`, `question_type`, `meta.original_id`,
`meta.exposure_note`, and who/which-model/decision provenance) and refuses to
write if a multi-word answer appears verbatim anywhere in the output.
`tests/test_public_partition.py` (17 tests) pins the contract and asserts
regeneration is byte-identical to the committed file.

`substrate.manifest.validate_freeze` now reads QA provenance from the staging
drafts rather than the public partition (which by design cannot carry it), and
adds a drift check so the two files cannot disagree about which questions are
published or under which split.

### 8.8 Third freeze review: three holes nobody had looked for

A third fresh reviewer (`opencode/space-bunny-free`, after `qwen3.8-27b:free`
returned a provider error and `nemotron-3.5-lightning-free` produced garbled
output and wrote nothing) confirmed the prior repairs, then found four things.

**R1 — the private manifest was git-ignored and never committed.** `.gitignore`
pattern `*private_test*.json` swallowed `corpus/private_test_manifest.json`, the
one file that carries the seal digest binding the out-of-repo private test to
this repository. `git ls-files` returned nothing; `git log --all` found no
commit; a fresh clone would have had no way to verify the private boundary —
while three documents asserted it was in-repo. Fixed with an explicit negation
rule and `git add -f`; a test now asserts the manifest is both un-ignored and
tracked, so it cannot silently regress.

**R2 — stage 6 passed on an empty partition.** `questions.json = []` produced
"0 ids, 0 structural error(s)" and PASS. Added a non-vacuity floor plus
answer-location and prose-leak diagnostics in stage 6 itself (the earlier fix
lived only in the builder and the unit tests, so a hand-edited partition slipped
through). 11 new tests in `tests/test_verifier_nonvacuity.py`, including one that
builds a deliberately leaky file and proves the unit tests fail on it.

**R3 — `docs/verify-round0.md` documented the leak as present.** It still said
the partition carries `meta (source_articles, group)` — exactly the answer-location
leak just removed — plus stale counts (209 items; "60/50/89", which sums to 199).
Corrected, and the stage-6 row now states what the stage actually enforces.

**R4 — the sweep ledger overstated its own coverage.** It claimed a review of
"all 197 approved items (…121 factoid, 14 ambiguous, 12 unanswerable)". Measured:
206 items, 128 factoid / 15 ambiguous / 13 unanswerable. The conclusion (only 3
affected) is unchanged; the arithmetic was wrong on three of five buckets and nine
items were unaccounted for. Corrected in place with the error stated, not
silently rewritten.

Non-blocking items also fixed: stage 9 passed while cross-checking **zero** pins
(it printed "no local cross-check available" and returned PASS — now a
fail-closed UNVERIFIED); `STATUS.md` mis-scoped the ambiguity hazard (6 → 15
items, 5 with empty `answer_text`) and described a scorer that does not exist;
and `STATUS.md` claimed scale retrievals "are adjudicated" when
`eval/scale_adjudication.py` has **zero consumers** — `eval/metrics.py` and
`eval/support.py` never mention scale or adjudication. That gap is now recorded
explicitly rather than left as a claim.

### 8.9 What the three reviews together establish

Three independent reviewers, none of whom implemented the work, each returned
REPAIR REQUIRED, and each found something the previous one did not:

- review 1: two items whose questions pre-stated their own comparison, plus a
  functional regression and a vacuous pass;
- review 2: a third such item in the **dev** split, found only by sweeping the
  whole set rather than sampling;
- review 3: the manifest was never committed, a stage passed on an empty file,
  and a stage passed while verifying nothing.

The pattern is the finding. Sampling is not verification, and a check that
compares nothing reports the same as a check that compares everything. The
project's own numbers demonstrate it: the pre-stated-premise class was 3 of 209
items, and three different reviewers needed three different methods to find it.
No reviewer returned PASS, so **the Round 0 freeze gate remains unsatisfied** and
no freeze tag exists.

### 8.10 Fourth freeze review: the consistent truncation

A fourth reviewer (`opencode/muse-spark-1.3-contributor-free`) used a method the
first three had not: instead of sampling the data, it asked *under what artifact
condition would each stage still print PASS?* It found the worst class of freeze
hole in the project.

**A consistent truncation passed three stages.** Delete 106 staging drafts **and**
the matching 106 entries in `corpus/questions.json` **together**, and:

- stage 5 saw 100 clean drafts → PASS
- stage 6 saw a self-consistent partition → PASS
- stage 8's partition/draft drift check compared the two sides against each
  other, found no disagreement → PASS

Every check inside the system agreed with every other check inside the system.
Nothing was left to disagree. The gap was that no check compared the system to
anything *outside* it.

This is worth stating plainly, because it is the general failure mode and not a
detail of this project: **a set of internal consistency checks cannot detect a
consistent corruption.** Every check the project had was of that kind — partition
vs drafts, drafts vs split map, manifest vs artifacts. All of them are necessary.
None of them is sufficient.

#### The fix is a pin outside the artifacts it checks

Note the wording, because the first version of this section got it wrong and an
independent review caught it: the census file lives **inside** the repository.
It is external to the *artifacts it checks* (drafts, partition), not external to
the repository. That distinction is not pedantic — an in-repo pin is defeated by
editing the data and the pin in the same commit, which is exactly what review v5
demonstrated. The trust root that actually holds is a digest recorded **outside
git**, described below.

`corpus/partition_census.json` holds the expected counts per split, the
quarantined ids, and the accounting identity `authored_total = published +
rejected`. It is a file that is not part of what it checks. Stages 5, 6 and
`validate_freeze` now require it and compare exactly — not "at least", because a
floor also passes a truncation that stops short of it.

A digest of the census is recorded in the custodian's private directory
(`freeze_census_pin.json`, outside git) alongside the private-test seal, and
stage 8 compares the live census against it. That out-of-repo digest is the real
trust root; the in-repo census is the thing being protected.

`RunManifest.require_partition_census` makes the requirement explicit and
opt-in, so the synthetic freeze fixtures (which build their own root and carry no
census) keep working without the check silently applying to real freezes and not
applying to fixtures.

`tests/test_partition_census.py` builds the exact truncation on a throwaway copy
and asserts stages 5, 6 and 8 each catch it, plus the missing-pin, wrong-pin and
quarantined-id-reappearing cases. The truncated tree that previously reported
9/10 now fails.

#### Other v4 findings

- The sweep-ledger census correction was incomplete: the headline count was fixed
  but the per-type breakdown still read 121 factoid / 26 comparison against a
  measured 128 / 28. Corrected.
- Stale counts again: `STATUS.md` and the ledger said 389 tests where the measured
  figure was 401, and one commit was unnamed in the ledger.
- Custody was re-checked by blob scan including dangling pre-private stash
  commits: only guard prose and one synthetic `qa-private-01` fixture. Clean.
- `check_training_overlap` can never return PASS by construction. That is
  disclosed and deliberate — but it means Round 1 training clearance is
  unimplemented, and it is recorded as such rather than presented as working.

### 8.11 Fifth freeze review: the pin that protects the pin

A fifth reviewer (`opencode/space-bunny-free`) tested the v4 fix rather than
trusting it, and found it defeatable.

**The census pin lives in git, so it can be edited with the data.** Truncate the
staging drafts and the partition to 100, then edit
`corpus/partition_census.json` so the counts agree — and stages 5, 6 and 8 all
PASS again. The freeze printed 10/10 while missing 106 of 206 questions. Every
check inside the repository agreed with every other check inside the repository,
and the one file whose whole job was to disagree lived in the same place the
data did.

Two things were wrong beyond the missing defence:

1. **Six documents called the in-repo census an "external pin"**, including
   §8.10 of this ledger — whose own text states the correct principle
   ("no check compared the system to anything *outside* it") and then contradicts
   it two paragraphs later. The file is external to the *artifacts* it checks.
   It is not external to the repository. A test now fails if our own documents
   overstate it. The review documents are excluded from that test: rewriting a
   reviewer's words to match ours would be the same sin as rewriting a historical
   error, which this project has now been caught at three times.

2. **`RunManifest.write()` exists and was never called.** The freeze produced a
   terminal verdict, not a durable artifact. There was no freeze tag, no manifest
   file, and no hash of the census recorded anywhere outside git.

#### The fix

- The census digest is now recorded **outside the repository**, in
  `<LMR_PRIVATE_EVAL_DIR>/freeze_census_pin.json`, beside the private-test seal
  and under the same trust model (procedural and workspace-based, not a kernel
  boundary). Stage 8 compares the live census against it and **fails closed**
  when the pin is absent or disagrees.
- `RunManifest.partition_census_sha256` binds the census to the freeze manifest.
  Building it revealed a third bug: the digest check had been written as an
  `elif` alternative to the content checks, so **recording a digest silently
  disabled the count checks**. Two separate questions now get two separate
  checks.
- `tests/test_census_trust_root.py` reproduces the co-edit and asserts stage 8
  catches it, asserts the pin is outside the repository, asserts a missing pin
  is a failure rather than silence, and pins the wording rule.

#### The pattern, third statement

Three review rounds have now found the same shape at three scales:

| scale | what every internal check agreed with |
|---|---|
| one item | the question text restating the fact its evidence supplied |
| the partition | the partition and the drafts agreeing on a truncated set |
| the whole freeze | the census agreeing with the data it was supposed to constrain |

An internal consistency check is necessary and never sufficient. The only thing
that catches a consistent corruption is something held outside it.

#### v5's judgement on convergence

The reviewer separated the two questions. The **code** has converged — 26 of 26
wrong-result mutations it tried were killed by real tests, and `eval/metrics.py`
and `eval/support.py` are genuine implementations rather than stubs. The
**integrity procedure** had not. Five reviewers each found a real hole using a
method the previous four lacked; the methods escalated in scope rather than by
luck. A sixth bounded method will also find something.

No reviewer has returned PASS. **The Round 0 freeze gate remains unsatisfied and
no freeze tag exists.**
