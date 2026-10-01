"""Independent evidence verification + sealing (stdlib only).

verify_draft(rec, nodes, *, article_index, map_groups, article_to_group, ...)
is the second-reader gate run on a completed draft BEFORE it enters any
train/dev/heldout set. Provenance context is REQUIRED — there is no
context-free verification path; omitting it raises TypeError and empty or
malformed context fails closed with explicit metadata errors. Checks:
  1. qa_schema validity (spans, negatives, readings, tautology,
     type/answerability consistency, provenance shape).
  2. Every sufficient-set span's text matches the corpus node with
     CODE-POINT equality (Python str indices, NOT bytes): offset slice when
     offsets are given, else full-text equality. This proves the draft
     quotes the corpus exactly — it does NOT prove the span answers the
     question, entails the answer, or is sufficient; those judgments belong
     to the named author and independent verifier.
  3. Source coverage: every evidence span's article must appear in the
     declared meta.source_articles (same group alone is insufficient).
  4. Same-split rule: every evidence span's article resolves to a group
      whose SPLIT equals the declared split. Multi-group chains are
      allowed iff every involved group sits in the same split
      (train->train ALLOW; train->heldout, dev->heldout, train->dev
      REJECT). Group equality is never required and never checked.
  5. No mixed-split chain via substrate validate_question_provenance.
  6. Hard negatives: node exists; no identity OR ancestor/descendant
     overlap with any evidence span; reviewed=True (a human confirmed
     non-answering status — lexical mining alone never establishes this).
  7. Approval binding: provenance.decision must be "approve" with a
     nonempty rationale, verifier distinct from author, and
     provenance.content_hash equal to draft_content_hash(rec) — any content
     change after approval invalidates it. Tooling never fabricates
     approvals; the actual reviewer named in provenance determines
     sufficiency, ambiguity, absence, and negative correctness.

seal_records() verifies every record at its current hash (duplicates fail,
missing/stale approvals fail, reviewer==author fails) and only then
partitions drafts into questions + train/dev labels + sealed heldout.
There is no unchecked dict-splitting seal path. Heldout output requires
allow_heldout=True AND HELDOUT_CUSTODIAN_MODE=benchmark (custodian path).

Custody honesty: all workers share one OS user, so there is no kernel
boundary — custody is procedural (separate file, access gate, opaque
hash, audit log). True isolation = the orchestrator withholds the sealed
file from development workers.

Log hygiene: all errors carry question ids/counts only, never Q/A text.
"""

from __future__ import annotations

import hashlib
import json
import os

from .qa_schema import validate_draft_record

CUSTODIAN_ENV_VAR = "HELDOUT_CUSTODIAN_MODE"

# Draft keys excluded from the content hash: authoring scaffolding and the
# approval block itself (the hash binds what was approved, not the approval).
_NON_SEMANTIC_KEYS = frozenset({"_instructions", "candidate_units", "provenance"})


def draft_content_hash(rec: dict) -> str:
  """Content-bound hash of a draft's semantic contents (qid/text/split/type,
  meta, evidence, hard negatives, labels). Approvals bind to this hash."""
  semantic = {k: v for k, v in rec.items() if k not in _NON_SEMANTIC_KEYS}
  canonical = json.dumps(semantic, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False)
  return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _node_index(nodes: list[dict]) -> dict:
  return {n["node_id"]: n for n in nodes}


def _article_of(nodes_by_id: dict, nid: str) -> str | None:
  cur = nid
  for _ in range(10):
    node = nodes_by_id.get(cur)
    if node is None:
      return None
    if node.get("kind") == "article":
      return cur
    cur = node.get("parent_id", "")
    if not cur:
      return None
  return None


def _title_key(title: str) -> str:
  import re
  return re.sub(r"\s+", " ", title.replace("_", " ").strip()).lower()


def _resolve_source(source: str, nodes_by_id: dict, article_index: dict) -> str | None:
  """Canonical article node id for a declared source, else None.

  Accepts a canonical node id directly, else requires a title resolving to
  exactly one corpus article node. Unknown/ambiguous sources return None
  (callers report id-only errors, never content).
  """
  if source in nodes_by_id and nodes_by_id[source].get("kind") == "article":
    return source
  by_title = article_index.get("by_title", {})
  matches = by_title.get(_title_key(source), [])
  article_matches = [m for m in matches
                     if nodes_by_id.get(m, {}).get("kind") == "article"]
  if len(article_matches) == 1:
    return article_matches[0]
  return None


