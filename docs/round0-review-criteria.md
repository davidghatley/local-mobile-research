# Round 0 Common Substrate — Adversarial Acceptance Criteria for Freeze (DRAFT CRITERIA)

**Status**: DRAFT — not an implementation PASS verdict. This document defines adversarial review criteria for independent critique of the Round 0 substrate. It does not certify that any substrate implementation has passed.

## Orchestrator adjudication — controlling corrections

The reviewer's latest consistency claim was not accepted. The following corrections control wherever the working draft below conflicts; conflicting draft examples are not freeze requirements:

- **Source-group split:** Every split searches the same global corpus. For the article-generalization pilot, source article/confusable-group IDs used to derive supervised QA must be disjoint across train, development, and held-out sets. Disjoint question/evidence/answer tuples alone are insufficient. Multi-article QA must respect group assignment. Public reference questions are a separate development/reference set, with overlap disclosed. Identical answer strings alone are not leakage.
- **Uncertainty:** Binary question-level sufficient-evidence completion and fractional span recall are distinct outcomes. Binomial intervals apply only where the Bernoulli independence assumptions are defensible. Use justified evidence-group/article resampling or another justified correlated-data method otherwise. No universal 30-cluster minimum, 10,000-bootstrap requirement, or mandatory beta regression is imposed. Report sample sizes, dependence, method limitations, and unresolved uncertainty; ordinary beta regression does not handle exact zero/one outcomes without modification.
- **Repeatability:** Predeclare the repeat protocol and acceptance criteria before the validation repetitions. Use exploratory repetitions to characterize numerical variation, then independently validate tolerances; choosing a tolerance equal to the maximum difference in the same acceptance data is circular. No universal five-repeat requirement or second-machine availability requirement applies to Round 0. Report cross-machine reproducibility as unmeasured until tested, and separate structural differences from timing/resource differences.
- **Cache state:** Process-cold measurements may have warm page cache. They do not establish cache-cold latency and are not conservative mobile projections. Record cache state as observed or unknown; do not assert the direction or magnitude of differences without matched measurements. No host-wide cache eviction is authorized.
- **Scores:** Raw absolute and relative thresholds are valid when their development selection and operating precision/recall are recorded. Probabilistic outputs can be evaluated with ECE/Brier before calibration. A threshold on a calibrated probability does not by itself prove selected-set precision or FNR. Threshold enums must include `model_probability_dev_selected`; no calibration certificate is required merely to evaluate model probabilities.

These corrections do not constitute substrate acceptance. A consolidated contract and implementation still require review.

This document defines the concrete, independently verifiable criteria that the Round 0 common substrate must satisfy before any architecture implementation begins. Each criterion is adversarial: it is designed to expose the specific failure modes that would invalidate downstream comparisons. No criterion exists merely to be checked off; each maps to a way the experiment could produce misleading results.

---

## 1. Evidence Ground Truth & Multi-Hop Requirements

### 1.1 Explicit Evidence Anchors
- **Criterion**: For every benchmark question in the development and held-out sets, the substrate provides a machine-readable mapping from question ID to the *exact* corpus nodes (sentence/span IDs, paragraph IDs, section IDs, article IDs) that constitute necessary and sufficient evidence for a correct answer.
- **Invalidates**: If evidence is only implicitly defined (e.g., "the article about X"), cascade survival cannot be measured per stage. A system could prune the only answering span while retaining the article, and the metric would not catch it.
- **Verification**: Schema `evidence_anchors.jsonl` with fields: `question_id`, `evidence_spans[]` (character offsets or sentence IDs), `evidence_paragraphs[]`, `evidence_sections[]`, `evidence_articles[]`, `is_multi_hop`, `hop_chain[]` (ordered list of entity/relation seeds for each hop).

### 1.2 Multi-Hop Ground Truth
- **Criterion**: For multi-hop questions, the ground truth identifies *sufficient evidence sets* — one or more combinations of corpus nodes that together provide all necessary evidence for a correct answer. Each sufficient set may be reachable via different retrieval paths. The substrate records *at least one* valid retrieval chain (initial seed → extracted entities/relations → retrieved nodes → evidence spans) as a reference, but does not require it to be unique or mandatory.
- **Invalidates**: Requiring a single unique ordered chain falsely penalizes systems that retrieve the answer via a different valid path, and falsely rewards systems that happen to follow the reference chain but fail to actually use the evidence. Direct successful retrieval (answer found in fewer hops) receives full answer/evidence credit but is *not* labeled as demonstrating iterative-hop capability.
- **Verification**: `evidence_anchors.jsonl` includes `sufficient_evidence_sets[]` (each set is a list of span/paragraph/section/article IDs that together suffice), `reference_hop_chains[]` (one or more valid ordered chains for documentation), `is_multi_hop` (true if *all* sufficient sets require >1 hop under the reference corpus topology). A system that retrieves a complete sufficient set in fewer hops than the reference chain is credited with evidence recall but its `multi_hop_demonstrated` flag is false.

