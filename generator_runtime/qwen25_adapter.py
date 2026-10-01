"""Fixed-generator offline adapter: Qwen2.5-1.5B-Instruct Q4_K_M via llama.cpp.

Round 0 generator worker artifact (repair v3). Implements the substrate
``Generator`` protocol WITHOUT modifying shared substrate files (read-only
imports only). The single authoritative contract is
``corpus/generator_config.json``: constructor settings must match it exactly
(differing values are rejected, not merged), and ``prepare()`` hash-checks
the model, the server binary, and every llama-owned shared library before
any latency timing runs.

Runtime model: ``llama-server`` subprocess, CPU-only (``-ngl 0``), greedy
deterministic decoding, orchestrator-pinned threads=1 for controlled Round 1.
Token counts are EXACT model-tokenizer measurements via ``/tokenize`` --
never whitespace estimates. Three counts are recorded separately (see
``last_token_accounting``):
  evidence_tokens  - exact tokens of the canonical evidence serialization;
                     the ONLY count that may be reported as evidence size,
                     enforced against HARD_EVIDENCE_TOKEN_CAP for hand-built
                     packets (shared ``build_packet`` now guarantees the cap
                     by construction: strict ranked-prefix, first-span
                     overflow yields an EMPTY packet with truncated=True);
  user_prompt_tokens - exact tokens of the rendered (untemplated) prompt;
  templated_input_tokens - exact tokens of the /apply-template model input,
                     must equal the completion ``usage.prompt_tokens``.

An EMPTY packet (zero spans) is a valid abstention outcome and passes
through generation: the fixed prompt instructs the model to state
insufficiency explicitly.

Sufficiency-gating contract (no adapter logic implied): whether the
generator is invoked at all is decided EXCLUSIVELY by the shared
substrate gate ``substrate.evidence.run_question`` (safe floor:
``decide_default``; ``EvidenceDecision`` with fail-closed
insufficient-iff-abstain invariant). This adapter MUST NOT implement its
own empty-packet suppression, must not invent sufficiency, and must not
be called on abstained questions — the gate returns (outcome, decision,
None) without touching ``generate``. See
``docs/abstention-and-telemetry-notes.md`` for the trace fields.

Citations use the shared substrate parser (``evidence.parse_citations``)
plus ``find_unknown_citations``: ``GeneratedAnswer.citations`` carries only
valid cited ids actually present in the output (EMITTED semantics per the
shared contract; AVAILABLE ids live on the packet). Unknown ids are
recorded, never silently dropped. Existence is not faithfulness.

Prompt delivery (orchestrator-accepted): the single rendered substrate
prompt (v0.2, PROMPT_HASH d8580509...) sent as one user message through the
model's pinned Jinja ChatML template.

Worker model: opencode/muse-spark-1.3-contributor-free (verified zero-cost).
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.evidence import (  # noqa: E402
  HARD_EVIDENCE_TOKEN_CAP, estimate_tokens, find_unknown_citations,
  parse_citations as substrate_parse_citations, serialize_evidence)
from substrate.generator import PROMPT_HASH, render_prompt  # noqa: E402
from substrate.types import EvidencePacket, GeneratedAnswer, Question  # noqa: E402

GENERATOR_ID = "qwen25-1.5b-q4km-fixed-v1"
CONFIG_REL_PATH = os.path.join("corpus", "generator_config.json")

# Cross-check constant (mirrors the PROMPT_HASH pattern): the GGUF-header
# ground truth for the embedded chat template. The config file is
# authoritative; a mismatch here means config drift, never a silent update.
PINNED_GGUF_TEMPLATE_SHA256 = (
  "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f")

def parse_citations(answer_text: str,
                    available: tuple[str, ...]) -> dict[str, list[str]]:
  """Split emitted citation candidates into valid-cited / unknown / not-cited.

  Bracket extraction delegates to the shared substrate parser
  (``evidence.parse_citations``); unknown-id detection uses the shared
  ``find_unknown_citations``. No adapter-local parsing remains.
  """
  seen = substrate_parse_citations(answer_text)
  available_list = list(available)
  cited_unknown = find_unknown_citations(seen, available_list)
  unknown_set = set(cited_unknown)
  cited_valid = [t for t in seen if t not in unknown_set]
  available_not_cited = [a for a in available_list if a not in cited_valid]
  return {
    "cited_valid": cited_valid,
    "cited_unknown": cited_unknown,
    "available_not_cited": available_not_cited,
  }


class ConfigDriftError(ValueError):
  """A caller-supplied value differs from the authoritative config contract."""


class RuntimeMismatchError(RuntimeError):
  """A runtime artifact hash does not match the pinned contract."""


class EvidenceOverBudgetError(ValueError):
  """Exact model-token evidence size exceeds HARD_EVIDENCE_TOKEN_CAP."""


class ServerStartupError(RuntimeError):
  """The llama-server subprocess failed to become ready (with diagnostics)."""


def sha256_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def _free_port() -> int:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    return int(sock.getsockname()[1])


def _http(base: str, path: str, payload: dict, timeout_s: int = 600) -> dict:
  req = urllib.request.Request(
    base + path,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
  )
  with urllib.request.urlopen(req, timeout=timeout_s) as resp:
    return json.load(resp)


def _port_closed(port: int) -> bool:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(2.0)
    return sock.connect_ex(("127.0.0.1", port)) != 0


class _ServerProc:
  """llama-server subprocess with diagnosed startup and reaped shutdown."""

  def __init__(self, cmd: list[str], env: dict[str, str]) -> None:
    self.cmd = cmd
    self.env = env
    self.proc: subprocess.Popen[bytes] | None = None
    self.port = int(cmd[cmd.index("--port") + 1])
    self.base = f"http://127.0.0.1:{self.port}"
    self.stderr_tail = ""

  def start(self, timeout_s: float = 120.0) -> float:
    """Spawn, wait for /health, return load_ms. Raises ServerStartupError."""
    self.proc = subprocess.Popen(
      self.cmd, env=self.env,
      stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert self.proc.stderr is not None
    t0 = time.perf_counter()
    deadline = t0 + timeout_s
    last_err: str | None = None
    while time.perf_counter() < deadline:
      if self.proc.poll() is not None:
        err = self._drain_stderr()
        raise ServerStartupError(
          f"llama-server exited early with code {self.proc.returncode}: "
          f"{err[-2000:]}")
      try:
        with urllib.request.urlopen(self.base + "/health", timeout=5) as resp:
          if resp.status == 200:
            return (time.perf_counter() - t0) * 1000.0
      except OSError as exc:
        last_err = str(exc)
        time.sleep(0.5)
    self.stop()
    raise ServerStartupError(
      f"llama-server not ready after {timeout_s}s (last error: {last_err}); "
      f"stderr: {self.stderr_tail[-2000:]}")

  def _drain_stderr(self) -> str:
    if self.proc is None:
      return self.stderr_tail
    try:
      _, err = self.proc.communicate(timeout=10)
      self.stderr_tail = (err or b"").decode("utf-8", "replace")
    except (subprocess.TimeoutExpired, ValueError):
      pass
    return self.stderr_tail

  def stop(self, timeout_s: float = 15.0) -> dict[str, object]:
    """terminate -> wait -> kill -> wait; always reaps. Returns report."""
    report: dict[str, object] = {"reaped": False, "port_closed": False}
    proc, self.proc = self.proc, None
    if proc is None:
      report["port_closed"] = _port_closed(self.port)
      report["reaped"] = True
      return report
    proc.terminate()
    try:
      proc.wait(timeout=timeout_s)
      report["terminated_cleanly"] = True
    except subprocess.TimeoutExpired:
      proc.kill()
      report["terminated_cleanly"] = False
      try:
        proc.wait(timeout=timeout_s)
      except subprocess.TimeoutExpired:
        report["reap_error"] = "process survived SIGKILL wait"
        return report
    self.proc = proc  # temporarily restore for drain, then clear
    self._drain_stderr()
    self.proc = None
    report["returncode"] = proc.returncode
    report["reaped"] = proc.poll() is not None
    report["port_closed"] = _port_closed(self.port)
    return report


class ResidentSession:
  """Controlled resident server: load timed once, warm calls after."""

  def __init__(self, server: _ServerProc, load_ms: float) -> None:
    self._server = server
    self.load_ms = load_ms
    self.closed = False

  @property
  def base(self) -> str:
    return self._server.base

  def close(self) -> dict[str, object]:
    if self.closed:
      return {"already_closed": True}
    self.closed = True
    return self._server.stop()

  def __enter__(self) -> "ResidentSession":
    return self

  def __exit__(self, *exc: object) -> None:
    self.close()


class LlamaCppGenerator:
  """Fixed Qwen2.5-1.5B Q4_K_M generator behind the substrate protocol."""

  generator_id = GENERATOR_ID
  prompt_hash = PROMPT_HASH

  def __init__(self, root: str, settings: dict | None = None,
               server_bin: str | None = None) -> None:
    self.root = root
    with open(os.path.join(root, CONFIG_REL_PATH), encoding="utf-8") as fh:
      self.config: dict = json.load(fh)
    if self.config.get("prompt_hash") != PROMPT_HASH:
      raise ConfigDriftError(
        "config prompt_hash does not match substrate PROMPT_HASH")
    gguf_meta = self.config.get("tokenizer_gguf") or {}
    if gguf_meta.get("chat_template_sha256") != PINNED_GGUF_TEMPLATE_SHA256:
      raise ConfigDriftError(
        "config tokenizer_gguf.chat_template_sha256 does not match the "
        "GGUF-header measurement")
    self.tokenizer_id: str = self.config.get("tokenizer", "TBD")
    if self.tokenizer_id in ("TBD", "", "unspecified"):
      raise ConfigDriftError("config tokenizer identity is not pinned")
    pinned = dict(self.config["generation"])
    pinned.update({k: self.config[k] for k in
                   ("context_window_pinned", "runtime_threads_measured")
                   if k in self.config})
    # Authoritative settings snapshot (config keys used by the adapter).
    self.settings: dict = {
      "n_ctx": self.config["context_window_pinned"],
      "n_gpu_layers": 0,
      "threads": self.config["runtime_threads_measured"],
      "temperature": self.config["generation"]["temperature"],
      "top_k": self.config["generation"]["top_k"],
      "top_p": self.config["generation"]["top_p"],
      "seed": self.config["generation"]["seed"],
      "max_tokens": self.config["generation"]["max_tokens"],
      "cache_prompt": self.config["generation"]["cache_prompt"],
    }
    if settings:
      unknown = set(settings) - set(self.settings)
      if unknown:
        raise ConfigDriftError(f"unknown settings keys refused: "
                               f"{sorted(unknown)}")
      differing = [k for k in settings if settings[k] != self.settings[k]]
      if differing:
        raise ConfigDriftError(
          f"settings differ from authoritative contract "
          f"(re-freeze required to change): {differing}")
    self.model_path = os.path.join(root, self.config["artifact_path"])
    default_bin = os.path.expanduser("~/.local/bin/llama-server")
    self.server_bin = server_bin or default_bin
    if not os.path.isfile(self.server_bin):
      raise RuntimeError(f"server binary missing: {self.server_bin}")
    self.last_timings: dict[str, float] = {}
    self.last_token_accounting: dict[str, int] = {}
    self.last_citation_audit: dict[str, list[str]] = {}
    self.last_finish_reason: str | None = None
    self.prepared = False

  # -- one-time verification (run BEFORE any latency timing) -------------

  def prepare(self) -> dict[str, object]:
    """Hash-check model + binary + libs against the contract. Once."""
    report: dict[str, object] = {}
    real_bin = os.path.realpath(self.server_bin)
    bin_digest = sha256_file(real_bin)
    if bin_digest != self.config["runtime_binaries"]["llama-server"]["sha256"]:
      raise RuntimeMismatchError("llama-server binary hash mismatch")
    report["binary"] = {"path": real_bin, "sha256": bin_digest}
    lib_dir = self.config["runtime_binaries"]["lib_dir"]
    bad: list[str] = []
    for name, meta in self.config["runtime_binaries"]["libs"].items():
      path = os.path.join(lib_dir, name)
      if not os.path.isfile(path):
        bad.append(f"{name}: missing")
        continue
      if sha256_file(os.path.realpath(path)) != meta["sha256"]:
        bad.append(f"{name}: hash mismatch")
    if bad:
      raise RuntimeMismatchError(f"shared-library mismatch: {bad}")
    report["libs_checked"] = len(self.config["runtime_binaries"]["libs"])
    size = os.path.getsize(self.model_path)
    if size != self.config["bytes"]:
      raise RuntimeMismatchError(
        f"model size {size} != contract {self.config['bytes']}")
    digest = sha256_file(self.model_path)
    if digest != self.config["sha256"]:
      raise RuntimeMismatchError("model sha256 mismatch with contract")
    report["model"] = {"bytes": size, "sha256": digest}
    self.prepared = True
    return report

  # -- session management --------------------------------------------------

  def _spawn(self) -> tuple[_ServerProc, float]:
    env = dict(os.environ)
    lib_dir = self.config["runtime_binaries"]["lib_dir"]
    env["LD_LIBRARY_PATH"] = lib_dir + ":" + env.get("LD_LIBRARY_PATH", "")
    server = _ServerProc([
      self.server_bin, "-m", self.model_path,
      "--port", str(_free_port()), "-c", str(self.settings["n_ctx"]),
      "-ngl", str(self.settings["n_gpu_layers"]),
      "-t", str(self.settings["threads"]),
      "--log-disable",
    ], env)
    return server, server.start()

  def start_session(self) -> ResidentSession:
    if not self.prepared:
      raise RuntimeError("prepare() must succeed before start_session()")
    server, load_ms = self._spawn()
    return ResidentSession(server, load_ms)

  # -- token accounting ----------------------------------------------------

  @staticmethod
  def _tokenize(base: str, text: str) -> int:
    return len(_http(base, "/tokenize", {"content": text})["tokens"])

  def _account(self, base: str, question: Question,
               packet: EvidencePacket) -> dict[str, object]:
    ev_text = serialize_evidence(packet.spans)
    rendered = render_prompt(question, packet)
    if ev_text not in rendered:
      raise RuntimeError("evidence serialization diverged from render_prompt")
    ev_tokens = self._tokenize(base, ev_text)
    if ev_tokens > HARD_EVIDENCE_TOKEN_CAP:
      raise EvidenceOverBudgetError(
        f"exact evidence tokens {ev_tokens} exceed cap "
        f"{HARD_EVIDENCE_TOKEN_CAP}")
    prompt_tokens = self._tokenize(base, rendered)
    messages = [{"role": "user", "content": rendered}]
    templated = _http(base, "/apply-template", {"messages": messages})["prompt"]
    templated_tokens = self._tokenize(base, templated)
    return {
      "evidence_text": ev_text,
      "messages": messages,
      "evidence_tokens": ev_tokens,
      "user_prompt_tokens": prompt_tokens,
      "templated_input_tokens": templated_tokens,
    }

  # -- generation -----------------------------------------------------------

  def generate(self, question: Question, packet: EvidencePacket,
               session: ResidentSession | None = None) -> GeneratedAnswer:
    assert PROMPT_HASH == self.prompt_hash  # pinned substrate prompt in use
    owned = session is None
    if owned:
      if not self.prepared:
        raise RuntimeError("prepare() must succeed before generate()")
      server, load_ms = self._spawn()
      session = ResidentSession(server, load_ms)
    assert session is not None
    try:
      acct = self._account(session.base, question, packet)
      s = self.settings
      t1 = time.perf_counter()
      out = _http(session.base, "/v1/chat/completions", {
        "messages": acct["messages"],
        "temperature": s["temperature"], "top_k": s["top_k"],
        "top_p": s["top_p"], "seed": s["seed"],
        "max_tokens": s["max_tokens"], "cache_prompt": s["cache_prompt"],
      })
      gen_ms = (time.perf_counter() - t1) * 1000.0
      usage = out.get("usage") or {}
      if usage.get("prompt_tokens") != acct["templated_input_tokens"]:
        raise RuntimeError(
          f"usage.prompt_tokens {usage.get('prompt_tokens')} != measured "
          f"templated input {acct['templated_input_tokens']}")
      if usage.get("completion_tokens", 0) > s["max_tokens"]:
        raise RuntimeError("server exceeded max_tokens cap")
      text = out["choices"][0]["message"]["content"]
      self.last_finish_reason = out["choices"][0].get("finish_reason")
      audit = parse_citations(text, tuple(packet.citations))
      timings = out.get("timings") or {}
      self.last_timings = {
        "server_load_ms": session.load_ms,
        "http_generate_ms": gen_ms,
        "prompt_ms": float(timings.get("prompt_ms", -1.0)),
        "predicted_ms": float(timings.get("predicted_ms", -1.0)),
        "prompt_n": float(timings.get("prompt_n", -1.0)),
        "predicted_n": float(timings.get("predicted_n", -1.0)),
      }
      self.last_token_accounting = {
        "evidence_tokens": int(acct["evidence_tokens"]),
        "user_prompt_tokens": int(acct["user_prompt_tokens"]),
        "templated_input_tokens": int(acct["templated_input_tokens"]),
        "usage_prompt_tokens": int(usage.get("prompt_tokens", -1)),
        "usage_completion_tokens": int(usage.get("completion_tokens", -1)),
      }
      self.last_citation_audit = audit
      # NOTE (shared-schema need): GeneratedAnswer has one citations field.
      # Availability (packet.citations) is preserved in last_citation_audit
      # and traces, not in this object. A separate available_citations
      # field requires substrate review.
      cited = [c for c in packet.citations if c in audit["cited_valid"]]
      completion_tokens = int(usage.get("completion_tokens", -1))
      return GeneratedAnswer(
        question_id=question.question_id,
        answer_text=text,
        citations=tuple(cited),
        generator_id=self.generator_id,
        prompt_hash=self.prompt_hash,
        evidence_token_estimate=estimate_tokens(str(acct["evidence_text"])),
        exact_evidence_tokens=int(acct["evidence_tokens"]),
        prompt_tokens=int(acct["templated_input_tokens"]),
        completion_tokens=completion_tokens,
      )
    finally:
      if owned:
        session.close()
