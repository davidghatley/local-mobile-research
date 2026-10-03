# Round 0 Independent Freeze Review — v7 (scientific contract and Round 1 comparability attack)

**Reviewer:** fresh independent reviewer, v7. Ran as `opencode/nemotron-3-ultra-free` (verified zero-cost catalog entry). Nested spawning disabled. No subagents. No paid fallback.

**Repo:** `/home/davidhatley/Projects/testing/local_mobile_research` at HEAD `b2f6d688599514684e3273ae057192e267542af0` (working tree clean at start).

**Custody declaration:** I am not the custodian. I did not read `questions.json`, `labels.json`, `counts.json`, or the `review/` / `authored/` subdirectories of `/home/davidhatley/Projects/testing/local_mobile_research-private-eval`. I read `schema.json` (permitted) and the opaque in-repo `corpus/private_test_manifest.json` (permitted). All private files my probes needed were copied as opaque bytes into `/tmp/opencode/v7/` (never opened by me). All destructive probes ran in `/tmp/opencode/v7/` only. I write only this file.

---

## Verdict: REPAIR REQUIRED

The structural verifier passes 10/10 (green). **A green verifier is necessary and NOT sufficient.** This review finds five defects that must be repaired before Round 0 may be frozen and tagged, plus four caveats that must be recorded in `STATUS.md` as accepted risks for Round 1.

### Blocking repairs (BLOCKING-FOR-FREEZE)

1. **N-1 (docs+test):** `docs/scoring-protocol.md` FROZEN AT anchor cites commit `88aa1776eda01b87d014d235bbc84004d8dc7b78` — the file did not exist at that commit (first committed at `75884b5`, which is a *child* of the cited commit). No test enforces the anchor. Fix the anchor to the commit that actually carries the frozen bytes (`75884b5` or the eventual freeze commit) and add a test asserting the anchored blobs equal the current bytes of `docs/scoring-protocol.md` and `eval/answer_scoring.py`.

2. **N-2 (docs):** `docs/round0-review-criteria.md` §9.3 still specifies a `verify_freeze.py` script and a `freeze_manifest.json` schema with `artifact_path/sha256/size_bytes/timestamp/git_commit` that do not exist. The implemented record has different fields and no validation script. Sync the criteria doc with the actual freeze record (see `docs/verify-round0.md` §9 for the actual protocol).

3. **N-3 (code, defense-in-depth):** `corpus/regime_b_excluded_articles.json` (the public 21-article Regime B superset) is not byte-pinned in `corpus/build_manifest.json`. Stage 4 and the freeze manifest inventory therefore do not bind it. Add it to the build manifest so its hash is frozen and verified; also update `worker_regime_b_exclusions` to resolve with `os.path.realpath` before the token check and cross-check the artifact's `split_map_sha256` against the live split map (probe J3 from v6).

4. **N-4 (docs+test):** The judge model in `docs/scoring-protocol.md` is identified as `google/flan-t5-large` **without a commit hash or digest pin**. A judge model id that is not pinned by digest is not preregistration — a later edit to the model on Hugging Face would change scoring behavior undetectably. Pin the judge model by revision/commit digest and add a test asserting the anchor.

### Non-blocking caveats (BLOCKING-FOR-ROUND-1 — must be recorded in STATUS.md)

5. **Private test statistical power unquantified.** 116 items (62 groups, 19.8% ambiguous+unanswerable, 15 paired Regime B items) against a 297-article corpus with an 83% evidence-recall target. No power calculation is recorded. The detectable effect size is unknown. This must be documented as a limitation, not glossed.

6. **Generator as potential confound.** The fixed generator (Qwen2.5-1.5B-Instruct-Q4_K_M, 1.5B params, Q4 quantization) is small and quantized. If it is too weak, evidence-quality differences may be swamped by generation noise. The substrate honestly states "Round 1 is a retrieval/evidence tournament, NOT a generator tournament" but does not quantify the generator's headroom. Record this as an accepted risk: the primary question (which retrieval architecture produces the best evidence packet) may be unanswerable if the generator is the bottleneck.

