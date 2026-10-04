# Round 1 Independent Readiness Review

**Date:** 2026-10-04  
**Reviewer:** Independent subagent (not the implementer)  
**Scope:** Adversarial review of Round 1 implementations against frozen contracts

---

## VERDICT: REPAIR REQUIRED

---

## Question-by-Question Verdict Table

| # | Question | Verdict | Evidence (file:line or command output) |
|---|----------|---------|----------------------------------------|
| A1 | Model-facing boundary obeyed? | **PASS** | All retrievers call `to_model_query` (runner.py:136); `assert_no_label_metadata` guards QueryInput (query.py:147-167). No retriever imports `custodian_truth` or `oracle`. |
| A2 | Staging dir carries label leakage? | **CONFIRMED** | `staging/qa-dev-11.json` lines 48-54 carries `meta.group`, `meta.source_articles`, `labels.answer_text`. `corpus/questions.json` lines 3-14 shows `meta: {}`. Worker boundary is procedural only — no code enforces it at retrieval time beyond `to_model_query`. No retriever exploits it (verified by code inspection). |
| A3 | Evidence budget identical? | **PASS** | `packer.py:104-112` calls `build_packet(exact=True, tokenizer=..., cap=HARD_EVIDENCE_TOKEN_CAP=1000)`. `tokenizer.py:65-78` uses pinned GGUF tokenizer. Per-article cap=3 enforced in `packer.py:77-82`. No system can give generator more text. |
| A4 | Score_kind declarations honest? | **PASS** | B1: `similarity` ✓ (b1_lexical.py:68). B2: `similarity` for both stages ✓ (b2_static.py:305, 320). B3: `logit` ✓ (b3_reranker.py:212). C: `logit`/`rank`/`similarity` correctly per head ✓ (shared_heads.py:76-80). All `threshold_policy.score_kind == stage.score_kind` validated at trace build (trace.py:104-108). |
| A5 | Thresholds from dev only? | **PASS** | MMD register is fixed in `R1_CONTRACT_ERRATUM.md:76-82` and `CONTRACT.md:110-118`. No code reads `shadow_dev` or `private` to select thresholds. `generator_floor.py:230-322` uses registered MMD only. |
| A6 | Retrieval unit = paragraph? | **PASS** | `corpus_view.py:19-20` documents retrieval unit is paragraph. `score_retrieval.py:8-11` defines survival via host paragraph. `eval/support.py::covers` (referenced) is ancestry-aware. |
| B7 | Recomputed metrics (B1,B2,B4) | **MIXED** | **B1 dev**: Stage-0 survival 70/73=95.89% ✓, final completion 54/73=73.97% ✓, item-level 76.36% ✓. **B4 dev**: identical to B1 (same retrieval) ✓. **B2**: No report file exists — traces written but `score_retrieval.score_traces` never run on B2 traces. **B4 shadow_dev**: Stage-0 120/122=98.36% ✓, final 80/122=65.57% ✓. |
| B8 | Loss attribution claim verified? | **PARTIAL** | `loss_attribution_B1_bm25_dev_core.json:2-7`: per-article cap=10, token budget=6, stage0 rank=3, survived=54. Per-article cap IS largest single mechanism (10/19 losses). But "no-cap ablation gain ~2 paragraphs" is NOT directly measured — the cap=0 ablation exists in `dev_core_cap0/` but was not scored against ground truth to compute the gain. |
| B9 | Generator-floor logic auditable? | **PASS** | `generator_floor.py:230-322` implements three-way rule correctly. Adversarial tests in report §2 (lines 43-64) confirm: zero discordance ⇒ Clopper-Pearson bound; small n ⇒ INCONCLUSIVE; strong effect ⇒ NOT FLOORED; null ⇒ UNDERPOWERED. McNemar exact p-values match closed forms (0.001953125 for n10=0,d=10 and n10=10,d=10). |
| B10 | Any "WIN" below MMD? | **NO FALSE WINS** | Floor probe verdict = UNDERPOWERED (not a win). B2, B3, C have no quality numbers yet (custodian scoring pending). No report claims a win. B2 label-free proxy (Jaccard 0.6121) explicitly labelled NOT YET MEASURED. |
| B11 | C_shared_heads n=12 vs n=59? | **NO INVALID COMPARISON** | `SHARED_HEADS_REPORT.md` covers `--limit 5` only (not 12). No comparison to n=59 runs. Report §5 explicitly states "Full dev (59) and shadow_dev (87) runs... NOT measured". |
| C12 | Android/mobile claims from desktop? | **PASS** | `SHARED_HEADS_REPORT.md` line 100: "Anything on-device: desktop CPU only; no mobile/Android claim is made or implied." `BASELINE_IMPLEMENTATION_REPORT.md` line 89: "≈75.7 min single-threaded CPU" labelled ESTIMATE. `R1_RUN_STATE_REPORT.md` line 92: "No CUDA. Neural inference... CPU-only." |
| C13 | MEASURED vs ESTIMATED consistent? | **MOSTLY PASS** | All tables label status. Minor: B2 query latency "~5–20 ms" (line 70) is ESTIMATE but table doesn't repeat label per cell (header says "Labels" column). B3 full-dev cost "ESTIMATE" clearly labelled. No unlabelled estimates found. |
| C14 | Peak RSS / latency honest? | **CONCERN** | `SHARED_HEADS_REPORT.md` lines 24, 48-50: RSS 822-1466 MB across stages, "box was shared with parallel workers; treat single-query timings as ±20% noisy". Model-load latency (674ms) separated from inference ✓. But contention noise acknowledged and not quantified — latency attribution has ~20% uncertainty. |
| C15 | Generator artifact excluded? | **PASS** | `BASELINE_IMPLEMENTATION_REPORT.md` lines 115-123: "~1 GB fixed generator is shared by all systems and excluded from per-baseline cost." Index storage (postings) separate from weights. |
| C16 | Private test untouched? | **PASS** | `R1_RUN_STATE_REPORT.md` lines 33, 44-50: "NO architecture scored against private. Private counts 116 items... never opened." Floor probe uses `staging/` (worker-visible) only with `LMR_CUSTODIAN_ORACLE_TOKEN`. No private-derived numbers in `experiments/results/`. |
| D17 | Required deliverables status | **SEE BELOW** | Detailed in "Missing Deliverables" section. |
| D18 | KaLM / hybrid-fusion / adapter-peft implemented? | **NOT DONE** | `experiments/` contains `kalm-cascade/`, `hybrid-fusion/`, `adapter-peft/` directories but they contain only `HYPOTHESIS.md` / `PLAN.md` prose — zero implementation, zero results. |
| D19 | Conclusions overstated? | **YES** | See "Overstated Claims" section. |

