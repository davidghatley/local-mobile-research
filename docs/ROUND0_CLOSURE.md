# Round 0 Closure — what actually happened

**Scope:** the full account of how `local-mobile-research` reached a frozen Round 0
substrate, what was wrong with it along the way, what the freeze does and does not
prove, and what Round 1 has decided so far.

**Date:** 2026-10-03. **Frozen at** tag `round0-freeze-r1`, commit
`a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`.

**Controlling specification:** `master_orchestration_prompt.txt`.

---

## 0. The short version

Round 0 built the shared experimental substrate for an offline System-1 retrieval
tournament: a 297-article corpus, a 206-item public QA partition, a 940-article
scale tier, a fixed generator with a pinned prompt, a scoring protocol, and a
10-stage verifier whose job is to say honestly whether the whole thing can be
frozen.

It nearly froze several times. **Eight independent reviews ran. Seven returned
`REPAIR REQUIRED`. The eighth returned `PASS`.** Every one of those seven verdicts
was correct, and every one found a defect that the team that wrote the code had
not seen — several of them defects that made the verifier *report success while
checking nothing*.

The freeze is now real: tag, out-of-repo durable manifest, out-of-repo tag-binding
record, digests all consistent, CI green, 518 tests, and an 11-probe adversarial
harness that a reviewer can re-run.

Round 1 has since completed **mise-en-place only**: six readiness reports, no
implementation. Two of them concluded their own family may not be buildable on a
phone at all. And the corpus was shown to be able to distinguish architectures
that differ by only about 10 percentage points — which is a statement about the
corpus, not about any architecture.

---

## 1. How the review process worked

Each review was a **fresh independent reviewer on a verified-free endpoint**, with
nested spawning disabled and paid fallback prohibited. Reviewers implemented none
of the code they reviewed, re-executed every reproducible claim rather than
trusting the orchestrator's report of it, and were explicitly barred from reading
private test content.

Each reviewer was also given a **different attack surface from its predecessors**,
because a reviewer given the same brief finds the same things:

| Review | Attack surface | Endpoint (self-recorded) |
| --- | --- | --- |
| v1 | data quality, end-to-end re-execution | `openrouter/qwen/qwen3.8-27b:free` |
| v2 | adversarial sweep of **all** approved QA items | `opencode/nemotron-3-ultra-free` |
| v3 | vacuity — which stages compare nothing | `opencode/space-bunny-free` |
| v4 | per-stage vacuity + consistent corruption | `opencode/muse-spark-1.3-contributor-free` |
| v5 | pins and control flow; is mutation coverage proof? | `opencode/space-bunny-free` |
| v6 | control flow and the trust chain of the durable record | `openrouter/qwen/qwen3.8-27b:free` |
| v7 | **the scientific contract and Round 1 comparability** | `opencode/nemotron-3-ultra-free` |
| v8 | confirm v7's findings closed; decide the freeze | `opencode/nemotron-3-ultra-free` |

Endpoint substitutions were recorded rather than hidden — v1 records that
`gemma-4-31b-it:free` failed at pickup; v3 records two prior failures
(`qwen3.8-27b:free` provider error, `nemotron-3.5-lightning-free` produced garbled
output and wrote nothing).

---

## 2. What each review actually found

### v1 — `REPAIR REQUIRED`, 7 findings

Re-ran everything and confirmed the verifier machinery itself was sound (10/10,
exit 0). Then found the *claim* "the repair run is complete" was false:

1. Two shadow-dev comparison items pre-stated the answer years, and had been
   approved on flawed reasoning.
2. A functional regression: `data_tools/derive.py` rejected **all** `shadow_dev`
   groups, untested.
3. **Stage 10 printed `MATCHES` when the manifest recorded no hash** — a vacuous
   pass on the private-custody check.
4. `eval/scale_adjudication.py` was documented but did not exist.
5. Verifier header and docs disagreed about which stages ran and what the exit
   code was.
6. Ledgers ended several commits earlier than the work they described.
7. `STATUS.md` was uncommitted.

### v2 — `REPAIR REQUIRED`, closed all 7, found one more

Confirmed all seven closed, then swept **all 207 approved items** for the same
defect class and found `qa-dev-24` — in the **dev** split, currently approved,
missed by v1's targeted check. A freeze on that state would have institutionalised
a known protocol-violating item in the evaluation set.

### v3 — `REPAIR REQUIRED`, findings R1–R10

Attacked vacuity directly. The blocking ones:

- **R1** — the freeze manifest was **git-ignored and untracked**. The freeze
  record was not in the repository at all.
- **R2** — stage 6 was an empty pass.
- **R4** — the sweep census said 197; the real number was different.
- **R10** — stage 9 passed with the pins absent.

