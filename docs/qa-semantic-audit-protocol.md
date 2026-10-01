# QA Semantic Audit Protocol (Round 0)

Status: **PROTOCOL + TOOLING ONLY. NOT EXECUTED.** No draft has been
audited under this protocol yet. The 70 staging drafts predate it and
validate under migration grace (no `meta.semantic_status`, no
`evidence.hop_glosses`, no `provenance.semantic_audit` required); they
will be audited — and where necessary repaired and re-approved — in
Phase 4, before any atomization migration.

Owner: Lane D (same worker as `data_tools/qa_schema.py`,
`data_tools/verify.py`, `substrate/splits.py` gating, and
`docs/qa-construction-protocol.md`).

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit,
verified zero-cost catalog entry). No nested spawning.

## 0. What code enforces vs what humans decide

Code enforces STRUCTURE and PROVENANCE only:

- `meta.evidence_groups`: present (once `meta.semantic_status` is set),
  a sorted distinct string list, includes the primary `meta.group`.
  Corpus coverage of the actual evidence articles is machine-checked in
  `data_tools/verify.py` (same-split rule).
- `evidence.hop_glosses`: present and chain-aligned for audited
  multi-hop drafts (structural check only).
- `provenance.semantic_audit`: every record carries all required fields,
  `leave_one_out_answerable` is `yes`/`no`, `decision_token` is in the
  closed vocabulary, reviewer differs from author, `corpus_revision` is
  present.

Code NEVER auto-decides sufficiency, minimality, or answerability. Any
implementation that tries to prove semantic necessity by
substring/overlap heuristics is FORBIDDEN: it leaks answer text into
ground truth and biases the tournament toward lexical architectures.
Scaffolds and templates leave `semantic_audit` pending/absent; tooling
never populates an approval.

## 1. Reviewer question template

For each sufficient set S, and for each atom x in S, the reviewer
answers in writing (recorded as `necessity_note` plus the
`leave_one_out_answerable` vote):

- **Q1 SUFFICIENCY.** Does S \ {x} — the set with x removed — still
  determine the answer? If yes, x is not necessary in this set.
- **Q2 NECESSITY.** What inferential work does x do? Name it (e.g.
  "supplies the bridge entity", "supplies the final property"), or write
  NONE with one of: redundant (entailed by the rest of S), setup
  (background the question already gives), duplicate (same proposition
  as another atom in S).
- **Q3 ALTERNATIVES.** Is there a genuinely different sufficient set —
  different node ids, not a re-phrasing of the same passage — that also
  determines the answer? If yes, record it as an additional sufficient
  set. Alternatives are encouraged, never collapsed.

Then DECISION, one closed-vocabulary token per audited set/atom:

- `approve` — S is sufficient and minimal; multi-hop label (if any) is
  genuine.
- `repair-minimality` — drop the redundant/setup/duplicate atom(s), or
  re-atomize an atom that internally carries answer + setup, then
  re-verify and re-approve.
- `repair-alternatives` — a genuinely different sufficient set exists
  and must be recorded alongside, then re-verify and re-approve.
- `relabel-multihop` — the question is answerable from a single atom;
  drop the multi-hop label (or vice versa: the chain is real but the
  label is missing), then re-verify and re-approve.
- `reject-replace` — the set cannot be repaired (ungrounded, tautological,
  leaked); discard the draft and write a replacement.

Semantic repairs change draft content, so existing content-hash approvals
are legitimately invalidated: the author and verifier re-approve the
repaired bytes. No bulk re-approval is ever permitted.

## 2. Single-atom answerability test (genuine multi-hop)

A multi-hop label is genuine iff NO single atom in any sufficient set
determines the answer on its own: for every atom x, the Q1 vote must be
`leave_one_out_answerable: no` for at least one removed atom per
reasoning step — i.e. removing any hop breaks the chain. If one atom
alone determines the answer, the draft is `relabel-multihop`.

Qualifying hop patterns (non-exhaustive; the reviewer judges, code does
not):

- cross-article entity linking (A names X, B says X did Y);
- entity discovery (first hop finds WHO/WHAT, second hop its property);
- relation chaining (X -> relation -> Y -> relation -> Z);
- disambiguation-then-lookup (first hop fixes which entity, second hop
  answers about it);
- location -> entity -> property;
- person -> organization -> event;
- work -> creator -> location.

Each chain entry carries a `hop_gloss` stating the distinct inferential
relation that hop contributes. The gloss is a structural requirement;
whether the hop is genuine is the reviewed judgment above.

## 3. Difficulty discipline

Difficulty must come from evidence composition — more hops, confusable
entities, distant passages — never from vague wording. A question the
reviewer can only answer by guessing what it asks for is
`repair-minimality` (rewrite the question) or `reject-replace`, never an
approved hard item.

## 4. Two passes and adjudication

Questionable items (any `repair-*`, `relabel-multihop`, or
`reject-replace` vote, or reviewer uncertainty on Q1–Q3) require TWO
independent reviewer passes with distinct reviewer identities. If the
passes disagree, the orchestrator adjudicates by inspecting the corpus
text behind the cited node ids directly — never by re-running a
heuristic, never by majority vote of model outputs.

## 5. Record shape

Each `provenance.semantic_audit` record:

```json
{
  "set_index": 0,
  "atom_node_id": "t:example:00:000:00",
  "leave_one_out_answerable": "no",
  "necessity_note": "supplies the bridge entity",
  "decision_token": "approve",
  "reviewer_id": "reviewer-person-or-model",
  "reviewer_model": "exact-model-string",
  "corpus_revision": "pilot-297-r1",
  "reviewed_utc": "2026-01-01T00:00:00+00:00"
}
```

`reviewer_id` must differ from `provenance.author`. `corpus_revision`
pins the exact corpus the reviewer read. Absent `semantic_audit` means
audit pending — never approved-by-default.
