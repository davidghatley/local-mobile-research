# Private evaluation custody

Status: interface and guards in place (Round 0 Phase 5). **No private content
exists yet.** Sealing happens only after Phase 6 authoring and independent
review.

## Location and environment variable

```
LMR_PRIVATE_EVAL_DIR=/home/davidhatley/Projects/testing/local_mobile_research-private-eval
```

The private directory is a **sibling of the repository**, outside git. The
default path is compiled into `substrate/private_eval.py` so the interface
works without configuration, and the env var allows relocation.

## What may live where

| Content | Main repository | Private directory |
|---|---|---|
| schema | yes (as a pointer + copy of field rules) | yes |
| counts, split metadata | yes | yes |
| opaque seal / content hashes | yes | yes |
| evaluation protocol / runner interface | yes | yes |
| private question text | **never** | yes |
| private answers, support atoms, labels | **never** | yes |
| private source ids that reveal answers | **never** | yes |
| private benchmark reports revealing answers | **never** | yes |

`tests/test_private_eval_tripwire.py` fails if private-evaluation filenames,
question text, or labels appear under the repository path, or if
`LMR_PRIVATE_EVAL_DIR` resolves inside the repository. The tripwire is an
explicit-path and provenance guard. It is **not** a semantic secret scanner
and does not claim to be one.

## Access model

Every process on this machine runs as the same OS user. **No kernel security
boundary exists and none is pretended.** Encryption or chmod would add no real
protection under one UID, so none is implemented. The boundary is
**procedural and workspace-based**:

| Role | May access private data |
|---|---|
| Top-level orchestrator / custodian | yes |
| Private-item authors (Phase 6, free models, explicitly assigned) | yes |
| Private-item reviewers (Phase 6, free models, different from authors) | yes |
| Round 1 architecture leads and workers | **no** |
| General QA / benchmark / corpus workers | **no** |
| Independent freeze reviewer (not assigned as custodian) | **no** |

Round 1 teams receive a **sanitized worktree or project copy** that excludes
`LMR_PRIVATE_EVAL_DIR`. They may access `train`, `dev`, `shadow_dev`, public
reference questions, the core corpus, the scale corpus, benchmark
interfaces, and opaque test hashes.

## The 89 shadow-dev items are not secret

The 89 `shadow_dev` questions were exposed in git history before this
boundary existed. They are dev-visible on purpose and are **never** to be
called held-out, sealed, secret, or proof of generalization. Deleting them
later would not restore secrecy, and history is not rewritten.

## Leakage checking (information asymmetry preserved)

Architecture teams will generate synthetic training questions from corpus
text. Document-level overlap is **legal**: Regime A explicitly allows
corpus-specific specialization. Exact or near-exact private **question**
leakage is not.

`substrate.private_eval.check_training_overlap()` is the custodian-side gate.
It takes training RECORDS (`{"synthetic_id", "text"}` dicts) or a training
file (JSON list or JSONL) via `check_training_file()`, and returns only:

```
{"verdict": "PASS" | "REJECT", "reason": ..., "flagged_ids": [synthetic training ids]}
```

It never returns the matched private question id, private text, private
answer, or private evidence. It **fails closed**: with no seal present, with
unreadable/malformed private questions, with malformed training input, or
whenever the comparison could not be executed, the verdict is `REJECT` with
a generic reason, never `PASS` on missing data. A legacy list of bare id
strings (no question text) also yields `REJECT`: without text there is
nothing to compare, so no clearance can be issued.

## Leakage rule (PREREGISTERED BEFORE any Round 1 training data exists)

Frozen at Round 0 closure, in `substrate/private_eval.py` module docstring
and constants. Thresholds may not be tuned after seeing a REJECT; changing
them once training data exists requires a recorded protocol amendment.

Normalization: casefold + collapse non-alphanumeric runs to one space +
strip. A record is FLAGGED when ANY layer fires against ANY private
question:

1. Normalized exact match (verbatim copy modulo case/punctuation/whitespace).
2. Token-set Jaccard similarity >= `OVERLAP_JACCARD_THRESHOLD = 0.80`.
   Order-insensitive, catches reworded duplicates reusing the private
   vocabulary. Deliberately conservative: a false positive costs the team
   only a rewrite; a false negative leaks a held-out question into training.
