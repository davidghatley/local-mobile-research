"""Corpus view: one canonical index document per paragraph, plus ancestry.

Implements the parts of `experiments/baselines/HYPOTHESIS.md` §2 and §3.1 that
every Round 1 system needs, in one place, so that no two architectures can drift.

The single load-bearing idea is ``D(p)``:

    D(p) = article_title + " " + section_heading + " " + paragraph_text

with exactly one exception: when the parent section's stripped text is the
literal placeholder ``(lead)``, the heading is omitted. That placeholder is a
converter artifact present in exactly 297 sections (one per article) and is not
prose; leaving it in would inject the content word "lead" into 297 documents.

The count of affected documents is returned by :meth:`CorpusView.lead_placeholder_docs`
and is asserted against 297 by the substrate's own tests, so a corpus change that
breaks the assumption fails loudly instead of silently changing the index.

Retrieval unit is the paragraph. Sentences and sections are never retrieved; an
article's title enters the index only through ``D(p)``.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from substrate.corpus import load_corpus_file  # noqa: E402
from substrate.types import CorpusNode  # noqa: E402

# The converter's lead-section marker. Compared against the STRIPPED section text.
LEAD_PLACEHOLDER = "(lead)"

CORE_CORPUS_REL = os.path.join("corpus", "corpus.jsonl")
SCALE_CORPUS_REL = os.path.join("corpus", "scale", "distractor.jsonl")

# Node id prefixes, as emitted by the frozen converter. Used only to build the
# article/section slug for scale-tier nodes that carry no article ancestor.
_ARTICLE_PREFIX = "a:"
_SECTION_PREFIX = "s:"


def _slug_from_paragraph_id(node_id: str) -> str:
  """``p:<article_slug>:<sec>:<para>`` -> ``<article_slug>``.

  A defensive fallback for a paragraph whose ancestry is missing from a
  partially-loaded tier. It never fires on the frozen corpus (asserted by
  :meth:`CorpusView.ancestry_complete`).
  """
  parts = node_id.split(":")
  if len(parts) >= 2 and parts[0] == "p":
    return parts[1]
  return ""


@dataclass
class CorpusView:
  """Read-only, traversal-ready view over one corpus tier.

  Attributes:
    nodes: every node in byte order of the source file.
    paragraphs: the retrievable unit, in index order. Index ``i`` is the BM25
      document id and is stable for a given tier file.
    by_id: node_id -> CorpusNode.
    doc_strings: index-aligned ``D(p)`` strings. Byte-identical for a given
      (corpus file, tier) pair, so it is hashable and pinnable.
    parent_article: index -> article node_id.
    parent_section: index -> section node_id or None.
    scale: whether this view is the merged core+scale tier.
  """

  nodes: list[CorpusNode]
  paragraphs: list[CorpusNode]
  by_id: dict[str, CorpusNode]
  doc_strings: list[str]
  parent_article: list[str]
  parent_section: list[str | None]
  tier_name: str
  scale: bool
  _article_title: dict[str, str] = field(default_factory=dict, repr=False)
  _alias_to_node: dict[str, str] = field(default_factory=dict, repr=False)

  # -- construction --------------------------------------------------------

  @staticmethod
  def load(repo_root: str, tier: str = "core") -> "CorpusView":
    """Load one tier.

    tier="core"   -> corpus/corpus.jsonl only (the PRIMARY index, 9,979 docs)
    tier="scale"  -> corpus/corpus.jsonl + corpus/scale/distractor.jsonl merged,
                      in that concatenation order (36,609 docs). The 940 scale
                      articles are DISTRACTOR material, never evidence
                      (docs/scale-method.md).
    """
    if tier not in ("core", "scale"):
      raise ValueError(f"tier must be 'core' or 'scale', got {tier!r}")

    core_path = os.path.join(repo_root, CORE_CORPUS_REL)
    nodes = load_corpus_file(core_path)
    scale = tier == "scale"
    if scale:
      scale_path = os.path.join(repo_root, SCALE_CORPUS_REL)
      if not os.path.isfile(scale_path):
        raise FileNotFoundError(f"scale tier requested but absent: {scale_path}")
      # Merged tier: core first, then scale, each in its own pinned byte order.
      nodes = nodes + load_corpus_file(scale_path)

    by_id = {n.node_id: n for n in nodes}
    article_title: dict[str, str] = {}
    alias_to_node: dict[str, str] = {}
    for n in nodes:
      if n.kind == "article":
        article_title[n.node_id] = n.text
        alias_to_node[_norm_title(n.text)] = n.node_id
        for a in n.aliases:
          alias_to_node.setdefault(_norm_title(a), n.node_id)
      # Non-article aliases resolve too, so a title/alias lookup can find a
      # paragraph by any route upstream is allowed to use.
      for a in n.aliases:
        alias_to_node.setdefault(_norm_title(a), n.node_id)

    paragraphs: list[CorpusNode] = []
    parent_article: list[str] = []
    parent_section: list[str | None] = []
    doc_strings: list[str] = []
    for n in nodes:
      if n.kind != "paragraph":
        continue
      sec = by_id.get(n.parent_id) if n.parent_id else None
      art_node = None
      art_id: str | None = None
      if sec is not None and sec.kind == "section":
        art_node = by_id.get(sec.parent_id) if sec.parent_id else None
        if art_node is not None and art_node.kind == "article":
          art_id = art_node.node_id
      if art_id is None:
        # Fallback: recover the article from the paragraph's own id.
        art_id = _ARTICLE_PREFIX + _slug_from_paragraph_id(n.node_id)
        art_node = by_id.get(art_id)
      title = article_title.get(art_id, "")
      heading = (sec.text.strip() if sec is not None else "")
      # The one documented exception. Deterministic, applied at index time, and
      # the affected count is reported so a test can assert it.
      if heading == LEAD_PLACEHOLDER:
        doc = f"{title} {n.text}".strip()
      else:
        doc = f"{title} {heading} {n.text}".strip()
      paragraphs.append(n)
      parent_article.append(art_id)
      parent_section.append(sec.node_id if sec is not None else None)
      doc_strings.append(doc)

    return CorpusView(
      nodes=nodes,
      paragraphs=paragraphs,
      by_id=by_id,
      doc_strings=doc_strings,
      parent_article=parent_article,
      parent_section=parent_section,
      tier_name=tier,
      scale=scale,
      _article_title=article_title,
      _alias_to_node=alias_to_node,
    )

  # -- accessors -----------------------------------------------------------

  @property
  def n_docs(self) -> int:
    """N for BM25. 9,979 core / 36,609 merged."""
    return len(self.paragraphs)

  def node_id(self, i: int) -> str:
    return self.paragraphs[i].node_id

  def ids(self) -> list[str]:
    """All retrievable node ids in index order."""
    return [p.node_id for p in self.paragraphs]

  def index_of(self, node_id: str) -> int:
    return self._id_to_i[node_id]

  @property
  def _id_to_i(self) -> dict[str, int]:
    cached = getattr(self, "_id_to_i_cache", None)
    if cached is None:
      cached = {p.node_id: i for i, p in enumerate(self.paragraphs)}
      object.__setattr__(self, "_id_to_i_cache", cached)
    return cached

  def title_of(self, i: int) -> str:
    return self._article_title.get(self.parent_article[i], "")

  def heading_of(self, i: int) -> str:
    sid = self.parent_section[i]
    if sid is None:
      return ""
    node = self.by_id.get(sid)
    return node.text.strip() if node is not None else ""

  def article_of(self, node_id: str) -> str:
    return self.parent_article[self.index_of(node_id)]

  def resolve_title_or_alias(self, name: str) -> str | None:
    """Canonical article node_id for a title or alias, else None.

    This is the shared title/alias lookup. It resolves to the ARTICLE node id;
    callers that need paragraphs use :meth:`paragraphs_of_article`. It never
    consults question metadata.
    """
    return self._alias_to_node.get(_norm_title(name))

  def paragraphs_of_article(self, article_node_id: str) -> list[str]:
    """Paragraph node ids of one article, in index order."""
    return [
      p.node_id for p, a in zip(self.paragraphs, self.parent_article)
      if a == article_node_id
    ]

  def lead_placeholder_sections(self) -> int:
    """How many SECTIONS carry the literal ``(lead)`` placeholder.

    Asserted == 297 by the frozen corpus: exactly one per article. A different
    number means the corpus changed and every BM25 number in the tournament is
    invalid.
    """
    return sum(
      1 for n in self.nodes
      if n.kind == "section" and n.text.strip() == LEAD_PLACEHOLDER
    )

  def lead_placeholder_docs(self) -> int:
    """How many INDEX DOCUMENTS had their ``(lead)`` heading omitted.

    This is NOT 297. It is the number of PARAGRAPHS sitting under those 297 lead
    sections, and a lead section may hold more than one paragraph (measured on
    the frozen corpus: 332 paragraphs across 297 articles, 1-5 paragraphs per
    affected article). Confusing the two is an easy way to "discover" a corpus
    defect that is not there, so both numbers are reported separately.
    """
    n = 0
    for i in range(self.n_docs):
      sec_id = self.parent_section[i]
      if sec_id is None:
        continue
      sec = self.by_id.get(sec_id)
      if sec is not None and sec.text.strip() == LEAD_PLACEHOLDER:
        n += 1
    return n

  def ancestry_complete(self) -> bool:
    """True when every paragraph resolved to a real article node."""
    return all(
      art in self._article_title
      for art in self.parent_article
    )

  def index_manifest(self) -> dict:
    """Everything needed to prove two runs indexed the same thing."""
    import hashlib

    h = hashlib.sha256()
    for s in self.doc_strings:
      h.update(s.encode("utf-8"))
      h.update(b"\x00")
    return {
      "tier": self.tier_name,
      "n_docs": self.n_docs,
      "n_nodes": len(self.nodes),
      "doc_strings_sha256": h.hexdigest(),
      "retrieval_unit": "paragraph",
      "doc_string_rule": (
        "article_title + ' ' + section_heading + ' ' + paragraph_text, "
        f"heading omitted when the section text is exactly {LEAD_PLACEHOLDER!r}"
      ),
      "lead_placeholder_sections": self.lead_placeholder_sections(),
      "lead_placeholder_docs": self.lead_placeholder_docs(),
      "ancestry_complete": self.ancestry_complete(),
      "first_doc_id": self.node_id(0) if self.n_docs else None,
      "last_doc_id": self.node_id(self.n_docs - 1) if self.n_docs else None,
    }


def _norm_title(s: str) -> str:
  """Title/alias normalisation, matching substrate.splits.norm_title's spirit.

  Deliberately simple and stdlib-only: NFKC, casefold, non-alphanumeric runs
  collapsed to a single space, strip.
  """
  import re
  import unicodedata

  u = unicodedata.normalize("NFKC", s or "").casefold()
  return re.sub(r"[^a-z0-9]+", " ", u).strip()


def load_questions(repo_root: str, split: str) -> list[dict]:
  """Worker-visible stored partition entries for one split, in file order.

  These are STORED entries and still carry split/question_type/meta. Callers
  must convert with ``substrate.query.to_model_query`` before anything
  model-facing sees them. This function deliberately returns the stored dict so
    the split filter is auditable; it never hands the dict to a model.
  """
  path = os.path.join(repo_root, "corpus", "questions.json")
  with open(path, encoding="utf-8") as fh:
      items = json.load(fh)
  if not isinstance(items, list):
    raise ValueError("corpus/questions.json must be a JSON list")
  return [e for e in items if e.get("split") == split]


def load_questions_all_splits(repo_root: str) -> list[dict]:
  path = os.path.join(repo_root, "corpus", "questions.json")
  with open(path, encoding="utf-8") as fh:
      items = json.load(fh)
  if not isinstance(items, list):
    raise ValueError("corpus/questions.json must be a JSON list")
  return items
