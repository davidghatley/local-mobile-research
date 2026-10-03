# Round 0 Independent Freeze Review — v6 (control-flow and trust-chain attack)

**Reviewer:** fresh independent reviewer, v6. Ran as `openrouter/qwen/qwen3.8-27b:free`
(verified zero-cost named endpoint). Nested spawning disabled. No subagents. No paid
fallback.

**Repo:** `/home/davidhatley/Projects/testing/local_mobile_research` at HEAD
`12dc6743c02615b1a512b85707517a132bb43600` (working tree clean at start).

**Method (deliberately different from v5):** v5 attacked the *data* (truncation,
co-edit, vacuous comparisons). This review attacks the **control flow of the freeze
mechanism and the trust chain of the durable record**: every path by which a durable
record could exist without a complete passing full run; stale-record persistence;
dirty-tree semantics; forgeability of the commit binding; tag/record mutual ambiguity;
the out-of-repo census pin's failure modes; clean-clone/code-only honesty; model-facing
metadata boundaries; leakage-gate information disclosure; Regime-B exclusion derivation;
scoring-policy post-hoc freedom.

**Custody declaration:** I am not the custodian. I did not read
`questions.json`, `labels.json`, `counts.json`, or the `review/` / `authored/`
subdirectories of the private evaluation directory. I read `schema.json` (permitted)
and the opaque in-repo `corpus/private_test_manifest.json` (permitted). I inspected
the out-of-repo `freeze_census_pin.json` **structurally only** (key names and value
types; the digest strings are also partially visible in repo docs/tests, and the
counts values I did not print). All private files that my probes needed were copied
as opaque bytes into `/tmp/opencode/v6/` (never opened by me), which mirrors exactly
what `tests/test_freeze_manifest_durability.py` does. All destructive probes ran in
`/tmp/opencode/v6/` only. I wrote only this file.

---

## 1. Static-review findings (recorded before probing)

### F-v6-1 (BLOCKER K, NEW, material): the scoring policy's "FROZEN AT" commit is a
### fiction — the frozen files did not exist at that commit, and no test enforces it

`docs/scoring-protocol.md` line 9:

> **FROZEN AT:** commit `88aa1776eda01b87d014d235bbc84004d8dc7b78`

Verified:

```
$ git cat-file -e 88aa177:docs/scoring-protocol.md
fatal: path 'docs/scoring-protocol.md' exists on disk, but not in '88aa177'
$ git cat-file -e 88aa177:eval/answer_scoring.py
fatal: path 'eval/answer_scoring.py' exists on disk, but not in '88aa177'
$ git log --oneline -3 -- docs/scoring-protocol.md
75884b5 Round 0 closure: ...   (only commit that ever touched the file)
```

Both "frozen" files were first committed at `75884b5`, a child of `88aa177`. The
pre-registration therefore cites a commit at which the preregistered policy does not
exist: `git show 88aa177:docs/scoring-protocol.md` cannot reproduce the frozen
document. The claim that a later diff "is detectable via `git log` / `git diff`" is
true in the weak sense (diff against any commit), but the named freeze anchor is
unverifiable. No test references `88aa177`, `FROZEN AT`, or the scoring protocol at
all — enforcement is manual process only. Whether this is a freeze *violation*
depends on whether "private outputs exist"; they do not yet (no Round 1 run), so the
gate is not broken — but the preregistration record is internally inconsistent and
must be corrected (anchor to the commit that actually carries the frozen bytes, or
commit the doc at the eventual freeze commit) before the freeze tag, because after
the tag the anchor is load-bearing.

### F-v6-2 (BLOCKER 3, NEW, minor-material): preregistered leakage threshold in the
### custody doc contradicts the implemented constant

`docs/private-eval-custody.md` lines 103–105:

> 3. `difflib.SequenceMatcher` ratio on normalized strings >=
>    `OVERLAP_CHAR_RATIO_THRESHOLD = 0.85`. ... `0.85` still requires a near-identical
>    character sequence.

`substrate/private_eval.py` line 271: `OVERLAP_CHAR_RATIO_THRESHOLD = 0.80`, with the
module docstring explaining that 0.85 missed the measured 0.838 insertion case and
that the threshold was **lowered to 0.80** from a measured separation
(`tests/test_private_leakage_gate.py` pins the 0.80 behaviour). The code and its test
agree on 0.80; the custody/protocol document still says 0.85. For a preregistered,
"amendment-only" threshold, the written preregistration and the implementation must
agree; as written, an auditor cannot tell which threshold the gate is frozen at.
Docs fix, no code fix needed (the code value is the one justified by the recorded
measurement).

### F-v6-3 (BLOCKER 1/F, probe-pending): stage 8's out-of-repo pin check is vacuous
### when the pin exists but carries no digest

`scripts/verify_round0` (stage 8, lines 1317–1328):

```python
pin = json.load(pf)
pinned = pin.get("partition_census_sha256")
if pinned and pinned != census_digest:
  mark_fail()
else:
  detail("census digest MATCHES out-of-repo freeze pin (%s)" % census_digest[:16])
```

If the pin is a JSON object **without** the `partition_census_sha256` key (or with it
null/empty), `pinned` is falsy, the `if` is skipped, and the stage prints
"MATCHES out-of-repo freeze pin" and does **not** mark failure. The check is
"if a digest is pinned, it must agree" — not "a digest must be pinned". A custodian
(or corruption) that strips the key from `freeze_census_pin.json` turns the trust
root into a rubber stamp that still prints MATCHES. The existing tests
(`tests/test_census_trust_root.py`, `tests/test_freeze_manifest_durability.py`)
cover *mismatch* and *absent pin*, not *pin present with the digest key removed*.
Probe in §2.

### F-v6-4 (BLOCKER 1, probe-pending): `--only 1,2,3,4,5,6,7,8,9,10` reaches the
### promotion conditions but must still not promote

With `--only` listing all ten stages, `N_EXECUTED == N_TOTAL == 10`, and a clean run
has `N_FAIL == 0`, `N_SKIP == 0` — the promotion guard's numeric conditions would all
hold. The only protection is the earlier shortcut

