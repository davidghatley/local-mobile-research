"""Fixed-generator contract: prompt pinning, full config schema, infra-only stub.

``GeneratorConfig`` is the full frozen generator contract: model identity,
artifact bytes/hash, quantization, runtime, tokenizer identity, sampling
params, and prompt hash. ``is_pinned()`` is fail-closed: any TBD/unspecified
field means NOT pinned.

``DeterministicStubGenerator`` exists ONLY for pipeline/telemetry tests and
is rejected by benchmark trace validation and freeze validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import serialize_evidence
from .types import (
  STUB_GENERATOR_IDS,
  EvidencePacket,
  GeneratedAnswer,
  Question,
  is_stub_generator,
  sha256_text,
)

# Fixed generation prompt (Round 0 v0.2). Any change requires re-freeze.
# v0.2: citation instruction rewritten after the v0.1 "[node_id] form" wording
# caused a literal "[node_id]" citation in synthetic smoke output. Single
# common prompt for all architectures; not benchmark-tuned.
FIXED_GENERATION_PROMPT = (
  "You are an offline research assistant. Answer the question using ONLY the "
  "provided evidence. Cite the exact bracketed identifier printed before the "
  "supporting evidence. For example, evidence labeled [source-7] must be "
  "cited as [source-7]. Do not write placeholder identifiers. "
  "If the evidence is insufficient, say so explicitly and "
  "list what is missing.\n\n"
  "EVIDENCE:\n{evidence}\n\nQUESTION:\n{question}\n\nANSWER:"
)

PROMPT_HASH = sha256_text(FIXED_GENERATION_PROMPT)

# Placeholder sentinels: any of these in a pinned field means UNPINNED.
PLACEHOLDER_VALUES = frozenset({"TBD", "unspecified", "", "SYNTHETIC"})


def _pinned_str(value: object) -> bool:
  return isinstance(value, str) and value not in PLACEHOLDER_VALUES


def render_prompt(question: Question, packet: EvidencePacket) -> str:
  return FIXED_GENERATION_PROMPT.format(
    evidence=serialize_evidence(list(packet.spans)), question=question.text
  )


@dataclass(frozen=True)
class GeneratorConfig:
  """Full frozen generator contract. Placeholders mean NOT pinned."""

  model_id: str
  revision: str
  prompt_hash: str
  quantization: str = "unspecified"
  runtime: str = "unspecified"
  file: str = "TBD"
  artifact_sha256: str = "TBD"
  artifact_bytes: int | None = None
  tokenizer_id: str = "TBD"
  chat_template_sha256: str = "TBD"
  sampling: dict[str, object] = field(default_factory=dict)
  context_window: int | None = None
  generator_id: str = "TBD"

  def is_pinned(self) -> bool:
    return (
      _pinned_str(self.model_id)
      and _pinned_str(self.revision)
      and _pinned_str(self.prompt_hash)
      and _pinned_str(self.quantization)
      and _pinned_str(self.runtime)
      and _pinned_str(self.file)
      and _pinned_str(self.artifact_sha256)
      and self.artifact_bytes is not None
      and self.artifact_bytes > 0
      and _pinned_str(self.tokenizer_id)
      and _pinned_str(self.chat_template_sha256)
      and bool(self.sampling)
    )

  def unpinned_fields(self) -> list[str]:
    missing = []
    for name in (
      "model_id",
      "revision",
      "prompt_hash",
      "quantization",
      "runtime",
      "file",
      "artifact_sha256",
      "tokenizer_id",
      "chat_template_sha256",
    ):
      if not _pinned_str(getattr(self, name)):
        missing.append(name)
    if not (self.artifact_bytes is not None and self.artifact_bytes > 0):
      missing.append("artifact_bytes")
    if not self.sampling:
      missing.append("sampling")
    return missing

  def to_dict(self) -> dict:
    return {
      "model_id": self.model_id,
      "revision": self.revision,
      "prompt_hash": self.prompt_hash,
      "quantization": self.quantization,
      "runtime": self.runtime,
      "file": self.file,
      "artifact_sha256": self.artifact_sha256,
      "artifact_bytes": self.artifact_bytes,
      "tokenizer_id": self.tokenizer_id,
      "chat_template_sha256": self.chat_template_sha256,
      "sampling": dict(self.sampling),
      "context_window": self.context_window,
      "generator_id": self.generator_id,
    }

  @staticmethod
  def from_dict(d: dict) -> "GeneratorConfig":
    # Tolerates the on-disk superset written by the generator owner, which
    # uses "sha256"/"bytes"/"generation" key names.
    sampling = d.get("sampling", d.get("generation", {}))
    artifact_bytes = d.get("artifact_bytes", d.get("bytes"))
    return GeneratorConfig(
      model_id=d.get("model_id", "TBD"),
      revision=d.get("revision", "TBD"),
      prompt_hash=d.get("prompt_hash", PROMPT_HASH),
      quantization=d.get("quantization", "unspecified"),
      runtime=d.get("runtime", "unspecified"),
      file=d.get("file", "TBD"),
      artifact_sha256=d.get("artifact_sha256", d.get("sha256", "TBD")),
      artifact_bytes=None if artifact_bytes is None else int(artifact_bytes),
      tokenizer_id=d.get("tokenizer_id", d.get("tokenizer", "TBD")),
      chat_template_sha256=d.get("chat_template_sha256", "TBD"),
      sampling=dict(sampling) if isinstance(sampling, dict) else {},
      context_window=None
      if d.get("context_window") is None
      else int(d["context_window"]),
      generator_id=d.get("generator_id", "TBD"),
    )


UNPINNED_GENERATOR_CONFIG = GeneratorConfig(
  model_id="TBD", revision="TBD", prompt_hash=PROMPT_HASH
)


class DeterministicStubGenerator:
  """INFRASTRUCTURE-ONLY stub. Deterministic extractive output for tests.

  NOT a research generator. Freeze and benchmark trace validation reject
  ``generator_id`` in ``STUB_GENERATOR_IDS``.
  """

  generator_id = "stub-infra-only-v0"
  prompt_hash = PROMPT_HASH

  def generate(self, question: Question, packet: EvidencePacket) -> GeneratedAnswer:
    top = packet.spans[0].text if packet.spans else "insufficient evidence"
    text = f"[infra-stub] question={question.question_id} evidence={top[:160]}"
    return GeneratedAnswer(
      question_id=question.question_id,
      answer_text=text,
      citations=tuple(packet.citations),
      generator_id=self.generator_id,
      prompt_hash=self.prompt_hash,
      evidence_token_estimate=packet.token_estimate,
      exact_evidence_tokens=packet.exact_evidence_tokens,
    )
