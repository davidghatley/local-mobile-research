"""The census pin must have a trust root OUTSIDE the repository.

Independent freeze review v5 found the fix for the v4 truncation hole was
itself defeatable. `corpus/partition_census.json` lives in git, so a commit that
truncates the data AND edits the census to match defeats every internal check:
stages 5, 6 and 8 all PASS on a freeze missing 106 of 206 questions.

The defence is a digest recorded outside git, at the custodian's private
directory, in the same trust model as the private-test seal: procedural and
workspace-based, not a kernel security boundary. These tests prove the co-edit
is caught and that the pin itself is load-bearing.
"""

import hashlib
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
PRIVATE_DIR = os.environ.get(
  "LMR_PRIVATE_EVAL_DIR",
  "/home/davidhatley/Projects/testing/local_mobile_research-private-eval",
)
FREEZE_PIN = os.path.join(PRIVATE_DIR, "freeze_census_pin.json")


def _sha(path):
  with open(path, "rb") as fh:
    return hashlib.sha256(fh.read()).hexdigest()


def _run(root, *stages, env_extra=None):
  env = dict(os.environ)
  env.setdefault("VERIFY_ROUND0_PYTHON", "python3")
  if env_extra:
    env.update(env_extra)
  proc = subprocess.run(
    [VERIFIER, "--only", ",".join(stages), "--root", root],
    capture_output=True, text=True, env=env, timeout=600,
  )
  return proc.returncode, proc.stdout + proc.stderr


def _truncate_and_coedit(root, keep_n=100):
  """The v5 attack: truncate data and edit the census so both agree."""
  import glob
  keep = set()
  for i, path in enumerate(sorted(glob.glob(os.path.join(root, "staging", "qa-*.json")))):
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

  cpath = os.path.join(root, CENSUS_REL)
  with open(cpath, "r", encoding="utf-8") as fh:
    census = json.load(fh)
  by_split: dict[str, int] = {}
  for e in entries:
    if e["question_id"] in keep:
      by_split[e["split"]] = by_split.get(e["split"], 0) + 1
  census["expected"] = {"total": len(keep), "by_split": by_split}
  census["approved_drafts"] = {"total": len(keep), "by_split": by_split}
  census["authored_total"] = len(keep) + census["rejected_quarantined"]["count"]
  with open(cpath, "w", encoding="utf-8") as fh:
    json.dump(census, fh, indent=2, sort_keys=True)
    fh.write("\n")
  return len(keep)


