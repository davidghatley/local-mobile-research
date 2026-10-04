# Generator-Floor Probe — Round 1, Phase 1B

**THE HARD GATE.** Result: **UNDERPOWERED / INCONCLUSIVE** — proceed, on
retrieval-primary evidence only.

Protocol: `experiments/comparability/CONTRACT.md` §5, with the 2026-10-03
orchestrator correction recorded in `experiments/R1_CONTRACT_ERRATUM.md`.
Implementation: `experiments/baselines/generator_floor.py` +
`run_floor_probe.py`. Raw artifacts:
`experiments/results/floor_probe/{dev,all}_{arms,report}.json` and, for every
item and every arm, the exact packet text under
`experiments/results/floor_probe/all_packets/`.

Scoring is `eval/answer_scoring.exact_match` — deterministic, stdlib, **no
judge**. A floor probe decided by a judge would be measuring the judge.

---

## 1. Verdict

| | |
|---|---|
| **Outcome** | `UNDERPOWERED / INCONCLUSIVE` |
| may proceed | **YES**, with the stated caveat |
| Split sets run | dev (n=59, 55 analysable) and dev+shadow_dev (n=146, 137 analysable) |
| Registered MMD used | dev 13 items / 22.0 pp; dev+shadow_dev **18 items / 12.3 pp** (`CONTRACT.md` §4) |
| Generator | `qwen25-1.5b-q4km-fixed-v1`, Q4_K_M, threads=1, greedy, max_tokens=256 |
| Judge | **not used** |

The gate's own rule for this outcome:

> continue retrieval-primary experiments, whose objective evidence metrics remain
> interpretable; **do NOT over-interpret final-answer differences**

That is what this run did. But the probe produced something more useful than the
verdict, and §4 below is the finding that actually governs the tournament.

## 2. Two defects I had to fix in my own gate before trusting it

Recorded because both would have produced a confidently wrong headline, and both
are the exact failure shape `R1_CONTRACT_ERRATUM.md` warns about.

**(a) Zero discordant pairs reported as zero effect.** With no discordant pairs I
originally returned the interval `[0, 0]`, whose upper bound is trivially below
the MMD — so a run with *no observed differences at all* would have declared
`GENERATOR FLOORED`. That is the superseded "≤5% ⇒ floored" rule wearing a
different hat. Replaced with the exact Clopper–Pearson one-sided 95% upper bound
for 0 successes in n trials (`0.0495` at n=59, `0.0203` at n=146), computed by
bisection on the binomial CDF so it needs no scipy.

**(b) Small runs looked precise because the interval was scaled to items.** The
registered MMD is an item *count*, so the interval was being converted to items
by multiplying by the *observed* n. A Wilson upper bound of 1.0 at n=3 becomes
"3 items", which sits below a 13-item MMD — so a 3-item smoke test declared
`GENERATOR FLOORED`. The verdict is now expressed in items but gated on
`n_analysable >= mmd_items` (you cannot bound a 13-item effect from 3
observations), not on `n >= split_size`. The dev split has 4 items with no gold
answer string, so 55 of 59 are analysable; a `n >= 59` guard would have refused
a verdict on a complete dev sweep forever.

Verified against 8 constructed cases before use: small-n ⇒ INCONCLUSIVE,
zero-discordance ⇒ a real bound, strong effect ⇒ NOT FLOORED, null ⇒
UNDERPOWERED. Exact McNemar p-values match closed forms (`n10=0,d=10` and
`n10=10,d=10` both ⇒ 0.001953125).

## 3. Results (dev + shadow_dev, n=137 analysable)

| arm | exact-match acc | mean exact evidence tokens | mean gen latency |
|---|---|---|---|
| **oracle** (minimal sufficient set) | **20/137 = 14.60%** | 405 | 3,513 ms |
| **oracle_size_matched** (BM25, same span count) | 18/137 = 13.14% | 345 | 3,587 ms |
| **B4** (BM25 top-500, the preregistered floor) | 16/137 = 11.68% | 795 | 4,637 ms |
| **degraded** (BM25 worst-ranked, required hosts excluded) | 1/137 = **0.73%** | 776 | 5,898 ms |

Paired, exact McNemar, on the same items:

| comparison | discordant | favours first | favours second | exact p | verdict |
|---|---|---|---|---|---|
| oracle vs degraded | 19 | **19** | 0 | **3.8 × 10⁻⁶** | generator discriminates, decisively |
| B4 vs degraded | 15 | **15** | 0 | **6.1 × 10⁻⁵** | B4's evidence beats garbage, decisively |
| oracle vs B4 | 8 | 6 | 2 | 0.289 | **not resolvable** |
| oracle vs oracle_size_matched | 2 | 2 | 0 | 0.500 | **not resolvable** |

## 4. The finding that governs the tournament

### 4.1 The generator is NOT blind to evidence

This is settled, and it is the opposite of a floor. Given the *same* questions
and the *same* generator, swapping deliberately wrong evidence for correct
evidence moves accuracy from **0.73% to 14.60%** — a 14× difference, with all 19
discordant pairs favouring the oracle, p = 3.8 × 10⁻⁶. B4's own evidence beats
the degraded control at p = 6.1 × 10⁻⁵. The negative control did precisely the job
`experiments/baselines/HYPOTHESIS.md` §6 assigned it: it rules out "the generator
cannot see evidence", which is the failure mode a floor verdict would have meant.

