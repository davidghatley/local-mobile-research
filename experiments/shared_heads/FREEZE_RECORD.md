# Architecture Freeze Record — Family C (shared encoder + multiple heads)

Frozen: **2026-10-04**, immediately after its DEV run and **BEFORE** any
shadow_dev execution. Per `experiments/comparability/CONTRACT.md` and the run
brief's Phase 12, nothing below may change in response to a shadow_dev score. A
mediocre shadow result is a result, not a tuning signal.

This record exists because the alternative — running shadow_dev first and
"just checking" — is how an independent confirmation gets converted into a second
tuning set, at which point it confirms nothing.

## Frozen configuration

| field | value |
|---|---|
| architecture id | `C_shared_heads_17m` |
| git commit (dev run) | `5fe988e6e35080391623d63dac9f9932d27263fe` |
| stage sequence | `bm25` → `heads_coarse` → `heads_fine` → `heads_sufficiency` |
| shared backbone | `cross-encoder/ettin-reranker-17m-v1` |
| backbone revision | `9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` |
| backbone `model.safetensors` | 67,193,928 B, sha256 `f970cbb7ae7f14082852ca6fb91a3171b346bdd9c78e871e1e8a0fdbde98ceb3` |
| `tokenizer.json` | 3,583,327 B, sha256 `28c5e078e4c52aa37cf0e6de1a212878f3dbd58dd1c70466298efe0b6b86db35` |
| quantization | none (fp32) |
| adapters | **NONE.** No LoRA, no PEFT. Family C is adapters-free by construction. |
| training | **NONE. Zero-shot.** No synthetic data, no fine-tuning, no adaptation. |
| training dataset hash | n/a — nothing was trained |
| Regime A/B manifests | n/a — nothing was trained, so the 21-document adaptation exclusion is vacuously satisfied. The 21 articles REMAIN in the query-time corpus. |
| thresholds | **NONE.** Top-K only at every stage. No score threshold is used anywhere. |
| `bm25` stage | `score_kind=similarity`, `top_k=500`, `calibration_method=none_ranking_only` |
| `heads_coarse` stage | `score_kind=rank`, `top_k=50`, `calibration_method=none_ranking_only` |
| `heads_fine` stage | `score_kind=logit`, `top_k=50`, `calibration_method=none_ranking_only` |
| `heads_sufficiency` stage | `score_kind=similarity`, `top_k=50`, `calibration_method=none_ranking_only` |
| candidate limits | stage-0 500; each head stage 50 |
| per-article cap | 3 |
| evidence budget | `build_packet(exact=True, pinned tokenizer, cap=1000)`; tokenizer `gguf-embedded:gpt2-bpe:vocab151936:bos151643:eos151645:addbos0:tplsha-cd8e9439` |
| seed | 20261004 (unused — no component uses randomness) |
| determinism | `torch.set_num_threads(1)`, `set_num_interop_threads(1)`, batch order = BM25 stage-0 rank order, total order by (score desc, node_id asc as UTF-8 bytes) |
| runtime | torch 2.14.1+cpu, transformers 5.18.0, sentence-transformers 6.1.0, Python 3.14.7, Linux x86_64, **CPU only, no CUDA** |
| corpus | `corpus/corpus.jsonl`, revision `pilot-297-r1`, `doc_strings_sha256 93e6b7f1aeb4d92a202da067aa13bb4273554cbf74f55a07c43136deb6e0ec81`, 9,979 paragraph documents |

## Correctness gate already cleared (before freeze)

* Shared-forward fine logits vs the single-head reference path
  (`CrossEncoder.predict`, same 500 pairs): **max abs diff 0.0**.
* One-forward property: the backbone is invoked once per (query, paragraph) pair
  and no head triggers an encoder pass. Structural, not sampled.
* Score-kind honesty: no sigmoid anywhere; no `calibrated_probability` or
  `model_probability` claim on any head.

## DEV result at freeze time

| metric | value |
|---|---|
| stage-0 survival | 70/73 = 0.9589 (identical to BM25 — heads reorder, never add) |
| all three head stages | 70/73 = 0.9589 each (unchanged) |
| **final packet completion** | **64/73 = 0.8767** (B1: 54/73 = 0.7397; **+10 paragraphs, +13.70 pp**) |
| item-level completion | 0.8909 (B1: 0.7636) |
| leaf context precision | 0.1923 (B1: 0.1181) |
| mean exact evidence tokens | 759 (B1: 781) — *fewer* tokens carrying *more* required evidence |
| median latency | 39,636 ms (B1: 36.3 ms) — **1,093×** |
| per-stage median latency | bm25 70.8 ms (0.2%), heads_coarse 39,538 ms (**99.8%**), heads_fine 3.8 ms, heads_sufficiency 7.1 ms |
| weights | 70,777,255 B (B1: none) |

**Registered MMD gate:** dev is 13 items / 22.0 pp. The measured delta is 10 items
/ 13.70 pp, which is **below the dev threshold and therefore UNRESOLVED on dev**.
In percentage terms it exceeds the dev+shadow_dev threshold of 12.3 pp, so the
powered split set is what decides. That is precisely what the single shadow_dev
run is for.

## Shadow_dev protocol (single run, no tuning)

1. Run the frozen configuration above on shadow_dev, retrieval-only, once.
2. Score with `experiments/common/score_all.py` against custodian ground truth.
3. Compare against B1's shadow_dev numbers on the same items and the same budget.
4. **No threshold, breadth, cap or budget may be adjusted afterwards.** A bug may
   be repaired, with provenance recorded; a mediocre score may not be tuned
   against.

## Explicit non-claims

* **No Android, GrapheneOS or on-device number.** Every latency above is desktop
  CPU at `threads=1` on an i7-8700-class host with no CUDA.
* **No calibration claim.** Every stage is ranking-only; `none_ranking_only` means
  these scores may not be thresholded as probabilities.
* **No claim that the three heads are individually useful.** They share one
  encode; the experiment cannot separate which head produced the gain, and does
  not claim to.
