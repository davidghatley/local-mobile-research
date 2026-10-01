"""v0.3 adversarial regression tests. All artifacts SYNTHETIC, tmp-only.

Covers reviewer-v02 bypass classes + orchestrator findings A/B: questions
content hashing, raw config bytes, semantic contract fields, runtime binary
inventory (synthetic tmp binaries only, never external paths), group-map
structure/disjointness/resolution, QA consistency, unified policy validation,
permitted unknown citations, binary completion, malformed-artifact gaps,
secrecy of error text, round0 unfitted-policy declarations.
"""

import hashlib
import json
import os
import tempfile
import unittest

from eval.run_format import validate_trace, migrate_legacy_trace
from substrate.generator import PROMPT_HASH, GeneratorConfig
from substrate.manifest import RunManifest, validate_freeze
from substrate.types import ThresholdPolicy
from tests.test_contract import good_trace, pinned_generator
from tests.test_freeze_adversarial import (
  REQUIRED_CORPUS_FILE,
  REQUIRED_GENERATOR_FILE,
  REQUIRED_LABELS_FILE,
  REQUIRED_QUESTIONS_FILE,
  FixtureRoot,
)


def aligned_root(tmp):
  """FixtureRoot with explicit QA provenance aligned to seeded-hash splits."""
  return FixtureRoot(tmp).align_questions("fixture-seed")


class TestQuestionsContentPin(unittest.TestCase):
  def test_question_text_change_detected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      self.assertTrue(validate_freeze(tmp, manifest).passed)
      # Same ids, same splits, altered text -> must fail.
      changed = [dict(q, text="CHANGED SYNTHETIC TEXT") for q in root.questions]
      root.write(REQUIRED_QUESTIONS_FILE, json.dumps(changed))
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("questions_sha256 mismatch" in g for g in check.gaps))

  def test_malformed_questions_gaps_not_crash(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      root.write(REQUIRED_QUESTIONS_FILE, "{not json")
      check = validate_freeze(tmp, root.manifest())
      self.assertFalse(check.passed)
      self.assertTrue(any("questions file" in g for g in check.gaps))


class TestGeneratorContractPin(unittest.TestCase):
  def _tamper_field(self, testcase, field, value):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      self.assertTrue(validate_freeze(tmp, manifest).passed)
      disk = dict(root.gen_dict)
      disk[field] = value
      root.write(REQUIRED_GENERATOR_FILE, json.dumps(disk))
      check = validate_freeze(tmp, manifest)
      testcase.assertFalse(check.passed)
      return check

  def test_generator_id_change_detected(self):
    check = self._tamper_field(self, "generator_id", "different-generator")
    self.assertTrue(any("generator_id" in g for g in check.gaps))

  def test_chat_template_change_detected(self):
    check = self._tamper_field(self, "chat_template_sha256", "d" * 64)
    self.assertTrue(any("chat_template_sha256" in g or "config_sha256" in g
                        for g in check.gaps))

  def test_context_window_change_detected(self):
    check = self._tamper_field(self, "context_window", 2048)
    self.assertTrue(any("context_window" in g or "config_sha256" in g
                        for g in check.gaps))

  def test_sampling_change_detected(self):
    check = self._tamper_field(self, "generation", {"temperature": 0.9})
    self.assertTrue(any("sampling" in g or "config_sha256" in g for g in check.gaps))

  def test_tokenizer_change_detected(self):
    check = self._tamper_field(self, "tokenizer_id", "other-tok")
    self.assertTrue(any("tokenizer_id" in g or "config_sha256" in g for g in check.gaps))

  def test_whitespace_only_change_detected(self):
    # Generic raw-byte pin: no semantic field changed, still fails.
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      self.assertTrue(validate_freeze(tmp, manifest).passed)
      with open(os.path.join(tmp, REQUIRED_GENERATOR_FILE), "a", encoding="utf-8") as fh:
        fh.write("\n")
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("generator_config_sha256 mismatch" in g for g in check.gaps))

  def test_license_change_detected_generically(self):
    # Non-whitelisted field: covered by raw config hash, not field list.
    check = self._tamper_field(self, "license", "SYNTHETIC-LICENSE")
    self.assertTrue(any("generator_config_sha256 mismatch" in g for g in check.gaps))


