# Adapter / PEFT Family — Hypothesis and Readiness Report (Round 1 Experiment Lead D)

Status: MISE-EN-PLACE READINESS ONLY. No implementation, no training, no
private evaluation, no synthetic data, no adapter weights in the repo.
Frozen substrate: tag `round0-freeze-r1`, commit
`a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`.
All measurements in this report are DESKTOP (API-metadata observations
dated 2026-10-03, local config reads, arithmetic). No Android or on-device
claim may be derived from any of it.
Worker endpoint: opencode/fledge-alpha-free (verified zero-cost).
No subagents spawned. No paid fallback used.
Companion file: `experiments/adapter-peft/PLAN.md`.

Labels used throughout: **VERIFIED** (checked against a primary source on the
date given), **DERIVED** (arithmetic from verified facts), **ESTIMATED** (to be
replaced by a `substrate.telemetry` measurement in PLAN.md), **ASSUMED**
(named risk, explicitly not measured), **PREDICTION** (honest expectation, not
a result).

## 0. FALSIFIABLE HYPOTHESIS AND KILL CONDITION

**Hypothesis (one sentence).** A LoRA-adapted small frozen base retriever/reranker
(33M-parameter bi-encoder or 17M cross-encoder) achieves required-evidence
survival on dev/shadow-dev **at least within the minimum meaningful
difference of its un-adapted base** and of the baseline "BM25 + one small
reranker" system, at essentially the runtime/storage of the small base itself —
i.e. parameter efficiency converts domain adaptation into quality at
small-model cost, which is precisely the System-1 constraint.

**What would REFUTE it (the specific comparison).** On the frozen dev set
(59 items) and shadow-dev set (87 items), scored through the preregistered
`eval/` harness with custodian-held labels, ANY of:

1. LoRA-adapted base is BELOW the **frozen un-adapted base** on
   required-evidence survival (dev+shadow-dev) by more than Wilson-CI overlap
   — i.e. the adapter adds nothing or hurts; OR
