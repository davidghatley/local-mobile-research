# local-mobile-research

An **offline, System-1 retrieval tournament** for on-device / GrapheneOS
question answering. The question is narrow and falsifiable:

> On a 297-article corpus, a phone, and a *fixed* small generator, **does
> retrieval quality actually matter — and what is the cheapest architecture that
> captures it?**

The generator is held constant on purpose. If evidence quality barely moves the
answer, retrieval research on-device is decoration, and this project is designed
to be able to conclude that.

**Experimental research only.** Every measurement in this repository is a
**desktop** measurement. No Android, GrapheneOS, or on-device performance claim
may be derived from anything recorded here. Several architectures are expected to
be ruled out at the *runtime* layer rather than the quality layer, and that is a
result, not a failure.

---

## Current state

| | |
| --- | --- |
| **Round 0** | **FROZEN** at tag [`round0-freeze-r1`](STATUS.md) |
| **Round 1** | Mise-en-place complete — six readiness reports, **no implementation yet** |
| Verification | `./scripts/verify_round0` → 10/10 stages PASS, exit 0, clean tree |
| Tests | 518 (`tests/`), 77 (`data_tools/`), 17 (`corpus/`) |
| Adversarial probes | `./docs/probes_round0.sh` → 11 probes, 18/18 checks |
| CI | GitHub Actions GREEN |
| Independent reviews | 8 freeze reviews — **7 `REPAIR REQUIRED`, then `PASS`** |

### Read these first

| Document | What it is |
| --- | --- |
| **[docs/STATUS.md](STATUS.md)** | The authoritative state record, the dated **ACCEPTED RISKS** table, and the freeze block. |
| **[docs/ROUND0_CLOSURE.md](ROUND0_CLOSURE.md)** | **What actually happened** — the eight reviews, every defect found, the freeze, and Round 1. Start here for the story. |
| **[experiments/R1_CONTRACT_ERRATUM.md](../experiments/R1_CONTRACT_ERRATUM.md)** | Post-freeze corrections, the threshold register, and the generator-floor rule. |
| [experiments/R1_TRAINING_CONTRACT.md](../experiments/R1_TRAINING_CONTRACT.md) | The preregistered common contract every Round 1 team receives. **Frozen — do not edit; see the erratum.** |

---

## The two things that outrank any architecture result

**1. This corpus can only separate architectures that differ by ~10 percentage
points.** Computed and cross-checked two ways
([`experiments/comparability/CONTRACT.md` §4](../experiments/comparability/CONTRACT.md)):

| split | n | minimum meaningful difference |
| --- | --- | --- |
| dev | 59 | 13 items = **22.0 pp** |
| shadow_dev | 87 | 15 items = **17.2 pp** |
| dev + shadow_dev | 146 | 18 items = **12.3 pp** |
| private (sealed) | 116 | 16 items = **13.8 pp** |
| all worker-visible | 206 | 21 items = **10.2 pp** |

That is underpowered for **most** architecture pairs, not merely close ones. A gap
below the threshold is noise and **must be recorded as a null result, never as a
win.**

**2. Two of five candidate families may be blocked at the runtime layer, not the
quality layer** — one has no exportable mobile backend at all, and one cannot ship
its adapter without merging it, which removes the argument for having an adapter.

And before either matters: **the generator floor has not been probed.** If the
fixed 1.5B Q4 generator cannot express differences between good and poor evidence
packets, the entire retrieval tournament measures nothing above the floor.

---

## Custody: the private test

The private test — 116 items, 62 groups — lives **outside this repository**, at
`$LMR_PRIVATE_EVAL_DIR`. It is sealed and never committed.

- In-repo, `corpus/private_test_manifest.json` carries **counts and hashes only**.
- No private question, answer, support atom, source id, or label appears in this
  repository, in any branch, or in its history.
- The model-facing surface is exactly `{question_id, text}`
  (`substrate/query.py`), enforced fail-closed by
  `assert_no_label_metadata`.
- The **out-of-repo** census pin is the trust root. Editing the corpus *and* its
  census together is caught, because the pin is not co-editable.
- The freeze tag, the durable manifest, and the tag-binding record are a
  **procedural custodian attestation, not a signature.**

Anyone working here should read [docs/private-eval-custody.md](private-eval-custody.md)
before touching anything under `experiments/`.

---

## Layout

```
substrate/     frozen shared substrate — query, evidence, manifest, telemetry, splits
eval/          frozen scoring, metrics, support, scale analysis
corpus/        206-item public partition, 297-article corpus, 940-article scale tier
generator/     the FIXED generator + pinned prompt (Round 1 is not a generator tournament)
data_tools/    corpus build, QA authoring, leakage gate
tests/         518 tests
scripts/       verify_round0 — the 10-stage freeze gate
experiments/   Round 1 architecture teams (created after the freeze)
docs/          protocol, reviews, ledgers, and this documentation
```

## Verify it yourself

```bash
export LMR_PRIVATE_EVAL_DIR=/path/to/local-mobile-research-private-eval

./scripts/verify_round0            # full: all 10 load-bearing stages, exit 0
./scripts/verify_round0 --code-only  # 7 stages, no private dir — this is NOT a freeze pass
./docs/probes_round0.sh            # 11 adversarial probes, 18 checks
python3 -m unittest discover -s tests
```

`--code-only` deliberately **drops the private-custody stage**: a real freeze needs
the out-of-repo private directory. The repo-contained half of that custody check
stays covered hermetically by `tests/test_private_eval_tripwire.py`. The CI log
says so in as many words on every run.

---

## The lesson this repository keeps re-learning

An internal consistency check is **necessary and never sufficient**. The same
failure shape appeared at three scales — a single item, a whole partition, and the
entire freeze:

- a partition census that agreed with itself because it was derived from the data
  it was supposed to check;
- a truncation that passed three consecutive stages;
- a fix that was defeated by co-editing the data and its census together;
- a stage that compared nothing and reported PASS;
- a leakage gate that, as first written, could never return PASS — and then, once
  repaired, was re-scoped because its behaviour made it an adaptive membership
  oracle;
- a `FROZEN AT` preregistration anchor pointing at a commit where the policy file
  **did not exist**;
- a scientific contract whose stated minimum meaningful difference was wrong by
  roughly **2×**, and refuted by its own worked example three lines earlier.

Each of these was found by a fresh pair of eyes, not by the team that wrote the
code. See [docs/ROUND0_CLOSURE.md](ROUND0_CLOSURE.md) for the full account.

## Ground rules

- The orchestrator may use a premium model; **every subagent must explicitly select
  a verified-free endpoint**. Nested spawning is disabled. Paid fallback is
  prohibited. Endpoint substitutions and failures are recorded, never papered over.
- The controlling specification is `master_orchestration_prompt.txt`.
- Public bounty questions are development/reference only — **never training
  examples**.
- Distinguish measured results, estimates, hypotheses, and interpretations. Label
  every number `MEASURED` or `ESTIMATED`.
- Preserve raw traces and exact provenance. A missing artifact blocks the freeze.
- **Do not claim Android performance from desktop measurements.**