```bash
if [ "$MODE" = "code-only" ] || [ -n "$ONLY" ]; then
  echo " RESULT: code-level checks completed (NOT a freeze pass)."
  exit 0
fi
```

which exits **before** the promotion block. If that ordering were ever reordered,
`--only`-with-all-ids would promote a "partial" run. No existing test runs
`--only` with all ten ids. Probe in §2. Related: `--only=` (empty value) is
treated as "no filter" and behaves exactly as a full run (degenerate but safe, since
it really is an unfiltered full run); noted, not a defect.

### F-v6-5 (BLOCKER C): dirty working tree is RECORDED, never a FAILURE — the commit
### binding of a dirty-tree freeze does not reproduce the verified bytes

`substrate/manifest.py` (`validate_freeze`, lines 765–768):

```python
# working_tree_dirty is RECORDED, never a gap: the binding is the flag in
# the record itself, ...
```

Consequences: a full run on a dirty tree promotes a durable record whose
`commit_sha` is the last clean commit while `code_hashes` bind the **dirty** on-disk
files. Anyone who checks out `commit_sha` re-verifies a *different* tree: the
recorded code hashes will mismatch, so the record is not reproducible from its own
commit binding. Nothing in the verifier, the docs, or the tests requires the freeze
run to be on a clean tree, and nothing at promotion time refuses `DIRTY`. Whether
that is acceptable depends on the stated re-verification protocol (if the protocol
says "the record's code_hashes are authoritative and the commit is informational",
the flag suffices; if it says "re-run at the recorded commit", a dirty freeze is
silently broken). The docs do not currently pick one. Probe in §2 (produce a dirty
record; then show re-verification at the recorded commit fails).

### F-v6-6 (BLOCKER D/E, probe-pending): the durable record is an unsigned JSON file
### in a custodian-controlled directory; no consumer protocol exists in-repo

The record (`freeze_manifest_<sha>.json` + `freeze_manifest.json` pointer) is plain
JSON with digest fields; there is no signature, no internal hash over its own
fields, and no code in the repository that *reads* a durable record and validates
it (grep for `freeze_manifest` consumers in §2). `RunManifest.read()` performs no
integrity check. So:

- `commit_sha` is forgeable to any 40-hex string; `stage_results` are forgeable;
  nothing in the record detects that.
- The only detection mechanism is *external re-verification*: re-run
  `scripts/verify_round0` at the claimed commit and compare a fresh record. That is
  a real but strictly procedural property, and it is only as strong as the promise
  that an independent actor will re-run it. The docs must say exactly this without
  overclaiming (probe §2: what do the docs actually claim?).
- Stale records are never cleaned up (probe §2: pre-seed an old
  `freeze_manifest_<oldsha>.json`, run a successful freeze at a new commit; the old
  record persists and nothing distinguishes it except the filename/commit field).
- The pointer is swung last-writer-wins; two concurrent runs at different commits
  can leave the pointer pointing at whichever finished last. A consumer that trusts
  "pointer == the current freeze" without re-checking `record.commit_sha` against
  the commit it expects is exposed. No consumer protocol is specified anywhere in
  the repo (tag creation, pointer reading, staleness detection). Probe §2.

### F-v6-7 (BLOCKER E, documentation gap): no tag↔record binding is specified

A repair tag exists (`round0-repair-2026-10-02` at `88aa177`) whose message says
"THE FREEZE GATE IS NOT SATISFIED" — so no freeze tag exists, consistent with the
tasking. But nothing in the repo specifies what the eventual freeze tag must
contain or how it becomes mutually unambiguous with the record: the record carries
no tag name; the tag message carries no record digest; there is no rule for what
happens when a tag is created at a commit with no record, or a record exists for a
commit with no tag. This is a process-spec gap, not a code bug: it must be written
down before the tag is created, because after the fact the ambiguity is permanent.

### F-v6-8 (BLOCKER G, probe-pending): code-only on a host without the private dir —
### skip-honesty to be measured, not assumed

To be probed in §2 on a clean-clone-style tree (tracked files only, no
`LMR_PRIVATE_EVAL_DIR`).

---

## 2. Probes (control flow and trust chain)

### 2.0 Probe workspace

- Repo copy: `/tmp/opencode/v6/repo` = `git archive HEAD` of the real repo (exact
  tracked bytes at `12dc674`), plus a copy of `.git`, plus read-only symlinks to the
  git-ignored bulk artifacts (`corpus/corpus.jsonl`, `corpus/raw`,
  `corpus/archive`, `corpus/scale/raw`, `corpus/scale/distractor.jsonl`,
  `generator_runtime/artifacts`). Untracked symlinks are excluded via
  `.git/info/exclude` so `git status --porcelain` is empty (clean tree).
- Throwaway private dir: `/tmp/opencode/v6/priv` = opaque byte copies of
  `questions.json labels.json counts.json seal.sha256 freeze_census_pin.json
  schema.json` (never opened by the reviewer).
- `TMPDIR=/tmp/opencode/v6/tmp` for verifier scratch so nothing lands on the real
  `/tmp` paths or the real private dir. `LMR_PRIVATE_EVAL_DIR` is **always** set to
  the throwaway dir for any full-mode probe.
- Clean clone: `/tmp/opencode/v6/cleanclone` = `git archive HEAD` only (no bulk
  artifacts, no private dir, `LMR_PRIVATE_EVAL_DIR` unset) — the CI-equivalent host.

### 2.1 Phase A — partial-run artifact creation (BLOCKER 1 control flow)

