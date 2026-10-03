# Round 1 Baselines — Implementation Plan (Mise-en-Place)

Status: READINESS PLAN. No code, no measurements, no private data.
Companion: `HYPOTHESIS.md` (the spec: four systems at implementation level,
pinned ids, exact tie-breaking, preregistered predictions, kill condition).
This file is the how, in order, with entry/exit gates. Frozen substrate
`round0-freeze-r1` (`a0e7534`). All DESKTOP. No Android claim.
Generator FIXED (`qwen25-1.5b-q4km-fixed-v1`) — no generator work exists in
this plan by design. No synthetic data is created at any phase, so the
custodian leakage gate is never triggered for this team (recorded, not
skipped).

The systems, in build order:

| Id | System | Weights | Role |
|---|---|---|---|
| B1 | BM25 / lexical only (§3 of HYPOTHESIS) | none | retrieval spec; shared stage-0 |
| B4 | B1 + shared packing + `decide_default` + fixed generator | none (shared 1 GB generator) | the true floor; generator-floor probe; KILL-CONDITION configuration |
| B2 | B1 ∪ static semantic channel (Borda) | static-retrieval-mrl-en-v1 | cheapest semantic falsifier |
| B3 | B1 stage-0 → 68M cross-encoder → top-50 → pack | ettin-reranker-68m-v1 | expensive-but-simple ceiling |

## Phase 0 — Pin and verify (gate: every hash recorded or STOP)

1. Re-resolve all four revisions via the Hub API and compare with the
   HYPOTHESIS.md §4.1/§5.1 observations of 2026-10-03:
   - `sentence-transformers/static-retrieval-mrl-en-v1` → expect
     `f60985c706f192d45d218078e49e5a8b6f15283a`
   - `cross-encoder/ettin-reranker-68m-v1` → expect
     `d166fa88ddde3c42bc3ee92f7df476d941c8204a`
   - `cross-encoder/ettin-reranker-17m-v1` → expect
     `9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` (record-only; needed only if
     the orchestrator assigns the 17M single-reranker baseline to this team)
   - `cross-encoder/ettin-reranker-32m-v1` → expect
     `b33e5ceb5110773ea9cf5e00c9bedc83a8c2afdd` (record-only)
   On drift: re-verify HYPOTHESIS.md §4/§5 against the new tree, record the
   drift, then proceed. No silent swap.
2. Download at the resolved revisions. Record in the run manifest per model:
   model id, revision SHA, weight-file sha256 + bytes, `config_sentence_transformers.json`
   bytes (static), `config.json`/`modules.json` bytes (ettin), `tokenizer.json`
   sha256 + bytes.
   - Static: assert `0_StaticEmbedding/model.safetensors` = 125,018,208 B and
     `tokenizer.json` = 711,396 B; assert the loaded tensor shape is
     `(30522, 1024)` fp32 — if the geometry differs from the DERIVED value,
     STOP (the HYPOTHESIS §4.1 derivation was wrong and §4.4 storage math
     must be redone).
   - 68M: record `model.safetensors` bytes (expect ≈ 272,578,560 B) and
     `onnx/model_qint8_arm64.onnx` presence + bytes (closes the peer-claim
     check on-disk, HYPOTHESIS §5.2).
3. Environment pins (recorded in the run manifest, exact versions):
   - Python: system python3 (Arch), stdlib only for B1 (no third-party import
     in the BM25 path — the bit-exactness claim of HYPOTHESIS §8.1 depends on
     it).
   - `sentence-transformers==3.3.0` (the version `config_sentence_transformers.json`
     records for the static model), matching `transformers`/`torch` (CPU)
     versions recorded.
   - `onnxruntime` pinned version for the Phase 3 parity variant only.
   - Determinism environment for ALL model inference: `OMP_NUM_THREADS=1`,
     no CUDA, fixed working directory, no parallel map.