---

## DEFECTS

### BLOCKER

**D1. B2 retrieval quality never scored — custodian metrics missing**
- **File:** `experiments/results/retrieval/dev_core/` — contains `traces_B2_bm25_static_union_dev_core.jsonl` but NO `report_b2_dev_core.json`
- **What is wrong:** The B2 system ran (59 questions, traces written) but `experiments.common.score_retrieval.score_traces` was never invoked on its traces. The primary retrieval metrics (stage survival, final packet completion, evidence tokens) are therefore UNMEASURED for B2. A baseline cannot be compared without its primary metrics.
- **Correct behaviour:** Run `score_retrieval.score_traces` on B2 traces against ground truth (custodian-side) and produce `report_b2_dev_core.json` and `report_b2_shadow_dev_core.json`.

**D2. B3 full dev run not executed — only latency projection exists**
- **File:** `BASELINE_IMPLEMENTATION_REPORT.md` lines 79-89
- **What is wrong:** B3 (68M reranker) measured per-card latency on 5 questions (~77.2 s/q) and projected 75.7 min for 59 questions. Since this exceeds the 40-min threshold, the spec mandates labelling as ESTIMATE — which was done — but the actual retrieval quality (stage survival, final packet completion) for B3 on dev is UNKNOWN. The ceiling system has no measured quality numbers.
- **Correct behaviour:** Either run B3 on a smaller representative sample (e.g., 10 questions) with full scoring, or explicitly declare that B3 quality is not measured and cannot be compared.

**D3. Shared Heads (Family C) quality not measured — only n=5 infra run**
- **File:** `SHARED_HEADS_REPORT.md` lines 81-89
- **What is wrong:** The report explicitly states "Per-head stage survival / top-K retention requires custodian-held labels... **No ndcg/mrr number is reported, and no quality win is claimed.**" The architecture family has zero measured retrieval quality. It cannot be shortlisted without custodian scoring.
- **Correct behaviour:** Submit C traces to custodian for scoring, or run custodion-side scoring if labels are accessible.

### MAJOR

**D4. dev_core_cap0 ablation not scored against ground truth**
- **File:** `experiments/results/retrieval/dev_core_cap0/` contains traces but no report
- **What is wrong:** The per-article cap ablation (cap=0) was run for B1 but `score_traces` was never invoked. The GENERATOR_FLOOR_REPORT.md §5 claims "no-cap ablation gain really only ~2 paragraphs" but this number is not in any artifact — it appears to be an unverified assertion.
- **Correct behaviour:** Score the cap=0 traces to measure actual no-cap completion rate and compute the true gain.

