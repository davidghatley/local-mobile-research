# Shortlist and Proposed Private-Test Protocol

Status: **pre-private.** The sealed private test has **NOT** been run. Nothing in
this document has been informed by any private result, because no private result
exists and none was requested.

---

## 1. Shortlist for private evaluation

### RECOMMEND — the reference arm

| system | why |
|---|---|
| **B1 / B4 (BM25, `k1=1.2, b=0.75`, top-500, shared packing policy)** | The strongest MEASURED system in this run and the only one with no weights at all. Stage-0 survival 0.9589 dev / 0.9836 shadow_dev; completion 0.7397 dev. 10,666,728 B index payload, 36 ms median latency, deployable today. Every other system must be measured *against* this, and the kill conditions in `experiments/comparability/CONTRACT.md` §6 are written in terms of it. |

B1 and B4 share a retriever and differ only in that B4 drives the generator. Since
the answer metric is now known to be unresolvable (§3 of
`experiments/results/R1_ANALYSIS.md`), **the private run needs B1's retrieval
metrics, and B4's answer column only as a descriptive record.** Testing both
consumes private items twice for one hypothesis.

### RECOMMEND — the ceiling arm, conditional

| system | condition |
|---|---|
| **B3 (BM25 top-500 → 68M cross-encoder → top-50)** | **Only if** its dev run finishes and shows either (a) completion above B1 by ≥ the registered MMD, or (b) at minimum a measurable per-stage reordering that justifies ~2,100× B1's latency (77 s vs 36 ms). If its dev completion lands within the MMD of B1 — which is the likely outcome given stage-0 saturation — it should be **retained as a scientific reference and NOT sent to private**, because spending the one-shot private set to confirm a null that dev already resolved is exactly the waste the register exists to prevent. |

### REJECT

| system | reason |
|---|---|
| **B2 (BM25 + static semantic union)** | **MEASURED null-to-negative.** Completion 0.7260 vs B1's 0.7397 — one paragraph WORSE. Stage-0 survival **identical** (70/73): the static channel contributed **zero** additional required evidence. Cost: 125,729,604 B of weights + 40,873,912 B of vector cache = **177 MB** and 6× the latency, for −1 paragraph. This confirms the preregistered prediction in `experiments/baselines/HYPOTHESIS.md` §4.5 exactly. Sending it to private would spend sealed items to re-measure a settled null. |

### NOT READY — do not send to private

| system | state |
|---|---|
| **C — shared encoder + multiple heads** | Implementation complete and correctness-gated (shared-forward parity vs the reference path: max abs diff **0.0**; 16,863,745 params resident; head-switch 0.2–7.6 ms). Full-dev quality run **in flight at time of writing**. Latency is the concern: **32.6 s median per query vs BM25's 36 ms — ~900×.** It needs a completed dev comparison before it can be shortlisted on quality grounds at all. |
| **Ettin cascade** | Implementation written, **never run**. No traces, no metrics. Its own team's kill rules ("if 17M ≈ 68M, test 17M-only") have not been applied because nothing has been measured. |
| **KaLM coarse-to-fine** | **NOT IMPLEMENTED.** No code, no measurement. The prior team's concern about a missing exportable mobile backend is neither confirmed nor refuted here. |
| **Adapter / PEFT (LoRA)** | **NOT IMPLEMENTED.** The prior team's merging concern is neither confirmed nor refuted. |
| **Hybrid fusion** | **NOT IMPLEMENTED.** Correctly not optimised first, per the brief — but it also cannot be recommended, because its components have no measured value to fuse. |

### RETAIN AS SCIENTIFIC REFERENCE ONLY

* The **oracle-evidence condition** — not a retriever, never a private candidate.
  Its role is the floor probe's upper bound, and it has already served it.
* **The degraded control** — likewise not a candidate; it exists to prove the
  generator discriminates, which it did (p = 3.8 × 10⁻⁶).

---

## 2. What the evidence says the private test should actually test

The measured findings constrain this sharply, and it is worth stating plainly
because it inverts the tournament's premise.

1. **Answer quality cannot be the private metric.** The oracle ceiling is 14.60%
   exact-match and B4 achieves 11.68%, so perfect retrieval buys **4 items**
   against a registered private MMD of **16 items**. A private run scored on final
   answers is a coin flip dressed as a result. **Recommend: score the private test
   on retrieval/evidence metrics only.** If answer metrics are recorded at all,
   they must be reported as descriptive, with the 4-item ceiling stated next to
   them.