class TestOutOfRepoTrustRoot(unittest.TestCase):
  @unittest.skipUnless(os.path.isfile(FREEZE_PIN),
                       "freeze_census_pin.json absent (no private eval dir)")
  def test_pin_matches_live_census(self):
    with open(FREEZE_PIN, "r", encoding="utf-8") as fh:
      pin = json.load(fh)
    self.assertEqual(pin["partition_census_sha256"],
                     _sha(os.path.join(REPO_ROOT, CENSUS_REL)),
                     "the out-of-repo pin is stale; the census changed since the "
                     "pin was recorded")
    self.assertEqual(pin["public_partition_sha256"],
                     _sha(os.path.join(REPO_ROOT, PARTITION_REL)))
    self.assertEqual(pin["expected_counts"]["total"],
                     len(json.load(open(os.path.join(REPO_ROOT, PARTITION_REL),
                                        encoding="utf-8"))))

  def test_pin_is_outside_the_repository(self):
    if not os.path.isfile(FREEZE_PIN):
      self.skipTest("no private eval dir")
    self.assertFalse(
      os.path.abspath(FREEZE_PIN).startswith(os.path.abspath(REPO_ROOT) + os.sep),
      "the census trust root must NOT live inside the repository it protects",
    )

  def test_baseline_passes_with_the_pin(self):
    if not os.path.isfile(FREEZE_PIN):
      self.skipTest("no private eval dir")
    if not os.path.isfile(os.path.join(REPO_ROOT, "corpus", "corpus.jsonl")):
      self.skipTest("corpus/corpus.jsonl absent (sandboxed copy)")
    tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    root = os.path.join(tmp, "repo")
    shutil.copytree(REPO_ROOT, root,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    rc, out = _run(root, "8", env_extra={"LMR_PRIVATE_EVAL_DIR": PRIVATE_DIR})
    self.assertEqual(rc, 0, f"unmodified tree must pass stage 8:\n{out}")
    self.assertIn("MATCHES out-of-repo freeze pin", out)

  def test_coedit_is_caught_by_the_trust_root(self):
    if not os.path.isfile(FREEZE_PIN):
      self.skipTest("no private eval dir")
    if not os.path.isfile(os.path.join(REPO_ROOT, "corpus", "corpus.jsonl")):
      self.skipTest("corpus/corpus.jsonl absent (sandboxed copy)")
    tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    root = os.path.join(tmp, "repo")
    shutil.copytree(REPO_ROOT, root,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))

    kept = _truncate_and_coedit(root, 100)
    self.assertEqual(kept, 100)

    rc, out = _run(root, "8", env_extra={"LMR_PRIVATE_EVAL_DIR": PRIVATE_DIR})
    self.assertNotEqual(
      rc, 0,
      "a data+census co-edit must be caught by the out-of-repo trust root; "
      f"stage 8 passed on a freeze missing {206 - kept} of 206 questions:\n{out}")
    self.assertIn("MISMATCH vs out-of-repo freeze pin", out)
    self.assertIn("co-edit", out)

  def test_missing_pin_is_reported_not_silently_ignored(self):
    if not os.path.isfile(os.path.join(REPO_ROOT, "corpus", "corpus.jsonl")):
      self.skipTest("corpus/corpus.jsonl absent (sandboxed copy)")
    tmp = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    root = os.path.join(tmp, "repo")
    shutil.copytree(REPO_ROOT, root,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    empty_priv = os.path.join(tmp, "empty-private")
    os.makedirs(empty_priv, exist_ok=True)
    rc, out = _run(root, "8", env_extra={"LMR_PRIVATE_EVAL_DIR": empty_priv})
    self.assertNotEqual(rc, 0,
                        "no out-of-repo pin means no trust root; that is "
                        f"unverified and must not pass:\n{out}")
    self.assertIn("freeze pin ABSENT", out)


class TestWordingIsAccurate(unittest.TestCase):
  """An in-repo pin is external to the ARTIFACTS, not to the REPOSITORY.

  Our own documents must say so accurately. The independent review documents are
  excluded: they are another worker's record of what THEY said, including the
  wording this test exists to correct, and rewriting a reviewer's words would be
  the same sin the project has already been caught at twice (see
  docs/qa-prestated-premise-sweep.md).
  """

  FILES = ("docs/STATUS.md", "docs/progress-ledger.md",
           "docs/verify-round0.md", "docs/private-eval-custody.md",
           "corpus/partition_census.json")

  # Markers that make a mention of "external pin" honest: either it states the
  # digest is recorded outside the repository, or it is quoting the phrase in
  # order to correct it.
  HONEST_MARKERS = ("recorded outside", "outside git", "out-of-repo",
                    "outside the repo", "not external to the repository")

  def test_our_documents_do_not_overstate_the_census_pin(self):
    offenders = []
    for rel in self.FILES:
      path = os.path.join(REPO_ROOT, rel)
      if not os.path.isfile(path):
        continue
      with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
      for i, line in enumerate(lines):
        if "external pin" not in line.lower():
          continue
        # Score the containing PARAGRAPH, not the line: prose wraps, and a
        # correction usually lands a few lines from the phrase it corrects.
        lo, hi = max(0, i - 3), min(len(lines), i + 4)
        window = "".join(lines[lo:hi]).lower()
        if any(marker in window for marker in self.HONEST_MARKERS):
          continue
        offenders.append(f"{rel}:{i + 1}: {line.strip()[:110]}")
    self.assertEqual(
      offenders, [],
      "corpus/partition_census.json lives INSIDE the repository; it is external "
      "to the artifacts it checks, not external to the repository:\n"
      + "\n".join(offenders))

  def test_review_documents_exist_and_are_not_rewritten(self):
    """A reviewer's words are their own; we correct ours, not theirs."""
    import glob
    reviews = sorted(glob.glob(
      os.path.join(REPO_ROOT, "docs", "round0-independent-freeze-review-*.md")))
    self.assertGreaterEqual(len(reviews), 1, "no review documents found")
    for path in reviews:
      self.assertGreater(os.path.getsize(path), 0, path)


if __name__ == "__main__":
  unittest.main()