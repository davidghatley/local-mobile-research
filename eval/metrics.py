"""Evaluation metrics for the retrieval tournament (stdlib only).

Survival vocabulary (distinct quantities, never conflated):
- ``recall_at_k`` (TRADITIONAL, preserved): fraction of the single required
  evidence set retrieved. Alias/title routes resolve to the CANONICAL passage
  id upstream, so alternative routes do not need alternative ids here.
- ``sufficient_set_completion`` (SEPARATE metric): BINARY 1.0 iff some
  genuinely different sufficient set is fully present (0.0 otherwise, None
  without ground truth); best fractional coverage exposed separately.
- ``survival_curve``: UNINTERRUPTED lineage survival of one evidence lineage
  through consecutive pruning stages (irreversible by construction: a pruned
  lineage is dead even if a later hop re-discovers the passage; the
  re-discovery is reported separately as recovery).
- ``stage_coverage``: actual per-stage evidence coverage (direct, cumulative).
- ``conditional_retention``: retention among evidence present in the previous
  stage, WITH numerator/denominator; None rate when the denominator is 0.
- ``lost_and_recovered``: spans lost vs spans reintroduced between stages.
- Compound claims: report direct cumulative coverage. NEVER the product of
  unconditional marginal recalls (wrong denominators, hides recovery).

Calibration: ``brier_score`` / ``expected_calibration_error`` accept ONLY
finite probabilities in [0, 1] with binary labels. Raw logits are rejected
(sigmoid alone is not calibration; callers must fit and report a calibration
method in the threshold policy).
"""

from __future__ import annotations

import math


def recall_at_k(retrieved: list[str], required: set[str], k: int) -> float:
  """Traditional recall@k against ONE required evidence set (canonical ids)."""
  if not required:
    return 1.0
  top = set(retrieved[:k])
  return len(top & required) / len(required)


def reciprocal_rank(retrieved: list[str], required: set[str]) -> float:
  for i, node_id in enumerate(retrieved, start=1):
    if node_id in required:
      return 1.0 / i
  return 0.0


def ndcg_at_k(retrieved: list[str], required: set[str], k: int) -> float:
  dcg = 0.0
  for i, node_id in enumerate(retrieved[:k], start=1):
    if node_id in required:
      dcg += 1.0 / math.log2(i + 1)
  ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(required), k) + 1))
  return dcg / ideal if ideal else 1.0


def sufficient_set_completion(
  retrieved: list[str], sufficient_sets: list[set[str]]
) -> dict:
  """Binary completion over genuinely ALTERNATIVE sufficient passage sets.

  Returns {"completion": 1.0 if ANY sufficient set is fully present else 0.0
  (None when no ground truth), "best_fractional_coverage": max fractional
  coverage across sets (diagnostic, NOT completion), "best_set_index",
  "per_set_coverage", "complete_sets"}. Partial coverage never counts as
  completion. Ordinary ``recall_at_k`` is unchanged.
  """
  if not sufficient_sets:
    return {
      "completion": None,
      "best_fractional_coverage": None,
      "best_set_index": None,
      "per_set_coverage": [],
      "complete_sets": [],
    }
  have = set(retrieved)
  coverages = []
  for s in sufficient_sets:
    coverages.append(1.0 if not s else len(have & s) / len(s))
  best = max(range(len(coverages)), key=lambda i: coverages[i])
  complete = [i for i, c in enumerate(coverages) if c == 1.0]
  return {
    "completion": 1.0 if complete else 0.0,
    "best_fractional_coverage": coverages[best],
    "best_set_index": best,
    "per_set_coverage": coverages,
    "complete_sets": complete,
  }


def stage_coverage(stage_candidate_ids: list[str], evidence_ids: set[str]) -> float:
  """Direct per-stage evidence coverage: |E ∩ C_s| / |E|."""
  if not evidence_ids:
    return 1.0
  return len(set(stage_candidate_ids) & evidence_ids) / len(evidence_ids)


def survival_curve(stage_hits: list[bool]) -> list[float]:
  """UNINTERRUPTED lineage survival through consecutive pruning stages.

  ``stage_hits[i]`` = lineage evidence present after stage i. Once a lineage
  is pruned it stays 0: later re-discovery via another route/hop is NOT
  lineage survival; report it via ``lost_and_recovered`` + ``stage_coverage``.
  """
  out: list[float] = []
  alive = True
  for hit in stage_hits:
    alive = alive and bool(hit)
    out.append(1.0 if alive else 0.0)
  return out


def conditional_retention(
  prev_candidate_ids: list[str], curr_candidate_ids: list[str], evidence_ids: set[str]
) -> dict:
  """Retention among evidence present in the previous stage, with denominators.

  Returns {"rate": float|None, "numerator": int, "denominator": int}.
  rate is None (UNDEFINED, not 0) when no evidence survived the previous
  stage. Never multiply these rates across stages.
  """
  prev_kept = set(prev_candidate_ids) & evidence_ids
  curr_kept = set(curr_candidate_ids) & evidence_ids
  den = len(prev_kept)
  num = len(prev_kept & curr_kept)
  return {"rate": (num / den if den else None), "numerator": num, "denominator": den}


def lost_and_recovered(
  prev_candidate_ids: list[str], curr_candidate_ids: list[str], evidence_ids: set[str]
) -> dict:
  """Spans lost vs reintroduced between consecutive stages (sorted lists)."""
  prev = set(prev_candidate_ids)
  curr = set(curr_candidate_ids)
  lost = sorted((prev - curr) & evidence_ids)
  recovered = sorted((curr - prev) & evidence_ids)
  return {"lost": lost, "recovered": recovered}


