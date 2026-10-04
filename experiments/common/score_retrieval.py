"""CUSTODIAN-SIDE scoring of retrieval traces against the required evidence set.

This is the PRIMARY measurement of Round 1. It is deterministic, needs no judge,
no generator and no answer, and it is interpretable whether or not the generator
floors -- which is exactly why it has to carry the tournament if the answer
metric turns out to be uninformative.

All survival metrics are stated at PARAGRAPH granularity, because that is the
retrieval unit: a required sentence "survives" a stage iff its host PARAGRAPH is
in that stage's candidate set, since retrieving an ancestor paragraph satisfies a
leaf atom (`eval/support.py::covers`, ancestry-aware).

Two properties this module is built to have:

  - It scores ANY stage of ANY system's trace, so a cascade's stage-by-stage
    survival and a flat baseline's single-stage survival come out of the same code
    and are directly comparable.
  - It reports DENOMINATORS everywhere. "Survival 0.9" means nothing without knowing
    whether that is 9 of 10 required atoms or 9 of 90, and an architecture that
    retrieves only easy single-atom items can otherwise look identical to one
    that retrieves everything.

ANSWER-SCORING IS NOT HERE. Answer metrics come from the generator and are
computed in the floor probe. Keeping the two apart is what lets a weak generator
degrade the answer column without touching the retrieval column.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.metrics import wilson_ci  # noqa: E402


@dataclass
class SurvivalReport:
  """Per-system, per-stage survival with denominators and CIs."""

  system_id: str
  tier: str
  split: str
  n_items: int
  n_items_with_required_evidence: int
  stage_rows: dict[str, dict] = field(default_factory=dict)
  final_packet_rows: dict[str, dict] = field(default_factory=dict)
  token_rows: dict[str, dict] = field(default_factory=dict)
  per_item: dict[str, dict] = field(default_factory=dict)
  notes: list[str] = field(default_factory=list)

  def to_dict(self) -> dict:
    return {
      "system_id": self.system_id,
      "tier": self.tier,
      "split": self.split,
      "n_items": self.n_items,
      "n_items_with_required_evidence": self.n_items_with_required_evidence,
      "stage_survival": self.stage_rows,
      "final_packet": self.final_packet_rows,
      "evidence_tokens": self.token_rows,
      "notes": self.notes,
    }


def required_host_paragraphs(gt, atom_to_host: dict[str, str]) -> list[str]:
  """Distinct retrievable host paragraphs of an item's required atoms."""
  out: list[str] = []
  seen: set[str] = set()
  for atom in gt.required_atom_ids:
    host = atom_to_host.get(atom, atom)
    if host and host not in seen:
      seen.add(host)
      out.append(host)
  return out


def _rate(hits: int, n: int) -> float | None:
  return (hits / n) if n else None