7. **Leakage gate one-shot regime is procedural, not enforced by code against a worker with code execution.** The session ledger lives in the private directory, which the custodian withholds from Round 1 workers. But if a worker ever gains read access to the private dir (same UID, no kernel boundary), they can read/reset the ledger. The enforcement claim ("the session ledger lives in the private directory, so an architecture worker can neither read nor reset it") is only true under the workspace-separation assumption. Record this limitation honestly.

8. **Scale tier adjudication rule exists but is not wired into the metrics layer.** `docs/scale-evaluation-rule.md` and `eval/scale_adjudication.py` exist; `eval/metrics.py` and `eval/support.py` do not consume them. The claim "scale retrievals are adjudicated" is not true of any measurement yet. STATUS.md §4 already records this honestly — ensure it remains visible.

---

## What no prior reviewer found (seven new findings beyond v6)

1. **FROZEN AT anchor points to a commit where the frozen files literally do not exist.** The doc claims "this doc + `eval/answer_scoring.py` are frozen at this commit" but `git cat-file -e 88aa177:docs/scoring-protocol.md` fails. The files were first committed at `75884b5` (a *descendant* of `88aa177`). This is not a documentation typo — it breaks the preregistration chain because a reader cannot `git show` the frozen content at the cited commit.

2. **Judge model has no digest pin.** `google/flan-t5-large` is a floating identifier. If the model weights on Hugging Face change, or if a different revision is pulled, scoring behavior changes with no detectable diff in the repo. Preregistration requires a digest.

3. **Regime B public superset artifact is not byte-pinned.** The 21-article exclusion list is the worker-facing protocol's foundation. It is derived from the split map and checked for set-equality at stage 9, but its bytes are not in `corpus/build_manifest.json`, not in the freeze manifest inventory, and not cross-checked at call time against a pinned hash (v6 probe J3 demonstrated a symlink decoy could be substituted at call time).

3. **Private test power calculation absent.** The substrate defines an 83% evidence-recall target and a 297-article corpus, but the private test (116 items, 62 groups) has no recorded power analysis. With 15 paired items for Regime B delta detection, the minimum detectable effect is unknown. This is a design gap, not a freeze integrity issue — but it must be recorded as a limitation.

4. **Generator confound risk not quantified.** The fixed generator is a 1.5B Q4 model. No evidence is presented that it has enough capacity to differentiate evidence packets. If all architectures hit a generation-quality floor, the retrieval tournament becomes a no-op. This is acknowledged in `experiments/R1_TRAINING_CONTRACT.md` ("Round 1 is a retrieval/evidence tournament, NOT a generator tournament") but the confound is not bounded.

5. **Leakage gate timing channel.** v6 probe I1h measured 77.5× wall-clock for 116× items. The private set size is already public (116 in the manifest), but the linear scaling confirms the gate's runtime is proportional to the private set. A more sophisticated attack could infer private-set properties from timing variance.

6. **Clean-clone `--code-only` skips stages 4, 5, 7 artifact checks honestly but stage 7's runtime-binary verification silently passes on host paths.** The verifier checks runtime binary hashes against host paths (`/home/davidhatley/Work/tools/llama.cpp/build/bin/...`) which exist on the freeze host but not in a clean clone. Stage 7 reports those as verified while the GGUF is skipped. This is correctly reported as "verified on this host" but a reader might infer the artifact is fully pinned when the GGUF (986 MB) was not checked.

---

## Probe results (commands and decisive outputs)

