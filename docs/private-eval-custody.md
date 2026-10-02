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
   `OVERLAP_CHAR_RATIO_THRESHOLD = 0.85`. Order-sensitive second signal for
   lightly edited copies. Set higher than the Jaccard threshold because
   character ratio is the noisier signal; 0.85 still requires a
   near-identical character sequence.

Deterministic, stdlib only, no network. Reasons are generic
("no question-level overlap detected" / "N record(s) flagged by
question-overlap rule"); only SYNTHETIC ids are returned.

## Seal protocol

Sealing occurs after every private item is independently reviewed and all
sufficient-set semantics are corrected. The seal is an opaque digest of
private bytes, readable by the main repository as a hash and never as
content. `substrate.private_eval.verify_seal()` raises (does not return
`False`) when no seal exists: absent is not a pass.
