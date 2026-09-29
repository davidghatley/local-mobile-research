"""Split + custodian tests. Synthetic ids only; no real labels touched."""

import json
import os
import tempfile
import unittest

from substrate.splits import (
  HeldoutAccessDenied,
  HeldoutCustodian,
  assign_split,
  assign_splits,
)


class TestSplits(unittest.TestCase):
  def test_deterministic(self):
    self.assertEqual(assign_split("q1", "seedA"), assign_split("q1", "seedA"))
    self.assertEqual(
      assign_splits(["q1", "q2"], "s"), assign_splits(["q1", "q2"], "s")
    )

  def test_different_seeds_can_differ(self):
    seen = {assign_split(f"q{i}", seed) for seed in ("s1", "s2") for i in range(50)}
    self.assertTrue(len(seen) > 1)

  def test_rough_fractions(self):
    ids = [f"q{i:04d}" for i in range(2000)]
    counts: dict[str, int] = {}
    for qid in ids:
      s = assign_split(qid, "frac-seed")
      counts[s] = counts.get(s, 0) + 1
    self.assertTrue(0.60 < counts["train"] / 2000 < 0.80)
    self.assertTrue(0.05 < counts["dev"] / 2000 < 0.25)
    self.assertTrue(0.05 < counts["heldout"] / 2000 < 0.25)

  def test_only_valid_split_names(self):
    for i in range(200):
      self.assertIn(assign_split(f"x{i}", "s"), ("train", "dev", "heldout"))

  def test_heldout_denied_by_default(self):
    with tempfile.TemporaryDirectory() as tmp:
      labels = os.path.join(tmp, "labels.json")
      with open(labels, "w", encoding="utf-8") as fh:
        json.dump({"q1": ["p1"]}, fh)
      cust = HeldoutCustodian(labels_path=labels,
                              audit_path=os.path.join(tmp, "audit.jsonl"))
      with self.assertRaises(HeldoutAccessDenied):
        cust.load_labels()

  def test_heldout_granted_only_with_flag_and_env(self):
    with tempfile.TemporaryDirectory() as tmp:
      labels = os.path.join(tmp, "labels.json")
      with open(labels, "w", encoding="utf-8") as fh:
        json.dump({"q1": ["p1"]}, fh)
      audit = os.path.join(tmp, "audit.jsonl")
      cust = HeldoutCustodian(labels_path=labels, audit_path=audit)
      old = os.environ.get("HELDOUT_CUSTODIAN_MODE")
      os.environ["HELDOUT_CUSTODIAN_MODE"] = "benchmark"
      try:
        with self.assertRaises(HeldoutAccessDenied):
          cust.load_labels(allow_heldout=False, accessor="t")
        got = cust.load_labels(allow_heldout=True, accessor="test-runner")
        self.assertEqual(got, {"q1": ["p1"]})
        with open(audit, encoding="utf-8") as fh:
          lines = fh.read().strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn("test-runner", lines[0])
      finally:
        if old is None:
          del os.environ["HELDOUT_CUSTODIAN_MODE"]
        else:
          os.environ["HELDOUT_CUSTODIAN_MODE"] = old

  def test_heldout_id_enumeration_blocked(self):
    with tempfile.TemporaryDirectory() as tmp:
      q = os.path.join(tmp, "q.json")
      with open(q, "w", encoding="utf-8") as fh:
        json.dump([{"question_id": "q1"}], fh)
      cust = HeldoutCustodian(labels_path=os.path.join(tmp, "nope.json"))
      with self.assertRaises(HeldoutAccessDenied):
        cust.question_ids_for(q, "heldout", "s")


if __name__ == "__main__":
  unittest.main()