**D5. B2 query latency reported as single estimate without distribution**
- **File:** `BASELINE_IMPLEMENTATION_REPORT.md` line 70
- **What is wrong:** "Query latency (per question) ~5–20 ms (estimated: table lookups + one GEMV over 9,979 × 1024)" — no per-question measurements, no median/p95/max. The static channel is a significant component of B2 latency; "ESTIMATE" label is present but the number is a single range, not a measured distribution.
- **Correct behaviour:** Measure B2 latency on the 59 dev questions (or a sample) and report full distribution.

**D6. Ettin cascade has no results at all**
- **File:** `experiments/ettin_cascade/` — only implementation, no results directory
- **What is wrong:** The cascade family is implemented but never run on any split. No traces, no metrics, no report.
- **Correct behaviour:** Run cascade on dev (at minimum) and produce retrieval metrics.

### MINOR

**D7. B2 static embedding cache not included in run_summary.json index_stats**
- **File:** `run_summary.json` line 10-12 (for B2 run) — only BM25 stats
- **What is wrong:** The 39 MB static embedding cache (`b2_static_embeddings.npy`) is a significant storage component but absent from the run summary's `index_stats`.
- **Correct behaviour:** Include embedding cache bytes in `index_stats` for B2 runs.

**D8. B3 per-card latency measured with 5 questions only — small sample**
- **File:** `BASELINE_IMPLEMENTATION_REPORT.md` line 81
- **What is wrong:** "Per-card latency (measured on 5 dev questions) ~77,240 ms per question" — 5 questions is a very small sample for a latency measurement that projects to 75 minutes. Variance across questions is unreported.
- **Correct behaviour:** Report min/median/max/p95 across the 5 questions, or increase sample.

**D9. Trace validation passes but `storage_bytes` is null everywhere**
- **File:** All trace files — `"storage_bytes": null`
- **What is wrong:** The wire trace schema requires `storage_bytes` (stage-score-semantics-notes.md line 63). It is set to `None` in runner.py:177. The CONTRACT.md §3 says storage is "ESTIMATED (index); MEASURED (per-file sizes)". Not measuring it at all leaves a gap in the primary metric chain.
- **Correct behaviour:** Populate `storage_bytes` with measured index + weight sizes per system.

---

## UNVERIFIED

| Item | Why Unverified |
|------|----------------|
| Private eval leakage gate end-to-end | Did not run `check_training_overlap` — only verified seal exists and gate code is present (`R1_RUN_STATE_REPORT.md:34`). Cannot confirm it issues PASS/REJECT correctly against real sealed set. |
| `eval/support.py::covers` ancestry logic | Referenced in contracts but not read. The claim "retrieving an ancestor paragraph satisfies a leaf atom" rests on this function. |
| `substrate.evidence.build_packet` exact token counting | Used via `packer.py:104`; relies on `llama-server /tokenize`. Did not independently verify token counts match generator's internal accounting. |
| Scale tier (core+distractor) runs | No scale-tier retrieval runs exist in `experiments/results/` — all runs are `core` tier only. |
| Custodian oracle packet construction legitimacy | Verified code path requires `LMR_CUSTODIAN_ORACLE_TOKEN` (oracle.py:44-58), but did not verify the token is not accidentally available to workers in the environment. |
| Synthetic training data + leakage clearance | Does not exist yet — `R1_RUN_STATE_REPORT.md:102` lists as gap. |
| Regime A/B manifests | Do not exist — same gap. |

---

## MISSING DELIVERABLES (from Run Brief / Contract)

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Baselines B0-B4 + ORACLE condition | **PARTIAL** | B1, B4 implemented & run (retrieval). B2 implemented & run but NOT scored. B3 implemented but NOT run on full dev (latency projection only). ORACLE condition exists as floor probe arm but not as standalone retriever. B0 (no retrieval) not mentioned. |
| Common synthetic training data + leakage clearance | **NOT DONE** | Gap listed in `R1_RUN_STATE_REPORT.md:102`. |
| Regime A/B manifests | **NOT DONE** | Gap listed in `R1_RUN_STATE_REPORT.md:103`. |
| All five architecture families | **NOT DONE** | Families in `experiments/`: baselines ✓, shared_heads ✓ (infra only), ettin_cascade ✓ (impl only), kalm-cascade ✗ (prose only), hybrid-fusion ✗ (prose only), adapter-peft ✗ (prose only). |
| DEV results for each | **PARTIAL** | B1, B4 have retrieval metrics. B2 traces exist but unscored. B3, C, cascade have no quality metrics. |
| Readiness review per architecture | **THIS REVIEW** | This is the first independent review. |
| Per-architecture freeze | **NOT DONE** | No architecture has been frozen post-review. |
| ONE frozen SHADOW_DEV run per architecture | **NOT DONE** | B1 and B4 have shadow_dev retrieval runs (unscored for quality? — actually B1/B4 shadow_dev reports exist but only retrieval metrics). Others: no. |
| Scale-tier experiment | **NOT DONE** | No scale-tier runs in results. |
| Final shortlist | **NOT DONE** | Premature — insufficient measured quality data. |

