# KaLM Coarse-to-Fine Cascade — Hypothesis (Mise-en-Place)

Status: READINESS REPORT. No implementation. No private data touched.
Frozen substrate: tag `round0-freeze-r1`, commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`.
All measurements below are DESKTOP. No Android claim.

## 0. One-sentence falsifiable hypothesis

A KaLM-Reranker-V1-Nano-R2 cascade that screens the full candidate set at
128x compression and rescores only the survivors at 4x (then 1x/None for the
final evidence cut) matches single-stage 4x recall on dev/shadow-dev at
strictly lower per-query decoder cost — and it is REFUTED if the 128x stage-0
screen loses more sufficient evidence than the cascade can recover, i.e. if
direct cumulative final recall of the cascade is below single-stage 4x recall
beyond the Wilson-CI overlap on the same dev/shadow-dev items.

## 1. The 128x question, up front

The single most valuable finding of this investigation is that the 128x
question cuts BOTH ways, and the model card answers half of it:

- VERIFIED (model card, BEIR table): Nano-R2 at 128x scores nDCG@10 55.11 vs
  58.75 at 2x on BEIR (93.8% retention), and 66.01 vs 71.63 on MIRACL
  (92.2% retention). At 128x, Nano-R2 (55.11) still beats V1-Nano at 32x
  (52.88) on BEIR.
- NOT VERIFIED: nDCG@10 retention is a RANKING claim over BEIR/MIRACL
  passages. Our tournament metric is SUFFICIENT-SET COMPLETION (binary) over
  Wikipedia paragraphs with conjunctive multi-hop sets. A reranker can retain
  94% of nDCG while systematically dropping the one complementary paragraph
  of a 2-atom sufficient set. Nothing in the card bounds per-stage
  sufficient-set survival at 128x.
- Hence the falsifier that matters: **if 128x retains enough signal to make
  stage-0 loss ≈ 0 on dev sufficient sets, most intermediate stages
  (64x/32x/16x/8x) are removable and the pipeline collapses to 128x → 4x →
  packet.** That two-stage collapse is the highest-value outcome of Round 1
  for this family. If instead 128x bleeds complementary atoms, the
  intermediates are load-bearing and each must earn its storage/compute.
- The dev/shadow-dev experiment that decides it: score every dev
  paragraph-pair at 128x AND 4x, and measure the rank displacement of gold
  sufficient-set members specifically (not mean nDCG). Report turnover@K for
  K in {50, 100, 200, 500}: the fraction of sufficient atoms ranked ≤K at 4x
  but >K at 128x. If turnover@200 ≈ 0, intermediates are removable.

## 2. Exact model ids, revisions, licenses

| Artifact | Id | Revision (pinned) | License | Status |
|---|---|---|---|---|
| Primary reranker | `KaLM-Embedding/KaLM-Reranker-V1-Nano-R2` | `32b242bb7fd7ad6fd404154c09560d249ffe017f` (main HEAD, lastModified 2026-09-23; API-resolved 2026-10-03) | apache-2.0 (card tags + API) | VERIFY-BEFORE-USE: floating `main` tag; re-resolve and re-pin at implementation time, record weight-file sha256 in run manifest |
| Base init | `google/t5gemma-2-270m-270m` | UNRESOLVED — not pinned in this report | VERIFY-BEFORE-USE (license chain of the T5Gemma2 init not checked) | Do not ship until checked |
| Paper | arXiv `2606.22807` (v3 describes the R2 recipe: SFT → soft-label distillation → model soup) | — | — | Prior only, not evidence |
| Stage checkpoints (`Yuki131/...-Stage1`, `...-Stage2-r64-a32`, `...-Stage2-r96-a48`) | NOT USED. Final souped R2 checkpoint only | — | — | Out of scope unless cascade needs a distillation teacher |
| GGUF exports (`...-Nano-Q8_0-GGUF`, `...-Nano-Q4_K_M-GGUF`) | Converted from **V1-Nano, not R2**; fixed chunk size 4; patched-llama.cpp-only runtime | apache-2.0 | VERIFIED INAPPLICABLE to R2 (see §4) |

Weight footprint (VERIFIED from Hub file listing): `model.safetensors`
1,572,182,264 bytes (~1.46 GiB, BF16, 786,029,296 params per API;
card table: 0.27B activated, 100M non-embedding + 168M embedding, 18+18
layers, hidden 640, 128K sequence length, vocab 262144).

Runtime pins required at implementation (from card): `sentence-transformers>=5.6,<6`,
`transformers>=5.3,<6`, PyTorch backend, `trust_remote_code=True`
(custom modeling code — load trusted revisions only).

## 3. Compression factors actually available (with evidence)

Mechanism (VERIFIED from `kalm_reranker_utils.py:pool_encoder_chunks`):
mask-aware mean over each consecutive group of `chunk_size` encoder hidden
states. `chunk_size=None` disables pooling (1x). Any positive int is
accepted by the code; the VALIDATED set is narrower.

| Factor | How selected | Evidence | Status |
|---|---|---|---|
| 1x (none) | `chunk_size=None` | README: "Set `chunk_size=None` to disable compression"; code path `forward_reranker_model(..., encoder_chunk_size=None)` skips pooling | VERIFIED available |
| 2x | `chunk_size=2` | BEIR/MIRACL robustness tables carry a 2x column for all R2 sizes | VERIFIED validated |
| 4x | `chunk_size=4` (default; `kalm_cross_encoder_config.json`) | Default in card, config, vLLM adapter; all headline numbers at r=4 | VERIFIED validated |
| 8x, 16x, 32x | `chunk_size=8/16/32` | Table columns; vLLM adapter explicitly supports `1, 2, 4, 8, 16, 32` | VERIFIED validated |
| 64x, 128x | `chunk_size=64/128` | Table columns (Nano-R2 BEIR 55.88 / 55.11); R2 extends validated max from 32x to 128x | VERIFIED validated **in the Python harness only** — the vLLM adapter caps at 32x |
| Non-powers of two (e.g. 3x, 6x, 96x) | accepted by `pool_encoder_chunks` (any positive int) | Code only; NO card numbers | ASSUMED functional, UNVALIDATED — do not use without a dev check |

"Matryoshka / MEP" in the card means ONE checkpoint serves all ratios
(test-time `chunk_size` switch, no retraining). There is no separate
per-ratio weight set to download.

## 4. Runtime / export feasibility — VERIFIED vs ASSUMED (highest-risk section)

### VERIFIED (blockers, quoted from the primary source)

1. **PyTorch-only.** Card, verbatim: "Only the PyTorch inference backend is
   currently supported; training, ONNX, and OpenVINO are not included in this
   release." `kalm_cross_encoder.py` raises `ValueError` for any
   `backend != "torch"`. There is NO ONNX, NO OpenVINO, NO ExecuTorch, NO
   CoreML/TFLite path for R2. Any mobile plan that assumes a serialised
   R2 graph is assuming something the vendor states does not exist.
2. **No R2 GGUF exists.** The only GGUF conversions
   (`-Q4_K_M-GGUF`, `-Q8_0-GGUF`) are built from **V1-Nano**, pin
   **encoder chunk size 4** ("Runtime boundaries"), require a **patched
   llama.cpp at pinned commit `277a105d`** ("Stock llama.cpp does not
   recognize the `t5gemma2` architecture … Ollama, LM Studio,
   `llama-server` and other stock frontends are not supported"), and offer
   "No … server mode". A cascade cannot run through that artifact: one
   fixed ratio, V1 weights, desktop-class custom binary.
3. **vLLM adapter is experimental, CUDA, single-GPU, and caps at 32x.**
   "Validated with Python 3.12, vLLM 0.19.1 … and CUDA BF16"; supported
   chunk sizes `1, 2, 4, 8, 16, 32`; "not vLLM's native … implementation or
   a complete vLLM-native kernel port". It is a serving convenience for a
   desktop GPU, not a mobile path, and 64x/128x do not survive it.

### VERIFIED (enabler)

4. **The encoder is query-independent, so per-corpus pre-encoding is
   architecturally sound.** In `_predict_batch`, encoder texts are
   `"<Document>: {document}"` while the query enters ONLY the decoder
   prompt (`build_decoder_text(query, instruction, …)`). Encoder hidden
   states therefore depend on (document) alone — encode once per corpus,
   reuse for every query. This is the load-bearing fact the whole cascade
   rests on, and it is verified in code, not assumed.

### ASSUMED (must be proven in implementation)

5. **No shipped pre-encode/cache API.** `KaLMReranker` and
   `KaLMCrossEncoderModule` always run encoder→pool→decoder inline per
   batch. Caching `get_encoder(doc)` outputs (or pooled variants) and
   feeding them to the decoder via `encoder_outputs=BaseModelOutput(...)`
   (the exact hook `forward_reranker_model` already uses) is a SMALL,
   code-verified-plausible change — but it is OUR code, untested, and its
   numerics (cache dtype, padding/mask handling across save/load) must be
   proven bit-faithful against inline scoring before any measurement counts.
6. **"Progressive decompression" is a MISNOMER — state it plainly.**
   Mean-pooling is lossy: 4x states CANNOT be derived from cached 128x
   states. There are exactly three honest designs: (a) cache FULL-RES states
   once, pool per stage on the fly (storage = full, §5 row "1x");
   (b) cache each cascade level separately (storage = sum of rows);
   (c) cache COARSE only and RE-ENCODE survivors at fine levels (storage =
   coarse row; per-query encoder cost returns for survivors). The proposal
   "decompress survivors" without re-encoding is mathematically impossible
   under this pooling — any PLAN.md review must reject it on sight.

### Bottom line for the phone question

As shipped, progressive multi-ratio scoring runs ONLY in a Python
(PyTorch/CUDA-or-CPU) research harness. It does NOT survive export because
there is nothing to export it TO (no ONNX/ExecuTorch path, no R2 GGUF, vLLM
adapter is CUDA-only and ratio-capped). Saying so plainly: **the mobile
story of this family today is "ship the 128x index + run the decoder
per query," and even that requires a phone-capable T5Gemma2
encoder-decoder runtime that does not currently exist.** Desktop tournament:
fully viable. Mobile: blocked at the runtime layer, independent of retrieval
quality.

## 5. Storage model (ALL numbers ESTIMATES unless marked VERIFIED)

VERIFIED constants: hidden size 640 (config + card table); encoder cap 1024
tokens; weights 1,572,182,264 B (Hub listing); corpus 9,979 paragraphs /
297 articles; paragraph text 13,257,320 chars total, avg 1,328, max 3,993
(measured from frozen `corpus/corpus.jsonl`).

ESTIMATE inputs (labelled): encoder tokens ≈ chars/3.5 (tokenizer fertility
UNVERIFIED — T5Gemma vocab is 262k; English Wikipedia typically 3–4
chars/token; MUST be measured at implementation and every table below
recomputed). Per-token state: 640 × 2 B = 1,280 B (bf16) / 2,560 B (fp32).
Corpus tokens ESTIMATE: 13,257,320 / 3.5 ≈ 3.79M. Padding/attention-mask
overhead ignored (understates by a few %).

| Compression | Tokens/unit (avg para, EST) | Bytes/para bf16 (EST) | 297-article corpus (EST) | bf16 fp32× |
|---|---|---|---|---|
| 1x (full) | ~380 | ~486 KB | ~4.8 GB | ~9.7 GB |
| 2x | ~190 | ~243 KB | ~2.4 GB | ~4.8 GB |
| 4x | ~95 | ~122 KB | ~1.2 GB | ~2.4 GB |
| 8x | ~48 | ~61 KB | ~607 MB | ~1.2 GB |
| 16x | ~24 | ~30 KB | ~303 MB | ~607 MB |
| 32x | ~12 | ~15 KB | ~152 MB | ~303 MB |
| 64x | ~6 | ~7.6 KB | ~76 MB | ~152 MB |
| 128x | ~3 | ~3.8 KB | ~38 MB | ~76 MB |

Per-article averages (EST, 33.6 paras/article): full ~16.4 MB bf16;
4x ~4.1 MB; 128x ~128 KB. NOTE: an article is NOT one encoder input —
articles exceed the 1024-token window, so pre-encoding is per
paragraph-chunk (or ≤1024-token article-chunk), never per article-string.
Longest paragraph (3,993 chars ≈ 1,140 EST tokens) slightly exceeds the
1024 cap: truncation policy at the cap is a measured edge case, not a
detail to ignore.

940-article scale tier (ESTIMATE, weaker basis): raw snapshots 100.8 MB /
940 articles (~107 KB/article). Assuming core-like density (44.6 KB
paragraph-text/article over 830 substantive articles after 110 redirect
stubs are excluded): ~37M chars ≈ 10.6M tokens → full bf16 ~13.5 GB;
4x ~3.4 GB; 128x ~106 MB. Scale length distribution UNVERIFIED — remeasure
from `corpus/scale/distractor.jsonl` (117.6 MB) at implementation.

Design consequence: only the 128x index (~38 MB core / ~106 MB scale, bf16)
is phone-plausible in size — and the phone still cannot run the decoder.
Design (a) full-res cache (~4.8 GB core) is desktop-only. The honest
desktop cascade is (b) 128x + 4x caches (~1.25 GB) or (c) 128x cache
(~38 MB) + re-encode survivors.

## 6. Training + calibration plan (dev/shadow-dev only; custodian one-shot)

1. **No architecture training.** The reranker is used FROZEN. "Training" in
   this family = (i) building the pre-encoded index (no QA data, no gate
   needed — corpus text is shared); (ii) generating SYNTHETIC calibration /
   threshold-selection QA from corpus text if needed.
2. **Synthetic data, if any, follows the contract**: generated ONLY from the
   shared corpus; public bounty questions are reference-only, never
   training; every batch passes the custodian leakage gate (`PASS` or
   REJECT + synthetic ids to remove) before use; HONEST LIMITATION carried
   from Round 0 — the hash-only gate is not yet seal-bound and correctly
   refuses PASS, so synthetic batches may be UNUSABLE until the custodian
   binds it. Contingency: threshold selection on dev/shadow-dev question
   TEXT with custodian-scored runs (see §12 ambiguity 1) or purely
   synthetic self-contained pairs.
3. **Regime B**: identical procedure twice; Model B excludes ALL 21 public
   articles (`substrate.query.worker_regime_b_exclusions()`, the ONLY
   sanctioned source) from synthetic adaptation data. Query-time corpus
   identical (21 REMAIN searchable). Manifest must show zero excluded docs
   in adaptation data (`verify_adaptation_exclusion`-style invariant).
4. **Calibration**: P(yes) = softmax([yes_logit, no_logit])[0] is
   `model_probability` (evaluable, NOT certified). ECE/Brier on dev with
   binary sufficient-set-membership labels; if miscalibrated (expected),
   fit temperature (single parameter) or isotonic on DEV ONLY, record
   `calibration_partition` provenance in the trace policy, freeze, and
   report ECE before/after on shadow-dev WITHOUT refitting. Raw absolute
   thresholds per stage are legal with any score_kind; any fitted-calibration
   claim without partition provenance is forbidden by the substrate.
5. **Instruction string** (`DEFAULT_INSTRUCTION = "Given a query, retrieve
   documents that answer the query."`) is a frozen hyperparameter: one fixed
   string for all questions (it is our retriever config, not per-question
   tuning), recorded in the run manifest. Trying >1 instruction = a
   Comparability-relevant choice; freeze ONE before the private run.