### 1.3 Negative Evidence / Distractors
- **Criterion**: For each question, the substrate identifies a set of *hard negative* corpus nodes: sibling paragraphs, neighboring sentences, linked articles, BM25 near-misses, semantic nearest neighbors, entity-confusable passages that a plausible but wrong retriever would rank highly.
- **Invalidates**: Without hard negatives, precision/recall curves **lack discriminative power at the operating point** — a retriever that returns the whole corpus achieves perfect recall but near-zero precision, and the PR curve cannot distinguish meaningful ranking quality from trivial full-corpus return. Hard negatives are required to evaluate whether the cascade actually separates evidence from plausible distractors at the budgets used.
- **Verification**: `hard_negatives.jsonl` per question with `node_id`, `negative_type` (enum: sibling_paragraph, neighbor_sentence, linked_article, bm25_nearmiss, semantic_nn, entity_confusion), `similarity_score`.

---

## 2. Statistical Strength for Evidence Survival (No Fixed Pass Threshold)

### 2.1 Survival Metrics: Direct Cumulative Coverage and Conditional Retention
- **Criterion**: The substrate reports three distinct metrics per stage, not a product of unconditional rates:
  1. **Stage-0 coverage**: `C₀ = |evidence_spans ∩ stage0_candidates| / |evidence_spans|` — fraction of necessary evidence present in the initial candidate pool.
  2. **Conditional retention per stage**: For stage `s ≥ 1`, `Rₛ = |evidence_spans ∩ candidates_s| / |evidence_spans ∩ candidates_{s-1}|` — fraction of evidence that *survived the previous stage* and is retained by this stage.
  3. **Direct cumulative coverage**: `Cₛ = |evidence_spans ∩ candidates_s| / |evidence_spans|` — fraction of original evidence surviving through stage `s`. This is the quantity that matters for downstream answer quality; it is computed directly, not as `∏ Rᵢ` (which double-counts losses when evidence can be recovered or when denominators differ).
- **Recovered evidence tracking**: If a later stage reintroduces evidence spans not present in the immediate prior stage's candidates (e.g., via multi-hop expansion), report `recovered_s = |evidence_spans ∩ candidates_s \ candidates_{s-1}|` separately. Do not fold recovery into retention.
- **Invalidates**: Multiplying unconditional per-stage survival rates (`∏ survival_s`) double-counts losses when evidence spans are lost at different stages and uses incorrect denominators. It also obscures recovery events. Reporting only the product makes it impossible to diagnose *where* and *why* evidence was lost or regained.
- **Verification**: `survival_metrics.json` per question per run with `stage0_coverage`, `conditional_retention[]`, `cumulative_coverage[]`, `recovered_spans[]`. Aggregated reports include mean, median, and per-question values.

### 2.2 Uncertainty Quantification: Appropriate Methods for Correlated Fractional Outcomes
- **Criterion**: Survival metrics are **fractional span recall** (not binary question completion), so binomial proportion CIs on question-level averages are **invalid** (they assume independent Bernoulli trials). The substrate must use a **justified method for correlated fractional data**: (a) **clustered bootstrap** resampling at the `article_id` or `evidence_group_id` level (whichever is the natural correlation unit), with ≥10,000 resamples, reporting percentile or BCa intervals; OR (b) a **mixed-effects beta regression** with random intercepts for article/evidence group, reporting profile likelihood CIs; OR (c) another method with a clear statistical justification documented in `uncertainty_method.md`. **`n_eff` formulas without a stated method are not accepted**. Query types are **strata** (for stratified reporting), not generally sound correlation clusters — do not cluster by query type unless empirically justified.
- **Insufficient clusters**: If the number of clusters (articles/evidence groups) is <30, the substrate **reports the uncertainty limitation explicitly** (e.g., "clustered bootstrap with 12 article clusters — CIs are approximate; treat as descriptive") rather than producing a bogus CI. The point estimate and per-question data are still reported.
- **No fixed pass threshold**: There is **no mandatory 99%, 95%, or any other survival percentage** for Round 0 freeze. A cascade with 80% cumulative coverage is a *valid negative result* — it correctly reveals that the architecture loses evidence. The substrate's job is to measure and report survival accurately with uncertainty; the orchestrator decides whether to proceed, repair, or abandon based on the measured values and their uncertainty characterization.
- **Invalidates**: Applying binomial proportion CIs (Wilson/Clopper-Pearson) to fractional span recall averaged over questions; reporting cluster-robust SEs or `n_eff` without a documented and justified resampling/modeling method; claiming precise CIs with <30 clusters without acknowledging the limitation.
- **Verification**: `survival_aggregate.json` with `metric`, `point_estimate`, `ci_lower`, `ci_upper`, `method` (enum: `clustered_bootstrap`, `mixed_beta_regression`, `other_justified`), `method_justification_ref` (path to `uncertainty_method.md`), `n_questions`, `n_clusters`, `cluster_unit` (enum: `article_id`, `evidence_group_id`), `cluster_count`, `limitation_note` (if `cluster_count < 30`). Per-question data preserved in `survival_metrics.json`.

