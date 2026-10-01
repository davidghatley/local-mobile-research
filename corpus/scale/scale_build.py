"""Offline deterministic converter for distractor-scale corpus.

Mirrors corpus/build_offline.py pipeline but with a DISJOINT node-id namespace
so it can never collide with the core 297-article corpus.

Pipeline: validate inputs -> candidate-order selection -> pageid dedup ->
convert (using build_pilot converter fns, uncapped sentences, removal stats) ->
substrate DAG validation -> stage to temp dir -> verify staged bytes ->
atomic publish (os.replace) + build manifest.

Key differences from build_offline.py:
  - Root node_id: "corpus:scale-distractors" (core uses "corpus:pilot")
  - Article node_ids: "d:<slug>" (core uses "a:<slug>")
  - Paragraph node_ids: "dp:<slug>:i:jj" (core uses "p:<slug>:i:jjj")
  - Sentence node_ids: "dt:<slug>:i:jj:k:kk" (core uses "t:<slug>:i:jj:k:kk")
  - All namespace prefixes deliberately chosen to be byte-disjoint from core.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys

from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
  # When running as `python3 corpus/scale/scale_build.py` from the project root,
  # __file__ is relative to cwd. HERE = corpus/scale.
  # The project root is two levels up from the scale/ directory.
  PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))  # .../local_mobile_research
  ROOT = PROJECT_ROOT
sys.path.insert(0, HERE)  # for build_pilot (converter only)
sys.path.insert(0, ROOT)  # for substrate (read-only validation/hashing)

import build_pilot as bp  # noqa: E402  (converter + constants; no fetch calls)

from substrate.corpus import (  # noqa: E402
  canonical_corpus_text,
  corpus_hash,
  nodes_from_jsonl,
  nodes_to_jsonl,
  validate_hierarchy,
)
from substrate.splits import validate_group_map  # noqa: E402
from substrate.types import CorpusNode  # noqa: E402

REQUIRED_SNAP_KEYS = ("requested_title", "normalized_title", "pageid",
                      "revid", "timestamp", "source_url", "wikitext",
                      "outlinks", "cluster", "split_group", "content_sha256")

STATS_KEYS = ("balanced_spans_removed", "balanced_span_chars",
              "templates_removed", "template_chars", "templates_rescued",
              "tables_closed", "tables_unclosed", "nslinks_removed",
              "nslink_chars", "comments_removed", "include_tags_removed",
              "refs_removed", "gallery_captions_kept", "orphan_lines_dropped",
              "paras_chunked", "sentences_hardsplit", "para_cap_hits")


def sha256_file(path):
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


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
    if hashlib.sha256(d["wikitext"].encode("utf-8")).hexdigest() != d["content_sha256"]:
      problems.append({"file": fname, "error": "content_sha256 mismatch"})
      continue
    d["_file"] = fname
    d["_sha256"] = sha256_file(path)
    snaps.append(d)
  return snaps, problems


def select_ordered(snaps, candidates):
  """Candidate-file order; unmatched raws appended (recorded)."""
  by_req = {}
  for s in snaps:
    by_req.setdefault(bp.norm_key(s["requested_title"]), []).append(s)
  ordered, used_ids, unmatched_notes = [], set(), []
  for e in candidates:
    key = bp.norm_key(e["t"])
    cands = [s for s in by_req.get(key, []) if id(s) not in used_ids]
    if not cands:
      unmatched_notes.append({"candidate": e["t"], "status": "no snapshot"})
      continue
    cands.sort(key=lambda s: s["normalized_title"])
    ordered.append(cands[0])
    used_ids.add(id(cands[0]))
    for extra in cands[1:]:
      unmatched_notes.append({"candidate": e["t"], "status": "duplicate raw",
                              "file": extra["_file"]})
  rest = sorted((s for s in snaps if id(s) not in used_ids),
                key=lambda s: s["normalized_title"])
  for s in rest:
    unmatched_notes.append({"candidate": s["requested_title"],
                            "status": "raw not in candidate order; appended",
                            "file": s["_file"]})
  return ordered + rest, unmatched_notes


def dedup_pageids(snaps):
  """Keep first per pageid in candidate order; record exclusions."""
  seen, kept, excluded = {}, [], []
  for s in snaps:
    if s["pageid"] in seen:
      excluded.append({"normalized_title": s["normalized_title"],
                       "pageid": s["pageid"], "file": s["_file"],
                       "reason": "duplicate pageid; kept " + seen[s["pageid"]]})
      continue
    seen[s["pageid"]] = s["normalized_title"]
    kept.append(s)
  return kept, excluded


def build_nodes(snaps):
  """Mirror of the pilot node schema with DISJOINT namespace.

  Node ID namespace:
    root:        corpus:scale-distractors
    articles:    d:<slug>
    sections:    dp:<slug>:i:02d
    paragraphs:  dq:<slug>:i:02d:j:03d
    sentences:   dt:<slug>:i:02d:j:03d:k:02d
  """
  title_to_art = {}
  for s in snaps:
    slug = bp.slugify(s["normalized_title"])
    aid = "d:" + slug
    if aid in title_to_art.values():
      aid = f"d:{slug}~{s['pageid']}"
    title_to_art[bp.norm_key(s["normalized_title"])] = aid

  nodes = [CorpusNode(node_id="corpus:scale-distractors", kind="corpus",
                      text="Round 0 Wikipedia distractor-scale corpus (experimental research only)",
                      meta={"license_note": "mixed CC BY-SA per-article; see article nodes"})]

  # Add cluster nodes
  for c in sorted({s["cluster"] for s in snaps}):
    nodes.append(CorpusNode(node_id="dp:" + bp.slugify(c), kind="cluster",
                            text=c, parent_id="corpus:scale-distractors", meta={"kind": "topic"}))

  art_of_node = {}
  removal = collections.Counter()
  per_article = {}
  for s in snaps:
    aid = title_to_art[bp.norm_key(s["normalized_title"])]
    slug = aid[2:]  # strip "d:" prefix
    st = collections.Counter()
    aliases = tuple([s["requested_title"]] if s["requested_title"] != s["normalized_title"] else [])
    nodes.append(CorpusNode(
      node_id=aid, kind="article", text=s["normalized_title"],
      parent_id="dp:" + bp.slugify(s["cluster"]), aliases=aliases,
      meta={"pageid": str(s["pageid"]), "revid": str(s["revid"]),
            "timestamp": s["timestamp"], "source_url": s["source_url"],
            "license": s["license"], "cluster": s["cluster"],
            "split_group": s["split_group"],
            "content_sha256": s["content_sha256"]}))
    art_of_node[aid] = s
    sects = bp.convert_article(s["normalized_title"], s["pageid"], s["revid"],
                               s["timestamp"], s["wikitext"], stats=st,
                               sent_cap=None)
    removal.update(st)
    per_article[s["normalized_title"]] = {k: st[k] for k in STATS_KEYS}
    for i, (head, level, paras) in enumerate(sects):
      sid = f"dp:{slug}:{i:02d}"
      nodes.append(CorpusNode(node_id=sid, kind="section", text=head or "(untitled)",
                              parent_id=aid, meta={"level": str(level)}))
      for j, (ptext, praw) in enumerate(paras):
        pid = f"dq:{slug}:{i:02d}:{j:03d}"
        plinks = []
        for tgt in bp.para_links(praw):
          tgt_aid = title_to_art.get(bp.norm_key(tgt))
          if tgt_aid and tgt_aid != aid and tgt_aid not in plinks:
            plinks.append(tgt_aid)
        nodes.append(CorpusNode(node_id=pid, kind="paragraph", text=ptext,
                                parent_id=sid, links=tuple(plinks),
                                meta={"char_len": str(len(ptext))}))
        for k, sent in enumerate(bp.split_sentences(ptext, cap=None)):
          nid = f"dt:{slug}:{i:02d}:{j:03d}:{k:02d}"
          nodes.append(CorpusNode(
            node_id=nid, kind="sentence",
            text=sent, parent_id=pid, meta={"char_len": str(len(sent))}))
  art_index = {n.node_id: n for n in nodes if n.kind == "article"}
  patched, in_corpus_links = [], 0
  for n in nodes:
    if n.kind == "article":
      s = art_of_node[n.node_id]
      targets = []
      for t in s["outlinks"]:
        tgt = title_to_art.get(bp.norm_key(t))
        if tgt and tgt != n.node_id and tgt not in targets:
          targets.append(tgt)
        in_corpus_links += len(targets)
      patched.append(CorpusNode(node_id=n.node_id, kind=n.kind, text=n.text,
                                parent_id=n.parent_id, links=tuple(targets),
                                aliases=n.aliases, meta=n.meta))
    else:
      patched.append(n)
  return patched, art_of_node, dict(removal), per_article, in_corpus_links


def run_offline(raw_dir, stage_dir, revision):
  """Full offline build into stage_dir. Returns summary dict. No network."""
  os.makedirs(stage_dir, exist_ok=True)
  cand_path = os.path.join(ROOT, "corpus", "article_candidates.json")
  with open(cand_path, encoding="utf-8") as fh:
    cand = json.load(fh)
  candidates = cand["articles"] + cand.get("spares", [])
  builder_path = os.path.abspath(__file__)
  snaps, problems = load_snapshots(raw_dir)
  ordered, order_notes = select_ordered(snaps, candidates)
  kept, excluded = dedup_pageids(ordered)
  nodes, art_of_node, removal, per_article, in_links = build_nodes(kept)
  errors = validate_hierarchy(nodes)
  if errors:
    raise RuntimeError(f"hierarchy invalid: {errors[:5]}")
  groups = {}
  for s in kept:
    groups.setdefault(s["split_group"], []).append(s["normalized_title"])
  split_map = {"seed": bp.SPLIT_SEED,
               "policy": "group-aware seeded hash 70/15/15; confusable groups kept intact",
               "groups": {g: {"split": bp.assign_split(g), "articles": sorted(t)}
                          for g, t in groups.items()}}
  arts = {bp.norm_key(n.text) for n in nodes if n.kind == "article"}
  gm = validate_group_map(split_map, arts)
  if gm["errors"]:
    raise RuntimeError(f"group map invalid: {gm['errors'][:5]}")
  chash = corpus_hash(nodes)
  jsonl = nodes_to_jsonl(nodes)
  paths = {
    "corpus.jsonl": os.path.join(stage_dir, "corpus.jsonl"),
    "split_map.json": os.path.join(stage_dir, "split_map.json"),
    "provenance.json": os.path.join(stage_dir, "provenance.json"),
    "input_manifest.json": os.path.join(stage_dir, "input_manifest.json"),
  }
  with open(paths["corpus.jsonl"], "w", encoding="utf-8") as fh:
    fh.write(jsonl)
  with open(paths["split_map.json"], "w", encoding="utf-8") as fh:
    json.dump(split_map, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")
  input_manifest = {
    "revision": revision,
    "candidate_list": {"path": "corpus/distractor_candidates.json",
                       "sha256": sha256_file(cand_path),
                       "seed": cand.get("seed"), "method": cand.get("method")},
    "builder": {"path": "corpus/scale/scale_build.py",
                "sha256": sha256_file(builder_path),
                "converter": "corpus/build_pilot.py converter fns (stats hooks, sent_cap=None)",
                "network": "none: offline path never calls api_get/fetch_article"},
    "raw_dir": raw_dir,
    "snapshots": [{"file": s["_file"], "sha256": s["_sha256"],
                   "normalized_title": s["normalized_title"],
                   "pageid": s["pageid"], "revid": s["revid"],
                   "included": s["normalized_title"] in {k["normalized_title"] for k in kept}}
                  for s in snaps],
    "order_notes": order_notes,
    "excluded_duplicates": excluded,
    "load_problems": problems,
  }
  with open(paths["input_manifest.json"], "w", encoding="utf-8") as fh:
    json.dump(input_manifest, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")
  from datetime import datetime, timezone  # noqa: E402
  prov = {
    "revision": revision,
    "built_utc": datetime.now(timezone.utc).isoformat(),
    "builder": "corpus worker opencode/muse-spark-1.3-contributor-free (offline rebuild, no network)",
    "supersedes": {"archive": "corpus/archive/pilot-247-v0/",
                   "corpus_hash": "ead3d771122c05e1499b06ca1393bfa4e5963bc7f532a5639554337b2d5a64f0"},
    "method": cand.get("method"),
    "candidate_seed": cand.get("seed"),
    "selection_independence": ("Predeclared list, not tuned on benchmark answers; "
      "public benchmarks already existed (see docs/reference-audit.md); guarantee is procedural."),
    "fetched_articles": len(kept),
    "node_counts": {k: sum(1 for n in nodes if n.kind == k)
                    for k in ("corpus", "cluster", "article", "section", "paragraph", "sentence")},
    "corpus_hash_sha256": chash,
    "canonical_text_sha256": hashlib.sha256(canonical_corpus_text(nodes).encode("utf-8")).hexdigest(),
    "article_level_in_corpus_links": in_links,
    "split_counts": {s: sum(len(g["articles"]) for g in split_map["groups"].values() if g["split"] == s)
                     for s in ("train", "dev", "heldout")},
    "license": bp.LICENSE, "license_note": bp.LICENSE_NOTE,
    "conversion_caps": {"max_paragraphs_per_article": bp.MAX_PAR_PER_ART,
                        "max_sentences_per_paragraph": None,
                        "sentence_omission": "none: all sentences preserved as nodes",
                        "max_outlinks_per_article": bp.MAX_LINKS_PER_ART,
                        "excluded_sections": sorted(bp.SKIP_SECTIONS)},
    "removal_stats_totals": removal,
    "removal_stats_per_article": per_article,
    "validation_errors": errors,
    "articles": [
      {"requested_title": s["requested_title"], "normalized_title": s["normalized_title"],
       "pageid": s["pageid"], "revid": s["revid"], "timestamp": s["timestamp"],
       "source_url": s["source_url"], "license": s["license"], "cluster": s["cluster"],
       "split_group": s["split_group"], "content_sha256": s["content_sha256"],
       "wikitext_bytes": len(s["wikitext"].encode("utf-8")),
       "outlinks_total": len(s["outlinks"]), "outlinks_truncated": s["outlinks_truncated"],
       "fetched_utc": s["fetched_utc"]} for s in kept],
  }
  with open(paths["provenance.json"], "w", encoding="utf-8") as fh:
    json.dump(prov, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")
  # Verify staged bytes before any publish.
  staged = nodes_from_jsonl(open(paths["corpus.jsonl"], encoding="utf-8").read())
  assert corpus_hash(staged) == chash, "staged corpus hash mismatch"
  assert not validate_hierarchy(staged), "staged hierarchy invalid"
  manifest = {
    "revision": revision,
    "input_manifest_sha256": sha256_file(paths["input_manifest.json"]),
    "artifacts": [{"path": f"corpus/{name}", "sha256": sha256_file(p),
                   "bytes": os.path.getsize(p)} for name, p in
                   sorted(paths.items()) if name != "input_manifest.json"] + [
      {"path": "corpus/input_manifest.json",
       "sha256": sha256_file(paths["input_manifest.json"]),
       "bytes": os.path.getsize(paths["input_manifest.json"])}],
  }
  with open(os.path.join(stage_dir, "build_manifest.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")
  return {"revision": revision, "articles": len(kept), "nodes": len(nodes),
          "corpus_hash": chash, "stage_dir": stage_dir, "paths": paths,
          "manifest": manifest, "removal": removal,
          "split_counts": prov["split_counts"]}


def publish(stage_dir, out_dir, names=("corpus.jsonl", "split_map.json",
                                      "provenance.json", "input_manifest.json",
                                      "build_manifest.json")):
  """Atomically publish staged files. Each file is copied to a temp name in
  the DESTINATION directory (same filesystem) then os.replace()d, so readers
  never see a partial file and cross-device staging still works."""
  import shutil  # noqa: E402
  os.makedirs(out_dir, exist_ok=True)
  for name in names:
    src = os.path.join(stage_dir, name)
    if not os.path.isfile(src):
      raise RuntimeError(f"stage missing {name}; publish aborted, corpus/ untouched")
  for name in names:
    tmp = os.path.join(out_dir, ".publish_tmp_" + name)
    shutil.copyfile(os.path.join(stage_dir, name), tmp)
    os.replace(tmp, os.path.join(out_dir, name))
  return [os.path.join(out_dir, n) for n in names]


def main(argv):
  import argparse  # noqa: E402
  ap = argparse.ArgumentParser(description="Offline-only corpus rebuild (no network).")
  ap.add_argument("--raw-dir", default=os.path.join(ROOT, "raw"))
  ap.add_argument("--out", default=os.path.join(ROOT, "scale"))
  ap.add_argument("--stage", default=os.path.join(ROOT, ".build_tmp"))
  ap.add_argument("--revision", default=None)
  args = ap.parse_args(argv)
  summary = run_offline(args.raw_dir, args.stage,
                        args.revision or "scale-distractors-r1")
  published = publish(args.stage, args.out)
  summary["published"] = published
  print(json.dumps({k: v for k, v in summary.items()
                    if k in ("revision", "articles", "nodes", "corpus_hash",
                             "split_counts", "removal", "published")},
                    indent=2, sort_keys=True))


if __name__ == "__main__":
  main(sys.argv[1:])