So the reason the oracle-vs-B4 comparison is unresolvable is **not** that the
generator ignores evidence. It is arithmetic about magnitudes:

> **Oracle accuracy is 14.60%. B4 accuracy is 11.68%.**
> **The entire headroom that perfect retrieval could possibly buy is 2.92 pp = 4 items.**
> **The registered resolution floor on this split set is 18 items = 12.3 pp.**

**The generator's ceiling sits an order of magnitude below the benchmark's
discrimination threshold.** Therefore:

1. **No architecture can be resolved by final-answer quality on this corpus, and
   this is knowable in advance of running any of them.** Even a retriever that
   returned the exact oracle packet for every item — the best case physically
   available — would produce a 4-item gain against an 18-item floor. Every
   architecture pair compared on answers will be a null, by arithmetic, not by
   accident.
2. **The retrieval/evidence metrics must carry the entire tournament.** Those are
   objective, judge-free, generator-free, and they do discriminate (§5).
3. Any future claim of the form "architecture X answers better than Y" on this
   corpus should be treated as **unsupported by construction**, not as a finding
   awaiting replication.

### 4.2 The preregistered metric is confounded by answer verbosity

Under the *exploratory, non-preregistered* containment check — is the gold answer
string present anywhere in the output — the ranking is the same but the levels are
wildly different:

| arm | containment | exact-match |
|---|---|---|
| oracle | 81.02% | 14.60% |
| oracle_size_matched | 69.34% | 13.14% |
| B4 | 67.15% | 11.68% |
| degraded | 19.71% | 0.73% |

B4's packet **contains** the gold answer for 67% of items yet scores 11.7% on
exact match. The gap is almost entirely a *format* penalty: the fixed prompt makes
the generator append a citation justification whose length grows with packet size,
and strict `exact_match` marks a verbose-but-correct answer wrong.

This confound runs **in both directions** and must be stated whenever answer
metrics are discussed:
- it can manufacture an apparent oracle advantage, because oracle packets are
  tighter (405 vs 795 tokens);
- it can hide a real one.

The `oracle_size_matched` arm exists to control for it — BM25's best paragraphs
truncated to the oracle's span count, varying only *which* paragraphs are present.
Oracle still beats it, but with 2 discordant pairs and p = 0.50, i.e. not
resolvably.

**`exact_match` remains the primary, preregistered metric.** The containment check
is reported alongside it and is explicitly labelled non-preregistered. Promoting
it after observing that it moves would be post-hoc threshold invention, which is
the thing this repository exists to prevent. Its real use is diagnostic: it
quantifies how much of the answer metric is measuring terseness.

## 5. Why retrieval-primary is nonetheless sound

Measured on dev, retrieval only, no generator involved
(`experiments/results/retrieval/dev_core/`):

| metric | value |
|---|---|
| BM25 stage-0 survival @500 (required paragraphs) | **70/73 = 0.9589** |
| final packet completion | 54/73 = 0.7397 |
| item-level completion | 0.7636 |
| loss attributable to the per-article cap of 3 | 10/73 |
| loss attributable to the 1000-token budget | 6/73 |
| loss attributable to stage-0 rank | 3/73 |

These are deterministic, need no judge, no generator and no answer, and they
separate systems. They are therefore unaffected by everything in §4. The
tournament proceeds on them.

## 6. Consequences, applied

| instruction | applied? |
|---|---|
| "If GENERATOR NOT FLOORED: continue with the fixed generator." | n/a — not the outcome |
| "If UNDERPOWERED: record the limitation; continue retrieval-primary experiments; do not over-interpret final-answer differences." | **YES.** Recorded here, continued, and answer differences are explicitly quarantined. |
| "If GENERATOR FLOORED: STOP, run a generator replacement study on DEV only, re-freeze the contract." | **NOT triggered.** No replacement study, no re-freeze. The generator contract is unchanged. |

The generator contract `qwen25-1.5b-q4km-fixed-v1` stands, unmodified. What
changes is the *role* of the answer metric: it is demoted from a possible
discriminator to a descriptive column that cannot decide any comparison on this
corpus.

**No private data was touched.** The probe read `staging/` ground truth for
worker-visible dev/shadow_dev items only, through the custodian path, and
required the explicit `LMR_CUSTODIAN_ORACLE_TOKEN` to build oracle packets. The
sealed private set was never opened.

## 7. What would actually resolve this

Not more items — the effect is bounded, not merely noisy. The arithmetic says a
usable answer-metric tournament needs the generator's oracle ceiling to sit
*above* the registered MMD, and it is at 14.6% against a 12.3 pp threshold, so the
generator would have to roughly triple its accuracy on gold evidence. The three
levers, in order of honest cost:

1. **Stop scoring final answers as a tournament metric.** Retrieval and evidence
   metrics already discriminate and cost nothing to compute. This is the
   recommendation.
2. **A stronger generator**, which is a different tournament with a different
   contract and would need its own floor probe. Out of scope for Round 1.
3. **More analysable items.** 9 of 146 worker-visible items carry no gold answer
   string and cannot be exact-matched at all. Fixing that raises n by ~6% and
   cannot bridge a 4-item effect to an 18-item threshold.
