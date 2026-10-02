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
It returns only:

```
{"verdict": "PASS" | "REJECT", "reason": ..., "flagged_ids": [synthetic training ids]}
```

It never returns the matched private question id, private text, private
answer, or private evidence. It **fails closed**: with no seal present the
verdict is `REJECT` with an explicit reason, never `PASS` on missing data.

## Seal protocol

Sealing occurs after every private item is independently reviewed and all
sufficient-set semantics are corrected. The seal is an opaque digest of
private bytes, readable by the main repository as a hash and never as
content. `substrate.private_eval.verify_seal()` raises (does not return
`False`) when no seal exists: absent is not a pass.