### v4 — `REPAIR REQUIRED`, the census defect

The partition census was **derived from the data it was supposed to check**, so it
agreed with itself by construction. A truncation that removed QA items *and*
updated the census consistently passed. This is the finding that produced the
external trust root.

### v5 — `REPAIR REQUIRED`, the co-edit defeat

v4's fix was defeated by co-editing the data and the census together. The pin had
to move **outside the repository**, where a worker cannot co-edit it. The same
review also made the standing methodological point:

> Mutation coverage is not proof of correctness.

### v6 — `REPAIR REQUIRED`, 9 findings on control flow and the trust chain

The most valuable round, because it confirmed the Blocker-1 control-flow design
sound across ten probes and then found nine things around it:

| # | Finding |
| --- | --- |
| N-1 | a vacuous pin check — the comparison could be skipped and still pass |
| N-2 | a **dirty working tree could be frozen**, so recorded code hashes would not match the recorded commit |
| N-3 | a fake `FROZEN AT` anchor |
| N-4 | doc/code threshold mismatch (0.85 documented vs 0.80 implemented) |
| N-5 | tag↔record mutual ambiguity; overstated atomicity claim |
| N-6 | a symlink decoy passed the Regime-B exclusion check |
| N-7 | the leakage gate's behaviour made it an **adaptive membership oracle** |
| N-8 | `abspath` used where `realpath` was required |
| N-9 | temp-file wording |

### v7 — `REPAIR REQUIRED`, four findings against the *science*

The first review to ignore the code almost entirely and ask what a green verifier
does **not** prove about the experiment it authorises.

- **N-1** — `docs/scoring-protocol.md` claimed `FROZEN AT commit 88aa177`, a
  commit at which the file, `eval/answer_scoring.py`, and their tests **did not
  exist**. A preregistration anchored to a fiction records nothing.
- **N-2** — `docs/round0-review-criteria.md` §9.3 specified a `verify_freeze.py`
  script and a manifest schema (`artifact_path`, `size_bytes`, `timestamp`,
  `git_commit`) that never existed.
- **N-3** — `corpus/regime_b_excluded_articles.json`, the public 21-document
  exclusion superset that teams are *told* to exclude, was **not byte-pinned**
  anywhere.
- **N-4** — the answer judge `google/flan-t5-large` was a **floating tag**. A
  model id without a digest is not preregistration.

Plus eight caveats that had to be recorded rather than resolved.

### v8 — `PASS`

Verified all four of v7's findings closed with its own probes — the anchor is
load-bearing (fails when moved to a non-existent commit or back to the fictional
`88aa177`), the `verify_freeze.py` fiction is gone repo-wide, the exclusion
superset is byte-pinned in both `build_manifest.json` and the freeze inventory
(tampering fails stage 8), and the judge is unambiguously recorded as unpinned.
Remaining repair list: **NONE**.

---

## 3. The three load-bearing fixes

### The durable record (Blocker 1)

Originally the freeze produced a *verdict* and nothing else. Now it produces a
**durable record**: stage 8 writes a candidate manifest to scratch, and the shell
promotes it atomically into the private directory **only** when the mode is
`full`, no `--only` was passed, `N_FAIL == 0`, `N_SKIP == 0`, and all stages ran.
The record binds the commit SHA, the dirty flag, digests of the corpus,
questions, split map, census, seal, generator and verifier, code hashes, the
artifact inventory, thresholds, regime groups, per-stage results, and a timestamp.

Proven adversarially: `--only 8` leaves no record; a broken stage 9 or 10 leaves
no record; a census co-edit is caught by the out-of-repo trust root; and **a
failing run leaves a pre-existing valid record byte-identical**.

### Hermetic CI (Blocker 2)

CI had been red at the reviewed commit. The custody test was rewritten hermetically
(synthetic fixture, environment passed to the subprocess only), a workflow banner
regex was fixed — and **proved load-bearing by injecting a banner** — and three
*additional* non-hermetic test files the review had not named were found and had
their hardcoded `/home/davidhatley/...` fallbacks removed.

### The leakage gate (Blocker 3)

First written as a hash-only comparison, then found to be an adaptive membership
oracle, then rebuilt as three preregistered layers with thresholds derived from a
**measured separation table** rather than guessed (0.85 → 0.80, char ratio), a
frozen three-field verdict, and **one-shot enforcement** through a session ledger.

---

## 4. What the freeze does and does not prove

`./scripts/verify_round0` → **10/10 stages PASS, exit 0, on a clean tree.**
`./docs/probes_round0.sh` → **11 probes, 18/18 checks.** CI **GREEN**.

