# Round 1 Implementation Run — Phase 0 State Report

Date: 2026-10-04. Author: orchestrator (custodian role for this run).
Status: orientation complete, pre-implementation. No architecture result yet.

Every figure below is either a **MEASURED** local observation with the command
that produced it, or a quotation from a frozen artifact. Nothing is estimated.

---

## 1. Repository and freeze invariants

| Check | Result |
|---|---|
| HEAD at orientation | `58a7b1ae815c8e75a032a7d531ee09c689fed835` — matches the last externally observed master |
| Commits newer than observed HEAD | none |
| Working tree | clean (`git status --short` empty) before and after verification |
| `round0-freeze-r1` | annotated tag; **tag object** `9d662c95a01541199bb548c007ef5a81e0d3094e`, **target commit** `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49` |
| Dispatch metadata discrepancy | the run brief records the frozen commit as `1e5b8a3e…`. That is the **parent** of the tag target (`git rev-parse a0e7534^ == 1e5b8a3e…`, single-parent commit, one file changed: `docs/STATUS.md` +39/-3). The tag, its target, and the freeze record all agree with each other. Recorded, not repaired: nothing in the frozen set is inconsistent. |
| `verify_round0` (full, 10 stages) | **10/10 PASS**, durable out-of-repo freeze record promoted, tree stayed clean |
| `verify_round0 --code-only` | 7/7 PASS (correctly drops the custody stage) |
| `docs/probes_round0.sh` | **18/18 checks PASS**, 11 probes |
| `tests/` | **518 tests, OK, 25 skipped** |
| Frozen artifacts altered? | **NO.** No edit to the tag, to `docs/scoring-protocol.md`, to `eval/answer_scoring.py`, or to any `round0-freeze-r1` file. |

## 2. Custody state

| Check | Result |
|---|---|
| Private store | `/home/davidhatley/Projects/testing/local_mobile_research-private-eval` (the code default; the env var was unset in this shell, which is why the first full `verify_round0` refused to promote a durable record) |
| Seal | present, `c6e1e98d843eaf1eb962a9ec2f89026af2d532f9b963c5d0a78d45056293c54c` |
| Private counts | 116 items, 62 groups, 12 unanswerable, 15 paired Regime-B items over 13 source articles |
| Has any architecture ever been scored against private? | **NO.** No `private_score` / `private_result` / `private_accuracy` artifact exists anywhere in the tree. `experiments/` contains only `HYPOTHESIS.md` and `PLAN.md` prose — zero implementation, zero results. |
| Leakage gate reachable? | **YES** — seal present, so `check_training_overlap` can issue `PASS`. This unblocks Phase 4. |
| Worker-facing Regime-B list | `substrate.query.worker_regime_b_exclusions()` reads only the public 21-article artifact. |

### Disclosure and quarantine

To confirm custody was intact I called `substrate.private_eval.counts()`, the
sanctioned custodian-side accessor. It returns counts and digests by design. It
also happens to carry a field `paired_regime_b.excluded_from_adaptation_articles`
— the **private** 13-article paired list.

**That field is quarantined.** It is not written to any file in this repository,
not used to build any exclusion list, not used to select training data, and not
used to shape any retrieval candidate set. Every worker exclusion list in this
run derives from the public `corpus/regime_b_excluded_articles.json` 21-article
superset via `worker_regime_b_exclusions()`, exactly as `substrate/query.py`
requires. Private question text, answers, support atoms, source ids and
per-question results were not read.

## 3. Judge resolution (Phase 1A) — RESOLVED, and it stays non-load-bearing

Accepted risk #4 and `docs/scoring-protocol.md` §2 both require an immutable
digest before any judge metric exists. Resolved from the Hub API on 2026-10-04:

| Field | Value |
|---|---|
| Provider | huggingface.co Hub |
| Model id | `google/flan-t5-large` |
| **Revision (immutable commit SHA)** | `0613663d0d48ea86ba8cb3d7a44f0f65dc596a2a` |
| Last modified | 2023-07-17T12:49:05Z (stable ~3 years at observation) |
| Gated / private | false / false |
| License | apache-2.0 — zero-cost to obtain and run |
| Weight file | `model.safetensors`, 3,132,668,804 B, **sha256 `a9dd06ce490f139af36e9eb77dd3758b4fd07a08a73d5a1abe5ff2591e2d388e`** |
| Tokenizer | `tokenizer.json`, 2,424,064 B, blobId `fc669fbad1a6a82119ca3e1fa75db33ee22ca47d` |
| Prompt | verbatim in `docs/scoring-protocol.md` §2 (unmodified) |
| Temperature / decoding | `0.0`, greedy, `do_sample=false`, `max_new_tokens=64`, `num_beams=1`, `early_stopping=true`, input truncated to 2048 tokens |
| Output schema | verbatim JSON Schema in `docs/scoring-protocol.md` §2 (unmodified) |

