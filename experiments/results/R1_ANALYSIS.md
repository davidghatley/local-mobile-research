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

| system | n | stage-0 survival | completion | item-level | leaf precision | mean tokens | median latency | weights |
|---|---|---|---|---|---|---|---|---|
| **`C_shared_heads_17m`** | 59 | 0.9589 | **0.8767** | **0.8909** | **0.1923** | 759 | 39,636 ms | 70,777,255 B |
| `B1_bm25` | 59 | 0.9589 | 0.7397 | 0.7636 | 0.1181 | 781 | 36.3 ms | none |
| `B4_bm25_fixed_generator` | 59 | 0.9589 | 0.7397 | 0.7636 | 0.1181 | 781 | 38.4 ms | none |
| `B2_bm25_static_union` | 59 | 0.9589 | 0.7260 | 0.7455 | — | 746 | 217.1 ms | 125,729,604 B |

All five rows are the **same 59 dev items, the same 73 required paragraphs, the
same 1000-token exact-token budget, the same shared BM25 stage-0.** The
`C_shared_heads_17m` row is a full n=59 run; an earlier n=12 subset of the same
system showed completion 0.9375 and was correctly NOT comparable — it is
superseded.

### 2.1 The one real effect in this round — and it is an allocation effect

`C_shared_heads_17m` beats BM25 by **+10 paragraphs, 54/73 → 64/73 = +13.70 pp**
of final packet completion. Item-level completion rises 0.7636 → 0.8909; leaf
context precision rises 0.1181 → 0.1923; and it does so while using **fewer**
mean evidence tokens (759 vs 781) — more required evidence inside the same cap.

The mechanism is exactly what §1.2 predicts, and the per-stage survival numbers
prove it:

```
bm25              70/73 = 0.9589
heads_coarse      70/73 = 0.9589   <- unchanged
heads_fine        70/73 = 0.9589   <- unchanged
heads_sufficiency 70/73 = 0.9589   <- unchanged
```

**Not one required paragraph was added by any head.** All 500 candidates were
already there; the heads only reordered them so that more required paragraphs
landed inside the ~3 available slots. The entire gain is budget allocation.

This is the strongest confirmation of this run's central claim: **on this corpus
the architecture's job is allocation, not retrieval.** A family that had improved
stage-0 recall would have been solving a problem that does not exist here.

### 2.2 The multi-head hypothesis is confirmed — on the cost side

Per-stage median latency for C:

| stage | median | share of total |
|---|---|---|
| `bm25` | 70.8 ms | 0.2% |
| `heads_coarse` (the single shared encode) | 39,538 ms | **99.8%** |
| `heads_fine` (readout) | 3.8 ms | 0.0% |
| `heads_sufficiency` (readout) | 7.1 ms | 0.0% |

Three heads cost **10.9 ms combined against a 39.5 s encode**. Head-switching is
free relative to encoding, which is the whole multi-head argument: one shared
representation replaces three separate models. The 3.00× parameter and compute
ratios remain **DERIVED** from measured components rather than measured against a
separately-run 3-checkpoint baseline — that baseline was not run, and the
distinction is preserved.

**But the cost is brutal and must be stated plainly: 39,636 ms median vs BM25's
36.3 ms is 1,093×.** Under the preregistered tie-break chain, which prefers lower
evidence-token cost and then lower latency, C wins the primary quality metric and
loses the cost metrics decisively.

### 2.3 Registered-threshold reading of C vs B1

| split set | registered MMD | measured delta | outcome |
|---|---|---|---|
| dev (n=59) | 13 items / 22.0 pp | 10 items / 13.70 pp | **UNRESOLVED at current power** — below the dev threshold |
| dev + shadow_dev (n=146) | 18 items / 12.3 pp | 13.70 pp in percentage terms exceeds 12.3 pp | **the powered split set decides** |

So the dev result alone is *not* a win, and this document does not call it one. It
is a large effect that the dev split cannot resolve, which is precisely the
situation the single shadow_dev confirmation run exists to settle. C's
configuration was frozen in `experiments/shared_heads/FREEZE_RECORD.md` **before**
that run was launched.

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

Cost paid for nothing: 125,729,604 B of weights, a 40,873,912 B document-vector
cache, and 6× the latency — for −1 paragraph.

## 3. What the neural families can and cannot do here

This follows from §1.2 rather than from any model's quality, and Family C is the
proof of it.

* **Survival metrics are saturated and cannot be improved by reordering.** BM25
  keeps 95.9% (dev) / 98.4% (shadow_dev) of required evidence at stage 0. Family
  C's four stages all read 70/73 — identical — because a head reorders *within* the
  stage-0 set and cannot add to it.
* **The movable metric is final packet completion, and it is worth 13.70 pp.** C
  captured most of it. That is the entire measured opportunity in this corpus
  short of a better stage 0.
* **What remains unclaimed by anyone:** the 3 required paragraphs outside BM25's
  top-500 (4.1%). No implemented system retrieved them.