def abstention_outcome(
  *, answerable: bool | None, abstained: bool
) -> str | None:
  """Classify one sufficiency decision against answerability ground truth.

  Returns "correct_abstention" (unanswerable + abstained: success),
  "false_abstention" (answerable + abstained: failure),
  "unsupported_generation" (unanswerable + generated: failure), or
  "answered_answerable" (answerable + generated: success). Returns None
  when ``answerable`` is None (unlabeled): no outcome is ever invented.
  """
  if answerable is None:
    return None
  if not isinstance(answerable, bool):
    raise ValueError(f"answerable must be True, False, or None; got {answerable!r}")
  abstained = bool(abstained)
  if abstained:
    return "correct_abstention" if not answerable else "false_abstention"
  return "answered_answerable" if answerable else "unsupported_generation"


def abstention_summary(records: list[dict]) -> dict:
  """Aggregate abstention outcomes with explicit denominators.

  ``records``: iterable of {"answerable": bool|None, "abstained": bool}.
  Unlabeled records (answerable None) contribute to ``n_unlabeled`` only
  and to NO rate. Each rate entry is {"n", "den", "rate"} where rate is
  None (UNDEFINED, not 0.0) when the denominator is 0 — following the
  ``conditional_retention`` precedent. Denominators: correct_abstention
  and unsupported_generation range over labeled-unanswerable records;
  false_abstention over labeled-answerable records; sufficiency_accuracy
  (correct decisions = correct_abstention + answered_answerable) over all
  labeled records.
  """
  n_correct_abstain = 0
  n_false_abstain = 0
  n_unsupported = 0
  n_answered = 0
  den_unanswerable = 0
  den_answerable = 0
  n_unlabeled = 0
  for rec in records:
    answerable = rec.get("answerable")
    if answerable is None:
      n_unlabeled += 1
      continue
    if not isinstance(answerable, bool):
      raise ValueError(f"answerable must be True, False, or None; got {answerable!r}")
    outcome = abstention_outcome(answerable=answerable, abstained=bool(rec.get("abstained")))
    if answerable:
      den_answerable += 1
      if outcome == "false_abstention":
        n_false_abstain += 1
      else:
        n_answered += 1
    else:
      den_unanswerable += 1
      if outcome == "correct_abstention":
        n_correct_abstain += 1
      else:
        n_unsupported += 1
  den_labeled = den_answerable + den_unanswerable
  n_correct = n_correct_abstain + n_answered

  def _rate(n: int, den: int) -> dict:
    return {"n": n, "den": den, "rate": (n / den if den else None)}

  return {
    "correct_abstention": _rate(n_correct_abstain, den_unanswerable),
    "false_abstention": _rate(n_false_abstain, den_answerable),
    "unsupported_generation": _rate(n_unsupported, den_unanswerable),
    "sufficiency_accuracy": _rate(n_correct, den_labeled),
    "n_labeled": den_labeled,
    "n_unlabeled": n_unlabeled,
  }


def token_stats(counts: list[int]) -> dict[str, float]:
  if not counts:
    return {"n": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
  ordered = sorted(counts)
  n = len(ordered)
  mean = sum(ordered) / n
  p50 = ordered[min(n - 1, n // 2)]
  p95 = ordered[min(n - 1, math.ceil(0.95 * n) - 1)]
  return {"n": float(n), "mean": mean, "p50": float(p50), "p95": float(p95), "max": float(ordered[-1])}


def wilson_ci(hits: int, n: int, z: float = 1.96) -> dict[str, float]:
  """Wilson score interval for a binomial proportion (95% default).

  Qualifies point rates with uncertainty; report alongside survival rates.
  """
  if n < 1:
    raise ValueError("n must be >= 1")
  if not (0 <= hits <= n):
    raise ValueError("hits must satisfy 0 <= hits <= n")
  p = hits / n
  denom = 1 + z * z / n
  center = (p + z * z / (2 * n)) / denom
  half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
  return {"lower": max(0.0, center - half), "upper": min(1.0, center + half)}


def _validate_prob_inputs(probs: list[float], labels: list[int]) -> None:
  if len(probs) != len(labels) or not probs:
    raise ValueError("probs and labels must be non-empty and same length")
  for p in probs:
    if not isinstance(p, (int, float)) or not math.isfinite(p):
      raise ValueError(f"calibration inputs must be finite, got {p!r}")
    if not (0.0 <= p <= 1.0):
      raise ValueError(
        f"calibration inputs must be probabilities in [0, 1], got {p!r}; "
        "raw logits need score_kind='logit' and a fitted calibration method "
        "(sigmoid alone is not calibration)"
      )
  for y in labels:
    if y not in (0, 1, True, False):
      raise ValueError(f"labels must be binary (0/1), got {y!r}")


def brier_score(probs: list[float], labels: list[int]) -> float:
  """Brier score on CALIBRATED probabilities only (logits rejected)."""
  _validate_prob_inputs(probs, labels)
  return sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)


def expected_calibration_error(
  probs: list[float], labels: list[int], n_bins: int = 10
) -> float:
  """ECE on CALIBRATED probabilities only (logits rejected)."""
  _validate_prob_inputs(probs, labels)
  if n_bins < 1:
    raise ValueError("n_bins must be >= 1")
  bins: list[list[int]] = [[] for _ in range(n_bins)]
  for i, p in enumerate(probs):
    idx = min(n_bins - 1, int(p * n_bins))
    bins[idx].append(i)
  ece = 0.0
  n = len(probs)
  for b in bins:
    if not b:
      continue
    acc = sum(labels[i] for i in b) / len(b)
    conf = sum(probs[i] for i in b) / len(b)
    ece += (len(b) / n) * abs(acc - conf)
  return ece
