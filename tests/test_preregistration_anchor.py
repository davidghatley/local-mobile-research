"""A preregistered anchor must be real, and must be enforced mechanically.

Independent freeze review v7 found that docs/scoring-protocol.md claimed
"FROZEN AT commit 88aa177" — a commit at which the file, and every file the
policy depends on, DID NOT EXIST. A preregistration anchored to a fiction
records nothing, and nothing stopped the fiction from being written in the
first place.

These tests make the anchor checkable rather than decorative: the cited commit
must exist, must be an ancestor of HEAD, and every artifact the policy depends
on must have been present at it.
"""

import json
import os
import re
import subprocess
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORING_DOC = os.path.join("docs", "scoring-protocol.md")
LEAKAGE_DOC = os.path.join("docs", "private-eval-custody.md")

# Files the scoring policy's preregistration depends on. If the policy is frozen
# before these exist, the freeze is fiction.
SCORING_DEPENDENTS = (
  "docs/scoring-protocol.md",
  "eval/answer_scoring.py",
  "tests/test_answer_scoring.py",
)


def _git(*args):
  return subprocess.run(["git", "-C", REPO_ROOT, *args],
                        capture_output=True, text=True)


def _require_history():
  """Skip when the checkout is shallow.

  `git cat-file -e <sha>:<path>` cannot see a commit the clone does not have, so
  a shallow clone would report every dependency as "missing" - a false failure
  that says nothing about the preregistration. Skipping is the honest outcome:
  the check is unverified here, not violated. The workflow sets
  fetch-depth: 0 so the check actually RUNS in CI rather than always skipping.
  """
  if not os.path.isdir(os.path.join(REPO_ROOT, ".git")):
    raise unittest.SkipTest("not a git checkout")
  r = _git("rev-parse", "--is-shallow-repository")
  if r.returncode == 0 and r.stdout.strip() == "true":
    raise unittest.SkipTest(
      "shallow clone: history needed to verify the preregistration anchor is "
      "not present (use fetch-depth: 0)")


def _commit_present(sha):
  return _git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0


def _anchor_from(doc_rel):
  path = os.path.join(REPO_ROOT, doc_rel)
  if not os.path.isfile(path):
    return None
  with open(path, "r", encoding="utf-8") as fh:
    m = re.search(r"\*\*FROZEN AT:\*\*\s*commit\s*`([0-9a-f]{40})`", fh.read())
  return m.group(1) if m else None


class TestScoringPreregistrationAnchor(unittest.TestCase):
  def setUp(self):
    if not os.path.isfile(os.path.join(REPO_ROOT, SCORING_DOC)):
      self.skipTest("scoring protocol absent")
    _require_history()

  def test_scoring_policy_carries_an_anchor(self):
    self.assertIsNotNone(_anchor_from(SCORING_DOC),
                         "the scoring policy must declare FROZEN AT commit")

  def test_anchor_commit_exists(self):
    sha = _anchor_from(SCORING_DOC)
    self.assertTrue(_commit_present(sha),
                    f"the FROZEN AT commit {sha} does not exist")

  def test_anchor_is_an_ancestor_of_head(self):
    sha = _anchor_from(SCORING_DOC)
    r = _git("merge-base", "--is-ancestor", sha, "HEAD")
    self.assertEqual(r.returncode, 0,
                     f"the FROZEN AT commit {sha} is not an ancestor of HEAD; a "
                     "preregistration cannot be anchored to a future or "
                     "divergent commit")

  def test_every_scoring_dependent_existed_at_the_anchor(self):
    """This is the check that caught the fiction.

    `git cat-file -e <sha>:<path>` fails when the file was not present at that
    commit, which is exactly what happened with 88aa177.
    """
    sha = _anchor_from(SCORING_DOC)
    missing = []
    for rel in SCORING_DEPENDENTS:
      r = _git("cat-file", "-e", f"{sha}:{rel}")
      if r.returncode != 0:
        missing.append(rel)
    self.assertEqual(missing, [],
                     f"the FROZEN AT commit {sha} does not contain "
                     f"{missing}; the preregistration is anchored to a commit "
                     "where its own artifacts did not exist")

  def test_anchor_is_not_the_pre_scoring_commit(self):
    """Regression pin for the specific fiction review v7 found.

    88aa177 predates the scoring protocol. If it ever reappears as the anchor,
    this test fails rather than letting the record look preregistered again.
    """
    sha = _anchor_from(SCORING_DOC)
    self.assertNotEqual(
      sha, "88aa1776eda01b87d014d235bbc84004d8dc7b78",
      "the scoring policy is anchored to a commit that predates the policy")


class TestJudgeModelIsNotFloatingSilently(unittest.TestCase):
  """A model id without a digest is not preregistration."""

  def test_unpinned_judge_is_declared_as_a_precondition(self):
    path = os.path.join(REPO_ROOT, SCORING_DOC)
    with open(path, "r", encoding="utf-8") as fh:
      text = fh.read()
    self.assertIn("flan-t5-large", text)
    self.assertTrue(
      "NOT YET PINNED" in text or "DIGEST" in text.upper(),
      "if the judge model carries no digest, the doc must say so loudly and "
      "make digest resolution a precondition, not leave a floating id looking "
      "like a pin")
    self.assertTrue(
      "BLOCKING-FOR-ROUND-1" in text,
      "an unpinned judge must be recorded as blocking for Round 1 use")


class TestRegimeBExclusionSupersetIsBytePinned(unittest.TestCase):
  """The list teams are told to exclude must be pinned, or it can be swapped.

  Review v7: corpus/regime_b_excluded_articles.json was not in
  corpus/build_manifest.json, so neither stage 4 nor the freeze inventory bound
  its bytes. An unpinned exclusion list can change between authoring and
  evaluation without any check noticing.
  """

  REL = "corpus/regime_b_excluded_articles.json"

  def setUp(self):
    rel = os.path.join(REPO_ROOT, "corpus", "build_manifest.json")
    if not os.path.isfile(rel):
      self.skipTest("build_manifest.json absent")
    with open(rel, "r", encoding="utf-8") as fh:
      self.manifest = json.load(fh)

  def test_exclusion_list_is_pinned(self):
    paths = {a.get("path") for a in self.manifest.get("artifacts", [])}
    self.assertIn(self.REL, paths,
                  f"{self.REL} must be byte-pinned in corpus/build_manifest.json")

  def test_pin_matches_the_bytes_on_disk(self):
    import hashlib
    entry = next(a for a in self.manifest["artifacts"] if a["path"] == self.REL)
    with open(os.path.join(REPO_ROOT, self.REL), "rb") as fh:
      raw = fh.read()
    self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
    self.assertEqual(len(raw), entry["bytes"])

  def test_query_module_agrees_with_the_pin(self):
    """The function teams actually call must read the pinned bytes."""
    import sys
    sys.path.insert(0, REPO_ROOT)
    from substrate.query import worker_regime_b_exclusions
    entry = next(a for a in self.manifest["artifacts"] if a["path"] == self.REL)
    got = worker_regime_b_exclusions()
    self.assertEqual(got.source_sha256, entry["sha256"],
                     "worker_regime_b_exclusions read bytes that differ from the "
                     "pinned artifact")


if __name__ == "__main__":
  unittest.main()