**It proves:** corpus and question-partition hashes, QA provenance from the staging
drafts, the generator pin, artifact pins, the model-facing query boundary, the
leakage-control artifacts, private-eval custody as opaque bytes, and the
consistency of the tag / manifest / binding triple.

**It does not prove, and says so on every run:** that any QA item is
*semantically* correct. 206 approved items carry reviewer-asserted labels from LLM
workers. No unit test can establish answerability, atom minimality, multi-hop
genuineness, or label correctness.

> **A freeze is not a claim of scientific validity.** It records that the substrate
> is structurally sound, the custody boundary holds, and the accepted risks are
> owned and dated.

The durable manifest and tag binding live **outside** the repository. They are a
**procedural custodian attestation, not a signature** — a custodian controlling the
private directory could forge both. It proves discipline, not authorship.

---

## 5. Accepted risks, dated and owned

Recorded in [`docs/STATUS.md`](STATUS.md). Not resolved, not hidden, and not
contradicted by the PASS printed above them.

| # | Risk | Consequence |
| --- | --- | --- |
| 1 | Semantic QA rests on LLM reviewers | Round 1 measures retrieval against a benchmark whose labels are judgments, not facts |
| 2 | **Private test power — now quantified, and low** | Only ~22 pp separable on dev, ~12 pp on dev+shadow_dev, ~10 pp on all 206 items, ~14 pp on the private set. Sub-threshold gaps are nulls. |
| 3 | The fixed 1.5B Q4 generator may **floor** | If it floors, the retrieval tournament measures nothing above the floor |
| 4 | The answer judge is not digest-pinned | Judge metrics **ABSENT** until resolved; deterministic primary metrics unaffected |
| 5 | The leakage gate is procedural, not a kernel boundary | It stops mistakes, not a determined adversary with filesystem access |
| 6 | Scale adjudication is only lightly wired | Scale-tier precision figures must be read with their `unjudged_top_k` |
| 7 | Tag + record pair is an attestation, not a signature | Proves procedural discipline, not authorship |

---

## 6. Round 1 — mise-en-place (reports only)

Six teams, disjoint file ownership, all on verified-free endpoints. **No
implementation, no synthetic data cleared, no dev run.**

| Team | Headline finding |
| --- | --- |
| **Baselines** | BM25 pinned to implementation level (`k1=1.2`, `b=0.75`, no stemming, no stopwords, paragraph-node index, top-K=500, ties by `(score, node_id)`). Argues a genuinely static semantic stage adds **0–2 points** — inside noise — and says so *before* a neural team is finished. |
| **Ettin cascade** | 17M/32M/68M recall-first cascade. Biggest risk is compound evidence loss: ~0.97 per-stage retention over four stages ≈ 0.885. |
| **KaLM cascade** | **Runtime does not survive export.** Model card is PyTorch-only; no R2 GGUF exists. Also: "progressive decompression" is a misnomer — mean-pooling is lossy, so fine states cannot be derived from cached coarse states. |
| **Adapter / PEFT** | Adapters **must be merged** to be exportable; llama.cpp LoRA is llama-decoder-only and BERT/ModernBERT retrievers have no llama.cpp path at all. The advantage survives only as *small-model runtime at large-model quality*, never as shipping the adapter. |
| **Hybrid fusion** | Headline is RRF (unsupervised, no tuning surface). Carries an explicit test that must **fail** if fusion silently degenerates to a single channel. |
| **Comparability** | Shared Stage 0 recommended; token-budget enforcement verified real by behavioural test; kill-condition recording protocol preregistered. |

### The finding that outranks all of them

**This corpus can only separate architectures differing by ~10 percentage points.**

The comparability lead's original figures (6 items on dev, 9 on shadow_dev, 14 on
all 206) **did not survive its own arithmetic**. It had computed two intervals
overlapping across almost their whole width and then, three lines later, called
them non-overlapping. Corrected by exhaustive scan and independently cross-checked
by a two-proportion z-test at α=0.05 / 80% power, which agrees within one item
everywhere:

| split | n | corrected MMD | originally claimed |
| --- | --- | --- | --- |
| dev | 59 | **13 items = 22.0 pp** | 6 items = 10.2% |
| shadow_dev | 87 | **15 items = 17.2 pp** | 9 items = 10.3% |
| dev + shadow_dev | 146 | **18 items = 12.3 pp** | 14 items = 9.6% |
| private (sealed) | 116 | **16 items = 13.8 pp** | — |
| all worker-visible | 206 | **21 items = 10.2 pp** | 14 items = 6.8% |

That is underpowered for **most** architecture pairs, not merely close ones.

