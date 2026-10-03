"""A consistent truncation must not pass the freeze gate.

Independent review v4 found the worst class of freeze hole: delete staging
drafts AND the matching partition entries together, and every internal
cross-check stays self-consistent. Stages 5, 6 and 8 all reported PASS on half
a freeze. The only defence is a pin held OUTSIDE the artifacts it checks:
corpus/partition_census.json.

Each test here constructs the truncation on a throwaway copy and asserts the
gate catches it. If these tests ever pass on a truncated tree, the census pin
has stopped biting.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(REPO_ROOT, "scripts", "verify_round0")
CENSUS_REL = "corpus/partition_census.json"
PARTITION_REL = "corpus/questions.json"


def _init_git(root):
    """Make a throwaway copy a real git checkout.

    A durable freeze record must bind the exact commit, and validate_freeze
    fails closed when it cannot. Copying the repo without .git therefore
    produces a tree that can never be frozen - correct behaviour, but useless
    for a test that is checking something else. Initialising a throwaway repo
    keeps these tests exercising a realistic freeze environment without
    shipping .git around.
    """
    import subprocess
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
    })
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "throwaway freeze fixture"],
    ):
        subprocess.run(cmd, cwd=root, env=env, capture_output=True, check=True)


def _copy_repo(tmp, name="repo"):
  dest = os.path.join(tmp, name)
  shutil.copytree(REPO_ROOT, dest,
                  ignore=shutil.ignore_patterns(".git", "__pycache__"))
  _init_git(dest)
  return dest


# The out-of-repo census trust root is reached ONLY through the environment.
#
# There is deliberately NO hardcoded developer path fallback here. A test that
# quietly falls back to /home/<someone>/... passes on that machine and fails on
# every other host, which is exactly the class of bug that left GitHub Actions
# red. If the variable is unset - as on a clean clone and a CI runner - the
# test SKIPS, because the trust root's entire purpose is to live outside the
# repository.
PRIVATE_DIR = os.environ.get("LMR_PRIVATE_EVAL_DIR", "")
CENSUS_PIN = os.path.join(PRIVATE_DIR, "freeze_census_pin.json")


def _require_census_pin():
  """Stage 8 requires the out-of-repo census trust root.

  A clean clone and a CI runner have no private evaluation directory, so these
  tests cannot run there. Skipping is the honest outcome: the census pin's
  whole purpose is to live outside the repository, so its absence off the
  freeze host is expected, not a defect.
  """
  if not os.path.isfile(CENSUS_PIN):
    raise unittest.SkipTest("no out-of-repo census trust root on this host (CI)")


def _require_corpus():
  """Stages 5 and 8 need the git-ignored 42 MB corpus artifact.

  scripts/verify_round0 runs this suite against a git-less sandbox copy where
  that artifact is absent by design. Skip there rather than fail: the point of
  these tests is the census pin, not the corpus.
  """
  if not os.path.isfile(os.path.join(REPO_ROOT, "corpus", "corpus.jsonl")):
    raise unittest.SkipTest("corpus/corpus.jsonl absent (sandboxed copy)")


# The out-of-repo census trust root is reached ONLY through the environment.
#
# There is deliberately NO hardcoded developer path fallback here. A test that
# quietly falls back to /home/<someone>/... passes on that machine and fails on
# every other host, which is exactly the class of bug that left GitHub Actions
# red. If the variable is unset - as on a clean clone and a CI runner - the
# test SKIPS, because the trust root's entire purpose is to live outside the
# repository.
PRIVATE_DIR = os.environ.get("LMR_PRIVATE_EVAL_DIR", "")


def _run(root, *stages, env_extra=None):
  env = dict(os.environ)
  env.setdefault("VERIFY_ROUND0_PYTHON", "python3")
  # Stage 8 requires the out-of-repo census trust root, so every invocation
  # here must be configured the way a real freeze run is.
  env.setdefault("LMR_PRIVATE_EVAL_DIR", PRIVATE_DIR)
  if env_extra:
    env.update(env_extra)
  proc = subprocess.run(
    [VERIFIER, "--only", ",".join(stages), "--root", root],
    capture_output=True, text=True, env=env, timeout=600,
  )
  return proc.returncode, proc.stdout + proc.stderr


def _truncate_consistently(root, keep_n):
  """Delete staging drafts and the matching partition entries TOGETHER."""
  import glob
  keep = set()
  drafts = sorted(glob.glob(os.path.join(root, "staging", "qa-*.json")))
  for i, path in enumerate(drafts):
    if i >= keep_n:
      os.remove(path)
    else:
      with open(path, "r", encoding="utf-8") as fh:
        keep.add(json.load(fh)["question_id"])
  ppath = os.path.join(root, PARTITION_REL)
  with open(ppath, "r", encoding="utf-8") as fh:
    entries = json.load(fh)
  with open(ppath, "w", encoding="utf-8") as fh:
    json.dump([e for e in entries if e["question_id"] in keep], fh,
              indent=2, sort_keys=True)
    fh.write("\n")
  return len(keep)


class TestCensusArtifact(unittest.TestCase):
  def test_census_exists_and_is_coherent(self):
    path = os.path.join(REPO_ROOT, CENSUS_REL)
    self.assertTrue(os.path.isfile(path), f"{CENSUS_REL} is required")
    with open(path, "r", encoding="utf-8") as fh:
      census = json.load(fh)
    exp = census["expected"]
    appr = census["approved_drafts"]
    rej = census["rejected_quarantined"]
    self.assertEqual(exp, appr, "expected and approved_drafts must agree")
    self.assertEqual(sum(exp["by_split"].values()), exp["total"])
    self.assertEqual(
      census["authored_total"], exp["total"] + rej["count"],
      "authored_total must equal published + rejected",
    )
    self.assertEqual(len(rej["ids"]), rej["count"])

  def test_census_matches_live_artifacts(self):
    with open(os.path.join(REPO_ROOT, CENSUS_REL), "r", encoding="utf-8") as fh:
      census = json.load(fh)
    with open(os.path.join(REPO_ROOT, PARTITION_REL), "r", encoding="utf-8") as fh:
      entries = json.load(fh)
    self.assertEqual(len(entries), census["expected"]["total"])
    counts: dict[str, int] = {}
    for e in entries:
      counts[e["split"]] = counts.get(e["split"], 0) + 1
    self.assertEqual(counts, census["expected"]["by_split"])
    self.assertEqual({e["question_id"] for e in entries} &
                     set(census["rejected_quarantined"]["ids"]), set())

  def test_census_is_tracked(self):
    if not os.path.isdir(os.path.join(REPO_ROOT, ".git")):
      self.skipTest("not a git checkout")
    rc = subprocess.run(["git", "ls-files", "--error-unmatch", CENSUS_REL],
                        cwd=REPO_ROOT, capture_output=True)
    self.assertEqual(rc.returncode, 0,
                     f"{CENSUS_REL} must be tracked; it is the only external "
                     "pin against a consistent truncation")


class TestConsistentTruncationIsCaught(unittest.TestCase):
  def setUp(self):
    _require_corpus()
    _require_census_pin()
    self.tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
    self.repo = _copy_repo(self.tmp)

  def test_baseline_full_subset_passes(self):
    rc, out = _run(self.repo, "5", "6", "8")
    self.assertEqual(rc, 0, f"untruncated tree must pass:\n{out}")

  def test_stage5_catches_consistent_truncation(self):
    _truncate_consistently(self.repo, 100)
    rc, out = _run(self.repo, "5")
    self.assertNotEqual(rc, 0, f"stage 5 must catch truncation:\n{out}")
    self.assertIn("census", out.lower())
    self.assertIn("truncation", out.lower())

  def test_stage6_catches_consistent_truncation(self):
    _truncate_consistently(self.repo, 100)
    rc, out = _run(self.repo, "6")
    self.assertNotEqual(rc, 0, f"stage 6 must catch truncation:\n{out}")
    self.assertIn("census", out.lower())
    self.assertIn("truncation", out.lower())

  def test_stage8_catches_consistent_truncation(self):
    _truncate_consistently(self.repo, 100)
    rc, out = _run(self.repo, "8")
    self.assertNotEqual(rc, 0, f"stage 8 must catch truncation:\n{out}")
    self.assertIn("census", out.lower())
    self.assertIn("truncation", out.lower())

  def test_missing_census_fails_closed(self):
    os.remove(os.path.join(self.repo, CENSUS_REL))
    for stage in ("5", "6", "8"):
      rc, out = _run(self.repo, stage)
      self.assertNotEqual(rc, 0,
                          f"stage {stage} must fail without the census pin:\n{out}")
      self.assertIn("census", out.lower())

  def test_inflated_census_fails_closed(self):
    path = os.path.join(self.repo, CENSUS_REL)
    with open(path, "r", encoding="utf-8") as fh:
      census = json.load(fh)
    census["expected"]["total"] = 9999
    census["approved_drafts"]["total"] = 9999
    with open(path, "w", encoding="utf-8") as fh:
      json.dump(census, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = _run(self.repo, "6")
    self.assertNotEqual(rc, 0, f"a wrong pin must fail:\n{out}")
    self.assertIn("census", out.lower())

  def test_rejected_id_reappearing_fails(self):
    path = os.path.join(self.repo, PARTITION_REL)
    with open(path, "r", encoding="utf-8") as fh:
      entries = json.load(fh)
    entries[0]["question_id"] = "qa-shadow-dev-84"
    with open(path, "w", encoding="utf-8") as fh:
      json.dump(entries, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = _run(self.repo, "6")
    self.assertNotEqual(rc, 0, f"a quarantined id must not reappear:\n{out}")
    self.assertIn("reject", out.lower())


if __name__ == "__main__":
  unittest.main()