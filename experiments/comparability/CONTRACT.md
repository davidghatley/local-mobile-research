# Comparability Contract — Round 1

**Purpose:** This contract makes cross-team comparison meaningful by specifying what must be byte-identical or provably-equivalent, and the enforcing mechanism for each item. Its failure mode is: two teams produce numbers that differ for reasons that have nothing to do with architecture quality, and nobody notices until after the winner is published.

---

## 1. Corpus and Scale Tier Identity

| What must be identical | Enforcing mechanism |
|---|---|
| Core corpus: `corpus/corpus.jsonl`, revision `pilot-297-r1`, sha256 `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64` (297 articles, 43,876,251 B) | `validate_freeze` recomputes the corpus hash and rejects any mismatch (substrate/manifest.py:389-390). Every team works from the pinned tag `round0-freeze-r1`. |
| Scale tier: `corpus/scale/distractor.jsonl` (sha256 `516463e340de8c53…` per `scale_build_manifest.json`), 940 articles | Teams may index core-only OR core+scale, but the index document order and sha256 must match the pinned build manifests. The merge configuration is declared in the run manifest and pinned there. |
| Partition census: `corpus/partition_census.json` outside git (pin in `freeze_census_pin.json`) | The census digest is recorded OUTSIDE git; a co-edit of data + census is detectable by comparing against the external digest. `validate_freeze` checks `partition_census_sha256` against the actual file (manifest.py:593-599). |
| Worker-visible questions: `corpus/questions.json` (206 items: train 60 / dev 59 / shadow_dev 87) | Questions sha256 is recorded in the run manifest and validated by `validate_freeze` (manifest.py:430-431). The in-repo manifest carries only `question_id`, `text`, `split`, `meta` (no `group`, `evidence_groups`, `source_articles`). |

### Ways teams could diverge and flatter themselves
- Using a different corpus revision or a modified scale tier without declaring it → detected by hash mismatch in `validate_freeze`.
- Including answer-adjacent metadata in questions (e.g., `meta.group`) that gives a retriever an unfair candidate set → the model-facing boundary `assert_no_label_metadata` and the query contract `to_model_query` prevent this, but if a team indexes using metadata that is publicly visible in questions.json, they gain an advantage. **Enforcing:** the corpus builder drops `group`/`evidence_groups`/`source_articles` from `meta` in the committed `questions.json`; any team that re-builder the partition must follow the same `data_tools/build_public_partition.py` script.
- Using a different scale adjudication rule → the contract specifies `docs/scale-evaluation-rule.md` as the sole adjudication procedure; any other rule is a protocol violation.

**Enforcing mechanism preference:** Executable hash checks (`validate_freeze`) over prose promises. These would be turned into unit tests that assert hash equality on every run.

---

## 2. Candidate Generation (Stage 0)

