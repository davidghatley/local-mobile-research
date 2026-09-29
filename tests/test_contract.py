"""Telemetry, manifest/freeze, contract-format tests. All fixtures SYNTHETIC."""

import json
import os
import tempfile
import unittest

from eval.run_format import validate_trace, write_traces_jsonl
from substrate.evidence import build_packet
from substrate.generator import (
  PROMPT_HASH,
  DeterministicStubGenerator,
  GeneratorConfig,
)
from substrate.manifest import RunManifest, derive_seed, validate_freeze
from substrate.telemetry import measure_storage, timed_phase, timed_stage
from substrate.types import EvidenceSpan, Question, ThresholdPolicy


def pinned_generator(**overrides):
  base = {
    "model_id": "org/model",
    "revision": "abc123",
    "prompt_hash": PROMPT_HASH,
    "quantization": "Q4_K_M",
    "runtime": "llama.cpp cpu",
    "file": "model.gguf",
    "artifact_sha256": "0" * 64,
    "artifact_bytes": 8,
    "tokenizer_id": "tok-v1",
    "chat_template_sha256": "c" * 64,
    "sampling": {"temperature": 0.0},
  }
  base.update(overrides)
  return GeneratorConfig.from_dict(base)


def pinned_manifest(**overrides):
  params = {
    "run_id": "r1",
    "seed": 0,
    "corpus_hash": "deadbeef",
    "code_hashes": {"a.py": "h"},
    "generator": pinned_generator(),
    "thresholds": {
      "stage0": ThresholdPolicy(
        threshold=0.5,
        interpretation="calibrated_probability",
        top_k=50,
        min_breadth=10,
        calibration_method="model_probability",
        score_kind="calibrated_probability",
      )
    },
  }
  params.update(overrides)
  return RunManifest(**params)


def good_trace():
  return {
    "question_id": "q1",
    "run_id": "r1",
    "architecture": "synthetic-infra",
    "seed": 0,
    "query": "synthetic?",
    "score_kind": "calibrated_probability",
    "stage_candidates": {"stage0": ["p1"]},
    "stage_scores": {"stage0": [0.9]},
    "pruning_decisions": {"stage0": [True]},
    "thresholds": {"stage0": {"threshold": 0.5, "interpretation": "calibrated_probability",
                               "calibration_method": "model_probability",
                               "score_kind": "calibrated_probability"}},
    "adaptive_compute_decision": "keep-top-50",
    "evidence_packet": {"spans": []},
    "evidence_token_count": 10,
    "evidence_token_method": "tokenizer:synth-tok",
    "retrieval_latency_ms": 1.0,
    "per_stage_latency_ms": {"stage0": 1.0},
    "model_loading_latency_ms": None,  # explicitly not measured
    "inference_latency_ms": 0.5,
    "peak_rss_mb": 12.0,
    "storage_bytes": 100,
    "generator_prompt_hash": PROMPT_HASH,
    "generator_id": "synth-generator-v1",
    "generator_response": "x",
    "citations": ["p1"],
    "available_citations": ["p1", "p2"],
    "grader_result": None,  # explicitly not graded yet
  }


class TestTelemetry(unittest.TestCase):
  def test_timed_stage_records_elapsed(self):
    with timed_stage() as holder:
      pass
    self.assertGreaterEqual(holder["elapsed_ms"], 0.0)

  def test_timed_phase_labels(self):
    with timed_phase("model_load") as holder:
      pass
    self.assertEqual(holder["phase"], "model_load")
    self.assertGreaterEqual(holder["elapsed_ms"], 0.0)

  def test_measure_storage_missing_path_is_zero(self):
    report = measure_storage(["/nonexistent-path-xyz"])
    self.assertEqual(report.total_bytes, 0)


class TestManifestFreeze(unittest.TestCase):
  def test_freeze_fails_without_artifacts(self):
    with tempfile.TemporaryDirectory() as tmp:
      check = validate_freeze(tmp, pinned_manifest())
      self.assertFalse(check.passed)
      self.assertTrue(any("missing required artifact" in g for g in check.gaps))

  def test_freeze_fails_when_unpinned(self):
    gen = GeneratorConfig.from_dict({"model_id": "TBD", "revision": "TBD"})
    self.assertFalse(gen.is_pinned())
    self.assertIn("quantization", gen.unpinned_fields())

  def test_freeze_fails_on_fake_code_hash(self):
    with tempfile.TemporaryDirectory() as tmp:
      check = validate_freeze(tmp, pinned_manifest(code_hashes={"a.py": "fakehash"}))
      self.assertFalse(check.passed)
      self.assertTrue(
        any("missing required artifact" in g for g in check.gaps)
        or any("code hash path missing" in g for g in check.gaps)
      )

  def test_freeze_fails_on_stub_generator(self):
    gen = pinned_generator(generator_id="stub-infra-only-v0")
    check = validate_freeze(tempfile.gettempdir(), pinned_manifest(generator=gen))
    self.assertFalse(check.passed)
    self.assertTrue(any("stub" in g for g in check.gaps))

  def test_threshold_policy_rejects_bare_sigmoid_claim(self):
    policy = ThresholdPolicy(
      threshold=0.5,
      interpretation="calibrated_probability",
      calibration_method="none_ranking_only",
    )
    self.assertTrue(policy.validate())

  def test_seed_derivation_deterministic(self):
    self.assertEqual(derive_seed(7, "split"), derive_seed(7, "split"))
    self.assertNotEqual(derive_seed(7, "split"), derive_seed(7, "model"))


class TestContractFormat(unittest.TestCase):
  def test_stub_generator_marks_infra_only(self):
    q = Question(question_id="q1", text="synthetic?")
    packet = build_packet("q1", [EvidenceSpan(node_id="p1", text="hello world")])
    ans = DeterministicStubGenerator().generate(q, packet)
    self.assertEqual(ans.generator_id, "stub-infra-only-v0")
    self.assertEqual(ans.prompt_hash, PROMPT_HASH)

  def test_trace_validation_catches_missing_fields(self):
    bad = {"question_id": "q1"}
    self.assertTrue(validate_trace(bad))
    self.assertEqual(validate_trace(good_trace()), [])

  def test_trace_rejects_stub_by_default(self):
    trace = dict(good_trace(), generator_id="stub-infra-only-v0")
    self.assertTrue(any("stub" in e for e in validate_trace(trace)))
    self.assertEqual(validate_trace(trace, allow_stub=True), [])

  def test_trace_rejects_estimate_by_default(self):
    trace = dict(good_trace(), evidence_token_method="whitespace-estimate")
    self.assertTrue(any("estimate" in e for e in validate_trace(trace)))
    self.assertEqual(validate_trace(trace, allow_estimate=True), [])

  def test_write_rejects_invalid_trace(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "t.jsonl")
      with self.assertRaises(ValueError):
        write_traces_jsonl(path, [{"question_id": "q1"}])
      write_traces_jsonl(path, [good_trace()])
      with open(path, encoding="utf-8") as fh:
        self.assertEqual(len(json.loads(fh.read().strip())), 26)


if __name__ == "__main__":
  unittest.main()
