"""Scale-tier analysis under incomplete relevance judgments (stdlib only).

The smallest explicit consumer of ``eval.scale_adjudication``. The 940
scale articles are classified (background 815 / confusable_adversarial 15 /
redirect_stub 110) but NOT exhaustively relevance-annotated, so:

- ``"background"`` is a heuristic classifier label, NOT a verified
  irrelevance judgment. This module NEVER asserts a background passage is
  irrelevant.
- A highly-ranked non-core confusable passage is routed to the adjudication
  mechanism (:func:`eval.scale_adjudication.adjudicate`) and triaged as
  ``"supporting"`` / ``"non_supporting"`` / ``"unknown"``. Without an
  explicit human verdict the triage is ``"unknown"`` — never silently
  resolved to either pole.
- All recall-style metrics range over KNOWN core support only, so unjudged
  items cannot move them. Incompleteness is reported first-class via
  ``counts["unjudged_top_k"]`` and a ``"limitations"`` list, so no reader
  mistakes a denominator for a verified one.

No precision figure over unjudged items is emitted. Deliberately, there is
no ``precision`` key in the output: precision needs judged negatives, which
we do not have.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from eval.scale_adjudication import adjudicate

SUPPORTING = "supporting"
NON_SUPPORTING = "non_supporting"
UNKNOWN = "unknown"

_LIMITATIONS_BASE = [
  "scale tier is not exhaustively relevance-annotated: only core evidence is judged",
  "background class is a heuristic label, never a verified irrelevance judgment",
  "confusable passages without an explicit human verdict are reported as unknown, never silently resolved",
  "no precision metric is reported: precision requires judged negatives, which do not exist here",
]


def triage_retrieval(
  node_id: str,
  human_verdicts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
  """Route one retrieved node through adjudication and triage it.

  - Core nodes: ``{"triage": "core", ...}`` — scored against recorded
    evidence labels; never adjudicated.
  - Scale confusable (or unclassified scale) nodes: needs adjudication.
    With an explicit human verdict in ``human_verdicts`` (``"supporting"``
    / ``"non_supporting"``) the triage follows it; otherwise triage is
    ``"unknown"``. ``"unknown"`` verdict strings also stay ``"unknown"``.
  - Scale background / redirect_stub nodes: ``{"triage":
    "unjudged_mechanical", ...}`` — mechanically unscored here and NEVER
    asserted irrelevant.
  """
  verdict = adjudicate(node_id)
  d = verdict.to_dict()
  if d["layer"] == "core":
    return {**d, "triage": "core"}
  if d["needs_adjudication"]:
    raw = (human_verdicts or {}).get(node_id)
    if raw == SUPPORTING:
      triage = SUPPORTING
    elif raw == NON_SUPPORTING:
      triage = NON_SUPPORTING
    else:
      triage = UNKNOWN  # absent, unknown, or malformed verdicts stay unknown
    return {**d, "triage": triage, "human_verdict": raw}
  # Mechanical classes: explicitly NOT judged irrelevant.
  return {**d, "triage": "unjudged_mechanical"}


def _rank_of_first(ranked: Sequence[str], known_support: set[str]) -> int | None:
  for i, nid in enumerate(ranked, start=1):
    if nid in known_support:
      return i
  return None


def _recall_at_k(ranked: Sequence[str], known_support: set[str], k: int) -> float:
  if not known_support:
    return 1.0
  return len(set(ranked[:k]) & known_support) / len(known_support)


def analyze_scale_retrieval(
  ranked_node_ids: Sequence[str],
  known_support_ids: set[str] | frozenset[str],
  k_list: Sequence[int] = (1, 5, 10, 20),
  human_verdicts: Mapping[str, str] | None = None,
  top_k_for_adjudication: int = 20,
) -> dict[str, Any]:
  """Compute scale metrics valid under incomplete judgments.

  ``ranked_node_ids`` is the system's full ranked list (retrieval order).
  ``known_support_ids`` is the KNOWN core support set (already extracted by
  the caller; this module reads no corpus or private files). Every
  recall-style metric ranges over ``known_support_ids`` ONLY, so unjudged
  scale items cannot move it.

  Returns a JSON-serializable dict with ``recall_at_k_known`` (per k),
  ``rank_of_first_known`` / ``reciprocal_rank_known`` (None when no known
  support is retrieved), ``candidate_counts``, ``reduction_ratio``,
  ``adjudication_requests`` (one entry per top-K non-core retrieval routed
  to adjudication), ``triages`` (per-node triage outcomes), ``counts``
  (including ``unjudged_top_k``), and ``limitations``.
  """
  ranked = list(ranked_node_ids)
  known = set(known_support_ids)
  ks = [int(k) for k in k_list]
  first_rank = _rank_of_first(ranked, known)
  recall = {f"recall@{k}_known": _recall_at_k(ranked, known, k) for k in ks}

  top_n = ranked[: max(0, int(top_k_for_adjudication))]
  triages: list[dict[str, Any]] = []
  requests: list[dict[str, Any]] = []
  n_unjudged_top = 0
  for rank, nid in enumerate(top_n, start=1):
    if nid in known:
      continue  # known support: judged by core labels, not adjudicated
    t = triage_retrieval(nid, human_verdicts)
    entry = {"rank": rank, **t}
    triages.append(entry)
    if t.get("needs_adjudication"):
      requests.append(entry)
    if t.get("triage") in (UNKNOWN, "unjudged_mechanical"):
      n_unjudged_top += 1

  n_candidate = len(ranked)
  return {
    **recall,
    "rank_of_first_known": first_rank,
    "reciprocal_rank_known": (1.0 / first_rank if first_rank else 0.0),
    "n_known_support": len(known),
    "candidate_counts": {"n_ranked": n_candidate, "top_k_examined": len(top_n)},
    "reduction_ratio": None,  # single-list analysis has no stages; see compare_scale_tiers
    "adjudication_requests": requests,
    "triages": triages,
    "counts": {
      "unjudged_top_k": n_unjudged_top,
      "top_k_examined": len(top_n),
      "n_adjudication_requests": len(requests),
      "n_unknown_triage": sum(1 for t in triages if t.get("triage") == UNKNOWN),
    },
    "limitations": list(_LIMITATIONS_BASE),
  }


def compare_scale_tiers(
  small_ranked: Sequence[str],
  large_ranked: Sequence[str],
  known_support_ids: set[str] | frozenset[str],
  k_list: Sequence[int] = (5, 20),
) -> dict[str, Any]:
  """Quantify known-support displacement as the candidate pool grows.

  Compares a small-pool run (e.g. core-only) against a large-pool run (e.g.
  core + 940 scale articles) over the SAME known support set. Reports per-k
  recall deltas, rank shifts of each known item (positive shift = pushed
  down by scale distractors), ``reduction_ratio`` of each list
  (``n_small / n_large`` for the large list; None when ``n_large`` is 0),
  and the same incompleteness ``limitations``.
  """
  small = list(small_ranked)
  large = list(large_ranked)
  known = set(known_support_ids)

  def _ranks(ranked: Sequence[str]) -> dict[str, int | None]:
    pos: dict[str, int] = {}
    for i, nid in enumerate(ranked, start=1):
      if nid in known and nid not in pos:
        pos[nid] = i
    return {nid: pos.get(nid) for nid in known}

  rs, rl = _ranks(small), _ranks(large)
  displacement = {
    nid: {
      "rank_small": rs[nid],
      "rank_large": rl[nid],
      "shift": (
        (rl[nid] - rs[nid])
        if (rs[nid] is not None and rl[nid] is not None)
        else None  # unranked in one run: shift undefined, not zero
      ),
    }
    for nid in sorted(known)
  }
  recall_delta = {}
  for k in [int(k) for k in k_list]:
    rs_k = _recall_at_k(small, known, k)
    rl_k = _recall_at_k(large, known, k)
    recall_delta[f"recall@{k}_known"] = {"small": rs_k, "large": rl_k, "delta": rl_k - rs_k}
  n_large = len(large)
  return {
    "recall_delta_known": recall_delta,
    "displacement": displacement,
    "candidate_counts": {"n_small": len(small), "n_large": n_large},
    "reduction_ratio": (len(small) / n_large if n_large else None),
    "limitations": list(_LIMITATIONS_BASE),
  }
