# Shared Encoder + Multiple Heads (Family C) — Hypothesis and Readiness Report

Status: PREREGISTERED HYPOTHESIS. No training, no private evaluation, no
synthetic data, no adapter weights. Frozen substrate: tag `round0-freeze-r1`
(commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`).
Zero-shot only in this run. All measurements DESKTOP CPU. No Android or
on-device claim may be derived from any of this.
Worker endpoint: local CPU inference only (no external model endpoint; the
only network use was Hub metadata reads already recorded by peer teams).
No subagents spawned. No paid fallback used.
Companion file: `experiments/shared_heads/PLAN.md` (the ordered how, with
gates). This file is the spec, written BEFORE any shared-heads result was
observed. Implementation: `experiments/shared_heads/shared_heads.py`,
CLI: `experiments/shared_heads/run_shared_heads.py`.

Labels used throughout: **MEASURED** (timed/counted on this host on the date
given), **DERIVED** (arithmetic from measured facts), **REPORTED** (a number
from a cited artifact I did not recompute), **ESTIMATED** (to be replaced by
a `substrate.telemetry` measurement), **PREDICTION** (honest expectation, not
a result).

## 0. FALSIFIABLE HYPOTHESIS AND KILL CONDITIONS

**Hypothesis (one sentence).** One shared 17M cross-encoder backbone, run
ONCE per (query, paragraph) pair with all task heads reading out from that
single forward pass, matches the retrieval quality of one full 17M checkpoint
per task within the minimum meaningful difference, at roughly one-Nth the
resident weights and encoder FLOPs for N heads — i.e. head-sharing converts
multi-task scoring into a readout problem at single-model cost.

**What would REFUTE it (stated in advance).** On the frozen dev set (59
items) and shadow-dev set (87 items), scored through the preregistered `eval/`
harness with custodian-held labels, ANY of:

1. The shared-backbone fine head is BELOW a single-head 17M reranker run
   (identical backbone, identical head, separate process) on
   required-evidence survival (dev+shadow-dev) by more than Wilson-CI
   overlap — i.e. sharing broke the forward pass (this should be impossible
   by construction; the parity probe in PLAN.md Phase 1 guards it, and a
   failure here is an implementation bug, not a scientific finding); OR
2. The shared-heads system fails to match **B1/B4-class BM25** within the
   minimum meaningful difference — i.e. the whole neural leg adds nothing
   resolvable over the lexical floor and the heads are dead weight; OR
3. The MEASURED shared-vs-separate compute or parameter ratio is ≈ 1 (no
   saving) — i.e. head readouts cost as much as the backbone, which refutes
   the cost half of the hypothesis outright.

**The threshold register (the ONLY numbers that gate anything).** Per
`experiments/comparability/CONTRACT.md` §4 as mirrored in
`experiments/R1_CONTRACT_ERRATUM.md` E-1b (the single authoritative source;
no threshold is invented here):

| split | n | minimum meaningful difference |
|---|---|---|
| dev | 59 | **13 items = 22.0 pp** |
| dev + shadow_dev | 146 | **18 items = 12.3 pp** |

**Any gap below the applicable row is a NULL RESULT, never a win.** A null
result is a valid result and is the expected outcome at current power for
close heads (see §5). The generator-floor verdict is the three-way
McNemar rule from CONTRACT.md §5 as corrected by E-1b (no floor /
floor / inconclusive-underpowered); the superseded "≤ 5% delta ⇒ floor" rule
is explicitly NOT used.

## 1. WHAT "ONE SHARED REPRESENTATION, SEVERAL HEADS" MEANS CONCRETELY

The shared backbone is `cross-encoder/ettin-reranker-17m-v1` at pinned
revision `9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` (apache-2.0), run on
desktop CPU with `torch.set_num_threads(1)`.

Concretely, per (query, paragraph) pair from the shared BM25 stage-0 top-500:

1. **ONE backbone forward**: the model's own tokenizer pairs
   `(QueryInput.text verbatim, paragraph p.text verbatim)` — the same
   canonical cross-encoder inputs as baseline B3 — then the ModernBERT
   7-layer encoder (hidden 256) + pooling runs exactly once, producing one
   cached pooled vector per pair (500 × 256 per query). MEASURED partition
   of the resident weights: backbone + pooling = **16,797,440 params**
   (exactly the Hub-reported 16.8M figure); the native scoring head
   (Dense-256-GELU → LayerNorm → Dense-256→1) = **66,305 params**; total
   resident **16,863,745 params MEASURED** by summing the loaded state dict
   on 2026-10-04 (the 66,305-param excess over the Hub metadata figure is the
   head the metadata count excludes; both numbers are recorded, neither is
   hidden).
2. **ALL heads read from that cached vector / its single logit.** No head
   may trigger a second encoder pass. The implementation asserts this by
   structure (the backbone module is called once per batch; heads are pure
   functions of its output), and the parity probe (PLAN.md Phase 1) asserts
   the fine head is bit-identical to the single-head reference path.
3. **The candidate SET is fixed by stage 0.** Heads reorder only; no head
   adds candidates (see §5 for why this honesty matters).

This is the SIMPLEST alternative to (a) one full checkpoint per task
(3 × 16.86M ≈ 50.6M resident for three tasks, 3 encoder forwards per pair)
and (b) LoRA-swapped checkpoints (family D, `experiments/adapter-peft`):
no second checkpoint is loaded, no adapter is merged or swapped, and
switching tasks costs one readout, not one weight swap.

## 2. HEAD SET: IMPLEMENTED vs DELIBERATELY DEFERRED

| Head | Status in this run | What it is | score_kind |
|---|---|---|---|
| fine relevance | IMPLEMENTED (trained) | the model's OWN native scoring head (Dense→LN→Dense, 66,305 trained params) applied to the cached pooled vector; raw logit, never a probability | `logit` |
| coarse relevance | IMPLEMENTED (zero-shot proxy, 0 params) | within-500 tertile bucket of the fine order: 1 = top tertile (best), 2, 3; a pure function of the shared forward's output, no trained weights | `rank` |
| sufficiency (gain-per-token) | IMPLEMENTED (zero-shot proxy, 0 params) | fine logit divided by `max(1, paragraph words)`; an allocation-density signal aimed at the measured binding constraint (§5); a pure function of the shared forward's output plus paragraph length, no trained weights | `similarity` |
| evidence presence | DEFERRED | would need a token/span-level head trained with span labels; workers have no span labels (all ground truth is custodian-held); any such head belongs to a future TRAINED-heads phase under the training contract, not to a zero-shot run | — |
| entailment (NLI) | DEFERRED | would need an NLI-trained head (NLI pairs, NLI objective); there is no training in this run (§6 of the adapter-peft hypothesis and the one-shot gate apply to training families; this family does none of it); deferred to a future trained-heads phase | — |

Why the proxies are honest: they are DECLARED as untrained readouts with 0
resident params, they trigger no encoder pass, and their quality is reported
per-head through custodian scoring rather than asserted. A bare sigmoid is
never applied and nothing is called a probability: the fine head emits a raw
logit (`logit`), the coarse head emits ordinals (`rank`), the density head
emits a raw ratio (`similarity`) — all ranking-only
(`calibration_method="none_ranking_only"`, top-K policies only). The proxies
exist so the SERVING claim (one forward, N readouts, measured switch cost)
is tested even before any head is trained; they are not a quality claim.

The PACKING head is preregistered: the final ranked list handed to the shared
packer comes from the **fine** head whenever it is emitted, else the highest
priority emitted head (fine > sufficiency > coarse), recorded in
`pack_report`. Packing by the trained head keeps the comparison clean: any
future density-vs-logit allocation difference is then attributable to the
head, not to a packing change.

## 3. WHAT MUST BE MEASURED (per-head, not pooled)

Every number below is reported per head where it varies, with total resident
weights kept separate from per-head sizes:

- **total resident weights** (MEASURED param count of the loaded backbone +
  native head; tokenizer bytes recorded separately, never folded into the
  weight count);
- **per-head size** (MEASURED: fine = 66,305 params; coarse = 0; sufficiency
  = 0 — the zeros are the finding, not an omission);
- **total latency per query** (MEASURED: BM25 + one backbone forward over
  500 pairs + all emitted head readouts; `torch.set_num_threads(1)` CPU
  reference);
- **per-head latency** (MEASURED readout + sort per head, backbone excluded);
- **head-switch cost** (MEASURED: wall time to produce head B's scores given
  the cached shared representation — i.e. pure readout cost, the number that
  replaces a weight swap in family D);
- **the shared-vs-separate ratio** (DERIVED from measured components:
  1 backbone + N readouts vs N full forwards for parameters AND compute;
  this ratio IS the hypothesis, stated as a number, not an adjective);
- **quality per task** (per-head stage survival / top-K retention, scored by
  the custodian harness from the per-head stage traces — worker-side this is
  NOT YET MEASURED; the traces are the deliverable, and any gap below the §0
  register is reported UNRESOLVED AT CURRENT POWER, never as a win).

## 4. COMPARISON C (THIS FAMILY) vs D (ADAPTER-PEFT)

Identical harness (corpus, splits, stage-0 K=500, evidence budget, fixed
generator, prompt, seeds, primary metrics):

1. **B4 / deterministic floor** and **B1 BM25**: the floor both families
   must clear within the §0 register or stop.
2. **Single-head 17M reranker** (same backbone + native head, separate
   process): family C must match it within the register (parity by
   construction; a miss is a bug). This isolates sharing from quality.
3. **Family D (LoRA-adapted small base)**: C's pitch is serving shape, not
   learned quality — one resident backbone, zero training, zero synthetic
   data, zero gate interaction, task switch = one readout (microseconds,
   MEASURED) vs D's merge-and-reload per task (D HYPOTHESIS §2: unmerged
   adapters are unshippable; merged artifacts are base-size dense models per
   task). D's pitch is learned quality C cannot claim zero-shot: if a task
   needs adaptation to corpus phrasing, C's untrained proxies lose to D's
   trained adapters, and that loss is C's honest boundary. The families are
   complements across the train/no-train line, and the comparison is decided
   by custodian-scored survival gaps against the §0 register, not by
   parameter counts.
4. **B3 (68M ceiling)**: the cost bar — C should deliver its quality-per-
   parameter story at 17M shared, not at 68M.

All deltas with Wilson CIs and denominators; nulls reported as
underpowered, never as equivalence.

## 5. THE MEASURED FACTS THAT BOUND THIS DESIGN (READ FIRST)

REPORTED from `experiments/results/retrieval/dev_core/` (the current run's
own artifacts; premises of this design, not its results):

- BM25 stage-0 recall@500 keeps 70/73 = **0.9589** of required evidence
  paragraphs. Only 3/73 (4.1%) of required evidence is outside the top-500.
- Final packet completion is 54/73 = **0.7397**. So 19/73 (26.0%) of required
  evidence is LOST between stage 0 and the generator.
- Loss attribution: per-article cap of 3 accounts for 10, the 1000-token
  budget for 6, stage-0 rank for 3.
- Removing the per-article cap (sanctioned ablation, baselines HYPOTHESIS
  §2.3) moved completion only 0.7397 → 0.7671 (+2 of 19): the loss MIGRATES
  to the token budget. **The 1000-token budget is the binding constraint.**
- Mean paragraph ≈ 210 words (≈ 280 generator tokens): a 1000-token packet
  holds only ≈ 3 paragraphs.

What this implies, stated plainly because the design must not pretend
otherwise: **the retriever is already near ceiling on stage-0 recall, so
this architecture's headroom is almost entirely in ALLOCATION of a tiny
budget, not in finding candidates.** No head in this family can recover the
3/73 outside the top-500 (the candidate set is fixed by construction), and
no reorder can fit 4 paragraphs of evidence into ≈ 3 slots. The sufficiency
(density) head exists precisely because of this: when the budget binds,
gain-per-token ordering is the only readout that can beat raw-logit ordering
into the packet — and if it does not beat it beyond the §0 register, that is
a recorded null, not a failure to tune harder. **PREDICTION (preregistered):
per-head quality gaps between fine, coarse, and sufficiency readouts will
fall below the 18-item / 12.3pp register on dev+shadow-dev and be reported
UNRESOLVED AT CURRENT POWER; the resolvable claim of this run is the serving
ratio (weights, FLOPs, switch cost), not a quality win.** An ndcg/mrr
improvement is never reported as a win.

## 6. NO-ADAPTER STATEMENT (EXPLICIT)

**No adapters, no LoRA, no fine-tuning of any kind is added in this run —
zero-shot only.** No adapter may be added to this family unless the
multi-head version is shown, against the §0 register with custodian-scored
metrics, to fail to model the tasks adequately — and any such addition would
be a new preregistered phase under the training contract with its own gate
verdicts, not a silent patch to these files.

## 7. DETERMINISM AND SCORE HONESTY

- CPU only, `torch.set_num_threads(1)`, `torch.inference_mode()`, eval mode;
  re-run determinism of the reference path is asserted by the parity probe,
  cross-runtime bit equality is NOT claimed (baselines HYPOTHESIS §8.7).
- Total order per head: (head score desc, node_id asc as UTF-8 bytes), except
  coarse buckets ascending (1 = best tertile) then (logit desc, node_id asc).
- `score_kind` per §2 table; every `ThresholdPolicy` top-K-only with
  `calibration_method="none_ranking_only"`; `threshold_policy.score_kind ==
  stage.score_kind` enforced at construction by `experiments.common.trace`.
  No sigmoid, no probability language, no ECE/Brier inputs anywhere.
- Query surface strictly `QueryInput(question_id, text)` via
  `to_model_query`; paragraph inputs are corpus node text, never labels.
  `experiments.common.custodian_truth` and `experiments.common.oracle` are
  never imported in retrieval code (a test asserts this).
