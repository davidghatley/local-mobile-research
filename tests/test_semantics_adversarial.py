"""Adversarial semantic tests. All fixtures SYNTHETIC, tmp-only.

Covers: score-domain validation, exact-tokenizer budgets, canonical
serialization, seal opacity (hash without parse), question-file validation,
raw-logit ranking legality with explicit kind, threshold policy semantics.
"""

import json
import os
import tempfile
import unittest

from eval.run_format import validate_trace, migrate_legacy_trace
from substrate.generator import PROMPT_HASH
from substrate.evidence import (
  build_packet,
  find_unknown_citations,
  serialize_evidence,
)
from substrate.splits import (
  HeldoutCustodian,
  sha256_bytes_of_file,
  validate_questions_file,
  verify_seal_opaque,
)
from substrate.types import EvidenceSpan, ThresholdPolicy, validate_score_value
from tests.test_contract import good_trace


def spans():
  # SYNTHETIC-ONLY spans.
  return [
    EvidenceSpan(node_id="p1", text="alpha beta"),
    EvidenceSpan(node_id="p2", text="gamma delta epsilon"),
  ]


class TestScoreDomains(unittest.TestCase):
  def test_calibrated_accepts_edges(self):
    validate_score_value(0.0, "calibrated_probability")
    validate_score_value(1.0, "calibrated_probability")

  def test_calibrated_rejects_logit_range(self):
    with self.assertRaises(ValueError):
      validate_score_value(5.0, "calibrated_probability")
    with self.assertRaises(ValueError):
      validate_score_value(-0.1, "calibrated_probability")

  def test_raw_logit_ranking_legal_when_explicit(self):
    validate_score_value(5.0, "logit")
    validate_score_value(-2.0, "logit")

  def test_nonfinite_always_rejected(self):
    for kind in ("calibrated_probability", "logit", "similarity"):
      with self.assertRaises(ValueError):
        validate_score_value(float("nan"), kind)

  def test_unknown_kind_rejected(self):
    with self.assertRaises(ValueError):
      validate_score_value(0.5, "vibes")

  def test_trace_with_logit_kind_accepts_raw_scores(self):
    trace = dict(good_trace(), stages=[{
      "stage": "stage0",
      "candidate_ids": ["p1", "p2"],
      "scores": [5.0, -2.0],
      "score_kind": "logit",
      "threshold_policy": {
        "threshold": 2.5,
        "interpretation": "raw_score_absolute",
        "calibration_method": "none_ranking_only",
        "score_kind": "logit",
        "top_k": None,
        "min_breadth": 0,
        "calibration_partition": ""
      },
      "pruning_decisions": [True, False],
      "latency_ms": 1.0,
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "model_identity": "synth-model-v1"
    }])
    self.assertEqual(validate_trace(trace), [])

  def test_trace_rejects_policy_kind_mismatch(self):
    trace = dict(good_trace(), stages=[{
      "stage": "stage0",
      "candidate_ids": ["p1"],
      "scores": [0.9],
      "score_kind": "logit",
      "threshold_policy": {
        "threshold": 0.5,
        "interpretation": "calibrated_probability",
        "calibration_method": "model_probability",
        "score_kind": "calibrated_probability",
        "top_k": 50,
        "min_breadth": 10,
        "calibration_partition": ""
      },
      "pruning_decisions": [True],
      "latency_ms": 1.0,
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "model_identity": "synth-model-v1"
    }])
    self.assertTrue(any("score_kind" in e for e in validate_trace(trace)))

  def test_trace_rejects_logits_mislabeled_calibrated(self):
    trace = dict(good_trace(), stages=[{
      "stage": "stage0",
      "candidate_ids": ["p1"],
      "scores": [5.0],
      "score_kind": "calibrated_probability",
      "threshold_policy": {
        "threshold": 0.5,
        "interpretation": "calibrated_probability",
        "calibration_method": "model_probability",
        "score_kind": "calibrated_probability",
        "top_k": 50,
        "min_breadth": 10,
        "calibration_partition": ""
      },
      "pruning_decisions": [True],
      "latency_ms": 1.0,
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "model_identity": "synth-model-v1"
    }])
    self.assertTrue(any("must be in [0, 1]" in e for e in validate_trace(trace)))

  def test_trace_rejects_negative_latency(self):
    trace = dict(good_trace(), retrieval_latency_ms=-1.0)
    self.assertTrue(any("retrieval_latency_ms" in e for e in validate_trace(trace)))

  def test_trace_rejects_unknown_citations(self):
    # v0.3 finding A: unknown emitted citations are permitted observations.
    trace = dict(good_trace(), citations=["p1", "ghost-node"])
    self.assertEqual(validate_trace(trace), [])

  def test_trace_rejects_inconsistent_audit(self):
    trace = dict(good_trace(), citations=["p1", "ghost-node"],
                 citation_audit={"available": ["p1", "p2"], "emitted": ["p1", "ghost-node"],
                                 "unknown": []})
    errors = validate_trace(trace)
    self.assertTrue(any("misclassifies unknowns" in e for e in errors))

  def test_trace_accepts_consistent_audit_with_unknowns(self):
    trace = dict(good_trace(), citations=["p1", "ghost-node"],
                 citation_audit={"available": ["p1", "p2"], "emitted": ["p1", "ghost-node"],
                                 "unknown": ["ghost-node"]})
    self.assertEqual(validate_trace(trace), [])

  def test_trace_rejects_malformed_audit(self):
    trace = dict(good_trace(), citation_audit={"available": ["p1"]})
    self.assertTrue(any("citation_audit" in e for e in validate_trace(trace)))


