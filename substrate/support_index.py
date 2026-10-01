"""Derived support index for ancestry-aware evidence semantics (Round 0 repair).

The corpus (``CorpusNode``) is FROZEN: this module derives a read-only index
from it and never mutates nodes or adds offset fields to them. For every
parent, intra-parent character offsets of each child are derived by ordered
``find`` of each child text from a running cursor. Fail-closed invariant:
every child must be found exactly once in order with only whitespace gaps,
else the build raises. A cycle guard rejects corrupt parent pointer cycles.
"""

from __future__ import annotations

from .types import CorpusNode

LEAF_KIND = "sentence"


class SupportIndex:
  """Parent/children maps, derived intra-parent offsets, leaf-sentence sets."""

  def __init__(self, nodes: list[CorpusNode]):
    by_id: dict[str, CorpusNode] = {}
    for n in nodes:
      if n.node_id in by_id:
        raise ValueError(f"support index: duplicate node_id {n.node_id!r}")
      by_id[n.node_id] = n
    self._nodes = by_id
    parent_of: dict[str, str | None] = {}
    children_of: dict[str, list[str]] = {n.node_id: [] for n in nodes}
    for n in nodes:
      parent_of[n.node_id] = n.parent_id
      if n.parent_id is not None:
        if n.parent_id not in by_id:
          raise ValueError(
            f"support index: node {n.node_id!r} parent {n.parent_id!r} missing"
          )
        children_of[n.parent_id].append(n.node_id)
    self._parent_of = parent_of
    self._children_of = children_of
    self._offsets: dict[str, dict[str, tuple[int, int]]] = {}
    for n in nodes:
      kids = children_of[n.node_id]
      if not kids:
        continue
      self._offsets[n.node_id] = self._derive_offsets(n, [by_id[k] for k in kids])
    self._guard_no_cycles()
    self._leaf_cache: dict[str, frozenset[str]] = {}

  @staticmethod
  def _derive_offsets(
    parent: CorpusNode, children: list[CorpusNode]
  ) -> dict[str, tuple[int, int]]:
    """Ordered ``find`` of each child text from a running cursor.

    Raises ValueError unless every child is found exactly once in order with
    only whitespace gaps between (and around) children.
    """
    out: dict[str, tuple[int, int]] = {}
    cursor = 0
    text = parent.text
    for child in children:
      if not child.text:
        raise ValueError(
          f"support index: child {child.node_id!r} of {parent.node_id!r} has empty text"
        )
      idx = text.find(child.text, cursor)
      if idx == -1:
        raise ValueError(
          f"support index: child {child.node_id!r} text not found in order "
          f"in parent {parent.node_id!r} from offset {cursor}"
        )
      gap = text[cursor:idx]
      if gap and not gap.isspace():
        raise ValueError(
          f"support index: non-whitespace gap before child {child.node_id!r} "
          f"in parent {parent.node_id!r}"
        )
      out[child.node_id] = (idx, idx + len(child.text))
      cursor = idx + len(child.text)
    tail = text[cursor:]
    if tail and not tail.isspace():
      raise ValueError(
        f"support index: non-whitespace trailing text in parent {parent.node_id!r} "
        "after last child"
      )
    head_missing = cursor == 0 and text.strip() != ""
    if head_missing:
      # Unreachable when children exist and the first find succeeded at 0
      # only if parent text is empty; kept as an explicit fail-closed guard.
      raise ValueError(
        f"support index: parent {parent.node_id!r} text not covered by children"
      )
    return out

  def _guard_no_cycles(self) -> None:
    for node_id in self._nodes:
      seen: set[str] = set()
      cur: str | None = node_id
      while cur is not None:
        if cur in seen:
          raise ValueError(f"support index: parent cycle through {cur!r}")
        seen.add(cur)
        cur = self._parent_of.get(cur)

  @property
  def nodes_by_id(self) -> dict[str, CorpusNode]:
    return self._nodes

  def parent_of(self, node_id: str) -> str | None:
    return self._parent_of[node_id]

  def children_of(self, node_id: str) -> tuple[str, ...]:
    return tuple(self._children_of[node_id])

  def child_span(self, parent_id: str, child_id: str) -> tuple[int, int]:
    return self._offsets[parent_id][child_id]

  def leaf_set(self, node_id: str) -> frozenset[str]:
    """Transitive leaf-sentence descendants; self if already a leaf sentence.

    Raises KeyError for unknown ids and ValueError on cycles.
    """
    if node_id not in self._nodes:
      raise KeyError(f"support index: unknown node_id {node_id!r}")
    cached = self._leaf_cache.get(node_id)
    if cached is not None:
      return cached
    result = self._leaf_set_uncached(node_id, ())
    self._leaf_cache[node_id] = result
    return result

  def _leaf_set_uncached(
    self, node_id: str, stack: tuple[str, ...]
  ) -> frozenset[str]:
    if node_id in stack:
      raise ValueError(f"support index: cycle through {node_id!r}")
    node = self._nodes[node_id]
    if node.kind == LEAF_KIND:
      return frozenset({node_id})
    kids = self._children_of[node_id]
    if not kids:
      return frozenset()
    out: set[str] = set()
    for kid in kids:
      cached = self._leaf_cache.get(kid)
      if cached is None:
        cached = self._leaf_set_uncached(kid, stack + (node_id,))
        self._leaf_cache[kid] = cached
      out |= cached
    return frozenset(out)


def build_support_index(nodes: list[CorpusNode]) -> SupportIndex:
  """Build a derived, read-only support index over frozen corpus nodes."""
  return SupportIndex(nodes)