| # | Probe | Command (abridged) | Result |
|---|-------|--------------------|--------|
| A1 | `--only 8` must not leave a durable record | `./scripts/verify_round0 --only 8` | rc=0; `STAGE 8 PASS`; `freeze candidate staged (scratch only...): .../verify_round0.nJcA2z/freeze_manifest_candidate.json`; **no** `freeze_manifest*.json` in priv. CLOSED as designed. |
| A2 | `--code-only` (7 stages) | `./scripts/verify_round0 --code-only` | rc=0; `stages passed: 7 failed: 0 skipped: 0`; banner present; **no** record. |
| A3 | `--only 1,2,3,4,5,6,7,8,9,10` (all ten via the filter) | same | rc=0; `stages passed: 10 failed: 0 skipped: 0` — **all numeric promotion conditions hold** — yet exit is the pre-promotion shortcut `RESULT: code-level checks completed (NOT a freeze pass)` and **no** record exists. The ordering guard works; it is currently the *only* thing standing between this input and a promotion, and no existing test exercises it. |
| A4 | `--only=` (empty value) | code inspection | `ONLY=""` makes `[ -n "$ONLY" ]` false: no PARTIAL banner, `SELECTED` = full stage set, and the run reaches the promotion block — i.e. identical to an unfiltered full run. Degenerate but safe (it really is a full unfiltered run). |
| A5 | Full run with a stage failing after 8 | (covered by the failed-full-run below + existing `test_stage9_failure_blocks_promotion` class) | No record; pre-existing record byte-identical. |
| A6 | Interrupted run between promotion steps (SIGKILL) | residue analysis + glob check | The promotion sequence is `cp cand → .freeze_manifest_<sha>.tmp.$$` then `mv` to the versioned name, then `cp` + `mv` for the pointer. Both `mv`s are in-directory renames (atomic). A SIGKILL between cp and mv can leave a **fully written hidden** `.freeze_manifest_<sha>.tmp.<pid>` in the private dir; it is not the versioned record, not the pointer, and is not matched by the repo's record glob (`freeze_manifest_[0-9a-f]{40}\.json`). No consumer can mistake it for a record. See §3 finding N-9 (docs overstate "half-written durable file is never left behind"). |
| A7 | Two concurrent runs | code analysis (not executed) | Versioned names are commit-keyed; temp names are PID-keyed; the `CANDIDATE_SHA == HEAD` check runs at promotion, so a run whose revision changed mid-run fails loudly ("revision changed mid-run"). Two same-commit runs write the same versioned name (last mv wins, both valid); two different-commit runs leave two individually valid records and a last-writer pointer that always carries bytes of one of them. No incoherent state identified. |
| A8 | Full pass + read-only private dir | `chmod 555 priv; ./scripts/verify_round0` (full) | **10/10 PASS, rc=1**: `FREEZE RECORD: FAIL -- cannot stage the versioned record in .../priv` then `RESULT: FAIL (durable freeze record could not be promoted)`. Fails loudly; no record; exit code is not 0. |
| A9 | Private dir on a different filesystem than scratch | cross-fs simulation (candidate device 55 tmpfs → dest device 57 root) | The promotion never performs a cross-fs `os.replace`: it `cp`s the candidate into `DEST_DIR` then `mv`s **within** `DEST_DIR`. Cross-fs verified working; pointer bytes == versioned bytes; injected read-only dest fails the `cp` guard → exit 1, no partial record. |
| A10 | `MODE=full` with `--only` also given | = A3 | Never promotes (A3). |

**Phase A conclusion:** I found **no** path by which a durable record is created
without a complete, unfiltered, zero-failure, zero-skip full run of the verifier
itself. The candidate/durable split from BLOCKER 1 is correctly wired. Residual
issues: the pin vacuity in §2.4 (which can make such a "pass" vacuous at stage 8),
and the dirty-tree promotion semantics in §2.3.

### 2.2 Phase B — stale durable manifest persistence

- Pre-seeded `freeze_manifest_0000...0.json` + pointer (fake old record), then
  ran a successful full run at `12dc674` (see §2.3). After the run:

```
freeze_manifest_0000...0000.json   (195 B, commit 0000..., UNCHANGED, byte-identical)
freeze_manifest_12dc6743...json    (11362 B, commit 12dc674, working_tree_dirty=true)
freeze_manifest.json               (pointer == new record bytes, verified by cmp)
```

- Stale records are **never cleaned up** and nothing in the repo distinguishes a
  stale record from a current one except its filename/`commit_sha` field. There is
  **no in-repo consumer** of the durable record at all (grep: only the verifier
  itself writes it; `RunManifest.read()` is used by tests; no verification tool
  reads a record and checks it — and `RunManifest.read()` performs **no**
  integrity check: a forged `commit_sha` or forged `stage_results` is accepted
  silently, probes D1/D2 below).
- The pointer is self-describing (its bytes carry the record's `commit_sha`), so a
  consumer that re-checks `record.commit_sha` against the commit it expects is
  safe. But **no such consumer protocol is specified anywhere in the repo** (see
  §3 N-5). A consumer that trusts "pointer == the current freeze" without that
  check is exposed to: a stale versioned record read directly by name, and a
  last-writer pointer from a concurrent different-commit run.

### 2.3 Phase C — dirty working tree (empirical)

1. Dirty the copy's `eval/metrics.py` (uncommitted comment append; `git status`
   shows ` M eval/metrics.py`), full run with the throwaway private dir:
   **rc=0, 10/10 PASS, durable record promoted.** The record carries
   `commit_sha = 12dc674...`, `working_tree_dirty: true`, and
   `code_hashes["eval/metrics.py"] = 53730a20...` — the **dirty** on-disk hash.
2. The pristine file at that commit hashes to `d1a3b49c...`. Mismatch.
   Therefore a re-verifier who checks out `record.commit_sha` and re-verifies
   **fails** on the recorded code hash: the verified state is **not reproducible
   from the record's own commit binding**. `validate_freeze` records the flag and
   never fails on it (`substrate/manifest.py:765-768`), the promotion block does
   not inspect it, and no doc states that a freeze tag may anchor only a
   clean-tree record.

**Phase C conclusion:** a freeze *can* legitimately happen on a dirty tree today,
and the resulting record's commit binding is then decorative. This is a
re-verification-protocol gap, not a crash: see §3 N-2.

### 2.4 Phase F — external census pin mismatch (empirical)