def score_traces(
  *,
  traces: list[dict],
  system_id: str,
  tier: str,
  split: str,
  ground_truth: dict,
  atom_to_host: dict[str, str],
  known_paragraphs: set[str],
) -> SurvivalReport:
  """Score one system's traces on one split. CUSTODIAN SIDES ONLY.

  ``known_paragraphs`` is the set of retrievable paragraph ids in the tier; a
  required atom whose host is outside it cannot be retrieved at all and is
  excluded from the denominator rather than counted as a permanent miss. That
  distinction matters at the scale tier, where the 940 distractor articles are
  merged in and an atom must still be genuinely retrievable.
  """
  rep = SurvivalReport(
    system_id=system_id, tier=tier, split=split, n_items=len(traces),
    n_items_with_required_evidence=0)

  # Accumulators: per stage name, per-item (hosts_required, hosts_survived).
  stage_acc: dict[str, list[tuple[int, int]]] = {}
  packet_acc: list[tuple[int, int]] = []
  packet_leaf_acc: list[tuple[int, int]] = []
  tokens: list[int] = []
  n_truncated = 0
  n_empty_packets = 0
  n_items_scored = 0

  for tr in traces:
    qid = tr["question_id"]
    gt = ground_truth.get(qid)
    if gt is None:
      continue
    req = [h for h in required_host_paragraphs(gt, atom_to_host) if h in known_paragraphs]
    if not req:
      rep.per_item[qid] = {"excluded": "no retrievable host paragraph for any required atom"}
      continue
    n_items_scored += 1
    req_set = set(req)
    rep.n_items_with_required_evidence = n_items_scored

    for st in tr["stages"]:
      name = st["stage"]
      # candidate_ids are in SCORE order; the set is what survival means.
      surviving = req_set & set(st["candidate_ids"])
      stage_acc.setdefault(name, []).append((len(req), len(surviving)))

    pk = tr["evidence_packet"]
    spans = list(pk.get("spans") or [])
    span_ids = [s["node_id"] for s in spans]
    packet_acc.append((len(req), len(req_set & set(span_ids))))
    # Context precision: exact hits over retrieved, at LEAF granularity only.
    # Ancestry-expanded ids are never fed into a precision denominator.
    leaves = {a for a in gt.required_atom_ids}
    exact_leaf_hits = sum(1 for nid in span_ids if nid in leaves)
    packet_leaf_acc.append((len(span_ids), exact_leaf_hits))

    tok = tr.get("evidence_token_count")
    if isinstance(tok, int):
      tokens.append(tok)
    if pk.get("truncated"):
      n_truncated += 1
    if not span_ids:
      n_empty_packets += 1

    rep.per_item[qid] = {
      "n_required_hosts": len(req),
      "n_hosts_in_packet": len(req_set & set(span_ids)),
      "hosts": req,
      "packet_span_ids": span_ids,
      "exact_evidence_tokens": tok,
      "stage_survival": {
        st["stage"]: len(req_set & set(st["candidate_ids"])) for st in tr["stages"]
      },
    }

  for name, rows in stage_acc.items():
    hits = sum(h for _, h in rows)
    n = sum(t for t, _ in rows)
    rep.stage_rows[name] = {
      "required_paragraphs": n,
      "survived": hits,
      "survival": _rate(hits, n),
      "wilson_ci": wilson_ci(hits, n) if n else None,
      "n_items": len(rows),
      "mean_required_per_item": (n / len(rows)) if rows else None,
    }
  if packet_acc:
    hits = sum(h for _, h in packet_acc)
    n = sum(t for t, _ in packet_acc)
    rep.final_packet_rows = {
      "required_paragraphs": n,
      "completed": hits,
      "completion": _rate(hits, n),
      "wilson_ci": wilson_ci(hits, n) if n else None,
      "n_items": len(packet_acc),
      "n_items_fully_complete": sum(1 for t, h in packet_acc if t == h),
      "item_level_completion": _rate(
        sum(1 for t, h in packet_acc if t == h), len(packet_acc)),
    }
  if packet_leaf_acc:
    retrieved = sum(r for r, _ in packet_leaf_acc)
    exact = sum(e for _, e in packet_leaf_acc)
    rep.final_packet_rows["context_precision_leaf"] = {
      "retrieved_leaf_nodes": retrieved,
      "exact_leaf_hits": exact,
      "leaf_precision": _rate(exact, retrieved),
      "note": (
        "exact leaf-node hits over retrieved leaf nodes. Ancestry-expanded "
        "paragraph ids are NOT in the denominator: a paragraph that contains a "
        "required sentence is not itself a retrieved leaf."
      ),
    }
  if tokens:
    srt = sorted(tokens)
    rep.token_rows = {
      "n": len(tokens),
      "mean": sum(tokens) / len(tokens),
      "median": srt[len(srt) // 2],
      "p95": srt[min(len(srt) - 1, int(0.95 * len(srt)))],
      "max": max(tokens),
      "min": min(tokens),
      "n_over_target_band_800": sum(1 for t in tokens if t > 800),
      "n_over_hard_cap_1000": sum(1 for t in tokens if t > 1000),
      "n_truncated": n_truncated,
      "n_empty_packets": n_empty_packets,
      "target_band": "300-800 typical, <=1000 hard cap (frozen comparability contract §2)",
    }
  if n_items_scored < len(traces):
    rep.notes.append(
      f"{len(traces) - n_items_scored} of {len(traces)} items were EXCLUDED from "
      f"the survival denominators because no required atom had a retrievable host "
      f"paragraph in this tier. They are listed in per_item with excluded=..., not "
      f"silently counted as misses."
    )
  return rep


def load_traces(path: str) -> list[dict]:
  out = []
  with open(path, encoding="utf-8") as fh:
    for line in fh:
      if line.strip():
        out.append(json.loads(line))
  return out
