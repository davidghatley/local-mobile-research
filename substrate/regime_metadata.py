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

PAIRED DESIGN (Issue 3, Phase 3): Regime B is a TAGGED PAIRED CONDITION over
the SAME questions, NOT an exclusive population. Regime A covers the full
shadow_dev population; Regime B re-evaluates a paired subset of those same
question ids under document-heldout (their source documents excluded from
ADAPTATION data only). Concretely:

- conditions: "corpus_known" (A) vs "document_heldout" (B), same question_id.
- QUERY-TIME corpus is UNCHANGED under B: excluded documents are removed
  from adaptation/training data, NEVER from the retrieval corpus. Every
  excluded adaptation doc MUST resolve to a live corpus article
  (see verify_query_corpus_unchanged).
- A-on-paired, B-on-same-paired, and delta are reported together via
  aggregate_paired_delta. aggregate_across_regimes() still REFUSES to pool
  mixed-regime metrics as separate random populations.

Split vocabulary (Issue 1): forward split is "shadow_dev"; legacy "heldout"
maps are still accepted by derivation for backward compatibility.

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

# Paired evaluation conditions: same question, two adaptation postures.
CONDITION_A = "corpus_known"
CONDITION_B = "document_heldout"
CONDITIONS = (CONDITION_A, CONDITION_B)

# Forward split vocabulary first; legacy "heldout" accepted for
# backward compatibility with pre-reclassification maps.
REGIME_SPLITS = ("shadow_dev", "heldout")


@dataclass(frozen=True)
class RegimeGroup:
    """A group assigned to a generalization regime."""
    group_key: str
    split: str  # "shadow_dev" (forward) or legacy "heldout"
    article_count: int
    article_titles: list[str]
    regime: str  # REGIME_A or REGIME_B


@dataclass(frozen=True)
class RegimePairing:
    """One paired question evaluated under BOTH conditions.

    question_id is evaluated under CONDITION_A ("corpus_known", adaptation
    may include the source docs) and CONDITION_B ("document_heldout",
    source docs excluded from ADAPTATION data). excluded_adaptation_docs
    lists the source document titles excluded from adaptation under B;
    they REMAIN in the query-time retrieval corpus (invariant enforced by
    verify_query_corpus_unchanged).
    """
    question_id: str
    group: str
    conditions: tuple[str, ...]  # always (CONDITION_A, CONDITION_B)
    source_articles: list[str]
    excluded_adaptation_docs: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "group": self.group,
            "conditions": list(self.conditions),
            "source_articles": list(self.source_articles),
            "excluded_adaptation_docs": list(self.excluded_adaptation_docs),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "RegimePairing":
        conditions = tuple(d.get("conditions", []))
        if tuple(conditions) != CONDITIONS:
            raise ValueError(
                f"RegimePairing {d.get('question_id')!r}: conditions must be "
                f"{list(CONDITIONS)}, got {list(conditions)}"
            )
        return RegimePairing(
            question_id=d["question_id"],
            group=d["group"],
            conditions=conditions,
            source_articles=list(d.get("source_articles", [])),
            excluded_adaptation_docs=list(d.get("excluded_adaptation_docs", [])),
        )


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


def _extract_domain(group_key: str) -> str:
    """Domain heuristic for Regime B diversity (first topic word)."""
    if group_key.startswith("solo:"):
        topic = group_key[5:]
        return topic.split()[0] if topic else "unknown"
    return group_key