| # | Probe | Result |
|---|-------|--------|
| F1 | pin present, `partition_census_sha256` key **removed** | **rc=0; prints `census digest MATCHES out-of-repo freeze pin (4925d84a40c8416f)`; `STAGE 8 PASS`. VACUOUS PASS CONFIRMED.** A full run under this pin would promote a durable record with no co-edit detection at all. This is the last open member of the "prints MATCHES while comparing nothing" defect class this review series has been catching (v1 stage-10, v3 zero-pin cross-check). See §3 N-1. |
| F1b | pin is a JSON **array** | rc=1; `verifier error in stage 8: AttributeError: 'list' object has no attribute 'get'` → `STAGE 8 FAIL`. Fail-safe (via crash, acceptable but ugly). |
| F2 | pin unreadable (`chmod 000`) | rc=1; `out-of-repo freeze pin unreadable: [Errno 13] Permission denied` → `STAGE 8 FAIL`. Fail-safe. |
| F3 | pin deleted (env set, empty private dir) — covered by existing `test_missing_pin_is_reported_not_silently_ignored` + code | `freeze pin ABSENT` → `mark_fail()`. Fail-safe. |
| F4 | private dir is a **symlink into the repo** (`/tmp/.../link_into_repo -> repo`) | `assert_private_dir_outside_repo` does **not** fire (it uses `os.path.abspath`, which does not resolve symlinks); stage 10 fails only because the private artifacts are absent at the resolved location. See §3 N-8. |
| F5 | private dir = a repo subdirectory | caught: `LMR_PRIVATE_EVAL_DIR resolves inside the repository (...)`; `STAGE 10 FAIL`. |
| F6 | `LMR_PRIVATE_EVAL_DIR` unset, full run | stage 8 prints `UNVERIFIED, not satisfied` (no `mark_fail`); stage 10 uses the compiled default dir; but the promotion block hard-fails on the unset env (`FREEZE RECORD: FAIL -- LMR_PRIVATE_EVAL_DIR is unset` → exit 1). No record. Fail-safe by inspection of `scripts/verify_round0:1841-1849`. |

### 2.5 Phase D — wrong-commit binding / forgeability (empirical)

- D1: took the promoted record, changed `commit_sha` to `ab...ab`, wrote it to
  scratch, `RunManifest.read()` → **accepted, no integrity check**.
- D2: forged `stage_results` to 10× PASS and `working_tree_dirty=false` →
  **accepted**.
- The record has **no signature and no internal hash over its own fields**
  (field list probed: 27 fields, all plain data).
- **Security property, stated plainly:** the durable record is a *procedural
  attestation*. It is tamper-*detectable* only by an independent actor
  re-running `scripts/verify_round0` at the claimed commit and comparing a fresh
  record (corpus/code/census/seal digests would diverge from a forged one). The
  custodian who controls the private directory can forge the record undetected
  **unless** that re-verification happens. The repo's docs are mostly careful
  about write-atomicity, but `docs/round0-review-criteria.md` §9.3 still
  describes the (unimplemented) schema `artifact_path/sha256/size_bytes/
  timestamp/git_commit` plus a `verify_freeze.py` that does not exist — the
  official gate document is out of sync with the implemented record. See §3 N-5.

### 2.6 Phase E — tag/manifest mismatch (spec gap, empirical check of current state)

- Current state verified: exactly one tag exists, `round0-repair-2026-10-02` →
  `88aa177`, annotated, message says "THE FREEZE GATE IS NOT SATISFIED". No
  freeze tag exists, consistent with the ledger.
- No document in the repo specifies what the eventual freeze tag must bind.
  **What the tag-binding record must contain (spec, not yet written):**
  1. tag target commit `C` == `record.commit_sha` of an existing
     `freeze_manifest_C.json`;
  2. that record has `working_tree_dirty == false`, `verifier_mode == "full"`,
     10× PASS `stage_results`;
  3. the tag message (or a recorded sidecar) carries the record's sha256 or
     filename, making tag↔record mutually locatable;
  4. rule: a tag at a commit with **no** record (or a record with
     `working_tree_dirty: true`) is invalid; the tag must not be created before
     the record exists;
  5. consumers verify the record at the tag target, not the pointer alone.
  None of 1–5 is written down anywhere yet. See §3 N-5.

### 2.7 Phase G — private path absent / code-only clean-clone behaviour (empirical)

Clean clone (tracked files only, no bulk artifacts, no private dir, env unset),
`--code-only`:

- rc=0; `stages passed: 3 failed: 0 skipped: 3` (plus stage 7 skipped inside a
  run); NOT VERIFIED section:

```
- 3  stage 3 (corpus converter tests): fixtures absent: corpus/raw
- 4  stage 4 (corpus-hash): required artifact absent
- 5  stage 5 (qa-validation): required artifact absent
- 7  stage 7 (generator-pin): required artifact absent
```

- Test-level audit of stage 1 on the clean clone: `Ran 442 tests ... OK
  (skipped=23)`. Every skip has a named, artifact-caused reason: 2 recursion
  guards (deliberate), 5 "no out-of-repo census trust root on this host (CI)",
  1 "freeze_census_pin.json absent", 1 "no private eval dir", 14
  "corpus/corpus.jsonl absent (sandboxed copy)". **All 23 are honest** (external
  artifact genuinely absent; none silently disable logic). No test failed where
  it should have; no silent skip found.
- Stage 7 on this host's clean clone additionally *verified* the runtime binary
  hashes (host paths exist here) and honestly skipped the 986 MB GGUF
  ("SKIPPED ... This check was NOT run. It is neither a pass nor a failure").
- Banner "THIS IS NOT A FREEZE PASS" present; `RESULT: all load-bearing stages
  PASS.` absent; no durable record possible (env unset + stages 6/8 not run).
- Real-repo baseline (this host, read-only): `tests/` 490 OK (skipped=19, all
  env-gated "no private eval dir"/"private custody digests unavailable" — honest),
  `data_tools/tests` 77 OK, `corpus/tests` 17 OK, `corpus/scale/tests` 38 OK.

**Phase G conclusion:** clean-clone/code-only behaves exactly as documented; the
skips are honest and enumerated. CLOSED.

### 2.8 Phase H — model-facing metadata leakage (empirical, in-process)

Adversarial partition entries with every field populated (deep nesting,
unicode lookalikes, unknown keys, answer-naming groups):