6. **Query surface**: `QueryInput(question_id, text)` via `to_model_query`
   ONLY. Stored `question_type` (visible in `corpus/questions.json`, e.g.
   `"multihop"`) MUST NOT reach the model — handing it to any controller
   hands it the decision. `assert_no_label_metadata` on every model-facing
   payload.

## 7. Thresholds and candidate policy per compression level

Policy STYLE (values are SELECTED on dev/shadow-dev, frozen in the manifest
BEFORE the private run — no numbers are pre-declared here):

- Candidate set: ALL 9,979 core paragraphs per question (no BM25 pre-filter
  in the primary arm — the 128x screen IS the pre-filter; a BM25-prefiltered
  arm may run as a diagnostic only). Scale tier: same policy over
  830 substantive scale paragraphs-units for the scale run.
- Stage 0 (128x): score all; keep top-M by P(yes) with M ∈ {200, 500, 1000}
  swept on dev; PLUS an absolute floor (P(129x) ≥ τ₀) so easy questions
  short-circuit with small survivor sets (adaptive compute; decision
  recorded in trace `adaptive_decision`). τ₀ swept on dev, frozen.
- Stage 1 (4x, survivors only): rescore; keep top-N, N ∈ {20, 50, 100}.
- Stage 2 (1x/None, top-N only): rescore for the final rank order; packet =
  ranked-prefix under the 1000-token hard cap toward the 300–800 target
  band via `build_packet(exact=True)` with the pinned tokenizer.
