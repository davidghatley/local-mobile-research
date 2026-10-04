# Round 1 Tournament Analysis — retrieval-primary

Split: dev (n=59, 55 analysable) and shadow_dev (n=87, 82 analysable), core tier.
Scored from raw JSONL by `experiments/common/score_all.py`; every number here is
reproducible from `experiments/results/retrieval/*/COMPARISON_*.json`.

**Threshold register** (`experiments/comparability/CONTRACT.md` §4, the one
authoritative source): dev **13 items / 22.0 pp**, shadow_dev **15 items /
17.2 pp**, dev+shadow_dev **18 items / 12.3 pp**. A gap below the applicable row
is a **NULL RESULT**, never a win. No threshold was invented anywhere in this run.

---

## 1. The two results that decide this round

### 1.1 The answer metric cannot resolve any architecture — by arithmetic

From `experiments/baselines/GENERATOR_FLOOR_REPORT.md` (n=137 analysable):

| arm | exact-match accuracy |
|---|---|
| oracle (gold evidence) | 20/137 = **14.60%** |
| B4 (BM25) | 16/137 = **11.68%** |
| degraded (anti-evidence) | 1/137 = 0.73% |

* **Total headroom perfect retrieval could buy: 2.92 pp = 4 items.**
* **Registered resolution floor on dev+shadow_dev: 18 items = 12.3 pp.**

The generator is emphatically **not** floored — swapping in gold evidence moves
accuracy 0.73% → 14.60%, with all 19 discordant pairs favouring the oracle,
p = 3.8 × 10⁻⁶. But its **ceiling** sits an order of magnitude below the
benchmark's discrimination threshold.

> **Consequence, knowable before running any architecture: every architecture pair
> compared on final-answer quality will be a null on this corpus — not by accident,
> but because the best physically available evidence packet beats BM25 by 4 items
> against an 18-item floor.** Any future "architecture X answers better than Y"
> claim here is unsupported by construction.

This retires the answer metric as a discriminator. It does **not** retire the
generator contract, and it is not a reason to swap generators.

### 1.2 The 1000-token evidence budget is the binding constraint — not the retriever

| metric (BM25 = B1 = B4) | dev | shadow_dev |
|---|---|---|
| stage-0 survival @500 | **70/73 = 0.9589** | **120/122 = 0.9836** |
| final packet completion | 54/73 = **0.7397** | 80/122 = **0.6557** |
| item-level completion | 0.7636 | 0.5976 |
| mean exact evidence tokens | 781 | 798 |

Retrieval is **saturated**. Atoms are found. What fails is the trip from "found" to
"shown": **26.0% of required evidence is lost between stage 0 and the generator.**

Loss attribution, dev, 73 required paragraphs
(`loss_attribution_B1_bm25_dev_core.json`):

| mechanism | count | share |
|---|---|---|
| survived | 54 | 0.7397 |
| **per-article cap of 3** | **10** | **0.1370** |
| 1000-token budget | 6 | 0.0822 |
| stage-0 rank (outside top-500) | 3 | 0.0411 |

And the sanctioned no-cap ablation (`HYPOTHESIS.md` §2.3 permits it) moves
completion only **0.7397 → 0.7671** (+2 of 19). The loss does not disappear; it
**migrates** from the cap to the token budget. Cap and budget are substitutes, not
complements.

Mean paragraph ≈ 210 words ≈ 280 generator tokens, so a 1000-token packet holds
**~3 paragraphs**. dev needs 1.33 required paragraphs per item on average, so the
budget is not absurd — it is simply tight enough that allocation, not recall,
decides the outcome.

> **This is the round's central architectural finding: on a 297-article corpus with
> ~210-word paragraphs, the tournament is a budget-allocation problem wearing a
> retrieval problem's clothes.** Stage-0 headroom is 4.1%. Nothing in the reranking
> family can address the other 21.9%.

## 2. System comparison (dev, core tier)

| system | n | stage-0 survival | completion | item-level | mean tokens |
|---|---|---|---|---|---|
| `B1_bm25` | 59 | 0.9589 | **0.7397** | 0.7636 | 781 |
| `B4_bm25_fixed_generator` | 59 | 0.9589 | 0.7397 | 0.7636 | 781 |
| `B2_bm25_static_union` | 59 | 0.9589 | **0.7260** | 0.7455 | 746 |
| `C_shared_heads_17m` (n=12 subset) | 12 | 1.0000 | 0.9375 | 0.9091 | 723 |
| `B3_bm25_plus_68m_rerank` | — | not yet scored | — | — | — |

