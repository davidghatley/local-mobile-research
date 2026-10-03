# Adapter / PEFT Family — Round 1 Mise-en-Place Plan

Status: READINESS REPORT ONLY. No implementation, no training, no private
data, no synthetic data, no adapter weights. Frozen substrate: tag
`round0-freeze-r1`, commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`.
All measurements DESKTOP. No Android or on-device claim.
Companion: `experiments/adapter-peft/HYPOTHESIS.md`.

## Phase 0 — Pins and environment (before ANY run)

1. Re-resolve Hub HEADs at implementation time for:
   `BAAI/bge-small-en-v1.5` (`5c38ec7…` observed 2026-10-03),
   `cross-encoder/ettin-reranker-17m-v1` (`9e4aa35…`),
   `Snowflake/snowflake-arctic-embed-xs` (`d8c8652…` — licence unverified,
   check card), `BAAI/bge-base-en-v1.5` / `BAAI/bge-large-en-v1.5`
   (comparators). Record each `revision` + weight-file sha256 + byte size in
   the run manifest. Any drift from the observed SHA = re-verify before use.
2. Pin library versions in the manifest: `transformers==5.18.0`,
   `peft==0.21.2`, `sentence-transformers==6.1.0`, `onnxruntime==1.30.0`,
   torch version from the shared env. No paid endpoints, no nested agents.
3. Assert `config.json` geometry matches HYPOTHESIS §3 (bert h=384/12L,
   ettin modernbert h=256/7L, xs bert h=384/6L); mismatch = STOP.
4. Verify the fixed generator pin (`GeneratorConfig.is_pinned()`,
   `PROMPT_HASH`) — the same instance serves generation of synthetic
   questions and the final harness for every arm.

## Phase 1 — Infrastructure probes (no QA labels, no synthetic data)

1. Implement `experiments/adapter-peft/` adapter wrapper implementing the
   `substrate.interfaces.Retriever` protocol: stage-0 BM25 (shared pinned
   pipeline) → adapter rescore → packet packing. Query surface strictly
   `QueryInput(question_id, text)` via `to_model_query`;
   `assert_no_label_metadata` on every model-facing payload.
2. Merge-parity probe (`test_merge_parity`) on 20 fixed pairs; target
   |Δlogit| ≤ 1e-5 fp32. FAIL → do not proceed: the export story collapses.
3. Frozen-base probe (`test_adapter_params_frozen_base`): non-LoRA tensors
   bit-identical after a dummy training step.
4. BM25 stage-0 on dev through the shared harness; confirm recall@500 ≥ 0.90
   (else fix stage 0 — hypothesis work is moot).

## Phase 2 — Synthetic data under the custodian gate

1. Generate synthetic questions from the shared corpus with the FIXED
   generator (fixed prompt, Q4_K_M, evidence budget 300–800). Recipe:
   sample paragraph → extract answer span → render question → gold positive =
   source paragraph; hard negatives = same-article paragraphs + BM25 top
   non-positives. Deterministic via `derive_seed` derivation logged in the
   manifest. Namespace `synth-peft-{regime}-{n}`.
2. Submit each batch to the ONE-SHOT custodian leakage gate. PASS → usable;
   REJECT → remove exactly the listed synthetic ids; no re-probing, no
   iterating against verdicts. HONEST LIMITATION: the gate is not yet
   seal-bound; if it refuses PASS, all adaptation work is blocked and the
   report says so — retrieval-only work continues.
3. Regime B manifest: adaptation-data manifest minus all 21 articles from
   `substrate.query.worker_regime_b_exclusions()`; unit-test
   `verify_adaptation_exclusion`; query-time corpus unchanged.

## Phase 3 — Adaptation runs (dev only for all selection)

1. Train LoRA on bge-small (r=8/16 on q,v first; r∈{8,16,32} recorded),
   InfoNCE with BM25-mined negatives; same recipe on ettin-17m with
   MarginMSE for the cross-encoder arm. Same synthetic manifest for both.
2. Determinism: fixed seed derivation; two identical short runs must match
   first-batch loss (catches uncontrolled RNG).
3. Merge both arms; merge-parity re-run on merged artifacts.
4. Ablations (each first-class, separately recorded):
   - adapter OFF (frozen base) — the base we must beat;
   - LoRA r sweep {8, 16, 32} at fixed budget;
   - LoRA on ["query","value"] vs ["query","value","dense"] (if stable);
   - LoRA-adapted bge-base (large+LoRA) — the base-size control;
   - synthetic-train vs retrieval-only (no adaptation) for the memorisation
     probes G1–G4 (HYPOTHESIS §5).

## Phase 4 — Calibration (dev only)

- Declare `score_kind` per arm (cosine = ranking kind; logits never
  thresholded as probabilities).
- Fit any temperature/isotonic map on train-synthetic scored pairs only;
  select all thresholds on dev; ONE shadow-dev confirmation run with frozen
  thresholds; record `calibration_partition` (sha256 of fitting manifest) in
  `ThresholdPolicy`; freeze everything before private.

## Phase 5 — Dev + shadow-dev confirmation

1. Generator floor check first (orchestration contract): oracle-packet vs
   B4-packet answer quality on dev; ≤5% delta ⇒ generator floors ⇒ STOP and
   report.
2. Per-stage survival metrics (HYPOTHESIS §7), false-negative kill
   attribution, conditioning caveats (denominator=0 ⇒ None, not 0).
3. Generalisation battery G1–G4 (HYPOTHESIS §5) recorded with verdicts.
4. Shadow-dev: one confirmation run, frozen thresholds, no re-tuning.
5. Regime A/B paired delta on the public 21-article superset protocol.

## Phase 6 — Sizes and runtime measurements (replace every ESTIMATE)

- `storage_manifest` for: BM25 index, merged small model fp32 + int8 export,
  adapter artifact (training-time), generator artifact (shared, excluded).
- `timed_phase` for model-load vs inference; `proc_peak_rss_mb` for the
  inference process; per-query latency for bi-encoder and cross-encoder arms.
- Merge-parity under int8 export (ORT): parity gate top-100 rank
  correlation ≥ 0.99 AND final-completion delta ≤ 1 item on 10 dev items;
  else int8 stays deployment-only and fp32 is the reportable path.

## Phase 7 — Readiness gate to the orchestrator

GO/NO-GO per HYPOTHESIS §9. Deliverables preserved: raw traces, run
manifest (seeds, hashes, thresholds, kill_condition), adaptation-data
manifest, gate verdicts, G1–G4 records, ONNX merge-export proof, and the
recorded finding for every ablation — including "the adapter was
unnecessary" or "merging evaporated the advantage" when that is what the
data says.

## Budget and failure handling

- No paid model fallback; no nested subagents. If blocked (gate refuses
  PASS, merge-parity fails, export blocked, stage-0 recall < 0.90), STOP and
  report — never patch around with a paid endpoint or a different generator.
