"""CUSTODIAN-SIDE ground truth for the WORKER-VISIBLE partition only.

This module reads `staging/*.json` -- the public QA records that carry
`evidence.sufficient_sets`, `labels.answer_text` and `meta.source_articles` for
the 206 train/dev/shadow_dev items. It exists so the custodian can build oracle
packets and score dev/shadow_dev answers.

It reads NOTHING from the sealed private store. Every function here takes a
question_id that came from `corpus/questions.json`, so the private set is
unreachable by construction rather than by convention.

    ############################################################
    #  BOUNDARY WARNING -- READ BEFORE USING THIS FOR RETRIEVAL  #
    ############################################################

`staging/` is TRACKED IN GIT (210 files, including in the frozen tag
`round0-freeze-r1`) and republishes, for every worker-visible item, the exact
fields `corpus/questions.json` was deliberately hardened to drop:

    staging/qa-dev-11.json   meta.source_articles = ['a:orange_colour', ...]
                             meta.group          = 'orange'
                             labels.answer_text  = 'Brazil'

    corpus/questions.json    meta = {}   (no group, no source_articles, no labels)

So the partition hardening is defeated by a sibling directory in the same
repository, on the same branch, in the same history. This is PRE-EXISTING and
FROZEN -- it is not introduced by Round 1, and it does not touch the private test
(private labels live outside the repository). It is recorded here because a
readiness reviewer asking "does the implementation receive hidden metadata?"
deserves the honest answer: the repository still contains it, so the answer can
only be established by the `QueryInput` boundary plus code audit, not by the
repo being clean. See `docs/R1_RUN_STATE_REPORT.md` §7.

Consequently: this module is CUSTODIAN ONLY. No retriever may import it. If an
architecture's retrieval code imports this module, that is a disqualifying
leakage bug, not a style complaint.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

STAGING_DIR = "staging"


@dataclass(frozen=True)
class GroundTruth:
  """One worker-visible item's custodian-side truth."""

  question_id: str
  split: str
  question_type: str
  text: str
  answer_text: str | None
  answerability: str
  group: str
  source_articles: tuple[str, ...]
  required_atom_ids: tuple[str, ...]
  sufficient_sets: tuple[tuple[str, ...], ...]
  hard_negative_ids: tuple[str, ...]

  @property
  def is_answerable(self) -> bool:
    return self.answerability == "answerable"


def load_ground_truth(repo_root: str, split: str) -> dict[str, GroundTruth]:
  """Custodian truth for one worker-visible split, keyed by question_id."""
  path = os.path.join(repo_root, "corpus", "questions.json")
  with open(path, encoding="utf-8") as fh:
    items = json.load(fh)
  out: dict[str, GroundTruth] = {}
  for e in items:
    if e.get("split") != split:
      continue
    qid = e["question_id"]
    rec_path = os.path.join(repo_root, STAGING_DIR, f"{qid}.json")
    with open(rec_path, encoding="utf-8") as fh:
      rec = json.load(fh)
    ev = rec.get("evidence") or {}
    sets: list[tuple[str, ...]] = []
    required: list[str] = []
    for s in ev.get("sufficient_sets") or []:
      ids = tuple(a["node_id"] for a in s)
      sets.append(ids)
      for nid in ids:
        if nid not in required:
          required.append(nid)
    labels = rec.get("labels") or {}
    meta = rec.get("meta") or {}
    out[qid] = GroundTruth(
      question_id=qid,
      split=split,
      question_type=rec.get("question_type", e.get("question_type", "")),
      text=e["text"],
      answer_text=labels.get("answer_text"),
      answerability=labels.get("answerability", "answerable"),
      group=meta.get("group", ""),
      source_articles=tuple(meta.get("source_articles") or ()),
      required_atom_ids=tuple(required),
      sufficient_sets=tuple(sets),
      hard_negative_ids=tuple(
        h["node_id"] for h in (rec.get("hard_negatives") or [])
      ),
    )
  return out


def atom_to_host_paragraph(view) -> dict[str, str]:
  """Map every sentence node id to its host paragraph node id.

  Derived from the corpus hierarchy alone -- no labels. A required sentence
  "survives" a stage iff its host paragraph is in that stage's candidate set,
  because retrieving an ancestor paragraph satisfies a leaf atom
  (`eval/support.py::covers`, ancestry-aware).
  """
  mapping: dict[str, str] = {}
  for node in view.nodes:
    if node.kind == "sentence":
      mapping[node.node_id] = node.parent_id or ""
  return mapping


def host_paragraphs_for(gt: GroundTruth, atom_to_host: dict[str, str]) -> list[str]:
  """Distinct host paragraphs of an item's required atoms, deterministically ordered."""
  hosts: list[str] = []
  seen: set[str] = set()
  for atom in gt.required_atom_ids:
    host = atom_to_host.get(atom, atom)
    if host and host not in seen:
      seen.add(host)
      hosts.append(host)
  return hosts


def partition_summary(repo_root: str, split: str) -> dict:
  """Counts only. Safe to print in a report; carries no item content."""
  gts = load_ground_truth(repo_root, split)
  by_type: dict[str, int] = {}
  by_answerability: dict[str, int] = {}
  n_atoms = 0
  n_hosts = 0
  with_gold = 0
  for gt in gts.values():
    by_type[gt.question_type] = by_type.get(gt.question_type, 0) + 1
    by_answerability[gt.answerability] = by_answerability.get(gt.answerability, 0) + 1
    n_atoms += len(gt.required_atom_ids)
    if gt.answer_text:
      with_gold += 1
    view = None
  return {
    "split": split,
    "n_items": len(gts),
    "by_type": dict(sorted(by_type.items())),
    "by_answerability": dict(sorted(by_answerability.items())),
    "n_required_atoms_total": n_atoms,
    "n_items_with_gold_answer_text": with_gold,
    "note": (
      "answerability 'answerable' items without a gold answer_text cannot be "
      "scored by exact match and are reported separately, never silently dropped"
    ),
  }
