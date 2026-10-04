"""The per-stage wire trace, written once so no system invents its own.

`docs/stage-score-semantics-notes.md` freezes the wire schema. Every stage entry
must carry, at minimum:

    stage, candidate_ids, scores, score_kind, threshold_policy,
    pruning_decisions, latency_ms, model_loading_latency_ms,
    inference_latency_ms, peak_rss_mb, model_identity

with the hard invariant ``len(candidate_ids) == len(scores) ==
len(pruning_decisions)``, and the critical invariant
``threshold_policy.score_kind == stage.score_kind``.

This module builds those entries through the frozen dataclasses so validation
happens at construction time, and it refuses to write a trace that does not
validate. A run that cannot produce a valid trace is a failed run, not a run
with a slightly-off JSON file.

Two failure modes this exists to prevent, both of which have already happened in
this project's history:

  1. Calling a logit a probability. `score_kind="logit"` with a sigmoid applied
     is still a logit. `ThresholdPolicy.validate()` enforces the domain rules,
     so a bare sigmoid cannot pass as `calibrated_probability`.
  2. Writing 0 where nothing was measured. `None` is EXPLICITLY NOT MEASURED;
     0 is a measurement of zero. The builders here take ``None`` verbatim.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.run_format import validate_trace  # noqa: E402
from substrate.types import ThresholdPolicy  # noqa: E402

# Declared interpretations for the policies this project actually uses.
# "unspecified" fails closed in ThresholdPolicy.validate(), so a stage must
# always name what its threshold means even when the policy is top-K only.
TOPK_ONLY_INTERPRETATION = "raw_score_absolute"
RANK_ONLY_CALIBRATION = "none_ranking_only"


def topk_policy(
  top_k: int,
  score_kind: str,
  min_breadth: int = 0,
  interpretation: str = TOPK_ONLY_INTERPRETATION,
  threshold: float | None = None,
) -> dict:
  """Top-K-only pruning policy with an explicitly declared interpretation.

  With ``threshold=None`` the interpretation is inert, but it must still be a
  declared, legal value -- otherwise the trace cannot say what domain the score
  lives in, which is the whole point of the field.
  """
  pol = ThresholdPolicy(
    threshold=threshold,
    interpretation=interpretation,
    top_k=top_k,
    min_breadth=min_breadth,
    calibration_method=RANK_ONLY_CALIBRATION,
    score_kind=score_kind,
  )
  pol.validate()
  return pol.to_dict()


def stage_entry(
  stage: str,
  candidate_ids: list[str],
  scores: list[float],
  score_kind: str,
  model_identity: str,
  threshold_policy: dict,
  kept: list[bool] | None = None,
  latency_ms: float = 0.0,
  model_loading_latency_ms: float | None = None,
  inference_latency_ms: float | None = None,
  peak_rss_mb: float | None = None,
) -> dict:
  """One wire stage record, validated before it is returned.

  ``model_identity`` must be a non-empty string with no placeholder. "the model"
  is not an identity; a reviewer cannot check a revision it was not told.
  """
  if not model_identity or not str(model_identity).strip():
    raise ValueError(f"stage {stage!r}: model_identity must be a non-empty string")
  if str(model_identity).strip().upper() in ("TBD", "UNKNOWN", "NONE", "UNSPECIFIED"):
    raise ValueError(f"stage {stage!r}: model_identity is a placeholder: {model_identity!r}")
  n = len(candidate_ids)
  if not (n == len(scores) == len(kept if kept is not None else candidate_ids)):
    raise ValueError(
      f"stage {stage!r}: array misalignment -- candidate_ids={n}, "
      f"scores={len(scores)}, pruning_decisions="
      f"{len(kept) if kept is not None else n}"
    )
  if kept is None:
    kept = [True] * n
  if threshold_policy.get("score_kind") != score_kind:
    raise ValueError(
      f"stage {stage!r}: threshold_policy.score_kind "
      f"({threshold_policy.get('score_kind')!r}) != stage score_kind ({score_kind!r})"
    )
  if latency_ms < 0:
    raise ValueError(f"stage {stage!r}: latency_ms must be >= 0")
  return {
    "stage": stage,
    "candidate_ids": list(candidate_ids),
    "scores": [float(s) for s in scores],
    "score_kind": score_kind,
    "threshold_policy": threshold_policy,
    "pruning_decisions": [bool(k) for k in kept],
    "latency_ms": float(latency_ms),
    "model_loading_latency_ms": model_loading_latency_ms,
    "inference_latency_ms": inference_latency_ms,
    "peak_rss_mb": peak_rss_mb,
    "model_identity": model_identity,
  }


def build_trace(
  *,
  run_id: str,
  architecture: str,
  seed: int,
  query: dict,
  stages: list[dict],
  evidence_packet: dict,
  evidence_token_count: int,
  evidence_token_method: str,
  retrieval_latency_ms: float,
  generator_id: str,
  generator_prompt_hash: str,
  generator_response: str | None,
  citations: list[str],
  available_citations: list[str],
  grader_result: dict | None = None,
  citation_audit: dict | None = None,
  model_loading_latency_ms: float | None = None,
  inference_latency_ms: float | None = None,
  peak_rss_mb: float | None = None,
  storage_bytes: int | None = None,
  adaptive_compute_decision: str | None = None,
  extra: dict[str, Any] | None = None,
) -> dict:
  """Assemble a full per-question wire trace and VALIDATE it before returning.

  ``generator_response`` is None on an abstention: the abstained item never
  touched the generator, and saying so with None is correct. It is NOT "", which
  would read as an empty generation -- a distinct failure mode the frozen
  protocol keeps separate on purpose (`empty_generation` vs a clean abstention).

  ``evidence_token_count`` must be an int. A whitespace estimate is rejected by
  ``validate_trace`` unless a caller explicitly opts into ``allow_estimate``,
  which no empirical Round 1 run does.
  """
  trace: dict[str, Any] = {
    "question_id": query["question_id"],
    "run_id": run_id,
    "architecture": architecture,
    "seed": seed,
    "query": query,
    "stages": stages,
    "adaptive_compute_decision": adaptive_compute_decision,
    "evidence_packet": evidence_packet,
    "evidence_token_count": evidence_token_count,
    "evidence_token_method": evidence_token_method,
    "retrieval_latency_ms": retrieval_latency_ms,
    "model_loading_latency_ms": model_loading_latency_ms,
    "inference_latency_ms": inference_latency_ms,
    "peak_rss_mb": peak_rss_mb,
    "storage_bytes": storage_bytes,
    "generator_prompt_hash": generator_prompt_hash,
    "generator_id": generator_id,
    "generator_response": generator_response,
    "citations": list(citations),
    "available_citations": list(available_citations),
    "grader_result": grader_result,
  }
  if citation_audit is not None:
    trace["citation_audit"] = citation_audit
  if extra:
    trace["extra"] = extra
  errors = validate_trace(trace, allow_estimate=False, allow_stub=False)
  if errors:
    raise ValueError(
      f"trace for {query['question_id']} failed validation: {errors}"
    )
  return trace


def write_traces(path: str, traces: list[dict]) -> dict:
  """Write one JSON object per line. Raises on any validation failure."""
  for t in traces:
    errors = validate_trace(t, allow_estimate=False, allow_stub=False)
    if errors:
      raise ValueError(f"trace {t.get('question_id')} invalid: {errors}")
  os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
  with open(path, "w", encoding="utf-8") as fh:
    for t in traces:
      fh.write(json.dumps(t, sort_keys=True) + "\n")
  return {"path": path, "n_traces": len(traces)}


def read_traces(path: str) -> list[dict]:
  out: list[dict] = []
  with open(path, encoding="utf-8") as fh:
    for line in fh:
      if line.strip():
        out.append(json.loads(line))
  return out
