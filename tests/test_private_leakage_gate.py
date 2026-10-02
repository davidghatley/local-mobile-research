"""Leakage-gate tests: the custodian-side question-overlap check.

ALL FIXTURES ARE SYNTHETIC. The synthetic private directory is built fresh
in a temp dir per test; the real out-of-repo private eval directory is never
read here. The synthetic seal mirrors the real seal chain in
``seal_private.py`` (canonical-JSON bytes -> per-item hashes -> aggregate ->
seal over the file digests), using the ``sha256_file`` helper from
``substrate.private_eval`` -- never a hand-rolled digest that trivially
matches.
"""

import hashlib
import json
import os
import tempfile
import unittest
from contextlib import contextmanager

from substrate import private_eval

# Synthetic private question texts. These exist ONLY in temp dirs created
# below; they are never written into the repository.
SYNTH_PRIVATE_ITEMS = [
  {"question_id": "synth-priv-1", "text": "What is the capital city of France?"},
  {"question_id": "synth-priv-2", "text": "Which element has the chemical symbol Au?"},
  {"question_id": "synth-priv-3",
   "text": "In what year did the Apollo 11 mission land on the Moon?"},
  {"question_id": "synth-priv-4", "text": "What river flows through the Grand Canyon?"},
]

UNRELATED_TEXT = "How many legs does a spider have?"


def _canon(obj):
  return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False).encode("utf-8")


def _build_synthetic_private_dir(path):
  """Write synthetic questions/labels/seal, mirroring the real seal chain."""
  qpath = os.path.join(path, "questions.json")
  with open(qpath, "wb") as fh:
    fh.write(_canon(SYNTH_PRIVATE_ITEMS))
  labels = {it["question_id"]: {"answerability": "answerable"}
            for it in SYNTH_PRIVATE_ITEMS}
  lpath = os.path.join(path, "labels.json")
  with open(lpath, "wb") as fh:
    fh.write(_canon(labels))
  per_item = {it["question_id"]: hashlib.sha256(_canon(it)).hexdigest()
              for it in SYNTH_PRIVATE_ITEMS}
  aggregate = hashlib.sha256(
    "".join(f"{k}:{v}\n" for k, v in sorted(per_item.items())).encode()
  ).hexdigest()
  # Imported helper, not a hand-rolled digest.
  qhash = private_eval.sha256_file(qpath)
  lhash = private_eval.sha256_file(lpath)
  seal = hashlib.sha256(_canon([qhash, lhash, aggregate])).hexdigest()
  with open(os.path.join(path, "seal.sha256"), "w", encoding="utf-8") as fh:
    fh.write(seal + "\n")


@contextmanager
def _point_at(path):
  """Point LMR_PRIVATE_EVAL_DIR at path, restoring os.environ afterwards."""
  key = private_eval.PRIVATE_EVAL_DIR_ENV
  old = os.environ.get(key)
  os.environ[key] = path
  try:
    yield
  finally:
    if old is None:
      os.environ.pop(key, None)
    else:
      os.environ[key] = old


