# Shortlist and Proposed Private-Test Protocol

Status: **pre-private.** The sealed private test has **NOT** been run. Nothing in
this document has been informed by any private result, because no private result
exists and none was requested.

---

## 1. Shortlist for private evaluation

### RECOMMEND — the challenger (this is now an evidence-backed recommendation)

| system | evidence |
|---|---|
| **C — shared encoder + multiple heads (17M)** | **The only architecture in Round 1 that clears the registered threshold.** Pooled dev+shadow_dev completion **160/195 = 0.8205 vs B1's 134/195 = 0.6872**: **+26 paragraphs = +13.33 pp against an 18-item MMD, with disjoint Wilson CIs** [0.7606, 0.8680] vs [0.6190, 0.7481]. Confirmed on shadow_dev **+16 paragraphs = +13.11 pp vs a 15-item MMD**, in a single run executed after a written freeze (`experiments/shared_heads/FREEZE_RECORD.md`) with zero tuning afterwards. It achieves this with **58 fewer mean evidence tokens** and **1.9× higher leaf context precision**. Correctness gate: shared-forward parity max abs diff **0.0**. |

**What recommending C does and does not mean.** C is recommended *as the single
challenger worth sealed items*, not as a proven mobile product. It costs 70,777,255 B
of weights and 300× BM25's latency on shadow_dev (26,161 ms vs 87.2 ms median),
and **no ONNX export, int8 parity gate, or on-device measurement was performed**.
A private run would establish that the quality result replicates on 116 unseen
items. It would establish nothing about phone deployment.

### RECOMMEND — the reference arm

| system | why |
|---|---|
| **B1 (BM25, `k1=1.2, b=0.75`, top-500, shared packing policy)** | The reference every kill condition is written against. Stage-0 survival 0.9589 dev / 0.9836 shadow_dev; completion 0.6872 pooled. **10,666,728 B** index payload, no weights, 36–87 ms median, **DEPLOYABLE TODAY**. It must be in the private run as the comparator, because "does C beat BM25" is the only question the private set can answer. |

B1 and B4 share a retriever and differ only in that B4 drives the generator. Since
the answer metric is now **known** to be unresolvable (§1 of
`experiments/results/R1_ANALYSIS.md`), **the private run needs B1's retrieval
metrics, and B4's answer column only as a descriptive record.** Running both as
scored arms would consume 116 sealed items twice for one hypothesis.

### DO NOT SEND — resolved by dev/shadow_dev already

| system | reason |
|---|---|
| **B3 (BM25 → 68M cross-encoder)** | **RETAIN AS SCIENTIFIC REFERENCE ONLY.** Dev completion 65/73 vs C's 64/73 — **one paragraph apart** — at **3.9× the weights** (276,173,159 B vs 70,777,255 B) and **2.0× the latency**. Practically tied, so it is not distinguishable on quality; and it is dominated on cost. Sending it to private would spend sealed items to re-measure a settled tie in favour of the smaller system. |
| **B2 (BM25 + static semantic union)** | **REJECT.** Completion 0.7260 vs B1's 0.7397 — one paragraph WORSE. Stage-0 survival **identical**: the static channel contributed **zero** additional required evidence. Cost: 125,729,604 B of weights + 40,873,912 B of cache = **166.6 MB** for −1 paragraph. This confirms the prediction preregistered in `experiments/baselines/HYPOTHESIS.md` §4.5 exactly. |
| **Ettin cascade** | **NOT RUN.** Implementation written, never executed. Its own kill rules ("if 17M ≈ 68M, test 17M-only") are unapplied — though note that the C-vs-B3 comparison already answers the underlying question in the collapse direction. |
| **KaLM coarse-to-fine** | **NOT IMPLEMENTED. MOBILE DEPLOYABILITY = BLOCKED**, confirmed with evidence rather than repeated: the Hub listing for `KaLM-Reranker-V1-Nano-R2` @ `32b242bb` (1,572,182,264 B) contains **zero non-PyTorch artifacts**, and stock llama.cpp cannot convert T5Gemma2 or ModernBERT. **There is nothing to export at any compression ratio.** Not a quality question — an artifact-layer dead end. |
| **Adapter / PEFT (LoRA)** | **NOT IMPLEMENTED. Storage advantage NEUTRALISED at deploy**, confirmed: sharing wins only while `Σ|adapters| < (A−1)×|base|`, and on the 17M base merging a second task already costs ~134.9 MB — **more than C's entire encoder**. No checked runtime preserves dynamic swapping for these encoders (llama.cpp `--lora` is generative-path only; ORT LoRA is GenAI-only). |
| **Hybrid fusion** | **NOT IMPLEMENTED.** Correctly not optimised first, and it now has nothing measured to fuse: the only two components with measured value (B3, C) are practically tied with each other. |

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
| **P1 — BM25 reference** | The frozen B1 configuration verbatim: `D(p)` index strings, pinned tokenizer, `k1=1.2 b=0.75`, no stemming, no stopwords, top-500, per-article cap 3, `build_packet(exact=True, pinned tokenizer, cap=1000)`. **Comparator.** |
| **P2 — shared encoder + heads (17M)** | The frozen C configuration verbatim, as recorded in `experiments/shared_heads/FREEZE_RECORD.md`: same shared BM25 stage-0 (top-500), one shared `ettin-reranker-17m-v1` encode over all 500 candidates, then coarse/fine/sufficiency readouts at top-50, per-article cap 3, same exact-token 1000-token budget. Zero-shot; no adapters; no trained weights. |