class TestThresholdPolicy(unittest.TestCase):
  def test_raw_score_policy_needs_no_calibration(self):
    policy = ThresholdPolicy(
      threshold=2.5,
      interpretation="raw_score_absolute",
      top_k=20,
      min_breadth=5,
      calibration_method="none_ranking_only",
      score_kind="logit",
    )
    self.assertEqual(policy.validate(), [])

  def test_probability_policy_accepts_model_probability(self):
    policy = ThresholdPolicy(
      threshold=0.5,
      interpretation="calibrated_probability",
      calibration_method="model_probability",
      score_kind="calibrated_probability",
    )
    self.assertEqual(policy.validate(), [])

  def test_probability_policy_rejects_ranking_only(self):
    policy = ThresholdPolicy(
      threshold=0.5,
      interpretation="calibrated_probability",
      calibration_method="none_ranking_only",
      score_kind="calibrated_probability",
    )
    self.assertTrue(policy.validate())

  def test_fitted_claim_requires_provenance(self):
    policy = ThresholdPolicy(
      threshold=0.5,
      interpretation="calibrated_probability",
      calibration_method="platt",
      score_kind="calibrated_probability",
    )
    self.assertTrue(any("provenance" in e for e in policy.validate()))
    proven = ThresholdPolicy(
      threshold=0.5,
      interpretation="calibrated_probability",
      calibration_method="platt",
      score_kind="calibrated_probability",
      calibration_partition="sha256:synth-cal-part",
    )
    self.assertEqual(proven.validate(), [])

  def test_legacy_float_migrates_fail_closed(self):
    policy = ThresholdPolicy.from_dict(0.7)
    self.assertEqual(policy.interpretation, "unspecified")
    self.assertTrue(policy.validate())


class TestExactTokens(unittest.TestCase):
  def test_exact_requires_tokenizer(self):
    with self.assertRaises(ValueError):
      build_packet("q", spans(), exact=True)

  def test_tokenizer_without_id_rejected(self):
    with self.assertRaises(ValueError):
      build_packet("q", spans(), tokenizer=lambda t: len(t))

  def test_exact_budget_enforced_on_model_tokens(self):
    calls = []

    def tok(text):
      calls.append(text)
      return len(text.split()) * 200  # SYNTHETIC model-token scale

    packet = build_packet("q", spans(), cap=1000, tokenizer=tok,
                          tokenizer_id="synth-tok", exact=True)
    # "[p1] alpha beta" -> 3*200=600 kept; both lines -> 7*200=1400 overflows.
    self.assertTrue(packet.truncated)
    self.assertEqual(packet.token_count_method, "tokenizer:synth-tok")
    self.assertEqual(packet.exact_evidence_tokens, 600)
    self.assertTrue(calls)

  def test_estimate_path_marked_infra_only(self):
    packet = build_packet("q", spans())
    self.assertEqual(packet.token_count_method, "whitespace-estimate")
    self.assertIsNone(packet.exact_evidence_tokens)

  def test_serialization_canonical(self):
    self.assertEqual(serialize_evidence(spans()), "[p1] alpha beta\n[p2] gamma delta epsilon")

  def test_find_unknown_citations(self):
    self.assertEqual(find_unknown_citations(["p1", "gx"], ["p1"]), ["gx"])


