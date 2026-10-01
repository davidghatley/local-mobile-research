"""Per-stage score kind / threshold policy semantic tests.

All fixtures SYNTHETIC, tmp-only. Covers the exact matrix from the repair plan.
"""

import unittest

from eval.run_format import validate_trace, migrate_legacy_trace
from substrate.generator import PROMPT_HASH
from substrate.types import ThresholdPolicy


def new_trace_base():
    """Base trace with NEW per-stage schema (no legacy flat fields)."""
    return {
        "question_id": "q1",
        "run_id": "r1",
        "architecture": "hybrid-pipeline",
        "seed": 42,
        "query": "synthetic query",
        "stages": [],  # filled per test
        "adaptive_compute_decision": "keep-top-50",
        "evidence_packet": {"spans": []},
        "evidence_token_count": 100,
        "evidence_token_method": "tokenizer:synth-tok",
        "retrieval_latency_ms": 10.0,
        "model_loading_latency_ms": 50.0,
        "inference_latency_ms": 5.0,
        "peak_rss_mb": 200.0,
        "storage_bytes": 1024,
        "generator_prompt_hash": PROMPT_HASH,
        "generator_id": "synth-generator-v1",
        "generator_response": "synthetic answer",
        "citations": [],
        "available_citations": [],
        "grader_result": None,
    }


def make_stage(
    name,
    score_kind,
    scores,
    candidate_ids=None,
    decisions=None,
    threshold=None,
    interpretation="raw_score_absolute",
    calibration_method="none_ranking_only",
    top_k=None,
    calibration_partition="",
    model_identity="model-v1",
    latency_ms=1.0,
):
    """Build a stage dict for the new schema."""
    if candidate_ids is None:
        candidate_ids = [f"{name}-p{i}" for i in range(len(scores))]
    if decisions is None:
        decisions = [s > (threshold or 0) for s in scores]
    return {
        "stage": name,
        "candidate_ids": candidate_ids,
        "scores": scores,
        "score_kind": score_kind,
        "threshold_policy": {
            "threshold": threshold,
            "interpretation": interpretation,
            "top_k": top_k,
            "min_breadth": 0,
            "calibration_method": calibration_method,
            "score_kind": score_kind,
            "calibration_partition": calibration_partition,
        },
        "pruning_decisions": decisions,
        "latency_ms": latency_ms,
        "model_loading_latency_ms": 10.0,
        "inference_latency_ms": 1.0,
        "peak_rss_mb": 50.0,
        "model_identity": model_identity,
    }


