# Round 0 Progress Ledger (steward-maintained)

Steward model: `opencode/muse-spark-1.3-contributor-free` (explicit verified free endpoint, zero-cost catalog entry confirmed 2026-09-29). No nested spawning.
Scope: this steward owns ONLY `docs/progress-ledger.md`. No other file edited.
Status: **ROUND 0 IN PROGRESS — NOT FROZEN.** No architecture work, no QA creation, no benchmark runs, no freeze claim authorized.
Controlling spec: `master_orchestration_prompt.txt`. Worker policy: `AGENTS.md`. Orchestrator record: `docs/orchestration-log.md`.

Method: worker claims below are attributed and preserved as claims; orchestrator verification notes appear only where `docs/orchestration-log.md` records an independent orchestrator rerun. Measured results, estimates, and hypotheses are labeled.

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

## 2. What was tried → worked / failed (with evidence)

Worked (orchestrator-verified where noted):
- Free-endpoint discipline held: every spawn used an explicit verified zero-cost endpoint; one failure substituted Muse→Muse, no paid fallback (log §§allocation, substitution).
- Substrate contract iterated v0.1→v0.3 + provenance gate: reviewer-reproduced bypasses closed and re-verified by probes (v03 review §verification; provenance final review §§acceptance/integration). Orchestrator reruns: 34→88→113→147→175 pass at successive stages (log).
- Generator adapter brought to scoped PASS: 14/14 adversarial (orchestrator-executed), 3/3 fresh-process repeats byte-identical, smoke v3 PASS (v03 review §§runs/sign-off).
- Shared evidence repair (full-serialization cap, prompt v0.2, shared parser) integrated without generator/config edits outside owner scope (repair doc §scope; 113/113).
- QA tooling repaired to 41/41 + 175/175 with fail-closed context, content-bound approval shape, hint-free projection, `seal_records()`, importer pins (repair doc §§1–7; orchestrator reran 41/41).
- Corpus rebuild reproduced deterministically from bytes with matching hashes and hierarchy-clean load (worker §§9–10; orchestrator checkpoint recompute).

Failed / rejected (evidence preserved):
- Nemotron reference worker silent failure (no output, no files) → substitution, not completion (log §failure).
- Substrate v0.1, v0.2, v0.3(initial): REPAIR REQUIRED each round with reviewer-reproduced bypasses (reviews §§verdict/probes). Not accepted from test counts.
- Generator v1/v2: REPAIR REQUIRED (config drift, `--help` side effects, citation copying, token mislabeling); old FAIL traces preserved, not overwritten (generator review §§defects/traces; readiness §history).
- Fixed generator does NOT reliably abstain: 7/7 fresh PIDs assert unsupported "0.5" on empty evidence; v3 evidence-bearing output cites descriptively with `cited_valid: []` (v03 review §§runs/observations; empty-evidence analysis §§observation/limits). Recorded as model behavior for upstream gating / generator tournament, not adapter defect.
- Corpus pilot-247-v0 rejected for QA: 13.7% debris, 24 truncations, 23/30 groups incomplete, 310× HTTP 429 (log §gate; pilot §§6–8 superseded record).
- QA tooling qualified PASS not accepted: report file absent + gaps found on inspection (optional provenance bypass, ambiguous semantics unchecked, partition≠approval, evaluator hint leakage, code-point≠semantic) → directed repairs + corrected REPAIR REQUIRED review (log §§qualified-PASS/corrected-artifact).
- Criteria draft sent back: incorrect survival-product math, hard cutoffs, corpus-vs-supervision conflation, permission guidance, restrictive multihop assumptions → resumed to Ultra critic with controlling adjudication (log; criteria §adjudication).

## 3. Key orchestrator decisions and why

- Bounded 247-article pilot over more fetching: 33 GB free disk made 21 GB wiki.db infeasible; boar pattern favored small local corpus (log §reference/audit; audit §7).
- Threads=1 for fixed Round 1 generator: cross-process variance at `-t 6` vs identical at `-t 1` in synthetic probes; reproducibility over ~28→~11 tok/s decode (readiness §0/§0b; log §integration).
- Prompt v0.2 + shared parser + strict full-serialization cap: per-span summation + first-span overflow + literal `[node_id]` emission observed; fixed as pre-freeze interface repair, not benchmark tuning (log §§integration/empty-diagnostic; evidence repair §§1–3).
- Hallucinated citations permitted as recorded failures (not trace rejection); completion binary with separate fractional diagnostic; `model_probability` as evaluable-uncalibrated state; Round 0 records declarations not learned fits: avoid selection bias, naming confusion, and demanding architecture thresholds pre-teams (v03 repair §2; log §v02-disposition).
- Mandatory nonempty source provenance + `public_reference` dev-only + UNKNOWN-not-zero: v0.3 optional-metadata skip contradicted article-generalization; controlled QA without sources bypassed group validation (log §v0.3-disposition; provenance repair §§verdict/scope).
- Offline-only rebuild from 297 raws, archive v0, no further network: v0 debris/truncation/group-breakage confounded evidence work; 50 extra raws already on disk made rebuild possible without new fetching (log §quality-gate; pilot §§0/9).
- Feasibility survey allowed as shared metadata-only work; no weights/architecture/divergence: unblocks Round 1 design info without breaking freeze sequencing (log §repair-verification).
- No Android claims from desktop; no second-machine / cache-cold mandates; no fixed survival %: desktop numbers are proxies; poor survival is valid negative result (criteria adjudication; contract §§6–7; log §adjudication).

