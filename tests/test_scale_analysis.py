"""Tests for eval.scale_analysis under incomplete relevance judgments."""

import unittest

from eval.scale_analysis import (
  NON_SUPPORTING,
  SUPPORTING,
  UNKNOWN,
  analyze_scale_retrieval,
  compare_scale_tiers,
  triage_retrieval,
)


class TestConfusableProducesUnknown(unittest.TestCase):
  def test_top_ranked_confusable_requests_adjudication_and_is_unknown(self):
    # World War II is a documented confusable; ranked #1 but not core support.
    ranked = ["dp:world_war_ii:00:000", "p:core:01:000"]
    out = analyze_scale_retrieval(ranked, {"p:core:01:000"}, k_list=(1, 5))
    self.assertEqual(len(out["adjudication_requests"]), 1)
    req = out["adjudication_requests"][0]
    self.assertEqual(req["rank"], 1)
    self.assertTrue(req["needs_adjudication"])
    self.assertEqual(req["triage"], UNKNOWN)
    # Unknown is never silently resolved to a false positive.
    self.assertNotIn(req["triage"], (SUPPORTING, NON_SUPPORTING))
    self.assertGreaterEqual(out["counts"]["unjudged_top_k"], 1)

  def test_explicit_human_verdict_resolves_triage(self):
    t = triage_retrieval("dp:world_war_ii:00:000", {"dp:world_war_ii:00:000": SUPPORTING})
    self.assertEqual(t["triage"], SUPPORTING)
    t2 = triage_retrieval("dp:world_war_ii:00:000", {"dp:world_war_ii:00:000": NON_SUPPORTING})
    self.assertEqual(t2["triage"], NON_SUPPORTING)


class TestBackgroundNotIrrelevant(unittest.TestCase):
  def test_background_never_asserted_irrelevant(self):
    # d:abba is background per the pageid-collision regression test.
    t = triage_retrieval("dp:abba:00:000")
    self.assertFalse(t["needs_adjudication"])
    self.assertEqual(t["triage"], "unjudged_mechanical")
    self.assertNotIn("irrelevant", (t.get("reason") or "").lower())


class TestKnownSupportOnly(unittest.TestCase):
  def test_unjudged_items_cannot_move_recall(self):
    known = {"p:core:01:000"}
    base = analyze_scale_retrieval(["p:core:01:000", "x"], known, k_list=(2,))
    junk = analyze_scale_retrieval(
      ["p:core:01:000", "dp:world_war_ii:00:000", "dp:abba:00:000", "dp:zzz:00:000"],
      known,
      k_list=(2,),
    )
    self.assertEqual(base["recall@2_known"], junk["recall@2_known"])
    self.assertIn("limitations", junk)
    self.assertTrue(junk["limitations"])
    self.assertIn("unjudged_top_k", junk["counts"])

  def test_no_precision_key(self):
    out = analyze_scale_retrieval(["p:core:01:000"], {"p:core:01:000"})
    self.assertNotIn("precision", out)


class TestReductionAndDisplacement(unittest.TestCase):
  def test_displacement_and_reduction(self):
    small = ["p:a", "p:b"]
    large = ["dp:world_war_ii:00:000", "p:a", "dp:abba:00:000", "p:b"]
    out = compare_scale_tiers(small, large, {"p:a", "p:b"}, k_list=(2,))
    self.assertEqual(out["displacement"]["p:a"]["shift"], 1)
    self.assertEqual(out["displacement"]["p:b"]["shift"], 2)
    self.assertAlmostEqual(out["reduction_ratio"], 2 / 4)
    self.assertEqual(out["recall_delta_known"]["recall@2_known"]["small"], 1.0)
    self.assertEqual(out["recall_delta_known"]["recall@2_known"]["large"], 0.5)
    self.assertTrue(out["limitations"])


if __name__ == "__main__":
  unittest.main()