4. Corpus integrity (fail closed): assert `corpus/corpus.jsonl` sha256 =
   `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64`
   (revision `pilot-297-r1`, 43,876,251 B) and
   `corpus/scale/distractor.jsonl` sha256 =
   `516463e340de8c53…` (per `corpus/scale/scale_build_manifest.json`); assert
   node counts 113,951 / 300,041; assert `worker_regime_b_exclusions()`
   loads 21 titles (source sha `0173a926…`) — record only; no baseline
   component ever consumes the list (§2.6 of HYPOTHESIS: Regime A ≡ B by
   construction).
   EXIT GATE: every hash above in the run manifest, or STOP.

## Phase 1 — BM25 (B1) implemented and measured (gate: bit-exact + measured)

1. Implement exactly per HYPOTHESIS §3 (unit = paragraph; `D(p)` with the
   `(lead)` omission; NFKC → casefold → `[a-z0-9]+`; no stemming; no
   stopword list; k1 = 1.2, b = 0.75; natural-log BM25, double, prescribed
   op order; top-500 by (score desc, node_id asc)). Packed binary index +
   JSON audit export; both sha256-pinned.
2. Deterministic tests first (stdlib `unittest`; each names the defect it
   catches):
   - `test_bm25_hand_score`: hand-computed BM25 scores on a 3-document toy
     corpus + a 20-document fixture from the real corpus (byte-exact doubles
     vs hand evaluation). Catches: formula/constant/rounding regressions.
   - `test_bm25_bit_exact`: two independent builds + two query runs →
     bit-identical score lists. Catches: op-order or dict-iteration drift.
   - `test_heading_placeholder`: `(lead)` omitted for exactly 297 documents;
     `D(p)` for a known paragraph byte-identical to the expected string.
     Catches: off-by-one in the omission rule or heading joining.
   - `test_index_stats`: N = 9,979 (core) / 36,609 (merged); `avgdl`, `df`,
     `tf` spot-checked against independent counts. Catches: index-build
     corruption silently zeroing or inflating recall.
   - `test_no_overlap_zero`: a query with no corpus overlap returns the empty
     positive set, never a padded list. Catches: top-K logic emitting
     zero-score documents.
   - `test_tie_break_total_order`: crafted equal scores → node_id byte-order
     decides; full candidate list is a permutation in the total order.
     Catches: unstable sorts that let two implementations diverge.
   - `test_query_contract`: the retriever accepts only
     `to_model_query` outputs; a payload carrying `split`/`question_type`/
     `group` raises `ForbiddenMetadataError`. Catches: label-metadata leaks
     into retrieval inputs (tournament-invalidating).
   EXIT GATE: all green before any benchmark number is produced.