## 4. Current gate state

**NOT FROZEN.** No architecture implementations, held-out runs, or tournament conclusions authorized.

Provenance/code gate: substrate code PASS on provenance scope (final review §§verdict/integration); v0.3 P0 bypasses closed (v03 review §verification); generator adapter PASS on captured v3 snapshot (v03 generator review §sign-off). These are scoped passes, not a Round 0 freeze.

Freeze still requires (per contract §9, final-review §status, log checkpoint):
1. Accepted pinned corpus (`corpus/corpus.jsonl` rebuilt `08aa2c53…089d1` exists but NOT accepted — completion report + independent quality review pending).
2. `corpus/questions.json` — absent (no real QA created by design).
3. Sealed held-out labels under orchestrator custody — absent; dev workers must not inspect/parse.
4. Independent re-review PASS of v0.3 + provenance + QA-tooling repairs on current snapshots.
5. `validate_freeze` on a real manifest passing with all pins/hashes/seeds/inventory.
6. Procedural custodian separation acknowledged as limitation (same OS user; true isolation = orchestrator withholds sealed file).

## 5. Outstanding blockers

- Independent corpus quality review of pilot-297-r1 (semantic preservation: infobox/wikitable/`{{chem}}` removals, sentence heuristic, offset-less anchors) — owner: orchestrator-assigned reviewer.
- Corpus worker completion report for rebuild — owner: corpus worker.
- Independent re-reviews: substrate v0.3 repairs, provenance repair, QA tooling + protocol repairs, model-feasibility pins — owner: orchestrator-assigned Ultra reviewers.
- Real QA creation blocked behind corpus finality + approved protocol/tooling + custodian assignment + public-import pin + volume/grouping decisions (protocol §7) — owners: orchestrator then QA workers. No labels yet by design.
- Generator residual: live `/props` template cross-check, empty-packet accounting adversarial path, single-fixture/seed generality — documented non-blocking gaps (v03 generator review §§static/gaps); upstream sufficiency gating for non-abstention.
- Stale artifact risk: prior "freeze status" lists and v0 hashes retained for audit must not be read as current pins; current candidate corpus hash is `08aa2c53…089d1`, generator prompt `d8580509…`, model sha `1adf0b11…6c3370` — all still pending freeze.

## 6. Measured vs estimates vs hypotheses

- MEASURED (orchestrator reran): tests 34, 88, 113, 147, 175 pass; data-tools 41/41; converter 17/17; corpus load 113,951 nodes / 0 hierarchy errors; corpus hash recompute match; manifest byte/SHA match; generator adversarial 14/14; model sha match; smoke/repeat/empty-probe raw traces as stored (byte-identical repeats, 7/7 identical empty answers, `cited_valid: []` in v3 smoke).
- MEASURED (worker-reported, reviewer-executed, not orchestrator-rerun): reviewer probes (freeze bypasses, tamper detection, policy rejections); token ratio ~1.49× whitespace on one fixture; load/prompt/decode timings on i7-8700 (process-cold, page-cache uncontrolled); debris re-scan 3/9,979 (LaTeX FPs); removal counts (26,784 templates, 6,854 rescues, etc.); link counts (1,748 total, 775 cross-split).
- ESTIMATES / PROXIES (not mobile claims): all latency/RAM/disk figures are desktop-CPU proxies; server RSS ~1.4–1.6 GB, client ~28 MB; page-cache effects reported as observed/unknown; no cache-cold or Android measurement.
- HYPOTHESES (untested): tiny-Ettin sufficiency, KaLM compression retention, heads-vs-LoRA, GLiNER/Laya utility, adaptive breadth, multihop frequency — all Round 1 questions, none decided. Feasibility doc statuses are VERIFIED_EXISTS / ADVERTISED_NOT_VERIFIED, never EXPERIMENTALLY_VERIFIED.

## 7. Attribution log (worker claims preserved)

- Substrate leads/repairs: Muse Spark Free — contract v0.3, evidence-token repair, v0.3 repair, provenance-gate repair; test claims 34/88/113/147/175 at respective stages.
- Reference audit: Muse Spark Free (replacement) — pins, eval/corpus/generator analysis, §7 recommendations.
- Corpus: Muse Spark Free — pilot-247-v0 then pilot-297-r1 rebuild, §§9–11 measurements.
- Generator: Muse Spark Free — artifact pin, adapter v1→v3, smoke/adversarial/repeat/empty-probe traces, readiness report.
- Dataset/QA tooling: Muse Spark Free — `data_tools/`, protocol, 7-item repair, 41-test claim.
- Model feasibility: explicit free Muse researcher — Hub metadata survey, catalog JSON.
- Independent reviews: Nemotron 3 Ultra Free — substrate v0.1/v0.2/v0.3, generator v1/v03, QA tooling corrected review, provenance final review. No review is a freeze.
- Endpoint failure: Nemotron 3.5 Lightning Free silent non-response → substitution recorded, no paid fallback.