- Fallback arm (the refutation arm): single-stage 4x over the full set.
  The cascade must beat THIS, not BM25.
- Threshold coupling rule: τ at a fine stage is fit CONDITIONAL on surviving
  the coarse stage (selection bias is real — coarse survivors are not a
  random sample); never reuse a single-stage-fitted τ inside a cascade.
- Freeze rule: (M, N, τ₀, τ₁, instruction, chunk sizes) frozen in
  `RunManifest.thresholds` as `ThresholdPolicy` entries; any post-freeze
  change = re-freeze.

## 8. Evidence-survival metrics per stage + false-negative localisation

Mandatory substrate vocabulary (no inventions, no products of marginals):

- Per stage s: `stage_coverage` (fraction of sufficient atoms present in
  stage-s survivors, direct), `conditional_retention` WITH
  numerator/denominator (None when denominator is 0 — undefined, not zero),
  `survival_curve` lineage (pruned stays pruned — assert monotonicity in
  tests), `lost_and_recovered` spans (recovery across stages is a DESIGN
  BUG in a pure cascade; count it, explain it).
- Compound claim = DIRECT cumulative final coverage vs the sufficient sets,
  NEVER the product of per-stage recalls (`compound_survival` stays removed).
- Rates qualified with `wilson_ci`; score_kind on every candidate
  (`model_probability` for P(yes)); ECE/Brier only on finite [0,1] probs
  with binary labels.