class TestSealOpacity(unittest.TestCase):
  def test_verify_seal_without_parsing(self):
    with tempfile.TemporaryDirectory() as tmp:
      sealed = os.path.join(tmp, "sealed.json")
      with open(sealed, "wb") as fh:
        fh.write(b'{"secret": ["node-9"]}')
      expected = sha256_bytes_of_file(sealed)
      self.assertTrue(verify_seal_opaque(sealed, expected))
      self.assertFalse(verify_seal_opaque(sealed, "0" * 64))

  def test_verify_seal_missing_fails_closed(self):
    with self.assertRaises(FileNotFoundError):
      verify_seal_opaque("/nonexistent-synth-seal", "0" * 64)

  def test_custodian_seal_hash_never_prints_labels(self):
    with tempfile.TemporaryDirectory() as tmp:
      sealed = os.path.join(tmp, "sealed.json")
      with open(sealed, "wb") as fh:
        fh.write(b'{"secret": ["node-9"]}')
      cust = HeldoutCustodian(labels_path=sealed,
                              audit_path=os.path.join(tmp, "audit.jsonl"))
      self.assertEqual(cust.seal_hash(), sha256_bytes_of_file(sealed))


class TestQuestionsValidation(unittest.TestCase):
  def test_valid_file(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "q.json")
      with open(path, "w", encoding="utf-8") as fh:
        json.dump([{"question_id": "a", "text": "t?", "split": "dev"}], fh)
      out = validate_questions_file(path)
      self.assertEqual(out, {"ids": ["a"], "errors": []})

  def test_duplicates_and_bad_splits_reported(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "q.json")
      with open(path, "w", encoding="utf-8") as fh:
        json.dump([
          {"question_id": "a", "text": "t?"},
          {"question_id": "a", "text": "t2?"},
          {"question_id": "b", "text": "", "split": "nope"},
        ], fh)
      out = validate_questions_file(path)
      self.assertTrue(any("duplicate" in e for e in out["errors"]))
      self.assertTrue(any("split" in e for e in out["errors"]))


class TestLegacyMigration(unittest.TestCase):
  """Tests for explicit legacy trace migration."""

  def test_legacy_flat_trace_rejected_by_validate_trace(self):
    """Legacy flat traces must be rejected by validate_trace with explicit error."""
    legacy = {
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
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "storage_bytes": 100,
      "generator_prompt_hash": PROMPT_HASH,
      "generator_id": "synth-generator-v1",
      "generator_response": "x",
      "citations": ["p1"],
      "available_citations": ["p1", "p2"],
      "grader_result": None,
    }
    errors = validate_trace(legacy)
    self.assertTrue(any("legacy flat trace fields detected" in e for e in errors))

  def test_migrate_legacy_trace_succeeds_with_model_identities(self):
    """Explicit migration with all model identities produces valid new-format trace."""
    legacy = {
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
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "storage_bytes": 100,
      "generator_prompt_hash": PROMPT_HASH,
      "generator_id": "synth-generator-v1",
      "generator_response": "x",
      "citations": ["p1"],
      "available_citations": ["p1", "p2"],
      "grader_result": None,
    }
    migrated = migrate_legacy_trace(legacy, model_identity_map={"stage0": "synth-model-v1"})
    self.assertIn("stages", migrated)
    self.assertEqual(len(migrated["stages"]), 1)
    self.assertEqual(migrated["stages"][0]["stage"], "stage0")
    self.assertEqual(migrated["stages"][0]["model_identity"], "synth-model-v1")
    self.assertEqual(validate_trace(migrated), [])

  def test_migrate_legacy_trace_fails_closed_without_model_identity(self):
    """Missing model_identity in migration map fails closed (no placeholder)."""
    legacy = {
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
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "storage_bytes": 100,
      "generator_prompt_hash": PROMPT_HASH,
      "generator_id": "synth-generator-v1",
      "generator_response": "x",
      "citations": ["p1"],
      "available_citations": ["p1", "p2"],
      "grader_result": None,
    }
    with self.assertRaises(ValueError) as cm:
      migrate_legacy_trace(legacy, model_identity_map={})  # missing stage0
    self.assertIn("no model_identity provided", str(cm.exception))


if __name__ == "__main__":
  unittest.main()