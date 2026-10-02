"""Tests for eval.answer_scoring (deterministic parts of the scoring protocol)."""

import unittest

from eval.answer_scoring import (
  abstention_outcome,
  exact_match,
  match_any_variant,
  normalize_answer,
  score_ambiguous_response,
  score_answerable_question,
  score_unanswerable_response,
)


class TestNormalization(unittest.TestCase):
  def test_casefold(self):
    self.assertEqual(normalize_answer("Paris"), normalize_answer("PARIS"))

  def test_punctuation(self):
    self.assertEqual(normalize_answer("St. Louis!"), normalize_answer("st louis"))

  def test_articles(self):
    self.assertEqual(normalize_answer("The Eiffel Tower"), normalize_answer("eiffel tower"))
    self.assertEqual(normalize_answer("A Cat"), normalize_answer("cat"))
    self.assertEqual(normalize_answer("An Apple"), normalize_answer("apple"))

  def test_whitespace(self):
    self.assertEqual(normalize_answer("  new   york\ncity "), "new york city")

  def test_unicode(self):
    # Full-width + composed-vs-decomposed compare equal after NFKC.
    self.assertEqual(normalize_answer("ＡＢＣ"), "abc")
    self.assertEqual(normalize_answer("caf\u00e9"), normalize_answer("cafe\u0301"))

  def test_non_string_rejected(self):
    with self.assertRaises(TypeError):
      normalize_answer(None)  # type: ignore[arg-type]


class TestMatching(unittest.TestCase):
  def test_exact_match(self):
    self.assertTrue(exact_match("The Eiffel Tower", "eiffel tower"))

  def test_accepted_variant(self):
    m = match_any_variant("NYC", "New York City", ["NYC", "New York"])
    self.assertTrue(m["match"])
    self.assertEqual(m["matched_variant"], "NYC")

  def test_mismatch(self):
    self.assertFalse(exact_match("Paris", "London"))
    m = match_any_variant("Paris", "London", ["Londres"])
    self.assertFalse(m["match"])
    self.assertIsNone(m["matched_variant"])

  def test_empty_prediction_never_matches(self):
    self.assertFalse(exact_match("   ", "Paris"))
    self.assertFalse(exact_match("the", "the"))


class TestAbstention(unittest.TestCase):
  def test_correct_abstain_is_success(self):
    self.assertEqual(abstention_outcome(answerable=False, abstained=True), "correct_abstention")
    r = score_unanswerable_response(abstained=True, produced_answer_text=False)
    self.assertEqual(r, {"outcome": "correct_abstention", "correct": True})

  def test_fabricated_answer_is_failure(self):
    self.assertEqual(abstention_outcome(answerable=False, abstained=False), "unsupported_generation")
    r = score_unanswerable_response(abstained=False, produced_answer_text=True)
    self.assertFalse(r["correct"])
    self.assertEqual(r["outcome"], "unsupported_generation")

  def test_answerable_abstention_is_failure(self):
    self.assertEqual(abstention_outcome(answerable=True, abstained=True), "false_abstention")
    r = score_answerable_question("anything", "anything", abstained=True)
    self.assertFalse(r["correct"])

  def test_unlabeled_is_none(self):
    self.assertIsNone(abstention_outcome(answerable=None, abstained=True))


class TestAmbiguity(unittest.TestCase):
  def test_grounded_readings_succeed(self):
    r = score_ambiguous_response(claimed_ambiguity=True, n_gold_readings=2, n_grounded_readings=2)
    self.assertTrue(r["correct"])
    self.assertEqual(r["outcome"], "grounded_ambiguity")

  def test_single_answer_only_fails(self):
    r = score_ambiguous_response(claimed_ambiguity=False, n_gold_readings=2, n_grounded_readings=1)
    self.assertFalse(r["correct"])
    self.assertEqual(r["outcome"], "single_answer_only")

  def test_claim_without_grounding_fails(self):
    r = score_ambiguous_response(claimed_ambiguity=True, n_gold_readings=3, n_grounded_readings=1)
    self.assertFalse(r["correct"])
    self.assertEqual(r["outcome"], "ungrounded_ambiguity")

  def test_degenerate_gold_rejected(self):
    with self.assertRaises(ValueError):
      score_ambiguous_response(claimed_ambiguity=True, n_gold_readings=1, n_grounded_readings=1)


class TestDeterminism(unittest.TestCase):
  def test_same_input_twice_identical(self):
    args = ("  The Eiffel Tower! ", "eiffel tower", ["Tour Eiffel"])
    self.assertEqual(match_any_variant(*args), match_any_variant(*args))
    self.assertEqual(normalize_answer(args[0]), normalize_answer(args[0]))
    a = score_ambiguous_response(claimed_ambiguity=True, n_gold_readings=2, n_grounded_readings=2)
    b = score_ambiguous_response(claimed_ambiguity=True, n_gold_readings=2, n_grounded_readings=2)
    self.assertEqual(a, b)


if __name__ == "__main__":
  unittest.main()