- FALSE-NEGATIVE localisation protocol (dev/shadow-dev, via custodian-scored
  or synthetic labels): for each lost sufficient atom, record (stage lost,
  coarse rank, fine rank-if-rescored, margin P(yes) gap to the cut,
  chunk-size sensitivity 128x→4x→1x rank trajectory). Aggregate into a
  loss ledger by question_type × atoms-per-set: the conjunctive-2-atom case
  is the canary (see §1). A stage whose losses concentrate on
  second-atoms-of-pairs is evidence the compression destroys complement
  signals, not just weak signals.
- Stage-0 recall, candidate reduction, final evidence recall, evidence
  token cost, context precision, abstention/sufficiency accuracy, latency /
  peak-RSS / storage manifest per the preregistered metric hierarchy
  (primary = evidence metrics; generated-answer metrics secondary and
  judge-gated — judge digest unpinned, so secondaries may be ABSENT).

## 9. Deterministic unit tests to write (each with what it catches)

1. `test_pool_math`: hand-computed mean over a 4×640 fixture incl. a
   partially-padded chunk vs `pool_encoder_chunks` — catches wrong-axis /
   mask-ignoring pooling (silent quality rot).
2. `test_pool_padding_edge`: all-pad chunk → pooled_mask 0, no NaN division
   (clamp(min=1) path) — catches NaN poisoning of the index.
