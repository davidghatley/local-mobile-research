"""Tripwire: private evaluation content must never live inside the repository.

SCOPE LIMIT (stated, not hidden): this is an explicit-path and provenance
guard. It is NOT a semantic secret scanner and does not attempt to detect
paraphrased or reworded private content. It fails closed on the things a
guard can actually check: private-evaluation filename patterns under the
repository path, a private directory that resolves inside the repository,
and known label/seal filename shapes.
"""

import json
import os
import re
import tempfile
import unittest
from unittest import mock

from substrate import private_eval
from substrate.private_eval import (
  PrivateEvalError,
  LeakageVerdict,
  assert_private_dir_outside_repo,
  check_training_overlap,
  counts,
  private_dir,
  seal_digest,
  verify_seal,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories that legitimately contain large/derived data or are not
# scanned for private content by this guard.
SKIP_DIR_PARTS = {".git", "__pycache__", "node_modules", ".build_tmp"}

# Filename patterns that must never appear under the repository path.
PRIVATE_NAME_PATTERNS = (
  re.compile(r"private_test", re.IGNORECASE),
  re.compile(r"private.*label", re.IGNORECASE),
  re.compile(r"label.*private", re.IGNORECASE),
  re.compile(r"^qa-private-", re.IGNORECASE),
  re.compile(r"\.seal$", re.IGNORECASE),
  re.compile(r"seal\.sha256$", re.IGNORECASE),
  re.compile(r"heldout_labels", re.IGNORECASE),
  re.compile(r"private_eval_dir", re.IGNORECASE),
)

# Documentation/interface files that legitimately mention the private
# concepts by name. These are the ONLY exemptions, by exact path.
NAME_EXEMPT_PATHS = {
  ".gitignore",
  "docs/private-eval-custody.md",
  "docs/STATUS.md",
  # The in-repo manifest is OPAQUE BY CONTRACT: counts, hashes, split metadata,
  # custody rules and the seal digest. It is asserted content-free by
  # test_in_repo_manifest_is_content_free below.
  "corpus/private_test_manifest.json",
  "substrate/private_eval.py",
  "tests/test_private_eval_tripwire.py",
  "tests/test_custody_audit.py",
  "tests/test_freeze_adversarial.py",
  "tests/test_splits.py",
  "scripts/verify_round0",
  "docs/verify-round0.md",
  "AGENTS.md",
}


def _is_exempt(rel_path: str) -> bool:
  return rel_path in NAME_EXEMPT_PATHS


def _walk_repo():
  for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS]
    for name in filenames:
      full = os.path.join(dirpath, name)
      rel = os.path.relpath(full, REPO_ROOT)
      if _is_exempt(rel):
        continue
      yield full, rel


