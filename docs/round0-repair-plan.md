# Round 0 Repair — PHASE 1 Design Adjudication

Orchestrator ruling after six independent free-model design lanes against HEAD `b38a457`.
Phase 1 produced designs only; no implementation yet.

## Accepted designs (with rulings)

### Lane A — Evidence semantics / support atoms (Muse Spark Free)
Accepted in principle: ancestry-aware support satisfaction via a derived leaf-set index,
canonical minimal leaf-sentence support atoms, support satisfaction kept strictly separate
from context precision / token cost.

Rulings:
- **ACCEPT** no corpus schema change. `CorpusNode` stays frozen; add a derived support index.
- **ACCEPT** the two-channel split. A parent-paragraph return MUST satisfy support while
  being separately penalized on precision and tokens. Never feed ancestry-expanded ids into
  precision inputs.
- **ACCEPT** rejection of `p:`/`s:`/`a:` atoms in *sealed* sufficient sets, with a staging
  grace flag during migration.
- **REJECT** the suggestion to add char offsets to `CorpusNode`. Derive offsets in the index.
- **REJECT** any automated `p:` -> minimal `t:` atom selection. Minimal-atom choice is a
  sufficiency judgment; an overlap heuristic would leak answer text into ground truth and
  bias the tournament toward lexical architectures. Automation may *propose* candidates only.

### Lane B — Per-stage score kinds (Nemotron Ultra Free)
Accepted: per-stage `score_kind`, per-stage `threshold_policy`, per-stage model identity,
raw scores preserved, legacy flat traces migrated explicitly.

Rulings:
- **ACCEPT** dropping the global top-level `score_kind`; every stage validates its own scores
  and its own policy.
- **REJECT** adding a *required* `model_identity` to internal `StageRecord` in `types.py`
  with a fabricated `"legacy-unknown"` default. Silent provenance fabrication is exactly the
  failure class this project exists to prevent. `model_identity` is required in the *wire
  trace* only; internal telemetry stays untouched. A legacy trace that cannot supply a model
  identity must fail closed rather than be assigned a placeholder.
- **ACCEPT** legacy migration, but it must be an explicit, tested, recorded transform — not a
  silent fallback inside `validate_trace`.

### Lane C — Abstention / storage / memory (Muse Spark Free)
Accepted: first-class `EvidenceDecision`, a shared `run_question` gate that skips the
generator on abstain, fail-closed storage totals, `VmHWM` peak RSS, and platform dispatch
replacing the `ru_maxrss` magnitude heuristic.

Rulings:
- **ACCEPT** the minimal safe floor: zero-span packet -> insufficient/abstain. This is an
  interface floor, not a tuned sufficiency model.
- **ACCEPT** `decision == insufficient` iff `generation_action == abstain`, enforced fail-closed.
- **ACCEPT** reason codes distinguishing `zero-spans` from `over-budget-empty`, so a packing
  failure is never misread as a retrieval decision.
- **ACCEPT** replacing the >1e9 magnitude heuristic with explicit `sys.platform` dispatch.
- **ACCEPT** updating `tests/test_measure_storage_missing_path_is_zero`, which currently
  enshrines the BLOCKER 10 bug. The bug-catching test must change with the fix.
- **REJECT** making `decision` silently defaulted on legacy loads. Legacy traces fail closed.

### Lane D — QA semantic audit / minimality / genuine multi-hop / same-split cross-group
(Muse Spark Free)
Accepted in full: leave-one-out minimality over ATOMS, the closed decision vocabulary
(approve / repair-minimality / repair-alternatives / relabel-multihop / reject-replace),
the single-atom answerability test for multi-hop, and replacing the one-group rule with a
same-split rule.

Rulings:
- **ACCEPT** two independent passes for questionable items with orchestrator adjudication by
  direct corpus inspection. Code may enforce structure and provenance; it may never auto-decide
  sufficiency, minimality, or answerability.
- **ACCEPT** the authoritative split gate stays in `substrate/splits.py`; `data_tools/verify.py`
  line ~188 one-group check is relaxed to a same-split check. Leakage prevention must not weaken.
- **ACCEPT** the noted inconsistency in `staging/qa-pilot-dev-05.json` (group `java` with
  sources spanning borneo + java) as a real finding to adjudicate during the audit, not a defect
  to paper over.
- **REJECT** collapsing alternative sufficient sets. Alternatives are encouraged.
- **REJECT** any bulk re-approval. Semantic repairs legitimately invalidate approvals; the
  existing content-hash machinery enforces this and must not be weakened.

