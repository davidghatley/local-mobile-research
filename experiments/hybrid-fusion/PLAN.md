# Hybrid Fusion — Gated Work Plan (Experiment Lead E)

Status: PLAN ONLY. No implementation, no training, no private evaluation.
Frozen substrate: tag `round0-freeze-r1`.
Worker endpoint: `opencode/muse-spark-1.3-contributor-free` (VERIFIED zero-cost).
No subagents. No paid fallback.
Operationalises `experiments/hybrid-fusion/HYPOTHESIS.md` (sound, verified;
all four revision commits match the live Hub). Do not re-litigate it here.
All measurements DESKTOP. No Android or on-device claim.

Companion: `HYPOTHESIS.md` (the why). This file is the how, with gates.

## Global conventions (bind every phase)

- **Number labels.** Every cost/latency/RAM/storage number is tagged
  `[MEASURED]` or `[ESTIMATED]`, never bare. Hub-API-observed byte counts
  (e.g. int8 ONNX 31,259,319 B) are `[MEASURED-remote]`; they become
  `[MEASURED-local]` only after Phase 0 weighs the downloaded bytes.
  All latencies, RSS, and index sizes below are `[ESTIMATED]` until the
  phase that measures them says otherwise.
- **Numbers Phases 0-1 replace with measurements:** weight-file sha256 +
  byte counts for both channels; self-exported ONNX bytes + sha256;
  tokenizer bytes; BM25/tokenizer pack path timings; Stage-0 recall;
  per-channel index-build `timed_phase` latency; `proc_peak_rss_mb`;
  retrieval `total_latency_ms`; per-file `storage_bytes`. Anything still
  `[ESTIMATED]` after Phase 1 is carried explicitly into the run manifest
  as `None` (explicitly not measured), never silently zeroed.
- **Query contract.** Model-facing input is `QueryInput(question_id, text)`
  ONLY via `substrate/query.py`. Any payload carrying `split`,
  `question_type`, or `group` to a model-facing entry point must raise
  `ForbiddenMetadataError` (§9 test 6).
- **Regime B.** Exclusions are the PUBLIC 21-document list ONLY, read ONLY
  via `substrate.query.worker_regime_b_exclusions()`. Query-time corpus is
  identical under both regimes. The headline (RRF, untrained) is
  Regime-A-identical-to-Regime-B BY CONSTRUCTION; only ablation A2 (learned
  combiner) produces paired A/B runs and a paired delta.
- **Generator FIXED.** `qwen25-1.5b-q4km-fixed-v1`, fixed prompt
  (`PROMPT_HASH` verified in `validate_freeze`, not just `is_pinned()`),
  `build_packet(exact=True, tokenizer=<pinned>)`, strict 1000-token cap,
  ranked-prefix, per-article cap 3. No generator tournament.
- **Private seal.** Never read `questions.json` private items, `labels.json`,
  `review/`, or `authored/`. `corpus/private_test_manifest.json`
  (counts/hashes) and the private schema are fine. No private evaluation,
  no tuning on private results — ever.