3. Measure (replace every ESTIMATE in HYPOTHESIS §3.4/§9; `timed_phase`,
   `storage_manifest`, `proc_peak_rss_mb`, three runs, median/p95):
   - index bytes (binary + JSON), build time, RAM — core AND merged tier
     (the merged build is also Phase 5's input).
   - query latency over the 206 worker-visible question texts.
   - `test_stage0_recall_floor` (synthetic toy corpus, hand-listed required
     node in top-K) guards the tokenizer from silently zeroing recall.
   Recall@{10,50,100,200,500} on dev/shadow-dev is custodian-scored in
   Phase 4 — workers see no labels; no local recall number is a substitute.

## Phase 2 — Static channel (B2) (gate: reference agreement + cost measured)

1. Build the reference embedder from the pinned static revision
   (sentence-transformers 3.3.0, fp32, CPU, single-threaded). Assert the
   Phase 0 shape check again at load time. Embed `D(p)` for all 9,979 core
   and 36,609 merged paragraph documents; cache the fp32 vectors
   (sha256-pinned artifact; int8 variant produced from the cache, recorded
   separately — never a separate embedding pass).
2. Determinism + re-implementation agreement:
   - two reference runs → byte-identical top-500 lists (20 dev questions as
     fixture).
   - any fast re-implementation (e.g., numpy over the fp32 table) must match
     the reference top-500 SET on the same 20-question fixture or is
     rejected (HYPOTHESIS §8.2 — set equality, not cross-language bit
     equality).
   - `test_static_input_identity`: the static channel's document string is
     byte-identical to the B1 index document string for all N documents.
     Catches: channel divergence (two different "corpora" being fused).
   - `test_borda_fusion`: integer Borda sums incl. the 501-fallback,
     one-list-only candidates, and a crafted tie → node_id break. Catches:
     floating-point creep or off-by-one ranks in the union.
3. Measure indexing cost at BOTH tiers (HYPOTHESIS §4.4 table): build time,
   vector-cache bytes (fp32 40,873,984 B core / 149,950,464 B merged
   DERIVED — confirm), RAM, query-time latency (query embed + GEMV).
   MRL-truncation and int8-ONNX variants are options only: off unless
   storage forces it, and any use requires a recorded dev quality check.
4. Disjoint-recall arbiter (custodian-scored, preregistered in HYPOTHESIS
   §4.5): static-only recall@500, BM25-only recall@500, union recall@500,
   and static-disjoint contribution = required host paragraphs ranked ≤500
   by static but not by BM25. **If static-disjoint ≥ ~5% of required
   paragraphs on dev+shadow-dev, the §4.5 prediction is refuted and the
   union keeps its stage.** If it does not fire, the finding is recorded:
   "cheapest semantic channel adds nothing measurable over specified BM25
   on this corpus" — stated in the final report either way.

## Phase 3 — Reranker ceiling (B3) (gate: reference deterministic + parity recorded)

1. Load the pinned 68M checkpoint (fp32, single-threaded, `batch_size=1`,
   document input = paragraph `p:text` verbatim, query = `QueryInput.text`
   verbatim — HYPOTHESIS §5.3). `score_kind="logit"`, top-K(50) policy only
   (no threshold, no sigmoid, no probability claim; `none_ranking_only`).
2. Determinism: two reference runs on 5 dev questions → identical logit
   lists and identical top-50 total orders (re-run determinism is the claim;
   cross-runtime bit equality is NOT claimed, HYPOTHESIS §8.4).
3. Measure the ceiling's cost honestly (this number is a headline datum):
   per-query wall time for 5 dev questions single-threaded fp32
   (500 cards), plus the int8 ORT multi-threaded variant's wall time;
   peak RSS both ways. HYPOTHESIS §5.4's ESTIMATE range (10²–10³ s
   single-threaded) is either confirmed or corrected — a slower measurement
   only STRENGTHENS the kill condition.
4. Parity gate for the int8 deployment variant: top-100 Spearman rank
   correlation ≥ 0.99 vs fp32 reference AND final-completion delta ≤ 1 item
   on 10 dev items, else int8 stays deployment-only and fp32 remains the
   reportable ceiling (HYPOTHESIS §5.4).
   `test_logit_never_probability`: no threshold path exists on raw logits in
   B3; `validate_score_value` rejects feeding B3 scores to ECE/Brier.
   Catches: calibration-category fraud on the ceiling baseline.

## Phase 4 — End-to-end runs on dev / shadow-dev (gate: telemetry complete)

Order matters; B4 first, always.

