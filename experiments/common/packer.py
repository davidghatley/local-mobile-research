"""Evidence packet construction under the shared, frozen budget policy.

`experiments/baselines/HYPOTHESIS.md` §2.3 specifies the packing policy that every
Round 1 system shares. Implemented here once:

  - input is the system's FINAL RANKED paragraph list, in rank order;
  - spans are WHOLE paragraph nodes (``EvidenceSpan(node_id, text)``, offsets
    None, ``hop=0``) -- the packet never carries a partial span, because a
    truncated span degrades the 1.5B generator and would make architectures
    incomparable for a reason that has nothing to do with architecture;
  - PER-ARTICLE CAP: at most 3 spans from any one article, applied as a
    deterministic skip, so one article's strong lexical match cannot eat the
    whole budget on a multi-hop or comparison item;
  - ``build_packet`` then applies the frozen strict ranked-prefix rule with the
    HARD_EVIDENCE_TOKEN_CAP and EXACT pinned-generator tokens.

An architecture does not get to improve answer quality by handing the generator
four times as much text. The cap is the same for every arm of the tournament,
including the oracle arm, and it is enforced here rather than trusted.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from substrate.evidence import (  # noqa: E402
  HARD_EVIDENCE_TOKEN_CAP, build_packet)
from substrate.types import EvidencePacket, EvidenceSpan  # noqa: E402

PER_ARTICLE_CAP = 3


@dataclass(frozen=True)
class PackReport:
  """What the packer did, so a trace can explain an empty or short packet."""

  considered: int
  admitted: int
  skipped_per_article_cap: int
  skipped_over_budget: int
  distinct_articles: int
  exact_evidence_tokens: int | None
  truncated: bool
  token_count_method: str


def spans_from_ranked(
  ranked_node_ids: list[str],
  node_text: dict[str, str],
  per_article_cap: int = PER_ARTICLE_CAP,
  node_article: dict[str, str] | None = None,
) -> tuple[list[EvidenceSpan], dict]:
  """Turn a final ranked id list into whole-paragraph spans under the cap.

  ``node_article`` maps node_id -> article node_id. It is REQUIRED to enforce
  the per-article cap; without it the cap cannot be applied, so this raises
  rather than silently shipping an uncapped packet.

  Returns the spans plus a bookkeeping dict. The cap is applied BEFORE the token
  budget, in rank order: a skipped span does not consume budget and does not
  stop packing (unlike a budget overflow, which stops everything).
  """
  if per_article_cap and node_article is None:
    raise ValueError(
      "node_article is required to enforce the per-article cap; refusing to "
      "build an uncapped packet"
    )
  spans: list[EvidenceSpan] = []
  per_article: dict[str, int] = {}
  skipped_cap = 0
  for nid in ranked_node_ids:
    art = node_article.get(nid) if node_article else None
    if per_article_cap:
      if art is not None and per_article.get(art, 0) >= per_article_cap:
        skipped_cap += 1
        continue
      if art is not None:
        per_article[art] = per_article.get(art, 0) + 1
    text = node_text.get(nid)
    if text is None:
      continue
    spans.append(EvidenceSpan(node_id=nid, text=text, hop=0))
  return spans, {"skipped_per_article_cap": skipped_cap,
                 "distinct_articles": len(per_article)}


def build_ranked_packet(
  question_id: str,
  ranked_node_ids: list[str],
  node_text: dict[str, str],
  tokenizer,
  tokenizer_id: str,
  node_article: dict[str, str] | None = None,
  per_article_cap: int = PER_ARTICLE_CAP,
  cap: int = HARD_EVIDENCE_TOKEN_CAP,
) -> tuple[EvidencePacket, PackReport]:
  """The one path from a ranked list to a packet. Exact tokens, strict cap."""
  spans, info = spans_from_ranked(
    ranked_node_ids, node_text, per_article_cap, node_article)
  packet = build_packet(
    question_id=question_id,
    spans=spans,
    hop_count=0,
    cap=cap,
    tokenizer=tokenizer,
    tokenizer_id=tokenizer_id,
    exact=True,  # REQUIRED: refuses to fall back to a whitespace estimate
  )
  report = PackReport(
    considered=len(ranked_node_ids),
    admitted=len(packet.spans),
    skipped_per_article_cap=info["skipped_per_article_cap"],
    # A budget overflow stops packing entirely; the remainder of the ranked list
    # is what did not make it in for budget reasons rather than cap reasons.
    skipped_over_budget=max(0, len(spans) - len(packet.spans)) if not packet.truncated else 0,
    distinct_articles=info["distinct_articles"],
    exact_evidence_tokens=packet.exact_evidence_tokens,
    truncated=packet.truncated,
    token_count_method=packet.token_count_method,
  )
  return packet, report