- **Corrections applied (authoritative where stricter than HYPOTHESIS.md):**
  (a) Leakage gate DOES issue PASS now (one-shot clearance session;
  `R1_CONTRACT_ERRATUM.md` E-1 supersedes HYPOTHESIS §6.2's "refuses PASS").
  (b) Minimum meaningful difference uses the corrected CONTRACT §4 scan:
  dev 13 items / 22.0 pp, dev+shadow-dev **18 items / 12.3 pp**, private
  16 items / 13.8 pp — NOT HYPOTHESIS §1's stale ~14/146 (9.6%).
  (c) Generator floor uses the CONTRACT §5 three-way McNemar rule
  (no-floor / floor / underpowered) — NOT HYPOTHESIS §10's stale ≤5% rule.
- **Kill condition as gate (from HYPOTHESIS §1.3, with corrected MMD):**
  > If the headline fused system's sufficient-set completion on
  > dev+shadow-dev is within Wilson-CI overlap of B1 (gap < 18 items on
  > n=146 at 95% confidence, z=1.96), OR the learned sparse channel's
  > packet-level disjoint recall over BM25 is < 5%, then fusion added
  > nothing measurable: the honest headline is "the hybrid is unnecessary —
  > BM25 alone is sufficient at a fraction of the cost." Recorded in the run
  > manifest under `kill_condition` with Wilson parameters (hits, n,
  > z=1.96) and per-item survival traces. NOT reframed.
  This condition gates Phases 2, 3, and 6 (see each exit criterion).

## Phase 0 — pin resolution

Owner: Pin / Provenance Owner.
Entry gate: frozen tag `round0-freeze-r1` checked out; sanitized worktree
(no private directory); HYPOTHESIS.md §§3-4 read and accepted as the pin
list (moving-head SHAs below are re-resolve targets, not pins).

Steps:

1. Re-resolve each repo's current main-head commit SHA via the Hub API:
  `opensearch-neural-sparse-encoding-v2-distill` (was
  `269e6638b2c4...` [MEASURED-remote 2026-10-03]),
  `static-retrieval-mrl-en-v1` (was `f60985c706f1...` [MEASURED-remote]),
  plus the two recorded non-selections if cited (`naver/splade-v3`
  @ `fdfeceb91d7b...`, cc-by-nc-sa-4.0; v1 @ `708f7e68f4aa...`).
  Record observed-vs-expected; any drift is a manifest entry, not a silent
  substitution.
2. Download weights; record per-file sha256 + byte counts
  (`pytorch_model.bin`, `model.safetensors`, `tokenizer.json`, `vocab.txt`
  for the sparse channel; fp32 table + `onnx/model_int8.onnx`
  [MEASURED-remote 31,259,319 B] + `0_StaticEmbedding/tokenizer.json`
  [MEASURED-remote 711,396 B] for the static channel). All become
  `[MEASURED-local]`.
3. DELIVERABLE — self-export the learned-sparse channel to ONNX (ships
  none): export via `optimum`/ORT, record exporter versions, exported
  bytes + sha256, and a rank-parity check (fp32 vs ONNX top-500 agreement
  on a fixed dev fixture; disagreement count reported, threshold
  preregistered before running it). Quantised-quality parity (int8 vs
  fp32 rankings) is measured here if an int8 variant is produced.
4. Record licence per channel (sparse v2-distill apache-2.0, static
  apache-2.0, splade-v3 cc-by-nc-sa-4.0 exclusion reason) in the manifest.
5. Write the run-manifest skeleton: repo ids, resolved SHAs, weight-file
  sha256/bytes, tokenizer bytes, ONNX artifact sha/bytes + exporter pins,
  corpus + questions sha256, generator config sha256, master seed +
  `derive_seed` log, scoring-protocol commit.

Exit criterion: a manifest a stranger could re-verify from cold — every
SHA re-resolvable, every byte count re-weighable, the self-exported ONNX
reproducible from the recorded exporter pins, with no `[ESTIMATED]` left
where a `[MEASURED-local]` belongs. BLOCKED exit: self-export fails or
rank parity fails → stop, report, do not substitute the static channel
silently (that substitution is ablation A1, Phase 3, declared as such).

## Phase 1 — shared Stage 0

Owner: Stage-0 Owner.
Entry gate: Phase 0 manifest complete; baseline lead's spec available
(`experiments/baselines/HYPOTHESIS.md` §3 + CONTRACT §2); pinned generator
tokenizer callable resolvable.

Steps:

1. Implement BM25 EXACTLY per the baseline pin: Okapi k1=1.2, b=0.75;
  tokenizer NFKC → casefold → `[a-z0-9]+` regex; no stemming; no
  stopwords; paragraph-node index; top-K=500; tie-break `(score, node_id)`;
  packing ranked-prefix, per-article cap 3 spans, strict 1000-token cap,
  `exact=True` with the pinned generator tokenizer.
2. Byte-compare against the baseline lead's Stage 0: run their published
  fixture, diff ranked lists item for item (ordered node ids + scores).
3. Measure and record `[MEASURED]`: Stage-0 build latency (`timed_phase`),
  `proc_peak_rss_mb`, packed binary index bytes, per-query retrieval
  `total_latency_ms` on the fixture. These replace the HYPOTHESIS §5.1-5.3
  `[ESTIMATED]` BM25 rows (15–40 MB core index, 10–120 s build, ~10 ms/query).

Exit criterion: ranked lists reproduce the baseline lead's published lists
item for item on the fixed fixture; any deviation is a defect, not an
ablation. No Phase 2 work starts on a divergent Stage 0.

## Phase 2 — each channel in isolation

Owner: Retrieval Lead.
Entry gate: Phase 1 byte-parity achieved. KILL-CONDITION PRE-CHECK ARMED
(see exit). Leakage gate untouched (no synthetic data needed: both neural
channels run FROZEN; index build is forward passes over corpus text only).

Steps:

1. Run three channel-alone systems with IDENTICAL packing and generator:
  BM25 alone (= B1 reference), learned sparse alone (frozen v2-distill),
  static dense alone (frozen; int8 ONNX path with the §5.4 parity gate).
2. Per channel, file an evidence-survival report BEFORE any fusion
  (HYPOTHESIS §8, paragraph granularity, ancestry-aware `covers`):
  `stage_coverage`, `conditional_retention` (numerator/denominator; None
  when denominator is 0), `survival_curve` lineage (assert pruned-stays-
  pruned), `lost_and_recovered` counts, candidate-set AND packet-level
  disjoint recall vs BM25 (explicit denominators), binary
  `sufficient_set_completion` + `best_fractional_coverage`,
  `leaf_precision`, `overshoot_tokens`, exact-token evidence cost, and the
  conjunctive-loss diagnostic (per-atom survival vs conjunctive completion
  gap on multi-atom items).
3. Apply the baseline lead's 5% arbiter to EACH neural channel at the
  PACKET level: packet-level disjoint recall over BM25 < 5% → that channel
  is dead weight (recorded, not hidden).
4. False-negative localisation on dev false negatives: walk each
  `survival_curve` backwards, attribute each kill upstream-most
  (channel-A-only / channel-B-only at this phase), with rank + score of the
  killed passage; aggregate per-stage kill counts + killed-passage score
  histograms.
5. Measure `[MEASURED]`: per-channel index-build latency, index bytes,
  `peak_rss_mb` (weights loaded + index resident), per-query latency split
  (encode vs lookup vs pack). These replace the HYPOTHESIS §5
  `[ESTIMATED]` rows for the learned sparse (~268 MB weights, 6–30 MB core
  index, ~2–10 min CPU build) and static (~125 MB fp32 / 31 MB int8,
  ~41 MB fp32 doc cache core, seconds-to-a-minute build).

Exit criterion: three filed survival reports with explicit denominators;
KILL GATE EVALUATED — if EITHER (a) best single channel vs B1 completion
gap < 18 items on dev+shadow-dev (Wilson overlap), OR (b) the learned
sparse channel's packet-level disjoint recall < 5%, then record
`kill_condition.met=true` with Wilson parameters + per-item traces and
downgrade the headline to "fusion unnecessary" before Phase 3 burns
fusion effort. A null inside overlapping intervals is recorded as
UNDERPOWERED, never as equivalence.

## Phase 3 — fusion

Owner: Fusion Lead.
Entry gate: Phase 2 reports filed; kill gate evaluated and headline not
killed (or killed-but-proceeding declared as confirmatory only).

Steps:

1. HEADLINE FIRST: RRF (k=60, preregistered, untuned) over BM25 +
  learned-sparse rankings. Rank-based only; no score normalisation surface.
2. Then preregistered ablations, each reported win-or-lose with identical
  corpus/splits/budget/generator/prompt/seeds/metrics:
  A1: BM25 + static dense via RRF (engages the baseline lead's B2/Borda
  point; uses the static channel's shipped int8 ONNX);
  A2: BM25 + learned sparse via learned combiner (logistic regression on
  channel scores) — ONLY after a leakage-gate PASS on the synthetic batch
  in a ONE-SHOT clearance session (`synth-hybrid-{regime}-{n}` namespace,
  adaptation manifest proving zero excluded-doc membership under Regime B,
  paired A/B runs + paired delta);
  A3: BM25 + learned sparse via CombSUM + min-max normalisation
  (normalisation choice declared and pinned; the surface RRF avoids).
3. Per fused system: full §8 survival metrics + packet-level disjoint
  recall vs B1 + conjunctive completion + three-way kill attribution
  (channel-A-only / channel-B-only / fusion-demotion).

Exit criterion: headline packet-level disjoint recall + completion delta
vs B1 measured with explicit denominators and Wilson CIs; each ablation
filed as win/lose/draw-against-headline; KILL GATE re-evaluated on the
headline (same 18-item / 5% rule, recorded identically). No threshold or
cut is tuned for the headline (top-K cuts pinned by the baseline spec).

## Phase 4 — the degeneration test (highest value)

Owner: Fusion Lead (with Eval Lead witnessing).
Entry gate: Phase 3 headline ranking implementation complete (any data).

Steps:

1. Implement `test_rrf_does_not_degenerate_to_single_channel` FIRST among
  §9 tests: fixture where sparse ranks paragraph X #1 and BM25 ranks X
  #500, and Y is BM25 #1 / sparse #500; assert fused top-2 contains BOTH
  X and Y. Companion: `test_rrf_rank_invariance` (monotonic score
  transform leaves fused order unchanged), `test_rrf_known_vector`
  (hand-computed order), `test_disjoint_recall_computation`,
  `test_conjunctive_survival_tracked`, `test_query_contract_enforcement`,
  `test_packet_budget_strict`, `test_pruned_stays_pruned`,
  `test_determinism`, `test_regime_b_manifest`,
  `test_kill_attribution_three_way` (all stdlib `unittest`, zero
  third-party deps; each names its defect).
2. Run the degeneration test against the REAL headline implementation (not
  a reimplementation): feed the fixture's two rankings through the shipped
  fusion code path.
3. Corroborate on real dev data: compute fused-vs-each-channel rank
  correlation / top-K overlap; a fused listing identical to either
  channel's listing is a degeneration finding.

What counts as fusion having done real work (ALL required):
(a) the degeneration unit test PASSES (fused top-2 = {X, Y});
(b) the fused dev listing is NOT rank-identical to either channel alone;
(c) packet-level disjoint recall over B1 is > 0 with an explicit
denominator AND at least one recovered paragraph survives the ~4-slot
budget into a packet whose completion changes (candidate-set-only wins
do not count — HYPOTHESIS §1.2 refuter 3).
If (a) fails, the fusion implementation is a no-op regardless of any
downstream metric: fix the code, do not reinterpret the metric.

Exit criterion: degeneration test passing in CI plus the three-part
real-work statement filled with measured numbers, or a recorded
degeneration finding that blocks Phase 6.

## Phase 5 — the baseline-engagement argument

Owner: Analysis Lead.
Entry gate: Phases 2–4 measurements in hand.
The question (HYPOTHESIS §2 table, last row): does a static semantic
channel add anything over BM25 here, and does the learned sparse channel
add anything beyond THAT?

Settling measurement (single, preregistered): PACKET-level disjoint recall
over BM25 for each second channel (learned sparse vs static dense) + each
fused system's sufficient-set completion delta vs B1 on dev+shadow-dev,
judged against the corrected 18-item Wilson MMD — with the B2
(BM25+static, Borda) and B4 (BM25+generator floor) comparisons from
HYPOTHESIS §12 carried alongside.

Outcome table (each row recorded verbatim, not reframed):

- Static packet disjoint recall < 5% AND within Wilson overlap of B1 →
  baseline lead's "0–2 points, inside noise" CONFIRMED; static channel adds
  nothing here.
- Learned-sparse packet disjoint recall ≥ 5% AND exceeds static's by a
  Wilson-separable margin → learned channel's complementarity (MLM
  expansion) is real on this corpus; its extra cost (no shipped ONNX, MLM
  index build [ESTIMATED→measured in Phase 2]) is the declared price.
- Learned-sparse ≈ static (both < 5%, or within overlap of each other) →
  the static channel's superior mobile story (shipped 31 MB int8 ONNX
  [MEASURED-remote]) makes IT the better engineering choice; reported as such.
