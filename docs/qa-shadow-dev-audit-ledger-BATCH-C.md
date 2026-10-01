# QA Shadow Dev Audit Ledger — Batch C

Round 0 Phase 2 semantic audit, Batch C: `qa-shadow-dev-61` … `qa-shadow-dev-90` (30 items).
Auditor: `round0-semantic-auditor-batchC` — model `openrouter/qwen/qwen3.8-27b:free`.
Corpus revision: `pilot-297-r1` (297 articles, 113,951 nodes).
Protocol: `docs/qa-semantic-audit-protocol.md` (primary check: Issue 2 sufficient-set
invariant — every `sufficient_set` must independently suffice; a conjunctive hop is ONE
set `[A,B]`, never `[A],[B]`). Every multihop/comparison item in the batch was audited,
not only the flagged ones.

**Token-mapping note:** Issue 2 set-merges (split conjunctive sets combined into one) are
recorded under the protocol token `repair-minimality` (set reconstruction); `relabel-multihop`
is reserved for items where a single atom independently determines the answer. Genuinely
different alternative sets recorded alongside are `repair-alternatives`. Top-level
`provenance.auditor` / `auditor_model` / `audit_decision` / `audit_rationale` /
`semantic_audit` fields follow the batch-A shadow-dev convention; `decision` /
`content_hash` / `verifier` remain `pending` / `""` / `tbd-independent-reviewer` (approvals
stay pending for the independent re-approval step — no self-approval).

Note: `qa-shadow-dev-60` does not exist (89 shadow-dev files total); it is outside this
batch's range and was not fabricated.

