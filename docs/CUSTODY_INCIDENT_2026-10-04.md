# CUSTODY INCIDENT — the private evaluation store went missing mid-run

Date: 2026-10-04, discovered during final verification of the Round 1 run.
Severity: **BLOCKER for any future private evaluation.** Does **not** affect any
Round 1 result in this run.

## What happened

At the start of this orchestration run the private store was present, sealed and
intact:

```
/home/davidhatley/Projects/testing/local-mobile-research-private-eval/
  seal.sha256          c6e1e98d843eaf1eb962a9ec2f89026af2d532f9b963c5d0a78d45056293c54c
  questions.json       116 items, sha256 efa02e5c19ebce4ccd48bad189935894dc7fa2b02aaf635b235bee72a855a9a5
  labels.json          116 keys, sha256 2cb931b6c988f15d95c00d00be75807ce3a2ec2cb8c40d956050fd9ebe94d32d
  counts.json, schema.json, freeze_census_pin.json, freeze_tag_binding.json,
  seal_private.py, verify_private.py, SEAL.md, README.md, authored/, review/
```

`./scripts/verify_round0` (full, 10 stages) returned **10/10 PASS** and promoted
a durable freeze record. Custody was healthy at that point.

At the end of the run, during final re-verification, **the entire directory is
gone from the filesystem.** Confirmed by 10 consecutive checks over 20 seconds:
`isdir` → False, and `stat`, `ls`, `cat`, and Python `os.path.exists` all report
`No such file or directory` for every file including `seal.sha256`,
`questions.json`, and `labels.json`. The parent directory
`/home/davidhatley/Projects/testing/` still exists and still lists the entry, but
the entry does not resolve — the classic signature of a btrfs directory whose
extent was removed underneath a cached handle.

Consequence: `./scripts/verify_round0` now fails stages 6, 8 and 10 with
`private seal verification failed: no private seal ... (absent is not a pass)`.
**That is the gate working correctly.** An absent seal is reported as absent and
never as a pass, exactly as `substrate/private_eval.py` is designed to do.

## What I did NOT do, and why

* **I did not recreate, reconstruct, or reseal anything.** Writing a new
  `seal.sha256` would fabricate a trust anchor for data whose provenance I cannot
  attest. The seal's entire value is that it was written by the custodian at
  sealing time.
* **I did not read, copy, or cache any private content** before the loss. The only
  private-side calls in this run were `counts()` (counts and digests, the
  sanctioned custodian accessor, used once at orientation) and
  `check_training_overlap` with a `None` session (which correctly returned
  `REJECT`). No private question, answer, support atom or source id was ever read,
  so no copy exists outside the deleted directory.
* **I did not touch the private path in any command I issued.** No `rm`, no
  `mv`, no write.

## What I verified about causation

| check | result |
|---|---|
| `scripts/verify_round0` deletion code | only `rm -f "$TMP_REC"`, `rm -f "$TMP_PTR"`, and `rm -f "$DEST_DIR"/.tmp-promote-*.tmp` — all its **own** temp files. It never removes questions, labels, or the seal. |
| `substrate/private_eval.py` deletion code | **none** |
| `docs/probes_round0.sh` | its cleanup is `rm -f "$PRIV"/freeze_manifest_*.json "$PRIV"/freeze_manifest.json` — durable **freeze records only**, by design, and its own final assertion is "real private dir left with no durable record". It never touches the seal, questions, or labels. Probe 7's `rm -rf "$P"` operates on `$WORK/p7priv`, a temp stub, never on `$PRIV`. |
| probes run during this session | the probe harness reported **18/18 PASS** on its final run, including "real private dir left with no durable record" |
| filesystem | `/home` is `btrfs` (`/dev/mapper/root[/@home]`). No kernel btrfs errors were readable. No systemd timers are active that could prune. |
| disk | 30 G free, unchanged from the start of the run — not a space-pressure eviction |
| git | the private directory was **never** committed, by design (`git log --all --diff-filter=A -- "*private-eval*"` shows only custody *infrastructure*, no content), so **git cannot restore it** |

**I cannot establish the cause.** Nothing in this session's commands deletes that
directory, and the surviving evidence points away from the repository's own
tooling. The honest statement is that the cause is **unidentified**, and an
unidentified deletion of a sealed evaluation store is itself the finding.

## Why this is a serious finding, not an inconvenience

This repository's custody model is **procedural, not a security boundary**
(accepted risk #5): every process runs as the same OS user, so any process can
read, modify, or delete the private store. What the design *does* guarantee is
**fail-closed detection** — and that guarantee just fired, correctly and
unprompted, on real data loss.

The concrete new risk this exposes: accepted risk #5 says a determined worker
could reset the one-shot clearance ledger. This incident shows the same
procedural boundary also permits **destroying the benchmark outright**, with no
recovery path, because the store was correctly never in git. Round 0's reviews
reasoned about ledger tampering; they did not consider store destruction.

## Impact on this run's results

**None.** Every Round 1 result in this run is retrieval-side and was computed
from the **public** worker-visible partition:

* the generator-floor probe used dev + shadow_dev items via `staging/`
  ground truth, in-repo;
* all survival, completion, precision, latency and storage figures come from
  `corpus/` and `experiments/results/`;
* the private test was **never run**, which was the required stopping point.

No private-derived number appears in any artifact. The recommended private
protocol in `experiments/results/R1_SHORTLIST_AND_PRIVATE_PROTOCOL.md` is
**blocked on restoring the seal**, not on any scientific question.

## Required actions before any private evaluation

1. **Restore the store from an out-of-repo backup.** The seal digest is recorded
   in-repo at `docs/STATUS.md` (line 38): `c6e1e98d843eaf1eb962a9ec2f89026af2d532f9b963c5d0a78d45056293c54c`,
   and `questions.json` must hash to
   `efa02e5c19ebce4ccd48bad189935894dc7fa2b02aaf635b235bee72a855a9a5`,
   `labels.json` to `2cb931b6c988f15d95c00d00be75807ce3a2ec2cb8c40d956050fd9ebe94d32d`.
   Restored bytes that do not match those digests are **not** the sealed private
   test and must be re-sealed from source, not patched.
2. **Re-run `./scripts/verify_round0` (full) and require 10/10 PASS** on a clean
   tree before any architecture work resumes.
3. **Add an integrity monitor** that alerts when `$LMR_PRIVATE_EVAL_DIR` or any
   of its four pin files disappears. The current design detects a *wrong* seal
   but has no scheduled check for a *missing* store, which is why this was found
   by an incidental final verification rather than by the tooling.
4. **Keep an out-of-repo, integrity-monitored backup** of the private store. The
   decision to keep it out of git was correct for confidentiality and fatal for
   recoverability; it needs a third option.
5. **Record this as a new accepted risk** (#8): the private store is
   single-copy, procedurally protected, and unrecoverable if deleted.

Until 1–2 are done, **the private test cannot be run and must not be run.** The
correct state is: retrieval evidence is complete and frozen; the private
benchmark does not exist on this machine.