2. LoRA-adapted base fails to beat **B1/B4-class BM25** and fails to match
   "BM25 + one small reranker" (the baseline lead's bar) within the minimum
   meaningful difference — i.e. the adapter does not earn its training+adapter
   complexity over the cheaper static path; OR
3. The merged-export path (§3) produces a runtime cost that equals the
   LARGER comparator model — i.e. merging has evaporated the size advantage; OR
4. The generalisation-vs-memorisation probe (§6) shows the dev-set gain is
   attributable to article-level memorisation, not transferable adaptation.

Any one of these is a refutation; this kill condition is stated IN ADVANCE and
recorded in the run manifest as `kill_condition` per
`experiments/comparability/CONTRACT.md` §6. A null result *inside* overlapping
Wilson intervals at n=59/87 is UNDERPOWERED, not equivalence. Risk 2 is now QUANTIFIED (2026-10-03): only ~22 pp separable on dev, ~12 pp on dev+shadow-dev, ~10 pp across all 206 items. Report as a null, not a win.

The cascade-family kill condition also binds us: if BM25 + one small reranker
matches a full cascade (or our adapted small base) within the minimum
meaningful difference, the correct output is "the cascade/adapter is
unnecessary" and must be recorded that way — we must clear the SAME bar the
cascade does, not a lower one.

## 1. EXACT BASE IDS + REVISION COMMITS + ADAPTER/PEFT METHOD IDS, LICENSES

### 1.1 Base candidates (VERIFIED via live Hub API, 2026-10-03)

| Role | Repo id | Head SHA observed 2026-10-03 | Last modified | Licence | Params (Hub safetensors metadata) | Status |
|---|---|---|---|---|---|---|
| Primary small bi-encoder retriever | `BAAI/bge-small-en-v1.5` | `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` | 2024-02-22 | mit | 33,360,512 (33.4M) | VERIFIED; stable ≥ 20 months. Pin = this SHA, weight sha256 at download |
| Small cross-encoder reranker | `cross-encoder/ettin-reranker-17m-v1` | `9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` | 2026-05-19 | apache-2.0 | 16,797,440 (16.8M) | VERIFIED; matches peer teams' 2026-10-03 observation exactly. Moving-head → re-resolve at implementation |
| Cheaper small retriever | `Snowflake/snowflake-arctic-embed-xs` | `d8c86521100d3556476a063fc2342036d45c106f` | 2024-12-13 | not stated in cardData (see card) | 22,565,376 (22.6M) | VERIFIED exists; licence tag absent on API → CHECK card text at implementation, VERIFY-BEFORE-USE |
| **Larger comparator (the "much larger model")** | `BAAI/bge-base-en-v1.5` | `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a` | 2024-02-21 | mit | 109,482,752 (109.5M) | VERIFIED. bge-large-en-v1.5 (335.1M, `d4aa6901…`, mit) recorded as second comparator |
| Tiny static baseline reference | `sentence-transformers/static-retrieval-mrl-en-v1` | `f60985c706f192d45d218078e49e5a8b6f15283a` | 2025-01-17 | apache-2.0 | ~30.5M-token table (see baselines §4.1) | VERIFIED via peer report; static (zero-transformer), so LoRA on it is meaningless — excluded as adapter base |

NOT selected (recorded to prevent silent substitution):
- Full fine-tuning of the large base as the comparator's adaptation path is
  OUT of scope: we compare against the large base's *off-the-shelf* quality,
  and optionally against a LoRA-adapted large base trained with the same
  synthetic budget (first-class ablation in PLAN.md) to isolate
  "adapter quality" from "base size".
- Community/fine-tuned bge variants (`BAAI/bge-*-qlora`, etc.): unpinned,
  quality-unverified, excluded for provenance cleanliness.

### 1.2 Adapter / PEFT method identity (VERIFIED at package level, 2026-10-03)

| Field | Value |
|---|---|
| Library | `peft` 0.21.2 (PyPI, live-checked 2026-10-03) |
| Method | LoRA (`LoraConfig`, r, alpha, dropout, target_modules), applied via `get_peft_model` |
| Merge API | `merge_and_unload()` on `PeftModel` — the standard LoRA fold into base weights (peft 0.21.2). VERIFIED at docs level: LoRA merge is supported for decoder/encoder `nn.Linear` stacks; **ASSUMED for our two exact bases until proven by a merge-parity test in PLAN.md Phase 3** |
| Tokenizer/training | `transformers` 5.18.0, `sentence-transformers` 6.1.0, PEFT training through the same frozen corpus and synthetic-data gate |
| Config pinning | LoRA r/alpha/dropout/target_modules + seed + synthetic-data manifest sha256 recorded in the run manifest; any change = new run, never silent |

VERIFY-BEFORE-USE: the two SHAs above are moving-head observations, not freeze
pins. Before ANY training run, the implementer re-resolves each repo SHA and
records weight-file sha256 in the run manifest. No weight bytes were downloaded
for this report; no weight sha256 is claimed.

## 2. THE CRUX, STATED PLAINLY: MERGED vs RUNTIME-APPLIED, AND DOES THE ADVANTAGE SURVIVE?

Runtimes and what breaks:

| Export path | Runtime-applied adapter | Merged adapter (`merge_and_unload`) |
|---|---|---|
| PyTorch (desktop reference) | Supported. Adapter is extra modules on top of the frozen base; ~zero added latency (two small matmuls per targeted linear) but NON-STANDARD state_dict | Supported, and numerically identical to the runtime-applied model up to fp tolerance (merge-parity test in PLAN.md). The exported artifact IS a plain dense model of the same architecture as the base |
| ONNX export | **BREAKS / not supported**: an unmerged PEFT wrapper is not a normal `AutoModel`; `torch.onnx.export`/`optimum` need the underlying base model. ASSUMED until tested — PLAN.md Phase 3 step 1 verifies merge-then-export | Works via the base model's standard export path (bge-small and ettin-17m both carry committed `onnx/` dirs — VERIFIED via tags 2026-10-03) |
| llama.cpp GGUF fast path | **BREAKS.** llama.cpp's `--lora` runtime support covers llama-family decoder LLMs only. Neither a BERT bi-encoder nor a ModernBERT cross-encoder has any llama.cpp path at all (ettin: VERIFIED no GGUF in-repo; KaLM peer finding: only V1-Nano GGUF, patched-llama.cpp-only) | Merged LoRA folds into the base's *fp* weights, but GGUF conversion still requires the architecture to be a llama.cpp-supported model. For bi-encoder/cross-encoder retrievers this path remains BLOCKED even after merging — ASSUMED-same-as-base, stated plainly: **our merged small retriever has no llama.cpp path, LoRA or not**. If a llama.cpp path is a hard requirement, this family is structurally blocked and that IS the finding |
| ExecuTorch | **BREAKS.** ExecuTorch has no PEFT adapter runtime hook; it exports a single graph via `torch.export`. An unmerged PEFT model's forward dispatch does not trace cleanly (ASSUMED — verified at implementation) | Merge first, then the merged dense model follows the base's export path. ExecuTorch support for BERT/ModernBERT encoders specifically is NOT established in this report (kapeer reports no ExecuTorch path for ModernBERT) → ASSUMED BLOCKED until demonstrated |
| Android/GrapheneOS | Runtime-applied adapters are effectively unshipped on-device today. GrapheneOS hardening (SELinux, linker namespace) additionally complicates custom native adapter code | Merging produces a standard small dense model; the on-device story then rides on ONNX Runtime Mobile (ORT ships Android ARM builds — ecosystem fact, NOT a measurement). GrapheneOS-specific issues untested |

**Blunt answer to the crux.** Adapters MUST be merged to be exportable. Once
merged, the artifact *is* the small base model's architecture with folded-in
weights: its runtime class and storage are the base's, not the adapter's.
Therefore the hypothesis's advantage survives merging **only in the form**:
"LoRA-trained quality ≈ large-model quality, at small-model runtime/storage."
It does NOT survive as "ship the adapter alone" — there is no supported
on-device adapter runtime for any model in this family. Storage of the adapter
itself (~0.1–1.2 MB, DERIVED below) is a training-time artefact, not a
deployment artefact. **If a measurement shows LoRA-small ≈ base-small on
dev/shadow-dev (no transferable gain), the correct headline is "the advantage
evaporates: merging gives you back exactly the small base, and it wasn't
better."** That outcome is priced into the kill condition (§0.1).

**Adapter storage vs larger merged model (DERIVED, tariff of the LoRA
configuration; training-time only):**

| Base | Params | LoRA r=8 on q,v per layer | Adapter params | Adapter fp32 | Base merged fp32 | bge-base comparator |
|---|---|---|---|---|---|---|
| bge-small (BERT, h=384, 12L) | 33.36M | 12 × 2 × (384·8 + 8·384) | 147,456 | ~0.57 MB | ~134 MB (DERIVED = 33.36M × 4 B) | 109.5M ≈ 438 MB fp32 |
| arctic-embed-xs (BERT, h=384, 6L) | 22.57M | 6 × 2 × 6,144 | 73,728 | ~0.29 MB | ~90 MB | — |
| ettin-17m (ModernBERT, h=256, 7L) | 16.80M | 7 × 2 × (256·8 + 8·256) | 57,344 | ~0.22 MB | ~67 MB | — |

LoRA r=16 doubles the adapter column; still < 2.5 MB. Even r=64 stays < 10 MB.
An adapter is 100–1000× smaller than shipping the larger model's weights —
that IS the storage pitch — but only at training time; the deployable merged
small model is what competes on device, at ~67–134 MB fp32 (ESTIMATED int8:
~17–34 MB, DERIVED by halving/quartering — to be MEASURED).

## 3. SIZES (every number labelled)

MEASURED (Hub API / local config, 2026-10-03):
- bge-small: 33,360,512 params; ettin-17m: 16,797,440; arctic-xs: 22,565,376;
  bge-base: 109,482,752; bge-large: 335,142,400.
- bge-small `modules.json`/safetensors geometry from config: BERT,
  hidden 384, 12 layers, intermediate 1536, vocab 30,522 (VERIFIED by reading
  `config.json`); ettin-17m: ModernBERT, hidden 256, 7 layers, intermediate
  384, vocab 50,368 (VERIFIED); arctic-xs: BERT, hidden 384, 6 layers (VERIFIED).

DERIVED (arithmetic): merged fp32 weight sizes in §2 table; LoRA parameter
counts in §2 table; int8 ≈ params × 1 B.

ESTIMATED (replace with telemetry in PLAN.md):
- RAM resident training (bge-small + LoRA + AdamW on 306-article synthetic
  set): **~1.5–3 GB** (fp32 master weights + 2 optimizer states over 33M +
  activations; LoRA trainables only ~0.6 MB keeps optimizer states tiny).
- RAM resident inference merged bge-small: **~150–250 MB** desktop.
- Latency per query (bge-small bi-encoder encode of one query, CPU):
  **ESTIMATED <10–30 ms**; ettin-17m cross-encoder over ~50 cards:
  **ESTIMATED 0.5–5 s single-threaded fp32** — the cross-encoder path is the
  expensive leg, same class as baseline B3's 68M but ~4× cheaper in params.
- Training time for a LoRA run (synthetic set of ~2–10k pairs, 1–3 epochs):
  **ESTIMATED minutes to ~1 hour** on the i7-8700.

## 4. TRAINING PLAN (synthetic questions, leakage gate, regimes)

1. **Synthetic question generation — FIXED generator only.** Questions are
   generated from the SHARED corpus (`corpus/corpus.jsonl` +
   `corpus/scale/distractor.jsonl`) using the pinned fixed generator
   (`qwen25-1.5b-q4km-fixed-v1`, `PROMPT_HASH`, fixed prompt, evidence budget
   300–800 tokens). The generator, prompt, quantisation, and budget are NOT
   changed and NO generator tournament is run. Template-based generation is an
   allowed cheaper variant only if recorded.
2. **Custodian leakage gate — ONE-SHOT clearance session.** Every synthetic
   batch is submitted to the custodian's gate
   (`data_tools.leakage_check` / `substrate.private_eval.check_training_overlap`)
   exactly once per batch; the verdict is PASS or REJECT + synthetic ids to
   remove, never matched private ids. Iterating batches against the verdict to
   probe the private set is FORBIDDEN (one-shot means one-shot). HONEST
   LIMITATION carried from Round 0: the gate's hash-only comparison is not yet
   seal-bound and correctly refuses PASS — until the custodian binds it, NO
   synthetic data may be used for adaptation. Retrieval-only work may proceed.
3. **Regime A vs Regime B adaptation (contract §4).** Model A: synthetic
   adaptation data may use any corpus document. Model B: the IDENTICAL
   procedure, but all 21 articles from
   `substrate.query.worker_regime_b_exclusions()` (public superset; never
   derive from private metadata) are excluded from adaptation data. Query-time
   corpus is IDENTICAL for A and B — the 21 stay retrievable. The run manifest
   carries an adaptation-data manifest proving zero excluded-doc membership;
   `verify_adaptation_exclusion`-style checks are unit-tested.
4. **What is trained.** LoRA on the frozen base encoder's attention
   projections (target_modules=["query","value"] for bge-small; ettin-17m
   equivalents), objective = contrastive InfoNCE over (synthetic question,
   positive paragraph, BM25-mined hard negatives) for the bi-encoder, and
   pointwise/pairwise MarginMSE distillation of passage relevance labels for
   the cross-encoder. Synthetic labels are provisional: positive = the source
   paragraph of the generating span; hard negatives = same-article non-answering
   paragraphs. Public bounty questions are dev/reference only, NEVER training.

## 5. GENERALISATION vs MEMORISATION TEST DESIGN (concrete)

The risk: synthetic questions are generated FROM THIS corpus, so an adapter
trained on them can score well by memorising article↔answer mappings while
learning nothing transferable. Protocol (all thresholds selected on dev/shadow-dev, frozen):

- **G1 — Article-held-out generalisation probe.** Split corpus articles into
  two disjoint halves by the public group structure. Train adapter A₁ on
  synthetics from half 1 ONLY. Evaluate on (a) synthetics from half-1 articles
  (memorisation-favourable) and (b) REAL dev items whose sources lie in half 2
  (generalisation-favourable), plus the same eval for the frozen base. The
  diagnostic is the DELTA-of-DELTAS: (adapter − base) on half-2 real items vs
  (adapter − base) on half-1 items. Strong half-1 gain + no half-2 gain =
  memorisation. Non-zero half-2 gain = transferable signal.
- **G2 — Regime-B as memorisation instrument.** Because Regime B excludes the
  21 articles from adaptation while scoring paired questions over them, the
  Regime A vs B paired delta on those same questions IS a memorisation probe:
  if A≫B on the paired set, the adapter's gain on those articles came from
  adaptation exposure, i.e. memory, not a transferable skill. Report the
  paired delta per contract §4, never pooled.
- **G3 — Paraphrase-held-out probe.** For each synthetic fact, generate two
  independent question phrasings; train on one, score the other. A model that
  memorised surface spans fails the held-out phrasing; a generalised one
  retains the gain. Report survival delta on held-out phrasings.
- **G4 — Leakage-margin audit.** For each dev item, measure whether the
  gold answer span or its near-duplicate string appears verbatim in any
  synthetic training question (edit-distance/n-gram overlap audit,
  stditlib-only). Report training-set verbatim-answer rate per split; a high
  rate flags memorisation exposure. This is a diagnostic, not a blocker.

A result is reported as "generalises" only if G1 half-2 delta AND G3
held-out-phrasing delta are both non-negative beyond Wilson overlap, while G2
A/B delta is small (≤ the minimum meaningful difference). Otherwise the
family is memorising and the finding is recorded as such. This is a genuine
scientific risk of the WHOLE synthetic-training approach, not only ours: every
family using corpus-derived synthetics must run an equivalent probe.

## 6. CALIBRATION PLAN

What is calibrated: the adapter-path's **sufficiency/decision thresholds and
reranker cutoffs** — never the scores' semantic kind lies. Bi-encoder cosine
and cross-encoder logit are `score_kind` declared ("model_probability" only
after provenance-tagged fitting; raw logits/cosine = ranking kinds).

On WHAT data, what split: fit any temperature/isotonic map on
TRAIN-derived synthetic scored pairs ONLY (labels provisional per §4);
select all thresholds on DEV (59 items, custodian-scored); confirm ONCE on
shadow_dev (87) with frozen thresholds. Shadow-dev never re-tunes — a
failure there is a generalisation finding, reported, with re-tuning recorded
as a demotion of shadow-dev to dev. `calibration_partition` provenance =
sha256 of the exact fitting-set manifest, recorded in `ThresholdPolicy`
(substrate invariant). Thresholds frozen in the run manifest BEFORE the
private run. Primary metrics are deterministic retrieval metrics; judge-based
secondary metrics stay ABSENT until the judge digest is pinned (accepted
risk 4).

## 7. EVIDENCE-SURVIVAL METRICS PER STAGE + FALSE NEGATIVE LOCALISATION

Vocabulary is the shared one (subpeer HYPOTHESIS files §8, `eval/support.py`,
`substrate/types.py`): per stage s — `stage_coverage` (direct fraction of
required atoms whose host paragraph survives, ancestry-aware),
`conditional_retention` WITH numerator/denominator (None when denominator 0),
`survival_curve` lineage (pruned stays pruned; `lost_and_recovered` ≈ 0),
final `sufficient_set_completion` (binary), `best_fractional_coverage`,
`leaf_precision`, evidence token cost (EXACT generator-tokenizer count,
never whitespace estimate), latency / peak_rss_mb / storage_bytes.

Our stage stack: stage-0 BM25 top-500 (shared, pinned) → [adapter] bi-encoder
rescore OR cross-encoder rescore → per-article-capped ranked-prefix packing
(`build_packet(exact=True)`, cap 1000, target 300–800). FALSE-NEGATIVE
localisation protocol (identical to peers): for each item with final
completion 0, walk the survival lineage backwards and record the upstream-most
stage that dropped below full coverage of ANY sufficient set; attribute the
kill to that stage with the killed passage's rank/score. Additional
adapter-specific localisation: report whether killed passages were present in
the adapter-path's training synthetics (verbatim-span audit §5-G4) — kills
concentrated on never-trained article types are evidence the adapter has not
generalised.

## 8. DETERMINISTIC UNIT TESTS (each names the defect it catches)

1. `test_merge_parity`: runtime-applied LoRA model vs `merge_and_unload()`
   model on 20 fixed (query, passage) pairs → logits equal within fp
   tolerance. Catches: merge math bugs / target_modules typos that silently
   leave adapters applied or unapplied (silent quality loss or a fake
   "adapter works" result).
2. `test_adapter_params_frozen_base`: all non-LoRA parameters bit-identical
   before/after training; only LoRA A/B matrices change. Catches: accidental
   full fine-tune (breaks the "frozen base" claim and the storage story).
3. `test_prune_persist`: a candidate removed at the adapter-rescore stage is
   absent from the packet. Catches: stage-plumbing re-expansion invalidating
   all survival claims.
4. `test_query_contract`: every model-facing entry point rejects payloads
   carrying `split`/`question_type`/`group`/`source_articles` with
   `ForbiddenMetadataError`; `to_model_query` copies exactly two fields.
   Catches: label/metadata leakage into the adapter model (tournament-invalidating).
5. `test_regime_b_manifest`: adaptation manifest containing any of the 21
   public excluded articles fails validation; the same articles remain in the
   query-time corpus. Catches: Regime-B adaptation leakage AND the opposite
   (excluding from retrieval, faking a B effect).
6. `test_packet_budget_strict`: first-span-overflow yields empty packet +
   `truncated=True`; no packet exceeds 1000 exact tokens. Catches:
   budget-accounting bugs (per-span vs full-serialisation counting).
7. `test_leak_gate_wiring`: the training-data builder refuses to emit a
   batch without a custodian PASS verdict artifact (and REJECT-with-ids
   removes exactly those synthetic ids). Catches: training on unvetted
   synthetics after a gate failure.
8. `test_score_kind_honesty`: raw cosine/logit paths carry
   `score_kind` ranking kinds; no `calibrated_probability` claim without
   `calibration_partition`. Catches: calibration-category fraud.
9. `test_determinism`: same seed-derivation → byte-identical synthetic
   manifest + identical first-batch loss. Catches: uncontrolled RNG making
   runs unreproducible.

## 9. DEV / SHADOW-DEV READINESS PLAN ("ready" definition)

READY requires ALL:
(a) synthetic-data gate PASS actually issued by custodian (or explicitly
blocked and adaptation work deferred — then READY only for retrieval-only
work); (b) LoRA merge-parity test green; (c) stage-0 BM25 recall ≥ 0.90 on
dev; (d) every reported stage's `conditional_retention` ≥ 0.99 with
denominators; (e) kill attribution accounts for 100% of dev false negatives;
(f) full telemetry (`complete=true`, no None-masquerading, exact token
counts); (g) all §8 tests green; (h) thresholds frozen in the manifest;
(i) generalisation probes G1–G4 run and their verdict recorded (either
verdict is acceptable — memorisation is a publishable finding, silence is
not).

NOT READY if ANY: gate PASS absent while claiming adaptation results;
merge-parity fails; stage-0 recall < 0.90; any stage's conditional
retention < 0.99 unexplained; shadow-dev diverges from dev beyond Wilson
overlap with no diagnosed cause; any telemetry field silently unmeasured;
judge digest unpinned AND judge metrics reported (primary metrics only);
private data touched; thresholds changed after freezing.

## 10. EXPECTED MOBILE BLOCKERS (plain)

1. **No runtime-applied adapter anywhere on-device.** Merging is mandatory;
   the "adapter" is a training-time artifact. Anyone shipping an unmerged
   PEFT wrapper on Android is already broken.
2. **No llama.cpp path for BERT/ModernBERT retrievers**, GGUF-quantised or
   otherwise, merged or not. The GGUF fast path is unavailable to this
   family by architecture, not by effort.
3. **ExecuTorch: no PEFT hook; BERT-family encoder support unestablished** —
   the merged model's ExecuTorch export is an open implementation risk,
   not a plan.
4. The **fixed generator (~1 GB Q4_K_M GGUF + llama.cpp) dwarfs every
   adapter-path component** and is the real end-to-end mobile blocker
   (shared with all families).
5. Cross-encoder (ettin-17m) rescoring of ~50 cards/query on a phone CPU is
   unmeasured and could blow the sub-100 ms System-1 budget by 1–2 orders
   of magnitude; the bi-encoder path is the only plausible sub-100 ms leg.
6. Quantised (int8) quality parity of the merged model is unmeasured — an
   int8 quality drop erases the adapter's gain.
7. GrapheneOS native-library/linker behaviour untested; desktop latency
   predicts nothing about phone latency. Nothing here is an Android claim.

## 11. BASELINE COMPARISON WE MUST BEAT

Identical comparison harness (corpus, splits, evidence budget, fixed
generator, prompt, seeds, primary metrics):

1. **B4 / deterministic floor**: BM25 stage-0 top-K → packet, no learned
   retrieval. Isolates what lexical retrieval + the generator achieve; also
   the generator floor check.
2. **BM25 + one small static reranker/static embedder** (the baseline lead's
   bar): if BM25 + one small reranker matches our adapted-small (or any
   cascade) within the minimum meaningful difference, the adapter family's
   headline is "the adapter is unnecessary on this corpus" — we must clear
   that bar, not a lower one.
3. **Frozen small base, no adaptation** (bge-small / ettin-17m off-the-shelf):
   the adapter must beat its own un-adapted base beyond Wilson overlap or the
   adapter weight-storage costs are dead weight.
4. **Larger frozen base** (bge-base 109M / bge-large 335M off-the-shelf): the
   "much larger model" whose quality the adapter is supposed to approximate
   at a fraction of the cost.
5. **LoRA-adapted large base** (same synthetic budget, same LoRA recipe on
   bge-base): isolates base size from adapter effect — if large+LoRA ≈
   small+LoRA, the smaller base wins outright; if large+LoRA ≫ small+LoRA,
   the parameter-efficiency claim fails on this corpus and that is the
   headline.

All deltas reported with Wilson CIs and explicit denominators; null results
reported as underpowered, never as equivalence.

## 12. AMBIGUITIES / PRECEDENT-SETTING (carried from peers)

- No worker-visible relevance labels exist for any split; threshold selection
  requires custodian-scored runs returning aggregate rates + per-item
  covered/not-covered FLAGS only. We adopt the peer proposal: submit stage
  traces, receive flags + aggregates, never atoms/answers/source ids.
- Scale adjudication is specified but unwired (STATUS.md risk 6): we report
  raw AND adjudicated series with the break annotated.
- Judge digest unpinned (risk 4): secondary generated-answer metrics ABSENT
  until pinned.
- Evidence-budget tokenizer = the pinned GENERATOR tokenizer (governs the
  generator's input); adapter model truncation limits are a per-model concern.
- Synthetic question ids namespaced `synth-peft-{regime}-{n}`, registered in
  the adaptation manifest, never submitted as benchmark queries.