class TestMixedPipelineCorrectlyDeclared(unittest.TestCase):
    """Mixed pipeline similarity -> logit -> model_probability -> calibrated_probability => PASS

    NOTE: The Lane B design requires 'model_probability' as a distinct score_kind.
    Currently substrate/types.py SCORE_KINDS lacks 'model_probability' (cross-lane conflict).
    This test uses the workaround: calibrated_probability with calibration_method=model_probability.
    """

    def test_four_stage_hybrid_pipeline_passes_workaround(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("bm25", "similarity", [0.9, 0.7, 0.5, 0.3],
                       threshold=0.6, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
            make_stage("ettin", "logit", [5.0, 2.0, -1.0, -3.0],
                       threshold=1.5, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
            # Workaround: calibrated_probability score_kind with model_probability calibration
            make_stage("kalm", "calibrated_probability", [0.95, 0.6, 0.3, 0.1],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="model_probability"),
            make_stage("calibrator", "calibrated_probability", [0.92, 0.55, 0.25, 0.05],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="temperature_scaling",
                       calibration_partition="sha256:cal-part-v1"),
        ]
        self.assertEqual(validate_trace(trace), [])

    # model_probability is now in SCORE_KINDS; guard resolved
    def test_four_stage_hybrid_pipeline_passes_native_model_probability(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("bm25", "similarity", [0.9, 0.7, 0.5, 0.3],
                       threshold=0.6, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
            make_stage("ettin", "logit", [5.0, 2.0, -1.0, -3.0],
                       threshold=1.5, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
            make_stage("kalm", "model_probability", [0.95, 0.6, 0.3, 0.1],
                       threshold=0.5,
                       interpretation="model_probability_dev_selected",
                       calibration_method="model_probability"),
            make_stage("calibrator", "calibrated_probability", [0.92, 0.55, 0.25, 0.05],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="temperature_scaling",
                       calibration_partition="sha256:cal-part-v1"),
        ]
        self.assertEqual(validate_trace(trace), [])


class TestStagePolicyScoreKindMismatch(unittest.TestCase):
    """ANY stage mislabeled (stage score_kind != policy score_kind) => FAIL"""

    def test_policy_score_kind_mismatch_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "logit", [5.0, 2.0],
                       threshold=1.0, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
        ]
        # Corrupt: policy says calibrated_probability but stage says logit
        trace["stages"][0]["threshold_policy"]["score_kind"] = "calibrated_probability"
        errors = validate_trace(trace)
        self.assertTrue(any("policy score_kind" in e and "!= stage score_kind" in e for e in errors))


class TestProbabilityThresholdOnLogit(unittest.TestCase):
    """Probability threshold on a logit => FAIL"""

    def test_probability_threshold_on_logit_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "logit", [5.0, 2.0],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="none_ranking_only"),  # ranking-only on logit with prob threshold
        ]
        errors = validate_trace(trace)
        # ThresholdPolicy.validate checks score_kind != "calibrated_probability" first
        self.assertTrue(any("probability interpretation requires calibrated_probability scores" in e for e in errors))

    def test_probability_threshold_on_logit_with_fitted_calibration_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "logit", [5.0, 2.0],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="platt",
                       calibration_partition="sha256:part"),
        ]
        errors = validate_trace(trace)
        # ThresholdPolicy.validate checks score_kind != "calibrated_probability" first
        self.assertTrue(any("probability interpretation requires calibrated_probability scores" in e for e in errors))


class TestRankingPolicyOnLogitNoProbabilityClaim(unittest.TestCase):
    """Ranking policy on a logit with no probability claim => PASS"""

    def test_raw_absolute_threshold_on_logit_passes(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "logit", [5.0, 2.0, -1.0],
                       threshold=1.0, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
        ]
        self.assertEqual(validate_trace(trace), [])

    def test_raw_percentile_threshold_on_logit_passes(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "logit", [5.0, 2.0, -1.0],
                       threshold=0.8, interpretation="raw_score_percentile",
                       calibration_method="none_ranking_only", top_k=2),
        ]
        self.assertEqual(validate_trace(trace), [])

    def test_top_k_only_on_logit_passes(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "logit", [5.0, 2.0, -1.0],
                       threshold=None, interpretation="raw_score_percentile",
                       calibration_method="none_ranking_only", top_k=2),
        ]
        self.assertEqual(validate_trace(trace), [])


class TestModelProbabilityWithDevThresholdEceBrier(unittest.TestCase):
    """model_probability with dev-selected threshold and ECE/Brier evaluable => PASS

    NOTE: The Lane B design requires 'model_probability' as a distinct score_kind.
    Currently substrate/types.py SCORE_KINDS lacks 'model_probability' (cross-lane conflict).
    These tests use the workaround: calibrated_probability with calibration_method=model_probability.
    """

    def test_model_probability_dev_threshold_passes_workaround(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.6, 0.3, 0.1],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="model_probability"),
        ]
        self.assertEqual(validate_trace(trace), [])

    def test_model_probability_raw_threshold_also_passes_workaround(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.6, 0.3, 0.1],
                       threshold=0.7, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
        ]
        self.assertEqual(validate_trace(trace), [])

    # model_probability is now in SCORE_KINDS; guard resolved
    def test_model_probability_dev_threshold_passes_native(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "model_probability", [0.9, 0.6, 0.3, 0.1],
                       threshold=0.5,
                       interpretation="model_probability_dev_selected",
                       calibration_method="model_probability"),
        ]
        self.assertEqual(validate_trace(trace), [])

    # model_probability is now in SCORE_KINDS; guard resolved
    def test_model_probability_raw_threshold_also_passes_native(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "model_probability", [0.9, 0.6, 0.3, 0.1],
                       threshold=0.7, interpretation="raw_score_absolute",
                       calibration_method="none_ranking_only"),
        ]
        self.assertEqual(validate_trace(trace), [])


