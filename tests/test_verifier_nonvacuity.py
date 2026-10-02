"""Stage 6 must not pass vacuously on an empty or leaky partition.

An independent review (v3) found two holes in stage 6:

  * `questions.json = []` produced "0 ids, 0 structural error(s)" and PASSED.
  * an injected `meta.group` + `rationale` (answer location + answer text)
    produced NO stage-6 diagnostic at all, while docs/verify-round0.md claimed
    stage 6 "requires" the partition to carry neither.

These tests pin both. Each one mutates a COPY of the repo; the real tree is
never modified.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(REPO_ROOT, "scripts", "verify_round0")
PARTITION_REL = "corpus/questions.json"


def run_stage6(root, *args):
  env = dict(os.environ)
  env.setdefault("VERIFY_ROUND0_PYTHON", "python3")
  proc = subprocess.run(
    [VERIFIER, "--only", "6", "--root", root, *args],
    capture_output=True, text=True, env=env, timeout=300,
  )
  return proc.returncode, proc.stdout + proc.stderr


class TestStage6NonVacuity(unittest.TestCase):
  def setUp(self):
    if not os.path.isfile(os.path.join(REPO_ROOT, PARTITION_REL)):
      self.skipTest("corpus/questions.json absent")
    self.tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
    self.repo = os.path.join(self.tmp, "repo")
    shutil.copytree(REPO_ROOT, self.repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    self.path = os.path.join(self.repo, PARTITION_REL)

  def _write(self, data):
    with open(self.path, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")

  def _read(self):
    with open(self.path, "r", encoding="utf-8") as fh:
      return json.load(fh)

  # ---- non-vacuity ------------------------------------------------------
  def test_baseline_passes(self):
    rc, out = run_stage6(self.repo)
    self.assertEqual(rc, 0, f"stage 6 must pass on the real partition:\n{out}")

  def test_empty_partition_fails(self):
    self._write([])
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"an empty partition must fail:\n{out}")
    self.assertIn("EMPTY", out)

  def test_truncated_partition_fails(self):
    self._write(self._read()[:3])
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"a truncated partition must fail:\n{out}")
    self.assertIn("truncated", out.lower())

  # ---- leak detection ---------------------------------------------------
  def test_answer_location_leak_fails(self):
    data = self._read()
    data[0].setdefault("meta", {})["group"] = "some_group"
    self._write(data)
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"meta.group must be caught:\n{out}")
    self.assertIn("answer location", out)

  def test_source_articles_leak_fails(self):
    data = self._read()
    data[0].setdefault("meta", {})["source_articles"] = ["Some Article"]
    self._write(data)
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"meta.source_articles must be caught:\n{out}")
    self.assertIn("answer location", out)

  def test_rationale_prose_leak_fails(self):
    data = self._read()
    data[0].setdefault("provenance", {})["rationale"] = "the atom states the answer"
    self._write(data)
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"provenance.rationale must be caught:\n{out}")
    self.assertIn("answer text in", out)

  def test_forbidden_field_still_fails(self):
    data = self._read()
    data[0]["evidence"] = {"sufficient_sets": []}
    self._write(data)
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"an evidence field must be caught:\n{out}")
    self.assertIn("forbidden field", out)

  def test_private_split_entry_fails(self):
    data = self._read()
    data[0]["split"] = "private_test"
    self._write(data)
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"a private_test entry must fail:\n{out}")
    self.assertIn("private_test", out)

  def test_retired_split_entry_fails(self):
    data = self._read()
    data[0]["split"] = "heldout"
    self._write(data)
    rc, out = run_stage6(self.repo)
    self.assertNotEqual(rc, 0, f"a retired heldout entry must fail:\n{out}")
    self.assertIn("heldout", out)


class TestPublicPartitionTestsAreLoadBearing(unittest.TestCase):
  """The new unit tests must actually fail against a leaky partition.

  A test suite that passes against a deliberately broken file tests nothing.
  This proves the guard bites.
  """

  def setUp(self):
    if not os.path.isfile(os.path.join(REPO_ROOT, PARTITION_REL)):
      self.skipTest("corpus/questions.json absent")
    self.tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
    self.repo = os.path.join(self.tmp, "repo")
    shutil.copytree(REPO_ROOT, self.repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))

  def _run_partition_tests(self):
    proc = subprocess.run(
      ["python3", "-m", "unittest", "tests.test_public_partition"],
      cwd=self.repo, capture_output=True, text=True, timeout=300,
    )
    return proc.returncode, proc.stdout + proc.stderr

  def test_leaky_partition_is_caught_by_unit_tests(self):
    path = os.path.join(self.repo, PARTITION_REL)
    with open(path, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    # Inject an answer into prose AND the answer's location into metadata.
    data[0].setdefault("meta", {})["source_articles"] = ["Some Article"]
    data[0].setdefault("provenance", {})["rationale"] = "x" * 200
    drafts = {}
    import glob
    for p in glob.glob(os.path.join(self.repo, "staging", "qa-*.json")):
      with open(p, "r", encoding="utf-8") as fh:
        rec = json.load(fh)
      drafts[rec["question_id"]] = rec
    target = drafts.get(data[0]["question_id"])
    if target is not None and target.get("labels", {}).get("answer_text"):
      data[0]["meta"]["exposure_note"] = (
        "the atom states " + target["labels"]["answer_text"])
    with open(path, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")

    rc, out = self._run_partition_tests()
    self.assertNotEqual(rc, 0,
                         "test_public_partition passed against a deliberately "
                         "leaky file, so it is not load-bearing:\n" + out[-3000:])
    self.assertIn("FAIL", out)

  def test_clean_partition_passes(self):
    rc, out = self._run_partition_tests()
    self.assertEqual(rc, 0, f"clean partition must pass:\n{out}")


if __name__ == "__main__":
  unittest.main()