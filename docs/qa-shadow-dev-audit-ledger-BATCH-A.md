# QA Shadow-Dev Semantic Audit — Ledger BATCH-A (items 01–30)

Auditor: `round0-semantic-auditor-batchA` / `opencode/muse-spark-1.3-contributor-free`
Corpus revision: `pilot-297-r1` (all node_ids grepped against `corpus/corpus.jsonl`; all exist).
Protocol: `docs/qa-semantic-audit-protocol.md`. Provenance: `decision` stays `pending`
(schema vocab forbids `repaired`/`rejected` there); audit outcome recorded in
`provenance.audit_decision` + `provenance.semantic_audit` (closed decision tokens,
reviewer != author). No nested spawning; no paid endpoints.
Pre-existing staging-wide validator errors (split-map `heldout` residue from the
Issue 1 reclassification + pending approvals) are orchestrator scope and untouched;
this batch introduces zero new validator errors (one pre-existing split error on
item 24 resolved by its repair).

## Verdicts

| id | verdict | before → after sufficient_sets |
|---|---|---|
| qa-shadow-dev-01 | unchanged | [p:cambridge:00:000] → same |
| qa-shadow-dev-02 | unchanged | [p:cambridge_massachusetts:00:000] → same |
| qa-shadow-dev-03 | unchanged | [p:harvard_university:00:000] → same |
| qa-shadow-dev-04 | unchanged | [p:solar_corona:00:000] → same |
| qa-shadow-dev-05 | unchanged | [p:corona_beer:00:000] → same |
| qa-shadow-dev-06 | unchanged | [p:corona_australis:00:000] → same |
| qa-shadow-dev-07 | unchanged | [p:jaguar:00:000] → same |
| qa-shadow-dev-08 | unchanged | [p:jaguar_cars:00:000] → same |
| qa-shadow-dev-09 | unchanged | [p:jaguar_supercomputer:00:000] → same |
| qa-shadow-dev-10 | unchanged | [p:lincolnshire:02:001] → same |
| qa-shadow-dev-11 | unchanged | [p:mount_vernon:00:000] → same |
| qa-shadow-dev-12 | unchanged | [p:washington_d_c:00:000] → same |
| qa-shadow-dev-13 | unchanged | [p:university_of_washington:00:000] → same |
| qa-shadow-dev-14 | unchanged | [p:oymyakon:00:000] → same |
| qa-shadow-dev-15 | unchanged | [p:mary_celeste:00:000] → same |
| qa-shadow-dev-16 | unchanged | [p:saola:00:000] → same |
| qa-shadow-dev-17 | unchanged | [p:dead_sea:00:000] → same |
| qa-shadow-dev-18 | unchanged | [p:harvard_university:08:000, p:harvard_university:09:000] → same |
| qa-shadow-dev-19 | unchanged | [p:university_of_cambridge:00:000, p:harvard_university:00:000] → same |
| qa-shadow-dev-20 | unchanged | [p:cambridge_massachusetts:00:000, p:university_of_cambridge:00:000] → same |
| qa-shadow-dev-21 | unchanged | [p:washington_state:01:000, p:george_washington:01:000] → same |
| qa-shadow-dev-22 | unchanged | [p:emancipation_proclamation:00:000, p:abraham_lincoln:01:000] → same |
| qa-shadow-dev-23 | unchanged | [p:american_civil_war:02:000, p:lincoln_motor_company:01:000] → same |
| qa-shadow-dev-24 | repaired+multihop-relabeled | [p:coronavirus:01:000, p:coronavirus:02:001] → [p:coronavirus:02:001] (type multihop→factoid, chain+gloss removed) |
| qa-shadow-dev-25 | unchanged | [p:atari_jaguar:00:000, p:atari_jaguar:03:000] → same |
| qa-shadow-dev-26 | unchanged | [p:cambridge_massachusetts:00:000, p:george_washington:00:000] → same |
| qa-shadow-dev-27 | unchanged | [p:corona_beer:01:000], [p:corona_australis:01:000] → same |
| qa-shadow-dev-28 | unchanged | [p:cambridge:00:000], [p:cambridge_massachusetts:00:000] → same |
| qa-shadow-dev-29 | unchanged | [] → same (absence re-verified) |
| qa-shadow-dev-30 | unchanged | [] → same (absence re-verified) |

## Notes

- No conjunctive-split defect found in this batch: every multi-atom sufficient set
  is already a single joint set (no `[A],[B]` singleton splits to merge).
- Item 24 repair: `p:coronavirus:02:001` alone places Almeida at St Thomas' Hospital
  collaborating with Tyrrell, determining the answer; `p:coronavirus:01:000`
  (coining) is corroboration only. Leave-one-out: removing 02:001 breaks the route;
  removing 01:000 does not. Relabeled multihop→factoid per protocol §2.
- Items 25/26 kept multihop: the second-hop passages carry no release-date /
  Cambridge-Common mention respectively (verified full text), so neither singleton
  determines the answer. Item 20/21/22/23 likewise genuine (bridge entity unfixed
  without hop 1; answer absent without hop 2).
- Negatives spot-checked full-text for all 30 (highest-risk: GW:04/GW:06 for
  river/years, atari_jaguar:04:000 for price, lincoln_motor_company:03:000 for
  namesake): none answer their question.
- Item 29 absence: launch-price slot blank corpus-wide (`p:atari_jaguar:02:000`
  "launched on November 23, 1993, at ,"); only other price statements are a
  redacted 1995 drop, an unquantified "low price point", and 2001 UK resale.
  Item 30 absence: sole wildfire node `t:moai:15:000:12` states "unknown number".
- 0 rejected. 0 routes added (no missed genuine alternatives found).
