# Round 0 Repair Run — Final Status

Authoritative status as of **2026-10-01**. Supersedes earlier status claims; see
`docs/progress-ledger.md` and `docs/orchestration-log.md` for full history.

## Verdict: NOT FROZEN

The common substrate is repaired, adversarially reviewed, and independently
re-verified. **The controlled evaluation set is not complete**, so no freeze is possible.

| Head | `688c779` |
|---|---|
| Verified controlled set | 120 items (60 train + 60 dev), all independently approved |
| Held-out | 89 authored, **0 independently verified**, not sealed |
| Freezes blocked by | held-out verification + sealing |

## Repaired and independently reviewed

| Blocker | State | Evidence |
|---|---|---|
| 1 evidence granularity | REPAIRED | derived support index; ancestry-aware support; leaf beats parent on precision/tokens; `docs/round0-review-evidence-semantics.md` PASS |
| 2 one score kind per trace | REPAIRED | per-stage `score_kind` + per-stage policy; `model_probability` is first-class and bounded | 
| 3 minimal sufficient sets | REPAIRED | leave-one-out protocol; all 70 original drafts audited |
| 4 genuine multi-hop | REPAIRED | only **2 of 10** original multihop labels were genuine |
| 5 one-group restriction | REPAIRED | same-split cross-group allowed; leakage prevention not weakened |
| 6 held-out too small | **PARTIAL** | 89 authored (target 120) — but unverified, so no gain yet |
| 7 two regimes | REPAIRED | Regime A (primary) + Regime B machine-readable; cross-regime aggregation refused |
| 8 sufficiency/abstention | REPAIRED | `EvidenceDecision`; generator provably not invoked on abstain |
| 10 storage honesty | REPAIRED | missing artifact → `total_bytes: null`, never a plausible total |
| 11 memory peak | REPAIRED | `VmHWM` peak vs `VmRSS` point, distinct; magnitude heuristic deleted |
| 13 one-command verify | REPAIRED | `scripts/verify_round0`; exits 1 honestly; CI never downloads the 986 MB model |
| 9 scale corpus | PARTIAL | tier 1 built: 940 articles (830 substantive), 38 tests pass |
| 12 stale docs | REPAIRED | `docs/STATUS.md` + docstring + protocol status corrections |

Blockers **3 and 4** were the substantive scientific findings; 6, 9 and 12 remain open.

## Controlled dataset (MEASURED)

```
drafts 209 | approved 120 | pending 89
splits   train 60 | dev 60 | heldout 89 (unverified)
types    factoid 123 | multihop 38 | comparison 20 | ambiguous 15 | unanswerable 13
```

Of the **verified 120**: all 50 new dev drafts were audited in five independent
batches (42 approve, 8 repaired, 0 rejected). **All 14 claimed dev multi-hop items
verified genuine** — no single atom determines the answer. The 60 train items were
audited in Phase 4 (59 approve, 11 repaired, 0 rejected).

## Honest statement of what is NOT established

- The 89 held-out drafts are **authored but unverified**. No independent reader has
  applied the leave-one-out test to them. They must not be sealed in this state.
- Held-out is 89 of a 120 target. The batch-3 author reported the corpus is
  tightening: rich paragraphs are now self-sufficient and natural cross-article
  chains are nearly exhausted. **A documented shortfall is preferred over weak items.**
- `qa-heldout-60.json` was accidentally deleted by an author and re-authored; the
  second attempt produced garbled output and did **not** create the file. It is
  genuinely missing. Ids 01–59 and 61–90 exist.
- Scale tier 1 is 940 articles, not the ~1000 target. `revid` is null in all 940
  snapshots (fetcher omitted `ids` from `rvprop`), so attribution rests on
  `source_url` + timestamp + content hash.
- Test counts prove **structure only**. They cannot establish semantic QA correctness.

## My own process failures (recorded, not hidden)

1. **No held-out drafts were committed to git** until batch 3 was done. When an author
   deleted `qa-heldout-60.json` it was unrecoverable. Now tracked; only the *sealed
   labels file* stays out of the repo.
2. **Commit `814dcc1` overstated the scale layer** — its message said the fetcher was
   not written, when both scripts existed and 940 snapshots had been fetched.
3. **The dev repair ledger was self-contradictory** for `qa-dev-40`: it said drop a
   redundant atom *and* record the minimal set as an alternative, which duplicated one
   route. Collapsed by ruling.
4. **`scripts/parse_semantic_audit.py` first over-reported** 61 drafts needing repair
   because it missed a decision format; corrected to the true 11.

## Every recorded failure and overturned claim

- Nemotron 3.5 Lightning reference-audit worker completed silently with no artifact → substituted.
- Reviewer Q9 rejection claimed nonexistent node ids → **overturned** by direct corpus check; the claimed "correct" ids did not exist.
- Mis-serialized `draft_content_hash` (reviewers reimplemented it) → fail-closed binding stopped it; root cause was that `hard_negatives[*].reviewed` sits inside the semantic hash.
- Verifier worker found a real `UnboundLocalError` (`groups_raw`) in `manifest.py` → confirmed and fixed.
- Binding worker **refused** 4 reviewer-proposed "alternative sets" that were only ancestor/descendant or granularity variants → correct, preserved.
- `test_measure_storage_missing_path_is_zero` enshrined the BLOCKER 10 bug → rewritten.
- Worker failures this session: three 504/503/502 upstream timeouts, one `Nemotron 3.5 Lightning` garbled-output failure.
- Batch-3 author deleted `qa-heldout-60.json` via an over-broad glob.

## Code verification

```
python3 -m unittest discover -s tests              → 321 OK
python3 -m unittest discover -s data_tools/tests   →  77 OK
python3 -m unittest discover -s corpus/tests       →  17 OK
python3 -m unittest discover -s corpus/scale/tests →  38 OK
./scripts/verify_round0                            → exit 1 (held-out artifacts absent)
```

`verify_round0` exits 1 with 6 stages PASS and 3 FAIL. The failures are missing
artifacts (`questions.json`, sealed labels, `regime_b_excluded_articles.json`), not
defects. It prints, by design, that no pass it emits implies semantic QA correctness.

## Next required steps to reach a freeze candidate

1. Independently verify all 89 held-out drafts (leave-one-out + single-atom test).
2. Repair and re-approve, as with the other sets.
3. Author `qa-heldout-60.json`.
4. Decide whether to top up held-out toward 120 or seal at 89 with the shortfall documented.
5. Emit `corpus/regime_b_excluded_articles.json`.
6. Seal via the custodian path; run `validate_freeze` against real artifacts.
7. Independent final freeze review by a reviewer who implemented none of this.