Explicitly **not** in the tournament: B3 (tied with C on quality, dominated on
cost), B2 (measured negative), the oracle packet, the degraded control, any
unrun or unimplemented architecture, and any variant of P1 or P2 with a different
budget, cap, or breadth.

**Two arms. Not three.** Every additional arm spends irreplaceable sealed items to
resolve differences this corpus cannot resolve, which is the central registered
finding of Round 1.

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
* Wilson 95% intervals on **both** arms, with hits/n recorded so the interval can
  be recomputed independently. The preregistered worker-visible result is
  recorded here for comparison and **must not be treated as a prior to confirm**:
  it is C 160/195 = 0.8205 vs B1 134/195 = 0.6872, disjoint Wilson CIs. The
  private run is a **single independent observation**, not a replication of a
  known answer.
* **If P2 − P1 ≥ 16 items → report the effect with its interval, and state that
  it replicates the worker-visible direction.** This is the expected outcome, so
  say in advance that a positive result is a *confirmation of an already-measured
  effect*, not a discovery. Overclaiming a confirmation as an independent finding
  is the specific failure this paragraph exists to prevent.
* **If P2 − P1 < 16 items → the recorded output is "the challenger is not
  distinguishable from BM25 on this corpus"**, and per the kill condition the
  correct conclusion is that **the challenger is unnecessary** — which may not be
  reframed as "the challenger works but BM25 is close." Note that the
  worker-visible evidence points the other way, so a null here would be a genuine
  surprise and must be reported as one, with the worker-visible numbers quoted
  alongside.
* **If P2 − P1 < 0 → the effect does not replicate at all.** Report plainly. Do
  not explain it away as noise without the interval.

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

### 3.6 Run it — with one condition attached

The earlier draft of this document said that if every challenger sat within the
registered MMD of BM25, the honest recommendation would be **not** to run the
private test at all. That condition did not fire, and the reason is worth stating
because it is the whole point of running dev and shadow_dev first:

**C cleared the threshold on the powered split set** (26 items vs an 18-item MMD,
disjoint Wilson CIs) **and replicated it on shadow_dev** (16 items vs a 15-item
MMD) in a single frozen run. So the private test now has exactly one
discriminating question — *does a +13 pp evidence-completion effect replicate on
116 unseen items?* — and answering it costs two arms rather than six.

**The condition I would attach: run P1 and P2 retrieval-only.** No generator
invocation in the private run at all. The floor probe established that the answer
metric cannot resolve anything on this corpus (a 4-item achievable ceiling
against a 16-item threshold), so spending generation time on 116 sealed items
would buy nothing. This also removes the generator from the private critical path
entirely, which removes a whole class of custody risk for no scientific loss.

**What the private run cannot tell you**, and should not be asked to: whether C is
deployable on a phone. That needs an ONNX export, an int8 parity gate against the
fp32 reference (Spearman ≥ 0.99 on top-100, ≤ 1 item completion delta on 10 dev
items), and a real on-device measurement. **None of that exists**, and no private
score would substitute for it. Recommend doing that work in parallel with, not
after, the private run.
