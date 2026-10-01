"""Train / dev / sealed-heldout split assignment and custodian separation.

Design:
- Deterministic seeded-hash assignment: split = f(sha256(seed + question_id)).
- Sealed held-out labels live in a SEPARATE file owned by the custodian.
- ``HeldoutCustodian`` refuses to disclose labels unless ``allow_heldout=true``
  is passed explicitly (benchmark phase only). Dev code paths pass nothing.
- OPAQUE seal verification (``verify_seal_opaque`` / ``seal_hash``) hashes raw
  bytes WITHOUT parsing or printing labels, so freeze validation can confirm
  the sealed artifact without inspecting it.
- HONEST LIMITATION: all agents run as the same OS user, so file permissions
  cannot truly seal labels and no encryption theater is implemented (it would
  not add a real boundary under one UID). Sealing here is procedural
  (separate file, access gate, opaque hash, audit log), not a kernel security
  boundary. True isolation requires the orchestrator to withhold the sealed
  file from development workers.

No real benchmark questions exist yet; freeze is blocked until they are pinned.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

TRAIN_FRACTION = 0.70
DEV_FRACTION = 0.15
# Remainder (0.15) -> heldout.
SPLITS = ("train", "dev", "heldout")

CUSTODIAN_ENV_VAR = "HELDOUT_CUSTODIAN_MODE"
CUSTODIAN_AUDIT_FILE = "heldout_access_log.jsonl"


def assign_split(question_id: str, seed: str) -> str:
  digest = hashlib.sha256(f"{seed}\x00{question_id}".encode("utf-8")).hexdigest()
  value = int(digest[:8], 16) / 0xFFFFFFFF
  if value < TRAIN_FRACTION:
    return "train"
  if value < TRAIN_FRACTION + DEV_FRACTION:
    return "dev"
  return "heldout"


def assign_splits(question_ids: list[str], seed: str) -> dict[str, str]:
  return {qid: assign_split(qid, seed) for qid in question_ids}


def sha256_bytes_of_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def verify_seal_opaque(labels_path: str, expected_sha256: str) -> bool:
  """Confirm the sealed file's bytes WITHOUT parsing or printing labels.

  Returns True iff the raw-byte SHA-256 matches. Raises FileNotFoundError
  when the sealed file is absent (fail closed).
  """
  if not os.path.isfile(labels_path):
    raise FileNotFoundError(f"sealed labels file missing: {labels_path}")
  return sha256_bytes_of_file(labels_path) == expected_sha256


def validate_questions_file(path: str) -> dict:
  """Schema-check a questions file WITHOUT touching sealed labels.

  Returns {"ids": [...], "errors": [...]}. Checks: top-level list, each entry
  has non-empty question_id/text, unique ids, split (if present) valid.
  """
  with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
  errors: list[str] = []
  ids: list[str] = []
  if not isinstance(data, list):
    return {"ids": [], "errors": ["questions file must be a JSON list"]}
  seen: set[str] = set()
  for i, entry in enumerate(data):
    if not isinstance(entry, dict):
      errors.append(f"entry {i}: not an object")
      continue
    qid = entry.get("question_id")
    if not qid or not isinstance(qid, str):
      errors.append(f"entry {i}: missing/empty question_id")
      continue
    if qid in seen:
      errors.append(f"duplicate question_id: {qid}")
    seen.add(qid)
    ids.append(qid)
    if not entry.get("text") or not isinstance(entry.get("text"), str):
      errors.append(f"{qid}: missing/empty text")
    if "split" in entry and entry["split"] not in SPLITS:
      errors.append(f"{qid}: invalid split {entry['split']!r}")
  return {"ids": ids, "errors": errors}


class HeldoutAccessDenied(RuntimeError):
  pass


@dataclass
class HeldoutCustodian:
  """Gatekeeper for sealed held-out labels (procedural custody, see module doc).

  ``labels_path`` points at the sealed file. ``load_labels`` raises
  ``HeldoutAccessDenied`` unless ``allow_heldout=True`` AND the custodian
  environment variable is set, optionally verifies the opaque seal hash, and
  appends every granted access to an audit log.

  Custody audit (append-only): every successful access logs accessor identity,
  role, purpose, timestamp_utc, labels_path, seal_sha256 at access time,
  question_ids actually read, and granted_by. Fails closed on empty/unknown
  accessor, role, or purpose. No delete/overwrite path.
  """

  labels_path: str
  audit_path: str = CUSTODIAN_AUDIT_FILE
  _cache: dict | None = field(default=None, repr=False)

  def seal_hash(self) -> str:
    """Opaque content hash of the sealed file (no parsing, no printing)."""
    return sha256_bytes_of_file(self.labels_path)

  def load_labels(
    self,
    *,
    allow_heldout: bool = False,
    accessor: str = "",
    role: str = "",
    purpose: str = "",
    granted_by: str = "",
    expected_sha256: str | None = None,
  ) -> dict:
    """Load held-out labels with full custody audit.

    Args:
      allow_heldout: Must be True (benchmark phase only).
      accessor: Identity of the accessor (e.g., "benchmark-runner-v1").
                Required, non-empty. Fail closed if empty/unknown.
      role: Role of the accessor (e.g., "evaluator", "auditor").
            Required, non-empty. Fail closed if empty/unknown.
      purpose: Purpose of access (e.g., "final-evaluation", "audit-review").
               Required, non-empty. Fail closed if empty/unknown.
      granted_by: Who granted this access (e.g., "orchestrator").
                  Required, non-empty. Fail closed if empty/unknown.
      expected_sha256: Optional seal hash to verify against current file.

    Returns:
      Dict of held-out labels (question_id -> label).

    Raises:
      HeldoutAccessDenied: If any gate fails or required fields are missing.
    """
    # Fail closed on missing identity/role/purpose/granted_by
    for field_name, field_value in (
      ("accessor", accessor),
      ("role", role),
      ("purpose", purpose),
      ("granted_by", granted_by),
    ):
      if not field_value or not isinstance(field_value, str) or not field_value.strip():
        raise HeldoutAccessDenied(
          f"held-out access denied: missing required field '{field_name}' "
          "(must be non-empty string)"
        )

    if not allow_heldout:
      raise HeldoutAccessDenied(
        "held-out labels are sealed: pass allow_heldout=True only in the "
        "benchmark phase (custodian-supervised)"
      )
    if os.environ.get(CUSTODIAN_ENV_VAR) != "benchmark":
      raise HeldoutAccessDenied(
        f"held-out access requires {CUSTODIAN_ENV_VAR}=benchmark "
        "(set only by the custodian/orchestrator at benchmark time)"
      )
    if expected_sha256 is not None and not verify_seal_opaque(
      self.labels_path, expected_sha256
    ):
      raise HeldoutAccessDenied("sealed labels hash mismatch: artifact changed since seal")
    if self._cache is None:
      with open(self.labels_path, "r", encoding="utf-8") as fh:
        self._cache = json.load(fh)

    # Capture question_ids actually read
    question_ids = list(self._cache.keys()) if isinstance(self._cache, dict) else []

    # Audit with full custody fields
    self._audit(
      accessor=accessor.strip(),
      role=role.strip(),
      purpose=purpose.strip(),
      granted_by=granted_by.strip(),
      question_ids=question_ids,
      seal_sha256=self.seal_hash(),
    )
    return dict(self._cache)

  def _audit(
    self,
    *,
    accessor: str,
    role: str,
    purpose: str,
    granted_by: str,
    question_ids: list[str],
    seal_sha256: str,
  ) -> None:
    import datetime

    entry = {
      "accessor": accessor,
      "role": role,
      "purpose": purpose,
      "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "labels_path": self.labels_path,
      "seal_sha256": seal_sha256,
      "question_ids": sorted(question_ids),
      "granted_by": granted_by,
    }
    with open(self.audit_path, "a", encoding="utf-8") as fh:
      fh.write(json.dumps(entry, sort_keys=True) + "\n")

  def question_ids_for(self, questions_path: str, split: str, seed: str) -> list[str]:
    """List question ids for a NON-heldout split without touching labels."""
    if split == "heldout":
      raise HeldoutAccessDenied(
        "enumerate held-out ids only through the benchmark runner with allow_heldout=True"
      )
    with open(questions_path, "r", encoding="utf-8") as fh:
      questions = json.load(fh)
    ids = [q["question_id"] for q in questions]
    return [qid for qid in ids if assign_split(qid, seed) == split]


def norm_title(title: str) -> str:
  """Title normalization aligned read-only with corpus/build_pilot.norm_key."""
  import re

  return re.sub(r"\s+", " ", title.replace("_", " ").strip()).lower()


# Question categories. Controlled QA needs full source provenance; public
# reference questions are dev-only comparability anchors with benchmark
# provenance (never training or heldout supervision).
CATEGORY_CONTROLLED = "controlled"
CATEGORY_PUBLIC_REFERENCE = "public_reference"
QUESTION_CATEGORIES = (CATEGORY_CONTROLLED, CATEGORY_PUBLIC_REFERENCE)


def build_article_index(nodes: list) -> dict:
  """Index article-kind corpus nodes for provenance resolution.

  Returns {"by_id": {node_id: {"title_key", "group"}}, "by_title":
  {title_key: [node_ids]}}. ``group`` comes from the node's
  ``meta.split_group`` (pilot builder records it) and may be None.
  """
  by_id: dict[str, dict] = {}
  by_title: dict[str, list[str]] = {}
  for node in nodes:
    kind = node.kind if hasattr(node, "kind") else node.get("kind")
    if kind != "article":
      continue
    nid = node.node_id if hasattr(node, "node_id") else node.get("node_id")
    text = node.text if hasattr(node, "text") else node.get("text", "")
    meta = node.meta if hasattr(node, "meta") else node.get("meta", {})
    title_key = norm_title(text)
    by_id[nid] = {"title_key": title_key, "group": meta.get("split_group")}
    by_title.setdefault(title_key, []).append(nid)
  return {"by_id": by_id, "by_title": by_title}


def validate_group_map(data: object, corpus_articles: set[str] | None = None) -> dict:
  """Validate a group-aware split map (pilot shape: groups->{split, articles}).

  Enforces: complete assignments (every group has a valid split and a
  non-empty article list), unique articles across groups (hence supervised
  split disjointness), and — when ``corpus_articles`` (norm_key'd corpus
  article titles) is given — that every mapped article resolves to a real
  corpus node. Returns {"article_to_split": {...}, "errors": [...]} with at
  most 3 example titles per error class (never question/answer content).
  """
  errors: list[str] = []
  article_to_split: dict[str, str] = {}
  article_to_group: dict[str, str] = {}
  if not isinstance(data, dict) or not isinstance(data.get("groups"), dict):
    return {
      "article_to_split": {},
      "article_to_group": {},
      "errors": ["split map must have a 'groups' object"],
    }
  groups = data["groups"]
  if not groups:
    return {
      "article_to_split": {},
      "article_to_group": {},
      "errors": ["split map declares no groups"],
    }
  if "seed" not in data:
    errors.append("split map missing seed")
  for group_key, rec in groups.items():
    if not isinstance(rec, dict):
      errors.append(f"group {str(group_key)[:60]}: not an object")
      continue
    split = rec.get("split")
    if split not in SPLITS:
      errors.append(f"group {str(group_key)[:60]}: invalid split {split!r}")
    articles = rec.get("articles")
    if not isinstance(articles, list) or not articles:
      errors.append(f"group {str(group_key)[:60]}: no articles assigned")
      continue
    for title in articles:
      if not isinstance(title, str) or not title.strip():
        errors.append(f"group {str(group_key)[:60]}: empty article title")
        continue
      key = norm_title(title)
      if key in article_to_split:
        errors.append(
          f"article assigned to multiple groups: {title[:80]} "
          f"({article_to_split[key]} vs {split})"
        )
      else:
        article_to_split[key] = split
        article_to_group[key] = str(group_key)
  if corpus_articles is not None:
    unresolved = [t for t in article_to_split if t not in corpus_articles]
    if unresolved:
      errors.append(
        f"{len(unresolved)} mapped articles resolve to no corpus node "
        f"(e.g. {unresolved[:3]})"
      )
  return {
    "article_to_split": article_to_split,
    "article_to_group": article_to_group,
    "errors": errors,
  }


def validate_question_provenance(
  questions: list[dict],
  *,
  article_index: dict,
  map_groups: dict,
  article_to_group: dict,
  split_seed: str,
  use_map_splits: bool,
) -> dict:
  """Strict QA source provenance. NO implicit exemption for absent metadata.

  Controlled (train/dev/heldout) questions MUST carry nonempty
  ``meta.source_articles`` (canonical article node ids, or pilot title
  identifiers with unambiguous resolution) AND a nonempty ``meta.group``.
  Group-only is insufficient: every source must resolve to a real corpus
  article node, belong to the claimed group, and sit in the QA's split;
  cross-split source sets and inconsistent group metadata are rejected.

  ``public_reference`` questions are dev-only: they require
  ``meta.source_benchmark`` + ``meta.source_revision`` +
  ``meta.original_question_id`` and are rejected on train/heldout. Their
  ``source_articles`` are optional; unresolvable/absent sources mean
  retrieval ground truth is UNKNOWN (callers must use None), never zero.

  The searchable corpus is SHARED across splits: resolution never filters by
  split; split equality is enforced on the QA declaration, not the corpus.

  Returns {"results": {qid: {"category", "group", "split", "sources",
  "source_groups", "source_splits", "evidence_groups",
  "ground_truth"}}, "errors": [...]}. Errors carry question ids and counts
  only — never question/answer/label text.
  """
  errors: list[str] = []
  results: dict[str, dict] = {}
  by_id = article_index.get("by_id", {})
  by_title = article_index.get("by_title", {})

  def resolve_source(source: str) -> str | None:
    """Canonical node id, or None. Sets errors for unknown/ambiguous."""
    if source in by_id:
      return source
    matches = by_title.get(norm_title(source), [])
    if len(matches) == 1:
      return matches[0]
    return None

  def group_split(group_key: str) -> str | None:
    if use_map_splits:
      split = map_groups.get(group_key)
      return split if split in SPLITS else None
    if split_seed in ("", "TBD"):
      return None
    return assign_split(group_key, split_seed)

  for entry in questions:
    if not isinstance(entry, dict):
      continue
    qid = entry.get("question_id", "?")
    if not isinstance(qid, str) or not qid:
      continue
    declared = entry.get("split", "dev")
    meta = entry.get("meta", {}) if isinstance(entry.get("meta"), dict) else {}
    category = meta.get("category", CATEGORY_CONTROLLED)
    if category not in QUESTION_CATEGORIES:
      errors.append(f"{qid}: unknown question category {str(category)[:40]!r}")
      continue

    if category == CATEGORY_PUBLIC_REFERENCE:
      if declared != "dev":
        errors.append(
          f"{qid}: public_reference allowed only on dev, not {declared}"
        )
        continue
      missing = [
        f
        for f in ("source_benchmark", "source_revision", "original_question_id")
        if not isinstance(meta.get(f), str) or not meta.get(f, "").strip()
      ]
      if missing:
        errors.append(f"{qid}: public_reference missing {sorted(missing)}")
        continue
      raw_sources = meta.get("source_articles", [])
      if raw_sources and (
        not isinstance(raw_sources, list)
        or any(not isinstance(s, str) or not s.strip() for s in raw_sources)
      ):
        errors.append(f"{qid}: public_reference source_articles malformed")
        continue
      resolved = [resolve_source(s) for s in raw_sources] if raw_sources else []
      known = bool(resolved) and all(r is not None for r in resolved)
      results[qid] = {
        "category": CATEGORY_PUBLIC_REFERENCE,
        "group": None,
        "split": declared,
        "sources": [r for r in resolved if r is not None],
        "ground_truth": "known" if known else "unknown",
      }
      continue

    # --- controlled QA: full provenance mandatory ---
    raw_sources = meta.get("source_articles")
    if (
      not isinstance(raw_sources, list)
      or not raw_sources
      or any(not isinstance(s, str) or not s.strip() for s in raw_sources)
    ):
      errors.append(f"{qid}: controlled QA requires nonempty source_articles")
      continue
    group = meta.get("group")
    if not isinstance(group, str) or not group.strip():
      errors.append(f"{qid}: controlled QA requires an explicit group")
      continue
    if use_map_splits and group not in map_groups:
      errors.append(f"{qid}: unknown group for split map")
      continue
    gsplit = group_split(group)
    if gsplit is None:
      errors.append(f"{qid}: group assignment unresolvable (no map, seed unpinned)")
      continue
    # Explicit declared-group check: the DECLARED meta.group's own split
    # must equal the declared rec.split, independent of what the sources
    # say. (Split names in messages are not secret; group keys/titles
    # stay out.)
    if declared != gsplit:
      errors.append(
        f"{qid}: declared group split {gsplit} != declared split {declared}")
      continue
    # meta.evidence_groups (optional): when present it must be a well-formed
    # list that includes the declared group, with every listed group known
    # and sitting in the declared split.
    ev_groups = meta.get("evidence_groups")
    if ev_groups is not None:
      if (not isinstance(ev_groups, list) or not ev_groups or any(
          not isinstance(g, str) or not g.strip() for g in ev_groups)):
        errors.append(f"{qid}: meta.evidence_groups malformed")
        continue
      if group not in ev_groups:
        errors.append(f"{qid}: meta.evidence_groups missing declared group")
        continue
      ev_bad = False
      for gkey in ev_groups:
        s = map_groups.get(gkey) if use_map_splits else group_split(gkey)
        if s is None:
          errors.append(f"{qid}: meta.evidence_groups has unknown group")
          ev_bad = True
          break
        if s != declared:
          errors.append(f"{qid}: meta.evidence_groups outside declared split")
          ev_bad = True
          break
      if ev_bad:
        continue
    node_ids: list[str] = []
    bad = False
    for source in raw_sources:
      nid = resolve_source(source)
      if nid is None:
        matches = by_title.get(norm_title(source), [])
        reason = "ambiguous" if len(matches) > 1 else "unknown"
        errors.append(f"{qid}: {reason} source article")
        bad = True
        continue
      node_ids.append(nid)
    if bad:
      continue
    # Effective group per source: map membership, else corpus node metadata.
    # (Split names in messages are not secret; group keys/titles stay out.)
    source_groups: dict[str, None] = {}
    ungrouped = 0
    for nid in node_ids:
      title_key = by_id[nid]["title_key"]
      node_group = article_to_group.get(title_key, by_id[nid]["group"])
      if node_group is None:
        ungrouped += 1
      else:
        source_groups[node_group] = None
    if ungrouped and use_map_splits:
      errors.append(f"{qid}: {ungrouped} source(s) group unresolvable against map and corpus")
      continue
    if ungrouped and not use_map_splits:
      # Seeded-hash mode without a map: no group authority beyond the
      # question's explicit claim + deterministic split derivation below.
      # Sources still resolve to real corpus nodes (no dangling refs).
      source_groups = {group: None}
    # Same-split rule: multiple GROUPS are allowed iff they all sit in ONE
    # split. Only genuinely cross-SPLIT source sets are rejected.
    split_of: dict[str, str | None] = {}
    for gkey in source_groups:
      split_of[gkey] = (map_groups.get(gkey) if use_map_splits
                        else group_split(gkey))
    if any(s is None for s in split_of.values()):
      n_bad = sum(1 for s in split_of.values() if s is None)
      errors.append(f"{qid}: {n_bad} source group(s) split unresolvable")
      continue
    distinct_splits = sorted({str(s) for s in split_of.values()})
    if len(distinct_splits) > 1:
      errors.append(
        f"{qid}: source articles span multiple splits "
        f"{distinct_splits} (cross-split chain)"
      )
      continue
    if group not in source_groups:
      errors.append(f"{qid}: inconsistent group metadata for source article(s)")
      continue
    if declared != distinct_splits[0]:
      errors.append(
        f"{qid}: declared split {declared} != source group split "
        f"{distinct_splits[0]}")
      continue
    results[qid] = {
      "category": CATEGORY_CONTROLLED,
      "group": group,
      "split": declared,
      "sources": node_ids,
      "source_groups": sorted(source_groups),
      "source_splits": distinct_splits,
      "evidence_groups": list(ev_groups) if ev_groups is not None else sorted(
        source_groups),
      "ground_truth": "known",
    }
  return {"results": results, "errors": errors}