The same review's **generator-floor rule was wrong in a way that could have
inverted the tournament's verdict**: it declared a floor if the oracle-vs-baseline
delta was ≤ 5%, which is *below what the probe can measure* — so it would have
reported "floored" when the truth was "underpowered", and stopped a tournament
that was fine. The comparison is **paired** (same items, different packet) so it
needs McNemar, not an unpaired Wilson, and the rule is now three-way: interval
excludes 0 → no floor; includes 0 with upper bound below the MMD → floor; includes
0 with upper bound above it → **INCONCLUSIVE**, its own outcome.

---

## 7. Corrections the orchestrator made to its own and the teams' work

Recorded because they are part of the history, not because they were tidy.

- **The comparability arithmetic above** — roughly 2× wrong, caught by recomputation.
- **A miss of my own:** I corrected the comparability `CONTRACT.md` and left its
  sibling `PLAN.md` carrying the superseded floor rule. Found only when checking
  whether lead E had propagated the fix.
- **Stale figures had spread to four more files** across three teams — two hybrid
  kill conditions gating on `~14/146 (9.6%)`, adapter-peft's plan with the old
  floor rule, and four teams still pointing at "no power calculation exists",
  which stopped being true the moment I computed one. All reconciled; a **threshold
  register** now fixes one authoritative number in one place.
- **A false blocker in a frozen document.** Lead D reported the leakage gate as
  unable to issue `PASS`, stalling its whole training plan. It was reading
  `R1_TRAINING_CONTRACT.md` §5, frozen when the gate genuinely could not issue
  PASS. The v6 repairs fixed the gate; the contract was not updated, because
  updating it would have meant editing a preregistered artifact. So the contract
  was left **byte-identical** (sha256 confirmed against the tag) and a dated
  **post-freeze erratum** supersedes the specific stale sentences.
- **Two harness bugs** in the probe suite that made probes measure their own
  scaffolding: symlinking a git-ignored *directory* (a `.gitignore` rule with a
  trailing slash does not match a symlink, so the tree went dirty and the
  dirty-tree rule correctly refused to freeze), and probe copies being synthetic
  single-commit repos so every history-dependent check failed for the wrong reason.
- **Endpoint failures**, recorded rather than papered over: one provider error and
  two upstream idle timeouts during Round 1; lead E's first run was cancelled after
  writing a complete 570-line hypothesis report and no plan. The report was
  verified and kept, not rewritten.

---

## 8. What has NOT happened

Stated plainly, because a freeze plus six reports can read as more progress than
it is.

- **No architecture is implemented.** Not one.
- **No synthetic training data has been cleared.**
- **No dev or shadow-dev run has happened.**
- **The generator floor has not been probed** — and per the corrected contract it
  must be, *before* the tournament, because a floored generator makes the whole
  retrieval tournament uninformative.
- **No private evaluation has been run, and none may be until the tournament lock.**
- **The answer judge is still unpinned** — a BLOCKING-FOR-ROUND-1 precondition.
- **Every measurement in this repository is a desktop measurement.**

---

## 9. How to verify any of this yourself

```bash
export LMR_PRIVATE_EVAL_DIR=/path/to/local-mobile-research-private-eval

git rev-parse round0-freeze-r1^{commit}       # the frozen commit
./scripts/verify_round0                        # 10/10, exit 0, clean tree
./docs/probes_round0.sh                        # 11 probes, 18 checks
python3 -m unittest discover -s tests          # 518
```

The out-of-repo tag-binding record carries the tag, the commit, the manifest
sha256, the census sha256 and the private seal sha256, and asserts
`commit == tag target`.

Then read the reviews. They are the most useful documents in the repository,
because each one is a record of a competent reviewer finding something the team
had missed — including, twice, a check that reported success while verifying
nothing at all.

---

## 10. The lesson

An internal consistency check is **necessary and never sufficient**. The same
failure shape appeared at three scales — a single item, a whole partition, and the
entire freeze:

- a census that agreed with itself because it was derived from the data it checked;
- a truncation that passed three consecutive stages;
- a fix defeated by co-editing the data and its census together;
- a stage that compared nothing and reported `PASS`;
- a gate that could never return `PASS`, then — once repaired — turned out to be
  an adaptive membership oracle;
- a preregistration anchored to a commit where the policy did not exist;
- a scientific contract whose stated minimum meaningful difference was wrong by 2×
  and refuted by its own worked example.

Every fix went through an internal consistency check too. One of them had
silently disabled the count checks it was supposed to enable, via an `elif`.

**None of these were found by the team that wrote the code.** All were found by a
fresh reviewer with a different brief. That is the finding.
