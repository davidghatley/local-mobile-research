"""Round 0 Wikipedia pilot corpus builder (corpus worker owned).

Reads corpus/article_candidates.json (predeclared, frozen before fetch),
fetches full wikitext + revid/timestamp/outlinks via the MediaWiki Action API,
saves per-article raw snapshots under corpus/raw/ (reproducible conversion
input), converts to substrate CorpusNode DAG JSONL (article > section >
paragraph > sentence with cross-links), reserves article groups to
train/dev/heldout in corpus/split_map.json (BEFORE any question creation),
and writes corpus/provenance.json.

Creates NO questions and NO heldout labels (other workers' scope).
Creates NO generator_config.json (generator owner's scope).
Modifies NO substrate files (read-only import for validation/hashing).

Caps: download 200 MB total; converted corpus.jsonl must stay well under the
500 MB on-disk pilot budget (expected tens of MB).
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from substrate.corpus import (  # noqa: E402  (read-only use; no modification)
  canonical_corpus_text,
  corpus_hash,
  nodes_to_jsonl,
  validate_hierarchy,
)
from substrate.types import CorpusNode  # noqa: E402

API = "https://en.wikipedia.org/w/api.php"
UA = "OfflineResearchPilot/0.1 (experimental research corpus; polite 4rps)"
LICENSE = "CC BY-SA 4.0"
LICENSE_NOTE = (
  "English Wikipedia article text fetched 2026-09-29 is licensed CC BY-SA 4.0; "
  "individual revisions may carry older dual terms (CC BY-SA 3.0/GFDL) — see "
  "per-article revid/timestamp/source_url for exact attribution."
)
DOWNLOAD_CAP = 200 * 1024 * 1024
TARGET = 500
SPLIT_SEED = "pilot-v1"
SLEEP_ARTICLE = 1.0  # politeness delay between per-article fetch cycles
SLEEP_PAGE = 0.5  # politeness delay between paginated outlink continuations
FETCH_TRIES = 6
CONSECUTIVE_FAIL_ABORT = 15  # circuit breaker: stop before exhausting list
MAX_PAR_PER_ART = 250
MAX_SENT_PER_PAR = 12
MAX_LINKS_PER_ART = 2500
SKIP_SECTIONS = {
  "see also", "references", "notes", "external links", "further reading",
  "bibliography", "sources", "footnotes", "citations",
}

CAND_PATH = os.path.join(ROOT, "corpus", "article_candidates.json")
RAW_DIR = os.path.join(ROOT, "corpus", "raw")
JSONL_PATH = os.path.join(ROOT, "corpus", "corpus.jsonl")
SPLIT_PATH = os.path.join(ROOT, "corpus", "split_map.json")
PROV_PATH = os.path.join(ROOT, "corpus", "provenance.json")

_heading_re = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")
_link_re = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
_sent_re = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(“‘\[])")
# Orphan table-markup lines from template-generated tables (e.g.
# {{election table}} emits rows with no {| opener anywhere): always safe to
# drop the structural lines; cell "|" lines only with a table signal present
# (a math block could otherwise lose a line starting with "|").
_TABLE_SIGNAL_RE = re.compile(r"(?m)^\s*(?:\{\||\|\}|\|-)")
_TABLE_STRUCT_RE = re.compile(r"^\s*(?:\{\|.*|\|\}\s*|\|\+.*|\|-.*|!(?:\s|=|$).*)")
_TABLE_CELL_RE = re.compile(r"^\s*\|")


def drop_orphan_table_lines(block):
  if _TABLE_SIGNAL_RE.search(block):
    keep = lambda ln: not _TABLE_STRUCT_RE.match(ln) and not _TABLE_CELL_RE.match(ln)
  else:
    keep = lambda ln: not _TABLE_STRUCT_RE.match(ln)
  return "\n".join(ln for ln in block.split("\n") if keep(ln))


def utcnow():
  return datetime.now(timezone.utc).isoformat()


def slugify(title):
  s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:50].strip("_")
  return s or "untitled"


def api_get(params, timeout=30, tries=FETCH_TRIES):
  query = urllib.parse.urlencode(params, doseq=True)
  last_err = "no attempt made"
  wait = 2.0
  for _ in range(tries):
    req = urllib.request.Request(API + "?" + query, headers={"User-Agent": UA})
    try:
      with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
    except urllib.error.HTTPError as exc:  # noqa: BLE001 - exact text kept
      last_err = f"{type(exc).__name__}: HTTP Error {exc.code}: {exc.reason}"
      if exc.headers:
        ra = exc.headers.get("Retry-After")
        if ra:
          try:
            wait = max(wait, float(ra))
          except ValueError:
            pass
      if exc.code == 429 or 500 <= exc.code < 600:
        time.sleep(min(wait, 60.0))
        wait *= 2
        continue
      raise RuntimeError(last_err)
    except Exception as exc:  # noqa: BLE001 - exact text kept
      last_err = f"{type(exc).__name__}: {exc}"
      time.sleep(min(wait, 60.0))
      wait *= 2
  raise RuntimeError(last_err + f" after {tries} tries")


def norm_key(title):
  return re.sub(r"\s+", " ", title.replace("_", " ").strip()).lower()


NS_PREFIXES = ("file:", "image:", "category:", "portal:", "draft:",
               "template:", "wikipedia:", "help:", "mediawiki:", "special:",
               "module:", "book:", "up:", "mos:", "wp:")
_NS_OPEN_RE = re.compile(r"\[\[(?:File|Image|Category|Portal|Draft|Template|Wikipedia|Help|MediaWiki|Special|Module|Book|UP|MOS|WP):", re.IGNORECASE)


def strip_balanced_spans(text, opener, closer, stats=None):
  """Remove balanced opener...closer spans (nesting-aware). Unbalanced
  openers are KEPT (visible residue) rather than eating to end of text —
  silent content loss is worse than visible residue."""
  out = []
  i = 0
  n = len(text)
  while i < n:
    if text.startswith(opener, i):
      depth = 0
      j = i
      found = False
      while j < n:
        if text.startswith(opener, j):
          depth += 1
          j += len(opener)
        elif text.startswith(closer, j):
          depth -= 1
          j += len(closer)
          if depth == 0:
            found = True
            break
        else:
          j += 1
      if found:
        if stats is not None:
          stats["balanced_spans_removed"] += 1
          stats["balanced_span_chars"] += j - i
        i = j
      else:
        out.append(text[i:i + len(opener)])
        i += len(opener)
    else:
      out.append(text[i])
      i += 1
  return "".join(out)


def strip_balanced_lines(text, opener, closer, stats=None):
  """Line-anchored balanced removal for wikitext block tables ({| ... |}).

  The opener must start a line (wikitext block structure). An UNCLOSED table
  drops only its opener line and keeps the content (layout-wrapper pattern
  seen in the wild, e.g. multi-column biography lists)."""
  import re as _re
  open_re = _re.compile(r"^[ \t:*#;]*" + _re.escape(opener))
  # In unclosed-table flush, drop table-markup lines but keep prose/list lines.
  markup_line_re = _re.compile(r"^\s*[|!]")
  lines = text.split("\n")
  out: list[str] = []
  buf: list[str] = []
  depth = 0
  for ln in lines:
    m = open_re.match(ln) if depth == 0 else None
    if m:
      rest = ln[m.end():]
      depth = 1 + rest.count(opener) - rest.count(closer)
      if depth <= 0:
        depth = 0
        if stats is not None:
          stats["tables_closed"] += 1
      continue
    if depth > 0:
      buf.append(ln)
      depth += ln.count(opener) - ln.count(closer)
      if depth <= 0:
        depth = 0
        buf = []
        if stats is not None:
          stats["tables_closed"] += 1
      continue
    out.append(ln)
  if buf and stats is not None:
    stats["tables_unclosed"] += 1
  out.extend(ln for ln in buf if not markup_line_re.match(ln))  # unclosed:
  # opener dropped, table-markup debris dropped, prose/list content kept
  return "\n".join(out)


def strip_ns_links(text, stats=None):
  """Remove [[Namespace:...]] links with balanced [[/]] scanning, so File
  captions containing nested [[links]] or multi-line text are fully removed
  instead of leaving fragment residue. Unbalanced openers are kept rather
  than eating to end of text (no silent loss)."""
  out = []
  i = 0
  n = len(text)
  while i < n:
    m = _NS_OPEN_RE.match(text, i)
    if not m:
      out.append(text[i])
      i += 1
      continue
    depth = 0
    j = i
    found = False
    while j < n:
      if text.startswith("[[", j):
        depth += 1
        j += 2
      elif text.startswith("]]", j):
        depth -= 1
        j += 2
        if depth == 0:
          found = True
          break
      else:
        j += 1
    if found:
      if stats is not None:
        stats["nslinks_removed"] += 1
        stats["nslink_chars"] += j - i
      i = j
    else:
      out.append(text[i:i + 2])
      i += 2
  return "".join(out)


def _positional_args(argstr, n):
  parts = [p.strip() for p in argstr.split("|")]
  return [p for p in parts if p and "=" not in p][:n]


def rescue_inline_templates(text, stats=None):
  """Rescue factual content from flat inline data templates BEFORE generic
  removal (only brace-free args; nested leftovers fall back to removal and
  stay counted as removed). {{cvt|60,268|km|mi}} -> '60,268 km'."""
  rules = [
    (r"\{\{(?:cvt|convert)\|([^{}]*?)\}\}",
     lambda m: " ".join(_positional_args(m.group(1), 2))),
    (r"\{\{(?:val|mvar)\|([^{}]*?)\}\}",
     lambda m: " ".join(_positional_args(m.group(1), 1))),
    (r"\{\{math\|([^{}]*?)\}\}", lambda m: m.group(1).strip()),
    (r"\{\{(?:sub|sup)\|([^{}]*?)\}\}",
     lambda m: " ".join(_positional_args(m.group(1), 1))),
    (r"\{\{frac\|([^{}]*?)\}\}",
     lambda m: (lambda p: "/".join(p) if len(p) == 2 else " ".join(p))(_positional_args(m.group(1), 2))),
    (r"\{\{(?:lang|transl|lit)\|[^{}|]*\|([^{}]*?)\}\}",
     lambda m: m.group(1).strip()),
    (r"\{\{coord\|([^{}]*?)\}\}",
     lambda m: " ".join(_positional_args(m.group(1), 99))),
  ]
  for _ in range(6):
    changed = False
    for pat, fn in rules:
      text, n = re.subn(pat, fn, text)
      if n:
        changed = True
        if stats is not None:
          stats["templates_rescued"] += n
    if not changed:
      break
  return text


def normalize_galleries(text, stats=None):
  """Convert '<gallery> File:X.jpg|caption </gallery>' lines to captions.

  Bare filenames (no caption) are dropped; 'File:name|caption' keeps the
  caption with its [[links]] intact for paragraph-level cross-links."""

  def _one(m):
    keep = []
    for ln in m.group(1).split("\n"):
      s = ln.strip()
      if not s:
        continue
      s2 = re.sub(r"^(?:File|Image)\s*:[^|]*\|", "", s).strip()
      if re.match(r"^(?:File|Image)\s*:", s2):
        continue  # bare filename, no caption content
      if s2:
        keep.append(s2)
    if stats is not None:
      stats["gallery_captions_kept"] += len(keep)
    return "\n".join(keep)

  return re.sub(r"<gallery[^>]*>(.*?)</gallery>", _one, text,
                flags=re.DOTALL | re.IGNORECASE)


def strip_block_markup(text, stats=None):
  """Remove multi-line constructs on FULL section text BEFORE paragraph split.

  (Applied pre-split because tables/templates/File captions routinely span
  blank lines; per-paragraph application left cross-block residue.)
  """
  text, n = re.subn(r"<!--.*?-->", "", text, flags=re.DOTALL)
  if stats is not None:
    stats["comments_removed"] += n
  text, n = re.subn(r"</?(?:onlyinclude|includeonly|noinclude)\s*>", "", text)
  if stats is not None:
    stats["include_tags_removed"] += n
  text, n = re.subn(r"<ref[^>/]*>.*?</ref>", "", text, flags=re.DOTALL)
  if stats is not None:
    stats["refs_removed"] += n
  text, n = re.subn(r"<ref[^>]*/>", "", text)
  if stats is not None:
    stats["refs_removed"] += n
  text = normalize_galleries(text, stats)
  text = rescue_inline_templates(text, stats)
  t0 = stats["balanced_spans_removed"] if stats is not None else 0
  c0 = stats["balanced_span_chars"] if stats is not None else 0
  text = strip_balanced_spans(text, "{{", "}}", stats)  # templates, nesting-aware
  if stats is not None:
    stats["templates_removed"] += stats["balanced_spans_removed"] - t0
    stats["template_chars"] += stats["balanced_span_chars"] - c0
  text = strip_ns_links(text, stats)
  text = strip_balanced_lines(text, "{|", "|}", stats)  # tables, line-anchored
  return text


def clean_inline(text):
  text = _link_re.sub(lambda m: (m.group(2) if m.group(2) is not None else m.group(1)).strip(), text)
  text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]*)\]", r"\1", text)
  text = re.sub(r"\[https?://[^\s\]]+\]", "", text)
  text = re.sub(r"'''''(.+?)'''''", r"\1", text)
  text = re.sub(r"'''(.+?)'''", r"\1", text)
  text = re.sub(r"''(.+?)''", r"\1", text)
  text = re.sub(r"<[^>]+>", "", text)
  text = html.unescape(text)
  text = text.replace("[[", "").replace("]]", "")  # unbalanced-link remnants
  text = re.sub(r"\{\{|\}\}", "", text)  # template remnants
  text = re.sub(r"[ \t]+", " ", text)
  return text.strip()


def para_links(wikitext_para):
  targets = []
  for m in _link_re.finditer(wikitext_para):
    tgt = m.group(1).strip()
    if re.match(r"(?i)^(file|image|category|portal|draft|template|wikipedia|help|mediawiki|special|module|book):", tgt):
      continue
    tgt = tgt.split("#")[0].strip()
    if tgt:
      targets.append(tgt)
  return targets


def convert_article(norm_title, pageid, revid, timestamp, wikitext, stats=None, sent_cap=12):
  """Return (sections, title_map_hint). sections = [(heading, level, [paras])];
  paras = [(clean_text, raw_wikitext)].

  stats (optional Counter-like): accumulates removal/conversion counters.
  sent_cap=None preserves ALL sentences (no omission); default 12 matches the
  original pilot converter byte-for-byte.
  """
  lines = wikitext.split("\n")
  sections = []
  cur_head, cur_level, cur_lines = "(lead)", 1, []
  for line in lines:
    m = _heading_re.match(line.strip())
    if m:
      sections.append((cur_head, cur_level, cur_lines))
      cur_head = clean_inline(m.group(2).strip())
      cur_level = len(m.group(1))
      cur_lines = []
    else:
      cur_lines.append(line)
  sections.append((cur_head, cur_level, cur_lines))
  out = []
  for head, level, sect_lines in sections:
    if level >= 2 and head.lower() in SKIP_SECTIONS:
      continue  # attribution sections excluded from nodes; API outlinks kept
    if level >= 5:  # fold deep headings into previous section as a paragraph
      if out:
        out[-1][2].append("**" + head + "**\n" + "\n".join(sect_lines))
      else:
        out.append(("(lead)", 1, ["**" + head + "**\n" + "\n".join(sect_lines)]))
      continue
    out.append((head, level, "\n".join(sect_lines).split("\n\n")))
  cleaned = []
  for head, level, blocks in out:
    paras = []
    # Block-level strip on the whole section BEFORE paragraph splitting, so
    # multi-line templates/tables/File links cannot strand residue.
    sec_text = strip_block_markup("\n".join(blocks) if isinstance(blocks, list) else blocks, stats)
    for b in sec_text.split("\n\n"):
      raw = drop_orphan_table_lines(b.strip())
      if stats is not None:
        stats["orphan_lines_dropped"] += b.strip().count("\n") + (1 if b.strip() else 0) - (raw.count("\n") + (1 if raw else 0))
      if not raw:
        continue
      stripped = raw.lstrip()
      text = "\n".join(
        re.sub(r"^[*#;:]+", "", ln).strip() for ln in raw.split("\n")
      )
      text = clean_inline(text)
      text = re.sub(r"\n{3,}", "\n\n", text).strip()
      if len(text) < 8:
        continue  # markup residue only; documented heuristic floor
      if len(text) <= 4000:
        paras.append((text, raw))
      else:
        # Long prose blocks are chunked on sentence boundaries (no content
        # loss); chunks share the block's outlink targets (documented).
        # Single overlong sentences (e.g. table-row debris without periods)
        # are hard-split on whitespace so no text is ever truncated away.
        buf = ""
        chunked = False
        for sent in split_sentences(text, cap=sent_cap):
          while len(sent) > 3000:
            chunked = True
            if stats is not None:
              stats["sentences_hardsplit"] += 1
            cut = sent.rfind(" ", 0, 3000)
            cut = cut if cut > 1000 else 3000
            if buf and len(buf) + 1 + cut > 3000:
              paras.append((buf, raw))
              buf = ""
            piece, sent = sent[:cut], sent[cut:].strip()
            buf = (buf + " " + piece).strip() if buf else piece
          if buf and len(buf) + 1 + len(sent) > 3000:
            paras.append((buf, raw))
            buf = sent
          else:
            buf = (buf + " " + sent).strip() if buf else sent
        if buf.strip():
          paras.append((buf.strip(), raw))
        if chunked and stats is not None:
          stats["paras_chunked"] += 1
      if len(paras) >= MAX_PAR_PER_ART:
        if stats is not None:
          stats["para_cap_hits"] += 1
        break
    if paras or level == 1:
      cleaned.append((head, level, paras))
  return cleaned


def split_sentences(para, cap=MAX_SENT_PER_PAR):
  parts = _sent_re.split(para)
  sents = [p.strip() for p in parts if p.strip()]
  return sents if cap is None else sents[:cap]


def assign_split(key, seed=SPLIT_SEED):
  digest = hashlib.sha256(f"{seed}\x00{key}".encode("utf-8")).hexdigest()
  value = int(digest[:8], 16) / 0xFFFFFFFF
  if value < 0.70:
    return "train"
  if value < 0.85:
    return "dev"
  return "heldout"


def fetch_article(req_title):
  params = {
    "action": "query", "format": "json", "formatversion": "2",
    "redirects": "1", "titles": req_title,
    "prop": "revisions|links|info", "rvprop": "ids|timestamp|content",
    "rvslots": "main", "plnamespace": "0", "pllimit": "500", "inprop": "url",
  }
  total = 0
  pages = None
  plcontinue = None
  links = []
  page = None
  while True:
    p = dict(params)
    if plcontinue:
      p["plcontinue"] = plcontinue
    raw = api_get(p)
    total += len(raw)
    d = json.loads(raw.decode("utf-8"))
    if pages is None:
      pages = d["query"]["pages"]
      if d["query"]["pages"][0].get("missing"):
        return None, total, "missing/invalid title"
      page = pages[0]
    links.extend(l["title"] for l in d["query"]["pages"][0].get("links", []))
    if "continue" in d and "plcontinue" in d["continue"] and len(links) < MAX_LINKS_PER_ART:
      plcontinue = d["continue"]["plcontinue"]
    else:
      break
    time.sleep(SLEEP_PAGE)
  rev = page["revisions"][0]
  return {
    "requested_title": req_title,
    "normalized_title": page["title"],
    "pageid": page["pageid"],
    "revid": rev["revid"],
    "timestamp": rev["timestamp"],
    "license": LICENSE,
    "source_url": page.get("fullurl", "https://en.wikipedia.org/wiki/" + urllib.parse.quote(req_title.replace(" ", "_"))),
    "wikitext": rev["slots"]["main"]["content"],
    "outlinks": links[:MAX_LINKS_PER_ART],
    "outlinks_truncated": len(links) >= MAX_LINKS_PER_ART,
    "redirects_from": [req_title] if req_title != page["title"] else [],
    "fetched_utc": utcnow(),
  }, total, None


def main():
  os.makedirs(RAW_DIR, exist_ok=True)
  cand = json.load(open(CAND_PATH, encoding="utf-8"))
  order = cand["articles"] + cand.get("spares", [])
  seen = set()
  uniq = []
  for e in order:
    k = norm_key(e["t"])
    if k not in seen:
      seen.add(k)
      uniq.append(e)
  cluster_of = {}
  group_of = {}
  for e in uniq:
    cluster_of[norm_key(e["t"])] = e["c"]
    group_of[norm_key(e["t"])] = e["g"] or ("solo:" + norm_key(e["t"]))

  fetched = []   # raw snapshot dicts in fetch order
  gaps = []      # {requested_title, stage, error}
  # Cumulative download accounting across resume runs (cap is global, not per-run).
  bytes_dl = 0
  try:
    with open(PROV_PATH, encoding="utf-8") as _pf:
      bytes_dl = int(json.load(_pf).get("download_bytes", 0))
  except (OSError, ValueError, KeyError):
    bytes_dl = 0
  consec_fetch_fail = 0
  for e in uniq:
    if len(fetched) >= TARGET:
      break
    if consec_fetch_fail >= CONSECUTIVE_FAIL_ABORT:
      gaps.append({"requested_title": "*", "stage": "abort",
                   "error": f"circuit breaker: {CONSECUTIVE_FAIL_ABORT} consecutive fetch failures; "
                            "stopping to preserve remaining candidates and respect rate limits"})
      break
    slug = slugify(e["t"])
    raw_path = os.path.join(RAW_DIR, slug + ".json")
    if os.path.isfile(raw_path):
      try:
        snap = json.load(open(raw_path, encoding="utf-8"))
        fetched.append(snap)
        consec_fetch_fail = 0
        continue
      except Exception as exc:  # noqa: BLE001
        gaps.append({"requested_title": e["t"], "stage": "resume-read", "error": f"{type(exc).__name__}: {exc}"})
    if bytes_dl > DOWNLOAD_CAP:
      gaps.append({"requested_title": e["t"], "stage": "fetch", "error": "download cap reached; stopped"})
      break
    try:
      snap, nbytes, err = fetch_article(e["t"])
    except Exception as exc:  # noqa: BLE001
      gaps.append({"requested_title": e["t"], "stage": "fetch", "error": f"{type(exc).__name__}: {exc}"})
      consec_fetch_fail += 1
      time.sleep(SLEEP_ARTICLE)
      continue
    bytes_dl += nbytes
    if bytes_dl > DOWNLOAD_CAP:
      gaps.append({"requested_title": e["t"], "stage": "fetch", "error": "download cap exceeded; snapshot discarded"})
      break
    if err is not None:
      gaps.append({"requested_title": e["t"], "stage": "resolve", "error": err})
      time.sleep(SLEEP_ARTICLE)
      continue
    consec_fetch_fail = 0
    snap["cluster"] = e["c"]
    snap["split_group"] = e["g"] or ("solo:" + norm_key(snap["normalized_title"]))
    snap["content_sha256"] = hashlib.sha256(snap["wikitext"].encode("utf-8")).hexdigest()
    with open(raw_path, "w", encoding="utf-8") as fh:
      json.dump(snap, fh, ensure_ascii=False)
      fh.write("\n")
    fetched.append(snap)
    time.sleep(SLEEP_ARTICLE)

  # Build nodes.
  title_to_art = {}
  for snap in fetched:
    slug = slugify(snap["normalized_title"])
    aid = "a:" + slug
    if aid in title_to_art.values():
      aid = f"a:{slug}~{snap['pageid']}"
    title_to_art[norm_key(snap["normalized_title"])] = aid

  nodes = [CorpusNode(node_id="corpus:pilot", kind="corpus",
                      text="Round 0 Wikipedia pilot corpus (experimental research only)",
                      meta={"license_note": "mixed CC BY-SA per-article; see article nodes"})]
  clusters = sorted({s["cluster"] for s in fetched})
  for c in clusters:
    nodes.append(CorpusNode(node_id="cluster:" + slugify(c), kind="cluster",
                            text=c, parent_id="corpus:pilot", meta={"kind": "topic"}))
  art_of_node = {}
  for snap in fetched:
    aid = title_to_art[norm_key(snap["normalized_title"])]
    slug = aid[2:]
    aliases = tuple([snap["requested_title"]] if snap["requested_title"] != snap["normalized_title"] else [])
    nodes.append(CorpusNode(
      node_id=aid, kind="article", text=snap["normalized_title"],
      parent_id="cluster:" + slugify(snap["cluster"]), aliases=aliases,
      meta={"pageid": str(snap["pageid"]), "revid": str(snap["revid"]),
            "timestamp": snap["timestamp"], "source_url": snap["source_url"],
            "license": snap["license"], "cluster": snap["cluster"],
            "split_group": snap["split_group"],
            "content_sha256": snap["content_sha256"]}))
    art_of_node[aid] = snap
    sects = convert_article(snap["normalized_title"], snap["pageid"],
                            snap["revid"], snap["timestamp"], snap["wikitext"])
    for i, (head, level, paras) in enumerate(sects):
      sid = f"s:{slug}:{i:02d}"
      nodes.append(CorpusNode(node_id=sid, kind="section", text=head or "(untitled)",
                              parent_id=aid, meta={"level": str(level)}))
      for j, (ptext, praw) in enumerate(paras):
        pid = f"s:{slug}:{i:02d}:{j:03d}".replace("s:", "p:", 1)
        plinks = []
        for tgt in para_links(praw):
          tgt_aid = title_to_art.get(norm_key(tgt))
          if tgt_aid and tgt_aid != aid and tgt_aid not in plinks:
            plinks.append(tgt_aid)
        nodes.append(CorpusNode(node_id=pid, kind="paragraph", text=ptext,
                                parent_id=sid, links=tuple(plinks),
                                meta={"char_len": str(len(ptext))}))
        for k, sent in enumerate(split_sentences(ptext)):
          nodes.append(CorpusNode(
            node_id=f"t:{slug}:{i:02d}:{j:03d}:{k:02d}", kind="sentence",
            text=sent, parent_id=pid, meta={"char_len": str(len(sent))}))
  # Article-level cross-links (API outlinks resolved into corpus).
  art_index = {n.node_id: n for n in nodes if n.kind == "article"}
  patched = []
  in_corpus_links = 0
  for n in nodes:
    if n.kind == "article":
      snap = art_of_node[n.node_id]
      targets = []
      for t in snap["outlinks"]:
        tgt = title_to_art.get(norm_key(t))
        if tgt and tgt != n.node_id and tgt not in targets:
          targets.append(tgt)
      in_corpus_links += len(targets)
      patched.append(CorpusNode(node_id=n.node_id, kind=n.kind, text=n.text,
                                parent_id=n.parent_id, links=tuple(targets),
                                aliases=n.aliases, meta=n.meta))
    else:
      patched.append(n)
  nodes = patched

  errors = validate_hierarchy(nodes)
  with open(JSONL_PATH, "w", encoding="utf-8") as fh:
    fh.write(nodes_to_jsonl(nodes))
  chash = corpus_hash(nodes)

  # Group-aware split reservation (before any question creation).
  groups = {}
  for snap in fetched:
    g = snap["split_group"]
    groups.setdefault(g, []).append(snap["normalized_title"])
  split_map = {"seed": SPLIT_SEED, "policy": "group-aware seeded hash 70/15/15; confusable groups kept intact",
               "groups": {g: {"split": assign_split(g), "articles": sorted(t)} for g, t in groups.items()}}
  with open(SPLIT_PATH, "w", encoding="utf-8") as fh:
    json.dump(split_map, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")

  # Cross-split link stats (contamination lens).
  art_split = {}
  for g, rec in split_map["groups"].items():
    for t in rec["articles"]:
      art_split[norm_key(t)] = rec["split"]
  cross = sum(1 for n in nodes if n.kind == "article"
              for tgt in n.links
              if art_split.get(norm_key(art_of_node[tgt]["normalized_title"])) != art_split[norm_key(n.text)])
  tot_links = sum(len(n.links) for n in nodes if n.kind == "article")

  by_kind = {}
  for n in nodes:
    by_kind[n.kind] = by_kind.get(n.kind, 0) + 1
  raw_bytes = sum(os.path.getsize(os.path.join(RAW_DIR, f)) for f in os.listdir(RAW_DIR))
  prov = {
    "built_utc": utcnow(), "builder": "corpus worker opencode/muse-spark-1.3-contributor-free",
    "method": cand.get("method"), "candidate_seed": cand.get("seed"),
    "target_articles": TARGET, "fetched_articles": len(fetched),
    "download_bytes": bytes_dl, "download_cap_bytes": DOWNLOAD_CAP,
    "raw_dir_bytes": raw_bytes,
    "corpus_jsonl_path": "corpus/corpus.jsonl",
    "corpus_jsonl_bytes": os.path.getsize(JSONL_PATH),
    "corpus_hash_sha256": chash,
    "canonical_text_sha256": hashlib.sha256(canonical_corpus_text(nodes).encode("utf-8")).hexdigest(),
    "node_counts": by_kind,
    "article_level_in_corpus_links": in_corpus_links,
    "article_level_cross_split_links": cross,
    "article_level_total_links": tot_links,
    "split_counts": {s: sum(len(g["articles"]) for g in split_map["groups"].values() if g["split"] == s)
                     for s in ("train", "dev", "heldout")},
    "license": LICENSE, "license_note": LICENSE_NOTE,
    "conversion_caps": {"max_paragraphs_per_article": MAX_PAR_PER_ART,
                        "max_sentences_per_paragraph": MAX_SENT_PER_PAR,
                        "max_outlinks_per_article": MAX_LINKS_PER_ART,
                        "excluded_sections": sorted(SKIP_SECTIONS)},
    "validation_errors": errors,
    "gaps": gaps,
    "articles": [
      {"requested_title": s["requested_title"], "normalized_title": s["normalized_title"],
       "pageid": s["pageid"], "revid": s["revid"], "timestamp": s["timestamp"],
       "source_url": s["source_url"], "license": s["license"], "cluster": s["cluster"],
       "split_group": s["split_group"], "content_sha256": s["content_sha256"],
       "wikitext_bytes": len(s["wikitext"].encode("utf-8")),
       "outlinks_total": len(s["outlinks"]), "outlinks_truncated": s["outlinks_truncated"],
       "fetched_utc": s["fetched_utc"]} for s in fetched],
  }
  with open(PROV_PATH, "w", encoding="utf-8") as fh:
    json.dump(prov, fh, indent=2, ensure_ascii=False, sort_keys=True)
    fh.write("\n")

  print(json.dumps({
    "fetched": len(fetched), "gaps": len(gaps), "download_bytes": bytes_dl,
    "raw_bytes": raw_bytes, "jsonl_bytes": os.path.getsize(JSONL_PATH),
    "corpus_hash": chash, "nodes": by_kind, "validation_errors": errors,
    "split_counts": prov["split_counts"],
    "cross_split_links": [cross, tot_links],
  }, indent=2, sort_keys=True))


if __name__ == "__main__":
  main()
