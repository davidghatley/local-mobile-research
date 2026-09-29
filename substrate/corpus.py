"""Corpus snapshot model: hierarchy validation, canonical hashing, JSONL I/O.

The REAL pinned corpus artifact does not exist yet (reference audit pending).
This module defines the format so the freeze can pin it deterministically.
"""

from __future__ import annotations

from .types import CorpusNode, canonical_json, sha256_text

VALID_KINDS = ("corpus", "cluster", "article", "section", "paragraph", "sentence")

# Expected parent kind for the primary hierarchy edge (DAG cross-links exempt).
EXPECTED_PARENT = {
  "cluster": "corpus",
  "article": "cluster",
  "section": "article",
  "paragraph": "section",
  "sentence": "paragraph",
}


def validate_hierarchy(nodes: list[CorpusNode]) -> list[str]:
  """Return a list of validation error strings (empty means valid)."""
  errors: list[str] = []
  by_id = {n.node_id: n for n in nodes}
  if len(by_id) != len(nodes):
    errors.append("duplicate node_id values present")
  for n in nodes:
    if n.kind not in VALID_KINDS:
      errors.append(f"node {n.node_id}: unknown kind {n.kind!r}")
    if not n.node_id:
      errors.append("node with empty node_id")
    expected = EXPECTED_PARENT.get(n.kind)
    if expected is None:
      continue  # corpus root
    if n.parent_id is None:
      errors.append(f"node {n.node_id}: kind {n.kind} requires parent_id")
    elif n.parent_id not in by_id:
      errors.append(f"node {n.node_id}: parent {n.parent_id} missing")
    elif by_id[n.parent_id].kind != expected:
      errors.append(
        f"node {n.node_id}: kind {n.kind} expected parent kind {expected}, "
        f"got {by_id[n.parent_id].kind}"
      )
    for target in n.links:
      if target not in by_id:
        errors.append(f"node {n.node_id}: cross-link target {target} missing")
      elif target == n.node_id:
        errors.append(f"node {n.node_id}: self cross-link")
  return errors


def canonical_corpus_text(nodes: list[CorpusNode]) -> str:
  """Canonical serialization used for the corpus hash (sorted by node_id)."""
  ordered = sorted((n.to_dict() for n in nodes), key=lambda d: d["node_id"])
  return canonical_json(ordered)


def corpus_hash(nodes: list[CorpusNode]) -> str:
  return sha256_text(canonical_corpus_text(nodes))


def nodes_to_jsonl(nodes: list[CorpusNode]) -> str:
  ordered = sorted(nodes, key=lambda n: n.node_id)
  lines = [canonical_json(n.to_dict()) for n in ordered]
  return "\n".join(lines) + ("\n" if lines else "")


def nodes_from_jsonl(text: str) -> list[CorpusNode]:
  import json

  nodes = []
  for lineno, line in enumerate(text.splitlines(), start=1):
    line = line.strip()
    if line:
      try:
        nodes.append(CorpusNode.from_dict(json.loads(line)))
      except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"corpus JSONL line {lineno}: {exc}") from exc
  return nodes


def load_corpus_file(path: str) -> list[CorpusNode]:
  """Strictly load a corpus JSONL file. Malformed lines raise (fail closed)."""
  with open(path, "r", encoding="utf-8") as fh:
    return nodes_from_jsonl(fh.read())


def hash_corpus_file(path: str) -> tuple[list[CorpusNode], str]:
  """Load, hierarchy-validate, and hash a corpus file. Returns (nodes, hash)."""
  nodes = load_corpus_file(path)
  errors = validate_hierarchy(nodes)
  if errors:
    raise ValueError(f"corpus hierarchy invalid: {errors[:5]}")
  return nodes, corpus_hash(nodes)
