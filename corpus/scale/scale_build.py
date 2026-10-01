"""Offline deterministic converter for the distractor-scale corpus tier 1.

Mirrors corpus/build_offline.py (the core build) converter-for-converter and
cap-for-cap, but publishes into a DISJOINT node-id namespace under
corpus/scale/ so a scale node can never collide with a core node. The core
297-article corpus is FROZEN: this builder only READS core artifacts (to
de-duplicate against them and to cite the core hash one-directionally).

Pipeline: validate inputs -> candidate-order selection -> mechanical core
de-duplication (pageid / normalized title / content hash) -> intra-tier pageid
de-duplication -> convert (build_pilot converter fns, same caps) ->
substrate hierarchy validation -> stage to temp dir -> verify staged bytes ->
atomic publish (os.replace).

Node-id namespace (disjoint from core by construction):
    root        corpus:scale-distractors      (core: corpus:pilot)
    cluster     dc:<slug>                     (core: cluster:<slug>)
    article     d:<slug>                      (core: a:<slug>)
    section     ds:<slug>:i:<nn>              (core: s:<slug>:i:<nn>)
    paragraph   dp:<slug>:i:<nn>:j:<nnn>      (core: p:<slug>:i:<nn>:j:<nnn>)
    sentence    dt:<slug>:i:<nn>:j:<nnn>:k:<nn>   (core: t:<slug>:...)

DETERMINISM IS LOAD-BEARING. Every published artifact is a pure function of
(raw snapshots bytes, distractor_candidates.json bytes, this file's bytes,
core corpus.jsonl bytes, the revision string). No wall clock, no PRNG, no
dict-order dependence, no network. `built_utc` is deliberately NOT written
into any published artifact; wall-clock build times go to the excluded
build_run_log.jsonl so that two builds are byte-identical. See
corpus/scale/tests/test_scale_corpus.py::test_double_build_is_byte_identical.

This module performs NO network I/O: it imports corpus/build_pilot.py for the
converter functions and constants only, and never calls api_get/fetch_article.

Usage:
    python3 corpus/scale/scale_build.py [--raw-dir D] [--out D] [--stage D]
                                        [--revision ID] [--check]
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # corpus/scale
ROOT = os.path.dirname(os.path.dirname(HERE))              # project root

sys.path.insert(0, os.path.join(ROOT, "corpus"))   # build_pilot (converter only)
sys.path.insert(0, ROOT)                           # substrate (read-only)

import build_pilot as bp  # noqa: E402  (converter + constants; no fetch calls)

from substrate.corpus import (  # noqa: E402
  canonical_corpus_text,
  corpus_hash,
  load_corpus_file,
  nodes_from_jsonl,
  nodes_to_jsonl,
  validate_hierarchy,
)
from substrate.types import CorpusNode  # noqa: E402

# --- scale-tier constants ----------------------------------------------------

SCALE_REVISION_DEFAULT = "scale-tier1-940-r1"
SCALE_ROOT_NODE_ID = "corpus:scale-distractors"
SCALE_ROOT_TEXT = ("Round 0 distractor-scale corpus tier 1 (irrelevant distractor "
                   "material; experimental research only)")

# Prefix table. Used both to build ids and to prove namespace disjointness.
NS_ROOT = "corpus:"
NS_CLUSTER = "dc:"
NS_ARTICLE = "d:"
NS_SECTION = "ds:"
NS_PARAGRAPH = "dp:"
NS_SENTENCE = "dt:"

REQUIRED_SNAP_KEYS = ("requested_title", "normalized_title", "pageid",
                      "revid", "timestamp", "source_url", "wikitext",
                      "outlinks", "cluster", "split_group", "content_sha256")

STATS_KEYS = ("balanced_spans_removed", "balanced_span_chars",
              "templates_removed", "template_chars", "templates_rescued",
              "tables_closed", "tables_unclosed", "nslinks_removed",
              "nslink_chars", "comments_removed", "include_tags_removed",
              "refs_removed", "gallery_captions_kept", "orphan_lines_dropped",
              "paras_chunked", "sentences_hardsplit", "para_cap_hits")

CORE_DEDUP_FIELDS = ("pageid", "normalized_title", "content_sha256")


def sha256_file(path):
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


# --- core (read-only) --------------------------------------------------------

def core_index(core_dir=None):
  """Read the frozen core corpus and build the de-duplication index.

  READ-ONLY. Returns (index, provenance) where index holds the three
  mechanical overlap keys for all 297 core articles.
  """
  core_dir = core_dir or os.path.join(ROOT, "corpus")
  nodes = load_corpus_file(os.path.join(core_dir, "corpus.jsonl"))
  errors = validate_hierarchy(nodes)
  if errors:
    raise RuntimeError(f"core corpus hierarchy invalid: {errors[:3]}")
  index = {"pageid": set(), "normalized_title": set(), "content_sha256": set()}
  titles = []
  for n in nodes:
    if n.kind != "article":
      continue
    index["pageid"].add(str(n.meta.get("pageid", "")))
    index["normalized_title"].add(bp.norm_key(n.text))
    index["content_sha256"].add(n.meta.get("content_sha256", ""))
    titles.append(n.text)
  with open(os.path.join(core_dir, "provenance.json"), encoding="utf-8") as fh:
    prov = json.load(fh)
  # Recompute rather than trust: the scale layer must cite a hash it verified.
  recomputed = corpus_hash(nodes)
  declared = prov.get("corpus_hash_sha256")
  if declared and declared != recomputed:
    raise RuntimeError(
      f"core provenance corpus_hash_sha256 {declared} != recomputed {recomputed}")
  return index, {"article_count": len(titles), "titles": titles,
                 "node_count": len(nodes), "corpus_hash": recomputed}


# --- snapshot loading --------------------------------------------------------

def load_snapshots(raw_dir):
  """Return (snaps, problems). No network. Verifies keys + content hash."""
  snaps, problems = [], []
  for fname in sorted(os.listdir(raw_dir)):
    if not fname.endswith(".json"):
      continue
    path = os.path.join(raw_dir, fname)
    try:
      with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    except Exception as exc:  # noqa: BLE001
      problems.append({"file": fname, "error": f"unreadable: {exc}"})
      continue
    missing = [k for k in REQUIRED_SNAP_KEYS if k not in d]
    if missing:
      problems.append({"file": fname, "error": f"missing keys {missing}"})
      continue
    if not isinstance(d["wikitext"], str):
      problems.append({"file": fname, "error": "wikitext is not a string"})
      continue
    if hashlib.sha256(d["wikitext"].encode("utf-8")).hexdigest() != d["content_sha256"]:
      problems.append({"file": fname, "error": "content_sha256 mismatch"})
      continue
    d["_file"] = fname
    d["_sha256"] = sha256_file(path)
    snaps.append(d)
  return snaps, problems


def is_redirect_stub(wikitext):
  """True when the fetched page body is only a #REDIRECT line (no article prose)."""
  head = wikitext.lstrip()[:40].upper()
  return head.startswith("#REDIRECT") or head.startswith("#REDIRECTION")


