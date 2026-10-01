"""Regime metadata: machine-readable generalization regimes derived from split map.

This module derives regime designations FROM corpus/split_map.json WITHOUT
modifying it. The split map's hash stays pinned; regime metadata is a separate
Round 0 artifact.

Two regimes (never conflated, never silently pooled):
- REGIME_A (query_heldout_corpus_known): corpus documents MAY be known during
  architecture adaptation; benchmark questions/labels/phrasing unseen.
  Architecture MAY generate synthetic training from any corpus text including
  documents later used to answer benchmark questions.
- REGIME_B (document_heldout): source documents for the evaluation slice are
  EXCLUDED from architecture-specific fine-tuning/example generation.

Regime B groups are a small subset of held-out groups with >=4 articles each
and diverse topics. Regime B groups are ALWAYS a subset of held-out groups,
never train/dev.

Helper: aggregate_across_regimes() refuses to pool mixed-regime metrics
(raises ValueError) rather than silently aggregating.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .splits import norm_title, validate_group_map


REGIME_A = "query_heldout_corpus_known"
REGIME_B = "document_heldout"
REGIMES = (REGIME_A, REGIME_B)


@dataclass(frozen=True)
class RegimeGroup:
    """A group assigned to a generalization regime."""
    group_key: str
    split: str  # always "heldout" for both regimes
    article_count: int
    article_titles: list[str]
    regime: str  # REGIME_A or REGIME_B


@dataclass(frozen=True)
class RegimeMetadata:
    """Complete regime metadata derived from a split map."""
    split_map_sha256: str
    regime_a_groups: list[RegimeGroup] = field(default_factory=list)
    regime_b_groups: list[RegimeGroup] = field(default_factory=list)
    derivation_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_map_sha256": self.split_map_sha256,
            "regime_a_groups": [
                {
                    "group_key": g.group_key,
                    "split": g.split,
                    "article_count": g.article_count,
                    "article_titles": g.article_titles,
                    "regime": g.regime,
                }
                for g in self.regime_a_groups
            ],
            "regime_b_groups": [
                {
                    "group_key": g.group_key,
                    "split": g.split,
                    "article_count": g.article_count,
                    "article_titles": g.article_titles,
                    "regime": g.regime,
                }
                for g in self.regime_b_groups
            ],
            "derivation_notes": list(self.derivation_notes),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "RegimeMetadata":
        return RegimeMetadata(
            split_map_sha256=d["split_map_sha256"],
            regime_a_groups=[
                RegimeGroup(
                    group_key=g["group_key"],
                    split=g["split"],
                    article_count=g["article_count"],
                    article_titles=g["article_titles"],
                    regime=g["regime"],
                )
                for g in d.get("regime_a_groups", [])
            ],
            regime_b_groups=[
                RegimeGroup(
                    group_key=g["group_key"],
                    split=g["split"],
                    article_count=g["article_count"],
                    article_titles=g["article_titles"],
                    regime=g["regime"],
                )
                for g in d.get("regime_b_groups", [])
            ],
            derivation_notes=list(d.get("derivation_notes", [])),
        )

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")

    @staticmethod
    def read(path: str) -> "RegimeMetadata":
        with open(path, "r", encoding="utf-8") as fh:
            return RegimeMetadata.from_dict(json.load(fh))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_split_map(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def derive_regime_metadata(split_map_path: str) -> RegimeMetadata:
    """Derive regime metadata from a split map file.

    Does NOT modify the split map. Returns a RegimeMetadata object with
    regime_a_groups and regime_b_groups populated.

    Regime B selection criteria:
    - Group must be in 'heldout' split
    - Group must have >= 4 articles
    - Select a diverse set of topics (prefer non-solo groups first,
      then diverse solo groups)
    - Regime B groups are a SUBSET of held-out groups
    """
    split_map = load_split_map(split_map_path)
    split_map_sha256 = sha256_file(split_map_path)

    # Validate the group map
    validation = validate_group_map(split_map)
    if validation["errors"]:
        raise ValueError(f"Split map validation failed: {validation['errors']}")

    groups_data = split_map.get("groups", {})
    heldout_groups: list[tuple[str, dict]] = []

    for group_key, rec in groups_data.items():
        if rec.get("split") == "heldout":
            articles = rec.get("articles", [])
            if len(articles) >= 4:
                heldout_groups.append((group_key, rec))

    # Sort by: non-solo groups first (more diverse topics), then by article count desc
    def sort_key(item: tuple[str, dict]) -> tuple[int, int]:
        group_key, rec = item
        is_solo = group_key.startswith("solo:")
        article_count = len(rec.get("articles", []))
        return (1 if is_solo else 0, -article_count)

    heldout_groups.sort(key=sort_key)

    # Select Regime B candidates: diverse topics, >=4 articles each
    # Target: a small subset (e.g., 4-8 groups) covering diverse domains
    regime_b_groups: list[RegimeGroup] = []
    regime_a_groups: list[RegimeGroup] = []
    seen_domains: set[str] = set()

    # Domain extraction heuristic for diversity
    def extract_domain(group_key: str) -> str:
        if group_key.startswith("solo:"):
            # Extract topic from solo:topic
            topic = group_key[5:]
            # Group by first word as rough domain
            return topic.split()[0] if topic else "unknown"
        return group_key

    for group_key, rec in heldout_groups:
        articles = rec.get("articles", [])
        domain = extract_domain(group_key)

        # Prefer diverse domains for Regime B
        if len(regime_b_groups) < 6 and domain not in seen_domains:
            regime_b_groups.append(RegimeGroup(
                group_key=group_key,
                split="heldout",
                article_count=len(articles),
                article_titles=list(articles),
                regime=REGIME_B,
            ))
            seen_domains.add(domain)
        else:
            regime_a_groups.append(RegimeGroup(
                group_key=group_key,
                split="heldout",
                article_count=len(articles),
                article_titles=list(articles),
                regime=REGIME_A,
            ))

    # Any remaining heldout groups with <4 articles go to Regime A
    for group_key, rec in groups_data.items():
        if rec.get("split") == "heldout" and len(rec.get("articles", [])) < 4:
            regime_a_groups.append(RegimeGroup(
                group_key=group_key,
                split="heldout",
                article_count=len(rec.get("articles", [])),
                article_titles=list(rec.get("articles", [])),
                regime=REGIME_A,
            ))

    notes = [
        f"Derived from split_map.json sha256={split_map_sha256[:16]}...",
        f"Total heldout groups with >=4 articles: {len(heldout_groups)}",
        f"Regime B groups selected: {len(regime_b_groups)} (diverse domains)",
        f"Regime A groups (remaining heldout): {len(regime_a_groups)}",
        "Regime B groups are a strict subset of heldout groups; never train/dev.",
    ]

    return RegimeMetadata(
        split_map_sha256=split_map_sha256,
        regime_a_groups=regime_a_groups,
        regime_b_groups=regime_b_groups,
        derivation_notes=notes,
    )


def aggregate_across_regimes(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate metrics ONLY if all share the same regime.

    Raises ValueError if metrics contain mixed regimes (refuses to silently pool).
    Each metric dict must have a 'regime' key with value REGIME_A or REGIME_B.
    """
    if not metrics:
        return {}

    regimes = {m.get("regime") for m in metrics}
    if len(regimes) != 1:
        raise ValueError(
            f"Refusing to aggregate across regimes: found {sorted(regimes)}. "
            f"Regime A and Regime B must be reported separately."
        )

    regime = next(iter(regimes))
    if regime not in REGIMES:
        raise ValueError(f"Unknown regime: {regime!r}")

    # Simple aggregation: mean of numeric fields, preserve regime
    aggregated = {"regime": regime, "count": len(metrics)}
    numeric_keys = set()
    for m in metrics:
        for k, v in m.items():
            if isinstance(v, (int, float)) and k not in ("regime", "count"):
                numeric_keys.add(k)

    for k in numeric_keys:
        values = [m.get(k, 0) for m in metrics if isinstance(m.get(k), (int, float))]
        if values:
            aggregated[k] = sum(values) / len(values)

    return aggregated