2. **The private test should test the budget hypothesis, not the ranker
   hypothesis.** This run's central finding is that the 1000-token evidence budget
   is the binding constraint (26.0% of required evidence lost post-retrieval;
   4.1% lost at stage 0). A private run comparing rerankers would be measuring the
   4.1%.

3. **Do not widen the architecture list.** Every additional system on the private
   set spends irreplaceable sealed items to resolve differences the corpus cannot
   resolve. Two arms is the honest maximum.

---

## 3. Proposed frozen private-test tournament protocol

To be preregistered and frozen **before** the private directory is read, and only
after the outstanding dev runs close.

### 3.1 Arms — exactly two

| arm | definition |
|---|---|
| **P1 — BM25 reference** | The frozen B1 configuration verbatim: `D(p)` index strings, pinned tokenizer, `k1=1.2 b=0.75`, no stemming, no stopwords, top-500, per-article cap 3, `build_packet(exact=True, pinned tokenizer, cap=1000)`. |
| **P2 — the single surviving challenger** | Whichever single system clears §4 below. At most one. If none clears, **P1 runs alone** and that is a complete, publishable result. |

Explicitly **not** in the tournament: the oracle packet, the degraded control,
B2, any unrun architecture, and any variant of P1 with a different budget.

### 3.2 Preregistered metrics — retrieval/evidence only

Primary, in the frozen tie-break order of `CONTRACT.md` §3:
required-evidence survival per stage → stage-0 recall → candidate reduction ratio
→ final evidence recall → evidence token cost → context precision → latency →
RAM → storage.

Every one of these is computed by `experiments/common/score_retrieval.py` from
raw traces, needs no judge, and needs no generator. `None` in telemetry means
explicitly not measured and is never 0.

**Answer metrics: collected descriptively, never decisive**, and reported with the
4-item ceiling and the 16-item private MMD printed adjacent to them.

### 3.3 Preregistered decision rule

* Private MMD: **16 items = 13.8 pp** (`CONTRACT.md` §4, the registered row).
* A gap below 16 items is reported as **PRACTICALLY TIED / UNRESOLVED AT CURRENT
  POWER**. Not a win. Not a ranking.
* Wilson 95% intervals on both arms, with hits/n recorded so the interval can be
  recomputed independently.
* If P2 ≤ P1 by less than 16 items: the recorded output is **"the challenger is
  not distinguishable from BM25 on this corpus"** — and, per the kill condition,
  **the correct conclusion is that the challenger is unnecessary**, which may not
  be reframed as "the challenger works but BM25 is close."
* If P2 > P1 by ≥ 16 items: report the effect size with its interval, and note
  that a single non-tied result on a 16-item threshold is one observation, not a
  replication.

### 3.4 Freeze requirements — all recorded before the private directory is opened

architecture id · git commit · model id **and revision** · weight sha256 ·
quantization · adapter hash · training dataset hash · training manifest ·
Regime A/B manifests · thresholds · calibration parameters · seeds · candidate
limits · evidence budget · generator hash · prompt hash · runtime versions.

### 3.5 Anti-leak rules (unchanged, non-negotiable)

* No threshold, budget, or ranking policy may be selected on private items. Any
  threshold so selected voids the run.
* `docs/scoring-protocol.md` may not be modified after private outputs exist.
* No architecture worker may read the private directory at any point.
* Synthetic training data requires custodian leakage clearance **before** use;
  only `PASS` admits data, and `REJECT` returns synthetic ids only.

### 3.6 What would make me recommend NOT running the private test at all

If the outstanding dev runs show that **every** challenger sits within the
registered MMD of BM25 — which is the current expectation, given stage-0 survival
of 0.9589–0.9836 — then the private test has no discriminating question left to
answer. Spending a 116-item sealed set to confirm that is not a scientific
purpose.

**In that case the honest recommendation is: do not run the private test, and
re-specify Round 2 around evidence-budget allocation instead of retrieval
ranking.** That recommendation is itself a legitimate outcome of this run, and
preferring it over spending sealed items is the whole point of having run the
floor probe and the dev comparisons first.