* **Therefore the tournament is a budget-allocation contest with a 4.1%
  retrieval contest attached**, and the brief's kill rule fires on the retrieval
  half: *if BM25 + one small reranker matches the full cascade within the
  minimum meaningful difference, the correct scientific output is "the cascade is
  unnecessary."*

What C does **not** establish, and this is important:

* it does not show the cascade is unnecessary — it shows a single 17M encoder with
  cheap readouts captures the allocation gain. A cascade's *additional* stages were
  never run, so the cascade-vs-C comparison is **UNMEASURED**;
* it does not show which head produced the gain — all three share one encode, and
  the run cannot attribute it;
* it does not show the gain survives on shadow_dev. That run was launched once,
  after the freeze, and its result is not in this document.

## 4. Mobile feasibility

Strictly separated from quality, per the brief. All figures MEASURED on desktop
CPU; **no Android, GrapheneOS or on-device number is claimed anywhere.**

| family | quality status | deployability status | evidence |
|---|---|---|---|
| B1/B4 BM25 | measured; the reference | **DEPLOYABLE NOW** | stdlib-only, **10,666,728 B** index payload, no weights, **36.3 ms** median / 125.4 ms p95 |
| B2 static | measured **null-to-negative** (−1 paragraph) | **NOT WORTH IT** | 125,729,604 B weights + 40,873,912 B cache = 166.6 MB, 217.1 ms median, for −1 paragraph |
| **C shared heads** | **measured: +13.70 pp completion, UNRESOLVED on dev, pending the single shadow run** | **UNVERIFIED** | 70,777,255 B weights; **1,093× BM25's latency**; ONNX/int8 export **not attempted**; no parity gate run |
| B3 68M reranker | run in flight at time of writing | **storage/runtime blocked on desktop** | ~273 MB fp32 weights; an `onnx/model_qint8_arm64.onnx` **file exists** in the snapshot — a file-presence check, **not** a measured runtime or parity result |
| Ettin cascade | **NOT RUN** | unknown | implementation written, never executed |
| KaLM | **NOT IMPLEMENTED** | **UNKNOWN — unmeasured** | the prior team's export concern is neither confirmed nor refuted here |
| adapter/PEFT | **NOT IMPLEMENTED** | **UNKNOWN — unmeasured** | the prior team's merging concern is neither confirmed nor refuted |
| hybrid-fusion | **NOT IMPLEMENTED** | unknown | correctly not optimised first; also has no measured components to fuse |

C's deployability is the open question that matters. A 70.8 MB encoder and a
1,093× latency penalty are both plausibly *survivable* on a phone for a 297-
article corpus and 500 candidates per query — but "plausibly survivable" is a
hypothesis, and this run deliberately does not convert it into a number. What
would settle it: an ONNX export, an int8 parity gate against the fp32 reference
(Spearman ≥ 0.99 on top-100 and ≤ 1 item final-completion delta on 10 dev items,
per `HYPOTHESIS.md` §5.4), and a real on-device measurement. None of that was
done.

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
| **C shared heads vs B1 BM25, dev** | **LARGE EFFECT, UNRESOLVED AT CURRENT POWER.** +10 paragraphs / +13.70 pp completion, but the dev MMD is 22.0 pp. Not a win on dev. Sent once to shadow_dev after a written freeze to settle it. |
| B2 static union vs B1 BM25 | **PRACTICALLY TIED / UNRESOLVED** (−1 paragraph; far below the 13-item dev MMD), and negative in sign. Preregistered prediction confirmed: the cheap semantic channel adds nothing measurable. |
| B4 vs B1 | **IDENTICAL BY CONSTRUCTION** — same retriever; the difference is generation, measured separately in the floor probe. |
| per-article cap 3 vs no cap | **+2 paragraphs** for removing it (0.7397 → 0.7671) — below the dev MMD, so unresolved as a *quality* claim, but mechanistically the largest single *policy* lever. |
| all neural heads vs BM25, **stage-0 survival** | **IDENTICAL (70/73).** Reordering cannot add candidates. Null by construction, and worth stating because it is the metric most likely to be misread as "the model did nothing". |
| B3 68M reranker vs BM25 | **NOT MEASURED** — run in flight. Do not assume a direction. |
| cascade vs C | **NOT MEASURED** — the cascade was never run. |
| oracle evidence vs BM25 evidence (answers) | **UNRESOLVED AND PROVABLY SO** — a 4-item ceiling against an 18-item floor. |
| oracle evidence vs degraded evidence (answers) | **CLEARLY BETTER** — p = 3.8 × 10⁻⁶, 19/19 discordant. The generator discriminates; it is the resolution that fails. |

**The headline is a mechanism, not a winner.** Retrieval is saturated at 0.96–0.98
and cannot be improved by reordering. What remains is a ~3-paragraph, 1000-token
allocation problem, and the single 17M shared-encoder system that attacked *that*
is the only architecture to produce a large measured effect in this round — at
1,093× the latency. Whether 70.8 MB and 1,093× is a defensible mobile trade for
+13.70 pp of evidence completion is the real question, and this run deliberately
leaves it open rather than answering it with a desktop number.
