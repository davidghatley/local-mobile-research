"""Deterministic derivation scaffolding (no LLM, no network, stdlib only).

Workflow (runs ONLY after corpus + split map are validated/frozen):
  1. Load corpus JSONL + split_map.json (read-only).
  2. Pick a group assigned to the target split (train/dev first; heldout
     only via the custodian path). Group choice is recorded in the manifest.
  3. Emit a draft SCAFFOLD for a human author: candidate evidence units
     (sentences/paragraphs) from within that ONE group, candidate hard
     negatives, and blank question/answer fields. The human writes the
     actual question text and answer — this tool never generates them.
  4. Author fills the scaffold, then data_tools.verify checks it, then a
     SECOND human verifies it (independent evidence verification), then
     seal.py splits questions from labels.

Hard rules enforced here:
  - Group-before-derivation: evidence units are drawn from exactly one
    predeclared split-map group; the scaffold records group + split.
  - No mixed-split chains: scaffold refuses groups whose articles span
    splits (corrupt map) and validate refuses multi-source drafts whose
    articles sit in different splits/groups.
  - One-group multi-hop: every sufficient-set span must resolve to the
    SAME group. Cross-group multi-hop is rejected; widening groups needs
    an orchestrator-approved grouping-protocol amendment before freeze.
"""

from __future__ import annotations

import hashlib
import json


def load_jsonl_nodes(path: str) -> list[dict]:
  out = []
  with open(path, "r", encoding="utf-8") as fh:
    for line in fh:
      line = line.strip()
      if line:
        out.append(json.loads(line))
  return out


def load_split_map(path: str) -> dict:
  with open(path, "r", encoding="utf-8") as fh:
    return json.load(fh)


def norm_title(title: str) -> str:
  import re
  return re.sub(r"\s+", " ", title.replace("_", " ").strip()).lower()


def article_nodes_by_title(nodes: list[dict]) -> dict[str, dict]:
  index = {}
  for n in nodes:
    if n.get("kind") == "article":
      index[norm_title(n.get("text", ""))] = n
  return index


def group_articles(split_map: dict, group: str) -> tuple[list[str], str]:
  """Return (articles, split) for a group. Raises on unknown/mixed groups."""
  groups = split_map.get("groups", {})
  if group not in groups:
    raise ValueError(f"unknown group (id only, no content): {group[:60]}")
  rec = groups[group]
  split = rec.get("split")
  articles = rec.get("articles", [])
  if split not in ("train", "dev", "heldout"):
    raise ValueError(f"group has invalid split: {split!r}")
  if not articles:
    raise ValueError("group has no articles")
  return list(articles), split


def evidence_units_for_group(nodes: list[dict], titles: list[str],
                             kinds: tuple = ("sentence", "paragraph"),
                             per_article_cap: int = 8) -> list[dict]:
  """Candidate evidence units (node ids + text) for scaffolding.

  Returns short units only (<= 600 chars) so scaffolds stay reviewable.
  Deterministic order (sorted node_id). Counts only — no content filtering.
  """
  by_title = article_nodes_by_title(nodes)
  wanted_ids = set()
  title_to_id = {}
  for t in titles:
    node = by_title.get(norm_title(t))
    if node is None:
      raise ValueError("scaffold article resolves to no corpus node")
    title_to_id[norm_title(t)] = node["node_id"]
  # Map article node -> descendant sentences/paragraphs via parent chains.
  parent = {n["node_id"]: n.get("parent_id") for n in nodes}
  kind_of = {n["node_id"]: n.get("kind") for n in nodes}
  text_of = {n["node_id"]: n.get("text", "") for n in nodes}

  def root_article(nid: str) -> str | None:
    cur = nid
    seen = 0
    while cur and seen < 8:
      if kind_of.get(cur) == "article":
        return cur
      cur = parent.get(cur)
      seen += 1
    return None

  article_ids = set(title_to_id.values())
  units = []
  per_article: dict[str, int] = {a: 0 for a in article_ids}
  for n in sorted(nodes, key=lambda d: d.get("node_id", "")):
    if n.get("kind") not in kinds:
      continue
    art = root_article(n["node_id"])
    if art not in article_ids:
      continue
    if per_article[art] >= per_article_cap:
      continue
    text = n.get("text", "")
    if not text.strip() or len(text) > 600:
      continue
    per_article[art] += 1
    units.append({"node_id": n["node_id"], "kind": n["kind"],
                  "article": art, "text": text})
  return units


def make_scaffold(question_id: str, group: str, split: str,
                  units: list[dict]) -> dict:
  """Blank draft scaffold: human fills text/answer/sufficient sets.

  Provenance starts as decision=pending with empty identities: the author
  fills author/author_model on completion, and the INDEPENDENT verifier
  (different person/model) records decision=approve + rationale + the
  content hash AFTER reviewing. Tooling never fabricates approvals.
  """
  return {
    "question_id": question_id,
    "text": "",
    "split": split,
    "question_type": "",
    "meta": {"source_articles": [], "group": group},
    "candidate_units": units,
    "evidence": {"sufficient_sets": [], "is_multi_hop": False,
                 "reference_hop_chains": []},
    "hard_negatives": [],
    "labels": {"answer_text": "", "answerability": ""},
    "provenance": {"author": "", "author_model": "", "verifier": "",
                   "verifier_model": "", "decision": "pending",
                   "rationale": "", "content_hash": ""},
    "_instructions": ("Human author: write question text grounded in "
                      "candidate_units; pick sufficient_sets as exact node "
                      "spans; add >=1 hard negative; independent verifier "
                      "approves with rationale + content hash."),
  }


def scaffold_id(group: str, n: int, split: str) -> str:
  h = hashlib.sha256(f"{group}\x00{n}\x00{split}".encode()).hexdigest()[:8]
  return f"qa-{split}-{h}"
