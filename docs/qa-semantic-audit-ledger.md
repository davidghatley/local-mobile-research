# Phase 4 Semantic Audit — Repair Ledger

Orchestrator adjudication after two independent second-reader passes over all 70 approved drafts.
Audit protocol: `docs/qa-semantic-audit-protocol.md`. Reports: `docs/qa-semantic-audit-pass1.md`
(multihop + comparison), `docs/qa-semantic-audit-pass2.md` (factoid + unanswerable + ambiguous).
Parser: `scripts/parse_semantic_audit.py`.

## Totals

| Outcome | Count |
|---|---|
| Drafts audited | 70 of 70 |
| approve (unchanged) | 59 |
| needs repair | 11 |
| reject-replace | 0 |

No draft was rejected outright. All defects are repairable in place; no item is deleted.

## Genuine multi-hop finding

Of 10 drafts labeled `multihop`, only **2 are genuine** (qa-train-05: Jobs→Pixar→Apple
entity chain; qa-train-32: cross-article Guido→Monty Python chain).

**8 carry an inflated label** — the question pre-states the bridging premise, so a single
support atom already determines the answer. A multi-hop label here means "quoted more than
one passage", which is exactly the failure mode BLOCKER 4 describes. These must be
relabelled, not quietly retained.

## Repair list (11)

### relabel-multihop (6) — question pre-states the bridge; single atom suffices
Drop `is_multi_hop`, remove `reference_hop_chains`, set `question_type` to `factoid`.

| Draft | Finding |
|---|---|
| qa-pilot-dev-03 | Both atoms in one article; question supplies the link. |
| qa-train-14 | {t:lunar_eclipse:00:000:00, :01} — single atom answers. |
| qa-train-24 | Single atom answers. |
| qa-train-36 | Single atom answers. |
| qa-train-09 | Only t:columbia_university:00:000:00 needed; chain premises given. |
| qa-train-44 | Single atom answers. |

### repair-minimality (3) — a sufficient set contains a redundant atom
Remove the redundant atom; re-verify the remaining set is minimal under leave-one-out.

| Draft | Redundant atom | Why redundant |
|---|---|---|
| qa-train-42 | p:seashell:11:000 | Question's first clause is a verbatim restatement of it; p:seashell:01:000 alone yields "conchology". ALSO needs relabel-multihop. |
| qa-train-21 | (audit-specified) | Non-minimal 2-atom set. |
| qa-train-44 | (audit-specified) | Non-minimal set. |

### repair-alternatives (3) — genuine independent support sets were missed
Add the alternative sufficient set. Alternatives are ENCOURAGED and must never be collapsed.

| Draft | Alternative to record | Caution |
|---|---|---|
| qa-train-28 | {t:k2:03:000:00} ("height given on maps... is 8611 metres") | Use the SENTENCE atom, NOT parent p:k2:03:000, whose continuation cites a conflicting 8609.02 m figure. |
| qa-pilot-dev-09 | {p:gorilla:08:000} to reading 0; {p:chimpanzee:10:000} to reading 1 | |
| qa-train-02 | {p:amazon_company:00:000} to reading 0 | t:amazon_company:00:000:01 is its sentence child (descendant, not distinct) — do NOT record. |

## Approved without change (59)

Includes all 5 unanswerable (absence claims verified corpus-wide, not by sampling), 4 of 6
ambiguous, 41 of 42 factoid, and 7 comparison / 2 multihop.

Two non-blocking findings recorded without a draft change:
- qa-train-30: one immaterial gloss imprecision in `absent_reason` (an AMS study is
  mislabeled). The absence claim itself is verified correct.
- qa-pilot-dev-05: `meta.group=java` with sources spanning borneo + java is **VALID** under
  the new same-split cross-group rule (both articles carry `split_group="java"`), and both
  atoms are genuinely necessary. Approved.

## Ruling on approval integrity

Semantic repairs legitimately invalidate and reissue approvals. The existing content-hash
machinery enforces this and must NOT be weakened or bulk-bypassed. Each repaired draft must:
1. have its content changed only as the audit specifies;
2. fail its stale-approval check until an independent reviewer re-verifies it;
3. receive a fresh approval bound to the NEW content hash;
4. record the semantic audit provenance (decision token, reviewer identity/model,
   corpus revision) in `provenance.semantic_audit`.

No draft retains an approval merely because it previously had one.

## After repairs

Re-run: `python3 -m data_tools.validate_qa --staging staging --corpus corpus/corpus.jsonl
--split-map corpus/split_map.json` and require 0 errors, plus the shared and data-tools suites.
A second independent reader must verify each repair; the author may not self-approve.