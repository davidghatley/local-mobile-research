# QA Shadow Dev Audit Ledger — Batch B

| ID | Verdict | Before → After Sets (node ids) |
|---|---|---|
| qa-shadow-dev-31 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-32 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-33 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-34 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-35 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-36 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-37 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-38 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-39 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-40 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-41 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-42 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-43 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-44 | unchanged | sufficient_sets unchanged |
| qa-shadow-dev-45 | repaired (sets-merged) | [p:acid:02:000],[p:acid:03:000] → [p:acid:02:000,p:acid:03:000] |
| qa-shadow-dev-46 | repaired (sets-merged) | [p:gda_sk:00:000],[p:zurich:00:000] → [p:gda_sk:00:000,p:zurich:00:000] |
| qa-shadow-dev-47 | unchanged | sufficient_sets unchanged (single atom contains both compared facts) |
| qa-shadow-dev-48 | repaired (sets-merged) | [p:superconductivity:01:000],[p:superconductivity:05:000] → [p:superconductivity:01:000,p:superconductivity:05:000] |
| qa-shadow-dev-49 | repaired (multihop-relabeled) | is_multi_hop: true → false; question_type: multihop → factoid; reference_hop_chains & hop_glosses removed; single sufficient set [p:jaguar_cars:00:000] retained |
| qa-shadow-dev-50 | unchanged | genuine multihop; sufficient_sets [p:coronavirus:01:000,p:corona_australis:00:000] intact |
| qa-shadow-dev-51 | unchanged | genuine multihop; sufficient_sets [p:emancipation_proclamation:00:000,p:lincoln_motor_company:01:000] intact |
| qa-shadow-dev-52 | unchanged | genuine multihop; sufficient_sets [p:mount_vernon:07:000,p:george_washington:04:000] intact |
| qa-shadow-dev-53 | repaired (multihop-relabeled) | is_multi_hop: true → false; question_type: multihop → factoid; single sufficient set [p:harvard_university:08:000] retained (atom independently determines 209-acre answer) |
| qa-shadow-dev-54 | unchanged | genuine multihop; sufficient_sets [p:university_of_cambridge:00:000,p:cambridge_massachusetts:00:000] intact |
| qa-shadow-dev-55 | unchanged | genuine multihop; sufficient_sets [p:fifa_world_cup:02:000,p:fifa_world_cup:02:001] intact |
| qa-shadow-dev-56 | unchanged | genuine multihop; sufficient_sets [p:university_of_washington:04:000,p:university_of_washington:00:000] intact |
| qa-shadow-dev-57 | unchanged | ambiguous; two readings preserved (1758 vs 1922) |
| qa-shadow-dev-58 | unchanged | ambiguous; two readings preserved (1791 vs 1853) |
| qa-shadow-dev-59 | unchanged | unanswerable; empty sufficient_sets; absent_reason documented |

**Summary:**
- 14 items: unchanged (no structural defects)
- 3 items: repaired (sets-merged) — comparison items where alternative-singleton sufficient sets were merged into single conjunctive sets (qa-shadow-dev-45, qa-shadow-dev-46, qa-shadow-dev-48)
- 2 items: repaired (multihop-relabeled) — inflated multi-hop labels removed where a single atom independently determines the answer (qa-shadow-dev-49, qa-shadow-dev-53)
- 0 items: rejected
- 2 items: ambiguous (qa-shadow-dev-57, qa-shadow-dev-58) — preserved as-is with readings field
- 8 items: genuine multihop (qa-shadow-dev-50 through 56, minus 53 which was relabeled)
- 1 item: unanswerable (qa-shadow-dev-59)

All 29 items now carry provenance audit fields `{auditor, auditor_model}` in `provenance`. Every `node_id` in `sufficient_sets` exists in `corpus/corpus.jsonl` (verified via grep).