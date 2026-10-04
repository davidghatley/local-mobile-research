# Shared Encoder + Multiple Heads (Family C) — Implementation Plan

Status: PREREGISTERED PLAN. No implementation runs, no private data, no
synthetic data. Frozen substrate `round0-freeze-r1` (`a0e7534`). All DESKTOP
CPU. No Android claim. Zero-shot only.
Companion: `experiments/shared_heads/HYPOTHESIS.md` (the spec).

The system, in build order:

| Stage | Component | Weights | Role |
|---|---|---|---|
| 0 | BM25 top-500 (shared pinned pipeline) | none | candidate set; identical to B1 |
| 1 | ettin-reranker-17m-v1 backbone, ONE forward per pair | 16,797,440 shared | the shared representation (pooled 256-d) |
| 2a | fine head (native Dense→LN→Dense) | 66,305 trained | ranking logit |
| 2b | coarse head (tertile bucket readout) | 0 (proxy) | cheap gate readout |
| 2c | sufficiency head (logit-per-word readout) | 0 (proxy) | allocation-density readout |

## Phase 0 — Pins and environment (gate: every hash recorded or STOP)

1. Confirm the backbone revision resolves to
   `9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` (local HF cache already holds
   this snapshot; offline load, no re-download). Record model id, revision,
   `model.safetensors` sha256 + bytes, `tokenizer.json` sha256 + bytes in
   the run summary. On drift: STOP, re-verify HYPOTHESIS §1, record drift.
2. Record library versions in the run summary: torch (CPU), transformers
   5.18.0, sentence-transformers 6.1.0 (the versions that load this
   checkpoint today). `torch.set_num_threads(1)`, CPU only, eval mode,
   `torch.inference_mode()`.
3. Assert backbone geometry at load: ModernBERT, 7 layers, hidden 256,
   vocab 50368; total params counted from the state dict (expect 16,863,745;
   any other value is RECORDED, not rounded to the expectation). Partition
   recorded: modules `0`,`1` = shared backbone; `2`,`3`,`4` = native head.
4. Verify the fixed generator pin exists (`PROMPT_HASH`) for trace
   validity — the run is retrieval-only (`generator=None`), so generation
   never executes, but every trace still carries the pinned prompt hash.
   EXIT GATE: all pins recorded, or STOP.

## Phase 1 — Shared-forward implementation + parity (gate: bit-exact or STOP)

1. Implement `experiments/shared_heads/shared_heads.py`: stage-0 BM25 via
   `experiments.common.bm25` (STAGE0_K=500, pinned k1/b/tokenizer); pair
   construction `(QueryInput.text verbatim, paragraph p.text verbatim)` —
   the B3 canonical cross-encoder inputs; ONE backbone forward per batch
   through the model's own `preprocess` + modules `0`→`1` with the pooled
   vector cached; heads as pure functions of the cache (fine via modules
   `2`→`3`→`4`; coarse tertile buckets; sufficiency logit-per-word).
   Query surface strictly `to_model_query`; never import
   `experiments.common.custodian_truth` or `experiments.common.oracle`
   (asserted by grep in the verify step).
2. Parity probe (the load-bearing test): manual shared-forward fine logits
   vs the single-head reference path (`CrossEncoder.predict` on the same
   pairs) — max abs diff must be 0.0 (observed 0.0 on a 4-pair probe
   2026-10-04). FAIL → STOP: the sharing implementation is invalid and no
   quality number from it means anything.
3. Score-honesty tests: every emitted stage passes
   `experiments.common.trace.stage_entry` + `topk_policy` construction with
   the HYPOTHESIS §2 score_kinds (fine `logit`, coarse `rank`, sufficiency
   `similarity`); `validate_trace(allow_estimate=False)` green on sample
   traces; no `model_probability`/`calibrated_probability` string appears in
   non-test code (grep).
4. One-forward assertion: instrument the backbone call count for one query —
   exactly ceil(500 / batch_size) module calls, zero per-head encoder calls.
   EXIT GATE: parity 0.0, honesty tests green, or STOP.

## Phase 2 — CLI + retrieval-only runs (gate: traces validate)

1. Implement `experiments/shared_heads/run_shared_heads.py`:
   `--split {dev,shadow_dev} --limit N --heads coarse,fine,sufficiency
   --out DIR` (plus `--tier` default core, `--seed`), reusing
   `experiments.common.runner.run_split` with `generator=None`, the shared
   `Bm25Index`, `PackerContext`, and the exact-tokenizer service (same
   pinned GGUF path as the baseline sweep — token counting is identical for
   every arm). Packing head priority preregistered: fine > sufficiency >
   coarse among emitted heads, recorded in `pack_report`.
2. Run `--split dev --limit 5`: all traces must pass
   `eval.run_format.validate_trace(allow_estimate=False)` with zero
   failures recorded in `failures_*.json`. Any validation error → fix the
   emitter, never the validator.
3. `git status --short` must show additions ONLY under
   `experiments/shared_heads/` (and `experiments/artifacts/` if a cache
   lands there); grep must show no `custodian_truth`/`oracle` import in the
   new files. EXIT GATE: 5/5 valid traces, clean status, or STOP.

## Phase 3 — Cost measurement (gate: every ESTIMATE replaced)

1. From the dev runs record MEASURED: model-load ms, per-query backbone ms
   (500 pairs), per-head readout+sort ms (fine/coarse/sufficiency
   separately), head-switch ms (readout given cache), BM25 ms, peak RSS,
   weight bytes on disk + resident param count, tokenizer bytes (separate
   line, never folded into weights).
2. Compute DERIVED shared-vs-separate ratios (parameters: resident vs
   3×16,863,745; compute: 1 backbone + N readouts vs N full forwards — the
   formula is stated beside the number) from the measured components.
3. Write `experiments/shared_heads/SHARED_HEADS_REPORT.md`: every number
   labelled MEASURED / DERIVED / ESTIMATED / REPORTED; quality per task
   stated as NOT YET MEASURED worker-side (traces submitted for
   custodian scoring); no ndcg/mrr win claim; no mobile claim; unresolved
   items listed explicitly. EXIT GATE: no unlabelled number in the report.

## Phase 4 — Dev + shadow-dev confirmation (custodian-scored)

1. Full `--split dev` and `--split shadow_dev` retrieval-only runs, frozen
   code, frozen heads, no threshold tuning (all policies are top-K by
   design; there is nothing to tune — stated so thresholds cannot drift).
2. Submit per-head stage traces for custodian scoring (per-head survival /
   top-K retention with denominators). Worker never reads labels.
3. Kill-condition check against the §0 register (dev 13/22.0pp;
   dev+shadow_dev 18/12.3pp): gaps below register → recorded NULL /
   UNRESOLVED AT CURRENT POWER. Generator-floor verdict, if run, uses the
   three-way McNemar rule only.
4. Family C vs D comparison recorded per HYPOTHESIS §4 (serving-shape win
   conditions for C, learned-quality boundary where D wins).

## What this plan will NOT do (hard constraints, repeated)

- No fine-tuning, no adapters/LoRA, no synthetic data (leakage gate never
  triggered; recorded, not skipped). The no-adapter statement in
  HYPOTHESIS §6 binds all phases.
- No reading of private questions/labels; no tuning on private results; no
  threshold fitting on shadow-dev.
- No generator invocation (retrieval-only), no prompt/sampling variation.
- No ndcg/mrr improvement reported as a win at any phase.
- No Android or on-device performance claim from any number here.
- No paid endpoint, no subagent spawning, no nested work.
- No modification of substrate/, eval/, corpus/, tests/, scripts/, docs/,
  or any frozen Round 0 file.
