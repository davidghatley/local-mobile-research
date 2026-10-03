# Comparability Plan — Round 1

**Purpose:** This plan operationalizes the comparability CONTRACT for Round 1 architecture teams. It specifies what each team must do, what the orchestrator will verify, and the gate sequence for proceeding to private evaluation.

---

## Overview

Round 1 is a **retrieval/evidence tournament**, not a generator tournament. The fixed generator (Qwen2.5-1.5B-Instruct Q4_K_M) and fixed prompt are shared by ALL architectures. The primary metrics are deterministic retrieval and evidence-survival metrics that require no judge model. The contract and plan preregister every enforcement mechanism so that cross-team comparison is meaningful.

**Five architecture families** are expected: B1 (BM25 only), B2 (BM25 + static semantic), B3 (68M cross-encoder reranker ceiling), B4 (BM25 + fixed generator floor, identical to B1's pipeline), and any additional teams building independent systems.

All systems must comply with the **model-facing query boundary** (`substrate.query.to_model_query`, exactly `question_id` and `text`), the **evidence budget** (300–800 exact tokens, 1000-token hard cap), and the **generator config pin** (model_id, revision, quantization, tokenizer_id, prompt_hash).

---

## Phase 0 — Pre-Implementation Verification (Orchestrator)

Before any architecture team begins implementation, the orchestrator runs `./scripts/verify_round0` on a **clean tree** at tag `round0-freeze-r1`. This must return **10/10 PASS**.

Verified items (from STATUS.md):
1. Shared substrate tests (422)
2. Data-tools tests (77)
3. Corpus converter tests (17)
4. Corpus structure + hash
5. QA validation (0 errors, 206 approved, census-matched)
6. Question/label partition: public-only file + out-of-repo opaque seal
7. Generator pin
8. Freeze manifest incl. paired regime fields, census digest, and durable out-of-repo freeze record
9. Leakage-control artifacts (paired Regime A/B, exclusions)
10. Private test exists outside repo, seal matches, labels stay outside

If verification fails, the architecture team must not begin work until all 10 stages pass. The team should report the specific gaps and request re-review.

---

## Phase 1 — Architecture Setup (Team Responsibility)

Each architecture team sets up their system under `experiments/<architecture>/` with the following binding requirements:

### 1.1 Model-Facing Query Interface (MANDATORY)
- Every query handed to any component (retriever, sufficiency controller, generator adapter) must be a `substrate.query.QueryInput` with exactly two fields: `question_id` and `text`.
- Use `substrate.query.to_model_query(entry)` as the ONLY sanctioned conversion from a stored partition entry.
- **FORBIDDEN:** `split`, `question_type`, `answerability`, `group`, `evidence_groups`, `source_articles`, `regime`, `regime_b`, `paired*`, `evidence`, `sufficient_sets`, `hard_negatives`, `label`, `labels`, `answer_text`, `meta`, `provenance` must NOT reach a model.
- Run `tests/test_query_contract.py` — it asserts `assert_no_label_metadata` fail-closed on every forbidden field at every nesting level.
- **Enforcing mechanism:** The substrate raises `ForbiddenMetadataError` if any forbidden field is present. This is tested unit-test wise; any violation blocks the run.

### 1.2 Corpus and Index (MANDATORY)
- Use the **pinned core corpus** `corpus/corpus.jsonl` revision `pilot-297-r1`. Do NOT modify corpus files.
- Use the **pinned scale tier** `corpus/scale/distractor.jsonl`. If indexing core+scale, declare it in the run manifest and use the merged document set (N=36,609).
- Use the **pinned paragraph-node index**: every `kind == "paragraph"` node. Do NOT use sentence-level or article-level retrieval.
- Index document string `D(p)` as defined in HYPOTHESIS.md §3.2: `article_title + " " + section_heading + " " + paragraph_text`, with the `(lead)` omission rule (297 sections).
- Tokenize queries and documents using the **pragma tokenizer** (NFKC → casefold → `[a-z0-9]+` regex, stdlib only). No stemming, no stopwords.
- **BM25 parameters: k1=1.2, b=0.75** (frozen). Any grid search `{k1 ∈ {0.9, 1.2, 1.5}, b ∈ {0.5, 0.75}}` must be recorded as a dev-selected ablation, not the baseline.
- Stage-0 candidate set: **top K = 500** documents by BM25 total order. If fewer than 500 have positive overlap, take all positive documents.

**Unit test the orchestrator will run:**
- `test_bm25_bit_exact` — hand-computed fixture; any re-implementation must match the pinned fixture's top-500 list byte-for-byte, or it is rejected.
- Index sha256 goes in the run manifest; a build that differs from the pin blocks the run.

### 1.3 Static Semantic Channel (B2 only)
- If implementing B2, use the **pinned embedding model** `sentence-transformers/static-retrieval-mrl-en-v1` at the verified revision `f60985c706f192d45d218078e49e5a8b6f15283a`.
- Tokenize with the model's fast tokenizer: `encode_batch(texts, add_special_tokens=False)`, no padding.
- Embed with mean over token-embedding rows, dimension 1024, NO L2 normalization inside; retrieval score = cosine = inner product.
- **Fusion rule (B2 §4.3):** Borda sum over ranks. `union = BM25 top-500 ∪ static top-500` (≤ 1000 docs). `fused(c) = r_bm25(c) + r_static(c)` (integer, exact). Rank by `(fused ascending, node_id ascending)`.
- **B2 index storage:** doc-vector cache: core 9,979 × 1024 × 4 B = 40,873,984 B (≈ 39.0 MiB fp32) or 10,218,496 B (≈ 9.75 MiB int8). Merged: 36,609 × 1024 × 4 B = 149,950,464 B (≈ 143.1 MiB fp32) or 37,487,616 B (≈ 35.7 MiB int8).

### 1.4 Reranker Channel (B3 only)
- If implementing B3, use the **pinned cross-encoder** `cross-encoder/ettin-reranker-68m-v1` at revision `d166fa88ddde3c42bc3ee92f7df476d941c8204a`.
- Pipeline: B1 stage-0 (BM25 top-500) → score ALL 500 with the 68M cross-encoder.
- Cross-encoder input: `QueryInput.text` (verbatim) as query; **paragraph node text verbatim (p:text), NOT D(p)**. The cross-encoder was trained on standalone (query, passage) pairs; the heading prefix is a BM25-specific trick — each channel uses its canonical input.
- Output: logit per candidate, `score_kind="logit"`. Total order: logit descending, node_id ascending.
- **Top-50 sizing:** keep top 50 after reranking for packed policy (§2.3: per-article cap 3, strict 1000-token cap, exact generator tokenizer, ranked prefix).
- **Parity gate:** Any deployment runtime (ORt int8, multi-thread) must clear the parity gate before rankings are reported: fp32 reference top-100 rank correlation (Spearman) ≥ 0.99 against the fp32 reference AND final-completion delta ≤ 1 item on 10 dev items, else it stays deployment-only.

### 1.5 Fixed Generator (ALL architectures)
- Use the **pinned generator**: `qwen25-1.5b-q4km-fixed-v1` (Qwen2.5-1.5B-Instruct Q4_K_M GGUF).
- **Prompt:** the FIXED_GENERATION_PROMPT (SHA256 pinned). Do NOT vary the prompt, add system messages, or enable sampling.
- **Generation path:** the ONLY sanctioned path is `substrate.evidence.run_question(retriever, generator, question, decide=decide_default)`. The default `decide_default` is the safe floor (`decide_default` from `substrate/evidence.py`).
- **No prompt variation, no sampling variation, no generator tuning.** The tournament is retrieval/evidence, not generation.
- **Tokenizer:** the pinned generator tokenizer. Token counting must use `exact=True` with the pinned tokenizer; whitespace estimates are INFRA-ONLY and must never be reported as measurements.
- **Evidence budget:** `TARGET_EVIDENCE_TOKENS_MIN = 300`, `TARGET_EVIDENCE_TOKENS_MAX = 800`, `HARD_EVIDENCE_TOKEN_CAP = 1000`. Budget enforced on the FULL serialization `serialize_evidence(kept + [span])` at every packing step.
- **Per-article cap:** at most 3 spans from one article per packet (deterministic skip; prevents one article's strong lexical match from eating the entire budget on multi-hop/comparison items).
- **Packet packing:** ranked-prefix semantics. First span that would overflow the cap stops packing (`truncated=True`). A first span that alone overflows yields an EMPTY packet with `truncated=True` (valid abstention outcome).

**Generator config that must be in `corpus/generator_config.json`:**
- `model_id`: `qwen25-1.5b-q4km-fixed-v1`
- `revision`: the pinned GGUF revision (as recorded in the manifest)
- `quantization`: `Q4_K_M`
- `tokenizer_id`: the pinned tokenizer identifier
- `prompt_hash`: `sha256_text(FIXED_GENERATION_PROMPT)` (computed from the fixed prompt)
- `runtime`: the runtime used (e.g., `gguf`)
- `artifact_sha256` and `artifact_bytes`: the GGUF artifact file hash and size

### 1.6 Sufficiency Policy (ALL architectures)
- **All four baselines use `decide_default` (the safe floor)** — no tuned sufficiency gate.
- The safe floor (`decide_default` from `substrate/evidence.py:162-203`):
  - Zero spans with `truncated=False` → insufficient/abstain, reason "zero-spans".
  - Zero spans with `truncated=True` → insufficient/abstain, reason "over-budget-empty" (distinct from zero-spans; keeps packing failure from being misread as a retrieval decision).
  - Any nonempty packet → sufficient/generate, reason "nonempty-packet".
- **No architecture may supply a tuned sufficiency policy** unless they document it as a recorded ablation. The floor is the same for everyone; if a team wants a different sufficiency gate, they must run a NEW tournament round with a new freeze.
- **Abstention outcome:** correct_abstention on unanswerable items is the only valid abstention; false_abstention on answerable items is a failure; unsupported_generation on unanswerable items is a failure.

### 1.7 Regime B (ALL architectures)
- **Model A:** normal corpus-known adaptation — architecture-specific synthetic training/adaptation may use any corpus document.
- **Model B:** the identical procedure, but ALL 21 publicly declared Regime-B articles are excluded from architecture-specific synthetic training/adaptation data.
- The public 21-document exclusion list: `corpus/regime_b_excluded_articles.json` (sorted union of cambridge / corona / jaguar / lincoln / washington groups).
- **Query-time corpus is IDENTICAL for A and B:** the 21 REMAIN in the retrieval corpus (excluded from adaptation data only).
- Workers exclude exactly the 21 articles from adaptation data using `substrate.query.worker_regime_b_exclusions()`.
- **Regime A ≡ Regime B BY CONSTRUCTION** for the baselines (BM25 is untuned, static and reranker are off-the-shelf pins; no fine-tuning anywhere). Both regime runs produce byte-identical outputs.
- **Regime B worker exclusion is derived from the PUBLIC artifact only** — never from private paired-regime metadata. The sanctioned function `worker_regime_b_exclusions()` reads ONLY `corpus/regime_b_excluded_articles.json` and validates the path is not private/symlinked.

### 1.8 Seed and Reproducibility
- Use **one master seed** for the run. Per-component seeds are derived via `substrate.manifest.derive_seed(master_seed, component)`.
- Log the seed derivation in the run manifest (`seed_derivation_log`).
- **No component uses randomness** — BM25 is deterministic stdlib; generator sampling is pinned and non-empty but fixed; retrieval candidate selection is top-K by score, no stochastic selection.
- If a team discovers any RNG usage, it is a bug and must be fixed before the run.
- Corpus document order = pinned byte order; every index artifact (binary + JSON) is sha256-pinned into the run manifest.

### 1.9 Telemetry and Metrics Collection
Each team must collect and report the following metrics in their run manifest (classified as MEASURED, ESTIMATED, or NOT YET MEASURABLE):

| Metric | Classification | Collection method |
|---|---|---|
| Stage-0 recall@500 | MEASURED | `eval/metrics.py:recall_at_k(retrieved, required, 500)` against required evidence set per item |
| Stage-1/candidate reduction ratio | MEASURED | `(candidates_out / candidates_in)` per stage from StageRecord traces |
| Final evidence recall | MEASURED | `|E ∩ final_packet_citations| / |E|` per item |
| Evidence token cost (exact_evidence_tokens) | MEASURED | `EvidencePacket.exact_evidence_tokens` from build_packet with exact tokenizer |
| Context precision (leaf_precision) | MEASURED | `eval/support.py:context_precision_report` on retrieved ids vs atoms |
| Abstention accuracy (sufficiency_accuracy) | MEASURED | `eval/metrics.py:abstention_summary` on {answerable, abstained} records |
| Latency (total_latency_ms) | MEASURED | `time.perf_counter` deltas via `timed_phase`, reported in MILLISECONDS |
| RAM (peak_rss_mb) | MEASURED | `resource.ru_maxrss` / Linux, reported in MEBIBYTES |
| Storage (storage_bytes) | ESTIMATED (index) / MEASURED (per-file) | `os.path.getsize` for index files; `storage_manifest` for component totals |
| Generator artifact size | NOT YET MEASURABLE (shared, excluded from per-baseline cost) | Reported as "shared 1 GB, excluded" in the run manifest |

**Tie-breaking chain** (applied in order):
1. Required-evidence survival per stage
2. Stage-0 recall
3. Candidate reduction ratio
4. Final evidence recall
5. Evidence token cost (lower is better)
6. Context precision (higher is better)
7. Abstention accuracy (higher is better)
8. Latency (lower is better)
9. RAM (lower is better)
10. Storage (lower is better)

**Judge dependency:** NO primary metric depends on `google/flan-t5-large`. The judge is UNPINNED and ABSENT (accepted risk #4); secondary generated-answer metrics are ABSENT for all baselines. The primary metrics are purely retrieval/evidence metrics.

---

## Phase 2 — Dev/Shadow-Dev Evaluation (Team Responsibility)

Each team evaluates their system on the **dev** (59 items) and **shadow_dev** (87 items) splits using ONLY the worker-visible data. Do NOT use private test items for tuning or threshold selection.

### 2.1 Threshold selection on dev only
- Teams may select thresholds (e.g., sufficiency score thresholds, confidence thresholds) on the **dev** split.
- **Anti-leak rule:** thresholds must be frozen in the run manifest BEFORE the private run begins. Any threshold tuned on private items voids the run.
- Record the selected threshold and the dev metric values in the run manifest.

### 2.2 Metric computation on dev + shadow_dev
- Compute all primary metrics on the combined dev + shadow_dev set (146 items).
- Report Wilson 95% CIs for binomial proportions (recall, survival rates) so the orchestrator can assess whether observed differences are meaningful.
- Report the kill condition result (see Section 6 of CONTRACT.md) if applicable.

### 2.3 Wilson CI reporting
- For each binomial proportion (e.g., required-evidence survival rate), compute the Wilson 95% CI: `wilson_ci(hits, n, z=1.96)` from `eval/metrics.py:227-240`.
- Report `{"lower": ..., "upper": ...}` alongside the point rate.
- The orchestrator uses these CIs to assess the kill condition and the minimum meaningful difference.

### 2.4 Anti-leak enforcement
- The orchestrator checks that no private test items appear in the dev/shadow_dev evaluation results.
- The in-repo `corpus/private_test_manifest.json` (opaque, counts + hashes only) is the seal check; the orchestrator asserts it is content-free (no question text, labels, or answers).
- If a team reports metrics that implicitly reveal private item information (e.g., a threshold that only makes sense for a private item), the run is rejected.

---

## Phase 3 — Generator Floor Check (Custodian-Scored, Preregistered)

**This phase runs BEFORE any private evaluation.** The custodian performs the generator floor check as a preregistered infrastructure check.

### 3.1 Floor detection procedure
1. **Run B4 end-to-end on dev FIRST** (BM25 + fixed generator + `decide_default`).
2. **Custodian oracle run:** For each dev item, the custodian constructs an ORACLE packet — the minimal complete sufficient set of paragraphs, packed by the same `build_packet` semantics (ranked-prefix, exact tokenizer, 1000-token cap).
3. **Compare answer quality:**
   - Let `A` = answers produced by B4 (regular packed packet).
   - Let `O` = answers produced by the custodian oracle packet.
   - Compute the answer-quality delta: proportion of dev items where `O` is CORRECT and `A` is INCORRECT (or vice versa), using deterministic answer-matching rules (normalize_answer, exact_match from `eval/answer_scoring.py`).
4. **Decision rule:**
   - The comparison is **PAIRED** (same items, different packet), so it needs McNemar's exact test, not an unpaired Wilson. Discordance needed for 80% power at n=146 is 23% at a 3:1 split favouring the oracle, 16% at 4:1, 9% at 9:1.
  Three-way decision rule — let `I` be the McNemar interval for the oracle's advantage:
  - `I` excludes 0 → generator does **not** floor; proceed.
  - `I` includes 0 and its upper bound is below the minimum meaningful difference → generator **FLOORS**; report and stop before private evaluation.
  - `I` includes 0 and its upper bound exceeds the minimum meaningful difference → **INCONCLUSIVE / UNDERPOWERED**, which is its own outcome and must NOT be recorded as "no floor".
  (The original "delta ≤ 5% ⇒ floor" rule was superseded: 5% is below what this probe can measure, so it would have called a floor what was really an underpowered test.)

### 3.2 Custodian legitimacy
- The **custodian** may use an oracle packet because they have access to ground-truth required evidence sets. This is legitimate under the custody rules.
- **A WORKER may NOT** construct or use an oracle packet during their run (would violate the model-facing boundary).
- **Refinement:** The oracle packet must be constructed outside the worker's runtime, using the same `build_packet` function with the pinned tokenizer. The only difference is span selection (ground-truth knowledge), which is determined by the custodian.

### 3.3 What happens if the floor is found
- The tournament **STOPS** and reports the floor finding.
- The correct scientific output is: "the generator floors on this corpus; the retrieval tournament measures nothing above the floor."
- Any architectures that claim superiority based on private-run results are suspect.
- The baseline lead (B4) is acknowledged as the correct floor configuration.
- The kill condition (§0 of HYPOTHESIS.md) is moot because the generator cannot express differences.

### 3.4 What happens if the floor is NOT found
- The tournament proceeds with the understanding that the generator can express differences.
- Retrieval metrics (recall, survival, etc.) are the primary comparability metric.
- The team proceeds to Phase 4 (private evaluation) with the understanding that the generator is not the bottleneck.

---

## Phase 4 — Private Evaluation (Custodian-Owned, NO TEAM ACCESS)

**Do NOT run private evaluation.** Do NOT tune on private results. The private test is outside the repository at `LMR_PRIVATE_EVAL_DIR`; it is sealed.

### 4.1 Custodian-only access
- The custodian runs the architecture's system on the private test items (116 items, 62 groups, 15 paired Regime-B items).
- The verdict is PASS or REJECT + the synthetic training ids to remove; it never discloses matched private ids/text/answers/evidence.
- The leakage gate (`data_tools.leakage_check` / `substrate.private_eval.check_training_overlap`) runs PASS or REJECT closed: with no seal it is REJECT, never PASS.

### 4.2 What teams must not do
- **Never read** `private_test_manifest.json` content, labels, answers, or evidence.
- **Never tune** thresholds on private results.
- **Never claim** Android or on-device performance from desktop measurements.
- **Never** modify the scoring protocol (`docs/scoring-protocol.md`) after private results are visible.

### 4.3 Post-private evaluation
- The custodian reports aggregate results (NOT per-item details that reveal private data).
- The orchestrator compares architecture performance against the kill condition and the minimum meaningful difference.
- If the kill condition is met (BM25 + small reranker matches cascade within Wilson CI), the output is: "the cascade is unnecessary — no statistically meaningful difference was detected."
- If the kill condition is not met, the orchestrator reports the actual delta with Wilson CIs.

---

## Phase 5 — Scale Adjudication (Optional, wired per accepted risk)

If the architecture team wishes to consume scale adjudication:

### 5.1 Adjudication procedure
- Follow `docs/scale-evaluation-rule.md`: a retrieved scale passage must NOT auto-count as a false positive merely for coming from the distractor layer.
- Procedure: identify the retrieval → check for core annotated evidence → evaluate the scale passage as supported/unsupporting/unknown (per rule) → classify outcome.
- **`eval/scale_adjudication.py` hook:** `needs_adjudication(article_class, has_core_evidence)` returns True only for `confusable_adversarial` articles with core evidence.

### 5.2 Reporting
- Report BOTH series: raw metrics AND adjudicated metrics via the standalone script.
- Annotate the break: "scale adjudication wired per accepted risk 6; raw metrics above, adjudicated below."
- If the adjudication rule is NOT consumed by `eval/metrics.py`, report raw metrics only and note the gap.

**Important:** Scale adjudication is **ACCEPTED RISK #6** — the rule exists but is not yet consumed by the metric layer. Until it is wired, no architecture should claim scale-related advantages.

---

## Phase 6 — Freeze and Durable Record

After all phases, the architecture team and the orchestrator produce a **durable freeze record**:

### 6.1 Run manifest
- Write a `run.json` (or use `RunManifest.write()`) containing:
  - `run_id`, `seed`, `corpus_hash`, `code_hashes`
  - `generator` (GeneratorConfig, fully pinned)
  - `thresholds` (declared policies only; no fitted calibrations)
  - `stage_results` (per-stage metrics: recall, survival, token cost, latency, RAM)
  - `kill_condition` result (met or not, with Wilson CI parameters)
  - `generator_floor_check` result (floored or not, delta, CI)
  - `partition_census_sha256` (binding to external census pin)
  - `public_reference_pins_sha256` (matching `references/public_eval_pins.json`)
  - `sealed_labels_sha256` (opaque, from out-of-repo private seal)
  - `commit_sha`, `verified_at_utc`, `verifier_sha256`, `verifier_mode`
  - `regime_a_heldout_groups`, `regime_b_document_heldout_groups`

### 6.2 Code hash verification
- Every file used in the run must have its sha256 recorded in `code_hashes` in the run manifest.
- `validate_freeze` (substrate/manifest.py:716-723) recomputes every code hash and rejects any mismatch.
- Code changes between runs require a new freeze tag.

### 6.3 Durable record binding
- The freeze tag `round0-freeze-r1` (or a new tag for Round 1) binds the verifier script hash, the verifier mode, and the verification timestamp.
- The durable record is stored OUTSIDE git in `<LMR_PRIVATE_EVAL_DIR>/freeze_manifest_<frozen-commit-sha>.json` and `<LMR_PRIVATE_EVAL_DIR>/freeze_tag_binding.json`.
- The manifest digest is self-referential: it embeds the commit SHA, the verifier hash, and the verification timestamp, so any commit that changes this line changes the digest — a self-referential figure that can never be correct, ensuring the record is durable.

### 6.4 Independent review
- Eight independent reviews have run for Round 0; Round 1 must have a fresh reviewer confirm repairs landed before the tournament begins.
- The reviewer checks: structure, hashes, splits, provenance, custody, and pins. They do NOT prove semantic QA correctness.

---
---
---
*End of PLAN.md*
