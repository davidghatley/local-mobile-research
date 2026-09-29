"""Conceptual retriever / generator interfaces every experiment must implement."""

from __future__ import annotations

from typing import Protocol

from .types import CorpusNode, EvidencePacket, GeneratedAnswer, Question, RetrievalOutcome


class Retriever(Protocol):
  """Common retrieval / evidence-mise-en-place interface (Round 0 contract)."""

  def prepare(self, corpus: list[CorpusNode]) -> None:
    """Index or pre-encode the pinned corpus snapshot. No question data."""
    ...

  def retrieve(self, question: Question) -> RetrievalOutcome:
    """Map one question to an evidence packet plus full stage trace."""
    ...


class Generator(Protocol):
  """Fixed-generator interface. ALL Round 1 architectures share one instance."""

  @property
  def generator_id(self) -> str:
    ...

  @property
  def prompt_hash(self) -> str:
    ...

  def generate(self, question: Question, packet: EvidencePacket) -> GeneratedAnswer:
    """Single generative pass over the evidence packet. No retrieval inside."""
    ...
