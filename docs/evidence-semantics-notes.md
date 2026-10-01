# Evidence Semantics Notes (Round 0 Repair, Lane A)

## Atoms are the minimal semantic support unit

A `SupportAtom` (`substrate/types.py`) is one leaf sentence (`atom_kind ==
"leaf"`, offsets both `None` — never `0..len`) or an exact subspan of one
(`atom_kind == "subspan"`, code-point offsets into the host leaf, `text`
code-point exact). Sealed sufficient sets use leaf atoms.

## Support satisfaction is ancestry-aware and upward-closed

`eval/support.py::covers` is TRUE iff the atom's host leaf is in the
retrieved node's transitive leaf set (`SupportIndex.leaf_set`), plus exact
code-point containment for subspan atoms. Ancestry and exact containment
only: no embedding similarity, no answer text, no thresholds. Retrieving a
parent paragraph therefore SATISFIES support for a required leaf.

## Precision and token cost are separate and granularity-penalizing

`context_precision_report` never receives ancestry-expanded ids. Each
retrieved id is `exact` (it IS a leaf atom), `imprecise` (covers but is
coarser), or `miss`; `leaf_precision` is exact hits over retrieved ids and
`overshoot_tokens` charges everything above the atom-text minimum. A parent
retrieval scores support = 1 with precision strictly lower and tokens
strictly higher than the direct leaf retrieval.

## Dual-metric gaming is dominated

Retrieving both the leaf `a` and its parent `P` keeps support at 1.0 but
lowers leaf precision (1.0 -> 0.5) and raises token cost, so no system can
claim both exactness and support from the same retrieval. Support
satisfaction must NEVER be used to inflate precision.

## Metric break, not a splice

Old exact-id-match numbers are NOT comparable to support numbers. Report
both series with the break annotated; never splice them into one trend.
The index invariant (ordered `find`, whitespace-only gaps, fail-closed) and
the frozen corpus guarantee the two series share provenance but measure
different things.