### Lane E — Regimes / custody / expansion (Nemotron Ultra Free)
Accepted: two machine-readable regimes, revised 240-item controlled targets, append-only
custody audit log, and custodian-run synthetic leakage check returning PASS/REJECT plus
non-revealing statistics.

Rulings:
- **ACCEPT** Regime A (query-heldout / corpus-known) as PRIMARY and Regime B (document-heldout)
  as a separate, separately reported slice. Every result must state its regime.
- **ACCEPT** the statistical reasoning that n=30 cannot support high-accuracy claims and n=120
  is a pragmatic ceiling. If corpus limits yield fewer than 120 good held-out items, report the
  shortfall with evidence. Do NOT silently revert to 30. Do NOT fill with weak questions.
- **ACCEPT** the leakage-check disclosure boundary: synthetic ids and aggregate distribution
  statistics only; never held-out ids, text, or answers.
- **REJECT** the design's suggestion to pin embedding-model similarity thresholds as fixed
  constants. Thresholds must be calibrated on dev with recorded operating characteristics, not
  asserted from an external default. If a local embedding model is unavailable at freeze time,
  the n-gram path must stand alone and be labeled as such.
- **REJECT** modifying `corpus/split_map.json` in place. Regime designation must live in
  Round 0 metadata derived from the split map, so the accepted split map's hash stays pinned.

### Lane F — Distractor-scale corpus (Muse Spark Free)
Accepted: separate wrapper layer with disjoint node-id namespace, tiered scaling curve,
per-tier manifests, mechanical de-duplication against the 297 core by pageid/title/content hash,
and a stopping rule that makes 50k non-blocking.

Rulings:
- **ACCEPT** `corpus/scale/` as a separate path with one-directional cross-referencing
  (tier manifest cites core hash; core cites nothing about scale).
- **ACCEPT** tiers as strict nested supersets from one predeclared seeded order.
- **ACCEPT** the stopping criterion: stop when the curve saturates or cleanly extrapolates;
  do not require 50k.
- **ACCEPT** fallback B (offline dump slice) and the requirement to label any fallback C
  index-expansion result as non-empirical.
- **ACCEPT** that scale work must NOT block the semantic repairs or the freeze.

## Cross-lane conflicts resolved

1. **Lane A "minimal atom" vs Lane D "minimal set".** Resolved in Lane D's favor with Lane A's
   constraint attached: atoms must be *semantically atomic* (one proposition each); an atom that
   internally carries answer + setup is `repair-minimality` and must be re-atomized. Lane A's
   length-based minimality is not sufficient on its own.
2. **Lane A rejecting `p:` atoms vs the existing 70 drafts.** Migration is required and is
   expensive. It must happen AFTER the semantic audit determines which atoms are actually
   necessary, so the audit runs on paragraph spans first and atomization runs second.
3. **Lane B legacy migration vs Lane C fail-closed.** Resolved: legacy *traces* migrate via an
   explicit recorded transform; legacy *outcomes* missing a decision fail closed. Migration is
   for wire compatibility, not for inventing provenance.

## Ownership map for PHASE 2

| Owner (free model) | Files |
|---|---|
| Lead A (Muse Spark) | `substrate/support_index.py` (new), `eval/support.py` (new), `tests/test_support_semantics.py` (new), `substrate/types.py` (SupportAtom only) |
| Lead B (Nemotron Ultra) | `eval/run_format.py`, `tests/test_contract.py`, `tests/test_semantics_adversarial.py` |
| Lead C (Muse Spark) | `substrate/telemetry.py`, `substrate/evidence.py`, `eval/metrics.py`, `tests/test_telemetry_*.py` (new), adapter docstring only |
| Lead D (Muse Spark) | `data_tools/qa_schema.py`, `data_tools/verify.py`, `substrate/splits.py`, `docs/qa-construction-protocol.md` |
| Lead E (Nemotron Ultra) | `substrate/manifest.py`, `data_tools/leakage_check.py` (new), `docs/qa-gate-decisions.md` |
| Verifier (one-command) | `scripts/verify_round0` (new), `.github/workflows/verify-round0.yml` (new) |

Conflict avoidance: `substrate/types.py` is shared between A and C. A owns ONLY `SupportAtom`
plus its exports; C owns ONLY `EvidenceDecision` plus its exports. No worker may edit another
worker's rows.

## Sequencing

1. A, B, C, D, E implement in parallel (disjoint files).
2. Orchestrator runs the full suite after each integration; no test-count inflation accepted
   as evidence of correctness.
3. Phase 3 independent adversarial review of each repaired component by a reviewer who did not
   write it.
4. Phase 4 semantic audit of all 70 drafts (audit on current paragraph spans).
5. THEN atomization migration, then expansion, then regimes, then scale, then freeze.