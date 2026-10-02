"""A freeze must leave a durable artifact, not only a terminal verdict.

Independent review v5 found that `RunManifest.write()` was implemented and never
called: a passing freeze run printed a verdict and left nothing behind to re-read,
hash, or compare against a later run. These tests pin the durable record and the
conditions under which it is (and is not) written.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(REPO_ROOT, "scripts", "verify_round0")
PRIVATE_DIR = os.environ.get(
  "LMR_PRIVATE_EVAL_DIR",
  "/home/davidhatley/Projects/testing/local_mobile_research-private-eval",
)


def _run(root, stages, private_dir):
  env = dict(os.environ)
  env.setdefault("VERIFY_ROUND0_PYTHON", "python3")
  if private_dir is not None:
    env["LMR_PRIVATE_EVAL_DIR"] = private_dir
  proc = subprocess.run(
    [VERIFIER, "--only", stages, "--root", root],
    capture_output=True, text=True, env=env, timeout=600,
  )
  return proc.returncode, proc.stdout + proc.stderr


def _copy(root_src, tmp, name="repo"):
  dest = os.path.join(tmp, name)
  shutil.copytree(root_src, dest,
                  ignore=shutil.ignore_patterns(".git", "__pycache__"))
  return dest


def _configure_private(dst):
  """Copy the out-of-repo custody files needed by stage 8.

  Only digests and the census pin are copied. No private question text, answer,
  support atom or label is read, and none is needed: the seal is verified as
  opaque bytes and the pin is a digest.
  """
  os.makedirs(dst, exist_ok=True)
  copied = []
  for name in ("freeze_census_pin.json", "seal.sha256"):
    src = os.path.join(PRIVATE_DIR, name)
    if not os.path.isfile(src):
      return None
    shutil.copy2(src, os.path.join(dst, name))
    copied.append(name)
  return copied


class TestFreezeManifestIsDurable(unittest.TestCase):
  def setUp(self):
    if not os.path.isfile(os.path.join(REPO_ROOT, "corpus", "corpus.jsonl")):
      self.skipTest("corpus/corpus.jsonl absent (sandboxed copy)")
    self.tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
    self.repo = _copy(REPO_ROOT, self.tmp)
    self.priv = os.path.join(self.tmp, "private")
    if not _configure_private(self.priv):
      self.skipTest("private custody digests unavailable")

  def test_run_manifest_write_is_not_dead_code(self):
    """The writer must exist and round-trip, or the durability claim is false."""
    from substrate.manifest import RunManifest
    self.assertTrue(hasattr(RunManifest, "write"),
                    "RunManifest.write is gone")
    self.assertTrue(callable(RunManifest.write))

  def test_passing_stage8_writes_the_manifest_outside_the_repo(self):
    rc, out = _run(self.repo, "8", self.priv)
    self.assertEqual(rc, 0, f"stage 8 must pass:\n{out}")
    self.assertIn("freeze manifest written", out)

    written = os.path.join(self.priv, "freeze_manifest.json")
    self.assertTrue(os.path.isfile(written),
                    "a passing freeze must leave a durable manifest")
    with open(written, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # The record must actually pin the things the freeze is about.
    self.assertEqual(data["phase"], "round0-substrate")
    self.assertEqual(len(data["corpus_hash"]), 64)
    self.assertEqual(len(data["sealed_labels_sha256"]), 64)
    self.assertEqual(len(data["questions_sha256"]), 64)
    self.assertEqual(len(data["split_map_sha256"]), 64)
    self.assertEqual(len(data["partition_census_sha256"]), 64)
    self.assertTrue(data["regime_a_heldout_groups"])
    self.assertTrue(data["regime_b_document_heldout_groups"])
    self.assertTrue(data["code_hashes"])

    # It must NOT be written into the repository.
    self.assertFalse(os.path.isfile(
      os.path.join(self.repo, "freeze_manifest.json")),
      "the freeze record must live outside the repository it constrains")
    self.assertFalse(os.path.isfile(
      os.path.join(self.repo, "corpus", "freeze_manifest.json")))

  def test_manifest_binds_the_census_digest(self):
    rc, _out = _run(self.repo, "8", self.priv)
    self.assertEqual(rc, 0)
    import hashlib
    with open(os.path.join(self.repo, "corpus", "partition_census.json"),
              "rb") as fh:
      live = hashlib.sha256(fh.read()).hexdigest()
    with open(os.path.join(self.priv, "freeze_manifest.json"), "r",
              encoding="utf-8") as fh:
      data = json.load(fh)
    self.assertEqual(data["partition_census_sha256"], live,
                     "the freeze record must bind the census it verified")

  def test_failing_stage8_writes_nothing(self):
    # Break the census so stage 8 fails.
    with open(os.path.join(self.repo, "corpus", "partition_census.json"),
              "r", encoding="utf-8") as fh:
      census = json.load(fh)
    census["expected"]["total"] = 9999
    with open(os.path.join(self.repo, "corpus", "partition_census.json"),
              "w", encoding="utf-8") as fh:
      json.dump(census, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = _run(self.repo, "8", self.priv)
    self.assertNotEqual(rc, 0, f"stage 8 must fail:\n{out}")
    self.assertFalse(
      os.path.isfile(os.path.join(self.priv, "freeze_manifest.json")),
      "a FAILING freeze must not leave a manifest that looks like a pass")


if __name__ == "__main__":
  unittest.main()