class TestRuntimeInventory(unittest.TestCase):
  def test_binary_tamper_detected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      self.assertTrue(validate_freeze(tmp, manifest).passed)
      root.write("bin/llama-server", b"TAMPERED", binary=True)
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("runtime binary sha256 mismatch" in g for g in check.gaps))

  def test_binary_missing_detected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      os.remove(os.path.join(tmp, "bin/libtest.so.0"))
      check = validate_freeze(tmp, root.manifest())
      self.assertFalse(check.passed)
      self.assertTrue(any("runtime binary missing" in g for g in check.gaps))

  def test_unpinned_binary_detected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      manifest.inventory = [p for p in manifest.inventory if "libtest" not in p.path]
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("unpinned in manifest inventory" in g for g in check.gaps))

  def test_malformed_runtime_section_gaps(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      disk = dict(root.gen_dict)
      disk["runtime_binaries"] = {"libs": "not-a-dict"}
      root.write(REQUIRED_GENERATOR_FILE, json.dumps(disk))
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)


class TestGroupMap(unittest.TestCase):
  def _group_manifest(self, root, groups, questions="default"):
    from substrate.manifest import sha256_file

    map_rel = "corpus/split_map.json"
    root.write(map_rel, json.dumps({"seed": "s", "groups": groups}))
    if questions == "default" and groups:
      first = next(iter(groups))
      first_split = groups[first].get("split", "train")
      questions = [
        {"question_id": "qa", "text": "q?", "split": first_split,
         "meta": {"source_articles": ["UPPER"], "group": first}},
      ]
    if questions != "default":
      root.write(REQUIRED_QUESTIONS_FILE, json.dumps(questions))
    manifest = root.manifest(split_method="group-map", split_map_path=map_rel)
    manifest.split_map_sha256 = sha256_file(os.path.join(root.tmp, map_rel))
    return manifest

  def test_empty_groups_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      check = validate_freeze(tmp, self._group_manifest(root, {}))
      self.assertFalse(check.passed)
      self.assertTrue(any("no groups" in g for g in check.gaps))

  def test_overlapping_articles_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      groups = {
        "g1": {"split": "train", "articles": ["Upper"]},
        "g2": {"split": "dev", "articles": ["upper "]},
      }
      check = validate_freeze(tmp, self._group_manifest(root, groups))
      self.assertFalse(check.passed)
      self.assertTrue(any("multiple groups" in g for g in check.gaps))

  def test_invalid_split_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      groups = {"g1": {"split": "nope", "articles": ["Upper"]}}
      check = validate_freeze(tmp, self._group_manifest(root, groups))
      self.assertFalse(check.passed)

  def test_unresolved_articles_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      groups = {"g1": {"split": "train", "articles": ["Nonexistent Place XYZ"]}}
      check = validate_freeze(tmp, self._group_manifest(root, groups))
      self.assertFalse(check.passed)
      self.assertTrue(any("no corpus node" in g for g in check.gaps))

  def test_resolved_map_passes(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      groups = {"g1": {"split": "train", "articles": ["UPPER"]}}
      check = validate_freeze(tmp, self._group_manifest(root, groups))
      self.assertTrue(check.passed, f"gaps={check.gaps}")

  def test_qa_group_leak_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = self._group_manifest(
        root, {"g1": {"split": "train", "articles": ["UPPER"]}},
        questions=[
          {"question_id": "qa", "text": "q?", "split": "dev",
           "meta": {"source_articles": ["UPPER"], "group": "g1"}},
        ],
      )
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("qa provenance" in g and "dev" in g for g in check.gaps))

  def test_malformed_map_gaps_not_crash(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = self._group_manifest(root, {"g1": {"split": "train", "articles": ["x"]}})
      root.write("corpus/split_map.json", "{broken")
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("malformed" in g for g in check.gaps))