- B4 within overlap of the hybrid → hybrid unnecessary regardless of
  channel (generator floor moots retrieval differences).

Exit criterion: one filled outcome row with Wilson parameters
(hits, n=146, z=1.96) + per-item traces, naming which channel (if any)
earned its cost.

## Phase 6 — dev / shadow-dev readiness

Owner: Eval Lead. Custodian runs oracle/floor probes; worker never
constructs oracle packets.
Entry gate: Phases 0–5 artifacts filed; all §9 unit tests passing;
telemetry schema complete (`None` = explicitly not measured).

Run order (DESKTOP, frozen `eval/` + `substrate/`, generator fixed):

1. Generator floor probe FIRST (CONTRACT §5 three-way McNemar on dev):
  custodian oracle packet vs B4 packet, paired discordant-pair analysis.
  FLOOR → STOP, report "generator floors; retrieval tournament
  uninterpretable above the floor." UNDERPOWERED → record as its own
  outcome (never as "no floor"); proceed on retrieval metrics only.
2. Channel-alone baselines (Phase 2 reports stand as these; no re-run
  without cause).
3. Headline RRF + ablations A1/A2/A3 (A2 gated on leakage PASS).
4. Threshold/cut selection on DEV ONLY, and only for A2 (headline has no
  tunable thresholds; top-K cuts pinned). Freeze into manifest.