def _ancestor_chain(nodes_by_id: dict, nid: str) -> list[str]:
  """Self + ancestors up the parent chain (bounded)."""
  chain = [nid]
  cur = nid
  for _ in range(10):
    parent = nodes_by_id.get(cur, {}).get("parent_id", "")
    if not parent:
      break
    chain.append(parent)
    cur = parent
  return chain


def verify_draft(rec: dict, nodes: list[dict], *, article_index: dict,
                 map_groups: dict, article_to_group: dict,
                 split_seed: str = "", use_map_splits: bool = True) -> list[str]:
  errors = validate_draft_record(rec)
  qid = rec.get("question_id", "?") if isinstance(rec, dict) else "?"
  # Fail closed on incomplete verification context: without the corpus
  # index, split map, and group table the provenance checks below would
  # silently pass, so missing context is an error, never a skip.
  if (not isinstance(article_index, dict) or not article_index.get("by_id")
      or not article_index.get("by_title")):
    return errors + [f"{qid}: incomplete verification context (article_index)"]
  if not isinstance(map_groups, dict) or not map_groups:
    return errors + [f"{qid}: incomplete verification context (map_groups)"]
  if not isinstance(article_to_group, dict) or not article_to_group:
    return errors + [f"{qid}: incomplete verification context (article_to_group)"]
  if not use_map_splits and (not isinstance(split_seed, str) or not split_seed):
    return errors + [f"{qid}: incomplete verification context (split_seed)"]
  if errors:
    return errors
  by_id = _node_index(nodes)
  group = rec["meta"]["group"]
  # Declared sources resolve to canonical article node ids up front: same
  # group alone is insufficient — every evidence article must be declared.
  declared: set[str] = set()
  for source in rec["meta"]["source_articles"]:
    nid = _resolve_source(source, by_id, article_index)
    if nid is None:
      errors.append(f"{qid}: declared source unresolvable or ambiguous")
    else:
      declared.add(nid)
  ev_ids: set[str] = set()
  ev_articles: set[str] = set()
  unanswerable = rec["labels"]["answerability"] == "unanswerable"
  if not unanswerable:
    for i, s in enumerate(rec["evidence"]["sufficient_sets"]):
      for j, span in enumerate(s):
        nid = span["node_id"]
        node = by_id.get(nid)
        if node is None:
          errors.append(f"{qid}: set {i} span {j} unknown node")
          continue
        ev_ids.add(nid)
        # Code-point-exact verification against the corpus node (Python str
        # slicing counts Unicode code points, NOT bytes/UTF-8 length, and
        # NOT grapheme clusters). Equality only — never entailment.
        corpus_text = node.get("text", "")
        cs, ce = span.get("char_start"), span.get("char_end")
        if cs is not None or ce is not None:
          if (isinstance(cs, bool) or isinstance(ce, bool)
              or not isinstance(cs, int) or not isinstance(ce, int)
              or not 0 <= cs < ce <= len(corpus_text)):
            errors.append(f"{qid}: set {i} span {j} bad char offsets")
            continue
          if span.get("text", "") != corpus_text[cs:ce]:
            errors.append(f"{qid}: set {i} span {j} text/offset mismatch")
        else:
          if span.get("text", "") != corpus_text:
            errors.append(f"{qid}: set {i} span {j} text != corpus node text")
        art = _article_of(by_id, nid)
        if art is None:
          errors.append(f"{qid}: set {i} span {j} article unresolvable")
          continue
        ev_articles.add(art)
        # Same-split rule: resolve the span's article -> group -> SPLIT and
        # compare SPLITS (not groups) against the declared split. A span
        # from another group of the SAME split is allowed; a span from any
        # other split is leakage and fails. Group equality is never checked.
        art_title_key = _title_key(by_id[art].get("text", ""))
        ag = article_to_group.get(art_title_key,
                                  by_id[art].get("meta", {}).get("split_group"))
        if not isinstance(ag, str) or not ag.strip():
          errors.append(f"{qid}: set {i} span {j} group unresolvable")
          continue
        if use_map_splits:
          asplit = map_groups.get(ag)
          if asplit not in ("train", "dev", "heldout"):
            errors.append(f"{qid}: set {i} span {j} group split unresolvable")
            continue
        else:
          from substrate.splits import assign_split
          asplit = assign_split(ag, split_seed)
        if asplit != rec["split"]:
          errors.append(f"{qid}: set {i} span {j} evidence split != declared split")
          continue
        eff_groups = rec["meta"].get("evidence_groups") or [group]
        if ag not in eff_groups:
          errors.append(f"{qid}: set {i} span {j} group not in meta.evidence_groups")
    missing_sources = ev_articles - declared
    if missing_sources:
      errors.append(
        f"{qid}: {len(missing_sources)} evidence article(s) missing "
        "from declared source_articles")
  for i, n in enumerate(rec.get("hard_negatives", [])):
    nid = n.get("node_id", "")
    if nid not in by_id:
      errors.append(f"{qid}: hard negative {i} unknown node")
      continue
    # Ancestor/descendant overlap: a negative containing an evidence span
    # (ancestor), contained in one (descendant), or identical all leak.
    neg_chain = set(_ancestor_chain(by_id, nid))
    if neg_chain & ev_ids:
      errors.append(f"{qid}: hard negative {i} overlaps evidence")
      continue
    contained = any(nid in _ancestor_chain(by_id, e) for e in ev_ids)
    if contained:
      errors.append(f"{qid}: hard negative {i} overlaps evidence")
      continue
    if not n.get("reviewed"):
      errors.append(f"{qid}: hard negative {i} not independently reviewed")
  # Cross-split / provenance gate via the substrate (ids only in errors).
  from substrate.splits import validate_question_provenance
  q = {"question_id": qid, "text": "placeholder",
       "split": rec["split"], "meta": rec["meta"]}
  out = validate_question_provenance(
    [q], article_index=article_index, map_groups=map_groups,
    article_to_group=article_to_group, split_seed=split_seed,
    use_map_splits=use_map_splits)
  errors.extend(out["errors"])
  # Approval binding: recorded human approval, content-bound. Missing,
  # non-approve, self-reviewed, rationale-free, or stale approvals fail.
  prov = rec.get("provenance", {})
  if not isinstance(prov, dict) or prov.get("decision") != "approve":
    errors.append(f"{qid}: missing or non-approve verification decision")
  else:
    if prov.get("author") == prov.get("verifier"):
      errors.append(f"{qid}: verifier must differ from author")
    if not isinstance(prov.get("rationale"), str) or not prov["rationale"].strip():
      errors.append(f"{qid}: approval needs nonempty rationale")
    if prov.get("content_hash") != draft_content_hash(rec):
      errors.append(f"{qid}: approval stale (content changed after approval)")
  return errors


