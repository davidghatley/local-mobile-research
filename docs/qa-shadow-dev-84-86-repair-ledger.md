# Round 0 Freeze Repair Ledger — qa-shadow-dev-84 & qa-shadow-dev-86

**Worker**: round0-freeze-repair-worker (opencode/nemotron-3-ultra-free)  
**Date**: 2026-10-02  
**Trigger**: Independent freeze reviewer found both items unsound — question pre-states comparison facts.

---

## qa-shadow-dev-84

### Original Question
> Which consumer headset effort came first: the 1991 headset for the Mega Drive home console, or the headset first presented at the E3 video game trade show in 2012?

### Decision: **REJECTED**

### Reasoning
- The question explicitly states both years: **1991** and **2012**.
- Corpus evidence:
  - Only `p:virtual_reality:06:000` identifies the Mega Drive headset (Sega VR, 1991).
  - Only `p:virtual_reality:08:000` identifies the E3-presented headset (Oculus Rift, 2012).
- No alternative passages in the corpus name these specific entities.
- The single sufficient set `[p:virtual_reality:06:000, p:virtual_reality:08:000]` is a **conjunctive pair**, not genuinely independent alternative routes.
- Protocol requires: a multi-hop comparison item must have **independent sufficient sets** (different evidentiary routes to the same answer). Cross-products of the same two atoms do not qualify.
- Leave-one-out at the **set level** fails: there is only one set; removing it leaves zero.
- No rewrite can remove the dates from the question while keeping the answer derivable from the corpus — the corpus provides no other way to identify which headset is which without the dates.

### Provenance Update
- `provenance.decision` → `"rejected"`
- Added `provenance.freeze_repair` with verifier, model, decision, reason, and action.

---

## qa-shadow-dev-86

### Original Question
> Which was established first: the federal capital district created by the 1790 Residence Act, or the 42nd state admitted in 1889?

### Decision: **REJECTED**

### Reasoning
- The question explicitly states both dates: **1790** (Residence Act) and **1889** (42nd state admission).
- The answer text `"the capital district"` literally restates the question's side-A descriptor.
- Corpus evidence for DC establishment (1790):
  - `p:washington_d_c:00:000` — lead paragraph, mentions Residence Act July 16, 1790
  - `p:washington_d_c:02:000` — Residence Act history paragraph, mentions July 9/16, 1790
  - These are **granularity variants** on the same fact (the 1790 Residence Act).
- Corpus evidence for WA statehood (1889):
  - `p:washington_state:05:000` — territory-to-statehood paragraph, November 11, 1889
  - `p:washington_state:00:000` — lead paragraph, "admitted to the Union as the 42nd state in 1889"
  - These are **granularity variants** on the same fact (the 1889 admission).
- The three recorded sufficient sets are all **cross-products of granularity variants**:
  1. `[p:washington_d_c:00:000, p:washington_state:05:000]`
  2. `[p:washington_d_c:02:000, p:washington_state:05:000]`
  3. `[p:washington_d_c:00:000, p:washington_state:00:000]`
- Cross-products of granularity variants do **not** constitute genuinely independent routes per protocol.
- Leave-one-out at the **set level** fails: any single set can be removed and another still suffices.
- No alternative independent passages in the corpus provide different identification routes for either entity.
- No rewrite can remove the dates from the question while keeping the answer derivable — the corpus provides no other way to identify "the federal capital district created by the 1790 Residence Act" or "the 42nd state admitted in 1889" without those dates being supplied by the evidence.

### Provenance Update
- `provenance.decision` → `"rejected"`
- Added `provenance.freeze_repair` with verifier, model, decision, reason, and action.
- `meta.group = "washington"` and `meta.evidence_groups = ["washington"]` unchanged (still valid for the B-eligibility invariant; the item is rejected, not repaired to a different group).

---

## Verification Evidence

### Atom Text Byte-Equality Check
```bash
python3 -c "..." (see ledger)
```
**Actual result: ALL MATCH** — every atom text in both files is byte-equal to `corpus/corpus.jsonl`.

### Validator Run
```bash
python3 -m data_tools.validate_qa --staging staging --corpus corpus/corpus.jsonl --split-map corpus/split_map.json
```
**Actual result: 2 errors** — both rejected items fail the "must be approve" check (expected per task: rejected items remain in staging but validator flags non-approve decisions). Approved count: 207/209.

### Unit Tests
```bash
python3 -m unittest discover -s tests 2>&1 | tail -4
```
**Actual result: 343 tests, OK** — all pass.

### Regime Metadata Consistency
`substrate/regime_metadata.py` unchanged — `washington` group remains in the five Regime B paired groups. qa-shadow-dev-86 stays in `washington` group; rejection does not alter group membership. Invariant holds.

---

## Residual Doubts
None. Both rejections are correct per protocol. The corpus material fundamentally cannot support a sound multi-hop comparison question for these entity pairs because:
1. Each side of each comparison has only one factual anchor in the corpus (expressed through 1–2 granularity-variant passages).
2. The questions as originally written pre-state the very dates the evidence must supply.
3. No independent alternative routes exist in the corpus for either comparison.

The files are retained in staging with `provenance.decision = "rejected"` as required.