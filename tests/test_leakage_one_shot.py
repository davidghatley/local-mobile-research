"""The leakage gate is a ONE-SHOT clearance decision, and that is enforced.

Independent freeze review v6 demonstrated that the gate is a boolean
near-duplicate MEMBERSHIP ORACLE: an architecture team with unlimited
submissions can binary-search the private set, and the wall-clock cost scales
with the private set's size. "Information asymmetry is preserved" was therefore
true only under a one-shot regime that was documented nowhere and enforced
nowhere.

These tests pin the enforcement, and pin the honest limit of the claim.
"""

import json
import os
import tempfile
import unittest

from tests.test_private_leakage_gate import (  # reuse the fixture builder
  _build_synthetic_private_dir,
  _canon,
  _point_at,
)
from substrate import private_eval

PRIVATE_TEXT = "Which river flows through Cairo?"
UNRELATED_TEXT = "How many legs does a spider have?"


class TestOneShotEnforcement(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self._write_private()

  def tearDown(self):
    self.tmp.cleanup()

  def _write_private(self):
    import hashlib
    qpath = os.path.join(self.tmp.name, "questions.json")
    lpath = os.path.join(self.tmp.name, "labels.json")
    items = [{"question_id": "qa-private-001", "text": PRIVATE_TEXT,
              "labels": {"answer_text": "the Nile"}}]
    with open(qpath, "wb") as fh:
      fh.write(_canon(items))
    with open(lpath, "wb") as fh:
      fh.write(_canon({"qa-private-001": {"answerability": "answerable"}}))
    per_item = {it["question_id"]: hashlib.sha256(_canon(it)).hexdigest()
                for it in items}
    aggregate = hashlib.sha256(
      "".join(f"{k}:{v}\n" for k, v in sorted(per_item.items())).encode()
    ).hexdigest()
    with open(os.path.join(self.tmp.name, "seal.sha256"), "w",
              encoding="utf-8") as fh:
      fh.write(hashlib.sha256(_canon([
        private_eval.sha256_file(qpath),
        private_eval.sha256_file(lpath),
        aggregate])).hexdigest() + "\n")

  def _check(self, records, session):
    with _point_at(self.tmp.name):
      return private_eval.check_training_overlap(records, session=session)

  # ---- the regime is enforced, not merely described ----
  def test_missing_session_is_refused(self):
    """An untrackable session cannot be one-shot, so it is refused."""
    with _point_at(self.tmp.name):
      v = private_eval.check_training_overlap(
        [{"synthetic_id": "s1", "text": UNRELATED_TEXT}])
    self.assertEqual(v.verdict, "REJECT")
    self.assertIn("session id is required", v.reason)

  def test_first_call_in_a_session_works(self):
    v = self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                    session="team-alpha")
    self.assertEqual(v.verdict, "PASS", v.reason)

  def test_second_call_in_the_same_session_is_refused(self):
    """The adaptive-oracle path. A REJECT then a re-PASS in one session would
    localise private content; the second call must not run at all."""
    self._check([{"synthetic_id": "s1", "text": PRIVATE_TEXT}], session="team-alpha")
    second = self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                         session="team-alpha")
    self.assertEqual(second.verdict, "REJECT")
    self.assertIn("one-shot", second.reason)
    self.assertEqual(second.flagged_ids, [])

  def test_a_fresh_session_is_authorised_deliberately(self):
    """A new session works again - that is the custodian opening a new
    clearance, not the caller retrying."""
    self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                session="team-alpha")
    v = self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                    session="team-beta")
    self.assertEqual(v.verdict, "PASS", v.reason)

  def test_ledger_lives_in_the_private_directory(self):
    """Enforcement point: the worker cannot read or reset it."""
    self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                session="team-alpha")
    ledger = os.path.join(self.tmp.name, "clearance_sessions.json")
    self.assertTrue(os.path.isfile(ledger),
                    "the session ledger must be out-of-repo, where a worker "
                    "cannot delete it to buy unlimited queries")
    with open(ledger, "r", encoding="utf-8") as fh:
      self.assertIn("team-alpha", json.load(fh))

  def test_unreadable_ledger_fails_closed(self):
    ledger = os.path.join(self.tmp.name, "clearance_sessions.json")
    with open(ledger, "w", encoding="utf-8") as fh:
      fh.write("{not json")
    v = self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                    session="team-gamma")
    self.assertEqual(v.verdict, "REJECT")
    self.assertIn("cannot evaluate leakage", v.reason)

  # ---- the refusal itself must not leak ----
  def test_refusal_carries_no_private_content(self):
    self._check([{"synthetic_id": "s1", "text": PRIVATE_TEXT}], session="team-alpha")
    second = self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                         session="team-alpha")
    blob = json.dumps(second.to_dict())
    for secret in (PRIVATE_TEXT, "Cairo", "Nile", "qa-private-001", "the Nile"):
      self.assertNotIn(secret, blob,
                       f"the one-shot refusal leaked {secret!r}")

  def test_result_object_still_has_exactly_three_fields(self):
    v = self._check([{"synthetic_id": "s1", "text": UNRELATED_TEXT}],
                    session="team-delta")
    self.assertEqual(sorted(v.to_dict()), ["flagged_ids", "reason", "verdict"])


class TestDocumentedLimitsMatchBehaviour(unittest.TestCase):
  """The honest limits must be written down, or the doc is marketing."""

  DOC = "docs/private-eval-custody.md"

  def _doc(self):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        self.DOC)
    if not os.path.isfile(path):
      self.skipTest(f"{self.DOC} absent")
    with open(path, "r", encoding="utf-8") as fh:
      return fh.read()

  def test_doc_states_the_one_shot_regime(self):
    doc = self._doc().lower()
    self.assertIn("one-shot", doc,
                  "the doc must state that the gate is one-shot")

  def test_doc_states_the_adaptive_oracle_limit(self):
    doc = self._doc().lower()
    self.assertTrue(
      "adaptive" in doc or "oracle" in doc,
      "the doc must admit the adaptive-caller limit rather than only "
      "claiming that information asymmetry is preserved")

  def test_doc_states_the_paraphrase_limit(self):
    doc = self._doc().lower()
    self.assertTrue(
      "paraphrase" in doc,
      "the doc must admit that semantic paraphrase is out of scope")

  def test_documented_thresholds_match_the_code(self):
    """A preregistered threshold that disagrees with the code is a false
    record. Review v6 found the doc at 0.85 while the code ran 0.80."""
    doc = self._doc()
    self.assertIn(str(private_eval.OVERLAP_JACCARD_THRESHOLD), doc)
    self.assertIn(str(private_eval.OVERLAP_CHAR_RATIO_THRESHOLD), doc)
    # And it must not still advertise the superseded value.
    self.assertNotIn(f"= 0.85", doc,
                     "the doc still advertises the superseded threshold")


if __name__ == "__main__":
  unittest.main()