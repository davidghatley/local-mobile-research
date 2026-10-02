"""Stage 10 (private-eval custody) must fail closed on an unbound manifest.

An independent freeze review found a vacuous pass: stage 10 printed
"MATCHES in-repo manifest" when the manifest recorded no hash to compare
against, so a manifest stripped of its digests would still pass. These tests
pin the fail-closed behaviour.
"""

import json
import os
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(REPO_ROOT, "scripts", "verify_round0")
MANIFEST_REL = "corpus/private_test_manifest.json"


def run_verifier(root, *args, env=None):
  import subprocess
  full_env = dict(os.environ)
  full_env.setdefault("VERIFY_ROUND0_PYTHON", "python3")
  if env:
    full_env.update(env)
  proc = subprocess.run(
    [VERIFIER, "--only", "10", "--root", root, *args],
    capture_output=True, text=True, env=full_env, timeout=300,
  )
  return proc.returncode, proc.stdout + proc.stderr


class TestStage10FailsClosed(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
    self.repo = os.path.join(self.tmp, "repo")
    shutil.copytree(REPO_ROOT, self.repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    self.manifest_path = os.path.join(self.repo, MANIFEST_REL)

  def _read_manifest(self):
    with open(self.manifest_path, "r", encoding="utf-8") as fh:
      return json.load(fh)

  def _write_manifest(self, data):
    with open(self.manifest_path, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")

  def test_baseline_passes(self):
    rc, out = run_verifier(self.repo)
    self.assertEqual(rc, 0, "stage 10 must pass on the real artifacts:\n%s" % out)
    self.assertIn("MATCHES in-repo manifest", out)

  def test_missing_recorded_questions_hash_fails(self):
    man = self._read_manifest()
    man["hashes"].pop("questions_json_sha256", None)
    self._write_manifest(man)
    rc, out = run_verifier(self.repo)
    self.assertNotEqual(rc, 0, "an unbound question set must fail:\n%s" % out)
    self.assertIn("no questions_json_sha256", out)
    self.assertNotIn("questions.json sha256 MATCHES", out)

  def test_missing_recorded_labels_hash_fails(self):
    man = self._read_manifest()
    man["hashes"].pop("labels_json_sha256", None)
    self._write_manifest(man)
    rc, out = run_verifier(self.repo)
    self.assertNotEqual(rc, 0, "unbound label set must fail:\n%s" % out)
    self.assertIn("no labels_json_sha256", out)
    self.assertNotIn("labels.json sha256 MATCHES", out)

  def test_missing_seal_fails(self):
    man = self._read_manifest()
    man.pop("seal_sha256", None)
    self._write_manifest(man)
    rc, out = run_verifier(self.repo)
    self.assertNotEqual(rc, 0, "no seal digest must fail:\n%s" % out)
    self.assertIn("no seal_sha256", out)

  def test_wrong_recorded_hash_fails(self):
    man = self._read_manifest()
    man["hashes"]["questions_json_sha256"] = "0" * 64
    self._write_manifest(man)
    rc, out = run_verifier(self.repo)
    self.assertNotEqual(rc, 0, "hash mismatch must fail:\n%s" % out)
    self.assertIn("MISMATCH", out)

  def test_manifest_with_private_content_fails(self):
    man = self._read_manifest()
    man["counts"]["sample_question"] = "qa-private-01"
    self._write_manifest(man)
    rc, out = run_verifier(self.repo)
    self.assertNotEqual(rc, 0, "private content in the manifest must fail:\n%s" % out)
    self.assertIn("PRIVATE CONTENT", out)

  def test_missing_manifest_fails(self):
    os.remove(self.manifest_path)
    rc, out = run_verifier(self.repo)
    self.assertNotEqual(rc, 0, "absent manifest must fail closed:\n%s" % out)
    self.assertIn("private_test_manifest.json", out)

  def test_private_dir_pointing_into_repo_fails(self):
    rc, out = run_verifier(
      self.repo,
      env={"LMR_PRIVATE_EVAL_DIR": os.path.join(self.repo, "staging")},
    )
    self.assertNotEqual(rc, 0, "an in-repo private dir must fail:\n%s" % out)
    self.assertIn("outside the repository", out)


if __name__ == "__main__":
  unittest.main()