class TestCalibratedProbabilityWithNoneRankingOnlyFails(unittest.TestCase):
    """calibrated_probability claimed with calibration_method none_ranking_only => FAIL"""

    def test_calibrated_probability_none_ranking_only_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.5, 0.2],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="none_ranking_only"),
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("probability threshold without evaluable model probabilities" in e for e in errors))


class TestFittedCalibrationEmptyPartitionFails(unittest.TestCase):
    """Fitted calibration with empty calibration_partition => FAIL"""

    def test_platt_without_partition_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.5, 0.2],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="platt",
                       calibration_partition=""),  # empty
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("provenance" in e for e in errors))

    def test_isotonic_without_partition_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.5, 0.2],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="isotonic",
                       calibration_partition=""),
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("provenance" in e for e in errors))

    def test_temperature_scaling_without_partition_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.5, 0.2],
                       threshold=0.5, interpretation="calibrated_probability",
                       calibration_method="temperature_scaling",
                       calibration_partition=""),
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("provenance" in e for e in errors))


class TestScoresOutside01DeclaredCalibratedFails(unittest.TestCase):
    """Scores outside [0,1] declared calibrated_probability => FAIL"""

    def test_negative_score_calibrated_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [-0.1, 0.5, 0.9]),
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("outside [0, 1]" in e or "must be in [0, 1]" in e for e in errors))

    def test_greater_than_one_score_calibrated_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.5, 1.5]),
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("outside [0, 1]" in e or "must be in [0, 1]" in e for e in errors))

    def test_logit_scores_declared_calibrated_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [5.0, -2.0, 0.8]),
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("outside [0, 1]" in e or "must be in [0, 1]" in e for e in errors))


class TestArrayMisalignmentFails(unittest.TestCase):
    """Array misalignment => FAIL"""

    def test_candidate_ids_scores_mismatch_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            {
                "stage": "stage0",
                "candidate_ids": ["p1", "p2"],
                "scores": [0.9],  # only 1 score
                "score_kind": "calibrated_probability",
                "threshold_policy": {"threshold": 0.5, "interpretation": "calibrated_probability",
                                     "calibration_method": "model_probability", "score_kind": "calibrated_probability"},
                "pruning_decisions": [True, False],
                "latency_ms": 1.0,
                "model_loading_latency_ms": 10.0,
                "inference_latency_ms": 1.0,
                "peak_rss_mb": 50.0,
                "model_identity": "model-v1",
            }
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("array length mismatch" in e for e in errors))

    def test_scores_decisions_mismatch_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            {
                "stage": "stage0",
                "candidate_ids": ["p1", "p2"],
                "scores": [0.9, 0.5],
                "score_kind": "calibrated_probability",
                "threshold_policy": {"threshold": 0.5, "interpretation": "calibrated_probability",
                                     "calibration_method": "model_probability", "score_kind": "calibrated_probability"},
                "pruning_decisions": [True],  # only 1 decision
                "latency_ms": 1.0,
                "model_loading_latency_ms": 10.0,
                "inference_latency_ms": 1.0,
                "peak_rss_mb": 50.0,
                "model_identity": "model-v1",
            }
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("array length mismatch" in e for e in errors))


