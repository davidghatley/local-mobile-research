"""Scale-tier retrieval adjudication rule.

WHY THIS EXISTS
---------------
The 940-article distractor tier is NOT purely irrelevant. Its candidate list
deliberately includes confusable material (Roman Empire, Nile, World War I/II,
Lion, Tiger, ...), so some scale passages can carry valid, partial, or
confusable-but-supporting statements. The semantic core remains the official
annotated evidence base, but a retrieved scale passage must NOT be scored as a
false positive merely because it came from the distractor layer.

This module implements the *decision rule* only. It does not adjudicate text;
adjudication is a human/agent decision. See docs/scale-evaluation-rule.md for
the full procedure and docs/scale-method.md for the layer's provenance.

    from eval.scale_adjudication import needs_adjudication
    if needs_adjudication(retrieved_node_id):
        ...  # route to an adjudicator
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

SCALE_CLASSIFICATION_REL = "corpus/scale/scale_classification.json"
SCALE_TIER_REL = "corpus/scale/tier_1k.json"

# Node-id prefixes identifying the scale layer (see docs/scale-method.md 4.2):
#   root      corpus:scale-distractors
#   cluster   dc:<slug>
#   article   d:<slug>
#   section   ds:...
#   paragraph dp:...
#   sentence  dt:...
# The core layer uses corpus:pilot, cluster:<slug>, a:, s:, p:, t: — so a
# scale node ALWAYS starts with "d" immediately followed by one of
# "", "c", "s", "p", "t" and then a colon. Bare "core" nodes never match.
SCALE_ARTICLE_PREFIX = "d:"
SCALE_NODE_RE = re.compile(r"^d(c|s|p|t)?:")

# Classes that REQUIRE adjudication before a retrieval can be scored.
ADJUDICATED_CLASSES = ("confusable_adversarial",)
# Classes that are safe to score mechanically.
MECHANICAL_CLASSES = ("background", "redirect_stub", "unknown")


@dataclass(frozen=True)
class AdjudicationVerdict:
  """What the scoring layer should do with one retrieved node."""

  node_id: str
  layer: str  # "core" | "scale"
  scale_class: str | None
  needs_adjudication: bool
  reason: str

  def to_dict(self) -> dict[str, Any]:
    return {
      "node_id": self.node_id,
      "layer": self.layer,
      "scale_class": self.scale_class,
      "needs_adjudication": self.needs_adjudication,
      "reason": self.reason,
    }


def _repo_root() -> str:
  return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@lru_cache(maxsize=1)
def _load_classification() -> dict[str, str]:
  """Map scale article node-id slug -> class. Empty when artifacts are absent.

  The classification is keyed by exact title, but two distinct scale articles
  can slugify identically (``ABBA`` and ``Abba`` both slug to ``abba``; the
  builder disambiguates with a ``~<pageid>`` suffix). A naive title->slug map
  would silently drop one. The tier manifest carries the authoritative
  ``node_id`` for every article, so resolve titles through it: title -> node
  slug, then node slug -> class. Titles absent from the tier fall back to a
  direct slug key.
  """
  path = os.path.join(_repo_root(), SCALE_CLASSIFICATION_REL)
  if not os.path.isfile(path):
    return {}
  try:
    with open(path, "r", encoding="utf-8") as fh:
      data = json.load(fh)
  except (ValueError, OSError):
    return {}

  by_title: dict[str, str] = {}
  for rec in data.get("articles", []):
    title = rec.get("title")
    cls = rec.get("class")
    if isinstance(title, str) and isinstance(cls, str):
      by_title[title] = cls

  out: dict[str, str] = {}
  for title, cls in by_title.items():
    out[_slugify(title)] = cls

  # Disambiguate through the tier manifest's authoritative node ids.
  tier_path = os.path.join(_repo_root(), SCALE_TIER_REL)
  if os.path.isfile(tier_path):
    try:
      with open(tier_path, "r", encoding="utf-8") as fh:
        tier = json.load(fh)
    except (ValueError, OSError):
      tier = {}
    for snap in tier.get("snapshots", []) or []:
      if not isinstance(snap, dict):
        continue
      node_id = snap.get("node_id")
      title = snap.get("normalized_title")
      if not isinstance(node_id, str) or not node_id.startswith(SCALE_ARTICLE_PREFIX):
        continue
      slug = node_id.split(":", 1)[1] if ":" in node_id else node_id
      cls = by_title.get(title) if isinstance(title, str) else None
      if cls is None:
        # Try the requested title, then the suffix-stripped slug.
        cls = by_title.get(snap.get("requested_title", "")) or out.get(
          _strip_pageid_suffix(slug))
      if cls is not None:
        out[slug] = cls
  return out


def _slugify(title: str) -> str:
  """Slug the scale builder actually assigns (corpus/build_pilot.slugify).

  Mirrors it exactly, including the 50-character truncation, so lookups match
  the emitted node ids. Article-identity collisions carry a ``~<pageid>``
  suffix (e.g. ``abba~17270720``), so lookups also retry the undecorated slug.
  """
  s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:50].strip("_")
  return s or "untitled"


def _strip_pageid_suffix(slug: str) -> str:
  return slug.split("~", 1)[0] if "~" in slug else slug


def is_scale_node(node_id: str) -> bool:
  """True iff the node id belongs to the scale layer's namespace."""
  return bool(node_id) and bool(SCALE_NODE_RE.match(node_id))