| What must be identical | Enforcing mechanism |
|---|---|
| **Stage 0 is SHARED** — all teams use the same candidate generation pipeline (BM25 with pinned parameters k1=1.2, b=0.75; tokenizer: NFKC → casefold → `[a-z0-9]+` regex; top-K=500; no stemming; no stopwords; paragraph-node index; per-article cap of 3 spans). | The baseline spec `experiments/baselines/HYPOTHESIS.md §3` pins every parameter. Any deviation is an "ablation" that must be recorded and reported separately, not the baseline. |
| **If Stage 0 is per-team:** results are NOT comparable across teams. The contract explicitly recommends a **shared Stage 0** because BM25 is stdlib-only and deterministic; making it per-team introduces an uncontrolled variable. The cost of choosing a shared Stage 0 is minimal (it advantages no one and disadvantages no one since the parameters are frozen), but if a team insisted on their own BM25, their numbers could not be compared to others. |
| **Evidence budget in TOKENS** (not passages, not characters): `TARGET_EVIDENCE_TOKENS_MIN = 300`, `TARGET_EVIDENCE_TOKENS_MAX = 800`, `HARD_EVIDENCE_TOKEN_CAP = 1000`. Token counting uses the **pinned generator tokenizer** via `build_packet(exact=True, tokenizer=<pinned tokenizer callable>)`. Whitespace estimates (`token_estimate`) are explicitly INFRA-ONLY and must never be reported as measurements. | The generator config (`corpus/generator_config.json`) pins `tokenizer_id` and the tokenizer callable. `build_packet` validates `exact=True` requires the pinned tokenizer. `evidence.py:106-112` raises `ValueError` if `exact=True` and tokenizer is None. Token counts that use `estimate_tokens` (whitespace split) are flagged as infra-only and excluded from empirical metrics. |
| **Exact generator id, revision, quantisation, and PROMPT_HASH**: `qwen25-1.5b-q4km-fixed-v1` (Qwen2.5-1.5B-Instruct Q4_K_M GGUF), pinned by the generator owner, shared by ALL architectures. The `PROMPT_HASH = sha256_text(FIXED_GENERATION_PROMPT)` is computed from the fixed prompt and verified in `validate_freeze` (manifest.py:653-654). A team proves they used those by having the generator config sha256 match the manifest, and by logging the exact `model_id`, `revision`, and `quantization` in the run manifest. | `GeneratorConfig.is_pinned()` requires `model_id`, `revision`, `prompt_hash`, `quantization`, `runtime`, `file`, `artifact_sha256`, `artifact_bytes > 0`, `tokenizer_id`, `chat_template_sha256`, and non-empty `sampling` all to be non-placeholder strings (generator.py:74-88). `validate_freeze` checks `gen.prompt_hash != PROMPT_HASH` → gap (manifest.py:653-654) and checks all semantic fields against the on-disk config (manifest.py:676-678). |
| **Telemetry schema**: `substrate.telemetry` + `substrate.types.StageRecord` / `RetrievalOutcome`. `None` = EXPLICITLY NOT MEASURED, never silent. Load-bearing fields: `candidates_in`, `candidates_out`, `latency_ms`, `total_latency_ms`, `peak_rss_mb`, `stages`, `packet`, `question_id`. Informational fields (may be None): `model_loading_latency_ms`, `inference_latency_ms`, `storage_bytes`, `hops`, `adaptive_compute_decision`. | The telemetry dataclasses use `None` as the explicit sentinel for "not measured" (types.py:27-28, telemetry.py:27-29). `StageRecord.from_dict` and `RetrievalOutcome.from_dict` default missing fields to `None`. Any code that silently omits `None` values or replaces them with 0 breaks comparability; the substrate validates schema completeness. |
| **Seed policy**: one master seed; per-component seeds derived via `substrate.manifest.derive_seed` / `derive_seeds`; the derivation is logged in the run manifest. What is seeded: master seed, split assignment (`assign_seed`), generator seed derivation. What is deliberately NOT seeded: randomness in BM25 (it is deterministic stdlib; no RNG used), randomness in retrieval (candidate set is top-K by score, no stochastic selection), randomness in generator (sampling is pinned and non-empty per config, but the tournament uses greedy/decoding params that are fixed). Nondeterminism (float reduction order, thread count) is controlled by declaring `None` in telemetry when the measurement is not feasible on desktop, and by the `validate_freeze` code-hash checks that ensure the same binary runs. | `derive_seed(master_seed, component)` uses `hashlib.sha25(f"{master_seed}\x00{component}".encode("utf-8")).hexdigest()` → first 16 hex digits (manifest.py:76-79). The run manifest records `seed_derivation_log`. If a team introduces uncontrolled RNG, their results must be reported with `peak_rss_mb` and `latency_ms` marked `None`, and the run manifest must document the uncontrolled component. |
| **Dev / shadow_dev splits and anti-leak rule**: train (60), dev (59), shadow_dev (87). Threshold selection (e.g. K=500 cut-off, sufficiency thresholds) may be tuned on **dev** only. **Anti-leak rule:** threshold selection on private test items is strictly forbidden; any threshold tuned on private results voids the run. The anti-leak rule is enforced by the leakage gate (custodian checks synthetic training overlap) and by the run manifest recording "thresholds selected on dev; frozen before private run." | Split assignments are derived from the master seed via `assign_seed` (manifest.py:37-79) or from the group-map in `corpus/split_map.json`. The anti-leak rule is a protocol rule: if a team reports a threshold that was tuned on private items, the run is rejected. In practice, the custodian records the dev-selected threshold in the run manifest before the private run begins. |
| **Pointer to the frozen scoring protocol**: `docs/scoring-protocol.md` (preregistered / frozen at commit `75884b52efb7ce5694f3e2afaf7097b28d0697e2`). This document must not be modified after private results are visible. | The scoring protocol is pinned at a specific commit. Any modification after private results are visible is detectable via `git log` / `git diff` and must be treated as a freeze break (scoring-protocol.md:6-20). The run manifest records the scoring protocol commit SHA. |