class TestPrivateContentNotInRepo(unittest.TestCase):
  def test_no_private_eval_filenames_in_repo(self):
    offenders = []
    for _full, rel in _walk_repo():
      for pattern in PRIVATE_NAME_PATTERNS:
        if pattern.search(rel):
          offenders.append(rel)
          break
    self.assertEqual(
      offenders, [], f"private-eval filenames found inside repo: {offenders}"
    )

  def test_no_private_item_id_content_in_repo(self):
    """A staging file may not be a private item (qa-private-NN)."""
    offenders = []
    staging = os.path.join(REPO_ROOT, "staging")
    if not os.path.isdir(staging):
      return
    for name in os.listdir(staging):
      if not name.endswith(".json"):
        continue
      path = os.path.join(staging, name)
      with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
      if re.search(r"qa-private-\d+", raw):
        offenders.append(name)
      data = None
      try:
        data = json.loads(raw)
      except json.JSONDecodeError:
        continue
      items = data if isinstance(data, list) else [data]
      for item in items:
        if not isinstance(item, dict):
          continue
        if item.get("split") == "private_test":
          offenders.append(f"{name} (split=private_test)")
    self.assertEqual(
      offenders, [], f"private_test content inside repo staging: {offenders}"
    )

  def test_private_manifest_is_tracked_not_ignored(self):
    """The opaque manifest MUST be in version control.

    It carries the seal digest that binds the out-of-repo private test to this
    repository. If it is git-ignored, a fresh clone cannot verify the private
    boundary at all, and the freeze gate silently loses its private half. An
    independent review found exactly this: .gitignore's `*private_test*.json`
    pattern swallowed the manifest, so it was untracked and never committed.
    """
    import subprocess

    manifest = "corpus/private_test_manifest.json"
    if not os.path.isfile(os.path.join(REPO_ROOT, manifest)):
      self.skipTest("in-repo private manifest not created")

    # The verifier runs the suite against a git-less copy of the tree, where
    # "is it tracked?" has no answer. Skip rather than fail there; the real
    # checkout runs this.
    inside = subprocess.run(
      ["git", "rev-parse", "--is-inside-work-tree"],
      cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if inside.returncode != 0 or inside.stdout.strip() != "true":
      self.skipTest("not inside a git work tree (sandboxed copy)")

    ignored = subprocess.run(
      ["git", "check-ignore", "-q", manifest],
      cwd=REPO_ROOT, capture_output=True,
    )
    self.assertNotEqual(ignored.returncode, 0,
                        f"{manifest} is git-ignored; a clone cannot verify the "
                        "private seal")

    tracked = subprocess.run(
      ["git", "ls-files", "--error-unmatch", manifest],
      cwd=REPO_ROOT, capture_output=True, text=True,
    )
    self.assertEqual(tracked.returncode, 0,
                     f"{manifest} is not tracked by git; it must be committed")

  def test_in_repo_manifest_is_content_free(self):
    """corpus/private_test_manifest.json carries hashes, never content.

    The manifest is the one private-test artifact allowed inside the repo, and
    it is only legitimate because it is opaque. This test fails if a private
    question id, answer, support atom, source id or label ever leaks into it.
    """
    path = os.path.join(REPO_ROOT, "corpus", "private_test_manifest.json")
    if not os.path.isfile(path):
      self.skipTest("in-repo private manifest not yet created")
    with open(path, "r", encoding="utf-8") as fh:
      data = json.load(fh)

    def walk_keys(obj, trail=""):
      if isinstance(obj, dict):
        for k, v in obj.items():
          yield from walk_keys(v, f"{trail}.{k}")
      elif isinstance(obj, list):
        for i, v in enumerate(obj):
          yield from walk_keys(v, f"{trail}[{i}]")
      else:
        yield trail, obj

    forbidden_keys = (
      "question", "answer", "sufficient_set", "support_atom", "atom",
      "label", "evidence_text", "hard_negative", "readings",
    )
    forbidden_values = ("qa-private-", "answer_text", "sufficient_sets")
    for trail, value in walk_keys(data):
      leaf = trail.rsplit(".", 1)[-1].lower()
      for bad in forbidden_keys:
        if leaf == bad or leaf.startswith(bad + "["):
          self.fail(f"private content key in in-repo manifest: {trail}")
      if isinstance(value, str):
        for bad in forbidden_values:
          self.assertNotIn(
            bad, value,
            f"private content fragment {bad!r} in manifest at {trail}",
          )

    # It MUST still carry the seal + counts, or it is not doing its job.
    self.assertIn("seal_sha256", data)
    self.assertIn("counts", data)
    self.assertGreater(data["counts"]["total"], 0)

  def test_private_dir_is_outside_repo(self):
    self.assertNotEqual(
      os.path.abspath(private_dir()),
      os.path.abspath(REPO_ROOT),
      "LMR_PRIVATE_EVAL_DIR must not be the repository root",
    )
    assert_private_dir_outside_repo()

  def test_assert_fails_when_private_dir_points_inside_repo(self):
    with tempfile.TemporaryDirectory() as tmp:
      with mock.patch.dict(
        os.environ, {"LMR_PRIVATE_EVAL_DIR": os.path.join(tmp, "staging")}
      ):
        # tmp is not the repo, so this must NOT raise.
        assert_private_dir_outside_repo()
      with mock.patch.dict(
        os.environ, {"LMR_PRIVATE_EVAL_DIR": os.path.join(REPO_ROOT, "staging")}
      ):
        with self.assertRaises(PrivateEvalError):
          assert_private_dir_outside_repo()
      with mock.patch.dict(
        os.environ, {"LMR_PRIVATE_EVAL_DIR": REPO_ROOT}
      ):
        with self.assertRaises(PrivateEvalError):
          assert_private_dir_outside_repo()


class TestFailClosed(unittest.TestCase):
  def test_verify_seal_raises_when_absent(self):
    with tempfile.TemporaryDirectory() as tmp:
      with mock.patch.dict(os.environ, {"LMR_PRIVATE_EVAL_DIR": tmp}):
        self.assertIsNone(seal_digest())
        with self.assertRaises(PrivateEvalError) as cm:
          verify_seal()
        self.assertIn("not sealed", str(cm.exception))

  def test_verify_seal_detects_mismatch(self):
    with tempfile.TemporaryDirectory() as tmp:
      with open(os.path.join(tmp, "seal.sha256"), "w", encoding="utf-8") as fh:
        fh.write("deadbeef\n")
      with mock.patch.dict(os.environ, {"LMR_PRIVATE_EVAL_DIR": tmp}):
        with self.assertRaises(PrivateEvalError) as cm:
          verify_seal("cafebabe")
        self.assertIn("mismatch", str(cm.exception))
        self.assertTrue(verify_seal("deadbeef"))

  def test_counts_never_fabricate(self):
    with tempfile.TemporaryDirectory() as tmp:
      with mock.patch.dict(os.environ, {"LMR_PRIVATE_EVAL_DIR": tmp}):
        result = counts()
        self.assertFalse(result["present"])
        self.assertEqual(result["counts"], {})
        self.assertIsNone(result["seal_sha256"])
        self.assertIsNone(result["questions_sha256"])

  def test_leakage_gate_fails_closed_without_seal(self):
    with tempfile.TemporaryDirectory() as tmp:
      with mock.patch.dict(os.environ, {"LMR_PRIVATE_EVAL_DIR": tmp}):
        verdict = check_training_overlap(["synthetic-1", "synthetic-2"])
        self.assertIsInstance(verdict, LeakageVerdict)
        self.assertEqual(verdict.verdict, "REJECT")
        self.assertIn("cannot evaluate leakage", verdict.reason)
        self.assertEqual(verdict.flagged_ids, [])

  def test_leakage_verdict_exposes_only_the_three_allowed_fields(self):
    """The verdict carries no channel for private content.

    The guarantee is STRUCTURAL: the dataclass has exactly three fields and
    no field can hold a private question id, text, answer, or evidence. The
    caller-visible payload is therefore limited to a verdict, a reason, and
    synthetic training ids.
    """
    import dataclasses

    fields = {f.name for f in dataclasses.fields(LeakageVerdict)}
    self.assertEqual(fields, {"verdict", "reason", "flagged_ids"})
    with tempfile.TemporaryDirectory() as tmp:
      with mock.patch.dict(os.environ, {"LMR_PRIVATE_EVAL_DIR": tmp}):
        payload = check_training_overlap(["synthetic-1"]).to_dict()
    self.assertEqual(sorted(payload), ["flagged_ids", "reason", "verdict"])
    self.assertIn(payload["verdict"], ("PASS", "REJECT"))


if __name__ == "__main__":
  unittest.main()
