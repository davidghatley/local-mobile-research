# Ettin Cascade — Hypothesis and Readiness Report (Round 1 Experiment Lead A)

Status: MISE-EN-PLACE READINESS ONLY. No implementation, no training, no private
evaluation. Frozen substrate: tag `round0-freeze-r1`
(commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`).
Worker endpoint: `opencode/muse-spark-1.3-contributor-free` (verified zero-cost).
No subagents spawned. No paid fallback used.

Prior shared evidence this report builds on (not re-verified here):
`docs/model-feasibility.md` (Round 0 feasibility worker, 2026-09-29) verified the
six official `cross-encoder/ettin-reranker-*-v1` checkpoints exist. This report adds
fresh per-model API observations dated 2026-10-03 and the cascade-specific plan.

## 1. EXACT HYPOTHESIS (falsifiable)

A three-stage cascade of tiny specialised rerankers over deterministic high-recall
retrieval — BM25 (+ optional static semantic prefilter) → 17M coarse relevance →
32M section refinement → 68M fine relevance → evidence packet → FIXED generator —
achieves required-evidence completion and final evidence recall on dev/shadow-dev
**at least equal to** a single large reranker baseline (the 68M reranker applied
directly to the full Stage-0 candidate set, same evidence budget, same fixed
generator), while scoring each query against **fewer total reranker parameters ×
candidates** (i.e. lower estimated rerank FLOPs per query) than that baseline.

The specific comparison that would REFUTE it: on the frozen dev set
(59 items) and the shadow-dev set (87 items), scored through the preregistered
`eval/` harness with custodian-held labels, the full 17M→32M→68M cascade fails to
match the single-68M-reranker baseline on required-evidence completion by more
than the Wilson-interval overlap — i.e. the cascade's completion is lower and the
95% Wilson CIs do not overlap — OR the cascade's measured desktop rerank cost
(latency × parameter-candidates, `substrate.telemetry.timed_phase` per stage) is
not lower than the baseline's. Either outcome refutes the hypothesis as stated.
A null result inside overlapping intervals is UNDERPOWERED, not equivalence
(STATUS.md accepted risk 2: no power calculation exists for 59/87 items).

Sizes 17M/32M/68M are NOT assumed optimal. §12 makes the BM25+17M-only
configuration a first-class ablation: if it nearly matches the full cascade,
that IS the headline result.

## 2. MODEL IDENTITIES

Canonical cascade candidates — the official `cross-encoder` organisation line
(documented base, documented head, documented loss):

| Stage role | HF repo id | Base encoder | License | Params (Hub-computed, MEASURED via API) |
|---|---|---|---|---|
| Stage 1 coarse | `cross-encoder/ettin-reranker-17m-v1` | `jhu-clsp/ettin-encoder-17m` (MIT-tagged) | Apache-2.0 | 16,797,440 |
| Stage 2 refine | `cross-encoder/ettin-reranker-32m-v1` | `jhu-clsp/ettin-encoder-32m` (MIT-tagged) | Apache-2.0 | 31,883,136 |
| Stage 3 fine | `cross-encoder/ettin-reranker-68m-v1` | `jhu-clsp/ettin-encoder-68m` (MIT-tagged) | Apache-2.0 | 68,144,640 |

Architecture (all three, verified from live API `config`: `architectures:
["ModernBertModel"]`, `model_type: modernbert`): ModernBERT encoder with a
single-logit ranking head `Pooling(cls) -> Dense(256,256,GELU,no-bias) ->
LayerNorm -> Dense(->1)`, trained with MSELoss. Output is a RAW LOGIT, not a
calibrated probability — every cascade stage needs calibration work (§6).
Max 7999 tokens per card (Round 0 feasibility). All three list
`sentence-transformers` as `library_name` (CrossEncoder class) and
`text-ranking` pipeline.

REVISION COMMITS — VERIFY-BEFORE-USE. On 2026-10-03 the live Hub API returned
these `sha` (main-branch head) values:

| Repo | Observed head SHA (2026-10-03, UNPINNED head, NOT a freeze pin) |
|---|---|
| `cross-encoder/ettin-reranker-17m-v1` | `9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` |
| `cross-encoder/ettin-reranker-32m-v1` | `b33e5ceb5110773ea9cf5e00c9bedc83a8c2afdd` |
| `cross-encoder/ettin-reranker-68m-v1` | `d166fa88ddde3c42bc3ee92f7df476d941c8204a` |

These are moving-head observations, NOT pinned revisions: the Hub can advance
`main` at any time. DO NOT implement against these SHAs without re-resolving.
Before any implementation run, the implementer MUST re-resolve each repo's
commit SHA, record the weight-file (`model.safetensors`) sha256, and enter both
in the run manifest. No weight bytes were downloaded for this report; no
sha256 is claimed. `docs/model-feasibility.md` §10 already records that no
commit-SHA revisions were pinned in Round 0 — this gap is carried, not closed.

NOT selected (recorded to prevent silent substitution):

- `cross-encoder/ettin-reranker-150m-v1` / `-400m-v1` / `-1b-v1`: official line,
  but 150M+ exceeds the cascade's per-stage mobile budget; 150M serves as the
  SINGLE-STRONG baseline alternative if 68M-alone proves too weak to be a
  meaningful upper bound. 1B has no ONNX/OpenVINO export (desktop
  teacher/reference only).
- Community MS-MARCO fine-tunes (`tomaarsen/ms-marco-ettin-{17,32,68,150}m-reranker`,
  `bansalaman18/*-{bce,ranknet,listnet}`, `kdhole/*1b*`): low-download,
  quality-unverified, mixed losses (BCE/RankNet/ListNet vs the official MSELoss
  line). Excluded for provenance cleanliness: one organisation, one loss, one
  head design across all three stages. If the official line underperforms,
  `tomaarsen/ms-marco-ettin-68m-reranker` (MarginMSELoss, MS-MARCO) is the named
  fallback candidate — adoption requires its own revision pin and a recorded
  justification, never a silent swap.
- Strong-reranker baseline/teacher options (desktop only, never mobile
  candidates): `Qwen/Qwen3-Reranker-0.6B` (595.8M) / `Qwen/Qwen3-Reranker-4B`
  per `docs/model-feasibility.md` §6. Teacher choice is an implementation
  decision; this report does not make it.

## 3. RUNTIME + EXPORT FEASIBILITY (verified vs assumed)

VERIFIED (live Hub file listings, 2026-10-03; sibling lists for 17m and 68m
returned verbatim, 32m identical in tags):

- All three cascade repos ship committed `onnx/` directories: `model.onnx`,
  `model_O1.onnx` … `model_O4.onnx` (optimised variants), PLUS quantised
  variants `model_qint8_arm64.onnx`, `model_qint8_avx512.onnx`,
  `model_qint8_avx512_vnni.onnx`, `model_quint8_avx2.onnx`.
- All three ship committed `openvino/` directories: full
  (`openvino_model.xml/.bin`) and `qint8_quantized` variants.
- Tags on all three include `onnx`, `openvino`, `endpoints_compatible`.
- `sentence-transformers` CrossEncoder loader is the documented runtime path
  (desktop reference path; CPU-capable).

ASSUMED (explicitly NOT verified — each is a named implementation risk):

- ONNX Runtime on ARM/Android executes these graphs. Ecosystem fact (ORT ships
  Android/ARM builds) is not a measurement. The committed `model_qint8_arm64.onnx`
  is an ADVERTISED artefact, not a tested one. No inference has been run in ANY
  runtime for this report.
- The O1–O4 optimisation levels and the qint8/quint8 quantisations preserve
  ranking quality within tolerance. Nothing in the listing proves
  quality-parity; the readiness plan (§10) requires a desktop ORT-vs-PyTorch
  parity check (rank correlation + completion delta) before any mobile claim.
- SIMD behaviour: AVX2/AVX512/VNNI artefacts target x86 desktops; the ARM64
  artefact targets mobile. Which kernels actually dispatch on GrapheneOS
  hardware is UNMEASURED.
- ExecuTorch: NO verified export path for ModernBERT cross-encoders found.
  Assume BLOCKED until an implementation run demonstrates export.
- llama.cpp: NO verified path. llama.cpp's reranking support covers
  BERT-family embeddings; a ModernBERT CrossEncoder with a
  Pooling→Dense→LayerNorm→Dense head is not a documented llama.cpp rerank
  target. Assume BLOCKED; the cascade's runtime story is ONNX Runtime (or
  OpenVINO on x86), not llama.cpp.
- Tokeniser on-device: the WordPiece-style ModernBERT tokeniser
  (`tokenizer.json` committed in each repo) must ship inside the mobile bundle;
  tokenisation cost and correctness parity (Python tokenisers vs ORT-token
  pre-processing) are unmeasured.

What would break on Android/GrapheneOS (stated plainly): (a) no GPU/NPU
acceleration is assumed — CPU-only ORT with int8 quantisation is the only
story with a committed artefact; (b) GrapheneOS's hardened allocator/SELinux
policy can break native-library loading paths that work on stock Android —
untested; (c) three separate model loads (17M+32M+68M) multiply cold-start
latency and peak RSS unless stages are loaded sequentially and released, which
is itself untested; (d) the fixed generator (Qwen2.5-1.5B Q4_K_M, ~986 MB,
llama.cpp CPU server) dwarfs the rerankers and is the actual mobile blocker
for the END-TO-END system — the cascade only shrinks the retrieval leg.

## 4. SIZES (measured vs estimated — labelled per number)

MEASURED (live Hub API, 2026-10-03):

| Model | Params (safetensors metadata) | Repo `usedStorage` (all files incl. ONNX/OpenVINO) |
|---|---|---|
| 17m | 16,797,440 | 455,213,212 B (~434 MB) |
| 32m | 31,883,136 | 863,597,989 B (~824 MB) |
| 68m | 68,144,640 | 1,845,309,911 B (~1.76 GB) |

`usedStorage` is the whole-repo footprint (fp32 safetensors + all ONNX/OpenVINO
variants), MEASURED but NOT the deployment size: the deployed artefact is ONE
runtime file per stage (e.g. one quantised ONNX each). Round 0 feasibility notes
17m fp32 safetensors ≈ 67 MB.

ESTIMATED (do not quote as measurements; implementation must replace with
`substrate.telemetry.measure_storage` / `storage_manifest` + `proc_peak_rss_mb`
readings):

| Component | Estimate | Basis |
|---|---|---|
| 17m fp32 weights resident | ~67 MB | Round 0 feasibility §1 |
| 32m fp32 weights resident | ~128 MB | linear in params (32/17 × 67 MB) |
| 68m fp32 weights resident | ~272 MB | linear in params (68/17 × 67 MB) |
| 17m int8 ONNX resident | ~17–25 MB | 1 B/param + ORT overhead, rough |
| 32m int8 ONNX resident | ~32–45 MB | ditto |
| 68m int8 ONNX resident | ~68–90 MB | ditto |
| BM25 index (113,951 corpus nodes, stdlib) | ~50–150 MB disk/RAM | rough; measured at implementation |
| Cascade int8 total (all three, sequential load) | peak ~68–90 MB + overhead | only one stage resident at a time |
| Cascade int8 total (all three, simultaneous) | ~120–160 MB + overhead | cold-start worst case |

Corpus scale facts (MEASURED locally): `corpus/corpus.jsonl` = 113,951 nodes;
`corpus/questions.json` = 206 items. Stage-0 BM25 scans the full node set per
query on CPU — its latency, not its size, is the desktop cost to watch.

## 5. TRAINING PLAN (synthetic questions, leakage gate, regimes)

Source of synthetic training questions: templates over the SHARED corpus text
only (`corpus/corpus.jsonl` + `corpus/scale/tier_1k.json` text). Procedure:
sample a corpus article/section, extract 1–2 factual propositions by rule (no
LLM authoring needed for v0; LLM paraphrase only as a later variant), render a
factoid question whose answer is a span in the sampled text, and record the
host node id as the provisional positive. Hard negatives: same-article
non-answering sentences + BM25 top-ranked non-answering nodes. Multi-hop
synthetics (bridge-entity pairs across linked articles via `links` DAG) are a
STRETCH variant, not the v0 plan — single-hop factoids first, because the
cascade's job is evidence survival, not hop reasoning.

What the leakage gate requires: EVERY synthetic batch MUST pass the custodian
leakage gate (`data_tools.leakage_check` vs the sealed private set) BEFORE use,
in a ONE-SHOT clearance session the custodian opens — the team submits the
synthetic batch, the custodian returns PASS or REJECT + the synthetic ids to
remove, never matched private ids/text/answers. Honest limitation carried from
Round 0: the gate's hash-only comparison is not yet seal-bound, so until the
custodian confirms binding, the gate correctly refuses PASS — NO synthetic data
may be used for adaptation until a PASS is actually issued. Training on the gate
verdict itself (e.g. iterating batches against REJECT/accept signals to probe
the private set) is FORBIDDEN: one-shot means one-shot per batch, and repeated
resubmission of near-identical batches is a probing attack, not development.

Public bounty questions (`public_reference`): development/reference ONLY, never
training examples, per contract §5. The 206 worker-visible question TEXTS are
likewise not training supervision for the rerankers (no labels are visible
anyway) — they may be used as UNLABELLED query-distribution samples (e.g. query
length/term statistics for BM25 tuning) but never as scored training pairs.

Regime A vs Regime B adaptation conditions (contract §4):

- Regime A: synthetic adaptation data may use ANY corpus document.
- Regime B: the IDENTICAL generation procedure, but all 21 articles in
  `corpus/regime_b_excluded_articles.json` (read ONLY via
  `substrate.query.worker_regime_b_exclusions()`) are excluded from the
  synthetic adaptation data. The query-time corpus is IDENTICAL (all 21 remain
  retrievable). The run manifest must carry an adaptation-data manifest proving
  zero excluded-doc membership under Regime B.
- The worker list is the public 21-document SUPERSET; the team must never
  attempt to derive which 13 are the private ones. Any analysis that partitions
  results by excluded-vs-included articles to infer the private 13 is
  FORBIDDEN.

## 6. CALIBRATION PLAN (P(yes)-style scores, splits, thresholds)

Score semantics starting point: the Ettin reranker head emits a raw logit
(MSELoss, single-logit). That is `score_kind="logit"`: legal for RANKING,
never a probability, never an ECE/Brier input, never directly thresholdable as
P(yes) (`substrate/types.py::validate_score_value`). There is no P(yes) head on
these checkpoints — any "P(yes)-style" score must be CONSTRUCTED, then proven.

Calibration path (in order):

1. v0 (no calibration claim): rank with raw logits, prune with TOP-K only
   (`score_kind="logit"`, threshold policy `kind="top_k"`). No probability
   language anywhere. This is the honest starting configuration.
2. v1 (model_probability WITHOUT fitted claim): apply a fixed sigmoid to map
   logits to [0,1] for thresholding convenience, declared as
   `score_kind="model_probability"` per the contract's evaluable-uncalibrated
   state. ECE/Brier may be REPORTED (they accept [0,1] probabilities) but no
   "calibrated" claim is made, and thresholds on these scores are legal
   dev-selected thresholds, not certified-calibrated decisions.
3. v2 (fitted calibration, only if v1 thresholds look lossy): temperature
   scaling or isotonic regression fitted on TRAIN-split synthetic scored pairs,
   with `calibration_partition` provenance recorded (the exact field format is
   an ambiguity — see §13; proposal: `sha256` of the fitting-set manifest).
   Certified calibration claims REQUIRE this provenance
   (`ThresholdPolicy.validate()` enforces it).

Data and splits: fit calibration maps on TRAIN-derived synthetic pairs ONLY
(60 train questions' query distribution may inform sampling; labels never enter
because none are visible). Select ALL thresholds on DEV (59 items, custodian
scoring). Confirm ONCE on shadow-dev (87 items). Thresholds are frozen in the
run manifest BEFORE any private run (contract §6). Shadow-dev is NOT a second
tuning set: if dev-selected thresholds fail on shadow-dev, that is a
generalisation finding to REPORT, not a licence to re-tune (re-tuning on
shadow-dev demotes it to dev and must be recorded as such).

## 7. THRESHOLDS AND CANDIDATE POLICY (recall-first early stages)

Policy principle: early stages buy recall, late stages buy precision. A
required leaf destroyed at Stage 1 can never be recovered downstream
(`survival_curve` lineage is uninterrupted: pruned stays pruned), while passing
a few extra losers forward costs only compute. Therefore every pre-final stage
uses a UNION keep-rule:

> KEEP a candidate at a non-final stage iff (score > stage_threshold) OR (rank
> ≤ stage_top_k) OR (needed to satisfy the per-source breadth floor).

Per-source breadth floor: at least B candidates per distinct article among the
Stage-0 set survive each non-final stage (proposed B=2, dev-tunable), so a
single article's passages can never be wiped out by a globally miscalibrated
threshold. The final (68M) stage uses a stricter rule (threshold AND top-K cap
sized to the evidence budget: ranked-prefix packing under the 1000-token hard
cap, targeting the 300–800 band, via `substrate.evidence.build_packet` with
`exact=True` and the pinned tokenizer).

Proposed starting grid (PROPOSED, dev-fitted, not claimed):

| Cut | Stage-0 BM25 | Stage 1 (17M) | Stage 2 (32M) | Stage 3 (68M → packet) |
|---|---|---|---|---|
| top-K | 500 | 200 | 50 | 10 spans |
| threshold | none (rank only) | logit τ₁ (low; dev-fit) | logit τ₂ (dev-fit) | τ₃ (dev-fit, strict) |
| breadth floor | n/a | B=2/article | B=2/article | none (budget rules) |

τ₁ is deliberately set for ~0.99 stage-conditional retention on dev even at
the cost of passing 200 forward: Stage 1's job is deleting obvious junk, not
finding answers. Ablations move each cut independently (§10).

## 8. EVIDENCE-SURVIVAL METRICS (per stage) + FALSE-NEGATIVE LOCATION

Reported at EVERY stage (shared vocabulary, `eval/support.py` + telemetry):

- `survival_curve`: uninterrupted lineage of each required atom's host leaf
  through stages (pruned stays pruned — the lineage primitive).
- `stage_coverage`: DIRECT per-stage fraction of required atoms covered
  (ancestry-aware `covers`: retrieving a parent paragraph SATISFIES support).
- `conditional_retention` WITH numerator/denominator per stage transition
  (None rate when denominator is 0 — undefined, never zero).
- `lost_and_recovered`: spans lost then re-surfaced (expected to be ~empty for
  a strict cascade; non-empty values flag re-expansion stages).
- Final `sufficient_set_completion` (BINARY: 1.0 iff ANY sufficient set fully
  present) + `best_fractional_coverage` diagnostic, `leaf_precision`
  (exact-hits granularity penalty), `overshoot_tokens`, evidence token cost
  (EXACT tokens, never whitespace estimates).

NEVER products of marginal recalls: `compound_survival` was REMOVED from the
substrate as invalid. The brief's "0.97^4 ≈ 0.885" arithmetic is illustrative
of compounding risk, not a metric — the reported compound quantity is the
DIRECT cumulative coverage (final completion), and stage budgets are set from
measured conditional retentions, not multiplied targets. Concretely: each
non-final stage must demonstrate ≥0.99 conditional retention on dev
(numerator/denominator shown); a stage below that fails its gate and its
threshold/top-K is loosened before any downstream work proceeds.

Locating FALSE NEGATIVES (which stage destroyed the sole answering passage):
for each dev/shadow-dev item with final completion 0.0, walk the recorded
`survival_curve` backwards from the packet to Stage 0 and record the FIRST
(upstream-most) stage whose `stage_coverage` dropped the item's ONLY sufficient
set below full coverage. Attribute the kill to that stage with the item id,
the stage's threshold/top-K/breadth settings, and the killed passage's rank and
score at that stage. Aggregate: per-stage kill counts + killed-passage score
histograms (are kills near-threshold, i.e. fixable by loosening τ, or
deep-ranked, i.e. a representation failure needing adaptation data?). This
attribution is implementable from stage traces WITHOUT label visibility at
implementation time — it needs custodian-scored harness output, which is a
process dependency (see §13 ambiguity 1).

## 9. DETERMINISTIC UNIT TESTS (what each one actually catches)

All stdlib `unittest`, zero third-party deps (substrate convention). Each test
below names the defect it catches — a test that only proves the code runs is
rejected:

1. `test_stage0_recall_floor`: BM25 over the pinned corpus on a FIXED toy
   corpus snapshot must return a hand-listed required node in top-K.
   Catches: tokeniser/stemming regressions that silently zero recall.
2. `test_pruned_stays_pruned`: a candidate dropped at Stage 1 must not appear
   in any downstream stage output for the same query.
   Catches: stage-plumbing bugs that re-expand the candidate set and invalidate
   every survival claim.
3. `test_union_keep_rule`: craft scores where the threshold alone would drop a
   breadth-floor candidate; assert it survives.
   Catches: threshold logic silently overriding the recall safety net (the
   exact failure mode §7 exists to prevent).
4. `test_query_contract_enforcement`: pass a payload containing `split`,
   `question_type`, `group` to every model-facing entry point; assert
   `ForbiddenMetadataError`.
   Catches: label-metadata leaks into reranker inputs (tournament-invalidating).
5. `test_packet_budget_strict`: ranked-prefix packing with a hostile span list
   (first span over cap) yields empty packet + `truncated=True`, and NO packet
   ever exceeds the cap on full-serialisation counting.
   Catches: budget-accounting bugs (per-span summation instead of
   full-serialisation counting) that let oversized packets reach the generator.
6. `test_logit_never_probability`: any path that thresholds raw logits must
   carry `score_kind="logit"`; assert `validate_score_value` rejects feeding
   logits to the ECE/Brier path and that no `calibrated_probability` claim
   exists without `calibration_partition`.
   Catches: calibration-category fraud (uncertified scores presented as
   calibrated).
7. `test_regime_b_manifest`: Regime-B adaptation manifest containing any of the
   21 excluded articles fails validation; query-time corpus still resolves them.
   Catches: adaptation-data leakage AND the opposite bug (excluding them from
   retrieval, which would fake a Regime-B effect).
8. `test_determinism`: same query twice → identical ranked candidate lists and
   identical packet bytes (fixed seeds via `derive_seed`, logged derivation).
   Catches: nondeterminism (unpinned threads, hash-order iteration) that makes
   every measured number unreproducible.
9. `test_kill_attribution`: synthetic trace with a known kill stage must be
   attributed to exactly that stage by the attribution routine.
   Catches: off-by-one stage indexing that blames the wrong stage and sends
   tuning effort to the wrong threshold.

## 10. DEV / SHADOW-DEV READINESS TEST PLAN

RUN (in order, all on DESKTOP, all through the frozen `eval/` + `substrate/`
harness, generator fixed):

1. Generator floor check FIRST (STATUS.md accepted risk 3): run the
   deterministic+fixed-generator baseline (Stage-0 BM25 top-K straight to
   packet, no rerank) on dev. If answer-quality metrics do not move between a
   good-oracle packet and a degraded packet, the generator FLOORS and the
   tournament measures nothing — STOP and report before burning rerank effort.
2. Baselines (§12): BM25-alone, lexical+static-semantic, single-68M reranker
   (and BM25+17M-only as the key ablation). Record completion, recall,
   precision, token cost, per-stage latency/RSS.
3. Full cascade v0 (logit + top-K only, §6 step 1): survival metrics per stage,
   kill attribution, cost vs single-68M.
4. Threshold fitting on dev (τ₁, τ₂, τ₃ + breadth B), freeze into manifest.
5. ONE confirmation run on shadow-dev with frozen thresholds. No re-tuning.
6. Regime A/B adaptation comparison (after custodian PASS on synthetic data):
   A-on-paired, B-on-same-paired, paired delta — never pooled.

"READY" means ALL of: (a) generator floor check shows headroom (oracle >>
degraded); (b) Stage-0 BM25 recall on dev ≥ 0.90 (if Stage 0 cannot see the
evidence, no cascade survives it — fix Stage 0 first); (c) every non-final
stage shows ≥ 0.99 conditional retention on dev with denominators shown;
(d) kill attribution runs and attributes 100% of dev false negatives to a
single stage each; (e) full storage/latency/RSS telemetry complete
(`complete=true`, no None-masquerading totals); (f) all §9 unit tests pass;
(g) thresholds frozen in manifest; (h) BM25+17M ablation completed and reported
win or lose.

NOT READY if ANY of: generator floors; Stage-0 recall < 0.90; any stage's
conditional retention < 0.99 without a recorded loosening; shadow-dev
confirmation diverges from dev beyond Wilson overlap with no diagnosed cause;
ANY telemetry field silently unmeasured (None must be explicit); leakage-gate
PASS not yet issued for the synthetic batch (then adaptation work is blocked,
retrieval-only work may proceed); judge digest still unpinned (then secondary
answer metrics stay ABSENT — readiness is judged on PRIMARY metrics only).

## 11. EXPECTED MOBILE BLOCKERS (stated plainly)

1. The GENERATOR dominates the mobile story (~986 MB GGUF + llama.cpp server)
   and is out of this experiment's scope — the cascade can only shrink the
   retrieval leg. Any end-to-end on-device claim must clear the generator
   first.
2. Three-model cold start: loading 17M+32M+68M (even int8, ~120–160 MB
   simultaneous) on a memory-pressured phone risks OOM-kills and multi-second
   startup. Sequential load-and-release is the mitigation; it is untested.
3. No verified ExecuTorch or llama.cpp path for ModernBERT cross-encoders;
   the entire on-device story rides on ONNX Runtime mobile + the advertised
   (unmeasured) `model_qint8_arm64.onnx` artefacts.
4. Quantised-quality parity (O1–O4, qint8/quint8) is unmeasured — a 2-point
   completion drop at int8 would erase the cascade's margin over BM25+17M.
5. GrapheneOS-specific native-library loading, background-execution limits,
   and thermal throttling under sustained cross-encoder scoring are all
   unmeasured. Desktop latency numbers predict NOTHING about phone latency.
6. Tokeniser parity: the committed `tokenizer.json` path on desktop (Python)
   vs on-device pre-processing must produce byte-identical token streams or
   scores shift silently.

## 12. BASELINE COMPARISON (what the cascade must beat)

Ordered by increasing strength; the cascade must justify itself against EACH,
and the comparison harness (corpus, splits, evidence budget, fixed generator,
prompt, seeds, primary metrics) is identical across all:

1. Deterministic + fixed generator (BM25 Stage-0 top-K → packet, no rerank,
   no semantic model). Isolates what lexical retrieval + the generator achieve
   alone — and doubles as the generator floor check (§10 step 1).
2. BM25 alone as pure ranker (no packet-aggressive cut): the honest lexical
   floor for recall@K at each K the cascade uses.
3. Lexical + static semantic (`sentence-transformers/static-retrieval-mrl-en-v1`
   prefilter or fusion — zero-transformer, ONNX present): the cheapest semantic
   signal. If the cascade cannot beat static retrieval + 17M, the 32M/68M
   stages are dead weight.
4. BM25 + 17M-reranker ONLY (no 32M/68M stages). THE LOAD-BEARING ABLATION:
   if this nearly matches the full cascade on completion/recall, the correct
   conclusion is that the cascade is unjustified and the single tiny reranker
   wins on cost. This team commits to reporting that outcome as the headline
   if it occurs — it is the most deployment-valuable result this experiment
   can produce.
5. ONE strong reranker (68M applied to the full Stage-0 set; 150M as the
   stronger alternative if 68M-alone looks weak). This is the refutation
   baseline from §1: matching it at lower cost is the hypothesis; failing to
   match it kills the cascade.

All baseline-vs-cascade deltas reported with Wilson CIs (rates) and explicit
denominators; null results reported as underpowered, never as equivalence.

## 13. CONTRACT AMBIGUITIES (precedent-setting — two teams could diverge here)

1. **Where do worker-measured dev survival metrics come from?** Workers cannot
   see labels/evidence, yet must "report evidence-survival at every stage" on
   dev. The contract implies custodian-scored harness runs but never specifies
   the mechanism (submit traces → custodian returns metrics? which fields come
   back?). PROPOSAL (precedent): teams submit per-stage ranked node-id lists +
   packets; custodian returns ONLY aggregate/rate metrics and per-item
   covered/not-covered FLAGS (never atoms, answers, or source ids). Per-item
   flags are needed for kill attribution (§8) and leak nothing if they carry
   no content. The orchestrator must rule before implementation begins.
2. **Scale adjudication is specified but unwired** (STATUS.md honest gap 6:
   `eval/scale_adjudication.py` exists; `eval/metrics.py` does not consume
   it). Two teams could report different precision numbers on identical
   retrievals. PROPOSAL: until wired, report BOTH series — raw (scale counts
   as miss) and adjudicated via the standalone script — with the break
   annotated per `docs/evidence-semantics-notes.md`.
3. **Judge digest unpinned** (STATUS.md risk 4): secondary answer metrics are
   ABSENT. PROPOSAL: readiness and refutation rest on PRIMARY deterministic
   metrics only; any team reporting judge numbers before the custodian pins
   the digest is in protocol violation.
4. **`calibration_partition` format unspecified.** A hash? A manifest path? An
   id string? Two teams' manifests could both "pass" with incomparable
   provenance. PROPOSAL: `sha256` of the exact fitting-set manifest file,
   recorded alongside the fitting code hash.
5. **Compound-recall language vs `compound_survival` removal.** The brief's
   "0.97^4" framing invites multiplying marginals, which the substrate
   forbids. PROPOSAL: stage gates use measured conditional retentions;
   compound claims use direct cumulative coverage only (§8).
6. **Evidence-budget tokenizer identity.** `build_packet(exact=True)` needs
   "the pinned tokenizer callable" — pinned to WHAT for retrieval teams: the
   generator's tokenizer (budget governs generator input, so this is the
   coherent choice) or each reranker's? PROPOSAL: the generator tokenizer
   governs the packet budget; reranker truncation (7999-token card max is
   never binding on short passages) is a separate, per-model concern.
7. **Synthetic question_id contract.** `to_model_query` requires nonempty
   `question_id`/`text`; synthetic items need ids that can never collide with
   real ids or leak into the harness. PROPOSAL: `synth-ettin-{regime}-{n}`
   namespace, registered in the adaptation manifest, rejected by the harness
   if ever submitted as benchmark queries.
