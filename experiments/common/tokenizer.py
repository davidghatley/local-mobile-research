"""Exact pinned-generator token counting.

The frozen evidence contract says the governing unit for an empirical run is the
EXACT model tokenizer, and that `substrate.evidence.build_packet(exact=True,
tokenizer=None)` must raise. So an empirical Round 1 run needs a callable that
counts tokens the way the fixed generator does.

The pinned tokenizer is the one EMBEDDED IN THE GGUF
(`corpus/generator_config.json`: `tokenizer =
"gguf-embedded:gpt2-bpe:vocab151936:bos151643:eos151645:addbos0:tplsha-cd8e9439"`).
It is not the `Qwen/Qwen2.5-1.5B-Instruct` HF tokenizer artifact, even though the
two share a BPE scheme: the contract pins the GGUF's, and a count from a
different artifact is a different measurement.

So this module counts tokens by asking the pinned runtime, over the same
``llama-server`` the generator uses, via its ``/tokenize`` endpoint.

Why a RESIDENT session rather than one server per question
----------------------------------------------------------
Measured on this host: ``llama-server`` load is 1,510 ms and a warm 35-token
generation is 3,911 ms. Paying 1,510 ms per question to count ~600 tokens of
evidence would dominate the retrieval latency it is supposed to measure, and it
would corrupt every latency number in the tournament. So the count is taken from
one long-lived server for the whole run, and the tokenizer's cost is accounted
separately and explicitly -- never folded into a system's retrieval latency.

The tokenizer is a pure function of the text and the pinned GGUF, so sharing one
server across questions does not change any count. It is a service, not state.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from generator_runtime.qwen25_adapter import (  # noqa: E402
  LlamaCppGenerator, ResidentSession, _free_port, _http)

_TOKENIZER_ID_FALLBACK = "UNPINNED"


class ExactTokenizer:
  """Callable ``str -> int`` counting exact pinned-generator tokens.

  Wraps a resident ``llama-server`` started with the SAME pinned model, context
  size and thread count as the generator, and counts over the same ``/tokenize``
  endpoint the generator adapter uses for its own token accounting. That is what
  makes ``build_packet``'s budget and the generator's own ``evidence_tokens``
  accounting the same number rather than two similar ones.
  """

  def __init__(self, repo_root: str, session: ResidentSession,
               tokenizer_id: str) -> None:
    self.repo_root = repo_root
    self._session = session
    self.tokenizer_id = tokenizer_id
    self.calls = 0
    self._cache: dict[str, int] = {}

  def __call__(self, text: str) -> int:
    return self.count(text)

  def count(self, text: str) -> int:
    hit = self._cache.get(text)
    if hit is not None:
      return hit
    n = len(_http(self._session.base, "/tokenize", {"content": text})["tokens"])
    self.calls += 1
    # Bounded cache: packets repeat prefixes heavily, and the whole point of an
    # exact count is that it is a pure function, so caching cannot change it.
    if len(self._cache) < 200_000:
      self._cache[text] = n
    return n

  def close(self) -> dict:
    return self._session.close()


class TokenizerService:
  """Owns the resident server and hands out :class:`ExactTokenizer`."""

  def __init__(self, repo_root: str, server_bin: str | None = None) -> None:
    self.repo_root = repo_root
    self.generator = LlamaCppGenerator(repo_root, server_bin=server_bin)
    self._tokenizer: ExactTokenizer | None = None
    self.load_ms: float | None = None

  def start(self) -> ExactTokenizer:
    if self._tokenizer is not None:
      return self._tokenizer
    # prepare() hash-checks the GGUF, the binary and every shared library against
    # the contract BEFORE anything is timed. It is a verification step, and it is
    # the reason an unpinned tokenizer cannot be silently substituted here.
    self.generator.prepare()
    session = self.generator.start_session()
    self.load_ms = session.load_ms
    tid = self.generator.tokenizer_id
    if tid in ("TBD", "", "unspecified"):
      raise ValueError("generator tokenizer identity is not pinned")
    self._tokenizer = ExactTokenizer(self.repo_root, session, tid)
    return self._tokenizer

  @property
  def tokenizer(self) -> ExactTokenizer:
    if self._tokenizer is None:
      return self.start()
    return self._tokenizer

  def as_callable(self) -> Callable[[str], int]:
    return self.tokenizer

  def close(self) -> dict:
    if self._tokenizer is None:
      return {"already_closed": True}
    rep = self._tokenizer.close()
    self._tokenizer = None
    return rep

  def __enter__(self) -> "TokenizerService":
    self.start()
    return self

  def __exit__(self, *exc: object) -> None:
    self.close()


def pinned_tokenizer_callable(repo_root: str, server_bin: str | None = None):
  """Context-managed accessor: ``with pinned_tokenizer_callable(root) as tok:``.

  Yields a ``str -> int`` callable plus its identity, so a caller cannot record
  a token count without also recording WHICH tokenizer produced it.
  """

  class _Ctx:
    def __enter__(self):
      self.service = TokenizerService(repo_root, server_bin=server_bin)
      self.tokenizer = self.service.start()
      return self.tokenizer

    def __exit__(self, *exc: object) -> None:
      self.service.close()

  return _Ctx()


def tokenizer_identity(tokenizer: ExactTokenizer) -> dict:
  """Provenance block for a run manifest. Never omit; an unlabelled token
  count is indistinguishable from a whitespace estimate."""
  return {
    "tokenizer_id": tokenizer.tokenizer_id,
    "count_method": "llama-server /tokenize on the pinned GGUF",
    "shared_with_generator": True,
    "note": (
      "exact model tokens; this is the governing unit for the evidence budget. "
      "A whitespace estimate may never be reported as a measurement."
    ),
  }
