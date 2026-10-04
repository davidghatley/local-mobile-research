"""CUSTODIAN-ONLY oracle evidence packets, for the generator-floor probe.

`experiments/comparability/CONTRACT.md` §5 is explicit about who may run the
oracle probe and why it is legitimate:

  - the CUSTODIAN may construct an oracle packet, because the custodian has
    access to the ground-truth required evidence set;
  - a WORKER may NOT, because that would hand the worker the answer's location;
  - the packet is packed with the SAME ``build_packet`` semantics, the SAME
    pinned tokenizer and the SAME hard cap as every other arm, so the only
    difference between arms is WHICH spans are selected;
  - the verdict is an infrastructure check, not an architecture result.

Two guards enforce the second bullet in code rather than in prose:

1. :func:`assert_custodian_context` must be called with an explicit custodian
   token before any packet is built. There is no default.
2. Every packet records, per item, WHICH required atom ids it carries, in a
   custodian-side audit file. That file is the evidence that the probe measured
   what it claims, and it is what an independent reviewer reads to check the
   probe did not quietly become a retriever.

Scope limit, stated because it is the easiest thing to get wrong: the oracle is
built from the PUBLIC worker's own partition entries (dev / shadow_dev) and
their recorded evidence groups. It never touches the sealed private set, and it
never returns a private id, text, answer or atom.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from substrate.types import EvidenceSpan  # noqa: E402

CUSTODIAN_TOKEN_ENV = "LMR_CUSTODIAN_ORACLE_TOKEN"
_CUSTODIAN_TOKEN = "custodian-only-oracle-packet-v1"


def assert_custodian_context(why: str) -> None:
  """Fail closed unless the caller presented the custodian token.

  Deliberately unforgiving: there is no default, no fallback, and no
  "development mode". A worker that reaches this function without the token
  gets an exception, not a packet.
  """
  got = os.environ.get(CUSTODIAN_TOKEN_ENV)
  if got != _CUSTODIAN_TOKEN:
    raise PermissionError(
      "oracle packet construction is custodian-only: it requires the "
      f"{CUSTODIAN_TOKEN_ENV} environment token. Requested by: {why!r}. "
      "A worker must not construct an oracle packet -- it hands the worker the "
      "answer's location (experiments/comparability/CONTRACT.md §5)."
    )


@dataclass(frozen=True)
class OracleSelection:
  """Which paragraphs the custodian chose, and why, for one item."""

  question_id: str
  ranked_node_ids: tuple[str, ...]
  required_atom_ids: tuple[str, ...]
  host_paragraph_ids: tuple[str, ...]
  n_required_atoms: int
  n_hosts: int
  complete: bool


def select_oracle_paragraphs(
  question_id: str,
  required_atom_ids: list[str],
  atom_to_host: dict[str, str],
  host_to_article: dict[str, str],
  max_per_article: int = 3,
) -> OracleSelection:
  """Map required sentence atoms to their host paragraphs, deterministically.

  The retrieval unit is the paragraph, and retrieving an ancestor paragraph
  SATISFIES a leaf-sentence atom (`eval/support.py::covers`, ancestry-aware).
  So the minimal complete sufficient set at paragraph granularity is: the set of
  DISTINCT HOST PARAGRAPHS of the item's required atoms.

  Ordering is deterministic and label-free: hosts are ordered by article
  (ascending UTF-8 bytes) then by node id, so an oracle packet's text order
  cannot leak which atom was "first" or otherwise encode ranking information.
  The per-article cap is applied identically to every arm of the tournament, so
  an item whose required atoms span more than ``max_per_article`` paragraphs in
  one article is handled the same way here as anywhere else.
  """
  hosts: list[str] = []
  seen: set[str] = set()
  for atom in required_atom_ids:
    host = atom_to_host.get(atom)
    if host is None or host in seen:
      continue
    seen.add(host)
    hosts.append(host)
  hosts.sort(key=lambda nid: (host_to_article.get(nid, "").encode("utf-8"), nid.encode("utf-8")))
  capped: list[str] = []
  per_article: dict[str, int] = {}
  dropped: list[str] = []
  for nid in hosts:
    art = host_to_article.get(nid, "")
    if per_article.get(art, 0) >= max_per_article:
      dropped.append(nid)
      continue
    per_article[art] = per_article.get(art, 0) + 1
    capped.append(nid)
  return OracleSelection(
    question_id=question_id,
    ranked_node_ids=tuple(capped),
    required_atom_ids=tuple(required_atom_ids),
    host_paragraph_ids=tuple(hosts),
    n_required_atoms=len(required_atom_ids),
    n_hosts=len(hosts),
    complete=not dropped,
  )


def degraded_selection(
  view,
  question_id: str,
  bm25_scored: list[tuple[int, float]],
  exclude: set[str],
  k: int = 4,
) -> tuple[str, ...]:
  """A deliberately worse but PLAUSIBLE packet: BM25's worst-ranked paragraphs.

  This is the negative control the baseline plan requires
  (`experiments/baselines/HYPOTHESIS.md` §6). Its purpose is to establish that
  the generator DOES discriminate when evidence quality differs, so that a null
  oracle-vs-B4 result can be read as "no ceiling to detect" rather than "the
  generator is insensitive to evidence entirely".

  Paragraphs carrying any required atom are excluded, so the control cannot
  accidentally contain the answer. If too few remain, the control is reported as
  unavailable for that item rather than silently back-filled with answer-bearing
  text.
  """
  tail = [i for i, _ in reversed(bm25_scored) if view.node_id(i) not in exclude]
  chosen = tuple(view.node_id(i) for i in tail[:k])
  return chosen
