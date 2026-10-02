"""Model-facing query contract: the boundary between stored entries and models.

corpus/questions.json is a STORED partition artifact. Every entry carries
evaluation metadata -- split, question_type, meta, provenance -- that the
evaluator and the orchestrator legitimately need for scoring. That metadata
must never cross into model-facing inputs: handing a sufficiency controller
question_type="unanswerable" hands it the decision it was supposed to make.

This module freezes the boundary (Round 0 closure, blocker 5):

- QueryInput: the ONLY model-facing question object. Two fields, frozen:
  question_id, text.
- to_model_query(entry): the ONLY sanctioned conversion from a stored
  partition entry to QueryInput. It copies question_id and text and NOTHING
  else; split, question_type, meta and provenance never cross this
  boundary.
- MODEL_FACING_FIELDS / FORBIDDEN_MODEL_FIELDS: the documented allowlist
  and denylist.
- model_visible_payload(entry): the exact dict a model may see for a stored
  partition entry (the allowlist and nothing else).
- assert_no_label_metadata(payload): fail-closed guard that raises
  ForbiddenMetadataError if a forbidden field is present on anything
  heading to a model, including attributes smuggled onto a QueryInput via
  object.__setattr__.
- worker_regime_b_exclusions(): the Regime B adaptation-data exclusion list
  for architecture workers, derived from the PUBLIC preregistered artifact
  corpus/regime_b_excluded_articles.json ONLY. Private paired-regime
  metadata (15 custodial paired items over 13 source articles, living
  outside the repository) never shapes a worker exclusion list; the public
  21 is a preregistered superset, so scoring the 15 secret paired items
  never reveals which 13 of the 21 matter. Invariant tested in
  tests/test_query_contract.py.

Verified against the committed corpus/questions.json (do not assume):
meta is NOT empty for every entry. 119 of 206 entries have meta == {}; the
87 shadow_dev reclassifications carry meta = {original_id, exposure_note}
only. No entry carries group / evidence_groups / source_articles in meta:
the builder (data_tools/build_public_partition.py) drops the answer's
LOCATION from meta in every entry, but original_id/exposure_note survive as
the reclassification record.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# The EXACT set of fields a model may see. Anything else on a stored
# partition entry is evaluation/orchestration metadata and stays on the
# stored side of this boundary.
MODEL_FACING_FIELDS: frozenset[str] = frozenset({"question_id", "text"})

# Fields that MUST NOT reach a model (denied regardless of split, regime,
# or architecture). Matched case-sensitively as payload keys / attribute
# names. Grouped by what they would hand a model:
FORBIDDEN_MODEL_FIELDS: frozenset[str] = frozenset({
  # evaluation metadata: hands a controller the desired decision
  "split",
  "question_type",
  "answerability",
  # the answer's LOCATION: a 1-3 article candidate set inside the corpus
  "group",
  "evidence_groups",
  "source_articles",
  # Regime-B membership / paired-condition tagging
  "regime",
  "regime_b",
  "regime_b_member",
  "regime_b_membership",
  "paired",
  "paired_regime",
  "paired_regime_b",
  # retrieval ground truth
  "evidence",
  "sufficient_sets",
  "hard_negatives",
  # labels / answers
  "label",
  "labels",
  "answer_text",
  # stored-entry containers: never model-facing in their entirety
  "meta",
  "provenance",
})


class ForbiddenMetadataError(ValueError):
  """A forbidden label/evaluation field reached a model-facing payload."""


# Maximum nesting depth the guard inspects. Payloads this deep are refused
# fail-closed rather than inspected partially.
_MAX_SURFACE_DEPTH = 10


@dataclass(frozen=True)
class QueryInput:
  """The ONLY model-facing question surface.

  Exactly two fields, by construction: question_id and text. No split, no
  question_type, no answerability, no group/source articles, no Regime-B
  membership, no evidence, no labels, no provenance. Normal attribute
  assignment is impossible (frozen); assert_no_label_metadata additionally
  catches smuggling via object.__setattr__ by checking the instance
  __dict__ itself.
  """

  question_id: str
  text: str

  def to_dict(self) -> dict:
    """The model-facing payload: exactly MODEL_FACING_FIELDS, nothing else."""
    return {"question_id": self.question_id, "text": self.text}


def _surface_keys(obj: object, depth: int = 0):
  """Yield every key a model could see on a payload, at every level.

  Mappings yield their keys (and recurse into values); sequences recurse;
  any other object yields its instance attribute names and recurses into
  attribute values. A QueryInput therefore yields exactly its fields,
  including attributes smuggled on via object.__setattr__.
  """
  if depth > _MAX_SURFACE_DEPTH:
    raise ValueError(
      f"model-facing payload nested deeper than {_MAX_SURFACE_DEPTH}; "
      "refusing to inspect (fail closed)"
    )
  if isinstance(obj, Mapping):
    for key, value in obj.items():
      yield key
      yield from _surface_keys(value, depth + 1)
  elif isinstance(obj, (list, tuple, set, frozenset)):
    for value in obj:
      yield from _surface_keys(value, depth + 1)
  else:
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
      for key, value in d.items():
        yield key
        yield from _surface_keys(value, depth + 1)


def assert_no_label_metadata(payload: object) -> None:
  """Fail-closed guard: raise if any forbidden field is present.

  Accepts a QueryInput (instance attributes are checked, which catches
  smuggling via object.__setattr__ on the frozen dataclass) or any payload
  destined for a model: for dicts/lists/nested structures, EVERY dict key
  at EVERY level is checked, so {"context": {"labels": ...}} fails too.
  Keys are matched case-sensitively; VALUES are not scanned for prose.
  Returns None when the payload is clean.
  """
  found: set[str] = set()
  for key in _surface_keys(payload):
    if key in FORBIDDEN_MODEL_FIELDS:
      found.add(key)
      if len(found) > 8:
        break
  if found:
    raise ForbiddenMetadataError(
      f"model-facing payload carries forbidden field(s): {sorted(found)}; "
      f"only MODEL_FACING_FIELDS={sorted(MODEL_FACING_FIELDS)} may reach a model"
    )


def to_model_query(entry: object) -> QueryInput:
  """The ONLY sanctioned conversion from a stored partition entry to the
  model-facing surface.

  Copies exactly question_id and text. split, question_type, meta,
  provenance and any other stored field never cross this boundary: they
  are evaluation metadata the evaluator and orchestrator need for scoring,
  and handing them to a model (notably question_type="unanswerable")
  hands it the desired decision.

  Accepts a Mapping (a corpus/questions.json entry), an object carrying
  question_id/text attributes (e.g. substrate.types.Question), or an
  existing QueryInput (idempotent). Raises ValueError when the entry does
  not carry nonempty string question_id/text. The result is always
  validated by assert_no_label_metadata before it is returned.
  """
  if isinstance(entry, QueryInput):
    query = entry
  else:
    if isinstance(entry, Mapping):
      qid = entry.get("question_id")
      text = entry.get("text")
    else:
      qid = getattr(entry, "question_id", None)
      text = getattr(entry, "text", None)
    if not isinstance(qid, str) or not qid:
      raise ValueError(
        "to_model_query: entry must carry a nonempty string 'question_id'"
      )
    if not isinstance(text, str) or not text:
      raise ValueError("to_model_query: entry must carry a nonempty string 'text'")
    query = QueryInput(question_id=qid, text=text)
  assert_no_label_metadata(query)
  return query


def model_visible_payload(entry: object) -> dict:
  """Return EXACTLY what a model may see for a stored partition entry.

  The keys are precisely MODEL_FACING_FIELDS ({'question_id', 'text'}) and
  the values are the ones to_model_query copied. Anything else on the
  stored entry -- split, question_type, meta, provenance -- stays on the
  stored side of the boundary.
  """
  return to_model_query(entry).to_dict()


REGIME_B_EXCLUSION_ARTIFACT = "corpus/regime_b_excluded_articles.json"

# Path tokens that mark private-content territory. The worker exclusion
# source is refused fail-closed if its resolved path carries any of them,
# so a redirect can never point the worker list at private material.
_PRIVATE_PATH_TOKENS = ("private", "sealed", "labels")


@dataclass(frozen=True)
class RegimeBWorkerExclusions:
  """Worker-facing Regime B adaptation-data exclusion list.

  articles: the PUBLIC preregistered exclusion superset -- 21 article
  titles over the cambridge / corona / jaguar / lincoln / washington
  groups. Workers exclude exactly these from architecture-specific
  synthetic training/adaptation data; they REMAIN in the query-time
  retrieval corpus.

  source_artifact / source_sha256: provenance (which public file the list
  came from, and its byte hash). split_map_sha256: the pinned split-map
  hash recorded in the artifact.
  """

  articles: tuple[str, ...]
  source_artifact: str
  source_sha256: str
  split_map_sha256: str

  def to_dict(self) -> dict:
    return {
      "articles": list(self.articles),
      "source_artifact": self.source_artifact,
      "source_sha256": self.source_sha256,
      "split_map_sha256": self.split_map_sha256,
    }


def worker_regime_b_exclusions(
  repo_root: str | Path | None = None,
) -> RegimeBWorkerExclusions:
  """The ONLY sanctioned source of the worker Regime B exclusion list.

  Reads the PUBLIC artifact corpus/regime_b_excluded_articles.json and
  NOTHING else. The private paired-regime metadata (15 custodial paired
  items over 13 source articles) lives outside the repository, and no
  function in this module -- or any function a worker may call -- reads
  it to shape a worker exclusion list. Because the public 21 is a
  preregistered SUPERSET of the private 13, scoring the 15 secret paired
  items never reveals which 13 of the 21 matter.

  Invariant (tested in tests/test_query_contract.py): the returned list is
  derived from the public artifact alone and equals its "articles" field;
  no private path is ever opened.

  Raises ValueError on a private-labeled source path, a malformed
  artifact, or a missing adaptation-only scope declaration.
  """
  root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parent.parent
  path = root / REGIME_B_EXCLUSION_ARTIFACT
  lowered = str(path).lower()
  if any(token in lowered for token in _PRIVATE_PATH_TOKENS):
    raise ValueError(
      f"refusing Regime B exclusion source that looks private: {path} "
      "(the worker list comes from the public artifact only)"
    )
  with open(path, "rb") as fh:
    raw = fh.read()
  try:
    doc = json.loads(raw.decode("utf-8"))
  except (ValueError, UnicodeDecodeError) as exc:
    raise ValueError(f"{REGIME_B_EXCLUSION_ARTIFACT}: unreadable JSON: {exc}") from exc
  if not isinstance(doc, dict):
    raise ValueError(f"{REGIME_B_EXCLUSION_ARTIFACT}: top level must be a JSON object")
  articles = doc.get("articles")
  if (
    not isinstance(articles, list)
    or not articles
    or any(not isinstance(a, str) or not a.strip() for a in articles)
  ):
    raise ValueError(
      f"{REGIME_B_EXCLUSION_ARTIFACT}: 'articles' must be a nonempty list "
      "of nonempty strings"
    )
  scope = str(doc.get("scope", "")).lower()
  if "adaptation" not in scope or "query-time" not in scope:
    raise ValueError(
      f"{REGIME_B_EXCLUSION_ARTIFACT}: 'scope' must state adaptation-data "
      "exclusion only, with the query-time corpus unchanged"
    )
  split_map_sha = doc.get("split_map_sha256")
  if not isinstance(split_map_sha, str) or not split_map_sha:
    raise ValueError(f"{REGIME_B_EXCLUSION_ARTIFACT}: missing split_map_sha256 pin")
  return RegimeBWorkerExclusions(
    articles=tuple(articles),
    source_artifact=REGIME_B_EXCLUSION_ARTIFACT,
    source_sha256=hashlib.sha256(raw).hexdigest(),
    split_map_sha256=split_map_sha,
  )


__all__ = [
  "FORBIDDEN_MODEL_FIELDS",
  "MODEL_FACING_FIELDS",
  "REGIME_B_EXCLUSION_ARTIFACT",
  "ForbiddenMetadataError",
  "QueryInput",
  "RegimeBWorkerExclusions",
  "assert_no_label_metadata",
  "model_visible_payload",
  "to_model_query",
  "worker_regime_b_exclusions",
]
