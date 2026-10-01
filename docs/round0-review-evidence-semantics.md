# Round 0 Independent Adversarial Review — Evidence Semantics (Phase 3)

Reviewer role: independent attacker (did not write the code). HEAD `230e7d5`.
Scope read: `docs/evidence-semantics-notes.md`, `substrate/support_index.py`,
`eval/support.py`, `SupportAtom` section of `substrate/types.py` (lines 155-208).
All probes below were EXECUTED on synthetic fixtures (no real corpus, no sealed
labels). Line references are to HEAD file contents.

## Attack 1 — Sibling false positive: PASS

Probe: fixture `P1 -> {a, b}`, `P2 -> {c}`, atom = leaf `a`.
`eval/support.py:48-55` gates on `atom.node_id in index.leaf_set(retrieved_id)`.

- `covers("b", atom_a)` = False (sibling leaf_set `{b}` disjoint). PASS
- `covers("aX", ...)` (textual-prefix id) = False (unknown id, `nodes_by_id.get`
  miss returns False, `support.py:48-50`). PASS
- `covers("c", ...)` (other section) = False; `covers("P2", ...)` = False. PASS
- Text-contains-but-excluded: node `D` (kind paragraph, text `"prefix " + s_a +
  " suffix"`, no children, leaf_set `{}`) contains the atom string yet
  `covers("D", atom_a)` = False — leaf-set gate precedes any text comparison
  for leaf atoms. PASS
- Unknown id `"nope"` = False (never raises; fail-open-safe by returning False,
  while index-known-but-inconsistent ids raise via `leaf_set` — correct split).
  PASS

## Attack 2 — Ancestor over-credit / precision separation: PASS

Probe: single-id retrievals against leaf atom `a` (whitespace token fn):

| retrieved | support | exact | imprecise | leaf_precision | total | overshoot |
|---|---|---|---|---|---|---|
| `a` | True | True | False | 1.0 | 4 | 0 |
| `P1` | True | False | True | 0.0 | 8 | 4 |
| `S1`/`A1` | True | False | True | 0.0 | 13 | 9 |

True ancestors satisfy support BY DESIGN (upward-closed, notes + `covers`
L52) and are always flagged `imprecise`, never `exact` (`support.py:82,185`).
No-equal-precision input exists: `exact` requires `rid` to BE a leaf atom's
host id (`support.py:174,185`); node ids are unique so a parent id can never
be exact; any added non-exact id strictly dilutes `exact_hits/n`. Token cost
strictly separates (4 < 8 < 13; overshoot 0 < 4 < 9). PASS

## Attack 3 — Dual-metric gaming (`[a, P1]`): PASS, dominated as claimed

Executed: `["a"]` -> support 1.0, precision 1.0, total 4, overshoot 0.
`["P1"]` -> support 1.0, precision 0.0, total 8, overshoot 4.
`["a","P1"]` -> support 1.0, precision **0.5**, total **12**, overshoot **8**.
Union-of-leaf-sets is not even needed for the domination: precision counts
exact ids over retrieved ids (`support.py:206`), so the extra parent adds a
denominator unit with zero numerator while adding full paragraph tokens.
Claiming both exactness and support from one retrieval is impossible. PASS

## Attack 4 — Subspan exploitation: PASS (intended, bounded)

Rule (`support.py:53-54`): subspan cover requires leaf-in-leaf-set AND
`atom.text in node.text` (code-point `in`). Executed with subspan "quasars"
of leaf `a`:

- Leaf `a` covers: True. Parent `P1` covers: True (intended upward-closure),
  but precision report scores it `imprecise`, leaf_precision 0.0, overshoot 7.
- Sibling `b`: False. Disjoint node `D` whose text DOES contain "quasars":
  **False** — the leaf-set gate fires first, so a large unrelated node
  containing the substring gets NO credit. The only nodes that can satisfy
  are true ancestors (whose leaf_set contains the host leaf by construction),
  which is the documented intent, and precision/token separation still holds
  for them. No break in precision separation. PASS

## Attack 5 — Precision inflation: PASS (no construction found)

`context_precision_report` (`support.py:174-196`) builds `exact_ids` from atom
host ids only and classifies each retrieved id WITHOUT ancestry expansion
(no `leaf_set` union is ever fed into a precision input — `leaf_set` is used
only as a boolean `covers` gate for the imprecise/miss label). Executed:

- `[P1]` -> 0.0, `[S1]` -> 0.0, `[a,P1,S1,A1]` -> 0.25, `[]` -> None.
- A paragraph blob alone scores precision 0.0, never 1.0: `P1` (kind
  paragraph) can never be in `exact_ids` (leaf-atom hosts only), and ids are
  unique so no paragraph aliases a leaf. No input constructed where a
  paragraph-only retrieval scores 1.0. PASS

## Attack 6 — Index integrity (fail-closed): PASS

`substrate/support_index.py:50-93` ordered-`find` + whitespace-gap invariant;
duplicate-id, missing-parent, empty-child, and cycle guards. Executed:

- Missing child text -> ValueError. PASS
- Non-whitespace gap (`AAA---BBB`) -> ValueError. PASS
- Out-of-order children -> ValueError (gap check). PASS
- Extra duplicate-text occurrence (`same same same`, 2 kids) -> ValueError
  (trailing-text). NOTE: exact-duplicate children (`same same`, 2 kids)
  builds successfully — this is CORRECT, not fail-open: two identical
  sentences are a legitimate corpus state and ordered-`find` resolves them
  deterministically. PASS
- True parent cycle (`X<->Y`, identical text so offsets derive) -> ValueError
  `parent cycle through 'X'` via `_guard_no_cycles`. Self-parent -> same.
  PASS
- Empty child text, duplicate node_id, trailing non-whitespace text ->
  all ValueError. PASS
- (An `X<->Y` cycle with non-covering texts fails even earlier at offset
  derivation — fail-closed either way.) PASS

## Attack 7 — No silent weakening of exact-id metrics: PASS

`git diff b38a457..HEAD -- eval/metrics.py substrate/types.py`: the ONLY
removed line in the entire diff is

- `substrate/types.py`: `if score_kind == "calibrated_probability" ...` ->
  `if score_kind in ("calibrated_probability", "model_probability") ...`
  (range-check extended to the NEW kind; behavior for every pre-existing kind
  byte-identical — strictly stronger validation, not a weakening).

`eval/metrics.py` changes are pure additions (`abstention_outcome`,
`abstention_summary`); `recall_at_k`, `reciprocal_rank`, `ndcg_at_k`,
`sufficient_set_completion`, `stage_coverage`, `survival_curve`,
`conditional_retention`, `lost_and_recovered` have zero signature/body
changes (grep for `^[-+].*def` on those names: no hits). The non-regression
property is therefore structural, not faked. PASS

## Attack 8 — Required non-regression (leaf must not lose to paragraph): PASS

Executed head-to-head on leaf atom `a` (numbers from Attack 2/3 runs):

- Support: leaf `[a]` 1.0 vs paragraph `[P1]` 1.0 — leaf does NOT lose. PASS
- Precision: leaf 1.0 vs paragraph 0.0 — leaf WINS. PASS
- Tokens: leaf total 4 / overshoot 0 vs paragraph total 8 / overshoot 4 —
  leaf WINS. PASS

## Verdict

PASS