1. **B4 + generator-floor check (STATUS risk 3, this team's):**
   - Run B4 on dev (59 items) end-to-end through `run_question`
     (`decide_default`, fixed generator, exact-tokenizer packing, shared
     per-article cap 3, strict 1000-token cap).
   - Custodian oracle run: same fixed generator, ORACLE packets (minimal
     complete sufficient sets packed with the same `build_packet` semantics)
     — custodian-side only; workers never see the atoms.
   - Degraded control: B4's BM25 BOTTOM-ranked paragraphs as the packet.
   - DECISION (preregistered): if answer-quality delta (oracle vs B4) ≈ 0
     within CI, the generator floors — STOP and report before further
     baseline work; the tournament measures nothing above the floor. If the
     oracle beats B4 and B4 beats the degraded control, the floor has
     headroom and Phases 4.2–4.4 proceed.
2. Run B1 (as a retrieval-only record: stage-0 candidate lists, no packet),
   B2, B3 on dev + shadow-dev. All through the frozen `eval/` harness with
   custodian scoring. Per HYPOTHESIS §7, report per stage: `stage_coverage`,
   `survival_curve` (pruned stays pruned), `conditional_retention` WITH
   numerator/denominator, `lost_and_recovered`, plus final
   `sufficient_set_completion`, `best_fractional_coverage`,
   `leaf_precision`, `overshoot_tokens`, exact evidence-token cost,
   abstention outcomes. Wilson CIs on every rate; denominators always shown;
   a null result is reported as UNDERPOWERED (accepted risk 2), never as
   equivalence.
3. Kill attribution: for every dev/shadow-dev item with final completion 0,
   walk the `survival_curve` backward and attribute the kill to the first
   stage that dropped the last surviving sufficient set, with item id, the
   stage settings (k1/b/K/caps), and the killed paragraph's rank/score.
   This is what tells the cascade teams WHERE complexity would have to pay.
4. **Kill-condition check (HYPOTHESIS §0):** B4 vs full cascade — pending the
   cascade team's private-run completion. On dev+shadow-dev, if B4 matches
   the cascade within Wilson-CI overlap on required-evidence completion AND
   final evidence recall, the report states: the cascade is unnecessary on
   this corpus; B4 (zero weights, ms-class, ~15–40 MB index) is the
   deployment. Threshold/config freeze (k1, b, K, caps, revisions, weight
   hashes, library versions, seed log) into the run manifest BEFORE any
   private run; no re-tuning on shadow-dev; thresholds dev-selected only
   (and none is needed: all four systems are top-K by design).

## Phase 5 — Scale tier (core + 940) (gate: displacement recorded)

1. Use Phase 1/2 merged artifacts (36,609 docs). Re-measure index bytes,
   build time, query latency at the merged tier (HYPOTHESIS §9 merged row).
2. Run B1/B4 (and B2/B3 if Phase 4 timing allows) on 10–20 dev questions
   against the merged corpus; report via
   `eval/scale_analysis.compare_scale_tiers`: known-support recall@K
   displacement, reduction ratio, `unjudged_top_k` + `limitations` per item.
   Because the adjudication rule is NOT yet wired into `eval/metrics.py`
   (accepted risk 6): report BOTH the raw series and the standalone
   `eval/scale_adjudication.py` series, with the break annotated. No scale
   retrieval auto-counts as a false positive. No Android claim; no
   precision claim beyond what `compare_scale_tiers` emits.

## Phase 6 — Freeze and report

1. Run-manifest freeze: every config value, revision + weight sha256,
   library version, seed log, index-artifact sha256, measured cost table
   (index vs weights, RAM, latency class, at BOTH tiers), all survival
   metrics with denominators, Wilson CIs, kill-attribution ledger,
   Regime-A ≡ Regime-B attestation (byte-identical outputs, vacuous
   adaptation set), and the static-disjoint-recall verdict.
2. Final report answers, in order: (a) which baselines survived and by how
   much; (b) the kill-condition verdict (or "pending cascade"); (c) the
   static-stage finding (HYPOTHESIS §4.5 — confirmed or refuted with the
   measured disjoint recall); (d) the ceiling's measured cost; (e) the
   generator-floor verdict; (f) verification log (HYPOTHESIS §11) plus any
   drift found in Phase 0.
3. Hand the re-resolution record (revisions + weight sha256s) to the
   custodian's pin inventory. This team's files remain the record of what
   was specified and measured; no pin in this directory overrides the
   freeze inventory.

## What this plan will NOT do (hard constraints, repeated)

- No reading of private questions/labels/review/authored material; the
  in-repo opaque `corpus/private_test_manifest.json` and the private schema
  are the only allowed boundary artifacts, and they were not even needed.
- No private evaluation, no tuning on private results, no threshold fitting
  on shadow-dev (a dev-only set; shadow-dev is confirmation-only, and here
  there is nothing to tune — all four systems are top-K by design).
- No generator tournament, no prompt/sampling variation, no sufficiency
  model beyond `decide_default`.
- No synthetic training/adaptation data (leakage gate not applicable;
  recorded as such), hence Regime B's 21-document exclusion is vacuous and
  the 21 articles remain in every query-time corpus.
- No Android or on-device performance claim from any number here.
- No paid endpoint, no subagent spawning, no nested work.