def seal_hash_of_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def seal_records(records: list[dict], *, nodes: list[dict],
                 article_index: dict, map_groups: dict,
                 article_to_group: dict, split_seed: str = "",
                 use_map_splits: bool = True,
                 allow_heldout: bool = False) -> dict:
  """Verify every record at its current hash, then partition for sealing.

  Fails closed: duplicate question ids fail; any verification error fails
  (including missing/stale approvals and reviewer==author); heldout drafts
  additionally require allow_heldout=True AND custodian env benchmark.
  Returns questions (evaluator-private, meta retained for the substrate
  provenance check — never retriever input), train/dev labels, sealed
  heldout labels, and a content manifest (ids/counts/hashes only).
  """
  if not isinstance(records, list) or not records:
    raise ValueError("seal requires a nonempty record list")
  ids = [r.get("question_id", "?") for r in records]
  if len(set(ids)) != len(ids):
    dupes = len(ids) - len(set(ids))
    raise ValueError(f"seal refused: {dupes} duplicate question id(s)")
  held = [r for r in records if r.get("split") == "heldout"]
  if held and not (allow_heldout and os.environ.get(CUSTODIAN_ENV_VAR) == "benchmark"):
    raise PermissionError(
      f"{len(held)} heldout draft(s) need custodian seal "
      f"(allow_heldout=True + {CUSTODIAN_ENV_VAR}=benchmark)")
  failures: dict[str, int] = {}
  for r in records:
    errs = verify_draft(r, nodes, article_index=article_index,
                        map_groups=map_groups, article_to_group=article_to_group,
                        split_seed=split_seed, use_map_splits=use_map_splits)
    if errs:
      failures[str(r.get("question_id", "?"))] = len(errs)
  if failures:
    raise ValueError(
      f"seal refused: {len(failures)} record(s) unverified")
  from .qa_schema import draft_to_label_entry, draft_to_question_entry
  questions = [draft_to_question_entry(r) for r in records]
  labels = {r["question_id"]: draft_to_label_entry(r) for r in records
            if r.get("split") in ("train", "dev")}
  sealed = {r["question_id"]: draft_to_label_entry(r) for r in records
            if r.get("split") == "heldout"}
  manifest = {
    "records": len(records),
    "splits": {s: sum(1 for r in records if r.get("split") == s)
               for s in ("train", "dev", "heldout")},
    "content_hashes": {r["question_id"]: draft_content_hash(r) for r in records},
  }
  return {"questions": questions, "labels": labels, "heldout_sealed": sealed,
          "manifest": manifest}
