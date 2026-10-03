# Ettin Cascade — Implementation Plan (ordered next steps)

Scope: steps AFTER this readiness report, BEFORE any private run. Owners are
ROLES (orchestrator assigns workers). No step touches private data unless
marked CUSTODIAN. Model-facing inputs are `QueryInput(question_id, text)` only.

1. **Orchestrator rulings on §13 ambiguities** (Owner: orchestrator; BLOCKS
   steps 5–8). Rule on: dev-metric return mechanism (proposal: aggregate rates
   + per-item covered/not-covered flags, no content), scale dual-reporting,
   primary-only refutation, `calibration_partition = sha256 of fitting-set
   manifest`, no multiplied marginals, generator tokenizer governs packet
   budget, `synth-ettin-{regime}-{n}` id namespace.
2. **Re-pin model revisions** (Owner: implementation worker). Re-resolve
   `cross-encoder/ettin-reranker-{17,32,68}m-v1` head SHAs + `model.safetensors`
   sha256 each; record license (Apache-2.0) + base-encoder (MIT) pins in run
   manifest. Observed 2026-10-03 heads are in HYPOTHESIS.md §2 and MUST NOT be
   trusted without re-resolution. Select the strong baseline now: 68M-alone,
   escalating to 150m-v1 (own pin required) if 68M looks weak.
3. **Desktop runtime parity check** (Owner: implementation worker). Load all
   three stages via sentence-transformers (CPU) AND via committed ONNX in ONNX
   Runtime; assert rank agreement (Kendall τ + top-K overlap) and completion
   parity on a toy set before any quality claim. Decides whether ORT is the
   implementation runtime or PyTorch stays the reference with ORT as export
   target. Replaces ESTIMATED sizes (§4) with `measure_storage` /
   `storage_manifest` + `proc_peak_rss_mb` readings.
4. **Generator floor check** (Owner: baseline worker). Deterministic
   BM25→packet→fixed-generator on dev with oracle vs degraded packets through
   the frozen harness. If the generator floors: STOP, report, do not proceed
   to step 5.
5. **Stage-0 + baselines 1–4** (Owner: baseline worker). BM25-alone recall@K;
   lexical+static (`static-retrieval-mrl-en-v1`); BM25+17M-only (load-bearing
   ablation); single-68M. All with per-stage latency/RSS telemetry. Gate: BM25
   recall ≥ 0.90 on dev or fix Stage 0 first.
6. **Cascade v0 (logit + top-K + breadth floor)** (Owner: cascade worker).
   Wire 17M→32M→68M with union keep-rule (§7), `survival_curve` lineage per
   query, kill attribution (§8). No thresholds yet. Compare cost and coverage
   vs step-5 baselines.
7. **Synthetic adaptation data + leakage clearance** (Owner: adaptation worker
   + CUSTODIAN). Generate Regime-A batch per §5; submit to ONE-SHOT custodian
   gate; on PASS, derive Regime-B batch by excluding the public 21 via
   `worker_regime_b_exclusions()` with a manifest proving exclusion. No PASS =
   no adaptation; steps 5–6 stand alone. Any fitted calibration (step 8 v2)
   also waits on data legitimacy, not just code readiness.
8. **Calibration + threshold freeze** (Owner: cascade worker). v0 top-K → v1
   sigmoid/`model_probability` → (optionally) v2 fitted with
   `calibration_partition`. Fit on train-derived pairs, select τ₁/τ₂/τ₃ + B on
   DEV, freeze in manifest. Enforce ≥0.99 conditional retention per non-final
   stage.
9. **Shadow-dev confirmation (ONE run)** (Owner: cascade worker + CUSTODIAN).
   Frozen system, no re-tuning. Divergence beyond Wilson overlap without
   diagnosed cause = NOT READY, report as generalisation finding.
10. **Regime A/B paired comparison** (Owner: evaluation worker + CUSTODIAN).
    A-on-paired, B-on-same-paired, paired delta via `aggregate_paired_delta`.
    Never pool.
11. **§9 unit tests green + readiness checklist** (Owner: cascade worker).
    All nine tests pass; §10 READY criteria (a)–(h) evidenced; report written
    distinguishing MEASURED vs ESTIMATED on every number. Private run only
    after orchestrator lock with all frozen systems.