def derive_regime_metadata(split_map_path: str) -> RegimeMetadata:
    """Derive regime metadata from a split map file.

    Does NOT modify the split map. Returns a RegimeMetadata object with
    regime_a_groups and regime_b_groups populated.

    PAIRED SEMANTICS (Phase 3): Regime A covers the FULL shadow_dev
    (or legacy heldout) population. Regime B groups name the diverse
    subset whose questions form the PAIRED evaluation subset (see
    derive_paired_subset): the SAME question ids are evaluated under both
    conditions, so Regime B groups OVERLAP Regime A by design — they are
    not a disjoint population.

    Regime B group selection criteria (deterministic):
    - Group must be in a regime split ("shadow_dev" forward, legacy
      "heldout" accepted)
    - Group must have >= 4 articles
    - Select a diverse set of topics (prefer non-solo groups first,
      then diverse solo groups), capped at 6 groups
    - Regime B groups are NEVER train/dev/private_test.
    """
    split_map = load_split_map(split_map_path)
    split_map_sha256 = sha256_file(split_map_path)

    # Validate the group map
    validation = validate_group_map(split_map)
    if validation["errors"]:
        raise ValueError(f"Split map validation failed: {validation['errors']}")

    groups_data = split_map.get("groups", {})
    regime_split_groups: list[tuple[str, dict]] = []

    for group_key, rec in groups_data.items():
        if rec.get("split") in REGIME_SPLITS:
            articles = rec.get("articles", [])
            if len(articles) >= 4:
                regime_split_groups.append((group_key, rec))

    # Sort by: non-solo groups first (more diverse topics), then by article count desc
    def sort_key(item: tuple[str, dict]) -> tuple[int, int, str]:
        group_key, rec = item
        is_solo = group_key.startswith("solo:")
        article_count = len(rec.get("articles", []))
        return (1 if is_solo else 0, -article_count, group_key)

    regime_split_groups.sort(key=sort_key)

    # Select Regime B paired-condition groups: diverse topics, >=4 articles
    regime_b_keys: list[str] = []
    seen_domains: set[str] = set()
    for group_key, _rec in regime_split_groups:
        domain = _extract_domain(group_key)
        if len(regime_b_keys) < 6 and domain not in seen_domains:
            regime_b_keys.append(group_key)
            seen_domains.add(domain)
    regime_b_set = set(regime_b_keys)

    regime_a_groups: list[RegimeGroup] = []
    regime_b_groups: list[RegimeGroup] = []
    for group_key, rec in groups_data.items():
        if rec.get("split") not in REGIME_SPLITS:
            continue
        articles = list(rec.get("articles", []))
        entry_a = RegimeGroup(
            group_key=group_key,
            split=rec.get("split"),
            article_count=len(articles),
            article_titles=articles,
            regime=REGIME_A,
        )
        regime_a_groups.append(entry_a)
        if group_key in regime_b_set:
            regime_b_groups.append(RegimeGroup(
                group_key=group_key,
                split=rec.get("split"),
                article_count=len(articles),
                article_titles=articles,
                regime=REGIME_B,
            ))
    regime_a_groups.sort(key=lambda g: g.group_key)
    regime_b_groups.sort(key=lambda g: g.group_key)

    notes = [
        f"Derived from split_map.json sha256={split_map_sha256[:16]}...",
        f"Total regime-split groups with >=4 articles: {len(regime_split_groups)}",
        f"Regime A groups (full shadow_dev population): {len(regime_a_groups)}",
        f"Regime B paired-condition groups: {len(regime_b_groups)} (diverse domains)",
        "Regime B is a TAGGED PAIRED CONDITION over the same questions, not "
        "an exclusive population: B groups overlap A by design; B groups "
        "are never train/dev/private_test.",
        "B excludes source documents from ADAPTATION data only; the "
        "query-time retrieval corpus is unchanged.",
    ]

    return RegimeMetadata(
        split_map_sha256=split_map_sha256,
        regime_a_groups=regime_a_groups,
        regime_b_groups=regime_b_groups,
        derivation_notes=notes,
    )


