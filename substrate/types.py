"""Round 0 common substrate: canonical dataclasses shared by all experiments.

All schemas are JSON-serializable via ``to_dict`` / ``from_dict`` helpers.
No architecture logic lives here.

Conventions (Round 0 v0.2):
- Telemetry fields use ``None`` to mean EXPLICITLY NOT MEASURED (never silent).
- Score semantics travel with scores via ``score_kind``; raw logits are legal
  for ranking iff ``score_kind`` says so, and are NEVER valid ECE/Brier inputs
  (sigmoid alone is not calibration).
- ``Candidate.node_id`` is always the CANONICAL passage id; alias/redirect/
  title routes resolve to it before scoring. Genuinely different sufficient
  passages are separate ids (see eval completion metric, not recall).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field


def canonical_json(obj: object) -> str:
  return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Score domains. Raw (uncalibrated) kinds are legal for RANKING only and must
# be labeled; only "calibrated_probability" may feed ECE/Brier or be compared
# to a probability threshold.
SCORE_KINDS = (
  "calibrated_probability",
  "logit",
  "similarity",
  "distance",
  "rank",
)

# How a threshold value is to be interpreted. "unspecified" is fail-closed:
# freeze rejects it.
THRESHOLD_INTERPRETATIONS = (
  "calibrated_probability",
  "raw_score_absolute",
  "raw_score_percentile",
  "unspecified",
)

# Calibration methods. "none_ranking_only" means scores are used for ranking
# (top-K / percentile) and must NOT be thresholded as probabilities.
# "model_probability" means the model natively emits probabilities (e.g.
# P(yes)) that are EVALUABLE via ECE/Brier and usable with dev-selected
# thresholds WITHOUT forced fitted calibration — but they are NOT certified
# calibrated. Truly calibrated claims require a fitted method PLUS provenance
# (calibration_partition). NOTE: a bare sigmoid/logistic squash with no
# fitted validation is NOT calibration; record it as "none_ranking_only",
# never as "platt".
CALIBRATION_METHODS = (
  "none_ranking_only",
  "model_probability",
  "temperature_scaling",
  "platt",
  "isotonic",
  "beta",
  "other_fitted",
  "unspecified",
)

# Methods that fit parameters on calibration data and therefore CERTIFY a
# calibrated claim only together with provenance (calibration_partition).
FITTED_CALIBRATION_METHODS = frozenset(
  {"temperature_scaling", "platt", "isotonic", "beta", "other_fitted"}
)

# Generator ids reserved for infrastructure-only stubs. Benchmark/freeze
# validation rejects these (fail closed); infra tests opt in explicitly.
STUB_GENERATOR_IDS = frozenset({"stub-infra-only-v0"})


def is_stub_generator(generator_id: str) -> bool:
  return generator_id in STUB_GENERATOR_IDS


def validate_score_value(score: float, score_kind: str) -> None:
  """Raise ValueError unless ``score`` is valid for ``score_kind``.

  Calibrated probabilities must be finite and in [0, 1]. Raw kinds must be
  finite (no range constraint). Non-finite values are always rejected.
  """
  if score_kind not in SCORE_KINDS:
    raise ValueError(f"unknown score_kind {score_kind!r}; expected one of {SCORE_KINDS}")
  if not isinstance(score, (int, float)) or not math.isfinite(score):
    raise ValueError(f"score must be finite, got {score!r} (kind={score_kind})")
  if score_kind == "calibrated_probability" and not (0.0 <= score <= 1.0):
    raise ValueError(
      f"calibrated_probability must be in [0, 1], got {score!r}; "
      "raw logits need score_kind='logit' and must not feed ECE/Brier"
    )


@dataclass(frozen=True)
class CorpusNode:
  """One addressable unit of the offline corpus DAG.

  ``kind`` is one of: corpus, cluster, article, section, paragraph, sentence.
  ``parent_id`` is the primary hierarchy edge; ``links`` holds cross-link DAG edges.
  ``node_id`` is CANONICAL: alias/redirect/title routes resolve to it upstream.
  """

  node_id: str
  kind: str
  text: str
  parent_id: str | None = None
  links: tuple[str, ...] = ()
  aliases: tuple[str, ...] = ()
  meta: dict[str, str] = field(default_factory=dict)

  def to_dict(self) -> dict:
    d = asdict(self)
    d["links"] = list(self.links)
    d["aliases"] = list(self.aliases)
    return d

  @staticmethod
  def from_dict(d: dict) -> "CorpusNode":
    for f in ("node_id", "kind", "text"):
      if f not in d:
        raise ValueError(f"CorpusNode missing required field: {f}")
    return CorpusNode(
      node_id=d["node_id"],
      kind=d["kind"],
      text=d["text"],
      parent_id=d.get("parent_id"),
      links=tuple(d.get("links", ())),
      aliases=tuple(d.get("aliases", ())),
      meta=dict(d.get("meta", {})),
    )


@dataclass(frozen=True)
class Question:
  question_id: str
  text: str
  split: str = "dev"  # train | dev | heldout
  meta: dict[str, str] = field(default_factory=dict)

  def to_dict(self) -> dict:
    return asdict(self)

  @staticmethod
  def from_dict(d: dict) -> "Question":
    for f in ("question_id", "text"):
      if f not in d:
        raise ValueError(f"Question missing required field: {f}")
    return Question(
      question_id=d["question_id"],
      text=d["text"],
      split=d.get("split", "dev"),
      meta=dict(d.get("meta", {})),
    )


@dataclass(frozen=True)
class ThresholdPolicy:
  """Per-stage pruning policy. No hardcoded thresholds in experiment code.

  ``interpretation`` declares what ``threshold`` means; ``top_k`` is the
  rank floor (keep top-K regardless); ``min_breadth`` preserves minimum
  search breadth; ``calibration_method`` records how scores were calibrated
  (or "none_ranking_only" for ranking use).
  """

  threshold: float | None = None
  interpretation: str = "unspecified"
  top_k: int | None = None
  min_breadth: int = 0
  calibration_method: str = "unspecified"
  score_kind: str = "calibrated_probability"
  calibration_partition: str = ""  # provenance (hash/id) for fitted claims

  def validate(self) -> list[str]:
    errors: list[str] = []
    if self.interpretation not in THRESHOLD_INTERPRETATIONS:
      errors.append(f"unknown threshold interpretation: {self.interpretation!r}")
    if self.calibration_method not in CALIBRATION_METHODS:
      errors.append(f"unknown calibration_method: {self.calibration_method!r}")
    if self.score_kind not in SCORE_KINDS:
      errors.append(f"unknown score_kind: {self.score_kind!r}")
    if self.interpretation == "unspecified":
      errors.append("threshold interpretation is unspecified (fail closed)")
    if self.threshold is not None:
      try:
        validate_score_value(self.threshold, self.score_kind)
      except ValueError as exc:
        errors.append(f"threshold invalid for {self.score_kind}: {exc}")
      if self.interpretation == "calibrated_probability":
        if self.score_kind != "calibrated_probability":
          errors.append("probability interpretation requires calibrated_probability scores")
        elif self.calibration_method in ("none_ranking_only", "unspecified"):
          errors.append(
            "probability threshold without evaluable model probabilities "
            "(ranking-only scores and sigmoid alone are not calibration)"
          )
        elif (
          self.calibration_method in FITTED_CALIBRATION_METHODS
          and not self.calibration_partition
        ):
          errors.append("fitted calibration claim requires provenance (calibration_partition)")
        # "model_probability" passes: natively probabilistic, ECE/Brier-
        # evaluable, dev-thresholdable without forced fitted calibration.
      # raw_score_absolute / raw_score_percentile are legal with any
      # score_kind and need no calibration claim.
    if self.top_k is not None and self.top_k < 1:
      errors.append("top_k must be >= 1")
    if self.min_breadth < 0:
      errors.append("min_breadth must be >= 0")
    return errors

  def to_dict(self) -> dict:
    return asdict(self)

  @staticmethod
  def from_dict(d: dict | float | int) -> "ThresholdPolicy":
    # Legacy float migration: explicit but fail-closed (interpretation
    # "unspecified" is rejected by freeze validation, never silently trusted).
    if isinstance(d, (float, int)):
      return ThresholdPolicy(threshold=float(d), interpretation="unspecified")
    return ThresholdPolicy(
      threshold=None if d.get("threshold") is None else float(d["threshold"]),
      interpretation=d.get("interpretation", "unspecified"),
      top_k=None if d.get("top_k") is None else int(d["top_k"]),
      min_breadth=int(d.get("min_breadth", 0)),
      calibration_method=d.get("calibration_method", "unspecified"),
      score_kind=d.get("score_kind", "calibrated_probability"),
      calibration_partition=d.get("calibration_partition", ""),
    )


@dataclass(frozen=True)
class Candidate:
  node_id: str  # canonical passage id (aliases resolved upstream)
  stage: str
  score: float
  rank: int
  kept: bool
  threshold: float | None = None
  score_kind: str = "calibrated_probability"

  def to_dict(self) -> dict:
    return asdict(self)

  @staticmethod
  def from_dict(d: dict) -> "Candidate":
    for f in ("node_id", "stage", "score", "rank", "kept"):
      if f not in d:
        raise ValueError(f"Candidate missing required field: {f}")
    return Candidate(
      node_id=d["node_id"],
      stage=d["stage"],
      score=float(d["score"]),
      rank=int(d["rank"]),
      kept=bool(d["kept"]),
      threshold=None if d.get("threshold") is None else float(d["threshold"]),
      score_kind=d.get("score_kind", "calibrated_probability"),
    )


@dataclass(frozen=True)
class EvidenceSpan:
  node_id: str  # canonical passage id
  text: str
  char_start: int | None = None
  char_end: int | None = None
  hop: int = 0

  def to_dict(self) -> dict:
    return asdict(self)

  @staticmethod
  def from_dict(d: dict) -> "EvidenceSpan":
    for f in ("node_id", "text"):
      if f not in d:
        raise ValueError(f"EvidenceSpan missing required field: {f}")
    return EvidenceSpan(
      node_id=d["node_id"],
      text=d["text"],
      char_start=d.get("char_start"),
      char_end=d.get("char_end"),
      hop=int(d.get("hop", 0)),
    )


@dataclass(frozen=True)
class EvidencePacket:
  """Bounded evidence handed to the single fixed generator.

  ``citations`` = AVAILABLE citations (canonical node ids backing the spans).
  Emitted citations live on ``GeneratedAnswer.citations``; unknown emitted
  ids are diagnosed by ``evidence.find_unknown_citations``.
  ``exact_evidence_tokens`` is the model-tokenizer count of the canonical
  serialization (None = not measured). ``prompt_tokens`` is the whole rendered
  model input incl. template/system (None = not measured). ``token_estimate``
  + ``token_count_method`` retain the whitespace estimate for INFRA use only.
  """

  question_id: str
  spans: tuple[EvidenceSpan, ...]
  citations: tuple[str, ...]
  token_estimate: int
  hop_count: int = 0
  truncated: bool = False
  token_count_method: str = "whitespace-estimate"
  exact_evidence_tokens: int | None = None
  prompt_tokens: int | None = None

  def to_dict(self) -> dict:
    return {
      "question_id": self.question_id,
      "spans": [s.to_dict() for s in self.spans],
      "citations": list(self.citations),
      "token_estimate": self.token_estimate,
      "hop_count": self.hop_count,
      "truncated": self.truncated,
      "token_count_method": self.token_count_method,
      "exact_evidence_tokens": self.exact_evidence_tokens,
      "prompt_tokens": self.prompt_tokens,
    }

  @staticmethod
  def from_dict(d: dict) -> "EvidencePacket":
    for f in ("question_id", "token_estimate"):
      if f not in d:
        raise ValueError(f"EvidencePacket missing required field: {f}")
    return EvidencePacket(
      question_id=d["question_id"],
      spans=tuple(EvidenceSpan.from_dict(s) for s in d.get("spans", [])),
      citations=tuple(d.get("citations", [])),
      token_estimate=int(d["token_estimate"]),
      hop_count=int(d.get("hop_count", 0)),
      truncated=bool(d.get("truncated", False)),
      token_count_method=d.get("token_count_method", "whitespace-estimate"),
      exact_evidence_tokens=None
      if d.get("exact_evidence_tokens") is None
      else int(d["exact_evidence_tokens"]),
      prompt_tokens=None if d.get("prompt_tokens") is None else int(d["prompt_tokens"]),
    )


@dataclass(frozen=True)
class HopRecord:
  """One multi-hop expansion step. Latency None = explicitly not measured."""

  hop: int
  seed: str
  candidates_in: int
  candidates_out: int
  latency_ms: float | None = None

  def to_dict(self) -> dict:
    return asdict(self)

  @staticmethod
  def from_dict(d: dict) -> "HopRecord":
    for f in ("hop", "seed", "candidates_in", "candidates_out"):
      if f not in d:
        raise ValueError(f"HopRecord missing required field: {f}")
    return HopRecord(
      hop=int(d["hop"]),
      seed=d["seed"],
      candidates_in=int(d["candidates_in"]),
      candidates_out=int(d["candidates_out"]),
      latency_ms=None if d.get("latency_ms") is None else float(d["latency_ms"]),
    )


@dataclass(frozen=True)
class StageRecord:
  stage: str
  candidates_in: int
  candidates_out: int
  threshold: float | None
  latency_ms: float
  required_survived: bool | None = None  # None when ground truth unavailable
  score_kind: str = "calibrated_probability"
  model_loading_latency_ms: float | None = None  # None = explicitly not measured
  inference_latency_ms: float | None = None  # None = explicitly not measured
  peak_rss_mb: float | None = None  # calling-process peak; None = not measured
  adaptive_compute_decision: str | None = None

  def to_dict(self) -> dict:
    return asdict(self)

  @staticmethod
  def from_dict(d: dict) -> "StageRecord":
    for f in ("stage", "candidates_in", "candidates_out", "latency_ms"):
      if f not in d:
        raise ValueError(f"StageRecord missing required field: {f}")
    return StageRecord(
      stage=d["stage"],
      candidates_in=int(d["candidates_in"]),
      candidates_out=int(d["candidates_out"]),
      threshold=None if d.get("threshold") is None else float(d["threshold"]),
      latency_ms=float(d["latency_ms"]),
      required_survived=d.get("required_survived"),
      score_kind=d.get("score_kind", "calibrated_probability"),
      model_loading_latency_ms=None
      if d.get("model_loading_latency_ms") is None
      else float(d["model_loading_latency_ms"]),
      inference_latency_ms=None
      if d.get("inference_latency_ms") is None
      else float(d["inference_latency_ms"]),
      peak_rss_mb=None if d.get("peak_rss_mb") is None else float(d["peak_rss_mb"]),
      adaptive_compute_decision=d.get("adaptive_compute_decision"),
    )


@dataclass(frozen=True)
class RetrievalOutcome:
  question_id: str
  packet: EvidencePacket
  stages: tuple[StageRecord, ...]
  total_latency_ms: float
  peak_rss_mb: float | None = None  # calling-process peak; None = not measured
  model_loading_latency_ms: float | None = None
  inference_latency_ms: float | None = None
  storage_bytes: int | None = None  # None = explicitly not measured
  hops: tuple[HopRecord, ...] = ()
  adaptive_compute_decision: str | None = None

  def to_dict(self) -> dict:
    return {
      "question_id": self.question_id,
      "packet": self.packet.to_dict(),
      "stages": [s.to_dict() for s in self.stages],
      "total_latency_ms": self.total_latency_ms,
      "peak_rss_mb": self.peak_rss_mb,
      "model_loading_latency_ms": self.model_loading_latency_ms,
      "inference_latency_ms": self.inference_latency_ms,
      "storage_bytes": self.storage_bytes,
      "hops": [h.to_dict() for h in self.hops],
      "adaptive_compute_decision": self.adaptive_compute_decision,
    }

  @staticmethod
  def from_dict(d: dict) -> "RetrievalOutcome":
    for f in ("question_id", "packet", "total_latency_ms"):
      if f not in d:
        raise ValueError(f"RetrievalOutcome missing required field: {f}")
    return RetrievalOutcome(
      question_id=d["question_id"],
      packet=EvidencePacket.from_dict(d["packet"]),
      stages=tuple(StageRecord.from_dict(s) for s in d.get("stages", [])),
      total_latency_ms=float(d["total_latency_ms"]),
      peak_rss_mb=None if d.get("peak_rss_mb") is None else float(d["peak_rss_mb"]),
      model_loading_latency_ms=None
      if d.get("model_loading_latency_ms") is None
      else float(d["model_loading_latency_ms"]),
      inference_latency_ms=None
      if d.get("inference_latency_ms") is None
      else float(d["inference_latency_ms"]),
      storage_bytes=None if d.get("storage_bytes") is None else int(d["storage_bytes"]),
      hops=tuple(HopRecord.from_dict(h) for h in d.get("hops", [])),
      adaptive_compute_decision=d.get("adaptive_compute_decision"),
    )


@dataclass(frozen=True)
class GeneratedAnswer:
  question_id: str
  answer_text: str
  citations: tuple[str, ...]  # EMITTED citations (claimed by the generator)
  generator_id: str
  prompt_hash: str
  evidence_token_estimate: int
  exact_evidence_tokens: int | None = None
  prompt_tokens: int | None = None  # whole model input incl. template/system
  completion_tokens: int | None = None

  def to_dict(self) -> dict:
    d = asdict(self)
    d["citations"] = list(self.citations)
    return d

  @staticmethod
  def from_dict(d: dict) -> "GeneratedAnswer":
    for f in ("question_id", "answer_text", "generator_id", "prompt_hash"):
      if f not in d:
        raise ValueError(f"GeneratedAnswer missing required field: {f}")
    return GeneratedAnswer(
      question_id=d["question_id"],
      answer_text=d["answer_text"],
      citations=tuple(d.get("citations", [])),
      generator_id=d["generator_id"],
      prompt_hash=d["prompt_hash"],
      evidence_token_estimate=int(d.get("evidence_token_estimate", 0)),
      exact_evidence_tokens=None
      if d.get("exact_evidence_tokens") is None
      else int(d["exact_evidence_tokens"]),
      prompt_tokens=None if d.get("prompt_tokens") is None else int(d["prompt_tokens"]),
      completion_tokens=None
      if d.get("completion_tokens") is None
      else int(d["completion_tokens"]),
    )
