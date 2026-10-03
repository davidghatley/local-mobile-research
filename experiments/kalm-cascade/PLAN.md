# KaLM Coarse-to-Fine Cascade — Implementation Plan (Mise-en-Place)

Status: READINESS PLAN. No code, no measurements, no private data.
Companion: `HYPOTHESIS.md` (the why + the falsifier). This file is the how,
in order, with entry/exit gates. Frozen substrate `round0-freeze-r1`
(`a0e7534`). All DESKTOP. Generator FIXED (`qwen25-1.5b-q4km-fixed-v1`).

## Phase 0 — Pin and verify (gate: every hash recorded or STOP)

1. `hf download KaLM-Embedding/KaLM-Reranker-V1-Nano-R2` to a content-pinned
   local dir. Re-resolve `main`, compare to `32b242bb7fd7ad6fd404154c09560d249ffe017f`;
   on drift, re-verify §§2–4 of HYPOTHESIS.md against the new tree before proceeding.
2. Record in the run manifest: model id, revision SHA, weight-file sha256,
   `sentence-transformers` / `transformers` / `torch` versions, CPU model +
   thread pinning, `kalm_cross_encoder_config.json` bytes
   (`query_max_length=512, document_max_length=1024, encoder_chunk_size=4`),
   instruction string, master seed + `derive_seed` log.
3. Install CPU-only env per HYPOTHESIS.md §10. GPU is NOT required and must
   not be required (keeps the desktop measurement reproducible).
4. Write HYPOTHESIS.md tests 1–4, 6, 9, 11 first (pool math, padding edge,
   1x definition, query-independence, boundary, policy validation, seeds).
   EXIT GATE: all green on CPU before any index byte is built.

## Phase 1 — Measure the tokenizer, replace the estimates

1. Tokenize all 9,979 paragraphs with the KaLM tokenizer
   (`<Document>: {paragraph}`, `add_special_tokens=False`, truncate 1024):
   exact token-count histogram, fertility (chars/token), truncation count at
   the 1024 cap (the ~1,140-token longest paragraph is the known edge).
2. Recompute HYPOTHESIS.md §5 with MEASURED tokens; check
   `test_storage_manifest` tolerance (±15%). A missing fertility table
   blocks Phase 2 (per STATUS.md: a missing artifact blocks freeze-style
   gates — same discipline here).
3. Decide candidate unit in writing: PARAGRAPH (default). Any deviation
   (sentence/section) requires recomputing §5 and the §7 sweep ranges.

## Phase 2 — Cache-faithfulness proof (gate: bit-faithful or STOP)

1. Implement the minimal cache path: `get_encoder(doc)` → save
   `(last_hidden_state, attention_mask)` bf16 → load → `pool_encoder_chunks`
   → decoder via the existing `encoder_outputs=BaseModelOutput(...)` hook.
   No new numerics: same functions, split across time.
2. `test_cache_faithfulness` (HYPOTHESIS.md test 5): cached vs inline
   `predict` within fp tolerance on a fixed 20-pair fixture at 128x, 4x, 1x.
   EXIT GATE: exact agreement gate green. NOTHING downstream may use the
   cache until this passes — every cascade number depends on it.
3. Write tests 7, 8, 10, 12 (survival monotonicity, packet budget, storage
   manifest, Regime-B manifest).

## Phase 3 — The 128x turnover pilot (gate: decides the cascade shape)

1. On 20 dev questions × full paragraph set: score 128x AND 4x AND 1x.
   Compute turnover@K (K = 50/100/200/500) for sufficient-set members
   (labels per the §12-A ruling — see Dependencies), plus the
   loss-ledger fields of §8 (stage lost, rank trajectory 128x→4x→1x,
   margin-to-cut, question_type × atoms-per-set split, second-atom canary).
2. DECISION RULE (preregistered here): turnover@200 ≈ 0 AND no
   second-atom concentration → collapse to 128x → 4x → packet (drop
   64x/32x/16x/8x). Else keep the cheapest intermediate that closes the
   gap, re-measure, and cost every kept stage in §5 currency.