def derive_paired_subset(
    split_map_path: str,
    staging_dir: str = "staging",
) -> tuple[list[RegimePairing], list[str]]:
    """Derive the paired evaluation subset deterministically.

    SELECTION RULE (deterministic, recorded in the artifact): all staging
    drafts with declared split "shadow_dev" whose meta.group is a Regime B
    paired-condition group AND whose meta.source_articles is a non-empty
    list of non-empty strings, sorted by question_id. Drafts failing the
    rule are counted in the notes (ids only), never silently dropped.

    Each pairing carries the SAME question_id under both conditions with
    the Regime-B-excluded source documents (the group's full article
    titles — document-heldout excludes whole source documents from
    adaptation data, never from the retrieval corpus).

    Returns (pairings, notes).
    """
    import os

    meta = derive_regime_metadata(split_map_path)
    split_map = load_split_map(split_map_path)
    groups_raw = split_map.get("groups", {})
    regime_b_set = {g.group_key for g in meta.regime_b_groups}

    try:
        staged = sorted(f for f in os.listdir(staging_dir) if f.endswith(".json"))
    except FileNotFoundError:
        return [], [f"staging dir absent: {staging_dir} (no pairings derivable)"]

    pairings: list[RegimePairing] = []
    skipped_no_group = 0
    skipped_no_sources = 0
    skipped_wrong_split = 0
    for fname in staged:
        with open(os.path.join(staging_dir, fname), "r", encoding="utf-8") as fh:
            try:
                rec = json.load(fh)
            except ValueError:
                continue
        if not isinstance(rec, dict):
            continue
        if rec.get("split") != "shadow_dev":
            skipped_wrong_split += 1
            continue
        qid = rec.get("question_id", "")
        memo = rec.get("meta", {}) if isinstance(rec.get("meta"), dict) else {}
        group = memo.get("group")
        sources = memo.get("source_articles")
        if not isinstance(group, str) or group not in regime_b_set:
            skipped_no_group += 1
            continue
        if (
            not isinstance(sources, list)
            or not sources
            or any(not isinstance(s, str) or not s.strip() for s in sources)
        ):
            skipped_no_sources += 1
            continue
        group_articles = list(groups_raw.get(group, {}).get("articles", []))
        pairings.append(RegimePairing(
            question_id=qid,
            group=group,
            conditions=CONDITIONS,
            source_articles=[str(s) for s in sources],
            excluded_adaptation_docs=group_articles,
        ))

    pairings.sort(key=lambda p: p.question_id)
    seen: set[str] = set()
    dupes = 0
    unique: list[RegimePairing] = []
    for p in pairings:
        if p.question_id in seen:
            dupes += 1
            continue
        seen.add(p.question_id)
        unique.append(p)

    notes = [
        "SELECTION RULE: shadow_dev staging drafts in Regime B "
        "paired-condition groups with nonempty meta.source_articles, "
        "sorted by question_id.",
        f"paired questions: {len(unique)}",
        f"skipped (split != shadow_dev): {skipped_wrong_split}",
        f"skipped (group not in Regime B paired set): {skipped_no_group}",
        f"skipped (source_articles missing/malformed): {skipped_no_sources}",
        f"skipped (duplicate question_id): {dupes}",
        f"split_map_sha256={meta.split_map_sha256[:16]}...",
    ]
    return unique, notes


def paired_subset_to_dict(
    pairings: list[RegimePairing],
    split_map_sha256: str,
    notes: list[str],
) -> dict[str, Any]:
    """Serialize the paired subset artifact (corpus/regime_b_paired.json)."""
    return {
        "split_map_sha256": split_map_sha256,
        "conditions": list(CONDITIONS),
        "selection_rule": notes[0] if notes else "",
        "pairings": [p.to_dict() for p in pairings],
        "notes": list(notes),
        "query_corpus_invariant": (
            "Regime B excludes documents from ADAPTATION data only; "
            "the query-time retrieval corpus is UNCHANGED."
        ),
    }