### Ways teams could diverge and flatter themselves
- Using a different top-K for stage-0 candidate selection → BM25 stage-0 is top-500 pinned; a different K changes the evidence packet and is a different system, not the baseline.
- Counting tokens with whitespace estimate instead of the pinned tokenizer → explicitly rejected (`build_packet` raises ValueError for `exact=True` without tokenizer).
- Tuning sufficiency thresholds on private test items → anti-leak rule; voided run.
- Modifying the scoring protocol after seeing private results → detectable via git; protocol break.

**Enforcing mechanism preference:** Executable checks over prose. Unit tests: (1) `test_questions_sha256` asserts questions.json hash matches manifest; (2) `test_generator_config_pinned` asserts generator config fields match the fixed values; (3) `test_token_count_method_rejected` asserts `estimate_tokens` is not accepted for empirical runs.

---

## 3. The Primary Metric Set

Every metric has an explicit formula, and each is classified as **MEASURED** (collected via stdlib telemetry), **ESTIMATED** (replaced by a custodian-scored harness measurement in Phase 4), or **NOT YET MEASURABLE** on desktop.

| Metric | Formula | Classification | Notes |
|---|---|---|---|
| **Required-evidence survival per stage** (stage_coverage) | `|E ∩ C_s| / |E|` where E = required evidence set for an item, C_s = candidates surviving stage s. Computed at paragraph granularity. | MEASURED | Derived from stage traces (candidate_ids). Denominator = number of required evidence atoms for the item. |
| **Stage-0 recall** | `recall@K` at K=500 against the required evidence set. | MEASURED | `eval/metrics.py:32-37` — traditional recall@k against canonical ids. |
| **Candidate reduction ratio** | `(candidates_out / candidates_in)` per stage. | MEASURED | Ratio of surviving candidates to entering candidates, per stage. |
| **Final evidence recall** | `|E ∩ final_packet_citations| / |E|` where final_packet = the packed evidence packet handed to the generator. | MEASURED | Counts exact_evidence_tokens‑matched citations in the final packet against required evidence E. |
| **Evidence token cost** | `exact_evidence_tokens` from the EvidencePacket (or `None` if not measured). | MEASURED | Exact model-tokenizer count; `token_estimate` (whitespace) is INFRA-ONLY and never reported as a measurement. |
| **Context precision** | `leaf_precision` = exact hits / n_retrieved, from `eval/support.py:context_precision_report`. | MEASURED | Exact matches on leaf node ids only; ancestry-expanded ids are never fed into precision inputs. |
| **Abstention accuracy** | `sufficiency_accuracy` = (correct_abstention + answered_answerable) / n_labeled, from `eval/metrics.py:abstention_summary`. | MEASURED | Correct abstentions on unanswerable items + correct answers on answerable items, over all labeled items. |
| **Latency** | `total_latency_ms` from `RetrievalOutcome` (perf_counter deltas in MILLISECONDS). | MEASURED (on desktop) | Model-loading + inference timed via `timed_phase`. Model-loading latency may be `None` if not separated. |
| **RAM** | `peak_rss_mb` from `MemoryReading` (calling-process peak RSS in MEBIBYTES). | MEASURED (on desktop) | `resource.ru_maxrss` / Linux; explicitly not Android‑derived. |
| **Storage** | `storage_bytes` from `RetrievalOutcome`; `storage_manifest` total_bytes. | ESTIMATED (index); MEASURED (per-file sizes) | Index storage estimated from binary size; per-file sizes measured via `os.path.getsize`. Generator artifact (~1 GB) is shared and excluded from per-baseline cost. |

### Tie-breaking rule
**Required-evidence survival per stage → Stage-0 recall → Candidate reduction ratio → Final evidence recall → Evidence token cost → Context precision → Abstention accuracy → Latency → RAM → Storage.**

If two architectures produce identical numbers on the primary metric chain, the tie breaks toward the system with the **lower evidence token cost**, then **lower latency**, then **lower RAM**, then **lower storage**. If all are identical, the result is a true tie.

