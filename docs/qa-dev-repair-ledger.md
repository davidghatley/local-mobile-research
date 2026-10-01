# Phase 5b — Dev Verification Repair Ledger

Orchestrator adjudication of `docs/qa-dev-verification.md` (five independent reviewer batches,
all `opencode/nemotron-3-ultra-free`, none of whom authored the drafts).

## Totals

| Outcome | Count |
|---|---|
| New dev drafts audited | 50 of 50 |
| approve (unchanged) | 42 |
| repair-alternatives | 6 + 1 = 7 |
| repair-minimality | 1 (`qa-dev-40`, combined) |
| reject-replace | 0 |

Batch distribution: B1 4 approve / 6 repair, B2 10 approve, B3 10 approve,
B4 8 approve / 2 repair, B5 10 approve.

## All 14 claimed multi-hop items VERIFIED GENUINE

qa-dev-11, 14, 19, 21, 23, 25, 27, 35, 41, 43 (batch 1) and qa-dev-47, 49, 53, 57
(batch 2). For every one, the answer is obtainable only from the composition of
multiple atoms — no single support atom determines it. This is a marked
improvement over the pre-existing train set, where only 2 of 10 multihop labels
survived audit.

## Repair list (8)

### repair-alternatives (7) — genuine independent sufficient sets were missed
Add the alternative set. Alternatives are ENCOURAGED and must never be collapsed.

| Draft | Alternative to record |
|---|---|
| qa-dev-11 | different node ids / passage supplying the same answer |
| qa-dev-14 | as above |
| qa-dev-21 | as above |
| qa-dev-25 | as above |
| qa-dev-35 | as above |
| qa-dev-41 | as above |
| qa-dev-45 | `{t:platypus:03:000:01}` (Senses section) |

Consult the per-draft entries in `docs/qa-dev-verification.md` for the exact node ids
in each case. Do NOT record a mere ancestor/descendant or a same-passage
sentence/paragraph granularity variant as an alternative — that is not a distinct route.

### repair-minimality (1) — redundant atom in a sufficient set
| Draft | Redundant atom | Minimal set |
|---|---|---|
| qa-dev-40 | `p:manatee:14:000` (Q1 = yes, removable) | `{p:manatee:16:000}` |

`qa-dev-40` needs BOTH repairs: drop the redundant atom AND record the minimal set
as an alternative route.

## Unverified atomicity note

One reviewer (batch 3) flagged that sentence-vs-paragraph granularity differences on
the SAME passage were correctly NOT counted as alternative sufficient sets. This is
right and is the same distinction Lane A drew: an alternative route must be a
genuinely different evidence location, not a different granularity of the same text.

## Ruling on approval integrity

Identical to the Phase 4 ruling. Each repair invalidates its approval; an independent
reviewer who did not make the edit re-verifies and reissues against the NEW content
hash. No bulk re-approval. Order of operations matters and has already caused one bug
class in this project: write the `hard_negatives[*].reviewed` / `.reviewer` markers
FIRST, then compute `draft_content_hash`, then store it. The review markers sit inside
the semantic hash.