def scale_class_for(node_id: str) -> str | None:
  """Classification of a scale node, or None for core nodes / unknown slugs.

  Handles ``~<pageid>`` slug disambiguation (e.g. ``abba~17270720``) by
  retrying the undecorated slug, so every one of the 940 articles resolves.
  """
  if not is_scale_node(node_id):
    return None
  parts = node_id.split(":")
  if len(parts) < 2:
    return None
  table = _load_classification()
  slug = parts[1]
  if slug in table:
    return table[slug]
  return table.get(_strip_pageid_suffix(slug))


def needs_adjudication(node_id: str) -> bool:
  """True when a retrieved node must be adjudicated before scoring.

  Core nodes never need it: the core corpus is the annotated evidence base, so
  a core retrieval is scored against the recorded labels directly.
  """
  if not is_scale_node(node_id):
    return False
  cls = scale_class_for(node_id)
  if cls is None:
    # Unknown scale node: fail safe and adjudicate rather than assume
    # irrelevance.
    return True
  return cls in ADJUDICATED_CLASSES


def adjudicate(node_id: str) -> AdjudicationVerdict:
  """Full verdict for one retrieved node, with an auditable reason string."""
  if not is_scale_node(node_id):
    return AdjudicationVerdict(
      node_id=node_id, layer="core", scale_class=None,
      needs_adjudication=False,
      reason="core corpus node: scored against recorded evidence labels",
    )
  cls = scale_class_for(node_id)
  if cls is None:
    return AdjudicationVerdict(
      node_id=node_id, layer="scale", scale_class=None, needs_adjudication=True,
      reason="scale node with no classification entry: adjudicate rather than "
             "assume irrelevance",
    )
  if cls in ADJUDICATED_CLASSES:
    return AdjudicationVerdict(
      node_id=node_id, layer="scale", scale_class=cls, needs_adjudication=True,
      reason="confusable scale article: a retrieved passage here may be valid "
             "alternative, partial, or confusable-but-supporting evidence and "
             "must not be scored as a false positive by layer membership alone",
    )
  return AdjudicationVerdict(
    node_id=node_id, layer="scale", scale_class=cls, needs_adjudication=False,
    reason="scale node classed %s: mechanical scoring is safe" % cls,
  )


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
  import sys

  for arg in sys.argv[1:]:
    print(json.dumps(adjudicate(arg).to_dict(), sort_keys=True))