# --- selection / de-duplication ----------------------------------------------

def select_ordered(snaps, candidates):
  """Candidate-file order; unmatched raws appended (recorded).

  `candidates` MUST be the scale list (corpus/scale/distractor_candidates.json),
  never the core list: the predeclared scale order is what defines the tier.
  """
  by_req = {}
  for s in snaps:
    by_req.setdefault(bp.norm_key(s["requested_title"]), []).append(s)
  ordered, used, notes = [], set(), []
  for e in candidates:
    key = bp.norm_key(e["t"])
    cands = sorted((s for s in by_req.get(key, []) if id(s) not in used),
                   key=lambda s: (s["normalized_title"], str(s["pageid"])))
    if not cands:
      notes.append({"candidate": e["t"], "status": "no_snapshot_on_disk"})
      continue
    ordered.append(cands[0])
    used.add(id(cands[0]))
    for extra in cands[1:]:
      notes.append({"candidate": e["t"], "status": "duplicate_raw",
                    "file": extra["_file"]})
  rest = sorted((s for s in snaps if id(s) not in used),
                key=lambda s: (s["normalized_title"], str(s["pageid"])))
  for s in rest:
    notes.append({"candidate": s["requested_title"],
                  "status": "raw_not_in_candidate_order_appended",
                  "file": s["_file"]})
  return ordered + rest, notes


def reject_core_overlap(snaps, index):
  """MECHANICAL de-duplication against the frozen core 297.

  Rejects on pageid, normalized title, or content-hash collision. Every
  rejection is recorded with the colliding core article. Mechanical only: no
  fuzzy/semantic matching, no tolerance.
  """
  kept, rejected = [], []
  for s in snaps:
    hits = []
    if str(s["pageid"]) in index["pageid"]:
      hits.append("pageid")
    if bp.norm_key(s["normalized_title"]) in index["normalized_title"]:
      hits.append("normalized_title")
    if s["content_sha256"] in index["content_sha256"]:
      hits.append("content_sha256")
    if hits:
      rejected.append({
        "file": s["_file"],
        "normalized_title": s["normalized_title"],
        "requested_title": s["requested_title"],
        "pageid": s["pageid"],
        "content_sha256": s["content_sha256"],
        "colliding_fields": sorted(hits),
        "reason": "mechanical overlap with frozen core corpus on " +
                  " + ".join(sorted(hits)),
      })
      continue
    kept.append(s)
  return kept, rejected