---

## OVERSTATED CLAIMS

### 1. "The generator's ceiling sits an order of magnitude below the benchmark's discrimination threshold" → **Technically true but misleading framing**
- **Source:** `GENERATOR_FLOOR_REPORT.md` lines 103-104
- **Issue:** The oracle accuracy is 14.6% (20/137), B4 is 11.7% (16/137). The gap is 2.9 pp = 4 items. The MMD is 18 items = 12.3 pp. The statement "order of magnitude" refers to 4 vs 18 (4.5×), not 10×. More importantly, the **exact-match metric is confounded by verbosity** (§4.2) — containment shows oracle 81% vs B4 67%. The 14.6% exact-match is a severe undercount of the generator's actual capability on oracle evidence. The ceiling may be higher than measured.

### 2. "Retrieval/evidence metrics must carry the entire tournament... they do discriminate (§5)" → **Unproven for non-baseline architectures**
- **Source:** `GENERATOR_FLOOR_REPORT.md` lines 112-113
- **Issue:** §5 shows B1 retrieval metrics (stage-0 survival 95.9%, final completion 74.0%). But **no other architecture has measured retrieval quality yet**. B2, B3, C, cascade have no survival/completion numbers. The claim that retrieval metrics "separate systems" is a hypothesis, not a measurement.

### 3. "Shared-vs-separate parameter ratio: 3.00×" and "compute ratio: ≈3.00×" → **Derived arithmetic, not measured**
- **Source:** `SHARED_HEADS_REPORT.md` lines 27-31, 58-64
- **Issue:** These are arithmetic derivations (3 heads × 16.86M params vs 1 shared 16.86M + 3×66K). The "3×" assumes the separate-checkpoint baseline would use 3 full checkpoints. But the separate baseline was **not run** (§5: "A separately executed 3-process baseline was NOT run"). The compute ratio assumes backbone dominates (true) but ignores that separate checkpoints could batch together. Label as DERIVED, not MEASURED — which the report does, but the headline numbers are presented prominently.

### 4. "B2 adds a static semantic channel" → **Implies quality improvement, but quality unmeasured**
- **Source:** Multiple reports
- **Issue:** B2 is implemented and runs. Its label-free proxy (Jaccard distance 0.6121) shows it retrieves different candidates than BM25. But **whether those different candidates improve required-evidence survival is unknown** — the custodian scoring was never run. The architecture is treated as "done" in reports but its primary metric is absent.

### 5. "Per-card latency ~77,240 ms per question" for B3 → **Single aggregate, no distribution**
- **Source:** `BASELINE_IMPLEMENTATION_REPORT.md` line 81
- **Issue:** Measured on 5 questions. No min/median/max reported. The projection to 75.7 minutes for 59 questions assumes zero variance. On a shared CPU with parallel workers (acknowledged in C report), actual wall time could differ significantly.

### 6. "The tournament proceeds on [retrieval metrics]" → **Premature**
- **Source:** `GENERATOR_FLOOR_REPORT.md` line 169
- **Issue:** The tournament has only ONE architecture (B1/BM25) with measured retrieval quality on dev. B4 is identical retrieval. B2 ran but unscored. B3, C, cascade have zero quality measurements. You cannot "proceed on retrieval metrics" when 5 of 6 systems lack them.

---

## Summary

**The substrate (common code) is solid** — it correctly enforces the model-facing boundary, evidence budget, score_kind honesty, threshold register, and retrieval unit. The trace schema validation works and catches real errors.

**The measurements are incomplete** — only B1/B4 have retrieval quality numbers on dev. B2 ran but is unscored. B3, C, and cascade have no quality data at all. The floor probe correctly returns UNDERPOWERED, which is the honest result.

**The reports overstate readiness** by presenting infrastructure runs (B2, C) as if they were evaluated architectures, and by framing the generator floor finding as settling the tournament's metric strategy when the alternative architectures haven't been measured.

**Repair required:** Score B2 traces, run B3 on a sample with scoring, run cascade on dev, submit C traces for custodian scoring. Only then can a shortlist be informed by data rather than infrastructure completeness.

---

*End of Review*