**Do not read the `C_shared_heads_17m` row as a win.** It is n=12 over 16 required
paragraphs, versus n=59 over 73 for the others. Its stage-0 survival of 1.0000
simply means the first 12 dev items are easy (all 16 required paragraphs were
inside BM25's top-500), which is exactly why its completion looks high. Comparing
it to the n=59 rows would be an invalid comparison and the independent review
flagged exactly this risk.

### B2 — a preregistered prediction that came true

`experiments/baselines/HYPOTHESIS.md` §4.5 predicted, in advance and on the record:

> **PREDICTION: the static stage adds little to nothing over well-specified BM25
> on this corpus.** Expected B2−B1 delta in final completion: 0–2 points.

**MEASURED: B2 − B1 = −1.37 pp** (0.7260 vs 0.7397; 53/73 vs 54/73 completed
paragraphs — a difference of **one paragraph**). Stage-0 survival is **identical**
at 70/73: the static channel contributed **zero** additional required evidence.

The prediction's stated arbiter was a MEASURED static-disjoint recall of ≥ ~5% of
required paragraphs. That measurement needs custodian labels and is reported in
`BASELINE_IMPLEMENTATION_REPORT.md` as a label-free proxy only. The arbiter
therefore fired on the directly measured outcome: **it did not fire.**

Cost paid for nothing: a second runtime, a 125,018,208 B fp32 weight table, and a
40.9 MiB document-vector cache, to buy −1 paragraph.

## 3. What the neural families can and cannot do here

This is the uncomfortable part, and it follows from §1.2 rather than from any
model's quality.

* **Survival metrics are saturated.** BM25 keeps 95.9% (dev) / 98.4% (shadow_dev)
  of required evidence at stage 0. A reranker reorders *within* the stage-0 set,
  so its maximum possible contribution to survival is the 4.1% that sits outside
  top-500 — and most of that is multi-hop second atoms that no cross-encoder
  reliably promotes.
* **Reordering only pays if the packet can hold the result.** And the packet holds
  ~3 paragraphs out of 500 candidates. The measured first-12 dev items show every
  head at survival 1.0000: the heads reordered a set that already contained
  everything, and completion moved only through allocation.
* **Therefore the neural families are competing for ~4 points of stage-0 headroom
  and ~22 points of budget-allocation headroom, and the latter is not theirs.**
  A compound cascade spends latency to chase the former while a one-line change to
  the packing policy moves the latter.

This is a **kill-condition result**, not a null result about model quality. The
brief's own rule applies:

> If BM25 + one small reranker matches the full cascade within the minimum
> meaningful difference, the correct scientific output is "the cascade is
> unnecessary."

On the evidence available at the time of writing, BM25 + zero rerankers is within
the registered MMD of every variant measured, and the remaining measurable gap is
attributable to a **packing policy**, not to a ranker.

## 4. Mobile feasibility

Strictly separated from quality, per the brief.

| family | quality status | deployability status | evidence |
|---|---|---|---|
| B1/B4 BM25 | **measured, the strongest measured system** | **DEPLOYABLE NOW** | stdlib-only index, 10,666,728 B posting payload MEASURED, 25–80 MB RSS class, millisecond latency. No weights at all. |
| B2 static | measured, **null / slightly negative** | not worth it | 125 MB fp32 weights + 40.9 MiB vector cache for −1 paragraph. |
| B3 68M reranker | pending | **RUNTIME-BLOCKED-ish, storage-blocked on desktop** | ~273 MB fp32 weights; ~77 s/query MEASURED at threads=1. An `onnx/model_qint8_arm64.onnx` **file exists** in the snapshot — that is a file-presence check, **not** a measured runtime or parity result. |
| C shared heads | subset only | promising on paper, **unverified** | 16,863,745 params resident, head-switch 0.2–7.6 ms MEASURED, shared-vs-separate ratio 3.00× **DERIVED from parameter arithmetic, not from a measured 3-checkpoint baseline**. |
| KaLM | **not implemented** | **UNKNOWN — unmeasured** | No code, no measurement. The prior team's export concern is neither confirmed nor refuted by this run. |
| adapter/PEFT | **not implemented** | **UNKNOWN — unmeasured** | The prior team's merging concern is neither confirmed nor refuted. |
| hybrid-fusion | **not implemented** | UNKNOWN | Correctly NOT optimised first, per the brief. |

**No Android, GrapheneOS or on-device number is claimed anywhere in this run.**
Everything above is desktop CPU on an i7-8700-class host with no CUDA.

## 5. Data quality and label caveats affecting every number

* **9 of 146 worker-visible items carry no gold `answer_text`** and cannot be
  exact-matched at all. They are excluded from answer denominators and reported,
  never silently dropped.
* **Leaf context precision is structurally low (0.118 dev / 0.296 shadow_dev)**
  because the retrieval unit is the whole paragraph while the metric's denominator
  counts retrieved *leaf* nodes. Paragraph-granularity completion is the meaningful
  number; the leaf figure is reported for completeness, not as a quality signal.
* **Semantic QA rests on LLM reviewers** (accepted risk #1, unaddressed by this
  run). Required-evidence sets are reviewer judgments, not facts.
* **`staging/` is git-tracked and republishes `meta.source_articles`,
  `meta.group` and `labels.answer_text` for all 206 worker-visible items**, while
  `corpus/questions.json` was deliberately hardened to drop exactly those fields.
  Pre-existing and frozen; it does not touch the private test. It means the
  no-hidden-metadata property is enforced **procedurally** (the `QueryInput`
  boundary plus code audit), not by the repository being clean. Verified: no
  implemented retriever reads those fields.

## 6. Conclusions, in the brief's own vocabulary

| comparison | outcome |
|---|---|
| B2 static union vs B1 BM25 | **PRACTICALLY TIED / UNRESOLVED** (−1 paragraph; far below the 13-item dev MMD). Prediction confirmed: the cheap semantic channel adds nothing measurable. |
| B4 vs B1 | **IDENTICAL BY CONSTRUCTION** — same retriever; the difference is generation, which this run measures separately. |
| per-article cap 3 vs no cap | **+2 paragraphs** for removing it — below the dev MMD, therefore unresolved as a *quality* claim, but mechanistically the largest single lever and the clearest *policy* finding. |
| any neural reranker vs BM25 | **NOT YET MEASURED** (B3 and C incomplete at time of writing). Do not assume a direction. |
| oracle evidence vs BM25 evidence (answers) | **UNRESOLVED AT CURRENT POWER**, and *provably* so: 4-item ceiling against an 18-item floor. |
| oracle evidence vs degraded evidence (answers) | **CLEARLY BETTER** — p = 3.8 × 10⁻⁶, 19/19 discordant. The generator discriminates; it is the resolution that fails. |

**The headline is not an architecture. It is that the experiment's binding
constraint is the evidence token budget, and the round should be re-specified
around allocation before more rerankers are built.**
