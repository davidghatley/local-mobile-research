#!/usr/bin/env python3
"""Deterministic synthetic smoke test (INFRA ONLY, repair v3).

SYNTHETIC fixtures only. Never benchmark, public-bounty, or held-out
queries. Output is an infrastructure check, never an empirical result.

v3: orchestrator-pinned threads=1; substrate prompt v0.2 (no [node_id]
literal); exact packets via the shared strict builder; citation
extraction via the shared substrate parser; an empty-packet leg verifies
the abstention outcome (zero spans, no crash, empty emitted citations).

Writes generator_runtime/smoke_trace_v3_<ts>.json. All older traces kept.
Usage: python3 scripts/generator_smoke.py [--root .]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generator_runtime.qwen25_adapter import (  # noqa: E402
  GENERATOR_ID, LlamaCppGenerator)
from substrate.evidence import (  # noqa: E402
  HARD_EVIDENCE_TOKEN_CAP, build_packet, estimate_tokens, parse_citations,
  serialize_evidence)
from substrate.generator import PROMPT_HASH, GeneratorConfig, render_prompt  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402
from substrate.types import EvidenceSpan, Question  # noqa: E402

FIXTURE_SPANS = [
  EvidenceSpan(node_id="synth-para-001",
               text="Synthetic fixture paragraph one about test widget "
                    "calibration procedures."),
  EvidenceSpan(node_id="synth-para-002",
               text="Synthetic fixture paragraph two says the tolerance "
                    "threshold is 5 units."),
]
FIXTURE_QUESTION = Question(
  question_id="synth-infra-001",
  text="What is the synthetic widget tolerance threshold?",
  split="dev",
  meta={"fixture": "synthetic-infra-only"},
)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    description="Synthetic INFRA-ONLY fixed-generator smoke test.")
  parser.add_argument("--root", default=".",
                      help="repository root (default: .)")
  root = parser.parse_args(argv).root
  gen = LlamaCppGenerator(root)
  t0 = time.perf_counter()
  prep = gen.prepare()
  verify_ms = (time.perf_counter() - t0) * 1000.0

  # Packet is built empirically inside the session (exact tokenizer);
  # no whitespace-estimate packet is used on this path.
  session = gen.start_session()
  try:
    load_ms = session.load_ms
    # Empirical path: exact-token packet via the shared builder + live
    # pinned tokenizer; replaces the whitespace packet above.
    def live_tokenize(text: str) -> int:
      req = urllib.request.Request(
        session.base + "/tokenize", data=json.dumps(
          {"content": text}).encode(),
        headers={"Content-Type": "application/json"})
      with urllib.request.urlopen(req, timeout=300) as resp:
        return len(json.load(resp)["tokens"])

    exact_packet = build_packet(
      FIXTURE_QUESTION.question_id, list(FIXTURE_SPANS), exact=True,
      tokenizer=live_tokenize, tokenizer_id=gen.tokenizer_id)
    packet = exact_packet
    answer1 = gen.generate(FIXTURE_QUESTION, packet, session)
    acct1 = dict(gen.last_token_accounting)
    audit1 = {k: list(v) for k, v in gen.last_citation_audit.items()}
    timings1 = dict(gen.last_timings)
    finish1 = gen.last_finish_reason
    answer2 = gen.generate(FIXTURE_QUESTION, packet, session)
    timings2 = dict(gen.last_timings)
    # Abstention leg: an oversize first span packs to an EMPTY truncated
    # packet under the strict shared builder; generation must proceed
    # without crash and emit no credited citations.
    empty_packet = build_packet(
      "synth-infra-empty", [EvidenceSpan(
        node_id="synth-huge-001", text=" ".join(["word"] * 5000))],
      exact=True, tokenizer=live_tokenize, tokenizer_id=gen.tokenizer_id)
    abstention = gen.generate(
      Question(question_id="synth-infra-empty",
               text="What is the synthetic widget tolerance threshold?",
               split="dev", meta={"fixture": "synthetic-infra-only"}),
      empty_packet, session)
    abstention_audit = {k: list(v)
                        for k, v in gen.last_citation_audit.items()}
    proc = session._server.proc
    server_pid = proc.pid if proc is not None else None
  finally:
    close_report = session.close()

  with open(os.path.join(root, "corpus", "generator_config.json"),
            encoding="utf-8") as fh:
    cfg = GeneratorConfig.from_dict(json.load(fh))

  # Evidence serialization must byte-match the evidence lines in render_prompt.
  ev_text = serialize_evidence(packet.spans)
  rendered = render_prompt(FIXTURE_QUESTION, packet)

  gone = True
  if server_pid is not None:
    try:
      os.kill(server_pid, 0)
      gone = False
    except (ProcessLookupError, PermissionError):
      gone = True

  # Citation extraction cross-check against the shared substrate parser.
  emitted = parse_citations(answer1.answer_text)
  parser_complete = (sorted(audit1["cited_valid"] + audit1["cited_unknown"])
                     == sorted(set(emitted)))
  mapping_correct = (list(answer1.citations)
                     == [c for c in packet.citations
                         if c in audit1["cited_valid"]])

  trace = {
    "label": "SYNTHETIC-INFRA-ONLY v3: not a benchmark or architecture result",
    "question_id": FIXTURE_QUESTION.question_id,
    "generator_id": answer1.generator_id,
    "generator_id_pinned": answer1.generator_id == GENERATOR_ID,
    "prompt_hash": answer1.prompt_hash,
    "prompt_hash_matches_substrate": answer1.prompt_hash == PROMPT_HASH,
    "config_pinned_compat": cfg.is_pinned(),
    "prepare_report": prep,
    "prepare_verify_ms": verify_ms,
    "session_load_ms_fresh_process": load_ms,
    "load_note": ("fresh process; OS page cache state not controlled, "
                  "so this is NOT a true cold-cache measurement"),
    "evidence_text_matches_render_prompt": ev_text in rendered,
    "packet_token_count_method": packet.token_count_method,
    "packet_method_is_exact_tokenizer": (
      packet.token_count_method == f"tokenizer:{gen.tokenizer_id}"),
    "packet_exact_matches_adapter": (
      packet.exact_evidence_tokens == acct1["evidence_tokens"]),
    "answer_exact_matches_packet": (
      answer1.exact_evidence_tokens == packet.exact_evidence_tokens),
    "answer_estimate_is_whitespace": (
      answer1.evidence_token_estimate == estimate_tokens(ev_text)),
    "answer_prompt_tokens_match_usage": (
      answer1.prompt_tokens == acct1["usage_prompt_tokens"]),
    "answer_completion_tokens_match_usage": (
      answer1.completion_tokens == acct1["usage_completion_tokens"]),
    "evidence_cap": HARD_EVIDENCE_TOKEN_CAP,
    "token_accounting_run1": acct1,
    "evidence_within_cap": acct1["evidence_tokens"] <= HARD_EVIDENCE_TOKEN_CAP,
    "usage_matches_templated": (acct1["usage_prompt_tokens"]
                                == acct1["templated_input_tokens"]),
    "completion_within_max_tokens": (
      acct1["usage_completion_tokens"] <= gen.settings["max_tokens"]),
    "finish_reason_run1": finish1,
    "answer_text": answer1.answer_text,
    "answer_citations_parsed_only": list(answer1.citations),
    "citation_audit": audit1,
    "parser_complete_all_emitted_ids_classified": parser_complete,
    "answer_citations_mapping_correct": mapping_correct,
    "citations_subset_of_packet": all(
      c in packet.citations for c in answer1.citations),
    "no_unknown_cited_ids_OBSERVATION_ONLY": (
      audit1["cited_unknown"] == []),
    "abstention_packet_empty_truncated": (
      len(empty_packet.spans) == 0 and empty_packet.truncated is True
      and empty_packet.exact_evidence_tokens is not None),
    "abstention_answer_text": abstention.answer_text,
    "abstention_citations_empty": list(abstention.citations) == [],
    "abstention_audit": abstention_audit,
    "deterministic_repeat_identical": answer1.answer_text == answer2.answer_text,
    "run1_timings_ms": timings1,
    "run2_warm_timings_ms": timings2,
    "session_close_report": close_report,
    "server_process_gone": gone,
    "client_peak_rss_mb": peak_rss_mb(),
  }
  out_path = os.path.join(
    root, "generator_runtime",
    f"smoke_trace_v3_{time.strftime('%Y%m%dT%H%M%S')}.json")
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(trace, fh, indent=2, sort_keys=True)
    fh.write("\n")
  print(json.dumps(trace, indent=2, sort_keys=True))
  print("trace:", out_path)
  checks = [
    trace["generator_id_pinned"],
    trace["prompt_hash_matches_substrate"],
    trace["config_pinned_compat"],
    trace["evidence_text_matches_render_prompt"],
    trace["packet_method_is_exact_tokenizer"],
    trace["packet_exact_matches_adapter"],
    trace["answer_exact_matches_packet"],
    trace["answer_estimate_is_whitespace"],
    trace["answer_prompt_tokens_match_usage"],
    trace["answer_completion_tokens_match_usage"],
    trace["evidence_within_cap"],
    trace["usage_matches_templated"],
    trace["completion_within_max_tokens"],
    trace["parser_complete_all_emitted_ids_classified"],
    trace["answer_citations_mapping_correct"],
    trace["citations_subset_of_packet"],
    trace["abstention_packet_empty_truncated"],
    trace["abstention_citations_empty"],
    trace["deterministic_repeat_identical"],
    close_report.get("reaped") is True,
    close_report.get("port_closed") is True,
    gone,
  ]
  print("SMOKE v3: " + ("PASS" if all(checks) else "FAIL"))
  return 0 if all(checks) else 1


if __name__ == "__main__":
  raise SystemExit(main())
