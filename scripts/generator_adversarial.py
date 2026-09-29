#!/usr/bin/env python3
"""Adversarial checks for the fixed-generator contract (SYNTHETIC ONLY).

No benchmark, public-bounty, or held-out queries. Every check is expected to
either PASS (attack correctly rejected/flagged) or FAIL (hole found).
Exits nonzero if any check fails.

Checks:
  drift-value   caller override of a pinned value (temperature) is rejected
  drift-key     unknown settings key is rejected
  drift-config  tampered config copy (prompt_hash) is rejected at init
  exact-guard   shared builder refuses exact=True without tokenizer
  exact-id-guard shared builder refuses tokenizer without id label
  citations     parser flags unknown ids; availability kept separately
  parse-conform adapter extraction matches substrate.parse_citations exactly
  runtime-bin   tampered binary hash in config copy fails prepare()
  runtime-exe   nonexistent server binary fails fast; early-exit server
                (/bin/false) yields a diagnosed, reaped ServerStartupError
  overbudget    exact model-token evidence over cap is refused pre-generation
  cap-enforce   max_tokens=4 via the chat API truncates with finish 'length'
  cleanup       resident session shutdown reaps the process and frees the port

Usage: python3 scripts/generator_adversarial.py [--root .]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generator_runtime.qwen25_adapter import (  # noqa: E402
  ConfigDriftError, EvidenceOverBudgetError, LlamaCppGenerator,
  RuntimeMismatchError, ServerStartupError, _ServerProc, _free_port,
  _port_closed, parse_citations)
from substrate.evidence import build_packet, parse_citations as shared_parse  # noqa: E402
from substrate.types import EvidencePacket, EvidenceSpan, Question  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
  RESULTS.append((name, ok, detail))
  print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def make_temp_root(real_root: str, tamper: dict | None = None) -> str:
  """Temp root with (possibly tampered) config; heavy model via symlink."""
  tmp = tempfile.mkdtemp(prefix="gen-adv-")
  os.makedirs(os.path.join(tmp, "corpus"))
  os.makedirs(os.path.join(tmp, "generator_runtime"))
  with open(os.path.join(real_root, "corpus", "generator_config.json"),
            encoding="utf-8") as fh:
    cfg = json.load(fh)
  if tamper:
    cfg.update(tamper)
  with open(os.path.join(tmp, "corpus", "generator_config.json"), "w",
            encoding="utf-8") as fh:
    json.dump(cfg, fh, indent=2, sort_keys=True)
    fh.write("\n")
  os.symlink(os.path.join(real_root, "generator_runtime", "artifacts"),
             os.path.join(tmp, "generator_runtime", "artifacts"))
  return tmp


Q = Question(question_id="synth-adv-001", text="Synthetic adversarial probe.",
             split="dev", meta={"fixture": "synthetic-infra-only"})


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    description="Adversarial checks for the fixed-generator contract "
                "(SYNTHETIC ONLY).")
  parser.add_argument("--root", default=".",
                      help="repository root (default: .)")
  root = parser.parse_args(argv).root

  # 1. Config drift: differing value rejected.
  try:
    LlamaCppGenerator(root, settings={"temperature": 0.7})
    check("drift-value", False, "override accepted")
  except ConfigDriftError:
    check("drift-value", True, "differing temperature rejected")

  # 2. Unknown key rejected.
  try:
    LlamaCppGenerator(root, settings={"nonsense_param": 1})
    check("drift-key", False, "unknown key accepted")
  except ConfigDriftError:
    check("drift-key", True, "unknown key rejected")

  # 3. Identical values are accepted (no false positive).
  try:
    LlamaCppGenerator(root, settings={"temperature": 0.0, "seed": 1234})
    check("drift-identical", True, "identical values accepted")
  except ConfigDriftError as exc:
    check("drift-identical", False, f"identical values rejected: {exc}")

  # 4. Tampered config copy rejected at init.
  tmp = make_temp_root(root, {"prompt_hash": "0" * 64})
  try:
    LlamaCppGenerator(tmp)
    check("drift-config", False, "tampered prompt_hash accepted")
  except ConfigDriftError:
    check("drift-config", True, "tampered prompt_hash rejected")
  finally:
    shutil.rmtree(tmp, ignore_errors=True)

  # 5b. Shared exact-path guards: exact without tokenizer, and tokenizer
  # without its id label, are both refused by the shared builder.
  try:
    build_packet("synth-adv-x", [], exact=True)
    check("exact-guard", False, "exact=True without tokenizer accepted")
  except ValueError:
    check("exact-guard", True, "exact=True without tokenizer refused")
  try:
    build_packet("synth-adv-x", [], tokenizer=lambda t: 0)
    check("exact-id-guard", False, "tokenizer without id accepted")
  except ValueError:
    check("exact-id-guard", True, "tokenizer without id refused")
  # 5. Citation parser: unknown ids flagged, availability preserved.
  audit = parse_citations(
    "Answer in [synth-para-001] and [ghost-node-999]; also [synth-para-001].",
    ("synth-para-001", "synth-para-002"))
  check("citations",
        audit["cited_valid"] == ["synth-para-001"]
        and audit["cited_unknown"] == ["ghost-node-999"]
        and audit["available_not_cited"] == ["synth-para-002"],
        f"audit={audit}")
  # 5c. Adapter extraction conforms exactly to the shared substrate parser.
  tricky = "Cite [a-1], [ spaced ] , [] and [a-1] plus [multi word id]."
  check("parse-conform",
        sorted(audit.keys()) == ["available_not_cited", "cited_unknown",
                                 "cited_valid"]
        and (parse_citations(tricky, ("a-1", "spaced"))["cited_valid"]
             == shared_parse(tricky)[:2])
        and shared_parse(tricky) == ["a-1", "spaced", "multi word id"],
        f"shared={shared_parse(tricky)}")

  # 6. Tampered binary hash fails prepare() (fast, before the 1GB check).
  tmp = make_temp_root(root)
  try:
    with open(os.path.join(tmp, "corpus", "generator_config.json"),
              encoding="utf-8") as fh:
      cfg = json.load(fh)
    cfg["runtime_binaries"]["llama-server"]["sha256"] = "0" * 64
    with open(os.path.join(tmp, "corpus", "generator_config.json"), "w",
              encoding="utf-8") as fh:
      json.dump(cfg, fh, indent=2, sort_keys=True)
      fh.write("\n")
    try:
      LlamaCppGenerator(tmp).prepare()
      check("runtime-bin", False, "tampered binary hash accepted")
    except RuntimeMismatchError:
      check("runtime-bin", True, "tampered binary hash rejected")
  finally:
    shutil.rmtree(tmp, ignore_errors=True)

  # 7. Nonexistent server binary fails fast.
  try:
    LlamaCppGenerator(root, server_bin="/nonexistent/llama-server")
    check("runtime-exe", False, "missing binary accepted")
  except RuntimeError as exc:
    check("runtime-exe", "missing" in str(exc), f"fast failure: {exc}")

  # 8. Early-exit server yields diagnosed, reaped error (direct _ServerProc
  # fault injection: prepare() would already reject a wrong binary, so the
  # spawn path itself is tested here).
  import os as _os
  srv = _ServerProc(["/bin/false", "--port", str(_free_port())],
                    dict(_os.environ))
  try:
    srv.start(timeout_s=15.0)
    check("early-exit", False, "false-binary server started")
  except ServerStartupError as exc:
    msg = str(exc)
    reaped = srv.proc is not None and srv.proc.poll() is not None
    check("early-exit", "code 1" in msg and reaped,
          f"diagnosed+reaped: {msg[:120]}")

  # Real-server checks (prepare once, resident session).
  gen = LlamaCppGenerator(root)
  gen.prepare()
  session = gen.start_session()
  try:
    # 9. Overbudget exact-token evidence refused BEFORE generation.
    big = EvidencePacket(
      question_id=Q.question_id,
      spans=(EvidenceSpan(node_id="synth-big-001",
                          text=" ".join(["word"] * 5000)),),
      citations=("synth-big-001",),
      token_estimate=5000,
      hop_count=0,
      truncated=False)
    try:
      gen.generate(Q, big, session)
      check("overbudget", False, "over-cap evidence generated")
    except EvidenceOverBudgetError as exc:
      check("overbudget", True, f"refused pre-generation: {exc}")

    # 10. max_tokens cap enforced by the chat API.
    req = urllib.request.Request(
      session.base + "/v1/chat/completions",
      data=json.dumps({
        "messages": [{"role": "user",
                      "content": "Count: 1 2 3 4 5 6 7 8 9 10"}],
        "temperature": 0.0, "seed": 7, "max_tokens": 4,
        "cache_prompt": True}).encode(),
      headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
      out = json.load(resp)
    usage = out.get("usage") or {}
    check("cap-enforce",
          out["choices"][0]["finish_reason"] == "length"
          and usage.get("completion_tokens") == 4,
          f"finish={out['choices'][0]['finish_reason']} "
          f"completion={usage.get('completion_tokens')}")
  finally:
    pid = session._server.proc.pid if session._server.proc else None
    port = session._server.port
    report = session.close()

  # 11. Cleanup: reaped + port freed + process gone.
  gone = True
  if pid is not None:
    try:
      os.kill(pid, 0)
      gone = False
    except (ProcessLookupError, PermissionError):
      gone = True
  check("cleanup",
        report.get("reaped") is True and report.get("port_closed") is True
        and _port_closed(port) and gone,
        f"close_report={report} gone={gone}")

  failed = [name for name, ok, _ in RESULTS if not ok]
  print(f"ADVERSARIAL: {'PASS' if not failed else 'FAIL'} "
        f"({len(RESULTS) - len(failed)}/{len(RESULTS)})")
  return 0 if not failed else 1


if __name__ == "__main__":
  raise SystemExit(main())