### 2.3 Stage-wise Recall at Operating Budget
- **Criterion**: For each pruning stage, report recall at the *actual operating budget* (e.g., top-200 candidates after stage 1, top-50 after stage 2), not an arbitrary large K. Report both unconditional recall (vs. all evidence spans) and conditional recall (vs. evidence spans present in prior stage).
- **Invalidates**: Reporting recall@1000 when the pipeline only passes 50 candidates forward hides the fact that the threshold discarded the answer.
- **Verification**: `stage_recall.json` with `stage`, `budget`, `unconditional_recall`, `conditional_recall`, `evidence_spans_retained`, `evidence_spans_lost[]`, `ci_lower`, `ci_upper`.

### 2.4 False-Negative Rate by Evidence Granularity and Question Cluster
- **Criterion**: Break down survival by evidence granularity (sentence, paragraph, section, article) **and** by article cluster (questions sharing the same source article). Report per-cluster survival with cluster-robust CIs.
- **Invalidates**: A system that retains the article but loses the specific answering sentence still loses the ability to cite precisely. Generator token budget is wasted on irrelevant context. Clustering reveals whether failures concentrate on specific articles/topics.
- **Verification**: Per-stage survival tables stratified by `evidence_granularity` and `article_cluster_id`, with cluster-robust CIs.

---

## 3. Leakage Controls (Procedural Custody, Not Filesystem Enforcement Claims)