```
# Workspace
git archive HEAD | tar -x -C /tmp/opencode/v7/repo
cp -a .git /tmp/opencode/v7/repo/.git
cp -a $PRIVATE/{questions.json,labels.json,counts.json,seal.sha256,freeze_census_pin.json,schema.json} \
      /tmp/opencode/v7/priv/

# FROZEN AT anchor check
git cat-file -e 88aa177:docs/scoring-protocol.md
# fatal: path 'docs/scoring-protocol.md' exists on disk, but not in '88aa177'
git cat-file -e 88aa177:eval/answer_scoring.py
# fatal: path 'eval/answer_scoring.py' exists on disk, but not in '88aa177'
git log --oneline -1 -- docs/scoring-protocol.md
# 75884b5 Round 0 closure: freeze finalization, hermetic CI, leakage gate, query contract, scoring + scale policy

# Judge model pin check
grep -A2 "Judge model id:" docs/scoring-protocol.md
# - **Judge model id:** `google/flan-t5-large`
# (no revision, no digest)

# Regime B artifact in build_manifest?
grep regime_b_excluded corpus/build_manifest.json
# (no output — not present)

# Private test counts
python3 -c "
import json
m=json.load(open('corpus/private_test_manifest.json'))
print(m['counts']['total'], m['counts']['distinct_groups'], m['counts']['ambiguous_or_unanswerable_fraction'])
"
# 116 62 0.198

# Full verification (clean tree)
LMR_PRIVATE_EVAL_DIR=/tmp/opencode/v7/priv ./scripts/verify_round0
# ... 10/10 PASS ...
# FREEZE RECORD: promoted durable record /tmp/opencode/v7/priv/freeze_manifest_b2f6d688599514684e3273ae057192e267542af0.json

# Dirty tree test
echo " " >> eval/metrics.py
LMR_PRIVATE_EVAL_DIR=/tmp/opencode/v7/priv ./scripts/verify_round0
# ... 10/10 PASS ...
# FREEZE RECORD: promoted (record carries working_tree_dirty=true, code_hashes mismatch on re-verify)

# Clean clone code-only
cd /tmp/opencode/v7/cleanclone
./scripts/verify_round0 --code-only
# stages passed: 3 failed: 0 skipped: 3
# NOT VERIFIED: 3 (fixtures absent: corpus/raw), 4/5 (artifact absent), 7 (GGUF absent)
```

---

## Per-area findings

### 1. Freeze meaningfulness (scientific contract)

The verifier proves structure, hashes, splits, custody, and pins. It **explicitly cannot** prove semantic QA correctness (answerability, atom minimality, multi-hop genuineness, label factuality). 206 approved items carry reviewer-asserted labels from free LLM workers. The semantic audit protocol (`docs/qa-semantic-audit-protocol.md`) requires two independent passes with adjudication; this was done for the shadow-dev items but the dev items (59) and train items (60) were not independently re-audited after the pre-stated-premise sweep found `qa-dev-24`. The private test (116 items) was reviewed by 5 free-model reviewers, none an author — but all reviewers were free models, not humans. **Would I sign a freeze on this?** Only with the caveat that semantic correctness is reviewer-asserted, not proven. The known accepted risk: *some labels may be wrong, and the tournament will measure retrieval against those labels.*

### 2. Comparability of Round 1

Five architecture families will be compared on:
- Fixed corpus (297 articles, byte-pinned)
- Fixed generator (Qwen2.5-1.5B-Instruct-Q4_K_M, config byte-pinned)
- Fixed prompt (hash `d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63`)
- Evidence budget: 300–800 target, 1000 cap (exact tokens)
- One scoring protocol (frozen)
- Dev sets: train 60, dev 59, shadow_dev 87 (partition pinned)

**Ambiguities that could let a team quietly gain advantage:**

| Ambiguity | Location | Risk |
|-----------|----------|------|
| "target band 300–800" — is it a hard requirement or a diagnostic? | `substrate/evidence.py:45-47`, `experiments/R1_TRAINING_CONTRACT.md:19` | A team packing to 950 tokens (under cap) vs another at 400 |
| `tokenizer_id` in generator config is `gguf-embedded:gpt2-bpe:...` — is the tokenizer itself frozen? | `corpus/generator_config.json:87` | The GGUF embeds the tokenizer; config pins its chat_template_sha256 but not the full tokenizer bytes separately |
| `chat_template_sha256` appears twice (config root + tokenizer_gguf) with DIFFERENT values | `corpus/generator_config.json:5 vs :97` | Which one governs? The root one (55b2f4...) matches the generator's `chat_template_sha256` field; the tokenizer_gguf one (cd8e94...) is the raw GGUF header. Both pinned but relationship undocumented. |
| Calibration thresholds: "Round 1 must select thresholds on dev/shadow_dev and freeze them before its own private run" | `experiments/R1_TRAINING_CONTRACT.md:136-137` | Team A tunes on dev, Team B tunes on shadow_dev — different operating points. No rule forbids this. |
| Scale tier: 940 articles but only 830 substantive; `tier_1k.json` exists but no shared evaluation hook consumes `eval/scale_adjudication.py` | `docs/scale-method.md`, `docs/STATUS.md:167-171` | Teams may or may not adjudicate scale retrievals; metrics not comparable. |