**Judge dependency:** No primary metric depends on the `google/flan-t5-large` judge. The judge is UNPINNED and ABSENT (accepted risk #4); secondary generated-answer metrics are ABSENT for all baselines. The primary metrics are purely retrieval/evidence metrics that require no judge.

---

## 4. Null / Floor Analysis

**This section now contains a power calculation.** Until 2026-10-03 it did not
(accepted risk #2, STATUS.md). With 206 worker-visible items (train 60 / dev 59 /
shadow_dev 87) and 116 private items in 62 groups, the corpus turns out to be
underpowered for most architecture pairs, not merely for close ones — see the
corrected table below for the magnitude.

### Minimum meaningful difference

We use a **Wilson-interval overlap argument** on a per-item proportion:

- For a binary survival metric (e.g., "required evidence survives stage s"), each item i yields a Bernoulli outcome (1 = survives, 0 = pruned).
- The per‑item survival rate for an architecture is `p = hits / n` where n = 206 (worker‑visible items) or n = 87 (dev‑only) or n = 59 (dev‑only).
- The Wilson 95% confidence interval for a proportion `p = hits/n` with `z = 1.96` is:
  ```
  center = (p + z²/(2n)) / (1 + z²/n)
  half  = z * sqrt(p*(1-p)/n + z²/(4n²)) / (1 + z²/n)
  CI = [max(0, center - half), min(1, center + half)]
  ```

- **Minimum meaningful difference** = the smallest gap between two architectures' Wilson CI upper/lower bounds that we would treat as real.

> **ORCHESTRATOR CORRECTION (2026-10-03).** The derivation that originally stood
> here was wrong, and its own worked example refuted it: it computed
> 51/59 vs 49/59 as `[0.803, 0.991]` vs `[0.766, 0.959]` — intervals that overlap
> across almost their whole width — then asserted three lines later that
> 53/59 vs 47/59 "gives non-overlapping CIs", which it does not
> (`[0.795, 0.953]` vs `[0.677, 0.880]`). The reported thresholds were roughly
> **half** the true values. Corrected numbers below, computed by exhaustive scan.

**Method.** For each split, take the stronger system at a realistic 90%
operating point and find the smallest hit-count gap at which the *weaker*
system's Wilson upper bound falls below the *stronger* system's lower bound.
Scanning every `n` by hand is where the original went wrong; this is a scan.

**Corrected minimum meaningful difference** (Wilson 95% non-overlap, stronger system at 90%):

| split | n | stronger | weaker | **gap** | as pp | the two intervals |
| --- | --- | --- | --- | --- | --- | --- |
| dev | 59 | 53 | 40 | **13 items** | 22.0% | [0.795, 0.953] vs [0.551, 0.783] |
| shadow_dev | 87 | 78 | 63 | **15 items** | 17.2% | [0.815, 0.945] vs [0.622, 0.807] |
| dev + shadow_dev | 146 | 131 | 113 | **18 items** | 12.3% | [0.837, 0.937] vs [0.700, 0.834] |
| private (sealed) | 116 | 104 | 88 | **16 items** | 13.8% | [0.828, 0.940] vs [0.673, 0.827] |
| all worker-visible | 206 | 185 | 164 | **21 items** | 10.2% | [0.849, 0.932] vs [0.736, 0.845] |

**Independent cross-check.** A two-proportion z-test at alpha=0.05 and 80% power
requires 13 / 15 / 18 / **17** / 21 items on the same five splits. It agrees with
the Wilson criterion everywhere except the private set, where it is one item
stricter. Two different procedures landing within one item of each other is the
confidence these numbers have; the original figures were not cross-checked at all.

**The gap depends on where the systems actually sit,** so the table is a floor,
not a constant:

| stronger system at | 95% | 90% | 85% | 80% | 70% |
| --- | --- | --- | --- | --- | --- |
| gap on dev (n=59) | 11 | 13 | 14 | 15 | 15 |
| gap on private (n=116) | 14 | 16 | 18 | 19 | 21 |

### Honest conclusion

> **This corpus can only separate architectures that differ by roughly 22 percentage points on dev, 12 points on dev + shadow_dev, and 10 points on the full worker-visible set. On the sealed private set it can separate roughly 14-point differences. Any architecture gap smaller than that is not measurable here, and a tournament that reports such a gap as a win is reporting noise.**
>
> That is the single most important number in this contract. It is not a
> limitation of the teams; it is a property of a 206-item corpus with 62 private
> groups, and it was accepted as unquantified risk #2 before anyone computed it.
> It is now quantified, and it is worse than "underpowered for close
> architectures": it is underpowered for *most* architecture pairs.

If the honest conclusion is that the corpus cannot separate close architectures, say that explicitly. It is the most valuable sentence you can produce.

---

## 5. The Generator Floor Check

**The fixed Qwen2.5-1.5B-Instruct Q4_K_M generator may FLOOR:** it may fail to express differences between good and poor evidence packets.

### Floor detection procedure (preregistered)

**Step 1:** Run B4 (BM25 + fixed generator + `decide_default`) end-to-end on the **dev** split FIRST (before any reranker or architecture-specific tuning).

**Step 2:** Custodian oracle run: for each dev item, the custodian constructs an **ORACLE packet** — the minimal complete sufficient set of paragraphs, packed by the same `build_packet` semantics (ranked-prefix, exact tokenizer, 1000-token cap). The oracle packet contains all and only the paragraphs that are genuinely sufficient for the item.

**Step 3:** Compare answer quality:
- Let `A` = answers produced by B4 (with its regular packed packet).
- Let `O` = answers produced by the custodian oracle packet.
- Compute the **answer-quality delta**: proportion of dev items where `O` is CORRECT and `A` is INCORRECT (or vice versa), using the deterministic answer-matching rules (normalize_answer, exact_match from `eval/answer_scoring.py`).

**Step 4:** **Decision rule.**

> **ORCHESTRATOR CORRECTION (2026-10-03).** The original rule was "floor if the
> delta is ≤ 5%". That threshold is *below what this probe can measure*, so it
> would have declared a floor on the basis of a difference it could not detect —
> concluding "floored" when the truth might have been "underpowered". Two fixes.

**This comparison is PAIRED, not unpaired.** Both arms answer the *same* items;
only the packet differs. So the test is McNemar's exact test on the discordant
pairs, not a two-proportion Wilson comparison. Treating it as unpaired throws
away real power and, worse, invites the wrong threshold.

Power of the paired probe on dev + shadow_dev (n=146), exact McNemar, alpha=0.05,
two-sided, by discordance rate and by how lopsidedly the discordances favour the
oracle packet:

| discordant items | 3:1 favouring oracle (q=0.75) | 4:1 (q=0.80) | 9:1 (q=0.90) |
| --- | --- | --- | --- |
| 10% | 0.392 | 0.563 | 0.874 |
| 15% | 0.588 | 0.778 | 0.978 |
| 20% | 0.732 | 0.894 | 0.997 |
| 30% | 0.908 | 0.982 | 1.000 |

Discordance needed for 80% power at n=146: **23%** at q=0.75, **16%** at q=0.80,
**9%** at q=0.90. (Validated: power 0.031 under a pure-null direction, 1.000 when
every discordance favours the oracle.)

**The three-way rule.** Let `d` be the observed discordance rate and let the
McNemar interval for the oracle's advantage be `I`:

- **`I` excludes 0** → the generator does **not** floor. Proceed.
- **`I` includes 0 and its upper bound is below the minimum meaningful
  difference** → the generator **FLOORS**. You have bounded the benefit of
  perfect evidence below anything this corpus could call real. **STOP and
  report** before burning rerank effort.
- **`I` includes 0 and its upper bound exceeds the minimum meaningful
  difference** → **INCONCLUSIVE / UNDERPOWERED.** This is the case the original
  rule silently collapsed into "floor". It must be recorded as its own outcome.
  The remedy is more items or a more sensitive probe, not a verdict.

Note the asymmetry that makes this probe worth running early: a *large* oracle
delta is cheap to detect, so the probe can prove the generator is **not** floored
even though it cannot resolve small effects. Run it before the tournament, not
after.

### What happens to the tournament if the floor is found

If the generator floor is found:
- **All subsequent quality metrics are uninterpretable** above the floor. The correct scientific output is "the generator floors on this corpus; the retrieval tournament cannot distinguish architectures above the generation floor."
- The tournament **stops** and reports the floor finding. Any architectures that claim superiority based on private‑run results are suspect, because the floor means the generator cannot express the difference.
- The baseline lead (B4) is acknowledged as the correct floor configuration; the kill condition (§0 of HYPOTHESIS.md) is moot because the generator cannot express differences.

### Is the custodian oracle-packet probe legitimate under the custody rules?

**Yes, the probe is legitimate** under the custody rules, with one refinement:

- The **custodian** may use an oracle packet because the custodian has access to the ground-truth required evidence sets and can construct the minimal sufficient set. The custodian is the sole party that may run the oracle probe; it is part of the custody infrastructure.
- **A WORKER may NOT** construct or use an oracle packet during their run, because that would hand the worker the answer's location and sufficient-set information, violating the model-facing boundary (`to_model_query` allows only `question_id` and `text`).
- **Refinement:** The oracle packet must be constructed by the custodian outside the worker's runtime, using only publicly available data (the question text, the corpus, the pinned generator config). The oracle packet's spans are determined by the custodian's analysis of the required evidence set, but the packet itself is packed using the same `build_packet` function with the pinned tokenizer — so the packing policy is identical. The only difference is which spans are included, which is determined by the custodian's knowledge of the ground truth.

The probe is legitimate because:
1. The custodian runs it **separately**, not as part of the architecture's end-to-end pipeline.
2. The packing (`build_packet`) and tokenizer are identical — the only difference is the span selection, which is the custodian's ground-truth knowledge.
3. The probe's verdict (floor or not) is reported as a **custodian-scored infrastructure check**, not as an architecture result.

**What happens if the probe finds the floor:** The tournament stops and reports the floor. The correct scientific output is "the generator floors; retrieval differences do not manifest in answer quality." If the probe does NOT find the floor, the tournament proceeds with the understanding that the generator can express differences, and the retrieval metrics (recall, survival, etc.) are the primary comparability metric.

---

## 6. What Would Make Us Recommend Abandoning a Family

**Kill condition (preregistered, from HYPOTHESIS.md §0):**

> **If BM25 + one small reranker matches a full cascade within the minimum meaningful difference**, the correct scientific output is "the cascade is unnecessary" — specify exactly how that result must be RECORDED so it cannot be buried or reframed.

### Concrete kill condition and recording protocol

**The kill condition:** On dev + shadow-dev (the 146 visible items), if **B1 (BM25 only)** or **B4 (BM25 + fixed generator floor)** achieves a required-evidence survival metric within the **minimum meaningful difference** of the full cascade (or B3 + rerankers), then the cascade is unnecessary on this corpus.

**Minimum meaningful difference** = the Wilson CI non-overlap threshold computed in Section 4. For the dev + shadow_dev combined set (n = 146) the threshold is **18 items = 12.3 percentage points**, not the ≈ 14 items / 9.6% originally stated here.

**Exact recording protocol — cannot be buried or reframed:**

1. **Record the kill condition result in the run manifest** under a new key `kill_condition: { "met": true/false, "system": "B1" or "B4" or "B3", "metric": "required_evidence_survival", "value": <number>, "minimum_meaningful_difference": <number>, "wilson_ci": { "lower": ..., "upper": ... } }`.
2. **Record the per-item survival traces** (candidate_ids surviving each stage) in the raw traces, so the calculation is reproducible.
3. **Record the Wilson CI parameters** (hits, n, z=1.96) so the interval can be recomputed.
4. **Record the full cascade's metric value** for comparison.
5. **Publish the kill condition result in the tournament summary** with the headline: "Kill condition met: BM25 + small reranker matches cascade within Wilson CI; cascade unnecessary on this corpus."
6. **The result must NOT be reframed** as "the cascade works but BM25 is close." If the kill condition is met, the output is "the cascade is unnecessary." If it is not met, the output reports the actual delta.

**What would make us recommend abandoning a family:** If the baseline B1 (or B4) achieves, e.g., 0.89 required-evidence survival on dev+shadow-dev, and the full cascade achieves 0.90, and the Wilson CI at n=146 shows non-overlap (i.e., the gap is ≥ 18 items), then the cascade IS distinguished and the family is NOT abandoned. If B1 achieves 0.89 and the cascade achieves 0.91 but the Wilson CI shows overlap (gap < 18 items), then the correct output is "the cascade is unnecessary — no statistically meaningful difference was detected."

**Preregistrated kill conditions for each family:**
- **B1 (BM25 only):** kill if B1's required-evidence survival on dev+shadow-dev is within Wilson CI of the cascade's survival.
- **B2 (BM25 + static reranker):** kill if B2's survival is within Wilson CI of B1's survival (since B2's prediction is that it adds little or nothing over B1).
- **B3 (68M reranker ceiling):** kill if B3's survival is within Wilson CI of B1's survival (since B3's prediction is that the reranker only reorders; if it doesn't add survival, it's unnecessary).
- **B4 (floor):** the generator-floor verdict is NOT a kill condition and NOT a binary. It is three-way — no floor / floor / underpowered — per Section 5. A tournament may not record `underpowered` as `no floor`.

**The cascade is unnecessary** is the correct scientific output when the kill condition is met. It must be recorded as specified above and cannot be buried or reframed.

---
---
---
*End of CONTRACT.md*