| ID | Verdict | Before → After Sets (node ids) |
|---|---|---|
| qa-shadow-dev-61 | repaired (sets-merged) | [p:virtual_reality:05:000],[p:cambridge_massachusetts:00:000] → [p:virtual_reality:05:000,p:cambridge_massachusetts:00:000] |
| qa-shadow-dev-62 | repaired (sets-merged + alternative recorded) | [p:virtual_reality:04:000],[p:cambridge_massachusetts:00:000] → [p:virtual_reality:04:000,p:cambridge_massachusetts:00:000], [p:virtual_reality:04:000,p:harvard_university:00:000] |
| qa-shadow-dev-63 | repaired (sets-merged) | [p:washington_state:00:000],[p:university_of_washington:00:000] → [p:washington_state:00:000,p:university_of_washington:00:000] |
| qa-shadow-dev-64 | repaired (multihop-relabeled) | is_multi_hop: true → false; question_type: multihop → factoid; reference_hop_chains & hop_glosses removed; [p:washington_state:00:000],[p:george_washington:00:000] → single sufficient set [p:george_washington:00:000] (atom contains "His namesakes include the national capital and the State of Washington" plus the answer — one atom determines it) |
| qa-shadow-dev-65 | repaired (sets-merged + alternative recorded) | [p:lincoln_motor_company:01:000],[p:abraham_lincoln:00:000] → [p:lincoln_motor_company:01:000,p:abraham_lincoln:00:000], [p:lincoln_motor_company:01:000,p:american_civil_war:02:000] |
| qa-shadow-dev-66 | repaired (sets-merged + alternative recorded) | [p:abraham_lincoln:01:000],[p:emancipation_proclamation:00:000] → [p:abraham_lincoln:01:000,p:emancipation_proclamation:00:000], [p:abraham_lincoln:01:000,p:emancipation_proclamation:00:001] |
| qa-shadow-dev-67 | repaired (multihop-relabeled) | is_multi_hop: true → false; question_type: multihop → factoid; reference_hop_chains & hop_glosses removed; [p:washington_d_c:00:000],[p:george_washington:00:000] → single sufficient set [p:george_washington:00:000] (same single-atom rationale as 64) |
| qa-shadow-dev-68 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-69 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-70 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-71 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-72 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-73 | repaired (alternative recorded) | [p:jaguar:00:000] → [p:jaguar:00:000], [p:jaguar:10:000] |
| qa-shadow-dev-74 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-75 | repaired (alternative recorded) | [p:atari_jaguar:00:000] → [p:atari_jaguar:00:000], [p:atari_jaguar:17:000] |
| qa-shadow-dev-76 | repaired (alternative recorded) | [p:lincolnshire:01:000] → [p:lincolnshire:01:000], [p:lincolnshire:00:000] |
| qa-shadow-dev-77 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-78 | repaired (alternatives recorded) | [p:american_civil_war:04:000] → [p:american_civil_war:04:000], [p:american_civil_war:00:000], [p:abraham_lincoln:15:000] |
| qa-shadow-dev-79 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-80 | repaired (alternative recorded) | [p:george_washington:00:000] → [p:george_washington:00:000], [p:george_washington:13:000] |
| qa-shadow-dev-81 | repaired (alternative recorded) | [p:university_of_washington:00:000] → [p:university_of_washington:00:000], [p:university_of_washington:04:000] |
| qa-shadow-dev-82 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-83 | repaired (alternative recorded) | [p:kyiv:00:000] → [p:kyiv:00:000], [p:kyiv:10:000] |
| qa-shadow-dev-84 | repaired (sets-merged) | [p:virtual_reality:06:000],[p:virtual_reality:08:000] → [p:virtual_reality:06:000,p:virtual_reality:08:000] |
| qa-shadow-dev-85 | repaired (sets-merged + alternative recorded) | [p:harvard_university:08:000],[p:university_of_washington:00:000] → [p:harvard_university:08:000,p:university_of_washington:00:000], [p:harvard_university:00:000,p:university_of_washington:00:000] |
| qa-shadow-dev-86 | repaired (sets-merged + alternatives recorded) | [p:washington_d_c:00:000],[p:washington_state:05:000] → [p:washington_d_c:00:000,p:washington_state:05:000], [p:washington_d_c:02:000,p:washington_state:05:000], [p:washington_d_c:00:000,p:washington_state:00:000] |
| qa-shadow-dev-87 | unchanged | ambiguous; two readings preserved |
| qa-shadow-dev-88 | unchanged | ambiguous; two readings preserved |
| qa-shadow-dev-89 | unchanged | unanswerable; empty sufficient_sets; absent_reason verified corpus-wide (Sensorama price absent) |
| qa-shadow-dev-90 | unchanged verdict, absent_reason repaired | unanswerable; empty sufficient_sets; absent_reason corrected — it had claimed the corpus discusses Carnot efficiency "only qualitatively", which is false: p:steam_engine:32:000 gives a theoretical Carnot efficiency of ~64% for a modern coal plant (a modern calculation, not Carnot's). No node gives a numerical efficiency computed by Carnot for his ideal engine; verdict stays unanswerable |

**Summary (30 items):**
- 12 items: approve unchanged — 68, 69, 70, 71, 72, 74, 77, 79, 82 (sufficient, minimal,
  well-grounded; all hard negatives confirmed non-answering with no evidence overlap),
  87, 88 (genuinely ambiguous, readings preserved), 89 (unanswerable, absence verified
  corpus-wide)
- 3 items: repaired (sets-merged) — 61, 63, 84 (Issue 2: conjunctive hops merged into one
  minimal set; multi-hop labels verified genuine — no single atom determines the answer)
- 5 items: repaired (sets-merged + alternative recorded) — 62, 65, 66, 85, 86 (Issue 2
  merge plus a genuinely different sufficient set recorded alongside)
- 7 items: repaired (alternative(s) recorded) — 73, 75, 76, 78, 80, 81, 83 (factoid sets
  left in place; corpus-wide scans found other passages that independently suffice)
- 2 items: repaired (multihop-relabeled) — 64, 67 (single atom `p:george_washington:00:000`
  independently determines the answer; relabeled multihop → factoid)
- 1 item: approve with `absent_reason` repaired for accuracy — 90 (verdict unchanged:
  unanswerable)
- 0 items: rejected

**Notes:**
- 86: the fourth possible combination `[p:washington_d_c:02:000, p:washington_state:00:000]`
  was considered and deliberately NOT recorded to avoid combinatorial set bloat; the three
  recorded sets cover the genuinely independent readings.
- 89/90 (unanswerable) carry no `semantic_audit` records (no sets/atoms to review) —
  consistent with the Phase 4 train unanswerable precedent.
- Source/evidence metadata updated where an alternative set introduced a new article:
  62 `source_articles += a:harvard_university`; 65 `source_articles += a:american_civil_war`
  with `evidence_groups = ["lincoln","solo:american civil war"]`; 78 `source_articles +=
  a:abraham_lincoln` with `evidence_groups = ["lincoln","solo:american civil war"]`.
- Candidates considered but NOT recorded as alternatives: `p:corona_beer:00:000` (no
  antitrust-transfer event stated), `p:university_of_washington:06:000` (no "U-Dub /
  public research" description), `p:washington_state:08:000` (no "state's highest elevation"
  description).
- All `node_id`s in the repaired sets resolve in `corpus/corpus.jsonl`
  (pilot-297-r1); every span text was rebuilt from the corpus so code-point equality holds.
  Preserved fields: `question_id`, `split: shadow_dev`, `meta.original_id`,
  `meta.exposure_note`, `provenance.author`/`author_model`.

**Verification:**
- Validator (run from repo root, copies of the 30 repaired files):
  `python3 -m data_tools.validate_qa --staging /tmp/opencode/batch-c/staging-final --corpus corpus/corpus.jsonl --split-map corpus/split_map.json`
  → `drafts: 30, approved: 0, errors: 118`, splits `shadow_dev: 30`, types
  `{ambiguous: 2, comparison: 3, factoid: 18, multihop: 5, unanswerable: 2}`.
- The 118 errors are ALL pre-existing classes, zero new structural errors
  (span-code-point, unknown-node, source-coverage, group-membership, and hard-negative
  checks all pass):
  - 58 × `set N span M evidence split != declared split` — `corpus/split_map.json` still
    maps the batches' evidence groups to retired `heldout` (owned by Phase 1/5, out of
    scope for this audit; `split_map.json` not edited)
  - 30 × `declared group split heldout != declared split shadow_dev` — same split-map cause
  - 30 × `missing or non-approve verification decision` — approvals are intentionally
    pending the independent re-approval step (no self-approval; `decision: pending`)
- Baseline (pristine 30 files, same command): 100 errors (40 span + 30 group + 30
  approval). The repair adds 18 span errors solely because newly recorded alternative sets
  also carry evidence atoms from the same split-mapped groups — no new defect class.
- Test suite: `python3 -m unittest discover -s tests` → `Ran 327 tests ... OK`
  (327 is the committed count; `docs/STATUS.md`'s 321 baseline predates the Phase 1 commit).