5. ONE confirmation run on shadow-dev with frozen cuts. No re-tuning.
6. Regime A/B paired comparison for A2 only (headline A≡B by
  construction, stated not re-proven by tuning).

READY iff ALL: (a) floor probe rules out flooring (McNemar interval
excludes 0); (b) Stage-0 BM25 recall on dev ≥ 0.90; (c) learned-sparse
candidate-set disjoint recall measured with denominators (5% arbiter
applied at packet level); (d) headline packet-level disjoint recall
measured with denominators; (e) all §9 tests pass; (f) telemetry complete
(`complete=true`, no None-masquerading totals); (g) kill attribution
covers 100% of dev false negatives; (h) A2 (if run) has leakage PASS +
frozen cuts.
NOT-READY if ANY: generator floors or probe underpowered-and-untreated;
Stage-0 recall < 0.90; sparse packet disjoint recall < 5% (headline
collapses to "fusion unnecessary" — recorded, not hidden); any telemetry
field silently unmeasured; A2 without leakage PASS; shadow-dev diverges
beyond Wilson overlap with no diagnosed cause; any threshold touched after
the shadow-dev freeze.

## Phase 7 — handoff

Owner: Experiment Lead E (author), recipients Comparability Lead + Custodian.
Entry gate: Phase 6 READY (or declared NOT-READY with reasons).