def dedup_pageids(snaps):
  """Keep the first snapshot per pageid in tier order; record the rest."""
  seen, kept, excluded = {}, [], []
  for s in snaps:
    key = str(s["pageid"])
    if key in seen:
      excluded.append({"normalized_title": s["normalized_title"],
                       "pageid": s["pageid"], "file": s["_file"],
                       "reason": "duplicate pageid within tier; kept " + seen[key]})
      continue
    seen[key] = s["normalized_title"]
    kept.append(s)
  return kept, excluded


# --- conversion --------------------------------------------------------------

def _title_keys(snap):
  """Identity keys for one snapshot: exact title first, then casefolded.

  Wikipedia titles are case-sensitive after the first character, so 'ABBA'
  and 'Abba' are distinct articles. Keying identity on bp.norm_key alone
  silently merges them, so the exact normalized title is the identity key and
  norm_key is only a secondary lookup for cross-link resolution.
  """
  return (snorm := snap["normalized_title"]), bp.norm_key(snorm)


def build_nodes(snaps, cluster_of):
  """Mirror of the core node schema with a DISJOINT namespace.

  Returns (nodes, art_of_node, removal, per_article, in_corpus_links).
  """
  # Pass 1: assign article node ids in tier order, disambiguating slug reuse.
  title_to_art = {}      # exact normalized title -> article node id
  used_ids = set()
  for s in snaps:
    slug = bp.slugify(s["normalized_title"])
    aid = NS_ARTICLE + slug
    if aid in used_ids:
      aid = f"{NS_ARTICLE}{slug}~{s['pageid']}"
    used_ids.add(aid)
    title_to_art[s["normalized_title"]] = aid

  # Secondary (casefolded) index for cross-link resolution only. Ambiguous
  # keys are dropped rather than resolved arbitrarily, so a link can never
  # silently attach to the wrong one of two case-variant articles.
  fold_to_art = {}
  ambiguous_folds = set()
  for t, aid in title_to_art.items():
    k = bp.norm_key(t)
    if k in fold_to_art:
      ambiguous_folds.add(k)
    else:
      fold_to_art[k] = aid
  for k in ambiguous_folds:
    fold_to_art.pop(k, None)

  def resolve(target):
    aid = title_to_art.get(target)
    if aid is not None:
      return aid
    return fold_to_art.get(bp.norm_key(target))

  nodes = [CorpusNode(node_id=SCALE_ROOT_NODE_ID, kind="corpus", text=SCALE_ROOT_TEXT,
                      meta={"license_note": "mixed CC BY-SA per-article; see article nodes",
                            "role": "irrelevant distractor material; not evidence-bearing"})]

  clusters = sorted({cluster_of(s) for s in snaps})
  cluster_id = {}
  for c in clusters:
    cid = NS_CLUSTER + bp.slugify(c)
    cluster_id[c] = cid
    nodes.append(CorpusNode(node_id=cid, kind="cluster", text=c,
                            parent_id=SCALE_ROOT_NODE_ID,
                            meta={"kind": "topic"}))

  art_of_node, removal, per_article = {}, collections.Counter(), {}
  para_links_total = 0
  for s in snaps:
    aid = title_to_art[s["normalized_title"]]
    slug = aid[len(NS_ARTICLE):]
    cid = cluster_id[cluster_of(s)]
    st = collections.Counter()
    aliases = tuple([s["requested_title"]]
                    if s["requested_title"] != s["normalized_title"] else [])
    revid = s.get("revid")
    nodes.append(CorpusNode(
      node_id=aid, kind="article", text=s["normalized_title"], parent_id=cid,
      aliases=aliases,
      meta={"pageid": str(s["pageid"]),
            "revid": "" if revid is None else str(revid),
            "timestamp": s["timestamp"],
            "source_url": s["source_url"],
            "license": bp.LICENSE,
            "license_source": "builder constant corpus/build_pilot.py:LICENSE; "
                              "fetcher recorded no per-article license field",
            "cluster": cluster_of(s),
            "split_group": s["split_group"],
            "content_sha256": s["content_sha256"]}))
    art_of_node[aid] = s
    sects = bp.convert_article(s["normalized_title"], s["pageid"], revid,
                               s["timestamp"], s["wikitext"], stats=st,
                               sent_cap=None)
    removal.update(st)
    per_article[s["normalized_title"]] = {k: st[k] for k in STATS_KEYS}
    for i, (head, level, paras) in enumerate(sects):
      sid = f"{NS_SECTION}{slug}:i:{i:02d}"
      nodes.append(CorpusNode(node_id=sid, kind="section", text=head or "(untitled)",
                              parent_id=aid, meta={"level": str(level)}))
      for j, (ptext, praw) in enumerate(paras):
        pid = f"{NS_PARAGRAPH}{slug}:i:{i:02d}:j:{j:03d}"
        plinks = []
        for tgt in bp.para_links(praw):
          tgt_aid = resolve(tgt)
          if tgt_aid and tgt_aid != aid and tgt_aid not in plinks:
            plinks.append(tgt_aid)
        para_links_total += len(plinks)
        nodes.append(CorpusNode(node_id=pid, kind="paragraph", text=ptext,
                                parent_id=sid, links=tuple(plinks),
                                meta={"char_len": str(len(ptext))}))
        for k, sent in enumerate(bp.split_sentences(ptext, cap=None)):
          nodes.append(CorpusNode(
            node_id=f"{NS_SENTENCE}{slug}:i:{i:02d}:j:{j:03d}:k:{k:02d}",
            kind="sentence", text=sent, parent_id=pid,
            meta={"char_len": str(len(sent))}))

  # Patch article-level outlinks. The fetcher's outlinks array is empty for
  # every tier-1 snapshot (it never requested prop=links), so this normally
  # contributes nothing; article-level DAG edges, where present, come from
  # paragraph-level resolution above.
  patched = []
  article_links = 0
  for n in nodes:
    if n.kind == "article":
      s = art_of_node[n.node_id]
      targets = []
      for t in s.get("outlinks", []):
        tgt = resolve(t)
        if tgt and tgt != n.node_id and tgt not in targets:
          targets.append(tgt)
      article_links += len(targets)
      patched.append(CorpusNode(node_id=n.node_id, kind=n.kind, text=n.text,
                                parent_id=n.parent_id, links=tuple(targets),
                                aliases=n.aliases, meta=n.meta))
    else:
      patched.append(n)
  links_total = article_links + para_links_total
  return patched, art_of_node, dict(removal), per_article, links_total