| # | Probe | Result |
|---|-------|--------|
| H1 | `object.__setattr__(q, "labels", {...})` on a `QueryInput` | `ForbiddenMetadataError` (instance `__dict__` is checked). |
| H2 | forbidden key nested at depth 3 | `ForbiddenMetadataError`. |
| H3 | nesting deeper than 10 levels | `ValueError` raised, payload refused fail-closed. |
| H4 | unicode-lookalike keys (`sliТ`, `sourcedоcument`) carrying metadata | **not caught** — documented limitation (case-sensitive exact key match; values not scanned). Safe *only* because the sanctioned path copies two fields; a whole-entry serialization with lookalike keys would pass the guard. |
| H5 | full adversarial stored entry through `to_model_query` | returns `QueryInput(question_id, text)` only; `model_visible_payload` is exactly `{'question_id', 'text'}`; the guard fires (`ForbiddenMetadataError` listing `group, labels, meta, paired_regime, question_..., ...`) if the whole entry were ever sent to a model. |
| H6 | `text` is a dict (metadata smuggled as a value) | `ValueError` (text must be a nonempty str). |
| H7 | empty `question_id` | `ValueError`. |
| H8 | forbidden-key *strings inside a set value* | not caught — documented keys-only semantics (a value that is a key-name is not a field). |
| H9 | clean `QueryInput` | passes. |
| H10 | `QueryInput` **subclass** adding a `labels` field | raised (`TypeError`/guard). |

**Phase H conclusion:** `to_model_query` + `assert_no_label_metadata` holds for
every construction I tried; residual lookalike-key exposure is documented and is
bounded by the two-field copy of the sanctioned path. CLOSED.

### 2.9 Phase I — leakage-gate information disclosure (empirical, synthetic private dir)

Using a synthetic private dir of 3 self-authored questions (full control; the
real private dir was never fed to the gate by me):

- I1a: benign record → `PASS`, reason `no question-level overlap detected`.
- I1b: exact copy + light edit → `REJECT`, reason `2 record(s) flagged by
  question-overlap rule`, `flagged_ids` = the caller's own synthetic ids.
- I1c: reason string names **only the count of the caller's own flagged
  records** — not the private set size, no private ids/text anywhere in the
  verdict. The 3-field boundary holds content-wise.
- I1d: malformed / bare-id / empty inputs → `REJECT` with generic reasons
  (fail closed). I1e: absent seal → `REJECT` (`absent is not a pass`). I1f:
  JSONL file path → `REJECT` with correct flagged id.
- **I1g (NEW): adaptive membership oracle.** Submitting a 10-candidate pool
  returned 8 flagged candidates — exact private texts *and* near-misses
  ("Which lake flows through the city of Cairo?", "When was the Brandenburg
  Gate built?"). With repeated batch submissions a team therefore gets a
  boolean "within the 0.8 flag ball of some private question" oracle and can
  **localize private question content to that ball** over their own candidate
  pools. The content itself never appears in any verdict, but the *behaviour*
  of the oracle leaks under adaptive use. The docs' claim "information
  asymmetry is preserved by design" is true only under a **one-shot,
  non-adaptive custodian regime** — which is currently a process assumption,
  not a documented or enforced control. See §3 N-7.
- **I1h (NEW): timing channel.** Wall-clock of `check_training_overlap` is
  linear in the private-set size (synthetic: 534 µs @1 q, 1338 µs @3 q,
  41356 µs @116 q; ratio 77.5× for 116× items). The private set **count** is
  timing-observable from the gate's latency (low value here — the count is
  public in the in-repo manifest — but the channel exists).

### 2.10 Phase J — Regime B exclusion leakage (empirical)

- J1: `worker_regime_b_exclusions` returns exactly the public artifact's 21
  articles, `source_artifact = corpus/regime_b_excluded_articles.json`,
  split-map pin present.
- J2: only `substrate/query.py` derives the worker list; `regime_metadata.py`
  references `regime_b_paired.json` only for the public in-repo paired artifact
  (which I verified contains **no** `qa-private-` ids and no `answer_text`).
  **No code path derives a worker exclusion from private paired-regime
  metadata.** The 15-paired-items/13-articles private pairing is referenced
  only as counts in the in-repo manifest.
- **J3 (NEW): symlink decoy accepted at call time.** Replacing
  `corpus/regime_b_excluded_articles.json` in the worktree copy with a symlink
  to a schema-conforming file elsewhere (`/tmp/.../decoyhome/regime_b_excluded_
  articles.json` — path string contains none of the `private|sealed|labels`
  tokens) made the function return the decoy's 2 articles. The token guard
  checks the *unresolved* path string; `open()` follows the symlink.
  Compounding: the artifact's bytes are **not pinned anywhere in the freeze
  record** — it is absent from `corpus/build_manifest.json` (verified), from
  `code_hashes` (.py only), and from the stage-8 inventory; stage 9 constrains
  only the *title set* of a committed artifact (21 vs split-map-derived), not a
  worktree-level substitution at call time. The artifact's own
  `split_map_sha256` field is checked for presence only, never against the live
  split map. See §3 N-6.

### 2.11 Phase K — scoring-policy post-hoc freedom (empirical)

- `docs/scoring-protocol.md` + `eval/answer_scoring.py` are byte-identical
  between their true origin `75884b5` and HEAD `12dc674`
  (`git diff --stat 75884b5..HEAD -- <both>` = empty). No private outputs exist
  yet, so no freeze break has occurred.
- **But** the stated anchor is wrong (see §1 F-v6-1): the files did not exist at
  `88aa177`, and **no test enforces any FROZEN AT commit** (grep for
  `88a177`/`scoring-protocol`/`FROZEN AT` across tests, substrate, eval,
  scripts: zero hits; the only reference is the doc itself). See §3 N-3.

### 2.12 Blocker-by-blocker closure verification (all seven)

