"""Deterministic hard-negative CANDIDATE mining (stdlib only, no embeddings/LLM).

Negative types:
  sibling_paragraph  — other paragraphs under the same section
  neighbor_sentence  — adjacent sentences in the same paragraph
  linked_article     — unit whose article is reachable via cross-link
  token_overlap_nearmiss — high token-overlap non-evidence unit. This is a
    stdlib lexical proxy. It is NOT BM25 and must never be labeled as such.
  entity_confusion   — unit from another article in the SAME confusable group
  same_group_distractor — any non-evidence unit from the same group

Output entries are CANDIDATES (reviewed=False). A candidate becomes an
evidence-grade hard negative only when a human confirms it does not answer
the question and sets reviewed=True. Lexical/topological mining alone never
establishes non-answering status.

All functions take node dicts (from derive.load_jsonl_nodes) and evidence
node ids, and return [{node_id, negative_type, reviewed}] with no content
in logs.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> set[str]:
  return set(_WORD.findall(text.lower()))


def mine_hard_negatives(nodes: list[dict], evidence_ids: set[str],
                        group_article_ids: set[str],
                        group_titles: dict[str, str] | None = None,
                        per_type_cap: int = 3) -> list[dict]:
  by_id = {n["node_id"]: n for n in nodes}
  out: list[dict] = []

  def add(nid: str, ntype: str) -> None:
    if nid in evidence_ids:
      return
    if nid in (o["node_id"] for o in out):
      return
    node = by_id.get(nid, {})
    if node.get("kind") not in ("sentence", "paragraph"):
      return
    # Candidates only: independent human review sets reviewed=True.
    out.append({"node_id": nid, "negative_type": ntype, "reviewed": False})

  # Parent map for sibling/neighbor strata.
  parent = {n["node_id"]: n.get("parent_id") for n in nodes}
  children: dict[str, list[str]] = {}
  for n in nodes:
    p = n.get("parent_id")
    if p:
      children.setdefault(p, []).append(n["node_id"])
  for c in children.values():
    c.sort()

  # sibling_paragraph: paragraphs sharing a section with evidence. For
  # sentence evidence, climb to the section (grandparent) first.
  section_of: dict[str, str] = {}
  for nid, node in by_id.items():
    if node.get("kind") != "paragraph":
      continue
    section_of[nid] = node.get("parent_id", "")
  ev_sections: set[str] = set()
  for e in evidence_ids:
    node = by_id.get(e, {})
    if node.get("kind") == "paragraph":
      ev_sections.add(node.get("parent_id", ""))
    elif node.get("kind") == "sentence":
      ev_sections.add(section_of.get(parent.get(e, ""), ""))
  for n in sorted(by_id):
    node = by_id[n]
    if node.get("kind") != "paragraph":
      continue
    if node.get("parent_id") in ev_sections and n not in evidence_ids:
      # Exclude the evidence sentence's own paragraph only if it is itself
      # evidence; other paragraphs in the section are true siblings.
      if n in evidence_ids:
        continue
      add(n, "sibling_paragraph")
      if sum(1 for o in out if o["negative_type"] == "sibling_paragraph") >= per_type_cap:
        break
  # neighbor_sentence: adjacent sentence under same paragraph parent.
  for e in sorted(evidence_ids):
    sibs = children.get(parent.get(e, ""), [])
    if e in sibs:
      i = sibs.index(e)
      for j in (i - 1, i + 1):
        if 0 <= j < len(sibs):
          add(sibs[j], "neighbor_sentence")
  # linked_article: first sentence/paragraph of a linked article.
  linked: set[str] = set()
  for e in evidence_ids:
    node = by_id.get(e, {})
    cur = e
    for _ in range(8):  # walk up to the article
      if by_id.get(cur, {}).get("kind") == "article":
        break
      cur = parent.get(cur, "")
    art = by_id.get(cur, {})
    for t in art.get("links", []) or []:
      linked.add(t)
  for n in sorted(by_id):
    node = by_id[n]
    if node.get("kind") not in ("sentence", "paragraph"):
      continue
    # attribute unit to its article
    cur, art_id = n, None
    for _ in range(8):
      if by_id.get(cur, {}).get("kind") == "article":
        art_id = cur
        break
      cur = parent.get(cur, "")
    if art_id in linked and n not in evidence_ids:
      add(n, "linked_article")
      if sum(1 for o in out if o["negative_type"] == "linked_article") >= per_type_cap:
        break
  # token_overlap_nearmiss: stdlib token-overlap lexical proxy against
  # evidence text. NOT BM25 — no index, no IDF, no ranking model.
  ev_toks: set[str] = set()
  for e in evidence_ids:
    ev_toks |= tokens(by_id.get(e, {}).get("text", ""))
  scored = []
  for n, node in by_id.items():
    if node.get("kind") not in ("sentence", "paragraph"):
      continue
    if n in evidence_ids:
      continue
    t = tokens(node.get("text", ""))
    if not t:
      continue
    overlap = len(t & ev_toks) / max(1, len(t | ev_toks))
    if overlap > 0.15:
      scored.append((overlap, n))
  scored.sort(reverse=True)
  for _, n in scored[:per_type_cap]:
    add(n, "token_overlap_nearmiss")
  # entity_confusion / same_group_distractor: non-evidence units whose
  # article is in the same group (confusable by construction).
  for n in sorted(by_id):
    node = by_id[n]
    if node.get("kind") not in ("sentence", "paragraph"):
      continue
    if n in evidence_ids:
      continue
    cur = n
    art_id = None
    for _ in range(8):
      if by_id.get(cur, {}).get("kind") == "article":
        art_id = cur
        break
      cur = parent.get(cur, "")
    if art_id in group_article_ids:
      ntype = "entity_confusion" if len(group_article_ids) > 1 else "same_group_distractor"
      add(n, ntype)
      if sum(1 for o in out if o["negative_type"] == ntype) >= per_type_cap:
        break
  return out
