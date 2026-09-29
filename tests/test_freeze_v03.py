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

from eval.run_format import validate_trace
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
    trace = dict(good_trace(), thresholds={"stage0": 0.7})
    self.assertTrue(any("unspecified" in e for e in validate_trace(trace)))

  def test_model_probability_accepted_in_trace(self):
    self.assertEqual(validate_trace(good_trace()), [])

  def test_platt_without_provenance_rejected_in_trace(self):
    trace = dict(
      good_trace(),
      thresholds={"stage0": {"threshold": 0.5, "interpretation": "calibrated_probability",
                             "calibration_method": "platt",
                             "score_kind": "calibrated_probability"}},
    )
    self.assertTrue(any("provenance" in e for e in validate_trace(trace)))

  def test_raw_absolute_threshold_legal_in_trace(self):
    trace = dict(
      good_trace(), score_kind="logit", stage_scores={"stage0": [3.1]},
      thresholds={"stage0": {"threshold": 2.5, "interpretation": "raw_score_absolute",
                             "calibration_method": "none_ranking_only",
                             "score_kind": "logit"}},
    )
    self.assertEqual(validate_trace(trace), [])

  def test_unknown_citations_permitted_failed_answer_preserved(self):
    trace = dict(good_trace(), citations=["ghost-1"],
                 generator_response="I hallucinate [ghost-1].")
    self.assertEqual(validate_trace(trace), [])
    self.assertIn("hallucinate", trace["generator_response"])


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


if __name__ == "__main__":
  unittest.main()