| Blocker | Repaired as claimed? |
|---|---|
| 1 | **Yes** — candidate/durable split works on every probe in §2.1 (A1–A10). New adjacent issues N-1/N-2/N-9 do not reopen the blocker. |
| 2 | **Yes** — `tests/test_private_eval_custody_failclosed.py` is fully hermetic (synthetic fixture, `--only 10`, env passed to subprocess only, no dev-path fallback); `--code-only` runs 7 stages (empirical A2); the only surviving `/home/davidhatley` reference in code is the documented runtime default in `substrate/private_eval.py` (not a test fallback). |
| 3 | **Yes (code)** — 3 preregistered layers; 0.80 thresholds justified by a recorded measured separation; frozen 3-field verdict empirically confirmed (§2.9). Doc mismatch N-4 (0.85 vs 0.80) and oracle property N-7 are new. |
| 4 | **Yes** — §2.10: public 21 only; new symlink gap N-6. |
| 5 | **Yes** — §2.8: two-field `QueryInput`, guarded conversion, all smuggling vectors refused. |
| 6 | **Partially** — the policy exists and is detailed, but its FROZEN AT anchor is a commit at which the policy did not exist and is enforced by no test (§1 F-v6-1 → N-3). |
| 7 | **Yes** — `eval/scale_analysis.py`: unjudged → `unknown`/`unjudged_mechanical`, recall over known-core-support only, `unjudged_top_k` + `limitations` first-class, no precision over unjudged; `tests/test_scale_analysis` green. |

---

## 3. New findings (numbered repair list)

- **N-1 (code, gate-level):** `scripts/verify_round0` stage 8: a pin that exists
  but lacks `partition_census_sha256` (or carries null/empty) prints "census
  digest MATCHES out-of-repo freeze pin" and passes (probe F1, rc=0). Require
  `isinstance(pin, dict)` and a 64-hex `partition_census_sha256`, failing
  otherwise; add a regression test (pin present, key stripped → stage 8 must
  FAIL with a non-vacuous message) in `tests/test_census_trust_root.py`.
- **N-2 (code, gate-level):** promote only on a clean tree: in the promotion
  block, read `working_tree_dirty` from the finalized candidate and refuse
  (exit 1, loud message) when it is true — a dirty record's `commit_sha` does
  not reproduce the verified bytes (probe §2.3). Alternatively, if dirty
  freezes are to remain possible, the tag protocol (N-5) must forbid anchoring a
  tag on a dirty record and the docs must say so. The hard check is the
  preferable fix.
- **N-3 (docs + test):** `docs/scoring-protocol.md` FROZEN AT `88aa177` — the
  file did not exist at that commit (first committed at `75884b5`); no test
  enforces the anchor. Fix the anchor to the commit that actually carries the
  frozen bytes and add a test asserting the current bytes of
  `docs/scoring-protocol.md` and `eval/answer_scoring.py` equal the anchored
  commit's blobs (or that no post-anchor commit touched them).
- **N-4 (docs):** `docs/private-eval-custody.md` lines 103–105 still state
  `OVERLAP_CHAR_RATIO_THRESHOLD = 0.85`; code and test are 0.80. Align the doc.
- **N-5 (docs/process):** write the tag↔record protocol (§2.6 items 1–5) and
  sync `docs/round0-review-criteria.md` §9.3 with the implemented record
  (currently it specifies `git_commit`/`verify_freeze.py`, neither of which
  exists). State plainly that the record is a procedural, re-verifiable
  attestation (no signature), and that staleness of versioned records is
  expected (they are never cleaned up).
- **N-6 (code, defense-in-depth):** byte-pin `corpus/regime_b_excluded_articles.
  json` (add to `corpus/build_manifest.json` so stage 4 + the stage-8 inventory
  bind it) and/or in `worker_regime_b_exclusions`: resolve the path with
  `os.path.realpath` before the token check and cross-check the artifact's
  `split_map_sha256` against the live split map (probe J3).
- **N-7 (docs/process):** record the leakage gate's one-shot property (§2.9
  I1g/I1h): the verdict is a boolean near-duplicate membership oracle; under
  adaptive resubmission the caller can localize private content to the flag
  ball, and timing is linear in the private-set size. The custodian regime must
  treat repeated similar resubmissions as an audit event (rate/audit control),
  and the module docstring + `docs/private-eval-custody.md` must say the
  information boundary holds for one-shot submission. No code change required.
- **N-8 (code, hardening):** `assert_private_dir_outside_repo` uses
  `os.path.abspath` (no symlink resolution): a symlinked private dir resolving
  into the repo passes the assertion (probe F4). Use `os.path.realpath` on both
  sides.
- **N-9 (docs):** `docs/verify-round0.md` §4 "A half-written durable file is
  never left behind" overstates: a SIGKILL between cp and mv can leave a fully
  written hidden `.freeze_manifest_*.tmp.<pid>` (probe A6). Soften the sentence
  and/or sweep `*.tmp.*` files at promotion start.

---

## 4. FINAL CLOSURE — in mandated order

### 4.1 Verdict

**REPAIR REQUIRED**

The BLOCKER 1 control flow is sound: I found no path by which a durable freeze
record exists without a complete, unfiltered, all-stages-passing full verifier
run (probes A1–A10). Stale records survive but are self-describing; clean-clone
code-only is honest; the model-facing boundary holds; Regime B derivation is
public-only; the leakage gate's 3-field verdict is content-free; the scale
metrics are unjudged-as-unknown.

However, five repairs must land before Round 0 may be frozen and tagged:

1. **N-1** (code): stage 8 must fail when the out-of-repo pin lacks a valid
   digest — a stripped pin currently prints MATCHES and a full run would
   promote a record with no co-edit detection (empirically confirmed, probe F1).
2. **N-2** (code): refuse promotion on `working_tree_dirty: true` (or encode
   that restriction in the tag protocol and docs) — a dirty-tree record's commit
   binding does not reproduce the verified state (empirically confirmed, §2.3).
3. **N-3** (docs+test): correct the scoring policy's FROZEN AT anchor (files
   absent at the cited commit) and enforce it with a test.
4. **N-4** (docs): custody doc's leakage threshold (0.85) contradicts the
   preregistered implemented constant (0.80).
5. **N-5** (docs/process): write the tag↔record binding protocol and desync-free
   `round0-review-criteria.md` §9.3 with the implemented record.

N-6…N-9 are defense-in-depth/docs and should land with the above but are not
individually gate-breaking.