### 3.1 Split Isolation: QA Supervision Disjointness, Not Corpus Removal
- **Criterion**: The benchmark splits (`train`, `dev`, `heldout`) are defined at the **QA supervision level** — i.e., which questions and their associated evidence anchors/labels are available for training, development tuning, and final held-out evaluation. The **global searchable corpus (indexed text, vectors, metadata) is identical and fully available to all splits**. Disjointness applies strictly to the **supervised QA groups**: (a) question IDs, (b) evidence anchor mappings (which spans/paragraphs are labeled as evidence for which question), (c) answer labels. The same corpus article may appear in the evidence anchors of questions across different splits — this is **expected and required** (the corpus is shared). What must be disjoint are the **provenance groups**: a question's evidence spans and answer must not appear in another split's training or development supervision.
- **Invalidates**: Removing held-out articles from the corpus would make the retrieval task artificially easier (smaller search space) and misrepresent the real offline scenario where the full corpus is always present. Conversely, leaking held-out *questions, evidence anchors, or answers* into training or threshold tuning invalidates the held-out evaluation. **Answer string overlap alone (e.g., two unrelated questions both answered "Paris") is not leakage** — leakage is sharing of question/evidence provenance groups or duplicate QA pairs.
- **Verification**: `splits_manifest.json` with `split`, `question_ids[]`, `evidence_anchor_ids[]`, `answer_labels_hash`, `supervised_article_groups[]` (article IDs that serve as evidence sources for this split's questions). `article_overlap.json` documents **corpus-level** article overlap across splits (expected: high, since corpus is shared). `supervised_group_overlap.json` documents overlap of **supervised provenance groups** (question+evidence+answer tuples) — these must be empty. `heldout_seal.json` contains `seal_timestamp`, `seal_hash` (SHA256 of heldout QA directory: questions + evidence anchors + answers), `sealer_id`. The held-out **QA directory** (not the corpus) is the sealed artifact.

### 3.2 Procedural Custody of Held-Out QA (Not chmod 0400 Claims)
- **Criterion**: Held-out QA data (questions, evidence anchors, answers) is protected by **procedural custody**: it resides in a designated directory (`heldout_qa/`) whose contents are hashed at seal time. Access is controlled by orchestrator policy — development workers are instructed not to read it, and the review process verifies compliance by checking worker logs, command histories, and file access timestamps. The substrate does **not** claim filesystem-level enforcement (e.g., `chmod 0400`, dedicated UIDs, sandboxing) unless such controls are actually implemented and verified in the environment. If the environment cannot enforce UID separation, the criterion is procedural custody with audit trail, not a false claim of technical enforcement.
- **Invalidates**: Claiming "workers run under a different UID without read access" when the environment uses a single user account misrepresents the actual leakage risk. The review must assess the *actual* controls in place, not a theoretical ideal.
- **Verification**: `heldout_custody_report.json` with `method` (enum: `uid_separation`, `container_sandbox`, `procedural_custody_with_audit`), `audit_log_path`, `seal_hash`, `worker_uids[]`, `access_check_timestamp`. If `method != uid_separation`, the report explicitly states "No UID separation enforced; leakage control is procedural with post-hoc audit."

### 3.3 Training Data Derivation Audit
- **Criterion**: Every training example generated from the corpus must be traceable to its source article/section/paragraph and the derivation rule (template, heuristic, LLM-generated with prompt hash).
- **Invalidates**: If training data inadvertently includes dev/heldout questions paraphrased, or uses the same evidence spans as dev questions, the experiment measures memorization not generalization.
- **Verification**: `training_provenance.jsonl` with `example_id`, `source_article_id`, `source_spans[]`, `derivation_method`, `derivation_prompt_hash`, `split_assignment` (must be `train` only).

### 3.3 Candidate Pool Equality
- **Criterion**: All architectures receive the **identical** Stage-0 candidate set for a given question. The candidate generation function is part of the common substrate, not the architecture.
- **Invalidates**: If Architecture A uses BM25+embeddings and Architecture B uses BM25 only, differences in Stage-1 input confound the comparison. The tournament tests pruning/extraction, not candidate generation.
- **Verification**: `candidate_pool_freeze.json` with `question_id`, `candidate_node_ids[]`, `candidate_scores[]`, `generation_hash`. All architectures read this file; none generate their own Stage-0 candidates.

### 3.4 Generator & Prompt Freeze
- **Criterion**: The generator model, its quantization, its prompt template, and its sampling parameters are fixed **before** Round 1 and identical for all architectures.
- **Invalidates**: If Architecture A gets a better generator or a tuned prompt, retrieval quality is confounded with generation quality.
- **Verification**: `generator_contract.json` with `model_id`, `revision`, `quantization`, `prompt_template_hash`, `sampling_params`, `tokenizer_hash`.

---

## 4. Query vs. Article Splits (Retrieval vs. Generation Separation)

### 4.1 Query-Split Evaluation
- **Criterion**: The benchmark questions are split by *query type* (factoid, multi-hop, comparative, long-tail, local/travel, numeric) and the substrate reports per-type survival and quality.
- **Invalidates**: Aggregate metrics hide failure modes. A system that works for factoid but fails on multi-hop could "win" on average while being useless for the target use case.
- **Verification**: `query_type_taxonomy.json` mapping `question_id` → `type[]`. All metrics reported per type.

### 4.2 Supervised Provenance Disjointness (Not Corpus Article Exclusion)
- **Criterion**: The supervised QA provenance groups (question + its labeled evidence spans + answer) must be disjoint across `train` / `dev` / `heldout`. The **global corpus is shared**; articles serving as evidence sources for held-out questions may also serve as evidence sources for train/dev questions. What must not overlap are the **supervision tuples**: no question's evidence spans and answer may appear in another split's supervision.
- **Invalidates**: If a held-out question's exact evidence spans and answer appear in training supervision (even paraphrased), the experiment measures memorization of that specific QA pair, not retrieval generalization. **Corpus article overlap across splits is expected and not invalidating**; only supervised provenance overlap invalidates.
- **Verification**: `supervised_group_overlap.json` with `train_provenance_groups[]`, `dev_provenance_groups[]`, `heldout_provenance_groups[]`, `overlap_train_dev`, `overlap_train_heldout`, `overlap_dev_heldout` (all must be empty). `article_overlap.json` documents corpus-level article overlap (expected: high, documented for transparency).

---

## 5. Candidate Pool Equality vs. Retrieval Comparison

### 5.1 Fixed Stage-0 Interface for Controlled Pruning Arm
- **Criterion**: For the **controlled pruning comparison** (the primary tournament arm where architectures differ only in pruning/extraction), the substrate provides a single deterministic function `stage0_candidates(question) -> List[Candidate]` where `Candidate = {node_id, bm25_score, embedding_score, title_match, entity_match, aliases[]}`. All architectures in this arm consume this exact output.
- **Invalidates**: Any architecture in the controlled arm that re-ranks, filters, or augments Stage-0 candidates before its "Stage 1" is no longer comparable.
- **Verification**: Unit test: `test_stage0_deterministic.py` — same question always yields identical candidate list (order, scores, count) across runs, architectures, machines.

### 5.2 Separately Labeled Baseline Arms (BM25 vs. Union)
- **Criterion**: The substrate **also defines and freezes** baseline candidate-generation configurations as *separately labeled arms*, not as part of the controlled pruning comparison. Minimum baselines:
  - `baseline_bm25_only`: Stage-0 candidates from BM25 only.
  - `baseline_bm25_union_embedding`: Stage-0 candidates from union of BM25 top-K and embedding top-K.
  - `baseline_bm25_union_embedding_entity`: Union of BM25, embedding, and entity/alias lookup.
  These baselines are **not** required to use the same Stage-0 pool as the controlled pruning arm. They are evaluated end-to-end (candidate generation + pruning + extraction) and labeled clearly in all results tables.
- **Invalidates**: Conflating candidate-generation differences with pruning differences, or omitting baselines that isolate the contribution of candidate generation.
- **Verification**: `baseline_arms.json` listing each baseline's candidate generation config, Stage-0 pool hash, and whether it shares the controlled arm's pool.

### 5.3 Multi-Hop Expansion Policy
- **Criterion**: For multi-hop questions, the substrate defines a **common expansion policy** that specifies: (a) when to trigger a new retrieval hop (e.g., evidence sufficiency score < threshold, or max hops not reached), (b) how to form the next-hop query seed (extracted entities/relations from current evidence), (c) which candidate generation method to use for the hop (same as Stage-0 or a designated variant). The policy is architecture-agnostic. **Actual seeds used at each hop are logged per architecture** (since different pruning may yield different extracted entities), enabling attribution of multi-hop success/failure to seed quality vs. retrieval vs. pruning.
- **Invalidates**: Architectures implementing ad-hoc multi-hop logic that cannot be compared, or logging only the final hop result without the seed chain.
- **Verification**: `multihop_policy.json` with `trigger_condition`, `seed_extraction_method`, `candidate_generation_method`, `max_hops`. Per-run traces include `hop_seeds_used[]` per architecture.

### 5.4 Retrieval vs. Pruning Attribution
- **Criterion**: Metrics must separate *retrieval failure* (evidence not in Stage-0 pool) from *pruning failure* (evidence in Stage-0 but discarded later). For multi-hop, also separate *expansion failure* (evidence not retrieved in later hops despite correct seed) from *seed extraction failure* (wrong seed extracted).
- **Invalidates**: Blaming the cascade for a candidate generation failure, or crediting the cascade for a candidate generation success.
- **Verification**: `attribution.json` per question: `stage0_recall`, `stage1_recall_given_stage0`, `stage2_recall_given_stage1`, `hop1_recall_given_seed`, `hop2_recall_given_seed`, `seed_extraction_accuracy`.

---

## 6. Stage Scoring Calibration & Raw Trace Correctness

### 6.1 Score Interpretation, Probabilities, and Calibration
- **Criterion**: Models used for pruning output **scores** (logits, distances, similarities, or values in [0,1] from a sigmoid/softmax head). A model's native output in [0,1] (e.g., a `P(yes)` head) is a **model probability** — it may be miscalibrated. The substrate **distinguishes** model probabilities from **empirically calibrated estimates** (obtained via temperature scaling, Platt, isotonic regression on a held-out calibration partition).
- **Calibration is for measurement, not a gate**: ECE and Brier score **can and should be computed on model probabilities** to *measure* miscalibration — they do not require a prior calibration certificate. A model probability used directly as a threshold (e.g., `score > 0.3`) is valid if the threshold is selected on **development data via precision/recall/FNR tradeoff**; no calibration mapping is mandatory for this use case. Calibration becomes necessary only when the threshold policy **interprets the numeric threshold as a calibrated probability claim** (e.g., "keep if P(evidence) > 0.95" where 0.95 is meant to correspond to 95% empirical precision).
- **Valid threshold selection methods**:
  - Raw score absolute threshold (selected on dev via PR/FNR)
  - Raw score percentile threshold (e.g., top-20% per batch)
  - Model probability threshold (selected on dev via PR/FNR, reported with ECE/Brier on dev)
  - Calibrated probability threshold (requires calibration report on disjoint partition)
- **Invalidates**: Computing ECE on logits or non-probabilistic scores; claiming a raw score threshold "controls FNR at 5%" without empirical validation on dev; treating a model probability as calibrated without reporting its ECE.
- **Verification**: `calibration_report.json` per model with `model_id`, `score_type` (enum: `logit`, `distance`, `similarity`, `model_probability`, `calibrated_probability`), `calibration_method` (enum: `none_dev_selected`, `temperature_scaling`, `platt`, `isotonic`, `beta_calibration`), `calibration_partition_hash` (if calibrated), `ece_on_dev`, `brier_on_dev`, `reliability_diagram_path`, `threshold_policy_ref`. If `score_type == model_probability` and `calibration_method == none_dev_selected`, the threshold policy must declare `threshold_interpretation: model_probability_dev_selected` and report dev ECE/Brier alongside the threshold.

### 6.2 Threshold Policy Enforcement
- **Criterion**: The substrate enforces a **threshold policy object** for each stage: `{threshold, threshold_interpretation: enum[calibrated_probability, raw_score_percentile, raw_score_absolute], top_k_floor, min_breadth, uncertainty_adaptive: bool}`. Architectures may not hardcode thresholds in code; they read the policy.
- **Invalidates**: Hardcoded thresholds prevent fair comparison and hide the actual operating point. Using a raw-score threshold while labeling it as a probability.
- **Verification**: `threshold_policy.json` per architecture per stage. Code audit: no numeric threshold literals in pruning logic; all thresholds loaded from policy.

### 6.3 Raw Trace Schema & Completeness
- **Criterion**: Every retrieval run produces a trace conforming to `trace_schema.json` (see Appendix A). Traces are written **atomically** (write to temp, rename) and include *every* scoring decision, *every* pruning decision, *every* threshold applied (with its interpretation), and *every* adaptive breadth decision.
- **Invalidates**: Missing traces, summarized traces, or traces written after the fact make postmortem impossible. "We forgot to log that stage" is not acceptable.
- **Verification**: Automated trace validator (`validate_traces.py`) runs on every experiment run. Failed validation = run rejected.

---

## 7. Fixed Generator Tokenization

### 7.1 Tokenizer Freeze
- **Criterion**: The generator's tokenizer (vocabulary, special tokens, chat template) is frozen at Round 0. Evidence packet token counts are measured **with this tokenizer only**.
- **Invalidates**: If Architecture A uses a tokenizer that compresses evidence better, it fits more evidence in the budget — an unfair advantage unrelated to retrieval quality.
- **Verification**: `tokenizer_contract.json` with `tokenizer_id`, `vocab_hash`, `chat_template_hash`, `special_tokens`. Evidence packet `token_count` field uses this tokenizer exclusively.

### 7.2 Evidence Packet Format
- **Criterion**: Evidence packet is a deterministic function of retrieved spans: `format_evidence(spans, citations) -> string`. No architecture-specific formatting.
- **Invalidates**: Different formatting changes token count and generator behavior.
- **Verification**: Single `format_evidence.py` in substrate, used by all.

---

## 8. Cold/Warm CPU & Mobile Measurements

### 8.1 Measurement Protocol: Process Cold vs. Verified Cache Cold
- **Criterion**: Latency and memory are measured under two clearly distinguished conditions:
  - **Process Cold**: Fresh process launch. Models not in process heap. Page cache (OS filesystem cache) **may contain** model weights and index files from prior runs — this is the realistic "app cold start" condition on a device that has run the app before. The substrate records whether page cache was populated (via `fincore` or `/proc/PID/pagemap` inspection) but does **not** drop host caches (requires root, disturbs system, not representative of mobile). **This measurement UNDERESTIMATES true cold-start latency** (since page cache is warm), which is the correct conservative direction for mobile projection.
  - **Process Warm**: Same process, models resident in heap, mmap populated. Measures steady-state inference.
  - **Optional Verified Cache Cold**: If the environment supports it (e.g., dedicated test machine, container with `sync; echo 3 > /proc/sys/vm/drop_caches`), a third measurement with verified-empty page cache may be recorded as `cache_cold`. This is supplementary, not required. **No general root prerequisite is imposed** — the substrate documents available methods (drop_caches, container, dedicated VM) and records which was used, or `unknown` if not measured.
- **Invalidates**: Calling "fresh process" a "cold cache" measurement when page cache is warm **and claiming it represents true cold start** (it underestimates latency). Dropping host caches via `drop_caches` requires root, affects the whole system, and does not represent mobile app cold start (where the OS page cache often retains recently used files) — but it is a valid supplementary data point if documented.
- **Verification**: `measurement_protocol.md` in substrate documents exact procedure for each mode. Benchmark runner executes all applicable modes. Results reported as `process_cold_latency_ms`, `process_cold_peak_rss_mb`, `page_cache_status` (enum: `unknown`, `verified_warm`, `verified_cold`), `warm_latency_ms`, `warm_peak_rss_mb`, `model_load_ms`. `cache_cold_*` fields optional with `cache_cold_method` (enum: `drop_caches`, `container`, `dedicated_vm`, `other`).

### 8.2 CPU-Only, Single-Thread Baseline
- **Criterion**: All measurements run on CPU, single-threaded (or with explicit thread count), no GPU, no accelerator. The substrate documents the exact CPU model and flags.
- **Invalidates**: Desktop GPU numbers are irrelevant to Android. Multi-threaded numbers hide latency variance.
- **Verification**: `hardware_manifest.json` with `cpu_model`, `cpu_flags`, `num_threads`, `governor`, `frequency_range`.

### 8.3 Mobile Projection (Not Measurement)
- **Criterion**: Round 0 does **not** claim Android performance. It records: model sizes, quantization formats, ONNX/ExecuTorch/llama.cpp export status, operator support gaps, mmap vs. malloc behavior.
- **Invalidates**: Extrapolating from desktop CPU to mobile ARM without measuring on device is explicitly forbidden by the master prompt.
- **Verification**: `mobile_projection.json` with `model_id`, `size_fp16_mb`, `size_int4_mb`, `size_int8_mb`, `onnx_export_status`, `executorch_export_status`, `unsupported_ops[]`, `mmap_friendly`.

---

## 9. Storage Accounting (Including Pre-encoding)

### 9.1 Complete Storage Budget
- **Criterion**: The substrate accounts for **all** persistent storage:
  - Corpus text (compressed)
  - Corpus indices (BM25, embedding, entity, alias, redirect)
  - Model weights (all checkpoints, adapters, LoRA)
  - Pre-encoded document representations (KaLM compressed vectors, static embeddings, etc.)
  - Tokenizer files
  - Configuration
- **Invalidates**: Reporting "model size = 50MB" while ignoring 5GB of pre-encoded KaLM vectors misleads the storage budget.
- **Verification**: `storage_manifest.json` with `component`, `size_bytes`, `format`, `compression`, `essential_for_inference` (bool). Total must be ≤ 50 GB (target ≤ 40 GB).

### 9.2 Pre-encoding Cost Inclusion
- **Criterion**: If an architecture uses pre-encoded representations (KaLM, static-retrieval-MRL, etc.), the **build-time** cost (compute, temporary storage) is documented, and the **runtime** storage cost is included in the manifest.
- **Invalidates**: "Pre-encoding makes retrieval fast" is true but irrelevant if the pre-encoded artifacts exceed the storage budget.
- **Verification**: `preencoding_report.json` with `model_id`, `corpus_hash`, `output_size_bytes`, `build_time_cpu_hours`, `build_peak_rss_gb`, `compression_factors[]`.

### 9.3 Hashes & Freeze Validation
- **Criterion**: Every artifact has a content-addressable hash. The freeze manifest records all hashes. Any post-freeze change to any artifact is detectable.
- **Invalidates**: Silent corruption or "tweaking" after freeze invalidates the entire tournament.
- **Verification**: `freeze_manifest.json` with `artifact_path`, `sha256`, `size_bytes`, `timestamp`, `git_commit`. Validation script `verify_freeze.py` compares current filesystem to manifest.

---

## 10. Reproducibility & Run Manifests

### 10.1 Reproducibility: Structural Identity with Documented Variance
- **Criterion**: Given the same seed, the same input produces **structurally identical** traces across runs **on the same hardware/software stack**. Structural identity means: same candidate sets at each stage (node IDs, order), same pruning decisions (kept/pruned node IDs), same extracted spans, same evidence packet text (token-for-token), same generator response (token-for-token). **Excluded from identity requirement**: timestamps, wall-clock latency measurements, peak RSS values, process IDs, thread IDs, and any non-deterministic hardware counters. Numeric scores (model logits, probabilities) must match within a **documented tolerance** derived from **actual pinned-stack repeat runs** (fixed inference engine version, fixed thread count, fixed CPU governor, fixed memory allocator) — not from vendor claims. The substrate runs **≥5 repeated executions** on the exact same machine configuration to establish the empirical variance distribution for each numeric field; the tolerance is set to cover the observed variance (e.g., max observed absolute difference across repeats). Cross-machine reproducibility is **not required to be bit-identical**; it is tested by running the same pinned stack on a second machine and reporting the **hardware variance** (differences in numeric scores, any structural divergences). Generation differences across machines are **measured and reported**, not treated as automatic invalidation.
- **Invalidates**: Claiming "ONNX Runtime guarantees bit-identical output" without empirical verification on the actual stack; using an arbitrary universal tolerance (e.g., 1e-6) without repeat-run evidence; treating cross-machine numeric differences as failure without measuring and reporting the variance.
- **Verification**: `reproducibility_test.py` runs each architecture ≥5 times on 10 dev questions with fixed seeds on the **reference machine** (documented in `hardware_manifest.json`). Report: `structural_identity: true/false`, `numeric_variance[]` (field, max_diff, p50_diff, p95_diff across repeats), `tolerance_used` (derived from max_diff), `excluded_fields[]`. Cross-machine test: same pinned stack on second machine, report `cross_machine_structural_identity`, `cross_machine_numeric_diffs[]`. All numeric diffs on reference machine must be within the empirically derived tolerance.

### 10.2 Run Manifest Schema
- **Criterion**: Every experiment run produces a `run_manifest.json` with: `run_id`, `architecture`, `git_commit`, `freeze_manifest_hash`, `seed`, `split`, `question_ids[]`, `hardware_manifest_hash`, `software_env_hash` (pip freeze / conda env export), `start_time`, `end_time`, `status`, `metrics_summary`, `trace_paths[]`.
- **Invalidates**: Without this, a result cannot be traced to its exact conditions.
- **Verification**: Manifest written atomically at run completion. Required for any result to be admitted to Round 2 review.

---

## 11. What Explicitly Invalidates Conclusions

The following conditions, if discovered at any point, **invalidate the Round 0 freeze and all downstream results**:

| Condition | Why It Invalidates |
|-----------|-------------------|
| Held-out QA (questions, evidence anchors, answers) inspected by any development worker | Leakage into threshold tuning, model selection, architecture decisions |
| Train/dev/heldout **supervised provenance groups** (question+evidence+answer tuples) overlap > 0 | Memorization masquerading as retrieval skill |
| Stage-0 candidate pool differs across architectures **in the controlled pruning arm** | Confounds retrieval with pruning |
| Generator/model/prompt differs across architectures | Confounds retrieval with generation |
| Threshold policy claims calibrated probability control without calibration certificate | Operating point unknown; FNR uncontrolled |
| Survival metrics reported only as product of unconditional rates (double-counting losses) | Masks where/why evidence lost; obscures recovery |
| Survival reported with binomial CIs on fractional recall, or cluster CIs without justified method | Overstates precision; hides generalization uncertainty |
| Traces missing stages, decisions, or thresholds | Postmortem impossible; cannot diagnose failures |
| Storage manifest omits pre-encoded vectors/indices | Budget exceeded in practice |
| Latency measured only warm, or only on GPU, or "cold" claimed as true cold start when page cache warm | Mobile projection fictitious; misrepresents cold-start |
| Non-deterministic runs produce structurally different evidence packets on same pinned stack | Results not reproducible; scientific claim void |
| Any artifact hash mismatches freeze manifest | Silent mutation; audit trail broken |

**Note**: A measured cumulative coverage of 80%, 90%, or 95% with proper uncertainty characterization **does not invalidate conclusions** — it is a valid (negative) result. The substrate's job is accurate measurement, not gatekeeping to an aspirational target. **Answer string overlap alone (e.g., two unrelated questions both answered "Paris") is not leakage** — leakage requires shared question/evidence provenance or duplicate QA pairs.

---

## Appendix A: Trace Schema (Normative)

```json
{
  "question_id": "string",
  "run_id": "string",
  "architecture": "string",
  "seed": "integer",
  "stage0": {
    "candidates": [{"node_id": "string", "bm25": "float", "embedding": "float", "title_match": "bool", "entity_match": "bool"}],
    "evidence_coverage": "float",
    "latency_ms": "float"
  },
  "stages": [
    {
      "stage": "integer",
      "model_id": "string",
      "input_count": "integer",
      "scores": [{"node_id": "string", "score": "float", "calibrated_prob": "float | null"}],
      "threshold_policy": {"threshold": "float", "threshold_interpretation": "enum[calibrated_probability, raw_score_percentile, raw_score_absolute]", "top_k_floor": "integer", "min_breadth": "integer", "uncertainty_adaptive": "bool"},
      "kept": ["node_id"],
      "pruned": ["node_id"],
      "recovered_spans": ["span_id"],
      "evidence_conditional_retention": "float",
      "evidence_cumulative_coverage": "float",
      "latency_ms": "float",
      "peak_rss_mb": "float"
    }
  ],
  "multihop": {
    "hops_executed": "integer",
    "hop_seeds_used": [{"hop": "integer", "seed_entities": ["string"], "seed_relations": ["string"], "candidates_retrieved": "integer"}],
    "hop_evidence_contribution": [{"hop": "integer", "evidence_spans_added": ["span_id"]}]
  },
  "evidence_extraction": {
    "model_id": "string",
    "input_spans": ["span_id"],
    "extracted_spans": [{"span_id": "string", "score": "float", "citation_id": "string"}],
    "evidence_cumulative_coverage": "float",
    "latency_ms": "float"
  },
  "evidence_packet": {
    "formatted_text": "string",
    "token_count": "integer",
    "citations": [{"citation_id": "string", "node_id": "string", "span_id": "string", "text": "string"}]
  },
  "generator": {
    "prompt": "string",
    "response": "string",
    "latency_ms": "float",
    "peak_rss_mb": "float"
  },
  "total_latency_ms": "float",
  "total_peak_rss_mb": "float",
  "storage_mb": "float",
  "survival_summary": {
    "stage0_coverage": "float",
    "conditional_retention_per_stage": ["float"],
    "cumulative_coverage_per_stage": ["float"],
    "recovered_spans_total": "integer"
  }
}
```

---

## Appendix B: Freeze Checklist (Sign-off Required)

Before Round 0 is declared frozen, an independent reviewer (not the substrate builder) must verify each item:

- [ ] Evidence anchors exist for all dev/heldout questions with span-level precision
- [ ] Multi-hop **sufficient evidence sets** and **reference hop chains** documented (no mandatory unique chain)
- [ ] Hard negatives identified for all questions
- [ ] Train/dev/heldout splits disjoint at **supervised provenance level** (question+evidence+answer tuples); corpus article overlap documented and expected
- [ ] Heldout **QA directory** sealed (hash recorded, sealer identified, custody method documented)
- [ ] Stage-0 candidate generation deterministic and frozen **for controlled pruning arm**
- [ ] Baseline arms (BM25-only, BM25+embedding, BM25+embedding+entity) defined and frozen separately
- [ ] Multi-hop expansion policy defined and frozen
- [ ] Generator contract frozen (model, quantization, prompt, tokenizer)
- [ ] All pruning models: score type declared; calibration reports present where thresholds claim calibrated probability control; dev ECE/Brier reported for model probabilities used directly
- [ ] Threshold policies defined per stage per architecture (no hardcoded values; threshold_interpretation declared)
- [ ] Trace schema implemented; validator passes on sample runs
- [ ] Process cold / warm / (optional cache cold) measurement protocol documented and runnable
- [ ] Hardware manifest recorded
- [ ] Storage manifest complete including pre-encoded artifacts
- [ ] All artifact hashes recorded in freeze manifest
- [ ] Reproducibility test passes (≥5 repeats on reference machine structurally identical; numeric variance empirically characterized; cross-machine variance measured and reported)
- [ ] Run manifest schema implemented
- [ ] Held-out QA access controlled by documented custody method (UID separation OR procedural with audit)
- [ ] Training data provenance logged; no dev/heldout QA provenance contamination

**Freeze is not granted by checklist completion alone.** The independent reviewer must also read a sample of traces, inspect a sample of training examples, and confirm that the substrate *actually* enables fair comparison — not just that the paperwork exists.

---

## Appendix C: Reviewer Independence Requirement

The Round 0 reviewer:
- Must not have contributed code, config, or data to the substrate
- Must use an explicitly free model (Gemma 4 31B Free or Nemotron 3 Ultra Free)
- Must produce a written review citing specific files, hashes, and test outputs
- Must explicitly state "PASS" or "REPAIR REQUIRED" with concrete reasons
- The review artifact is preserved as `docs/round0-review-<timestamp>.md`

---

*This criteria document is itself part of the freeze. Changes after freeze require orchestrator approval and full re-review.*