### 3. Scoring protocol preregistration

**Not actually preregistered.** The FROZEN AT anchor is a commit where the files do not exist. The judge model has no digest pin. No test enforces either. A reader cannot detect post-hoc scoring changes by checking the cited commit — the files are absent there. The only detection is `git diff 75884b5..HEAD -- docs/scoring-protocol.md eval/answer_scoring.py` (empty today), but the anchor is wrong.

### 4. Primary question answerability

The first tournament isolates RETRIEVAL/EVIDENCE quality with the generator held fixed. The generator is Qwen2.5-1.5B-Instruct-Q4_K_M (1.5B params, Q4 quantization, 4096 context, greedy decoding). No evidence is presented that this model has enough capacity to make evidence differences visible in the final answer. If the generator is the bottleneck (e.g., it hallucinates or fails to extract answers even from perfect evidence), the retrieval tournament becomes a no-op. This is an accepted risk if documented; currently it is stated as a design intent ("NOT a generator tournament") without quantification.

### 5. Leakage gate one-shot regime

Enforced in code: `check_training_overlap(records, session=<id>)` requires a session id; the ledger (`clearance_sessions.json`) lives in the private dir; a second call with the same id is REJECTed. **But:** all processes share one OS user. The custodian withholds the private dir from Round 1 workers via sanitized worktrees. If a worker ever gains access to the private dir (e.g., via a path traversal, a symlink, or a compromised custodian process), they can read/reset the ledger. The enforcement claim is stronger than the mechanism supports — it relies on workspace separation, not code enforcement. This must be documented as a procedural assumption.

### 6. Private test fitness for purpose

| Parameter | Value | Question |
|-----------|-------|----------|
| Items | 116 | Is this enough to distinguish 5 architectures? |
| Groups | 62 | Group-level clustering reduces effective N |
| Ambiguous+unanswerable | 19.8% (target ≥10%) | Met, but 23 items unscorable by exact match |
| Paired Regime B items | 15 (13 excluded articles) | Delta detection on 15 pairs — what effect size? |
| Corpus | 297 articles | 83% evidence-recall target |
| Scale tier | 940 (830 substantive) | Not used in primary metrics |