### 4.2 Table of the seven repaired blockers (closed? evidence)

| # | Blocker | Closed? | Evidence (this review) |
|---|---------|---------|------------------------|
| 1 | Freeze finalization: candidate in scratch; durable record promoted by shell only after full unfiltered clean pass | **Yes** | §2.1 A1–A10: `--only 8` (rc=0, no record), `--only 1..10` (10/10 PASS, no record), `--code-only` (no record), failed full run (no record, stale record byte-identical), successful full run (exactly one versioned record + byte-identical pointer, commit/verifier/stage bindings all correct), read-only priv (10/10 PASS then `FREEZE RECORD: FAIL`, exit 1), cross-fs promotion safe. Adjacent new issues N-1/N-2/N-9 noted. |
| 2 | Hermetic CI: `test_private_eval_custody_failclosed.py` builds own fixture; `--code-only` drops stage 10 (7 stages); no hardcoded dev-path fallbacks in tests | **Yes** | Read the whole test: synthetic private dir, `--only 10`, env via subprocess only. Empirical A2: `stages passed: 7`. Grep: only `/home/davidhatley` left in code is the documented runtime default in `substrate/private_eval.py:99` (not a test). Clean-clone run §2.7: rc=0, all skips named. |
| 3 | Leakage gate: `check_training_overlap` on `{synthetic_id, text}`; 3 preregistered layers; threshold 0.80 char ratio from measured separation; frozen 3-field result | **Yes (code)** | §2.9: all fail-closed paths verified (no seal/malformed/bare-ids/empty → REJECT); verdict carries only verdict + generic reason + synthetic ids; thresholds in `substrate/private_eval.py:265-271` with recorded probe table. New: doc says 0.85 (N-4); adaptive-oracle property needs a documented one-shot regime (N-7). |
| 4 | Regime B: workers use the PUBLIC 21-document exclusion list, never the private 13 | **Yes** | §2.10: `worker_regime_b_exclusions` reads only `corpus/regime_b_excluded_articles.json` (21 articles, verified equal to artifact); no code path derives a worker list from private paired metadata; in-repo `regime_b_paired.json` contains no private ids. New gap: symlink-decoy at call time + artifact not byte-pinned in the freeze record (N-6). |
| 5 | Model-facing query: `QueryInput(question_id, text)` only | **Yes** | §2.8 H1–H10: two-field frozen dataclass; `to_model_query` copies exactly two fields; `assert_no_label_metadata` catches `__setattr__` smuggling, nested keys, subclass fields; depth>10 refused; non-string text refused. Lookalike-key limitation documented. |
| 6 | Scoring policy preregistered in `docs/scoring-protocol.md` | **Partially** | Policy exists, is detailed, and is unchanged since its true origin `75884b5` (verified). But FROZEN AT cites `88aa177`, at which both frozen files did not exist (`git cat-file -e` fails for both), and no test enforces the anchor → N-3. |
| 7 | Scale metrics with unjudged-as-unknown, `eval/scale_analysis.py` | **Yes** | Docstring + code: `unknown`/`unjudged_mechanical` triage, recall over known core support only, `unjudged_top_k` + `limitations` first-class, no precision over unjudged; `tests.test_scale_analysis` OK. |

### 4.3 Probe results (commands and key outputs)

Full details in §2.0–§2.12. Key commands and decisive outputs:

```
# Workspace
git archive HEAD | tar -x -C /tmp/opencode/v6/repo          # exact tracked bytes at 12dc674
cp -a .git /tmp/opencode/v6/repo/.git                       # commit binding resolves to the real commit
cp -a $PRIVATE/{questions.json,labels.json,counts.json,seal.sha256,freeze_census_pin.json,schema.json} \
      /tmp/opencode/v6/priv/                                # opaque bytes only, never opened by me

# A1  --only 8 -> no durable record
LMR_PRIVATE_EVAL_DIR=/tmp/opencode/v6/priv ./scripts/verify_round0 --only 8     # rc=0
  -> "STAGE 8 freeze-manifest: PASS", "freeze candidate staged (scratch only...)"
  -> ls priv/ : no freeze_manifest*.json

# A3  --only all ten -> promotion shortcut, no record
./scripts/verify_round0 --only 1,2,3,4,5,6,7,8,9,10        # rc=0
  -> "stages passed: 10   failed: 0   skipped: 0"
  -> "RESULT: code-level checks completed (NOT a freeze pass)."
  -> priv: 0 freeze records

# A2  --code-only -> 7 stages, no record
./scripts/verify_round0 --code-only                         # rc=0, "stages passed: 7", banner present

# B/C  stale record + dirty tree + successful full run
printf '...\n' >> eval/metrics.py                           # git status: " M eval/metrics.py"
./scripts/verify_round0                                     # rc=0, 10/10 PASS
  -> promoted freeze_manifest_12dc674...json + pointer (bytes identical)
  -> record: commit_sha=12dc674..., working_tree_dirty=true, 10x PASS stage_results
  -> stale freeze_manifest_0000...json UNCHANGED (byte-identical)
  -> record code_hashes[eval/metrics.py]=53730a20... vs pristine-at-commit d1a3b49c...  (mismatch)

# A8  read-only private dir
chmod 555 priv && ./scripts/verify_round0                   # 10/10 PASS, rc=1
  -> "FREEZE RECORD: FAIL -- cannot stage the versioned record" / "RESULT: FAIL"

# F1  pin without partition_census_sha256 -> VACUOUS MATCHES
python3 - <<'EOF'  # strip the key from a copy of the pin
...
./scripts/verify_round0 --only 8                            # rc=0
  -> "census digest MATCHES out-of-repo freeze pin (4925d84a40c8416f)" / "STAGE 8 ... PASS"

# F2  pin chmod 000  -> "out-of-repo freeze pin unreadable: [Errno 13]" -> STAGE 8 FAIL (rc=1)
# F1b pin = JSON array -> AttributeError -> STAGE 8 FAIL (rc=1)
# F4  LMR_PRIVATE_EVAL_DIR -> symlink into repo: boundary assertion does NOT fire
#     (abspath, no realpath); stage 10 fails only on absent artifacts
# F5  LMR_PRIVATE_EVAL_DIR = repo/corpus -> "resolves inside the repository" -> STAGE 10 FAIL

# G   clean clone (tracked files only, env unset)
./scripts/verify_round0 --code-only                         # rc=0
  -> "stages passed: 3   failed: 0   skipped: 3"
  -> NOT VERIFIED: 3 (fixtures absent: corpus/raw), 4/5 (artifact absent), 7 (GGUF absent)
  -> stage 1: "Ran 442 tests ... OK (skipped=23)" — all skips artifact-caused (named reasons)
  -> real repo baseline: tests 490 OK (skipped=19, env-gated), data_tools 77 OK,
     corpus 17 OK, corpus/scale 38 OK

# D   forgery
RunManifest.read(record_with_commit_sha="ab"*20)            # accepted, no integrity check
RunManifest.read(record_with_forged_all_PASS_stage_results) # accepted

# J3  symlink decoy for the regime-B artifact
ln -s /tmp/opencode/v6/decoyhome/... corpus/regime_b_excluded_articles.json
worker_regime_b_exclusions(root) -> returns decoy's 2 articles   # token check on unresolved path

# K   frozen-file provenance
git cat-file -e 88aa177:docs/scoring-protocol.md   # fatal: not in '88aa177'
git cat-file -e 88aa177:eval/answer_scoring.py    # fatal: not in '88aa177'
git log --oneline -3 -- docs/scoring-protocol.md  # 75884b5 only
git diff --stat 75884b5..HEAD -- docs/scoring-protocol.md eval/answer_scoring.py  # empty
```