class TestLeakageGate(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    _build_synthetic_private_dir(self.tmp.name)

  def tearDown(self):
    self.tmp.cleanup()

  def _check(self, records):
    with _point_at(self.tmp.name):
      return private_eval.check_training_overlap(records)

  def test_exact_duplicate_rejects_and_flags_id(self):
    verdict = self._check([
      {"synthetic_id": "syn-1", "text": "What is the capital city of France?"},
    ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, ["syn-1"])

  def test_normalization_variant_rejects(self):
    verdict = self._check([
      {"synthetic_id": "syn-1", "text": "  WHAT is the Capital City of FRANCE???  "},
    ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, ["syn-1"])

  def test_near_duplicate_above_threshold_rejects(self):
    # Drops "the": Jaccard 6/7 ~= 0.857 >= 0.80, so layer 2 must fire.
    verdict = self._check([
      {"synthetic_id": "syn-1", "text": "Which element has chemical symbol Au?"},
    ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, ["syn-1"])

  def test_unrelated_question_passes(self):
    verdict = self._check([
      {"synthetic_id": "syn-1", "text": UNRELATED_TEXT},
    ])
    self.assertEqual(verdict.verdict, "PASS")
    self.assertEqual(verdict.flagged_ids, [])
    self.assertIn("no question-level overlap", verdict.reason)

  def test_multiple_records_only_offending_ids_returned(self):
    verdict = self._check([
      {"synthetic_id": "syn-clean", "text": UNRELATED_TEXT},
      {"synthetic_id": "syn-bad-1", "text": "What is the capital city of France?"},
      {"synthetic_id": "syn-bad-2", "text": "Which element has chemical symbol Au?"},
    ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, ["syn-bad-1", "syn-bad-2"])

  def test_missing_private_seal_rejects(self):
    os.remove(os.path.join(self.tmp.name, "seal.sha256"))
    verdict = self._check([
      {"synthetic_id": "syn-1", "text": UNRELATED_TEXT},
    ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, [])

  def test_malformed_training_input_rejects(self):
    bad_inputs = [
      "not a list",
      [],
      [{"synthetic_id": "syn-1"}],  # missing text
      [{"text": "some text"}],  # missing synthetic_id
      [{"synthetic_id": "", "text": "some text"}],
      [{"synthetic_id": "syn-1", "text": ""}],
      [{"synthetic_id": "syn-1", "text": 42}],
      ["just-a-string-id"],  # legacy bare ids carry no text: fail closed
    ]
    for bad in bad_inputs:
      with self.subTest(bad=bad):
        verdict = self._check(bad)
        self.assertEqual(verdict.verdict, "REJECT")
        self.assertEqual(verdict.flagged_ids, [])

  def test_private_dir_absent_rejects(self):
    with _point_at(os.path.join(self.tmp.name, "does-not-exist")):
      verdict = private_eval.check_training_overlap([
        {"synthetic_id": "syn-1", "text": UNRELATED_TEXT},
      ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, [])

  def test_malformed_private_questions_reject(self):
    with open(os.path.join(self.tmp.name, "questions.json"), "w",
              encoding="utf-8") as fh:
      fh.write("{not valid json")
    verdict = self._check([
      {"synthetic_id": "syn-1", "text": UNRELATED_TEXT},
    ])
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, [])

  def test_no_private_content_in_result_object(self):
    private_strings = []
    for it in SYNTH_PRIVATE_ITEMS:
      private_strings.append(it["text"])
      private_strings.append(it["question_id"])
    flagged = self._check([
      {"synthetic_id": "syn-1", "text": "What is the capital city of France?"},
    ])
    passing = self._check([
      {"synthetic_id": "syn-1", "text": UNRELATED_TEXT},
    ])
    for verdict in (flagged, passing):
      blob = json.dumps(verdict.to_dict(), ensure_ascii=False)
      for secret in private_strings:
        self.assertNotIn(secret, blob)
      # Structural guarantee: exactly the three allowed fields.
      self.assertEqual(sorted(verdict.to_dict()), ["flagged_ids", "reason", "verdict"])

  def test_determinism_same_input_twice(self):
    records = [
      {"synthetic_id": "syn-clean", "text": UNRELATED_TEXT},
      {"synthetic_id": "syn-bad", "text": "What is the capital city of France?"},
    ]
    first = self._check(records)
    second = self._check(records)
    self.assertEqual(first.to_dict(), second.to_dict())

  def test_training_file_json_list(self):
    path = os.path.join(self.tmp.name, "training.json")
    with open(path, "w", encoding="utf-8") as fh:
      json.dump([
        {"synthetic_id": "syn-1", "text": "What is the capital city of France?"},
        {"synthetic_id": "syn-2", "text": UNRELATED_TEXT},
      ], fh)
    with _point_at(self.tmp.name):
      verdict = private_eval.check_training_file(path)
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, ["syn-1"])

  def test_training_file_jsonl(self):
    path = os.path.join(self.tmp.name, "training.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
      fh.write(json.dumps({"synthetic_id": "syn-1", "text": UNRELATED_TEXT}) + "\n")
      fh.write(json.dumps({"synthetic_id": "syn-2",
                           "text": "What river flows through the Grand Canyon?"}) + "\n")
    with _point_at(self.tmp.name):
      verdict = private_eval.check_training_file(path)
    self.assertEqual(verdict.verdict, "REJECT")
    self.assertEqual(verdict.flagged_ids, ["syn-2"])

  def test_training_file_malformed_rejects(self):
    path = os.path.join(self.tmp.name, "training.json")
    with open(path, "w", encoding="utf-8") as fh:
      fh.write("{bad json")
    with _point_at(self.tmp.name):
      verdict = private_eval.check_training_file(path)
    self.assertEqual(verdict.verdict, "REJECT")
    with _point_at(self.tmp.name):
      missing = private_eval.check_training_file(
        os.path.join(self.tmp.name, "no-such-file.json"))
    self.assertEqual(missing.verdict, "REJECT")


if __name__ == "__main__":
  unittest.main()
