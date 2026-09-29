"""Metrics tests with hand-computed expectations. All fixtures SYNTHETIC."""

import unittest

from eval.metrics import (
  brier_score,
  conditional_retention,
  expected_calibration_error,
  lost_and_recovered,
  ndcg_at_k,
  recall_at_k,
  reciprocal_rank,
  stage_coverage,
  sufficient_set_completion,
  survival_curve,
  token_stats,
  wilson_ci,
)


class TestTraditionalMetrics(unittest.TestCase):
  def test_recall_preserved(self):
    self.assertAlmostEqual(recall_at_k(["a", "b"], {"a", "c"}, 2), 0.5)
    self.assertEqual(recall_at_k(["a"], set(), 1), 1.0)

  def test_reciprocal_rank(self):
    self.assertAlmostEqual(reciprocal_rank(["x", "a"], {"a"}), 0.5)
    self.assertEqual(reciprocal_rank(["x"], {"a"}), 0.0)

  def test_ndcg_perfect_is_one(self):
    self.assertAlmostEqual(ndcg_at_k(["a", "b"], {"a", "b"}, 2), 1.0)

  def test_token_stats_p95(self):
    stats = token_stats([100, 200, 300, 400, 500])
    self.assertEqual(stats["n"], 5.0)
    self.assertEqual(stats["max"], 500.0)
    self.assertEqual(token_stats([])["n"], 0)


class TestSurvivalVocabulary(unittest.TestCase):
  def test_lineage_is_uninterrupted(self):
    # A lineage pruned at stage 1 stays dead even if re-discovered later.
    self.assertEqual(survival_curve([True, False, True]), [1.0, 0.0, 0.0])

  def test_stage_coverage_recovers(self):
    # ...while direct coverage honestly reports the recovery.
    ev = {"p1"}
    self.assertEqual(stage_coverage(["p0"], ev), 0.0)
    self.assertEqual(stage_coverage(["p1"], ev), 1.0)

  def test_conditional_retention_reports_denominators(self):
    r = conditional_retention(["p1", "p2"], ["p2", "p3"], {"p1", "p2"})
    self.assertEqual(r, {"rate": 0.5, "numerator": 1, "denominator": 2})

  def test_conditional_retention_undefined_not_zero(self):
    r = conditional_retention(["p0"], ["p1"], {"p1"})
    self.assertEqual(r["denominator"], 0)
    self.assertIsNone(r["rate"])

  def test_lost_and_recovered(self):
    out = lost_and_recovered(["p1", "p2"], ["p2", "p3"], {"p1", "p2", "p3"})
    self.assertEqual(out, {"lost": ["p1"], "recovered": ["p3"]})


class TestCompletion(unittest.TestCase):
  def test_alternative_set_completes(self):
    # Genuine alternative passage p3 suffices although canonical p1 is absent.
    out = sufficient_set_completion(["p3", "x"], [{"p1", "p2"}, {"p3"}])
    self.assertEqual(out["completion"], 1.0)
    self.assertEqual(out["best_set_index"], 1)
    self.assertEqual(out["complete_sets"], [1])

  def test_partial_completion_exposes_fraction_separately(self):
    out = sufficient_set_completion(["p1"], [{"p1", "p2"}, {"p3", "p4", "p5"}])
    self.assertEqual(out["completion"], 0.0)  # binary: no set fully covered
    self.assertAlmostEqual(out["best_fractional_coverage"], 0.5)
    self.assertEqual(out["complete_sets"], [])

  def test_no_ground_truth_is_none_not_zero(self):
    self.assertIsNone(sufficient_set_completion(["p1"], [])["completion"])


class TestCalibrationAdversarial(unittest.TestCase):
  def test_brier_perfect_is_zero(self):
    self.assertAlmostEqual(brier_score([1.0, 0.0], [1, 0]), 0.0)

  def test_ece_perfect_is_zero(self):
    self.assertAlmostEqual(
      expected_calibration_error([1.0, 1.0, 0.0, 0.0], [1, 1, 0, 0]), 0.0, places=6
    )

  def test_ece_confidently_wrong_is_high(self):
    self.assertGreater(expected_calibration_error([0.95] * 10, [0] * 10), 0.8)

  def test_logits_rejected_ece(self):
    with self.assertRaises(ValueError):
      expected_calibration_error([5.0, -2.0], [1, 0])

  def test_logits_rejected_brier(self):
    with self.assertRaises(ValueError):
      brier_score([5.0, 0.5], [1, 0])

  def test_out_of_range_rejected(self):
    with self.assertRaises(ValueError):
      brier_score([1.5, 0.5], [1, 0])

  def test_nonfinite_rejected(self):
    with self.assertRaises(ValueError):
      expected_calibration_error([float("nan"), 0.5], [1, 0])
    with self.assertRaises(ValueError):
      brier_score([float("inf")], [1])

  def test_nonbinary_labels_rejected(self):
    with self.assertRaises(ValueError):
      brier_score([0.9], [2])
    with self.assertRaises(ValueError):
      expected_calibration_error([0.9], [-1])


class TestWilson(unittest.TestCase):
  def test_interval_contains_point(self):
    ci = wilson_ci(8, 10)
    self.assertLessEqual(ci["lower"], 0.8)
    self.assertGreaterEqual(ci["upper"], 0.8)

  def test_invalid_inputs_rejected(self):
    with self.assertRaises(ValueError):
      wilson_ci(3, 0)
    with self.assertRaises(ValueError):
      wilson_ci(5, 4)


if __name__ == "__main__":
  unittest.main()
