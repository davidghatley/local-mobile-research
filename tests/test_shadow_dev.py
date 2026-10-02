"""Issue 1 tripwire: exposed held-out reclassified as dev-visible shadow_dev.

Asserts the Phase 1 reclassification invariant:
(a) no staging file uses the retired split "heldout";
(b) every staging/qa-shadow-dev-*.json has split shadow_dev + meta.original_id
    + meta.exposure_note (provenance preserved, never secret);
(c) count == 89 with id 60 recorded absent (never fabricated);
(d) SPLITS contains shadow_dev and private_test;
(e) no in-repo question file declares split private_test (private data lives
    OUTSIDE the repo at LMR_PRIVATE_EVAL_DIR, Phase 5).

Synthetic assertions on file metadata only; never prints question/answer text.
"""

import glob
import json
import os
import unittest

from substrate.splits import SPLITS

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
STAGING = os.path.join(REPO_ROOT, "staging")


def _load(path):
  with open(path, "r", encoding="utf-8") as fh:
    return json.load(fh)


class TestShadowDevReclassification(unittest.TestCase):
  def test_splits_vocabulary(self):
    self.assertIn("shadow_dev", SPLITS)
    self.assertIn("private_test", SPLITS)
    self.assertIn("train", SPLITS)
    self.assertIn("dev", SPLITS)
    self.assertNotIn("heldout", SPLITS)

  def test_no_staging_file_uses_retired_heldout(self):
    files = sorted(glob.glob(os.path.join(STAGING, "*.json")))
    self.assertTrue(files, "staging dir has no json files")
    bad = []
    for path in files:
      try:
        rec = _load(path)
      except (ValueError, OSError):
        continue
      if isinstance(rec, dict) and rec.get("split") == "heldout":
        bad.append(os.path.basename(path))
    self.assertEqual(bad, [], f"staging files still use retired split heldout: {bad[:5]}")

  def test_no_staging_shadow_dev_filename_uses_heldout(self):
    leftovers = sorted(glob.glob(os.path.join(STAGING, "qa-heldout-*.json")))
    self.assertEqual(
      [os.path.basename(p) for p in leftovers], [],
      "retired qa-heldout-* filenames remain in staging (must be qa-shadow-dev-*)",
    )

  def test_shadow_dev_records_carry_provenance(self):
    files = sorted(glob.glob(os.path.join(STAGING, "qa-shadow-dev-*.json")))
    # 89 were reclassified in Phase 1. Two (qa-shadow-dev-84, -86) were
    # independently REJECTED during the freeze review and quarantined under
    # staging/rejected/, so the usable shadow-dev set is honestly 87.
    self.assertEqual(len(files), 87, f"expected 87 shadow-dev files, found {len(files)}")
    for path in files:
      rec = _load(path)
      base = os.path.basename(path)
      self.assertEqual(rec.get("split"), "shadow_dev", base)
      num = base[len("qa-shadow-dev-"):-len(".json")]
      self.assertEqual(rec.get("question_id"), f"qa-shadow-dev-{num}", base)
      meta = rec.get("meta")
      self.assertIsInstance(meta, dict, base)
      self.assertTrue(
        isinstance(meta.get("original_id"), str) and meta["original_id"].startswith("qa-heldout-"),
        f"{base}: meta.original_id missing",
      )
      self.assertTrue(
        isinstance(meta.get("exposure_note"), str) and meta["exposure_note"].strip(),
        f"{base}: meta.exposure_note missing",
      )
      prov = rec.get("provenance")
      self.assertIsInstance(prov, dict, base)
      self.assertTrue(
        isinstance(prov.get("author"), str) and prov["author"].strip(),
        f"{base}: original author must be preserved",
      )
      self.assertIn("reclassification", prov, f"{base}: reclassification entry missing")

  def test_count_is_honest_and_id_60_absent(self):
    files = sorted(glob.glob(os.path.join(STAGING, "qa-shadow-dev-*.json")))
    nums = sorted(p[len(os.path.join(STAGING, "qa-shadow-dev-")):-len(".json")] for p in files)
    self.assertEqual(len(nums), 87)
    self.assertNotIn("60", nums, "qa-shadow-dev-60 was never authored and must stay absent")
    # 89 = 87 usable + 2 rejected-and-quarantined. The rejected ids are named
    # in staging/rejected/ and must not reappear as usable items.
    rejected_dir = os.path.join(STAGING, "rejected")
    rejected = sorted(os.path.basename(p) for p in
                      glob.glob(os.path.join(rejected_dir, "qa-shadow-dev-*.json")))
    self.assertEqual(rejected, ["qa-shadow-dev-84.json", "qa-shadow-dev-86.json"])
    self.assertNotIn("84", nums)
    self.assertNotIn("86", nums)
    self.assertEqual(
      len(nums) + len(rejected), 89,
      "89 reclassified items must all be accounted for: usable or rejected",
    )
    # The absence of 60 and the rejection of 84/86 are recorded in docs, not
    # silently dropped and never fabricated. STATUS.md must name both facts.
    with open(os.path.join(REPO_ROOT, "docs", "STATUS.md"), "r", encoding="utf-8") as fh:
      status = fh.read()
    self.assertIn("60", status)
    self.assertIn("89", status)
    self.assertIn("87", status, "STATUS.md must state the usable count is 87")
    # The quarantine README must account for all 89.
    with open(os.path.join(rejected_dir, "README.md"), "r", encoding="utf-8") as fh:
      readme = fh.read()
    self.assertIn("89", readme)
    self.assertIn("87", readme)

  def test_no_in_repo_private_test_questions(self):
    offenders = []
    for path in sorted(glob.glob(os.path.join(STAGING, "*.json"))):
      try:
        rec = _load(path)
      except (ValueError, OSError):
        continue
      if isinstance(rec, dict) and rec.get("split") == "private_test":
        offenders.append(os.path.basename(path))
    self.assertEqual(offenders, [], f"in-repo private_test question files: {offenders[:5]}")
    for rel in (os.path.join("corpus", "questions.json"),):
      full = os.path.join(REPO_ROOT, rel)
      if os.path.isfile(full):
        data = _load(full)
        entries = data if isinstance(data, list) else []
        bad = [e.get("question_id") for e in entries
               if isinstance(e, dict) and e.get("split") == "private_test"]
        self.assertEqual(bad, [], f"{rel} contains in-repo private_test entries")


if __name__ == "__main__":
  unittest.main()
