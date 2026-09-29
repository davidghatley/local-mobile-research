#!/usr/bin/env python3
"""Empty-evidence diagnostic probe (INFRA ONLY, predeclared paired design).

Question: is the empty-packet "0.5" answer model behavior or session-state
contamination? The adapter and fixed generator/model/prompt/settings are
NOT modified by this probe.

Paired design (all SYNTHETIC, fixed question, threads=1, seed 1234):
  Leg A (fresh):  N independent fresh processes answer the empty-packet
                  question (zero spans). Baseline behavior.
  Leg B (resident-after-evidence): fresh process answers the
                  evidence-bearing query FIRST, then the identical
                  empty-packet question in the SAME resident session.
  Leg C (resident-empty-first): fresh process answers the empty-packet
                  question first, then the evidence query (order control).

Per request verified and recorded: rendered messages contain the EMPTY
serialized evidence block (sha-logged), exactly one user message (no
conversation history), pinned cache_prompt=false from the live settings,
and usage/template token equality. Recorded per run: full inputs/outputs,
answer sha256, seed, server PID/port/session load, exact config snapshot.

Attribution rule (predeclared): A-identical + B==A  => contamination
unlikely, intrinsic model behavior. B systematically != A => possible
session-state contamination (investigate slot/KV reuse despite
cache_prompt=false). Variance everywhere => nondeterminism, no attribution.

Writes generator_runtime/empty_probe_<ts>.json.
Usage: python3 scripts/generator_empty_probe.py [--root .] [--fresh 3]
       [--resident 2]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generator_runtime.qwen25_adapter import LlamaCppGenerator  # noqa: E402
from substrate.evidence import build_packet, serialize_evidence  # noqa: E402
from substrate.generator import render_prompt  # noqa: E402
from substrate.types import EvidenceSpan, Question  # noqa: E402

EVIDENCE_SPANS = [
  EvidenceSpan(node_id="synth-para-001",
               text="Synthetic fixture paragraph one about test widget "
                    "calibration procedures."),
  EvidenceSpan(node_id="synth-para-002",
               text="Synthetic fixture paragraph two says the tolerance "
                    "threshold is 5 units."),
]
Q = Question(question_id="synth-empty-probe",
             text="What is the synthetic widget tolerance threshold?",
             split="dev", meta={"fixture": "synthetic-infra-only"})


def sha(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def live_tokenizer_factory(base: str):
  def tok(text: str) -> int:
    req = urllib.request.Request(
      base + "/tokenize", data=json.dumps(
        {"content": text}).encode(),
      headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
      return len(json.load(resp)["tokens"])
  return tok


def empty_packet(gen, session):
  return build_packet(Q.question_id, [], exact=True,
                      tokenizer=live_tokenizer_factory(session.base),
                      tokenizer_id=gen.tokenizer_id)


def evidence_packet(gen, session):
  return build_packet(Q.question_id, list(EVIDENCE_SPANS), exact=True,
                      tokenizer=live_tokenizer_factory(session.base),
                      tokenizer_id=gen.tokenizer_id)


def request_record(gen, question, packet):
  """Verify (not assume) the exact request the adapter will send."""
  rendered = render_prompt(question, packet)
  ev_text = serialize_evidence(packet.spans)
  messages = [{"role": "user", "content": rendered}]
  return {
    "rendered_sha256": sha(rendered),
    "rendered": rendered,
    "evidence_block_empty": ev_text == "",
    "single_user_message_only": (
      len(messages) == 1 and messages[0]["role"] == "user"),
    "cache_prompt_pinned_false": gen.settings["cache_prompt"] is False,
    "seed": gen.settings["seed"],
    "threads": gen.settings["threads"],
  }


def generate_record(gen, session, question, packet, kind: str) -> dict:
  req = request_record(gen, question, packet)
  answer = gen.generate(question, packet, session)
  return {
    "kind": kind,
    "request": req,
    "answer_text": answer.answer_text,
    "answer_sha256": sha(answer.answer_text),
    "citations": list(answer.citations),
    "citation_audit": {k: list(v)
                       for k, v in gen.last_citation_audit.items()},
    "token_accounting": dict(gen.last_token_accounting),
    "finish_reason": gen.last_finish_reason,
  }


def fresh_session_info(session) -> dict:
  proc = session._server.proc
  return {
    "server_pid": proc.pid if proc is not None else None,
    "port": session._server.port,
    "load_ms": session.load_ms,
  }


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    description="Empty-evidence diagnostic probe (SYNTHETIC ONLY).")
  parser.add_argument("--root", default=".",
                      help="repository root (default: .)")
  parser.add_argument("--fresh", type=int, default=3,
                      help="Leg A fresh processes (default: 3)")
  parser.add_argument("--resident", type=int, default=2,
                      help="Leg B/C resident sessions each (default: 2)")
  args = parser.parse_args(argv)
  if args.fresh < 1 or args.resident < 1:
    parser.error("counts must be >= 1")

  gen = LlamaCppGenerator(args.root)
  prep = gen.prepare()
  with open(os.path.join(args.root, "corpus", "generator_config.json"),
            encoding="utf-8") as fh:
    config_text = fh.read()
  config_snapshot = {
    "sha256": hashlib.sha256(config_text.encode("utf-8")).hexdigest(),
    "prompt_hash": gen.config["prompt_hash"],
    "model_sha256": gen.config["sha256"],
    "tokenizer": gen.tokenizer_id,
    "generation": dict(gen.config["generation"]),
    "threads": gen.settings["threads"],
    "n_ctx": gen.settings["n_ctx"],
  }

  legs: dict[str, list] = {"A_fresh_empty": [], "B_evidence_then_empty": [],
                           "C_empty_then_evidence": []}
  # Leg A: fresh process per empty question.
  for i in range(args.fresh):
    session = gen.start_session()
    try:
      info = fresh_session_info(session)
      rec = generate_record(gen, session, Q, empty_packet(gen, session),
                            f"A{i}")
      rec.update(info)
      legs["A_fresh_empty"].append(rec)
    finally:
      session.close()
  # Legs B/C: resident sessions with ordered pairs.
  for i in range(args.resident):
    session = gen.start_session()
    try:
      info = fresh_session_info(session)
      ev = generate_record(gen, session, Q, evidence_packet(gen, session),
                           f"B{i}-evidence")
      em = generate_record(gen, session, Q, empty_packet(gen, session),
                           f"B{i}-empty")
      ev.update(info)
      em.update({k: v for k, v in info.items()})
      legs["B_evidence_then_empty"].append({"first": ev, "second": em})
    finally:
      session.close()
  for i in range(args.resident):
    session = gen.start_session()
    try:
      info = fresh_session_info(session)
      em = generate_record(gen, session, Q, empty_packet(gen, session),
                           f"C{i}-empty")
      ev = generate_record(gen, session, Q, evidence_packet(gen, session),
                           f"C{i}-evidence")
      em.update(info)
      ev.update({k: v for k, v in info.items()})
      legs["C_empty_then_evidence"].append({"first": em, "second": ev})
    finally:
      session.close()

  a_texts = {r["answer_sha256"] for r in legs["A_fresh_empty"]}
  b_texts = {p["second"]["answer_sha256"]
             for p in legs["B_evidence_then_empty"]}
  c_texts = {p["first"]["answer_sha256"]
             for p in legs["C_empty_then_evidence"]}
  trace = {
    "label": "SYNTHETIC-INFRA-ONLY empty-evidence diagnostic: model behavior "
             "vs session-state contamination. Not an acceptance gate.",
    "attribution_rule": "A-identical + B==A => intrinsic; B systematically "
                        "!= A => possible contamination; variance "
                        "everywhere => no attribution",
    "adapter_unmodified": True,
    "no_tuning": True,
    "config_snapshot": config_snapshot,
    "prepare_report": prep,
    "legs": legs,
    "legA_distinct_texts": len(a_texts),
    "legB_empty_distinct_texts": len(b_texts),
    "legC_empty_distinct_texts": len(c_texts),
    "B_empty_matches_A_set": bool(b_texts) and b_texts <= a_texts,
    "C_empty_matches_A_set": bool(c_texts) and c_texts <= a_texts,
  }
  out_path = os.path.join(
    args.root, "generator_runtime",
    f"empty_probe_{time.strftime('%Y%m%dT%H%M%S')}.json")
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(trace, fh, indent=2, sort_keys=True)
    fh.write("\n")
  for r in legs["A_fresh_empty"]:
    print(f"A pid={r['server_pid']} load={r['load_ms']:.0f}ms "
          f"sha={r['answer_sha256'][:16]} cited={r['citations']} "
          f"unknown={r['citation_audit']['cited_unknown']}")
    print(f"   text: {r['answer_text']!r}")
  for p in legs["B_evidence_then_empty"]:
    s = p["second"]
    print(f"B(empty after evidence) pid={p['first']['server_pid']} "
          f"sha={s['answer_sha256'][:16]} cited={s['citations']}")
    print(f"   text: {s['answer_text']!r}")
  for p in legs["C_empty_then_evidence"]:
    f_ = p["first"]
    print(f"C(empty first) pid={f_['server_pid']} "
          f"sha={f_['answer_sha256'][:16]} cited={f_['citations']}")
    print(f"   text: {f_['answer_text']!r}")
  print("trace:", out_path)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