**Consequence, and it is the important part:** this does not change what governs
the tournament. `experiments/comparability/CONTRACT.md` §3 already states that no
primary metric depends on the judge, and the tie-break chain
(survival → stage-0 recall → reduction → final evidence recall → token cost →
context precision → abstention → latency → RAM → storage) is entirely
deterministic. The Phase 1B generator-floor probe uses
`eval/answer_scoring.normalize_answer` / `exact_match`, not the judge. The judge
therefore becomes an *available secondary* metric, not a gate. See
`docs/judge-pin-r1.md`.

## 4. Environment reality check (MEASURED)

This is the part that determines what is physically possible in one run, and it
is stated before any implementation so the stop point is not a surprise later.

| Resource | Measured | Consequence |
|---|---|---|
| Python | 3.14.7 | — |
| Pre-installed ML stack | **none.** No `torch`, `transformers`, `tokenizers`, `sentence_transformers`, `onnxruntime`, `safetensors`, `huggingface_hub`. Only `numpy` 2.5.2. | The frozen substrate is stdlib-only and needs nothing. Every *neural* family needs a stack built first. `torch` 2.14.1+cpu and `transformers` 5.18.0 do have cp314 wheels and were installed into an out-of-tree venv at `/tmp/opencode/lmr-venv`. |
| Fixed generator | present, 986,048,768 B, sha256 matches the contract; `llama-server` at the pinned build `050dde5` | MEASURED working: server load 1,510 ms; warm generate **3,911 ms** for 35 completion tokens at `threads=1`; prompt eval 669 ms / 156 tokens. A 146-item two-arm paired probe is ≈ 25–60 min. Feasible. |
| CPU / RAM | 12 threads, 62 GB total, **28 GB available** | No CUDA. Neural inference and any fine-tuning are CPU-only. |
| Accelerators | Intel UHD 630 + 2× AMD FirePro (no CUDA) | No GPU hiding inside any latency number — which happens to satisfy the "is GPU batching hiding mobile-unfriendly computation" review question, but also removes any escape from CPU cost. |
| Disk | `/home` **30 GB free (94% used)** | The 3.1 GB judge and the ettin checkpoints (17M/32M/68M ≈ 67/128/273 MB) fit. Bulk artefact accumulation does not. |

## 5. Repository gaps this run must close

| Gap | Status |
|---|---|
| `shared-backbone + multiple-heads` experiment | **DOES NOT EXIST.** `experiments/` holds `adapter-peft`, `baselines`, `comparability`, `ettin-cascade`, `hybrid-fusion`, `kalm-cascade`. The multi-head family is the simplest alternative to multiple checkpoints *and* to LoRA-swapped checkpoints, so it is created in this run. |
| Shared Round 1 implementation substrate | absent. Every retrievable primitive (corpus traversal, `D(p)`, BM25, candidate ids, packet construction, exact-token budget, latency/RSS/storage, stage-survival, tier runner) is specified in `experiments/baselines/HYPOTHESIS.md` §2–§3 but implemented nowhere. |
| Baselines | specified, not implemented. |
| Synthetic training set | does not exist. |
| Regime A/B training manifests | do not exist. |

## 6. Plan admitted at orientation

The full twelve-phase programme in the run brief — five architecture families
implemented, trained on a common synthetic corpus, tuned on DEV, independently
reviewed, frozen, run once on SHADOW_DEV, then analysed by six independent
analyst roles — is larger than one orchestration run on a 12-thread CPU-only
host with 30 GB of disk, and the binding constraint is not the agent budget, it
is CPU time and the absence of a GPU.

The honest sequencing is therefore to spend this run on the parts that are
decisive and cheap, and to stop at the first hard gate rather than manufacture
the rest:

1. the shared substrate and the baselines (no gate depends on them being absent);
2. **the generator-floor probe**, which is the repository's own hard gate and
   which costs ~1 hour;
3. whatever the gate permits, in the order the gate permits it.

The floor probe is run first among the experiments precisely because the frozen
comparability contract makes it a *stop* condition, and because a tournament run
against a generator that cannot express evidence quality produces numbers that
mean nothing. If it reports FLOORED, phases 6–14 are void by the repository's own
rule and the correct output is the floor finding.

Nothing below is reported as a result unless it was measured.
