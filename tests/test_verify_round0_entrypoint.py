"""Entry-point tests for scripts/verify_round0.

These tests cover the VERIFIER HARNESS itself, not the substrate:

  * the entry point exists, is executable, and is a single command;
  * ``--help`` is SIDE-EFFECT FREE -- it must not run a stage, must not
    resolve the repository, and must not print a stage verdict. A --help that
    ran the whole suite has broken this project twice already, so this is
    asserted aggressively (verdict scan + scratch-dir scan + timing bound);
  * a deliberately corrupted ARTIFACT COPY fails with a non-zero exit and
    names the failing stage. The real repository is never mutated: the test
    copies the tree to a temp directory and corrupts only the copy;
  * ``--code-only`` runs the code-level portion with the freeze artifacts
    absent and prints an explicit "not a freeze pass" disclaimer;
  * the verifier never prints sealed label content and never mutates the tree.

RECURSION GUARD: this module runs the verifier, and the verifier runs
``python3 -m unittest discover -s tests`` (which discovers this module). The
verifier exports VERIFY_ROUND0_IN_VERIFIER=1 to every child it spawns; when
that marker is present the whole module skips, which breaks the cycle.

Runs with ``python3`` on any platform the verifier supports. stdlib only.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "verify_round0")

# RECURSION GUARD (module level).
# The verifier runs `python3 -m unittest discover -s tests`, which discovers
# this module, whose tests run the verifier. The verifier exports
# VERIFY_ROUND0_IN_VERIFIER=1 to every child it spawns, so when that marker is
# present we skip the whole module and the cycle is broken.
_IN_VERIFIER = os.environ.get("VERIFY_ROUND0_IN_VERIFIER") == "1"
_RECURSION_REASON = "running inside verify_round0; skipping to avoid recursion"

# Bulk, git-ignored, and irrelevant to harness behavior.
_COPY_EXCLUDE = shutil.ignore_patterns(
  ".git", "__pycache__", "*.pyc", "raw", "archive", "artifacts", "corpus.jsonl",
)

CORPUS_JSONL = os.path.join("corpus", "corpus.jsonl")


def setUpModule():
  """Skip this whole module when the verifier is driving the suite.

  unittest treats a SkipTest raised from setUpModule as "skip the entire
  module", which is exactly the granularity needed to break the cycle.
  """
  if _IN_VERIFIER:
    raise unittest.SkipTest(_RECURSION_REASON)


def run_verifier(*args, cwd=None, env=None, timeout=600):
  """Run the verifier as a subprocess. Returns (rc, stdout+stderr)."""
  child_env = dict(os.environ)
  # Break the recursion cycle: the verifier's own suite run must not re-enter.
  child_env["VERIFY_ROUND0_IN_VERIFIER"] = "1"
  if env:
    child_env.update(env)
  proc = subprocess.run(
    [SCRIPT, *args],
    cwd=cwd or ROOT,
    env=child_env,
    capture_output=True,
    text=True,
    timeout=timeout,
  )
  return proc.returncode, proc.stdout + proc.stderr


def copy_tree(dest, with_corpus=False):
  """Copy the repository into dest WITHOUT git-ignored bulk artifacts.

  with_corpus=True additionally exposes corpus/corpus.jsonl (42 MB) through a
  symlink to the real file so hash recomputation can run. It is a symlink, so
  the verifier cannot mutate the real corpus through the copy.
  """
  shutil.copytree(ROOT, dest, ignore=_COPY_EXCLUDE, symlinks=True,
                  ignore_dangling_symlinks=True)
  if with_corpus:
    src = os.path.join(ROOT, CORPUS_JSONL)
    link = os.path.join(dest, CORPUS_JSONL)
    if os.path.isfile(src):
      os.symlink(src, link)
  return dest


class TestEntryPointBasics(unittest.TestCase):
  def test_entry_point_exists(self):
    self.assertTrue(os.path.isfile(SCRIPT),
                    "scripts/verify_round0 must exist: %s" % SCRIPT)

  def test_entry_point_is_executable(self):
    self.assertTrue(os.access(SCRIPT, os.X_OK),
                    "scripts/verify_round0 must be executable (chmod +x)")

  def test_entry_point_is_a_single_command_with_no_extension(self):
    # The brief pins the filename exactly. A stray .py or .sh would mean two
    # entry points and ambiguity about which one CI runs.
    self.assertEqual(os.path.basename(SCRIPT), "verify_round0")
    self.assertTrue(SCRIPT.endswith(os.path.join("scripts", "verify_round0")))

  def test_entry_point_has_a_shebang(self):
    with open(SCRIPT, "r", encoding="utf-8") as fh:
      first = fh.readline().strip()
    self.assertTrue(first.startswith("#!"),
                    "entry point needs a shebang so ./scripts/verify_round0 works")

  def test_entry_point_is_posix_ish_bash(self):
    with open(SCRIPT, "r", encoding="utf-8") as fh:
      src = fh.read()
    self.assertTrue(src.startswith("#!/usr/bin/env bash"),
                    "the entry point must be a POSIX-ish bash script")

  def test_rejects_unknown_argument(self):
    rc, out = run_verifier("--definitely-not-a-flag")
    self.assertEqual(rc, 2,
                     "an unknown flag must be a usage error, not a run:\n%s" % out)

  def test_rejects_bad_only_id(self):
    rc, out = run_verifier("--only", "42")
    self.assertEqual(rc, 2,
                     "an out-of-range stage id must be a usage error:\n%s" % out)


class TestHelpIsSideEffectFree(unittest.TestCase):
  """--help must not run the suite.

  This is a regression test for a bug that occurred TWICE in this project:
  a --help implementation that ran the whole verification suite.
  """

  def test_help_exits_zero(self):
    rc, out = run_verifier("--help")
    self.assertEqual(rc, 0, "--help must exit 0:\n%s" % out)

  def test_help_short_flag_exits_zero(self):
    rc, out = run_verifier("-h")
    self.assertEqual(rc, 0, "-h must exit 0:\n%s" % out)

  def test_help_prints_usage(self):
    rc, out = run_verifier("--help")
    self.assertIn("usage: scripts/verify_round0", out)
    self.assertIn("--code-only", out)

  def test_help_prints_no_run_sections(self):
    # The words PASS/FAIL legitimately appear in --help prose (they document
    # exit codes), so assert on the SHAPE of a real run, not on bare words.
    rc, out = run_verifier("--help")
    for marker in ("STAGE ", "SUMMARY", "RESULT:", "NOT VERIFIED"):
      self.assertNotIn(marker, out,
                       "--help printed %r; it ran a stage:\n%s" % (marker, out))
    self.assertIsNone(re.search(r"\[\d/9\]", out),
                      "--help printed a stage banner; it ran a stage:\n%s" % out)

  def test_help_prints_no_stage_verdict_line(self):
    # A real run always emits a "STAGE <n> <name>: <VERDICT>" line.
    rc, out = run_verifier("--help")
    for line in out.splitlines():
      self.assertFalse(
        line.startswith("STAGE ") and line.rstrip().endswith(("PASS", "FAIL", "SKIP")),
        "--help printed a stage verdict line %r" % line)

  def test_help_does_not_resolve_the_repository(self):
    # --help must short-circuit BEFORE the root check. If it resolved the
    # root, this bogus path would produce exit 2 instead of 0.
    rc, out = run_verifier("--help", "--root", "/nonexistent/definitely/not/a/repo")
    self.assertEqual(rc, 0,
                     "--help must not resolve/validate the repository root:\n%s" % out)

  def test_help_does_not_run_with_a_hostile_environment(self):
    # The verifier refuses to run under custodian mode. --help must still
    # work, proving the guard is evaluated after argument parsing.
    rc, out = run_verifier("--help", env={"HELDOUT_CUSTODIAN_MODE": "benchmark"})
    self.assertEqual(rc, 0,
                     "--help must work even when the run guard would block:\n%s" % out)

  def test_help_leaves_no_scratch_directory(self):
    tmpdir = tempfile.mkdtemp(prefix="verify-help-")
    try:
      rc, out = run_verifier("--help", env={"TMPDIR": tmpdir})
      self.assertEqual(rc, 0)
      leftovers = os.listdir(tmpdir)
      self.assertEqual(leftovers, [],
                       "--help must not create scratch files; found %r" % leftovers)
    finally:
      shutil.rmtree(tmpdir, ignore_errors=True)

  def test_help_does_not_write_into_the_working_directory(self):
    probe = os.path.join(tempfile.mkdtemp(prefix="verify-help-probe-"), "probe")
    os.makedirs(probe)
    try:
      rc, out = run_verifier("--help", cwd=probe)
      self.assertEqual(rc, 0)
      self.assertEqual(os.listdir(probe), [],
                       "--help must not write into the working directory")
    finally:
      shutil.rmtree(os.path.dirname(probe), ignore_errors=True)

  def test_help_is_fast(self):
    # Running the three test suites takes seconds. A --help that ran them
    # would blow past this bound comfortably.
    start = time.monotonic()
    rc, out = run_verifier("--help")
    elapsed = time.monotonic() - start
    self.assertEqual(rc, 0)
    self.assertLess(elapsed, 5.0,
                    "--help took %.1fs; it appears to run the suite" % elapsed)


class TestCorruptedArtifactFailsLoudly(unittest.TestCase):
  """A corrupted artifact COPY must fail non-zero and name the stage.

  The real repository is NEVER mutated. Each test gets its OWN temp copy,
  because a corruption must not leak into a sibling test (unittest orders
  tests alphabetically, which would otherwise reorder the checks silently).
  The corpus JSONL is exposed via a symlink so hash recomputation can run;
  the verifier only ever reads it.
  """

  def setUp(self):
    self.tmp = tempfile.mkdtemp(prefix="verify-round0-corrupt-")
    self.addCleanup(shutil.rmtree, self.tmp, True)
    self.copy_root = copy_tree(os.path.join(self.tmp, "repo"), with_corpus=True)

  def test_uncorrupted_copy_passes_the_corpus_hash_stage(self):
    # Control: an untouched copy must PASS. Without this, the tests below
    # could "pass" merely because the stage always fails.
    rc, out = run_verifier("--only", "4", "--root", self.copy_root)
    self.assertIn("STAGE 4 corpus-hash: PASS", out,
                  "the control copy should pass stage 4:\n%s" % out)
    self.assertEqual(rc, 0, "the control copy should exit 0:\n%s" % out)

  def test_corrupt_provenance_hash_fails_and_names_stage(self):
    # Flip one hex digit of the recorded canonical corpus hash. The corpus-hash
    # stage recomputes from corpus.jsonl and must notice.
    target = os.path.join(self.copy_root, "corpus", "provenance.json")
    self.assertTrue(os.path.isfile(target),
                    "test fixture expects corpus/provenance.json to exist")
    with open(target, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    original = data["corpus_hash_sha256"]
    corrupted = ("0" if original[0] != "0" else "1") + original[1:]
    self.assertNotEqual(corrupted, original, "the corruption must be a real change")
    data["corpus_hash_sha256"] = corrupted
    with open(target, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")

    rc, out = run_verifier("--only", "4", "--root", self.copy_root)
    self.assertNotEqual(rc, 0,
                        "a corrupted provenance hash must exit non-zero:\n%s" % out)
    self.assertIn("STAGE 4 corpus-hash: FAIL", out,
                  "the failing stage must be named and reported FAIL:\n%s" % out)
    self.assertIn("MISMATCH", out,
                  "the mismatch must be reported explicitly:\n%s" % out)
    self.assertIn("corpus_hash_sha256", out,
                  "the mismatching field must be named:\n%s" % out)

  def test_corrupt_split_map_fails_the_corpus_hash_stage(self):
    # Corrupt a different pinned artifact, proving detection is not specific
    # to one file.
    target = os.path.join(self.copy_root, "corpus", "split_map.json")
    with open(target, "r", encoding="utf-8") as fh:
      text = fh.read()
    self.assertIn('"seed"', text, "split_map fixture should contain a seed key")
    with open(target, "w", encoding="utf-8") as fh:
      fh.write(text.replace('"seed"', '"seedX"', 1))
    rc, out = run_verifier("--only", "4", "--root", self.copy_root)
    self.assertNotEqual(rc, 0,
                        "a corrupted split map must exit non-zero:\n%s" % out)
    self.assertIn("STAGE 4 corpus-hash: FAIL", out,
                  "the stage must be named and reported FAIL:\n%s" % out)

  def test_corrupt_generator_config_fails_the_generator_pin_stage(self):
    # Corrupt the pinned prompt hash; the generator-pin stage compares it
    # against the substrate PROMPT_HASH and must reject it.
    target = os.path.join(self.copy_root, "corpus", "generator_config.json")
    with open(target, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    data["prompt_hash"] = "0" * 64
    with open(target, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = run_verifier("--only", "7", "--root", self.copy_root)
    self.assertNotEqual(rc, 0,
                        "a corrupted prompt hash must exit non-zero:\n%s" % out)
    self.assertIn("STAGE 7 generator-pin: FAIL", out,
                  "the stage must be named and reported FAIL:\n%s" % out)
    self.assertIn("MISMATCH", out,
                  "the mismatch must be reported explicitly:\n%s" % out)

  def test_missing_corpus_artifact_fails_in_full_mode(self):
    # A copy WITHOUT the corpus JSONL must FAIL in full mode, not quietly
    # skip: unverified is not frozen.
    bare = copy_tree(os.path.join(self.tmp, "bare"), with_corpus=False)
    rc, out = run_verifier("--only", "4", "--root", bare)
    self.assertNotEqual(rc, 0,
                        "an absent load-bearing artifact must fail:\n%s" % out)
    self.assertIn("artifact absent", out,
                  "the absent artifact must be named:\n%s" % out)
    self.assertIn("corpus.jsonl", out,
                  "the absent artifact path must be named:\n%s" % out)

  def test_verifier_does_not_mutate_the_repository_tree(self):
    def fingerprint(base):
      seen = {}
      for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", ".git", "raw", "archive")]
        for name in filenames:
          if name.endswith(".pyc"):
            continue
          full = os.path.join(dirpath, name)
          try:
            st = os.stat(full)
          except OSError:
            continue
          seen[os.path.relpath(full, base)] = (st.st_size, int(st.st_mtime))
      return seen

    with tempfile.TemporaryDirectory(prefix="verify-readonly-") as tmp:
      copy_root = copy_tree(os.path.join(tmp, "repo"))
      before = fingerprint(copy_root)
      self.assertTrue(before, "the copy produced no files")
      run_verifier("--code-only", "--only", "9", "--root", copy_root)
      after = fingerprint(copy_root)
      self.assertEqual(sorted(before), sorted(after),
                       "the verifier must not create or delete files in the tree")
      for rel in sorted(before):
        if rel == os.path.join("scripts", "verify_round0"):
          # Reading the entry point updates atime only; size/mtime are stable.
          continue
        self.assertEqual(before[rel], after[rel],
                         "the verifier must not modify %s" % rel)


class TestCodeOnlyMode(unittest.TestCase):
  """--code-only must run without the freeze artifacts and say so loudly."""

  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp(prefix="verify-round0-codeonly-")
    cls.copy_root = copy_tree(os.path.join(cls.tmp, "repo"))

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp, ignore_errors=True)

  def test_code_only_runs_with_freeze_artifacts_absent(self):
    # The copy has no corpus/questions.json and no sealed labels, exactly like
    # the pre-freeze repository. --code-only must still get through the
    # code-level portion.
    self.assertFalse(os.path.exists(
      os.path.join(self.copy_root, "corpus", "questions.json")))
    self.assertFalse(os.path.exists(
      os.path.join(self.copy_root, "corpus", "heldout_labels.sealed.json")))

    rc, out = run_verifier("--code-only", "--root", self.copy_root)
    self.assertIn(rc, (0, 1),
                  "--code-only must exit 0 or 1, never crash with 2:\n%s" % out)
    self.assertNotIn("Traceback", out,
                     "--code-only must not crash:\n%s" % out)

  def test_code_only_prints_not_a_freeze_pass(self):
    rc, out = run_verifier("--code-only", "--root", self.copy_root)
    self.assertIn("THIS IS NOT A FREEZE PASS", out,
                  "--code-only must print its not-a-freeze-pass banner:\n%s" % out)

  def test_code_only_skips_the_freeze_gated_stages(self):
    rc, out = run_verifier("--code-only", "--root", self.copy_root)
    self.assertNotIn("[6/9]", out,
                     "--code-only must not run stage 6 (question/label partition)")
    self.assertNotIn("[8/9]", out,
                     "--code-only must not run stage 8 (freeze manifest)")

  def test_code_only_lists_what_it_did_not_verify(self):
    rc, out = run_verifier("--code-only", "--root", self.copy_root)
    self.assertIn("NOT VERIFIED", out,
                  "--code-only must enumerate unverified checks:\n%s" % out)

  def test_code_only_never_claims_a_freeze_pass(self):
    rc, out = run_verifier("--code-only", "--root", self.copy_root)
    for forbidden in ("RESULT: all load-bearing stages PASS.",
                      "freeze granted", "ROUND 0 IS FROZEN"):
      self.assertNotIn(forbidden, out,
                       "--code-only must not claim a freeze pass: %r" % forbidden)
    self.assertIn("RESULT: code-level checks completed (NOT a freeze pass).", out,
                  "--code-only must state its result explicitly:\n%s" % out)

  def test_code_only_disclaims_semantic_qa(self):
    rc, out = run_verifier("--code-only", "--root", self.copy_root)
    self.assertIn("does NOT verify semantic QA correctness", out,
                  "every run must state the semantic-QA limit:\n%s" % out)

  def test_full_mode_runs_the_freeze_gated_stages(self):
    rc, out = run_verifier("--root", self.copy_root)
    self.assertIn("[6/9]", out,
                  "a full run must execute stage 6:\n%s" % out[:2000])
    self.assertIn("[8/9]", out,
                  "a full run must execute stage 8:\n%s" % out[:2000])

  def test_full_mode_fails_when_freeze_artifacts_are_missing(self):
    rc, out = run_verifier("--root", self.copy_root)
    self.assertNotEqual(rc, 0,
                        "a full run must fail while freeze artifacts are absent:\n%s" % out)


class TestSemanticQAIsNeverCertified(unittest.TestCase):
  """The verifier must never print a PASS implying semantic QA correctness."""

  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp(prefix="verify-round0-semantics-")
    cls.copy_root = copy_tree(os.path.join(cls.tmp, "repo"))

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp, ignore_errors=True)

  def test_output_states_the_semantic_qa_limit(self):
    rc, out = run_verifier("--code-only", "--only", "5", "--root", self.copy_root)
    self.assertIn("does NOT verify semantic QA correctness", out,
                  "the verifier must state its semantic-QA limit:\n%s" % out)
    self.assertIn("cannot", out.lower())

  def test_output_names_the_undecidable_properties(self):
    rc, out = run_verifier("--code-only", "--only", "5", "--root", self.copy_root)
    for phrase in ("answerable", "minimal", "multi-hop", "label"):
      self.assertIn(phrase, out.lower(),
                    "the disclaimer must name what it cannot decide: %r" % phrase)

  def test_no_stage_is_named_as_a_semantic_qa_verdict(self):
    rc, out = run_verifier("--code-only", "--only", "5", "--root", self.copy_root)
    for forbidden in ("semantic QA: PASS", "QA semantics verified",
                      "answers are correct", "ground truth verified"):
      self.assertNotIn(forbidden, out,
                       "the verifier must not claim semantic QA correctness: %r"
                       % forbidden)


class TestSafetyProperties(unittest.TestCase):
  """Safety properties that hold for every invocation."""

  def _script_source(self):
    with open(SCRIPT, "r", encoding="utf-8") as fh:
      return fh.read()

  def test_no_network_references_in_the_entry_point(self):
    src = self._script_source()
    for token in ("import socket", "import urllib", "import requests",
                  "urlopen(", "http.client", "curl ", "wget "):
      self.assertNotIn(token, src,
                       "the verifier must not reference the network: %r" % token)

  def test_never_prints_sealed_label_content(self):
    src = self._script_source()
    self.assertIn("verify_seal_opaque", src,
                  "the verifier should verify the seal by opaque bytes")
    # The sealed file must never be opened for content on the same line that
    # names it.
    for line in src.splitlines():
      if "heldout_labels.sealed.json" in line:
        self.assertNotIn("open(", line,
                         "the sealed file must never be opened: %s" % line.strip())

  def test_disables_bytecode_writing(self):
    self.assertIn("PYTHONDONTWRITEBYTECODE=1", self._script_source(),
                  "the verifier must not write .pyc files into the repository")

  def test_refuses_to_run_under_custodian_mode(self):
    rc, out = run_verifier(
      "--only", "4",
      env={"HELDOUT_CUSTODIAN_MODE": "benchmark"},
    )
    self.assertEqual(rc, 2,
                     "the verifier must refuse label-read authority:\n%s" % out)
    self.assertIn("HELDOUT_CUSTODIAN_MODE", out)

  def test_help_is_not_blocked_by_custodian_mode(self):
    # Contrast with the test above: --help must stay usable so the refusal
    # message can be discovered.
    rc, out = run_verifier("--help", env={"HELDOUT_CUSTODIAN_MODE": "benchmark"})
    self.assertEqual(rc, 0)