### 4.4 What I could not verify (and why)

- **CI on GitHub** — I cannot run the Actions workflow; I verified its
  clean-clone-equivalent locally (§2.7) and checked its log-format assertions
  against actual output.
- **Timing of the gate against the real private dir** — measured only on a
  synthetic private dir (§2.9 I1h); the code path is identical, the real-dir
  magnitude is expected but not benchmarked, deliberately (no unnecessary
  execution against the sealed dir).
- **Two concurrent full runs** — analyzed step-by-step (§2.1 A7); not executed
  (~2×8 min). Collision surface: PID-keyed temps, commit-keyed versioned names,
  per-run `CANDIDATE_SHA == HEAD` check; no incoherent state identified.
- **Mid-run commit race** — the `CANDIDATE_SHA != COMMIT_SHA` promotion check is
  verified by inspection; not empirically raced.
- **Private content itself** — custody; all private-side probes used opaque
  byte copies or the sanctioned verdict-only API.

### 4.5 Remaining repair list

1. **N-1 (code, gate):** `scripts/verify_round0` stage 8 — require the pin to
   carry a 64-hex `partition_census_sha256`; fail otherwise (today: stripped
   pin → "MATCHES" + PASS, probe F1). Regression test: pin present, key
   stripped → stage 8 FAIL, in `tests/test_census_trust_root.py`.
2. **N-2 (code, gate):** promotion block — refuse when the candidate's
   `working_tree_dirty` is true (loud exit 1); a dirty record's commit binding
   does not reproduce the verified bytes (probe §2.3). If dirty freezes must
   stay possible, the tag protocol (N-5) must forbid anchoring on dirty records
   and say so; the hard check is preferable.
3. **N-3 (docs + test):** `docs/scoring-protocol.md` — anchor FROZEN AT to the
   commit that actually carries the frozen bytes (`75884b5`, or the eventual
   freeze commit), and add a test asserting the anchored blobs equal the current
   bytes of `docs/scoring-protocol.md` and `eval/answer_scoring.py`.
4. **N-4 (docs):** `docs/private-eval-custody.md` lines 103–105 —
   `OVERLAP_CHAR_RATIO_THRESHOLD` 0.85 → 0.80.
5. **N-5 (docs/process):** write the tag↔record binding protocol (§2.6 items
   1–5: tag target == record.commit_sha; record clean-tree, full-mode, 10×PASS;
   tag message or sidecar carries the record's digest; no tag without a record;
   consumers verify at the tag target, not the pointer alone) and sync
   `docs/round0-review-criteria.md` §9.3 with the implemented record (the
   `git_commit`/`verify_freeze.py` schema it describes does not exist). State
   plainly that the record is a procedural, re-verifiable attestation with no
   signature, and that stale versioned records persist by design.
6. **N-6 (code, defense-in-depth):** byte-pin
   `corpus/regime_b_excluded_articles.json` (add to `corpus/build_manifest.json`
   so stage 4 + stage-8 inventory bind it); in `worker_regime_b_exclusions`
   resolve with `os.path.realpath` before the token check and verify the
   artifact's `split_map_sha256` against the live split map (probe J3).
7. **N-7 (docs/process):** record the leakage gate's one-shot information
   boundary (§2.9 I1g/I1h): the verdict is a boolean near-duplicate membership
   oracle; adaptive resubmission localizes private content to the 0.8 flag
   ball; timing is linear in the private-set size. Custodian control: repeated
   similar resubmissions are an audit event. Note in the module docstring and
   `docs/private-eval-custody.md`. No code change required.
8. **N-8 (code, hardening):** `substrate/private_eval.assert_private_dir_outside_
   repo` — use `os.path.realpath` on both sides (probe F4: symlinked private
   dir into the repo passes the assertion today).
9. **N-9 (docs):** `docs/verify-round0.md` §4 — "A half-written durable file is
   never left behind" overstates: a SIGKILL between cp and mv can leave a fully
   written hidden `.freeze_manifest_*.tmp.<pid>` (probe A6). Soften the wording
   and/or sweep `*.tmp.*` at promotion start.

**Convergence:** the repair loop is converging. This round's findings are
strictly narrower than v5's: one silent trust-root bypass (N-1, the same
"prints MATCHES while comparing nothing" family as v1), one record-anchoring
semantics gap (N-2), and small docs/process/hardening items (N-3…N-9). Nothing
undermines the candidate/durable architecture; nothing touches the corpus,
partitions, or private test content. After N-1…N-5 land (each a few lines), with
regression tests executed in a full run, I would expect a PASS on re-review.