class TestUnifiedPolicyAndCitations(unittest.TestCase):
  def test_bare_float_threshold_rejected_in_trace(self):
    trace = dict(good_trace(), stages=[{
      "stage": "stage0",
      "candidate_ids": ["p1"],
      "scores": [0.9],
      "score_kind": "calibrated_probability",
      "threshold_policy": {
        "threshold": 0.7,
        "interpretation": "unspecified",
        "calibration_method": "unspecified",
        "score_kind": "calibrated_probability",
        "top_k": None,
        "min_breadth": 0,
        "calibration_partition": ""
      },
      "pruning_decisions": [True],
      "latency_ms": 1.0,
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "model_identity": "synth-model-v1"
    }])
    self.assertTrue(any("unspecified" in e for e in validate_trace(trace)))

  def test_model_probability_accepted_in_trace(self):
    self.assertEqual(validate_trace(good_trace()), [])

  def test_platt_without_provenance_rejected_in_trace(self):
    trace = dict(good_trace(), stages=[{
      "stage": "stage0",
      "candidate_ids": ["p1"],
      "scores": [0.9],
      "score_kind": "calibrated_probability",
      "threshold_policy": {
        "threshold": 0.5,
        "interpretation": "calibrated_probability",
        "calibration_method": "platt",
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
    self.assertTrue(any("provenance" in e for e in validate_trace(trace)))

  def test_raw_absolute_threshold_legal_in_trace(self):
    trace = dict(good_trace(), stages=[{
      "stage": "stage0",
      "candidate_ids": ["p1"],
      "scores": [3.1],
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
      "pruning_decisions": [True],
      "latency_ms": 1.0,
      "model_loading_latency_ms": None,
      "inference_latency_ms": 0.5,
      "peak_rss_mb": 12.0,
      "model_identity": "synth-model-v1"
    }])
    self.assertEqual(validate_trace(trace), [])

  def test_unknown_citations_permitted_failed_answer_preserved(self):
    trace = dict(good_trace(), citations=["ghost-1"],
                 generator_response="I hallucinate [ghost-1].")
    self.assertEqual(validate_trace(trace), [])
    self.assertIn("hallucinate", trace["generator_response"])

  def test_mixed_kind_pipeline_valid(self):
    """similarity -> logit -> model_probability -> calibrated_probability all correctly declared."""
    trace = dict(good_trace(), stages=[
      {
        "stage": "bm25",
        "candidate_ids": ["p1", "p2", "p3"],
        "scores": [0.95, 0.87, 0.72],
        "score_kind": "similarity",
        "threshold_policy": {
          "threshold": 0.5,
          "interpretation": "raw_score_absolute",
          "calibration_method": "none_ranking_only",
          "score_kind": "similarity",
          "top_k": 50,
          "min_breadth": 10,
          "calibration_partition": ""
        },
        "pruning_decisions": [True, True, True],
        "latency_ms": 5.0,
        "model_loading_latency_ms": None,
        "inference_latency_ms": 5.0,
        "peak_rss_mb": 50.0,
        "model_identity": "bm25-index-v1"
      },
      {
        "stage": "ettin",
        "candidate_ids": ["p1", "p2"],
        "scores": [4.2, -1.5],
        "score_kind": "logit",
        "threshold_policy": {
          "threshold": 2.0,
          "interpretation": "raw_score_absolute",
          "calibration_method": "none_ranking_only",
          "score_kind": "logit",
          "top_k": 20,
          "min_breadth": 5,
          "calibration_partition": ""
        },
        "pruning_decisions": [True, False],
        "latency_ms": 50.0,
        "model_loading_latency_ms": 100.0,
        "inference_latency_ms": 45.0,
        "peak_rss_mb": 2000.0,
        "model_identity": "ettin-encoder-v3"
      },
      {
        "stage": "kalm",
        "candidate_ids": ["p1"],
        "scores": [0.85],
        "score_kind": "model_probability",
        "threshold_policy": {
          "threshold": 0.5,
          "interpretation": "model_probability_dev_selected",
          "calibration_method": "model_probability",
          "score_kind": "model_probability",
          "top_k": 10,
          "min_breadth": 3,
          "calibration_partition": ""
        },
        "pruning_decisions": [True],
        "latency_ms": 200.0,
        "model_loading_latency_ms": 500.0,
        "inference_latency_ms": 180.0,
        "peak_rss_mb": 4000.0,
        "model_identity": "kalm-reranker-v2"
      },
      {
        "stage": "calibrator",
        "candidate_ids": ["p1"],
        "scores": [0.92],
        "score_kind": "calibrated_probability",
        "threshold_policy": {
          "threshold": 0.5,
          "interpretation": "calibrated_probability",
          "calibration_method": "temperature_scaling",
          "score_kind": "calibrated_probability",
          "top_k": 5,
          "min_breadth": 1,
          "calibration_partition": "sha256:cal-partition-v1"
        },
        "pruning_decisions": [True],
        "latency_ms": 10.0,
        "model_loading_latency_ms": 50.0,
        "inference_latency_ms": 8.0,
        "peak_rss_mb": 100.0,
        "model_identity": "platt-calibrator-v1"
      },
    ])
    self.assertEqual(validate_trace(trace), [])

  def test_model_probability_dev_selected_accepted_on_model_probability_stage(self):
    """model_probability_dev_selected on a model_probability stage is ACCEPTED."""
    trace = dict(good_trace(), stages=[{
      "stage": "kalm",
      "candidate_ids": ["p1"],
      "scores": [0.85],
      "score_kind": "model_probability",
      "threshold_policy": {
        "threshold": 0.5,
        "interpretation": "model_probability_dev_selected",
        "calibration_method": "model_probability",
        "score_kind": "model_probability",
        "top_k": 10,
        "min_breadth": 3,
        "calibration_partition": ""
      },
      "pruning_decisions": [True],
      "latency_ms": 200.0,
      "model_loading_latency_ms": 500.0,
      "inference_latency_ms": 180.0,
      "peak_rss_mb": 4000.0,
      "model_identity": "kalm-reranker-v2"
    }])
    self.assertEqual(validate_trace(trace), [])

  def test_model_probability_dev_selected_rejected_on_logit_stage(self):
    """model_probability_dev_selected on a logit stage is REJECTED."""
    trace = dict(good_trace(), stages=[{
      "stage": "ettin",
      "candidate_ids": ["p1"],
      "scores": [4.2],
      "score_kind": "logit",
      "threshold_policy": {
        "threshold": 0.5,
        "interpretation": "model_probability_dev_selected",
        "calibration_method": "model_probability",
        "score_kind": "logit",
        "top_k": 10,
        "min_breadth": 3,
        "calibration_partition": ""
      },
      "pruning_decisions": [True],
      "latency_ms": 50.0,
      "model_loading_latency_ms": 100.0,
      "inference_latency_ms": 45.0,
      "peak_rss_mb": 2000.0,
      "model_identity": "ettin-encoder-v3"
    }])
    errors = validate_trace(trace)
    self.assertTrue(any("model_probability_dev_selected interpretation requires" in e
                        for e in errors))


class TestRound0DeclarationsAndSecrecy(unittest.TestCase):
  def test_unfitted_declarations_pass_freeze(self):
    # Round 0 records declarations; learned fits come from Round 1 teams.
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      manifest = root.manifest()
      manifest.thresholds["rank-only"] = ThresholdPolicy(
        threshold=None, interpretation="raw_score_percentile", top_k=50,
        calibration_method="none_ranking_only", score_kind="logit")
      check = validate_freeze(tmp, manifest)
      self.assertTrue(check.passed, f"gaps={check.gaps}")

  def test_error_text_carries_no_secrets(self):
    secret = "SECRET-LABEL-CONTENT-XYZ"
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      root.write(REQUIRED_LABELS_FILE,
                 f'{{"qa": ["{secret}"]}}'.encode("utf-8"), binary=True)
      check = validate_freeze(tmp, root.manifest())
      self.assertFalse(check.passed)
      self.assertFalse(any(secret in g for g in check.gaps))

  def test_unknown_phase_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = aligned_root(tmp)
      check = validate_freeze(tmp, root.manifest(phase="experiment"))
      self.assertFalse(check.passed)
      self.assertTrue(any("phase" in g for g in check.gaps))


class TestLegacyMigration(unittest.TestCase):
  """Tests for explicit legacy trace migration (also in test_semantics_adversarial)."""

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

  def test_migrate_legacy_trace_produces_valid_new_format(self):
    """migrate_legacy_trace produces a valid new-format trace."""
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


if __name__ == "__main__":
  unittest.main()