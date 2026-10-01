"""Support-semantics evaluation: ancestry-aware satisfaction, separate precision.

Two strictly separated channels (never conflate them):

- SUPPORT (this module's ``covers`` / ``atom_satisfaction`` /
  ``sufficient_set_completion_support``): satisfied iff the atom's host leaf
  is in the retrieved node's transitive leaf set (upward-closed ancestry).
  For subspan atoms the retrieved span text must additionally contain the
  atom text exactly (code-point ``in``). No embeddings, no answer text, no
  thresholds.
- PRECISION / COST (``context_precision_report``): exact atom hits,
  imprecise covers, overshoot tokens, leaf precision. Coarse (ancestor)
  retrieval always scores support while scoring strictly worse precision at
  strictly higher token cost. Support satisfaction must NEVER inflate
  precision: ancestry-expanded ids are never fed into precision inputs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from substrate.support_index import SupportIndex
from substrate.types import CorpusNode, SupportAtom

TokenFn = Callable[[str], int]


def _tokens(token_fn: TokenFn | None, text: str) -> int:
  if token_fn is None:
    return len(text.split())
  return int(token_fn(text))


def covers(
  retrieved_id: str,
  atom: SupportAtom,
  index: SupportIndex,
  nodes_by_id: Mapping[str, CorpusNode],
) -> bool:
  """TRUE iff the retrieved node supports the atom (ancestry + containment).

  Leaf atoms: ``atom.node_id`` must be in ``index.leaf_set(retrieved_id)``.
  Subspan atoms: additionally the retrieved span text must contain the atom
  text exactly (code-point ``in``). Unknown retrieved ids never cover
  (return False); a retrieved id known to ``nodes_by_id`` but missing from
  the index raises via ``leaf_set`` (internal inconsistency, fail closed).
  """
  node = nodes_by_id.get(retrieved_id)
  if node is None:
    return False
  if atom.node_id not in index.leaf_set(retrieved_id):
    return False
  if atom.atom_kind == "subspan":
    return atom.text in node.text
  return True


def atom_satisfaction(
  retrieved: Sequence[str],
  atoms: Sequence[SupportAtom],
  index: SupportIndex,
  nodes_by_id: Mapping[str, CorpusNode],
) -> dict:
  """Per-atom support satisfaction over a retrieved id list.

  Returns ``{"per_atom": [...], "satisfied_count": int,
  "satisfaction_rate": float | None}``. Each per-atom entry holds
  ``satisfied`` (some retrieved id covers), ``covering_id`` (first covering
  id in retrieval order, else None), ``exact`` (covering id IS the host leaf
  of a full-leaf atom), and ``imprecise`` (satisfied but not exact).
  Subspan atoms are never exact: node retrieval always returns whole nodes.
  ``satisfaction_rate`` is None (not 0) when there are no atoms.
  """
  per_atom: list[dict] = []
  for atom in atoms:
    covering_id: str | None = None
    for rid in retrieved:
      if covers(rid, atom, index, nodes_by_id):
        covering_id = rid
        break
    satisfied = covering_id is not None
    exact = bool(satisfied and covering_id == atom.node_id and atom.atom_kind == "leaf")
    per_atom.append(
      {
        "atom": atom.to_dict(),
        "node_id": atom.node_id,
        "satisfied": satisfied,
        "covering_id": covering_id,
        "exact": exact,
        "imprecise": bool(satisfied and not exact),
      }
    )
  satisfied_count = sum(1 for e in per_atom if e["satisfied"])
  return {
    "per_atom": per_atom,
    "satisfied_count": satisfied_count,
    "satisfaction_rate": (satisfied_count / len(per_atom) if per_atom else None),
  }


def sufficient_set_completion_support(
  retrieved: Sequence[str],
  sufficient_sets_atoms: Sequence[Sequence[SupportAtom]],
  index: SupportIndex,
  nodes_by_id: Mapping[str, CorpusNode],
) -> dict:
  """Binary completion over genuinely ALTERNATIVE atom sets (support mode).

  Same shape as the exact-id ``sufficient_set_completion`` (``completion``,
  ``best_fractional_coverage``, ``best_set_index``, ``per_set_coverage``,
  ``complete_sets``) plus per-atom support detail and
  ``coverage_mode: "support"``. A set is complete iff EVERY atom in it is
  support-satisfied; partial coverage never counts as completion. Support
  numbers are NOT comparable to exact-id numbers: report the break, never
  splice the series.
  """
  if not sufficient_sets_atoms:
    return {
      "completion": None,
      "best_fractional_coverage": None,
      "best_set_index": None,
      "per_set_coverage": [],
      "complete_sets": [],
      "coverage_mode": "support",
      "per_atom": [],
    }
  seen: dict[SupportAtom, None] = {}
  for atom_set in sufficient_sets_atoms:
    for atom in atom_set:
      seen.setdefault(atom)
  detail = atom_satisfaction(retrieved, list(seen), index, nodes_by_id)
  satisfied_by_atom = {
    SupportAtom.from_dict(e["atom"]): e["satisfied"] for e in detail["per_atom"]
  }
  coverages: list[float] = []
  for atom_set in sufficient_sets_atoms:
    members = list(atom_set)
    if not members:
      coverages.append(1.0)
    else:
      hit = sum(1 for a in members if satisfied_by_atom.get(a, False))
      coverages.append(hit / len(members))
  best = max(range(len(coverages)), key=lambda i: coverages[i])
  complete = [i for i, c in enumerate(coverages) if c == 1.0]
  return {
    "completion": 1.0 if complete else 0.0,
    "best_fractional_coverage": coverages[best],
    "best_set_index": best,
    "per_set_coverage": coverages,
    "complete_sets": complete,
    "coverage_mode": "support",
    "per_atom": detail["per_atom"],
  }


def context_precision_report(
  retrieved: Sequence[str],
  atoms: Sequence[SupportAtom],
  index: SupportIndex,
  nodes_by_id: Mapping[str, CorpusNode],
  token_fn: TokenFn | None = None,
) -> dict:
  """Granularity-penalizing precision and token cost of a retrieved list.

  Each retrieved id is classified WITHOUT ancestry expansion: ``exact`` (the
  id IS a full-leaf atom's host leaf), ``imprecise`` (covers at least one
  atom but is not exact), or ``miss`` (covers nothing). ``leaf_precision``
  is exact hits over retrieved ids (None when nothing retrieved).
  ``overshoot_tokens`` is ``max(0, total - minimal)`` where minimal is the
  atom-text token sum. A parent-paragraph retrieval covering a required leaf
  scores support elsewhere but here scores precision 0 for that id with the
  full paragraph token cost.
  """
  exact_ids = {a.node_id for a in atoms if a.atom_kind == "leaf"}
  per_retrieved: list[dict] = []
  exact_hits = 0
  imprecise_covers = 0
  misses = 0
  total_tokens = 0
  for rid in retrieved:
    node = nodes_by_id.get(rid)
    text = node.text if node is not None else ""
    ntok = _tokens(token_fn, text) if node is not None else 0
    total_tokens += ntok
    if rid in exact_ids:
      cls = "exact"
      exact_hits += 1
    elif node is not None and any(
      covers(rid, a, index, nodes_by_id) for a in atoms
    ):
      cls = "imprecise"
      imprecise_covers += 1
    else:
      cls = "miss"
      misses += 1
    per_retrieved.append({"node_id": rid, "class": cls, "tokens": ntok})
  minimal_tokens = sum(_tokens(token_fn, a.text) for a in atoms)
  n = len(list(retrieved))
  return {
    "n_retrieved": n,
    "exact_hits": exact_hits,
    "imprecise_covers": imprecise_covers,
    "misses": misses,
    "total_tokens": total_tokens,
    "minimal_tokens": minimal_tokens,
    "overshoot_tokens": max(0, total_tokens - minimal_tokens),
    "leaf_precision": (exact_hits / n if n else None),
    "per_retrieved": per_retrieved,
  }