# --- build -------------------------------------------------------------------

def _rel(path):
  return os.path.relpath(path, ROOT).replace(os.sep, "/")


def run_offline(raw_dir, stage_dir, revision, tier_name="tier_1k",
                tier_requested=1000, cluster_source="candidate"):
  """Full offline build into stage_dir. Returns a summary dict. No network."""
  # Clean the stage dir first: a stale artifact from an earlier build would be
  # silently measured by disk_footprint.built_tier_bytes and published.
  if os.path.isdir(stage_dir):
    shutil.rmtree(stage_dir)
  os.makedirs(stage_dir, exist_ok=True)
  scale_dir = HERE
  cand_path = os.path.join(scale_dir, "distractor_candidates.json")
  with open(cand_path, encoding="utf-8") as fh:
    cand = json.load(fh)
  candidates = list(cand["articles"]) + list(cand.get("spares", []))
  builder_path = os.path.abspath(__file__)

  # Cluster attribution: the predeclared scale candidate list is authoritative;
  # the fetcher wrote the placeholder "distractor" into every snapshot.
  cand_cluster = {e["t"]: e["c"] for e in candidates}

  def cluster_of(s):
    if cluster_source == "candidate":
      return cand_cluster.get(s["requested_title"], s["cluster"])
    return s["cluster"]

  snaps, problems = load_snapshots(raw_dir)
  ordered, order_notes = select_ordered(snaps, candidates)

  core_idx, core_info = core_index()
  after_core, excluded_core = reject_core_overlap(ordered, core_idx)
  kept, excluded_dupes = dedup_pageids(after_core)

  nodes, art_of_node, removal, per_article, links_total = build_nodes(kept, cluster_of)
  errors = validate_hierarchy(nodes)
  if errors:
    raise RuntimeError(f"scale hierarchy invalid: {errors[:5]}")

  # NO split map is emitted for the scale tier, deliberately.
  #
  # The distractor tier is irrelevant material: it is never evaluated, never used
  # as evidence, and never enters a measured train/dev/heldout question set. Every
  # tier-1 snapshot carries split_group="distractor", so a group map here would be
  # a single group whose bp.assign_split() label is an arbitrary hash artefact that
  # implies a measurement partition that does not exist. Emitting one would be
  # fabricating a split. Instead the tier manifest records split_group as
  # non-measurement and corpus/scale/tests asserts that no scale article appears in
  # the core split_map.json, which is the property that actually matters for
  # leakage: distractor mass cannot enter a measured split.
  split_group_values = sorted({s["split_group"] for s in kept})
  arts = {bp.norm_key(n.text) for n in nodes if n.kind == "article"}

  chash = corpus_hash(nodes)
  jsonl = nodes_to_jsonl(nodes)
  names = ["distractor.jsonl", "scale_provenance.json",
           "scale_input_manifest.json", "tier_1k.json", "scale_build_manifest.json"]
  paths = {n: os.path.join(stage_dir, n) for n in names}
  with open(paths["distractor.jsonl"], "w", encoding="utf-8") as fh:
    fh.write(jsonl)

  node_counts = {k: sum(1 for n in nodes if n.kind == k)
                 for k in ("corpus", "cluster", "article", "section",
                           "paragraph", "sentence")}
  redirect_stubs = [s["normalized_title"] for s in kept
                    if is_redirect_stub(s["wikitext"])]

  # --- per-tier manifest --------------------------------------------------
  def snap_record(s):
    revid = s.get("revid")
    return {
      "file": s["_file"],
      "sha256": s["_sha256"],
      "pageid": s["pageid"],
      "revid": revid,
      "timestamp": s["timestamp"],
      "source_url": s["source_url"],
      "license": bp.LICENSE,
      "license_source": "builder constant (fetcher recorded no license field)",
      "bytes": len(s["wikitext"].encode("utf-8")),
      "wikitext_bytes_recorded_by_fetcher": s.get("bytes"),
      "content_sha256": s["content_sha256"],
      "requested_title": s["requested_title"],
      "normalized_title": s["normalized_title"],
      "node_id": None,  # filled below
      "cluster": cluster_of(s),
      "split_group": s["split_group"],
      "is_redirect_stub": is_redirect_stub(s["wikitext"]),
      "revid_available": revid is not None,
    }

  node_id_by_title = {n.text: n.node_id for n in nodes if n.kind == "article"}
  records = []
  for s in kept:
    r = snap_record(s)
    r["node_id"] = node_id_by_title[s["normalized_title"]]
    records.append(r)

  def dir_bytes(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
      for fn in filenames:
        fp = os.path.join(dirpath, fn)
        if os.path.isfile(fp) and not os.path.islink(fp):
          total += os.path.getsize(fp)
    return total

  raw_bytes = dir_bytes(raw_dir)
  submitted = len(candidates)

  tier = {
    "tier": tier_name,
    "revision": revision,
    "role": ("IRRELEVANT DISTRACTOR MATERIAL. This tier carries no evidence, is not "
             "part of any question set, and exists only to provide background mass "
             "for scale/regime experiments. The 297-article core corpus is the only "
             "evidence-bearing semantic base."),
    "article_counts": {
      "submitted_candidates": submitted,
      "raw_snapshots_on_disk": len(snaps),
      "passed_core_dedup": len(after_core),
      "built_articles": len(kept),
      "rejected_core_overlap": len(excluded_core),
      "rejected_duplicate_pageid": len(excluded_dupes),
      "snapshot_load_problems": len(problems),
      "redirect_stub_articles": len(redirect_stubs),
      "substantive_articles_excluding_redirect_stubs": len(kept) - len(redirect_stubs),
      "core_articles_referenced": core_info["article_count"],
    },
    "tier_target": {
      "requested": tier_requested,
      "achieved": len(kept),
      "met": len(kept) >= tier_requested,
      "shortfall": max(0, tier_requested - len(kept)),
      "shortfall_reason": (
        "The predeclared scale candidate list contains 960 titles. 20 were "
        "parked not_found by the fetcher and no re-fetch was performed for this "
        "tier, so the achievable maximum on disk is 940. The ~1000 target was "
        "therefore NOT met; 940 is the honest achieved count."
        if len(kept) < tier_requested else None),
    },
    "node_counts": node_counts,
    "node_ids": {"total": len(nodes),
                 "namespace": {"root": NS_ROOT, "cluster": NS_CLUSTER,
                               "article": NS_ARTICLE, "section": NS_SECTION,
                               "paragraph": NS_PARAGRAPH, "sentence": NS_SENTENCE}},
    "byte_sizes": {
      "distractor_jsonl_bytes": len(jsonl.encode("utf-8")),
      "raw_snapshot_bytes": raw_bytes,
      "raw_snapshot_file_count": len(snaps),
    },
    "disk_footprint": {
      "raw_dir_bytes": raw_bytes,
      "raw_dir_mib": round(raw_bytes / 1048576, 2),
      "distractor_jsonl_bytes": os.path.getsize(paths["distractor.jsonl"]),
      "note": ("Raw snapshots dominate disk use. Every other built artifact's "
               "exact byte size is pinned in scale_build_manifest.json, which is "
               "written after this file. corpus/scale/raw/ is git-ignored and "
               "recoverable only while the per-file hashes in this manifest "
               "still match."),
    },
    "core_reference": {
      "direction": "one-directional: this tier cites the core; the core cites nothing about scale",
      "core_corpus_path": "corpus/corpus.jsonl",
      "core_corpus_sha256": sha256_file(os.path.join(ROOT, "corpus", "corpus.jsonl")),
      "core_corpus_hash": core_info["corpus_hash"],
      "core_build_manifest_sha256": sha256_file(os.path.join(ROOT, "corpus", "build_manifest.json")),
      "core_article_count": core_info["article_count"],
    },
    "merged_view": {
      "definition": ("canonical corpus hash over the union of core nodes and scale "
                     "nodes; the two roots coexist because their namespaces are disjoint"),
      "core_nodes": core_info["node_count"],
      "core_articles": core_info["article_count"],
      "scale_nodes": len(nodes),
    },
    "excluded_core_overlap": excluded_core,
    "excluded_duplicate_pageid": excluded_dupes,
    "snapshot_load_problems": problems,
    "order_notes": order_notes,
    "selection_independence": {
      "attestation": (
        "PROCEDURAL, NOT EMPIRICAL. The 960-title candidate list was frozen in "
        "corpus/scale/distractor_candidates.json before any fetch and before any "
        "question construction, with seed 'scale-v1', and its method string "
        "declares it independent of benchmark answers. No scale title was chosen "
        "by looking at a held-out answer, and no scale article is evidence-bearing. "
        "This is a procedural guarantee about a curated list; it is not a "
        "statistical independence test."),
      "candidate_seed": cand.get("seed"),
      "candidate_method": cand.get("method"),
      "candidate_list_sha256": sha256_file(cand_path),
      "declared_excludes_core_297": True,
      "verified_core_overlap_count": len(excluded_core),
      "verification_method": ("mechanical set intersection on pageid, normalized title "
                              "(bp.norm_key), and content sha256 against all 297 core "
                              "article nodes"),
    },
    "builder": {
      "path": "corpus/scale/scale_build.py",
      "sha256": sha256_file(builder_path),
      "converter": "corpus/build_pilot.py converter fns (stats hooks, sent_cap=None)",
      "converter_sha256": sha256_file(os.path.join(ROOT, "corpus", "build_pilot.py")),
      "caps": {"max_paragraphs_per_article": bp.MAX_PAR_PER_ART,
               "max_sentences_per_paragraph": None,
               "sentence_omission": "none: all sentences preserved as nodes",
               "max_outlinks_per_article": bp.MAX_LINKS_PER_ART,
               "excluded_sections": sorted(bp.SKIP_SECTIONS)},
      "network": "none: the offline path never calls api_get/fetch_article",
      "determinism": ("pure function of raw bytes + candidate list + builder bytes + "
                      "core corpus bytes + revision; no clock, no PRNG"),
    },
    "attribution": {
      "license": bp.LICENSE,
      "license_note": bp.LICENSE_NOTE,
      "per_article_fields": ["source_url", "revid", "timestamp", "content_sha256"],
      "known_gap": (
        "revid is null in all 940 tier-1 snapshots: the fetcher requested "
        "rvprop=timestamp|user|comment|content and omitted 'ids', so no revision "
        "id was ever returned. No re-fetch was performed for this tier. "
        "Attribution is therefore pinned by source_url + revision timestamp + "
        "content sha256 rather than by oldid."),
      "revid_available_count": sum(1 for r in records if r["revid_available"]),
      "revid_missing_count": sum(1 for r in records if not r["revid_available"]),
    },
    "cluster_source": cluster_source,
    "split_assignment": {
      "split_map_emitted": False,
      "reason": ("No split map is emitted. This tier is irrelevant distractor material: "
                 "it is never evaluated, never evidence, and never part of a measured "
                 "train/dev/heldout question set. All snapshots carry the single "
                 "split_group 'distractor', so any group map would be one arbitrary "
                 "hash label implying a measurement partition that does not exist."),
      "observed_split_group_values": split_group_values,
      "measured_splits": [],
      "leakage_property": ("no scale article appears in the frozen core "
                           "corpus/split_map.json; asserted by "
                           "corpus/scale/tests/test_scale_corpus.py"),
    },
    "article_level_in_corpus_links": links_total,
    "redirect_stub_titles": redirect_stubs,
    "snapshots": records,
    "measurement_scope": (
      "ALL scale measurements are DESKTOP measurements. No Android or on-device "
      "performance claim may be derived from anything in this tier."),
  }
  with open(paths["tier_1k.json"], "w", encoding="utf-8") as fh:
    json.dump(tier, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")

  # --- provenance ----------------------------------------------------------
  prov = {
    "revision": revision,
    "tier": tier_name,
    "builder": "corpus/scale/scale_build.py (offline build, no network)",
    "built_utc": None,
    "built_utc_note": ("deliberately null: wall-clock time is excluded from published "
                       "artifacts so two builds are byte-identical; wall-clock times "
                       "are recorded in the git-ignored build_run_log.jsonl"),
    "method": cand.get("method"),
    "candidate_seed": cand.get("seed"),
    "selection_independence": tier["selection_independence"]["attestation"],
    "articles": len(kept),
    "node_counts": node_counts,
    "corpus_hash_sha256": chash,
    "canonical_text_sha256": hashlib.sha256(
      canonical_corpus_text(nodes).encode("utf-8")).hexdigest(),
    "conversion_caps": tier["builder"]["caps"],
    "removal_stats_totals": removal,
    "removal_stats_per_article": per_article,
    "validation_errors": errors,
    "split_assignment": tier["split_assignment"],
    "core_reference": tier["core_reference"],
    "excluded_core_overlap_count": len(excluded_core),
    "excluded_duplicate_pageid_count": len(excluded_dupes),
    "article_level_in_corpus_links": links_total,
    "articles_detail": [
      {"node_id": node_id_by_title[s["normalized_title"]],
       "requested_title": s["requested_title"],
       "normalized_title": s["normalized_title"],
       "pageid": s["pageid"],
       "revid": s.get("revid"),
       "timestamp": s["timestamp"],
       "source_url": s["source_url"],
       "license": bp.LICENSE,
       "cluster": cluster_of(s),
       "split_group": s["split_group"],
       "content_sha256": s["content_sha256"],
       "wikitext_bytes": len(s["wikitext"].encode("utf-8")),
       "outlinks_total": len(s.get("outlinks", [])),
       "outlinks_truncated": s.get("outlinks_truncated"),
       "is_redirect_stub": is_redirect_stub(s["wikitext"])}
      for s in kept],
  }
  with open(paths["scale_provenance.json"], "w", encoding="utf-8") as fh:
    json.dump(prov, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")

  # --- input manifest ------------------------------------------------------
  kept_titles = {s["normalized_title"] for s in kept}
  input_manifest = {
    "revision": revision,
    "candidate_list": {"path": "corpus/scale/distractor_candidates.json",
                       "sha256": sha256_file(cand_path),
                       "seed": cand.get("seed"),
                       "submitted": submitted,
                       "method": cand.get("method")},
    "builder": tier["builder"],
    "raw_dir": _rel(raw_dir),
    "raw_dir_sha256_of_contents": {
      "file_count": len(snaps),
      "aggregate_sha256": hashlib.sha256(
        "".join(f'{s["_file"]}:{s["_sha256"]}\n' for s in snaps).encode("utf-8")
      ).hexdigest(),
    },
    "snapshots": [{"file": s["_file"], "sha256": s["_sha256"],
                   "normalized_title": s["normalized_title"],
                   "pageid": s["pageid"], "revid": s.get("revid"),
                   "bytes": len(s["wikitext"].encode("utf-8")),
                   "included": s["normalized_title"] in kept_titles}
                  for s in snaps],
    "order_notes": order_notes,
    "excluded_core_overlap": excluded_core,
    "excluded_duplicate_pageid": excluded_dupes,
    "load_problems": problems,
  }
  with open(paths["scale_input_manifest.json"], "w", encoding="utf-8") as fh:
    json.dump(input_manifest, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")

  # --- verify staged bytes before any publish ------------------------------
  staged = nodes_from_jsonl(open(paths["distractor.jsonl"], encoding="utf-8").read())
  if corpus_hash(staged) != chash:
    raise RuntimeError("staged corpus hash mismatch; publish aborted")
  if validate_hierarchy(staged):
    raise RuntimeError("staged hierarchy invalid; publish aborted")
  if {n.node_id for n in staged} & core_node_ids():
    raise RuntimeError("staged node ids collide with core; publish aborted")

  manifest = {
    "revision": revision,
    "tier": tier_name,
    "role": tier["role"],
    "corpus_hash_sha256": chash,
    "core_reference": tier["core_reference"],
    "artifacts": [{"path": f"corpus/scale/{n}", "sha256": sha256_file(paths[n]),
                   "bytes": os.path.getsize(paths[n])}
                  for n in names if n != "scale_build_manifest.json"],
    "scale_input_manifest_sha256": sha256_file(paths["scale_input_manifest.json"]),
    "measurement_scope": tier["measurement_scope"],
  }
  with open(paths["scale_build_manifest.json"], "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")

  return {"revision": revision, "articles": len(kept), "nodes": len(nodes),
          "node_counts": node_counts, "corpus_hash": chash,
          "stage_dir": stage_dir, "paths": paths, "tier": tier,
          "excluded_core_overlap": len(excluded_core),
          "excluded_duplicate_pageid": len(excluded_dupes),
          "redirect_stubs": len(redirect_stubs),
          "tier_met": len(kept) >= tier_requested,
          "raw_bytes": raw_bytes,
          "jsonl_bytes": len(jsonl.encode("utf-8"))}


def core_node_ids():
  """Set of frozen core node ids (read-only) for the disjointness pre-publish gate."""
  nodes = load_corpus_file(os.path.join(ROOT, "corpus", "corpus.jsonl"))
  return {n.node_id for n in nodes}


def merged_view_hash():
  """Canonical corpus hash over core nodes + scale nodes (merged view)."""
  core = load_corpus_file(os.path.join(ROOT, "corpus", "corpus.jsonl"))
  scale = nodes_from_jsonl(
    open(os.path.join(HERE, "distractor.jsonl"), encoding="utf-8").read())
  return corpus_hash(core + scale), len(core), len(scale)


def publish(stage_dir, out_dir, names=("distractor.jsonl", "scale_provenance.json",
                                      "scale_input_manifest.json",
                                      "tier_1k.json",
                                      "scale_build_manifest.json")):
  """Atomically publish staged files: copy to a temp name in the DESTINATION
  directory (same filesystem) then os.replace, so readers never observe a
  partial file."""
  os.makedirs(out_dir, exist_ok=True)
  for name in names:
    if not os.path.isfile(os.path.join(stage_dir, name)):
      raise RuntimeError(f"stage missing {name}; publish aborted, nothing written")
  for name in names:
    tmp = os.path.join(out_dir, ".publish_tmp_" + name)
    shutil.copyfile(os.path.join(stage_dir, name), tmp)
    os.replace(tmp, os.path.join(out_dir, name))
  return [os.path.join(out_dir, n) for n in names]


def main(argv):
  import argparse  # noqa: E402
  ap = argparse.ArgumentParser(
    description="Offline-only distractor-scale tier build (no network).")
  ap.add_argument("--raw-dir", default=os.path.join(HERE, "raw"))
  ap.add_argument("--out", default=HERE)
  ap.add_argument("--stage", default=os.path.join(HERE, ".build_tmp"))
  ap.add_argument("--revision", default=SCALE_REVISION_DEFAULT)
  ap.add_argument("--tier", default="tier_1k")
  ap.add_argument("--tier-requested", type=int, default=1000)
  ap.add_argument("--cluster-source", default="candidate",
                  choices=("candidate", "snapshot"))
  ap.add_argument("--dry-run", action="store_true",
                  help="build and verify into the stage dir only; do not publish")
  args = ap.parse_args(argv)
  summary = run_offline(args.raw_dir, args.stage, args.revision,
                        tier_name=args.tier, tier_requested=args.tier_requested,
                        cluster_source=args.cluster_source)
  if args.dry_run:
    summary["published"] = []
    summary["dry_run"] = True
  else:
    summary["published"] = publish(args.stage, args.out)
  print(json.dumps({k: v for k, v in summary.items()
                    if k not in ("paths", "tier")}, indent=2, sort_keys=True))


if __name__ == "__main__":
  main(sys.argv[1:])