3. `difflib.SequenceMatcher` ratio on normalized strings >=
   `OVERLAP_CHAR_RATIO_THRESHOLD = 0.80`. Order-sensitive second signal for
   lightly edited copies. Set higher than the Jaccard threshold because
   character ratio is the noisier signal; 0.80 was verified against a measured
   separation (see table below). The old 0.85 threshold missed the 0.838
   insertion case; 0.80 catches it while sitting well clear of the unrelated
   cluster.

Measured separation (preregistered, fixed before Round 1 training data):
  exact duplicate ................................. 1.000   flagged
  case/punctuation/whitespace variant ........... 1.000   flagged
  "Which river flows through the city of Cairo?"
      vs "Which river flows through Cairo?" ...... 0.838   flagged
  unrelated ("How many legs does a spider have?") . 0.222   clean
  unrelated ("When was the Berlin Wall built?") .. 0.361   clean

Deterministic, stdlib only, no network. Reasons are generic
("no question-level overlap detected" / "N record(s) flagged by
question-overlap rule"); only SYNTHETIC ids are returned.

## Seal protocol

Sealing occurs after every private item is independently reviewed and all
sufficient-set semantics are corrected. The seal is an opaque digest of
private bytes, readable by the main repository as a hash and never as
content. `substrate.private_eval.verify_seal()` raises (does not return
`False`) when no seal exists: absent is not a pass.


---

## The leakage gate is a ONE-SHOT clearance decision

Review v6 demonstrated that this gate is a **boolean near-duplicate membership
oracle** against an adaptive caller. The returned object has only three fields,
so it cannot *carry* private content — but an architecture team permitted to
call it repeatedly can binary-search the private set: REJECT on one candidate
and PASS on a mutated candidate localises private content to the flag boundary.
Wall-clock cost also scales with the size of the private set (review v6
measured 77.5x for 116x items).

So the asymmetry claim in the section above is only true under a one-shot
regime. That regime is now **enforced**, not merely asserted:

- `check_training_overlap(records, session=<id>)` requires a session id. A call
  without one is REJECTed, because an untrackable session cannot be one-shot.
- The first clearance in a session is consumed. A second call with the same id
  is REJECTed without running the comparison at all.
- The session ledger lives in the **private directory**, so an architecture
  worker can neither read nor reset it.
- A fresh session is opened by the **custodian**, deliberately and on the
  record. It is not the caller retrying.

### Authorising a second clearance

An architecture team that needs a re-clearance after editing flagged records
asks the custodian for a new session id. The custodian records who asked, for
which team, and why. Repeated requests are a signal to investigate whether the
team is probing rather than iterating, and are grounds to deny.

### Measured separation, and what the thresholds do NOT catch

The character-ratio threshold was corrected from 0.85 to **0.80** after review v6
showed a lightly edited copy slipping through. The separation is measured, not
guessed (`max(jaccard, char_ratio)` on normalized text):

| case | score | flagged |
|---|---|---|
| exact duplicate | 1.000 | yes |
| case / punctuation / whitespace variant | 1.000 | yes |
| "…through the city of Cairo?" vs "…through Cairo?" | 0.838 | yes |
| unrelated ("How many legs does a spider have?") | 0.222 | no |
| unrelated ("When was the Berlin Wall built?") | 0.361 | no |

**A genuine semantic paraphrase is NOT caught.** "Cairo does the Nile flow
through?" scores 0.508 and "The Nile flows through which city?" scores 0.625 —
both below every threshold, because token and character similarity do not
measure meaning. The threshold is set deliberately above that band so it cannot
fire on unrelated vocabulary.

This is a scope decision, not an oversight. The gate targets **near-exact
leakage**: a copied or lightly edited private question, which is the realistic
failure mode, since no team would knowingly paraphrase a sealed question into
its training data. Catching deliberate paraphrase would require an embedding
model, which would make the threshold un-auditable and un-reproducible. **If a
future threat model includes paraphrase leakage, this gate must be replaced, not
re-tuned, and the replacement must be preregistered before use.**
