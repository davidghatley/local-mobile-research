# Shared Heads (Family C) — Report on the dev --limit 5 Run

Run: `experiments/shared_heads/run_shared_heads.py --split dev --limit 5
--heads coarse,fine,sufficiency`, retrieval-only, 2026-10-04, desktop CPU
(i7-8700-class), `torch.set_num_threads(1)` + `torch.set_num_interop_threads(1)`.
Raw traces: `experiments/artifacts/shared_heads_dev5/traces_C_shared_heads_17m_dev_core.jsonl`
(5/5 pass `validate_trace(allow_estimate=False)`, 0 failures).
Backbone: `cross-encoder/ettin-reranker-17m-v1` @
`9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6`, offline from local HF cache.

Every number below is labelled. Unlabelled numbers do not exist in this file.

## 1. WEIGHTS (MEASURED + DERIVED)

| Quantity | Value | Status |
|---|---|---|
| Total resident params (state-dict sum at load) | 16,863,745 | MEASURED |
| Shared backbone + pooling (modules 0,1) | 16,797,440 | MEASURED (exactly the Hub metadata figure) |
| Native fine head (modules 2,3,4: Dense-256-GELU → LN → Dense-1) | 66,305 | MEASURED |
| Coarse head params | 0 (declared zero-shot readout) | MEASURED (by construction) |
| Sufficiency head params | 0 (declared zero-shot readout) | MEASURED (by construction) |
| `model.safetensors` on disk | 67,193,928 B | MEASURED (HF cache blob) |
| `tokenizer.json` on disk | 3,583,327 B | MEASURED (HF cache blob; never folded into weights) |
| Peak process RSS during run | 822–1466 MB across stages | MEASURED (`peak_rss_mb`; includes torch runtime + shared libs, NOT weights alone) |
| BM25 index posting payload (core, 9,979 docs) | 10,666,728 B | MEASURED (`posting_array_bytes`) |

**Shared-vs-separate parameter ratio: 3.00× DERIVED** — three separate
single-task 17M checkpoints would resident 3 × 16,863,745 = 50,591,235
params; the shared backbone residents 16,863,745 once (backbone amortised,
per-head marginal cost 66,305 / 0 / 0). The ratio is arithmetic from the two
measured counts, not a second measurement.

## 2. LATENCY (MEASURED, per query over BM25 top-500, n=5 dev items)

| Component | qa-dev-11 | qa-dev-12 | qa-dev-13 | qa-dev-14 | qa-dev-15 |
|---|---|---|---|---|---|
| BM25 stage-0 (500) | 52.3 ms | 21.3 ms | 54.0 ms | 35.1 ms | 27.1 ms |
| ONE shared backbone forward (500 pairs) | 22,447 ms | 29,024 ms | 22,147 ms | 31,129 ms | 27,727 ms |
| fine readout + sort | 2.6 ms | 2.4 ms | 2.1 ms | 2.2 ms | 2.4 ms |
| coarse readout + sort | 0.3 ms | 0.3 ms | 0.4 ms | 0.3 ms | 0.2 ms |
| sufficiency readout + sort | 3.9 ms | 6.0 ms | 4.2 ms | 7.6 ms | 6.9 ms |
| total retrieval | 22,509 ms | 29,056 ms | 22,210 ms | 31,176 ms | 27,766 ms |

- Model load (one-time, outside per-query latency): 673.8 ms MEASURED.
- Per-card backbone cost: 44–62 ms MEASURED (length-dependent; real
  ~300-token cards — the 2.6 ms figure from the 20-pair toy probe used
  25-token cards and is NOT representative; it is superseded by this table).
- Backbone latency varies 22–31 s across items (passage-length mix) and the
  box is shared with parallel workers; treat single-query timings as
  ±20% noisy. The RATIO below is robust to that noise because both sides
  scale with the same backbone cost.

**Head-switch cost (MEASURED):** time to produce another head's scores given
the cached shared representation: coarse 0.2–0.4 ms, fine 2.1–2.6 ms,
sufficiency 3.9–7.6 ms. Task switching costs one readout (milliseconds),
not one weight load (674 ms) or one re-encode (tens of seconds).

**Shared-vs-separate compute ratio: ≈3.00× DERIVED** — shared per query =
F + h_fine + h_coarse + h_suff (F ≈ 26.5 s mean backbone, h_* ≈ 0.01 s
combined) vs three separate single-head forwards ≈ 3F. Formula stated beside
the number; the components are the measured table above. A separately
executed 3-process baseline was NOT run (see §5); the arithmetic leaves no
room for it to differ materially since readouts are 4 orders of magnitude
below the backbone.

## 3. CORRECTNESS GATES (MEASURED)

- Parity probe: shared-forward fine logits vs single-head reference path
  (`CrossEncoder.predict`, same 500 pairs): max abs diff **0.0** MEASURED.
  Two batching-fidelity bugs were found and fixed during implementation
  (ragged BM25-order batching; a spurious interleave predict does not apply
  to text pairs) — each had injected ~5e-6 fp noise. The probe now gates at
  0.0 and passes.
- One-forward assertion: backbone module invoked exactly ceil(500/32)
  times per query; no head triggers an encoder pass (by construction;
  backbone call count is structural, not sampled).
- Score honesty: fine=`logit`, coarse=`rank`, sufficiency=`similarity`;
  no sigmoid, no `model_probability`/`calibrated_probability` string in
  non-test code; 5/5 traces validate with `allow_estimate=False`.

## 4. QUALITY PER TASK: NOT YET MEASURED (worker-side)

Per-head stage survival / top-K retention requires custodian-held labels
and is scored by the custodian harness from the submitted per-head stage
traces — it is explicitly NOT computed here. **No ndcg/mrr number is
reported, and no quality win is claimed.** Preregistered expectation
(HYPOTHESIS §5): per-head gaps will fall below the 18-item / 12.3pp
dev+shadow-dev register and be recorded UNRESOLVED AT CURRENT POWER. A null
is a valid result.

## 5. WHAT WAS NOT MEASURED (explicit)

- Per-head retrieval quality (custodian-scored; pending trace submission).
- Full dev (59) and shadow_dev (87) runs (this report covers --limit 5 only).
- A separately executed 3-checkpoint baseline under identical thread config
  (compute ratio is derived from measured components, §2).
- Quantized/int8 variants, ONNX export, or any deployment-format parity.
- Cross-run determinism statistics (single run; re-run bit-equality NOT yet
  demonstrated — the parity probe covers path-equivalence, not re-runs).
- Anything on-device: desktop CPU only; no mobile/Android claim is made or
  implied.

## 6. C vs D (adapter-peft) — STANDING AFTER THIS RUN

Family C's serving claim is now MEASURED numbers, not adjectives: one
16.86M resident, task switch ≤ 7.6 ms, sharing parity 0.0. Family D's claim
(zero-shot quality is insufficient; adaptation needs trained LoRA) is
untouched by this run — C's coarse/sufficiency heads are declared untrained
proxies, and any task where they lose to D's trained adapters beyond the
registered MMD is C's honest boundary, to be recorded when custodian scores
land. No adapters were added (HYPOTHESIS §6 binds); zero-shot only.