def excluded_articles_doc(
    pairings: list[RegimePairing],
    split_map_sha256: str,
) -> dict[str, Any]:
    """Build the regime_b_excluded_articles.json document.

    Deterministic: sorted union of excluded_adaptation_docs over the paired
    subset. verify_round0 stage 9 checks set-equality of "articles" against
    the union of Regime B group articles.
    """
    articles = sorted({t for p in pairings for t in p.excluded_adaptation_docs})
    return {
        "split_map_sha256": split_map_sha256,
        "derived_from": "corpus/regime_b_paired.json (paired subset, deterministic)",
        "scope": (
            "adaptation-data exclusion ONLY under Regime B "
            "(document_heldout). These articles REMAIN in the query-time "
            "retrieval corpus."
        ),
        "articles": articles,
    }


def evaluate_paired(
    pairings: list[RegimePairing],
    score_fn: Any,
) -> list[dict[str, Any]]:
    """Evaluate the SAME question ids under conditions A and B.

    score_fn(question_id, condition) -> numeric score. Returns one dict per
    pairing: {"question_id", "group", "corpus_known", "document_heldout"}.
    Raises ValueError on duplicate question ids.
    """
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for p in pairings:
        if p.question_id in seen:
            raise ValueError(
                f"duplicate question_id in paired subset: {p.question_id!r}"
            )
        seen.add(p.question_id)
        results.append({
            "question_id": p.question_id,
            "group": p.group,
            CONDITION_A: score_fn(p.question_id, CONDITION_A),
            CONDITION_B: score_fn(p.question_id, CONDITION_B),
        })
    return results


def verify_adaptation_exclusion(
    pairings: list[RegimePairing],
    adaptation_docs: Any,
) -> list[str]:
    """Verify Regime B source docs are excluded from adaptation data.

    adaptation_docs: iterable of document titles/ids present in the
    adaptation/training data manifest. Returns violation strings (empty =
    pass). Comparison is title-normalized (substrate.splits.norm_title).
    """
    present = {norm_title(str(d)) for d in adaptation_docs}
    violations: list[str] = []
    for p in sorted(pairings, key=lambda x: x.question_id):
        for doc in p.excluded_adaptation_docs:
            if norm_title(doc) in present:
                violations.append(
                    f"{p.question_id}: excluded adaptation doc present "
                    f"in adaptation data"
                )
    return violations


def verify_query_corpus_unchanged(
    pairings: list[RegimePairing],
    corpus_titles: Any,
) -> list[str]:
    """Verify the query-time corpus still contains every B-excluded doc.

    corpus_titles: iterable of article titles (raw or normalized) in the
    retrieval corpus. Returns violation strings (empty = pass). A Regime B
    exclusion that removes a document from RETRIEVAL (not just adaptation)
    is an invariant violation.
    """
    available = {norm_title(str(t)) for t in corpus_titles}
    violations: list[str] = []
    for p in sorted(pairings, key=lambda x: x.question_id):
        for doc in p.excluded_adaptation_docs:
            if norm_title(doc) not in available:
                violations.append(
                    f"{p.question_id}: excluded doc missing from "
                    f"query-time corpus"
                )
    return violations