3. `test_chunk_none_vs_one`: `chunk_size=None` and `chunk_size=1` agree on
   unpadded inputs — pins the 1x definition two teams could split on.
4. `test_encoder_query_independence`: same document × 3 different queries →
   identical encoder hidden states — the load-bearing §4.4 fact, pinned
   against future checkpoint swaps.
5. `test_cache_faithfulness`: cached-encode→pool→decode equals inline
   predict within fp tolerance on a fixed 20-pair fixture — catches any
   drift in OUR cache path (the assumed part of §4).
6. `test_query_boundary`: `to_model_query` on a real stored entry drops
   `question_type`/`split`/`meta`/`provenance`; `assert_no_label_metadata`
   raises on a smuggled payload — catches leakage into the model.
7. `test_survival_monotonicity`: pruned stays pruned across a scripted
   3-stage cascade incl. empty-survivor and all-pruned edges — catches
   lineage bookkeeping bugs.
8. `test_packet_budget`: ranked-prefix packing under the 1000-token cap on
   exact tokens incl. first-span-overflow → empty+truncated=True — catches
   budget overruns reaching the fixed generator.
9. `test_threshold_policy_validation`: bare floats migrate fail-closed;
   score_kind/policy mismatch rejected — catches unprovenanced calibration
   claims.
10. `test_storage_manifest`: index bytes per level predicted from token
    counts within ±15% of measured — catches silent dtype/shape changes in
    the cache format.
11. `test_seed_derivation`: `derive_seed(master, component)` logged and
    reproducible — catches untracked randomness.
12. `test_regime_b_manifest`: adaptation-data manifest contains zero of the
    public 21 — catches Regime-B leakage before the custodian ever sees it.

## 10. Dev / shadow-dev readiness plan ("ready" definition)

- Environment: CPU-only PyTorch + `transformers>=5.3,<6` +
  `sentence-transformers>=5.6,<6` (versions pinned in manifest); NO GPU
  required for mise-en-place (functional 128x/4x/1x agreement checks run on
  CPU; timing runs need the documented desktop CPU + thread pinning).
- Model: `hf download KaLM-Embedding/KaLM-Reranker-V1-Nano-R2`, re-resolve
  `main` → commit SHA, verify weight sha256, record both; assert
  `main != 32b242bb…` triggers a re-verification (floating-tag drift guard).
