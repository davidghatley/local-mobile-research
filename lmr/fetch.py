"""Rebuild the 297-article corpus from the exact Wikipedia revisions it was built from.

`corpus/provenance.json` pins every article to a revision id and the sha256 of its
wikitext. This module fetches those revisions (not today's pages), refuses any
whose bytes differ from the pin, and runs the existing offline converter
(`corpus/build_offline.py`) to produce `corpus/corpus.jsonl`.

One known difference from the original build: article-level cross-links were
taken from the live API link list at fetch time, which is not recoverable for an
old revision. Here they are re-derived from the pinned wikitext instead.
Paragraph text and ids, which are all that retrieval uses, come from the same
bytes and are unchanged.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "corpus"))
sys.path.insert(0, ROOT)

import build_pilot as bp  # noqa: E402

BATCH = 20


def _fetch_batch(revids: list[int]) -> dict[int, dict]:
  raw = bp.api_get({
    "action": "query", "format": "json", "formatversion": "2",
    "revids": "|".join(str(r) for r in revids),
    "prop": "revisions|info", "rvprop": "ids|timestamp|content",
    "rvslots": "main", "inprop": "url",
  })
  out = {}
  for page in json.loads(raw.decode("utf-8"))["query"]["pages"]:
    for rev in page.get("revisions", []):
      out[rev["revid"]] = {"page": page, "rev": rev}
  return out


def fetch_raw(raw_dir: str, log=print) -> int:
  """Write one verified snapshot per pinned article into raw_dir. Returns count."""
  prov = json.load(open(os.path.join(ROOT, "corpus", "provenance.json")))["articles"]
  os.makedirs(raw_dir, exist_ok=True)
  todo = [a for a in prov
          if not os.path.exists(os.path.join(raw_dir, bp.slugify(a["requested_title"]) + ".json"))]
  log(f"{len(prov) - len(todo)} cached, {len(todo)} to fetch")
  for i in range(0, len(todo), BATCH):
    batch = todo[i:i + BATCH]
    got = _fetch_batch([a["revid"] for a in batch])
    for a in batch:
      hit = got.get(a["revid"])
      if hit is None:
        raise RuntimeError(f"revision {a['revid']} ({a['normalized_title']}) not returned")
      text = hit["rev"]["slots"]["main"]["content"]
      digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
      if digest != a["content_sha256"]:
        raise RuntimeError(f"{a['normalized_title']}: wikitext sha256 {digest} != pinned {a['content_sha256']}")
      snap = {
        "requested_title": a["requested_title"],
        "normalized_title": a["normalized_title"],
        "pageid": a["pageid"], "revid": a["revid"], "timestamp": a["timestamp"],
        "license": a["license"], "source_url": a["source_url"],
        "wikitext": text, "content_sha256": digest,
        "outlinks": bp.para_links(text)[:bp.MAX_LINKS_PER_ART],
        "outlinks_truncated": False,
        "redirects_from": [], "fetched_utc": bp.utcnow(),
        "cluster": a["cluster"], "split_group": a["split_group"],
      }
      path = os.path.join(raw_dir, bp.slugify(a["requested_title"]) + ".json")
      with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False)
      os.replace(path + ".tmp", path)
    log(f"  fetched {min(i + BATCH, len(todo))}/{len(todo)}")
    time.sleep(bp.SLEEP_ARTICLE)
  return len(prov)


def build(raw_dir: str, log=print) -> str:
  """Convert snapshots to corpus/corpus.jsonl without touching tracked files."""
  import build_offline as bo
  stage = os.path.join(ROOT, "corpus", ".build_tmp")
  summary = bo.run_offline(raw_dir, stage, "pilot-297-r1")
  dest = os.path.join(ROOT, "corpus", "corpus.jsonl")
  shutil.copyfile(os.path.join(stage, "corpus.jsonl"), dest + ".tmp")
  os.replace(dest + ".tmp", dest)
  shutil.rmtree(stage, ignore_errors=True)
  log(f"built {summary['articles']} articles, {summary['nodes']} nodes -> {dest}")
  return dest


def ensure_corpus(log=print) -> str:
  dest = os.path.join(ROOT, "corpus", "corpus.jsonl")
  if os.path.exists(dest):
    return dest
  raw = os.path.join(ROOT, "corpus", "raw")
  fetch_raw(raw, log)
  return build(raw, log)