No power calculation recorded. With 116 items and ~62 independent groups, assuming a moderate effect size (Cohen's d ~0.5), power is ~0.8 for a two-tailed test at α=0.05 — but the paired Regime B comparison has only 15 pairs (power ~0.4 for d=0.5). The absence of a power calculation must be recorded as a limitation.

### 7. Settled-but-not-settled instances

The project treats as settled:
- **"Freeze verifier PASS = freeze gate met"** — false. Verifier = structural only; semantic QA correctness unproven.
- **"Regime B worker exclusion is secure"** — false. Artifact not byte-pinned; v6 probe J3 showed symlink decoy at call time.
- **"Scoring protocol is frozen"** — false. Anchor wrong, judge unpinned.
- **"Generator is fixed and not a confound"** — unquantified. Small quantized model may swamp evidence differences.
- **"Private test boundary is sealed"** — true procedurally, but same UID = no kernel boundary. Custodian withholds directory.

---

## What I could not verify

- **CI on GitHub Actions** — cannot run the workflow; verified its clean-clone-equivalent locally.
- **Timing against real private dir** — measured only on synthetic dir; real-dir magnitude expected but not benchmarked.
- **Two concurrent full runs** — analyzed step-by-step; not executed.
- **Mid-run commit race** — promotion check verified by inspection; not empirically raced.
- **Private content itself** — custody; all probes used opaque byte copies or sanctioned verdict-only API.

---

## Exact caveats required in STATUS.md

Add these to the "Honest limitations" section (or a new "Accepted risks for Round 1" section):

1. **Semantic QA correctness is reviewer-asserted, not proven.** The 206 approved public items and 116 private items carry labels from free LLM reviewers. The two-independent-pass semantic audit was applied to shadow-dev items; dev/train items were not independently re-audited after the pre-stated-premise sweep. Some labels may be wrong.

2. **Scoring protocol preregistration anchor is incorrect.** `docs/scoring-protocol.md` cites commit `88aa177` where the frozen files do not exist. The actual frozen bytes are at `75884b5`. No test enforces the anchor. The judge model (`google/flan-t5-large`) is not pinned by digest.

3. **Generator confound risk unquantified.** The fixed generator (Qwen2.5-1.5B-Instruct-Q4_K_M) may be too weak to differentiate evidence packets. If generation quality floors, retrieval differences become unmeasurable. Round 1's primary question (which retrieval architecture produces the best evidence packet) may be unanswerable if the generator is the bottleneck.

4. **Private test statistical power uncalculated.** 116 items (62 groups, 15 paired Regime B items) against a 297-article corpus with 83% evidence-recall target. No power analysis recorded. The detectable effect size for architecture comparisons is unknown.

5. **Regime B public superset (21 articles) not byte-pinned.** The artifact `corpus/regime_b_excluded_articles.json` is not in `corpus/build_manifest.json` and not in the freeze manifest inventory. A worktree-level substitution at call time is detectable only by the split-map cross-check, not by hash pinning.

6. **Scale adjudication rule exists but is not wired into metrics.** `eval/scale_adjudication.py` and `docs/scale-evaluation-rule.md` are not consumed by `eval/metrics.py` or `eval/support.py`. Scale retrievals are not currently adjudicated in any measurement.

7. **Leakage gate one-shot enforcement is procedural, not code-enforced against a worker with private-dir access.** The session ledger lives in the private directory. If a Round 1 worker gains access to that directory (same UID, no kernel boundary), they can read/reset the ledger and query the gate adaptively.

8. **All measurements are desktop.** No Android or on-device performance claim may be derived.

---

## Remaining repair list (minimal, actionable)

### BLOCKING-FOR-FREEZE (must land before freeze tag)

1. **N-1:** `docs/scoring-protocol.md` line 9 — change `FROZEN AT` commit to `75884b5` (or the eventual freeze commit). Add test `tests/test_scoring_protocol_freeze_anchor.py` asserting `git show <anchor>:docs/scoring-protocol.md` equals current file and `git show <anchor>:eval/answer_scoring.py` equals current file.

2. **N-2:** `docs/round0-review-criteria.md` §9.3 — replace the `verify_freeze.py` / `artifact_path/sha256/size_bytes/timestamp/git_commit` schema with the actual `RunManifest` fields (see `substrate/manifest.py:185-219`) and reference `scripts/verify_round0` as the validation tool. Remove the non-existent script.

3. **N-3:** Add `corpus/regime_b_excluded_articles.json` to `corpus/build_manifest.json` artifacts list with its bytes and sha256. Update `substrate/query.py:worker_regime_b_exclusions` to use `os.path.realpath` before the token check and verify the artifact's `split_map_sha256` against the live split map.

4. **N-4:** `docs/scoring-protocol.md` line 71 — pin the judge model by revision/commit digest (e.g., `google/flan-t5-large@<revision-sha>`). Add test asserting the pinned revision matches the current scoring code's expectation.

### BLOCKING-FOR-ROUND-1 (record as caveats in STATUS.md, no code change)

5. **N-5:** Record private test power limitation (116 items, 62 groups, 15 paired) as accepted risk.

6. **N-6:** Record generator confound risk (Qwen2.5-1.5B-Instruct-Q4_K_M may floor) as accepted risk.

7. **N-7:** Record leakage gate one-shot procedural assumption (workspace separation, not kernel boundary) as accepted risk.

8. **N-8:** Ensure scale adjudication unwired status remains visible in STATUS.md (already there at §4, line 167-171).

---

## Convergence

The repair loop is converging. v6 closed the control-flow holes (candidate/durable split, dirty-tree promotion, vacuous pin check, hermetic CI, one-shot leakage gate). v7 finds that the **scientific contract** has cracks: the preregistration anchor is wrong, the judge is unpinned, the Regime B superset isn't byte-pinned, the private test power is unknown, and the generator confound is unquantified. These are not verifier bugs — they are design decisions that must be documented as limitations before Round 1 begins.

After N-1 through N-4 land (each a few lines + regression tests), with a full verification run passing, I would return PASS with the eight caveats above recorded in STATUS.md.