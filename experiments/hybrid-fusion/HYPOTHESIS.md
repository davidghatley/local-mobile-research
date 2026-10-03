# Round 1 Hybrid Fusion — Hypothesis and Mise-en-Place Readiness Report (Experiment Lead E)

Status: MISE-EN-PLACE READINESS ONLY. No implementation, no training, no private
evaluation, no synthetic data. Frozen substrate: tag `round0-freeze-r1`
(commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`).
Worker endpoint: `opencode/longcat-2.5-preview-free` (VERIFIED zero-cost).
No subagents spawned. No paid fallback used.
All measurements and predictions below are DESKTOP. No Android or on-device
claim may be derived from any of this.

Companion file: `experiments/hybrid-fusion/PLAN.md` (the ordered how, with gates).

## 0. Design summary (read this first)

Two design axes, deliberately separated:

- **CHANNEL axis** — what the second retrieval channel is. Candidates: a learned
  sparse (SPLADE-style) encoder, or the static dense embedding the baseline lead
  already pinned. This axis decides *what complementarity is available*.
- **FUSION-MECHANISM axis** — how the two channels' rankings are combined.
  Candidates: Reciprocal Rank Fusion (unsupervised), a learned combiner
  (supervised), CombSUM over normalised scores, Borda count. This axis decides
  *how honestly the combination can be evaluated*.

**HEADLINE configuration: RRF fusion of BM25 + a learned sparse channel
(`opensearch-project/opensearch-neural-sparse-encoding-v2-distill`).**

The headline pairs the channel most likely to be complementary (a learned sparse
encoder that performs MLM-based term expansion — qualitatively different from
both BM25's exact-term matching and the static channel's hashed bag-of-words)
with the fusion mechanism that has *no tuning surface to absorb the channel's
benefit* (RRF is rank-based, parameter-free up to one preregistered constant, and
invariant to monotonic score transformations within each channel). This is the
combination under which the honest null — "fusion added nothing over the best
single channel" — is most detectable, because there is no learned weight that
could silently re-describe a channel that was already strong.

The baseline lead's static-dense channel and every learned-fusion variant are
preregistered as ablations (§2), not silent substitutions.

## 1. Falsifiable hypothesis, refuting comparison, preregistered kill condition

### 1.1 The hypothesis (one sentence)

> Fusing the pinned BM25 lexical channel with a learned sparse (SPLADE-style)
> channel via Reciprocal Rank Fusion recovers required-evidence paragraphs that
> BM25 alone misses — measured as **packet-level disjoint recall** — improving
> sufficient-set completion on dev+shadow-dev by more than the Wilson-CI minimum
> meaningful difference, at a storage and latency cost far below a cross-encoder
> cascade.

### 1.2 The specific refuting comparison

On the frozen dev (59 items) and shadow-dev (87 items), scored through the
preregistered `eval/` harness with custodian-held labels:

- Let `E_i` = the required evidence set for item `i` (paragraph granularity,
  ancestry-aware per `eval/support.py::covers`).
- Let `P_fused` = the final packed packet of the headline system.
- Let `P_bm25` = the final packed packet of B1 (BM25 alone, identical packing).
- **Disjoint recall** = |{e ∈ E_i : e ∈ P_fused AND e ∉ P_bm25}| / |E_i|,
  aggregated over dev+shadow-dev with explicit denominators.
- **Sufficient-set completion** = fraction of items where ANY sufficient set is
  fully present in the packet (binary), plus `best_fractional_coverage`.

The hypothesis is REFUTED if either:
1. The fused system's sufficient-set completion on dev+shadow-dev is **within
   Wilson-CI overlap** of B1's (gap < **18 items = 12.3 pp** on dev+shadow-dev (n=146), Wilson 95% non-overlap, stronger system at a 90% operating point), OR
2. The packet-level disjoint recall of the fused system over B1 is **< 5%** of
   required paragraphs (the baseline lead's own arbiter, adopted here), OR
3. The disjoint recall is > 0 at the candidate-set level but **does not survive
   to the packet** (the recovered paragraphs are crowded out by the ~4-slot
   evidence budget) — i.e. fusion changes the candidate set but not the answer.

A null result inside overlapping intervals is UNDERPOWERED, not equivalence
(STATUS.md accepted risk 2, now QUANTIFIED 2026-10-03: only ~22 pp separable
on dev, ~12 pp on dev+shadow-dev, ~10 pp across all 206 worker-visible items).

### 1.3 Preregistered kill condition

> **KILL CONDITION.** If the headline fused system's sufficient-set completion
> on dev+shadow-dev is within Wilson-CI overlap of B1 (BM25 alone), OR the
> learned sparse channel's packet-level disjoint recall over BM25 is < 5%, then
> fusion added nothing measurable on this corpus and the honest headline is
> "the hybrid is unnecessary — BM25 alone is sufficient at a fraction of the
> cost." This result is recorded in the run manifest under `kill_condition` with
> the Wilson parameters (hits, n, z=1.96) and per-item survival traces, and is
> NOT reframed as "fusion works but BM25 is close."

The kill condition is recorded per the comparability contract §6 protocol:
`kill_condition: {met, system, metric, value, minimum_meaningful_difference,
wilson_ci, per_item_traces}`.

## 2. Fusion-mechanism comparison table

| Mechanism | Needs training? | Tuning surface | Leakage surface | Determinism | Expected cost | Role |
|---|---|---|---|---|---|---|
| **Reciprocal Rank Fusion (RRF)** | No | One constant k=60 (preregistered, standard) | None | Bit-exact (integer ranks) | ~0 (rank arithmetic) | **HEADLINE** |
| Borda count (rank sum) | No | None | None | Bit-exact (integer ranks) | ~0 | Ablation (integer-exact alternative) |
| CombSUM + min-max normalisation | No | Normalisation choice (min-max vs z-score) | None | Float (normalisation-dependent) | ~0 | Ablation (score-norm alternative) |
| Learned combiner (logistic regression on channel scores) | Yes — synthetic questions from corpus | Feature set, regularisation, train/val split | **High** — a dev-tuned weight can absorb the channel it weights | Deterministic given training data, but training data is a tuning surface | Low compute, high protocol cost | Ablation (supervised comparison) |
| Learned sparse channel (SPLADE-style) as the second channel | No (used frozen, off-the-shelf) | None (frozen) | None (no fine-tuning) | Reference-pinned (§4) | ~268 MB fp32 weights + index build | **HEADLINE channel** |
| Static dense channel (baseline lead's pin) | No (used frozen) | None | None | Reference-pinned | ~125 MB fp32 + 40.9 MB doc cache | Ablation (engages baseline lead's argument) |

**Why RRF is the headline.** The load-bearing reason is epistemic, not
engineering: with n=59 dev items and no power calculation, a learned combiner
has almost no data to learn from and a real risk of silently absorbing the
channel's benefit (the brief's explicit warning). RRF has no such surface. RRF
is also **invariant to monotonic score transformations within each channel**,
which means the cross-channel score-normalisation problem — the brief's warning
that "different normalisations change the answer" — **does not arise** for the
headline. Normalisation is a comparability surface only for the CombSUM
ablation, where it is declared and pinned.

**Why the learned sparse channel is the headline second channel.** The baseline
lead argues a *static* semantic channel adds 0–2 points because it is a
smoothed, learned tf-idf over hashed tokens. A SPLADE-style learned sparse
encoder is qualitatively different: it runs an MLM over the text and maps terms
to *related vocabulary terms* (query expansion + document expansion), producing
a sparse vector over the 30,522-token WordPiece vocab. It can match paraphrase
and synonym relations ("nyc" ↔ "new york") that neither exact-term BM25 nor the
hashed static channel can. It stays in the sparse/lexical domain, so it needs no
dense vector index and no 40 MB document cache — its index is an inverted list
over vocab terms, an order of magnitude smaller.

## 3. Exact model ids, revision commits, licences (VERIFIED via Hub API 2026-10-03)

### 3.1 Channels

| Channel | Repo id | Revision (main head, re-resolve at implementation) | Licence | Architecture | Params / size | ONNX shipped? |
|---|---|---|---|---|---|---|
| BM25 (lexical) | — (stdlib, pinned) | — | — | Okapi BM25, k1=1.2, b=0.75 | — | n/a |
| **Learned sparse (HEADLINE)** | `opensearch-project/opensearch-neural-sparse-encoding-v2-distill` | `269e6638b2c4f648996691f6d751495285d8f330` | **apache-2.0** | DistilBertForMaskedLM + SpladePooling (max, relu) | 66,985,530 F32 (~268 MB) | **No** (self-export required) |
| Static dense (ablation) | `sentence-transformers/static-retrieval-mrl-en-v1` | `f60985c706f192d45d218078e49e5a8b6f15283a` | apache-2.0 | StaticEmbedding (EmbeddingBag, mean) | 125,018,208 B table | **Yes** (`onnx/model_int8.onnx` 31,259,319 B) |

All three SHAs were observed via the live Hub API on 2026-10-03 and are
**moving-head observations, NOT freeze pins**. The implementer MUST re-resolve
each repo's commit SHA, record the weight-file sha256, and enter both in the
run manifest before use (PLAN.md Phase 0). No weight bytes were downloaded for
this report; no weight-file sha256 is claimed.

**Peer cross-check (recorded):** the baseline lead's 2026-10-03 observation of
`static-retrieval-mrl-en-v1` @ `f60985c706f192d45d218078e49e5a8b6f15283a` matches
this report's independent observation exactly. No disagreement to record.

### 3.2 Models considered and NOT selected (recorded to prevent silent substitution)

| Model | Reason excluded |
|---|---|
| `naver/splade-v3` @ `fdfeceb91d7b9de7985b38addd3ba9f53a59a355` | **cc-by-nc-sa-4.0 (non-commercial)** — licence incompatible with a deployment story; otherwise architecturally equivalent to the OpenSearch v1 |
| `naver/splade-cocondenser-ensembledistil` / `-selfdistil` | cc-by-nc-sa-4.0; 2022-era; superseded by the v2-distill line |
| `opensearch-project/opensearch-neural-sparse-encoding-v1` @ `708f7e68f4aada15c2d59144a5187c521da6d8db` | BERT-base (133M params, ~440 MB) — 2× the v2-distill size for +0.004 BEIR NDCG@10 (0.524 vs 0.528, README table); the v2-distill is strictly better on the efficiency axis |
| `opensearch-project/opensearch-neural-sparse-encoding-doc-v2-mini` | 23M params but "inference-free" (document-expansion only, no query expansion) — asymmetric; weaker BEIR (0.497) and not a symmetric retrieval channel |
| `opensearch-project/opensearch-neural-sparse-encoding-doc-v3-distill` | Document-expansion only (asymmetric); the v2-distill's symmetric query+document expansion is the better complement to BM25 |

### 3.3 Self-reported quality (from README model-index, NOT verified in our harness)

| Model | BEIR avg NDCG@10 (self-reported) | Source |
|---|---|---|
| `opensearch-neural-sparse-encoding-v2-distill` | 0.528 | README table (13 BEIR subsets) |
| `opensearch-neural-sparse-encoding-v1` | 0.524 | README table |
| `static-retrieval-mrl-en-v1` | 0.503 (NanoBEIR mean) | model-index (baseline lead §4.1) |

These are out-of-corpus priors only, never reported as results. The v2-distill's
0.528 vs the static channel's 0.503 is a weak prior that the learned sparse
channel is the stronger second channel; it is NOT evidence of disjoint recall on
this corpus.

## 4. Runtime + export feasibility (VERIFIED vs ASSUMED)

### 4.1 BM25 (lexical channel)

- **VERIFIED:** stdlib-only (`re`, `unicodedata`, `array`, `struct`). No runtime
  dependency, no export needed. Runs on any platform with a Python interpreter.
- **What breaks on Android/GrapheneOS:** nothing channel-specific. A pure-Python
  BM25 over 9,799 paragraphs is ~10 ms/query on desktop (ESTIMATE); on a phone
  CPU it is slower but still the cheapest channel by orders of magnitude.

### 4.2 Learned sparse channel (`opensearch-neural-sparse-encoding-v2-distill`)

- **VERIFIED (Hub file listing, 2026-10-03):** the repo ships
  `pytorch_model.bin` + `model.safetensors` + `tokenizer.json` + `vocab.txt`.
  **No `onnx/` directory.** No ONNX, no OpenVINO, no ExecuTorch, no GGUF.
- **VERIFIED (README):** encoding = MLM over tokens → max-pool over vocab →
  `log1p(relu(·))` → sparse vector over 30,522 WordPiece terms; similarity =
  dot product of sparse vectors. Query and document are BOTH expanded
  (query-expansion + document-expansion).
- **ASSUMED (NOT verified — named implementation risk):**
  - Self-export to ONNX via `optimum` / `onnxruntime` works and preserves ranking
    quality. The repo ships no ONNX, so this is OUR export path, untested.
  - ONNX Runtime on ARM/Android executes the exported graph. Ecosystem fact
    (ORT ships Android/ARM builds) is not a measurement.
  - Quantised-quality parity (int8 vs fp32 rankings) is an implementation-time
    measurement.
  - Tokeniser parity: the committed `tokenizer.json` (WordPiece) must produce
    byte-identical token streams on-device vs desktop, or scores shift silently.
- **What breaks on Android/GrapheneOS (stated plainly):** (a) no shipped ONNX
  means the entire on-device story rides on an untested self-export; (b) no
  GPU/NPU acceleration is assumed — CPU-only inference of a 67M-param MLM over
  9,799 paragraphs is the index-build cost, and per-query cost is one MLM
  forward pass over the query plus a sparse dot product; (c) GrapheneOS's
  hardened allocator/SELinux policy can break native-library loading paths that
  work on stock Android — untested; (d) the fixed generator (Qwen2.5-1.5B
  Q4_K_M, ~1 GB) dwarfs the sparse channel and is the actual mobile blocker for
  the end-to-end system.

### 4.3 Static dense channel (ablation)

- **VERIFIED (Hub file listing, 2026-10-03):** ships `onnx/model_int8.onnx`
  (31,259,319 B) — the genuinely reduced variant. This is the best mobile story
  of any channel in this report.
- **ASSUMED:** ORT executes the int8 ONNX on ARM/Android with quality parity
  (the baseline lead's §5.4 parity gate applies).

### 4.4 Bottom line for the phone question

The static channel has a shipped int8 ONNX (best mobile story). The learned
sparse channel has NO shipped ONNX (self-export required, untested). The
headline system's mobile story is therefore **weaker than the ablation's** on
the runtime axis — a cost paid for the learned sparse channel's complementarity.
This trade-off is stated plainly and is itself a finding: if the learned sparse
channel's disjoint recall does not clear the 5% arbiter, the static channel's
superior mobile story makes it the better engineering choice, and that is
reported as such.

## 5. Sizes (RAM resident, storage, index build) — MEASURED vs ESTIMATED

Corpus facts (VERIFIED locally against frozen artifacts): 9,979 paragraph nodes
(core), 2,103,768 paragraph words, mean 210.8 words/paragraph. Scale tier:
36,609 paragraph documents (merged core+scale).

### 5.1 Storage per channel

| Component | Core 297 (9,799 paras) | Merged 940 (36,609 paras) | Label |
|---|---|---|---|
| BM25 packed binary index | ~15–40 MB | ~60–160 MB | ESTIMATE (baseline lead §3.4) |
| Learned sparse weights (fp32) | 66,985,530 × 4 B = **267,942,120 B** (~256 MiB) | same (tier-independent) | DERIVED from VERIFIED param count |
| Learned sparse inverted index | ~6–30 MB (EST: 9,799 × 100–500 non-zero terms × ~6 B/posting) | ~22–110 MB | ESTIMATE |
| Static dense weights (fp32) | **125,018,208 B** (VERIFIED) | same | VERIFIED |
| Static dense weights (int8 ONNX) | **31,259,319 B** (VERIFIED) | same | VERIFIED |
| Static dense doc cache (fp32) | 9,979 × 1024 × 4 B = **40,873,984 B** | 36,609 × 1024 × 4 B = **149,950,464 B** | DERIVED |
| Static dense doc cache (int8) | **10,218,496 B** | **37,487,616 B** | DERIVED |

### 5.2 RAM resident (ESTIMATE, replaced by `proc_peak_rss_mb` at implementation)

| Component | Core | Merged | Label |
|---|---|---|---|
| BM25 index + Python overhead | 25–80 MB | 60–160 MB | ESTIMATE |
| Learned sparse weights (fp32, loaded) | ~268 MB + overhead | same | ESTIMATE |
| Learned sparse inverted index | ~6–30 MB | ~22–110 MB | ESTIMATE |
| Static dense weights (fp32) | ~125 MB + overhead | same | ESTIMATE |
| Static dense doc cache (fp32) | ~41 MB | ~150 MB | ESTIMATE |

### 5.3 Index build cost

| Channel | Core 297 | Merged 940 | Label |
|---|---|---|---|
| BM25 | 10–120 s pure-Python | ~3.6× core | ESTIMATE (baseline lead §3.4) |
| Learned sparse (MLM over 9,799 docs) | ~2–10 min CPU (67M-param MLM forward over ~2.3 M tokens) | ~3.6× core | ESTIMATE |
| Static dense (table lookup + mean) | seconds to a minute | ~3.6× core | ESTIMATE (baseline lead §4.4) |

All index-build times are ESTIMATES, replaced by `timed_phase` measurements in
PLAN.md Phase 1/2. The ~1 GB fixed generator is shared by all systems and
excluded from per-system cost.

## 6. Training plan (learned components, synthetic data, leakage gate, regimes)

### 6.1 What is trained and what is frozen

- **BM25:** untuned, stdlib, deterministic. No training.
- **Learned sparse channel (v2-distill):** used **FROZEN**, off-the-shelf. No
  fine-tuning. The only "adaptation" is building the inverted index over the
  pinned corpus (a forward pass over corpus text — no QA data, no labels, no
  leakage gate needed).
- **Static dense channel (ablation):** used FROZEN. No fine-tuning.
- **Learned combiner (ablation A2):** the ONLY trained component. Trained on
  synthetic questions generated from the corpus (§6.2).

### 6.2 Synthetic training data (for the learned-combiner ablation only)

Source: templates over the SHARED corpus text only (`corpus/corpus.jsonl` +
`corpus/scale/distractor.jsonl` text). Procedure: sample a corpus paragraph,
extract 1–2 factual propositions by rule (no LLM authoring for v0), render a
factoid question whose answer is a span in the sampled text, and record the
host node id as the provisional positive. Hard negatives: same-article
non-answering paragraphs + BM25 top-ranked non-answering nodes. Multi-hop
synthetics are a STRETCH variant, not the v0 plan.

**Leakage gate (binding):** EVERY synthetic batch MUST pass the custodian
leakage gate (`data_tools.leakage_check` against the sealed private set) BEFORE
use, in a ONE-SHOT clearance session. The verdict is PASS or REJECT + the
synthetic ids to remove; it never discloses matched private ids/text/answers.
Honest limitation carried from Round 0: the gate's hash-only comparison is not
yet seal-bound, so until the custodian confirms binding, the gate correctly
refuses PASS — NO synthetic data may be used until a PASS is actually issued.
Training on the gate verdict itself (iterating batches against REJECT/accept
signals) is FORBIDDEN: one-shot means one-shot per batch.

Public bounty questions (`public_reference`) are development/reference ONLY,
never training examples. The 206 worker-visible question TEXTS are not training
supervision (no labels are visible) — they may be used as UNLABELED
query-distribution samples only.

### 6.3 Regime A vs Regime B adaptation conditions

- **Regime A:** synthetic adaptation data may use ANY corpus document.
- **Regime B:** the IDENTICAL generation procedure, but ALL 21 articles in
  `corpus/regime_b_excluded_articles.json` (read ONLY via
  `substrate.query.worker_regime_b_exclusions()`) are excluded from the
  synthetic adaptation data. The query-time corpus is IDENTICAL (all 21 remain
  retrievable). The run manifest must carry an adaptation-data manifest proving
  zero excluded-doc membership under Regime B.
- The headline (RRF, no training) is Regime-A ≡ Regime-B BY CONSTRUCTION; the
  21-document exclusion is vacuously satisfied. The learned-combiner ablation
  must produce both regimes and report the paired delta.

### 6.4 Synthetic question_id contract

Synthetic items use the namespace `synth-hybrid-{regime}-{n}`, registered in
the adaptation manifest, rejected by the harness if ever submitted as benchmark
queries (precedent: ettin team §13 proposal).

## 7. Calibration plan (what is calibrated, on what data, on what split)

**The headline (RRF) requires NO calibration.** RRF operates on integer ranks,
not scores, so there is no score threshold, no probability, no ECE/Brier. The
only constant is k=60 (the standard RRF constant), preregistered and untuned.
This is a deliberate design choice: it removes the calibration surface from the
headline entirely.

**The learned-combiner ablation (A2)** produces a weight per channel. That
weight is a RANKING weight, not a probability — it is `score_kind="logit"`-like
and is never thresholded as P(yes). If a probability interpretation is desired
for the ablation, a fixed sigmoid is applied and declared
`score_kind="model_probability"` (evaluable, NOT certified); ECE/Brier may be
reported but no "calibrated" claim is made without `calibration_partition`
provenance. Any fitted calibration (temperature/isotonic) is fit on
TRAIN-derived synthetic pairs ONLY, with the fitting-set manifest sha256
recorded, and thresholds are selected on DEV ONLY and confirmed ONCE on
shadow-dev.

**Thresholds:** the only thresholds in the headline are the top-K cuts (K=500
for stage-0, then the packet budget). These are PINNED by the baseline
specification, not tuned. No dev-selected threshold exists in the headline.

## 8. Evidence-survival metrics per channel and after fusion

All metrics at paragraph granularity (a required sentence survives iff its host
paragraph is in the stage's candidate set; ancestry-aware `covers`). Reported
for EACH channel alone (BM25, learned sparse, static dense) and AFTER fusion:

- `stage_coverage`: DIRECT per-stage fraction of required atoms covered.
- `conditional_retention` WITH numerator/denominator per stage transition
  (None when denominator is 0 — undefined, never zero).
- `survival_curve` lineage (pruned stays pruned — assert monotonicity in tests).
- `lost_and_recovered` spans (recovery across stages is a DESIGN BUG in a pure
  fusion; count it, explain it).
- **Disjoint recall** (the load-bearing metric for this family): for each
  channel and for the fused system, the fraction of required paragraphs
  recovered that the reference channel (BM25) misses. Measured at TWO levels:
  1. **Candidate-set disjoint recall** (does the channel/fusion rank a
     missed paragraph into the top-500?).
  2. **Packet-level disjoint recall** (does the missed paragraph survive the
     ~4-slot evidence budget into the final packet?). The hypothesis is stated
     at the PACKET level; candidate-set disjoint recall that does not survive
     to the packet is recorded as a candidate-set-only win and does NOT count
     toward the hypothesis.
- Final `sufficient_set_completion` (BINARY: 1.0 iff ANY sufficient set fully
  present) + `best_fractional_coverage` diagnostic, `leaf_precision`,
  `overshoot_tokens`, evidence token cost (EXACT tokens, never whitespace).
- **Conjunctive sufficient sets:** for each multi-atom item, track whether ALL
  atoms of a conjunctive set survive TOGETHER. A fused ranking can put the top
  passage first and still fail a two-atom question — the per-atom survival
  rates are reported alongside the conjunctive completion rate, and the gap
  between them is the "conjunctive loss" diagnostic.

**False-negative localisation:** for each dev/shadow-dev item with final
completion 0.0, walk the recorded `survival_curve` backwards from the packet to
Stage 0 and record the FIRST (upstream-most) stage whose `stage_coverage`
dropped the item's ONLY sufficient set below full coverage. Attribute the kill
to that stage with the item id, the stage's threshold/top-K settings, and the
killed passage's rank and score at that stage. Aggregate: per-stage kill counts
+ killed-passage score histograms (are kills near-threshold, i.e. fixable by
loosening the cut, or deep-ranked, i.e. a representation failure?). For the
fused system, a kill is attributed to the FUSION stage if the paragraph was
present in neither channel's top-500 but the fusion promoted it (a fusion
error), or to a channel if the paragraph was in that channel's top-500 but the
fusion demoted it below the cut (a fusion-demotion error). This three-way
attribution (channel-A-only, channel-B-only, fusion-demotion) is the mechanism
that localises whether fusion is helping or hurting.

## 9. Deterministic unit tests (and what each actually catches)

All stdlib `unittest`, zero third-party deps (substrate convention). Each test
names the defect it catches — a test that only proves the code runs is rejected:

1. **`test_rrf_does_not_degenerate_to_single_channel`** (the load-bearing test):
   a synthetic fixture where the sparse channel ranks paragraph X #1 and BM25
   ranks X #500, and paragraph Y is BM25 #1 and sparse #500. Assert the fused
   top-2 contains BOTH X and Y (each promoted by its strong channel). **Catches:
   fusion silently degenerating to a single channel** — if the fused ranking
   equals BM25's ranking, this test FAILS. This is the test that distinguishes
   real fusion from a no-op.
2. **`test_rrf_rank_invariance`**: apply a monotonic transform (e.g. ×1000,
   +7, log) to one channel's scores; assert the fused ranking is unchanged.
   Catches: accidental score-dependence in a rank-based fusion (would indicate
   the implementation is not actually RRF).
3. **`test_rrf_known_vector`**: a hand-computed RRF fixture (3 docs, 2 channels,
   known ranks) → known fused order. Catches: off-by-one rank errors, wrong k,
   tie-breaking bugs.
4. **`test_disjoint_recall_computation`**: a fixture where the fused packet
   contains a paragraph absent from the BM25 packet; assert disjoint recall
   counts it. Catches: disjoint-recall bookkeeping bugs that would hide the
   hypothesis's load-bearing metric.
5. **`test_conjunctive_survival_tracked`**: a 2-atom item where one atom survives
   and the other does not; assert `sufficient_set_completion` = 0.0 and
   `best_fractional_coverage` = 0.5. Catches: reporting per-atom survival as if
   it were conjunctive completion (the exact failure mode §8 warns about).
6. **`test_query_contract_enforcement`**: pass a payload containing `split`,
   `question_type`, `group` to every model-facing entry point; assert
   `ForbiddenMetadataError`. Catches: label-metadata leaks into channel inputs
   (tournament-invalidating).
7. **`test_packet_budget_strict`**: ranked-prefix packing with a hostile span
   list (first span over cap) yields empty packet + `truncated=True`, and NO
   packet ever exceeds the cap on full-serialisation counting. Catches:
   budget-accounting bugs that let oversized packets reach the generator.
8. **`test_pruned_stays_pruned`**: a candidate dropped at stage 1 must not
   appear in any downstream stage output for the same query. Catches:
   stage-plumbing bugs that re-expand the candidate set and invalidate every
   survival claim.
9. **`test_determinism`**: same query twice → identical fused ranking and
   identical packet bytes. Catches: nondeterminism (unpinned threads,
   hash-order iteration) that makes every measured number unreproducible.
10. **`test_regime_b_manifest`**: Regime-B adaptation manifest containing any of
    the 21 excluded articles fails validation; query-time corpus still resolves
    them. Catches: adaptation-data leakage AND the opposite bug (excluding them
    from retrieval, which would fake a Regime-B effect).
11. **`test_kill_attribution_three_way`**: a synthetic trace where a paragraph is
    in the sparse channel's top-500 but the fusion demoted it below the cut;
    assert the kill is attributed to "fusion-demotion", not to the sparse
    channel. Catches: misattribution that sends tuning effort to the wrong
    stage.

## 10. Dev / shadow-dev readiness plan, "ready" definition, NOT-READY triggers

RUN (in order, all on DESKTOP, all through the frozen `eval/` + `substrate/`
harness, generator fixed):

1. **Generator floor check FIRST** (STATUS.md accepted risk 3): run B4
   (BM25 + fixed generator + `decide_default`) end-to-end on dev. If the
   answer-quality delta (oracle packet vs B4 packet) is tested **paired** with
   McNemar's exact test, the comparison is three-way — `I` excludes 0 (no floor,
   proceed) / `I` includes 0 with upper bound below the minimum meaningful
   difference (floor, STOP) / `I` includes 0 with upper bound above it
   (INCONCLUSIVE, underpowered, its own outcome) — and only the middle case stops
   the run. The original "≤ 5% ⇒ floor" rule was superseded: 5% is below what
   this probe can measure, so it would have called a floor what was really an
   underpowered test.
2. **Channel-alone baselines**: BM25 alone, learned sparse alone, static dense
   alone. Record stage-0 recall, disjoint recall vs each other, per-channel
   survival. This is where the baseline lead's 5% arbiter is applied to EACH
   channel.
3. **Headline fusion (RRF)**: BM25 + learned sparse via RRF. Record packet-level
   disjoint recall vs BM25, sufficient-set completion, conjunctive completion,
   per-stage survival, cost.
4. **Ablations**: (A1) BM25 + static dense via RRF; (A2) BM25 + learned sparse
   via learned combiner (only after leakage-gate PASS on synthetic data); (A3)
   BM25 + learned sparse via CombSUM + min-max norm. Each reported win or lose.
5. **Threshold/cut selection on dev** (only for the learned-combiner ablation;
   the headline has no tunable thresholds). Freeze into manifest.
6. **ONE confirmation run on shadow-dev** with frozen cuts. No re-tuning.
7. **Regime A/B comparison** (for the learned-combiner ablation only; the
   headline is A≡B by construction).

"READY" means ALL of: (a) generator floor check shows headroom (oracle >>
degraded); (b) Stage-0 BM25 recall on dev ≥ 0.90 (if Stage 0 cannot see the
evidence, no fusion survives it); (c) the learned sparse channel's candidate-set
disjoint recall over BM25 is measured and reported (the 5% arbiter is the
decision point); (d) the headline's packet-level disjoint recall is measured
with explicit denominators; (e) all §9 unit tests pass; (f) full
storage/latency/RSS telemetry complete (`complete=true`, no None-masquerading
totals); (g) kill attribution runs and attributes 100% of dev false negatives;
(h) the learned-combiner ablation (if run) has leakage-gate PASS and frozen
cuts.

NOT READY if ANY of: generator floors; Stage-0 recall < 0.90; the learned
sparse channel's disjoint recall is < 5% (then the channel is dead weight and
the headline collapses to "fusion unnecessary" — recorded, not hidden); ANY
telemetry field silently unmeasured; leakage-gate PASS not yet issued for the
synthetic batch (then the learned-combiner ablation is blocked, retrieval-only
work proceeds); shadow-dev confirmation diverges from dev beyond Wilson overlap
with no diagnosed cause.

## 11. Expected mobile blockers (stated plainly)

1. **The GENERATOR dominates the mobile story** (~986 MB GGUF + llama.cpp
   server) and is out of this experiment's scope — fusion only shrinks the
   retrieval leg. Any end-to-end on-device claim must clear the generator first.
2. **The learned sparse channel ships NO ONNX.** The entire on-device story for
   the headline channel rides on an untested self-export via `optimum`. This is
   the single largest runtime risk in the headline design.
3. **The static dense channel has a shipped int8 ONNX** (31 MB) — a better
   mobile story than the headline channel. If the learned sparse channel's
   disjoint recall does not clear the 5% arbiter, the static channel is the
   better engineering choice on the runtime axis, and that is reported.
4. **No GPU/NPU acceleration is assumed** — CPU-only inference everywhere.
   Desktop latency numbers predict NOTHING about phone latency.
5. **GrapheneOS-specific native-library loading, background-execution limits,
   and thermal throttling** under sustained MLM inference are all unmeasured.
6. **Tokeniser parity:** the committed `tokenizer.json` (WordPiece) on desktop
   vs on-device pre-processing must produce byte-identical token streams or
   sparse weights shift silently.
7. **Index build on device:** building the learned sparse inverted index
   requires a 67M-param MLM forward pass over 9,799 paragraphs. On a phone
   this is minutes of CPU and a thermal event; the index is therefore a
   build-once-ship artifact, not an on-device build. The static channel's
   index build is cheaper (table lookups only).

## 12. Baseline comparison (what the hybrid must beat) + kill condition

Ordered by increasing strength; the hybrid must justify itself against EACH,
and the comparison harness (corpus, splits, evidence budget, fixed generator,
prompt, seeds, primary metrics) is identical across all:

1. **B1 (BM25 alone)** — the lexical floor. The headline must beat B1 on
   sufficient-set completion by more than the Wilson-CI minimum meaningful
   difference (**18 items = 12.3 pp** on dev+shadow-dev (n=146), Wilson 95% non-overlap, stronger system at a 90% operating point). **This is the primary kill
   condition** (§1.3).
2. **B4 (BM25 + fixed generator, no reranker)** — the true floor. If B4 matches
   the hybrid within Wilson-CI overlap, the hybrid is unnecessary.
3. **B2 (BM25 + static dense, Borda)** — the baseline lead's semantic fusion.
   The hybrid must show that the LEARNED SPARSSE channel's disjoint recall
   exceeds the STATIC channel's by a measurable margin; if the static channel
   performs equivalently, the learned sparse channel's extra cost (no shipped
   ONNX, MLM index build) is unjustified and that is reported.
4. **BM25 + 17M reranker (single tiny cross-encoder)** — the cheapest neural
   reranker point. If this matches the hybrid, the hybrid's second channel is
   unnecessary.
5. **B3 (68M reranker ceiling)** — the expensive-but-simple ceiling. The hybrid
   must approach B3's completion at a fraction of the storage/latency, OR show
   that B3's completion is itself within Wilson-CI of B1 (in which case the
   whole neural cascade is unnecessary and the hybrid's modest gain over B1 is
   the honest ceiling).

**The kill condition that a simple BM25 configuration matching this system would
make the family unnecessary:** if B1 (BM25 alone, identical packing, identical
generator) achieves sufficient-set completion on dev+shadow-dev within Wilson-CI
overlap of the headline fused system, THEN the hybrid fusion family is
unnecessary on this corpus. This is recorded in the run manifest under
`kill_condition` with the full Wilson parameters and per-item traces, and is
NOT reframed. The honest null — "fusion added nothing over the best single
channel" — is a first-class outcome, not a failure to be hidden.

## 13. Verification log (this report)

- 2026-10-03, Hub API: `opensearch-project/opensearch-neural-sparse-encoding-v2-distill`
  (sha `269e6638b2c4f648996691f6d751495285d8f330`, lastModified 2025-06-30,
  license apache-2.0, DistilBertForMaskedLM, 66,985,530 F32 params, siblings —
  NO onnx/ directory, README with BEIR table + encoding procedure,
  `1_SpladePooling/config.json` = max/relu, `modules.json` = MLMTransformer +
  SpladePooling) — all VERIFIED.
- 2026-10-03, Hub API: `opensearch-project/opensearch-neural-sparse-encoding-v1`
  (sha `708f7e68f4aada15c2d59144a5187c521da6d8db`, apache-2.0, BertForMaskedLM,
  132,955,706 params, NO onnx/) — VERIFIED; recorded as the larger alternative.
- 2026-10-03, Hub API: `naver/splade-v3` (sha
  `fdfeceb91d7b9de7985b38addd3ba9f53a59a355`, **cc-by-nc-sa-4.0**) — VERIFIED;
  excluded for licence.
- 2026-10-03, Hub API: `sentence-transformers/static-retrieval-mrl-en-v1`
  (sha `f60985c706f192d45d218078e49e5a8b6f15283a`, lastModified 2025-01-17,
  apache-2.0, siblings incl. `onnx/model_int8.onnx`) — VERIFIED; matches the
  baseline lead's independent observation exactly.
- 2026-10-03, Hub API: `opensearch-project` author search (8 neural sparse
  models enumerated; v2-distill selected, v1/doc-v2-mini/doc-v3-distill
  recorded as considered-and-excluded with reasons).
- No weight bytes were downloaded; no sha256 of any weight file is claimed in
  this report. No private question, label, review, or authored artifact was
  read. No Android claim anywhere in this file.
