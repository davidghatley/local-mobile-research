#!/usr/bin/env python3
"""Fresh-process repeat protocol (INFRA ONLY, predeclared).

Reproducibility probe, NOT a universality guarantee: N independent fresh
``llama-server`` processes answer one fixed synthetic prompt
(orchestrator-pinned threads=1, seed 1234, temp 0.0 / top_k 1). Records per
process: answer-text sha256, token accounting (evidence / user-prompt /
templated / usage), citation audit, and load vs inference timings with the
page-cache caveat stated (process-cold only; no cache-cold claim).

SYNTHETIC fixture only. Never benchmark, public-bounty, or held-out
queries. Writes generator_runtime/repeat_trace_<ts>.json.
Usage: python3 scripts/generator_repeat.py [--root .] [--runs 3]
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
from substrate.evidence import build_packet  # noqa: E402
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
  question_id="synth-infra-repeat",
  text="What is the synthetic widget tolerance threshold?",
  split="dev",
  meta={"fixture": "synthetic-infra-only"},
)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    description="Fresh-process repeat protocol (SYNTHETIC ONLY).")
  parser.add_argument("--root", default=".",
                      help="repository root (default: .)")
  parser.add_argument("--runs", type=int, default=3,
                      help="independent fresh processes (default: 3)")
  args = parser.parse_args(argv)
  if args.runs < 2:
    parser.error("--runs must be >= 2 to probe repeatability")

  gen = LlamaCppGenerator(args.root)
  prep = gen.prepare()
  runs: list[dict] = []
  for i in range(args.runs):
    session = gen.start_session()
    try:
      def live_tokenize(text: str, base: str = session.base) -> int:
        req = urllib.request.Request(
          base + "/tokenize", data=json.dumps(
            {"content": text}).encode(),
          headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
          return len(json.load(resp)["tokens"])

      packet = build_packet(
        FIXTURE_QUESTION.question_id, list(FIXTURE_SPANS), exact=True,
        tokenizer=live_tokenize, tokenizer_id=gen.tokenizer_id)
      answer = gen.generate(FIXTURE_QUESTION, packet, session)
      runs.append({
        "run": i,
        "load_ms": session.load_ms,
        "answer_sha256": hashlib.sha256(
          answer.answer_text.encode("utf-8")).hexdigest(),
        "answer_text": answer.answer_text,
        "citation_audit": {k: list(v)
                           for k, v in gen.last_citation_audit.items()},
        "citations": list(answer.citations),
        "token_accounting": dict(gen.last_token_accounting),
        "finish_reason": gen.last_finish_reason,
        "threads": gen.settings["threads"],
      })
    finally:
      close_report = session.close()
      runs[-1]["close_report"] = close_report

  texts = {r["answer_sha256"] for r in runs}
  loads = [r["load_ms"] for r in runs]
  trace = {
    "label": "SYNTHETIC-INFRA-ONLY repeat protocol: reproducibility probe, "
             "not a universality guarantee",
    "protocol": f"{args.runs} independent fresh processes, fixed synthetic "
                "prompt, threads=1, seed 1234, temp 0.0/top_k 1",
    "page_cache_note": "process-cold only (fresh PID per run); OS page cache "
                       "state uncontrolled — no cache-cold claim",
    "runs": runs,
    "distinct_answer_texts": len(texts),
    "all_identical": len(texts) == 1,
    "load_ms_per_process": loads,
    "prepare_report": prep,
  }
  out_path = os.path.join(
    args.root, "generator_runtime",
    f"repeat_trace_{time.strftime('%Y%m%dT%H%M%S')}.json")
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(trace, fh, indent=2, sort_keys=True)
    fh.write("\n")
  for r in runs:
    print(f"run {r['run']}: load_ms={r['load_ms']:.1f} "
          f"sha={r['answer_sha256'][:16]} finish={r['finish_reason']} "
          f"cited={r['citations']} unknown={r['citation_audit']['cited_unknown']}")
  print(f"distinct texts: {len(texts)}/{args.runs}")
  print("trace:", out_path)
  print("REPEAT: " + ("PASS (all identical)" if len(texts) == 1
                       else "OBSERVED VARIANCE (see trace)"))
  return 0 if len(texts) == 1 else 2


if __name__ == "__main__":
  raise SystemExit(main())