To the Comparability Lead (form: run-manifest keys + raw-trace files,
stdlib-readable, no private content):

- Run manifest: pin SHAs, weight/ONNX sha256 + bytes, corpus/questions/
  generator/sha pins, seed-derivation log, merge config (core vs merged),
  scoring-protocol commit, per-system configs (RRF k=60; A3 norm choice;
  A2 weights + fitting-set manifest sha256), ALL cost/latency/RAM/storage
  tagged `[MEASURED]`/`[ESTIMATED]`, `kill_condition` record
  `{met, system, metric, value, minimum_meaningful_difference: 18 items /
  12.3 pp on n=146, wilson_ci, per_item_traces}`.
- Raw traces: per-item candidate ids per stage, survival curves, kill
  attributions, packet bytes + `token_count_method` labels, discordant-pair
  table for the floor probe.
- Tournament-summary headline in kill-protocol wording if the gate met
  ("Kill condition met: …"), never "fusion works but BM25 is close."

To the Custodian:

- Leakage-clearance session request (A2 synthetic batch only), one-shot;
  adaptation manifest with Regime-B zero-membership proof; `synth-hybrid-*`
  namespace registration (harness must reject them as benchmark queries).
- Floor-probe execution request (oracle packets are custodian-built,
  custodian-run).
- No private run is requested by this plan beyond the standard frozen-system
  private run after all cuts freeze; no dev re-tuning follows it.

---

## Verification note

No weight bytes downloaded for this plan; no new sha256 claimed. No private
question, label, review, or authored artifact read. No Android claim.