3. Also record per-query decoder latency + peak RSS per ratio on the pinned
   CPU (load vs inference separated via `timed_phase`; subprocess memory via
   `proc_rss_mb` if a server is involved — default: in-process). These are
   the cost denominators for the §12 baseline comparison.

## Phase 4 — Threshold sweep + freeze (dev; shadow-dev confirms, never fits)

1. Sweep (M, N, τ₀, τ₁) per HYPOTHESIS.md §7 ranges on DEV ONLY
   (M ∈ {200,500,1000}, N ∈ {20,50,100}; τ fit conditional on survival).
   Objective: max direct cumulative final completion subject to decoder-cost
   budget; report the full frontier, not a point.
2. Calibration sub-step: ECE/Brier of raw P(yes) on dev; fit temperature OR
   isotonic on DEV ONLY if needed, with `calibration_partition` provenance;
   freeze. Confirm (no refit) on shadow-dev.
3. Freeze (M, N, τ₀, τ₁, instruction, chunk sizes, calibration) into
   `RunManifest.thresholds` as validated `ThresholdPolicy` entries.
   Confirm the frozen point once on shadow-dev. Any change = re-freeze +
   re-confirm. Shadow-dev is NEVER fit on (it is dev-visible, not held-out,
   but the discipline is what makes the private run credible).

## Phase 5 — Full dev + shadow-dev runs, baseline arms, report

1. Run cascade + single-stage 4x + single-stage 128x + single-stage 1x arms
   over dev and shadow-dev with complete `StageRecord`/`RetrievalOutcome`
   traces (26 required fields; unmeasured telemetry = explicit null, never
   silent; `score_kind=model_probability` throughout).
2. Compute §8 metrics: stage_coverage, conditional_retention (with
   denominators), survival lineage, lost_and_recovered, direct cumulative
   completion (NEVER products), Wilson CIs, ECE, evidence-token cost,
   context precision, abstention accuracy, latency/RSS/storage manifest.
3. Apply the §12 verdict rule: non-inferior completion vs 4x AND strictly
   lower decoder cost (pre-compute amortised separately), else REFUTED →
   recommend single-stage 4x. Check the generator floor FIRST (STATUS.md
   risk 3): if evidence deltas do not move answer metrics on ANY arm,
   say so and keep the evidence-level verdict primary.
4. Scale-tier run: same frozen point over the 830 substantive scale units;
   read with `unjudged_top_k` + limitations (STATUS.md risk 6; the
   adjudication rule is not yet wired into the metric layer — Round 1 work,
   not ours to assume).
5. Regime A/B: identical procedure; B excludes the public 21 from
   adaptation data; report A-on-paired, B-on-same-paired, delta via
   `aggregate_paired_delta` (never pooled).

## Dependencies / rulings needed before Phase 3

- D1 (ORCHESTRATOR): §12-A — how are dev/shadow-dev thresholds and ECE
  computed with no worker-visible labels? (synthetic-only vs
  custodian-scored runs). Blocks Phase 3–4.
- D2 (CUSTODIAN): leakage-gate seal binding timeline (STATUS.md risk 5 /
  contract §5 limitation). If unbound, synthetic batches stay unusable and
  D1's answer must be custodian-scored runs.
- D3 (ORCHESTRATOR): confirm PARAGRAPH as the cross-team candidate unit
  (§12-B), or bless per-team units with a conversion rule.
- D4 (CUSTODIAN): judge digest pin (STATUS.md risk 4) before ANY
  answer-metric is reported; until then answer columns stay ABSENT.

## Explicit non-goals

No ONNX/ExecuTorch packaging attempt (vendor states it does not exist);
no R2 GGUF build (V1-only precedent, fixed-ratio, patched runtime);
no vLLM deployment (CUDA-only, 32x-capped, irrelevant to the cascade
question); no generator/instruction tuning; no private-data access at any
phase; no Android measurement.