class TestMissingModelIdentityFails(unittest.TestCase):
    """Missing model_identity in a stage => FAIL"""

    def test_missing_model_identity_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.5],
                       model_identity=""),  # empty string
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("model_identity" in e and "non-empty string" in e for e in errors))

    def test_none_model_identity_fails(self):
        trace = new_trace_base()
        trace["stages"] = [
            make_stage("stage0", "calibrated_probability", [0.9, 0.5],
                       model_identity=None),  # None
        ]
        errors = validate_trace(trace)
        self.assertTrue(any("model_identity" in e and "non-empty string" in e for e in errors))

    def test_absent_model_identity_fails(self):
        trace = new_trace_base()
        stage = make_stage("stage0", "calibrated_probability", [0.9, 0.5])
        del stage["model_identity"]
        trace["stages"] = [stage]
        errors = validate_trace(trace)
        self.assertTrue(any("model_identity" in e and "non-empty string" in e for e in errors))


class TestLegacyMigrationExplicitAndTested(unittest.TestCase):
    """Legacy trace migration explicit and tested"""

    def make_legacy_trace(self):
        return {
            "question_id": "q1",
            "run_id": "r1",
            "architecture": "legacy",
            "seed": 42,
            "query": "legacy query",
            "score_kind": "calibrated_probability",
            "stage_candidates": {"stage0": ["p1", "p2"], "stage1": ["p1"]},
            "stage_scores": {"stage0": [0.9, 0.5], "stage1": [0.8]},
            "pruning_decisions": {"stage0": [True, False], "stage1": [True]},
            "thresholds": {
                "stage0": {"threshold": 0.7, "interpretation": "calibrated_probability",
                           "calibration_method": "model_probability", "score_kind": "calibrated_probability"},
                "stage1": {"threshold": 0.5, "interpretation": "calibrated_probability",
                           "calibration_method": "model_probability", "score_kind": "calibrated_probability"},
            },
            "per_stage_latency_ms": {"stage0": 5.0, "stage1": 2.0},
            "adaptive_compute_decision": "keep-top-50",
            "evidence_packet": {"spans": []},
            "evidence_token_count": 100,
            "evidence_token_method": "tokenizer:synth-tok",
            "retrieval_latency_ms": 10.0,
            "model_loading_latency_ms": 50.0,
            "inference_latency_ms": 5.0,
            "peak_rss_mb": 200.0,
            "storage_bytes": 1024,
            "generator_prompt_hash": PROMPT_HASH,
            "generator_id": "synth-generator-v1",
            "generator_response": "legacy answer",
            "citations": [],
            "available_citations": [],
            "grader_result": None,
        }

    def test_legacy_migration_all_identities_provided_passes(self):
        legacy = self.make_legacy_trace()
        migrated = migrate_legacy_trace(legacy, model_identity_map={
            "stage0": "model-stage0-v1",
            "stage1": "model-stage1-v2",
        })
        # Verify new schema structure
        self.assertIn("stages", migrated)
        self.assertEqual(len(migrated["stages"]), 2)
        self.assertEqual(migrated["stages"][0]["stage"], "stage0")
        self.assertEqual(migrated["stages"][1]["stage"], "stage1")
        self.assertEqual(migrated["stages"][0]["model_identity"], "model-stage0-v1")
        self.assertEqual(migrated["stages"][1]["model_identity"], "model-stage1-v2")
        # Legacy flat fields dropped
        for f in ("score_kind", "stage_scores", "stage_candidates", "pruning_decisions", "thresholds", "per_stage_latency_ms"):
            self.assertNotIn(f, migrated)
        # Migrated trace validates
        self.assertEqual(validate_trace(migrated), [])

    def test_legacy_migration_missing_model_identity_fails_closed(self):
        legacy = self.make_legacy_trace()
        with self.assertRaises(ValueError) as cm:
            migrate_legacy_trace(legacy, model_identity_map={
                "stage0": "model-stage0-v1",
                # stage1 missing
            })
        self.assertIn("no model_identity provided", str(cm.exception))
        self.assertIn("fails closed", str(cm.exception))

    def test_legacy_migration_empty_model_identity_fails_closed(self):
        legacy = self.make_legacy_trace()
        with self.assertRaises(ValueError) as cm:
            migrate_legacy_trace(legacy, model_identity_map={
                "stage0": "model-stage0-v1",
                "stage1": "",  # empty
            })
        self.assertIn("non-empty string", str(cm.exception))

    def test_legacy_migration_malformed_arrays_fails(self):
        legacy = self.make_legacy_trace()
        legacy["stage_scores"]["stage0"] = [0.9]  # mismatch with 2 candidates
        with self.assertRaises(ValueError) as cm:
            migrate_legacy_trace(legacy, model_identity_map={
                "stage0": "model-stage0-v1",
                "stage1": "model-stage1-v2",
            })
        self.assertIn("array length mismatch", str(cm.exception))

    def test_legacy_migration_policy_score_kind_mismatch_fails(self):
        legacy = self.make_legacy_trace()
        legacy["thresholds"]["stage0"]["score_kind"] = "logit"  # mismatch with global calibrated_probability
        with self.assertRaises(ValueError) as cm:
            migrate_legacy_trace(legacy, model_identity_map={
                "stage0": "model-stage0-v1",
                "stage1": "model-stage1-v2",
            })
        self.assertIn("policy score_kind", str(cm.exception))
        self.assertIn("!= trace score_kind", str(cm.exception))

    def test_legacy_migration_unknown_score_kind_fails(self):
        legacy = self.make_legacy_trace()
        legacy["score_kind"] = "vibes"
        with self.assertRaises(ValueError) as cm:
            migrate_legacy_trace(legacy, model_identity_map={
                "stage0": "model-stage0-v1",
                "stage1": "model-stage1-v2",
            })
        self.assertIn("unknown score_kind", str(cm.exception))

    def test_legacy_migration_not_a_legacy_trace_fails(self):
        # Missing flat fields
        trace = new_trace_base()
        trace["stages"] = [make_stage("s0", "calibrated_probability", [0.9])]
        with self.assertRaises(ValueError) as cm:
            migrate_legacy_trace(trace, model_identity_map={})
        self.assertIn("not a legacy trace", str(cm.exception))