def pair_conditions(
    results_a: list[dict[str, Any]],
    results_b: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join two per-condition result sets on question_id.

    Each result dict must carry "question_id". REFUSES to join unrelated
    populations: raises ValueError unless both sides cover EXACTLY the
    same question-id set (reports counts only, never content). Returns
    joined dicts sorted by question_id:
    {"question_id", "corpus_known": <a-metrics>, "document_heldout": <b-metrics>}.
    """
    def index(results: list[dict[str, Any]], tag: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for r in results:
            qid = r.get("question_id")
            if not isinstance(qid, str) or not qid:
                raise ValueError(f"{tag}: result missing question_id")
            if qid in out:
                raise ValueError(f"{tag}: duplicate question_id {qid!r}")
            out[qid] = {k: v for k, v in r.items() if k != "question_id"}
        return out

    map_a = index(results_a, CONDITION_A)
    map_b = index(results_b, CONDITION_B)
    only_a = sorted(set(map_a) - set(map_b))
    only_b = sorted(set(map_b) - set(map_a))
    if only_a or only_b:
        raise ValueError(
            "Refusing paired delta over mismatched populations: "
            f"{len(only_a)} id(s) only under {CONDITION_A}, "
            f"{len(only_b)} id(s) only under {CONDITION_B}. "
            "Paired deltas require the SAME question ids under both "
            "conditions."
        )
    return [
        {
            "question_id": qid,
            CONDITION_A: map_a[qid],
            CONDITION_B: map_b[qid],
        }
        for qid in sorted(map_a)
    ]


def aggregate_paired_delta(
    paired: list[dict[str, Any]],
) -> dict[str, Any]:
    """Report A-on-paired, B-on-same-paired, and delta.

    Input: output of pair_conditions() (or equivalent dicts with
    "question_id", "corpus_known" metrics-dict, "document_heldout"
    metrics-dict). Numeric metrics present on BOTH sides are averaged per
    side; delta = mean(document_heldout) - mean(corpus_known). Raises
    ValueError on empty input, missing conditions, or non-numeric sides.
    Unlike aggregate_across_regimes (which refuses unpaired pooling), this
    is the SUPPORTED paired reporting path.
    """
    if not paired:
        raise ValueError("aggregate_paired_delta requires a nonempty paired list")
    seen: set[str] = set()
    metric_names: set[str] = set()
    for entry in paired:
        qid = entry.get("question_id")
        if not isinstance(qid, str) or not qid:
            raise ValueError("paired entry missing question_id")
        if qid in seen:
            raise ValueError(f"duplicate question_id in paired delta: {qid!r}")
        seen.add(qid)
        for cond in (CONDITION_A, CONDITION_B):
            side = entry.get(cond)
            if not isinstance(side, dict):
                raise ValueError(
                    f"{qid}: missing condition {cond!r}; paired delta "
                    f"requires both {CONDITION_A!r} and {CONDITION_B!r}"
                )
        common = {k for k, v in entry[CONDITION_A].items()
                  if isinstance(v, (int, float))}
        common &= {k for k, v in entry[CONDITION_B].items()
                   if isinstance(v, (int, float))}
        metric_names.update(common)

    metrics: dict[str, dict[str, float]] = {}
    for name in sorted(metric_names):
        vals_a = [e[CONDITION_A][name] for e in paired
                  if isinstance(e[CONDITION_A].get(name), (int, float))]
        vals_b = [e[CONDITION_B][name] for e in paired
                  if isinstance(e[CONDITION_B].get(name), (int, float))]
        if not vals_a or not vals_b:
            continue
        mean_a = sum(vals_a) / len(vals_a)
        mean_b = sum(vals_b) / len(vals_b)
        metrics[name] = {
            f"mean_{CONDITION_A}": mean_a,
            f"mean_{CONDITION_B}": mean_b,
            "mean_delta": mean_b - mean_a,
        }
    return {
        "n_paired": len(paired),
        "question_ids": sorted(seen),
        "metrics": metrics,
    }


def aggregate_across_regimes(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate metrics ONLY if all share the same regime.

    Raises ValueError if metrics contain mixed regimes (refuses to silently pool).
    Each metric dict must have a 'regime' key with value REGIME_A or REGIME_B.
    NOTE (paired design): A and B are NOT separate random populations; use
    aggregate_paired_delta for A-on-paired / B-on-same-paired reporting.
    """

    if not metrics:
        return {}

    regimes = {m.get("regime") for m in metrics}
    if len(regimes) != 1:
        raise ValueError(
            f"Refusing to aggregate across regimes: found {sorted(regimes)}. "
            f"Regime A and Regime B must be reported separately "
            f"(or paired via aggregate_paired_delta on identical question ids)."
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