- Corpus: frozen `corpus/corpus.jsonl` (43.9 MB, 113,951 nodes) + paragraph
  tokenizer-fertility measurement (replaces the §5 chars/3.5 ESTIMATE with a
  measured tokens table — a missing artifact blocks further storage claims).
- READY = (i) tests 1–12 green; (ii) cache-faithfulness proven;
  (iii) measured fertility + storage tables replace §5 estimates;
  (iv) 128x-vs-4x turnover@K pilot on 20 dev questions complete (decides
  whether intermediates survive into the plan); (v) thresholds procedure
  (§7) executable end-to-end on a 5-question smoke run with full
  `StageRecord`/`RetrievalOutcome` traces validating. No private run, no
  private data, no generator tuning at any point.

## 11. Expected mobile blockers, plainly

1. No serialised R2 artifact exists (no ONNX/ExecuTorch/CoreML; torch-only
   enforced in code) — full stop, the pipeline cannot be packaged today.
2. T5Gemma2 encoder-decoder is unsupported by stock llama.cpp/ExecuTorch
   runtimes; the only GGUF is V1/4x-fixed/patched-desktop-llama.cpp.
3. 786M params / 1.57 GB BF16 weights exceed any reasonable phone budget
   before a single index byte is counted; no quantised R2 exists.
4. Realistic phone-side index = 128x ONLY (~38 MB core EST), which forces
   the two-stage-collapse outcome (§1) AND a phone decoder that does not
   exist.
5. 128K training context vs 1024-token document cap: long-paragraph
   truncation behaviour on-device is uncharacterised.
6. vLLM (the only non-naïve server path) is CUDA-single-GPU, capped at 32x,
   experimental — irrelevant to mobile, noted so nobody cites it as one.

## 12. Baseline comparison that justifies the pipeline

Primary: **single-stage KaLM-R2-Nano @4x over the identical candidate set**
(same paragraphs, same instruction, same evidence budget, same fixed
generator). The cascade must show, on dev/shadow-dev with Wilson CIs:
(a) final sufficient-set completion within the pre-declared non-inferiority
margin of the 4x arm, AND (b) strictly lower measured per-query decoder
cost (encoder pre-computation amortised and reported separately, never
folded into per-query latency silently) — or higher completion at equal
cost. Secondary: cascade vs single-stage @128x (proves the fine stages earn
their keep) and vs single-stage @1x (proves compression was worth it at
all). If the cascade cannot beat single-stage 4x on (a∧b), it is
refuted and the family recommendation collapses to "run single-stage 4x,
keep 128x as a cheap-filter option". Generator-floor risk (STATUS.md
accepted risk 3: Qwen2.5-1.5B may not express evidence differences) applies
equally to all arms — check the floor on the first dev run before reading
any answer-metric delta.

## Appendix. Contract ambiguities two teams could implement incompatibly

A. **No worker-visible relevance labels exist for ANY split**
   (`corpus/questions.json` carries no atoms/answers), yet Round 1 must
   "select thresholds on dev/shadow-dev and freeze them". The contract does
   not say HOW: synthetic-QA-only tuning vs custodian-scored dev runs are
   different experiments with different validity. Must be ruled before
   implementation.
B. **Candidate unit is unspecified** (paragraph / sentence / section /
   article-chunk). Recall, survival, and storage numbers are incomparable
   across teams until the unit is fixed. This report assumes PARAGRAPH and
   says so.
C. **Pre-compute attribution**: is index-build latency part of per-query
   cost, amortised capex, or storage-manifest-only? Three teams will report
   three different "latencies" for the same system. Pre-encoding makes this
   load-bearing for THIS family specifically.
D. **1x definition**: `chunk_size=None` vs `chunk_size=1` — identical on
   unpadded inputs, potentially different under padding. Fixed by test 3,
   but the contract does not fix it.
E. **`corpus/regime_b_paired.json` sits in-repo** (public 56-question
   pairing) next to the SECRET 15-item private pairing the contract forbids
   touching. A worker that reads the wrong file commits a custody violation
   by mistake. Tooling should resolve exclusions ONLY via
   `worker_regime_b_exclusions()`.
F. **BEIR/MIRACL retention priors** (§1 card numbers) are out-of-corpus
   claims. The contract neither blesses nor bans their use as design priors
   (fine) vs reported results (must never be). The line needs stating.
G. **`model_probability` vs "calibrated"**: two teams can report the same
   P(yes) numbers with different calibration claims. Require ECE +
   `calibration_partition` provenance with every calibration adjective.