class TestUnidentifiableLegacyTraceFailsClosed(unittest.TestCase):
    """Unidentifiable legacy trace fails closed (no silent upgrade)"""

    def test_legacy_trace_without_model_identity_map_fails(self):
        # This tests that validate_trace rejects legacy flat fields
        # (migration is explicit, not a fallback)
        legacy = {
            "question_id": "q1",
            "run_id": "r1",
            "architecture": "legacy",
            "seed": 42,
            "query": "legacy",
            "score_kind": "calibrated_probability",
            "stage_candidates": {"stage0": ["p1"]},
            "stage_scores": {"stage0": [0.9]},
            "pruning_decisions": {"stage0": [True]},
            "thresholds": {"stage0": {"threshold": 0.5, "interpretation": "calibrated_probability",
                                       "calibration_method": "model_probability", "score_kind": "calibrated_probability"}},
            "per_stage_latency_ms": {"stage0": 1.0},
            "adaptive_compute_decision": "keep",
            "evidence_packet": {"spans": []},
            "evidence_token_count": 10,
            "evidence_token_method": "tokenizer:synth",
            "retrieval_latency_ms": 1.0,
            "model_loading_latency_ms": None,
            "inference_latency_ms": 1.0,
            "peak_rss_mb": 10.0,
            "storage_bytes": 100,
            "generator_prompt_hash": PROMPT_HASH,
            "generator_id": "synth-gen",
            "generator_response": "x",
            "citations": [],
            "available_citations": [],
            "grader_result": None,
        }
        # validate_trace should REJECT legacy flat fields explicitly
        errors = validate_trace(legacy)
        self.assertTrue(any("legacy flat trace fields detected" in e for e in errors))


if __name__ == "__main__":
    unittest.main()