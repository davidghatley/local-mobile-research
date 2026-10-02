"""Durable freeze-record promotion tests (Round 0 closure).

Architecture under test: stage 8 builds and validates a freeze CANDIDATE in
the verifier's scratch dir only. The DURABLE record
(``<LMR_PRIVATE_EVAL_DIR>/freeze_manifest_<commit>.json`` plus the stable
pointer ``<LMR_PRIVATE_EVAL_DIR>/freeze_manifest.json``) is promoted by the
shell AFTER the stage loop, if and only if the run was full, unfiltered
(no ``--only``), and every stage passed with zero skips.

These tests pin the promotion gate from both sides: partial, code-only, and
failed full runs must leave no durable record (and must not disturb a
pre-existing one), while a successful full run must leave exactly one
correct record binding the commit SHA, the verifier hash, and every stage
result.

RECURSION GUARD: a full verifier run executes stage 1
(``python3 -m unittest discover -s tests``) inside the repo copy, which would
discover THIS module and spawn unbounded nested full runs. Like
``tests/test_verify_round0_entrypoint.py``, this module skips entirely when
``VERIFY_ROUND0_IN_VERIFIER=1`` is present.

Hermeticity: every test works on throwaway copies in temp dirs. The real
repository and the real private directory are never mutated and never gain
files. Private files are handled as opaque bytes (copied, never opened).

Disk quota: full-tree copies exceed the /tmp tmpfs budget shared with other
tooling, so repo copies are SLIM (bulk git-ignored artifacts are symlinked
read-only; only small mutable files are materialised) and live on the /home
filesystem, which has room. Copies include ``.git`` so the candidate binds
the real commit SHA.
"""

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(REPO_ROOT, "scripts", "verify_round0")
REAL_PRIVATE = os.environ.get(
  "LMR_PRIVATE_EVAL_DIR",
  "/home/davidhatley/Projects/testing/local_mobile_research-private-eval",
)
STAGE_IDS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]

# Sibling workspace on the /home filesystem (room for copies). Never inside
# the repository and never inside the private directory.
WORK_PARENT = os.path.dirname(REPO_ROOT)

# Exact relative paths that are bulk by size and are therefore symlinked
# read-only instead of copied. Anything else over _SYMLINK_BYTES is also
# symlinked (git-ignored bulk is never mutated by these tests).
_SYMLINK_BYTES = 32 * 1024 * 1024
_SKIP_DIRS = {"corpus/scale", "corpus/raw"}
_SKIP_FILES = {"corpus/corpus.jsonl"}

# Opaque private files staged into throwaway private dirs. Copied as bytes,
# never opened: the seal is verified by hash, never parsed.
PRIVATE_FILES = (
  "freeze_census_pin.json",
  "seal.sha256",
  "questions.json",
  "labels.json",
  "counts.json",
)

FULL_TIMEOUT = 1500


def setUpModule():
  if os.environ.get("VERIFY_ROUND0_IN_VERIFIER") == "1":
    raise unittest.SkipTest(
      "running inside verify_round0; skipping to avoid nested full runs")


def _sha256_file(path):
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def _run_verifier(args, root, private_dir, timeout=FULL_TIMEOUT, tmpdir=None):
  """Run the verifier once. private_dir=None leaves the env untouched.

  tmpdir, when given, becomes TMPDIR for the verifier subtree only: nested
  throwaway copies land there instead of the quota-capped /tmp tmpfs.
  """
  env = dict(os.environ)
  env.setdefault("VERIFY_ROUND0_PYTHON", "python3")
  env["VERIFY_ROUND0_IN_VERIFIER"] = "1"
  if private_dir is not None:
    env["LMR_PRIVATE_EVAL_DIR"] = private_dir
  if tmpdir is not None:
    env["TMPDIR"] = tmpdir
  proc = subprocess.run(
    [VERIFIER] + list(args) + ["--root", root],
    capture_output=True, text=True, env=env, timeout=timeout,
  )
  return proc.returncode, proc.stdout + proc.stderr


def _slim_copy(src, dst):
  """Copy a repo tree with bulk artifacts symlinked read-only.

  Small files are materialised (tests mutate some of them); ``.git`` is
  copied (4.8 MB) so the candidate binds the real commit SHA; bulk
  git-ignored artifacts (corpus/scale, corpus/raw, corpus.jsonl, the 986 MB
  GGUF, anything else over 32 MB) become symlinks to the real files, which
  the verifier only ever reads.
  """
  os.makedirs(dst)
  src = os.path.abspath(src)
  for dirpath, dirnames, filenames in os.walk(src):
    rel = os.path.relpath(dirpath, src)
    rel = "" if rel == "." else rel
    # Prune before descending: never copy bulk dirs, .git (handled below),
    # or bytecode caches.
    dirnames[:] = sorted(
      d for d in dirnames
      if os.path.join(rel, d) not in _SKIP_DIRS
      and d not in (".git", "__pycache__"))
    dest_dir = os.path.join(dst, rel) if rel else dst
    os.makedirs(dest_dir, exist_ok=True)
    for name in filenames:
      if name.endswith((".pyc", ".pyo")):
        continue
      src_path = os.path.join(dirpath, name)
      rel_path = os.path.join(rel, name) if rel else name
      if rel_path in _SKIP_FILES or os.path.getsize(src_path) > _SYMLINK_BYTES:
        os.symlink(src_path, os.path.join(dst, rel_path))
      else:
        shutil.copy2(src_path, os.path.join(dst, rel_path))
  # .git: real copy, so `git -C <copy> rev-parse HEAD` resolves.
  shutil.copytree(os.path.join(src, ".git"), os.path.join(dst, ".git"),
                  symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
  # Symlink the pruned bulk dirs.
  for rel_dir in sorted(_SKIP_DIRS):
    os.symlink(os.path.join(src, rel_dir), os.path.join(dst, rel_dir))


def _stage_private(dst):
  """Stage opaque private bytes into a throwaway dir. Returns False when the
  real private directory lacks the required files (caller must skip)."""
  os.makedirs(dst, exist_ok=True)
  for name in PRIVATE_FILES:
    src = os.path.join(REAL_PRIVATE, name)
    if not os.path.isfile(src):
      return False
    shutil.copy2(src, os.path.join(dst, name))
  return True


def _freeze_records(priv):
  """Versioned durable records (exactly the freeze_manifest_<sha>.json set)."""
  out = []
  for path in glob.glob(os.path.join(priv, "freeze_manifest_*.json")):
    if re.fullmatch(r"freeze_manifest_[0-9a-f]{40}\.json",
                    os.path.basename(path)):
      out.append(path)
  return sorted(out)


class FreezePromotionBase(unittest.TestCase):
  """One slim repo copy + one throwaway private dir per test."""

  need_full_artifacts = True

  def setUp(self):
    if self.need_full_artifacts:
      if not os.path.isfile(os.path.join(REPO_ROOT, "corpus", "corpus.jsonl")):
        self.skipTest("corpus/corpus.jsonl absent (42 MB git-ignored corpus)")
    self.work = tempfile.mkdtemp(prefix="lanea-freeze-", dir=WORK_PARENT)
    self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
    self.repo = os.path.join(self.work, "repo")
    _slim_copy(REPO_ROOT, self.repo)
    self.priv = os.path.join(self.work, "private")
    # Quota-capped /tmp breaks nested throwaway copies; keep them here.
    self.env_tmp = os.path.join(self.work, "tmp")
    os.makedirs(self.env_tmp, exist_ok=True)
    if not _stage_private(self.priv):
      self.skipTest("private custody digests unavailable")
    if self.need_full_artifacts:
      self._require_full_run_inputs()

  def _require_full_run_inputs(self):
    """Full runs need the GGUF, the runtime, and the seal trust root.

    Anything missing means the environment cannot produce a full pass, so
    skip with a reason instead of asserting on an impossible run.
    """
    import sys
    sys.path.insert(0, self.repo)
    try:
      from substrate.generator import GeneratorConfig
      cfg_path = os.path.join(self.repo, "corpus", "generator_config.json")
      with open(cfg_path, "r", encoding="utf-8") as fh:
        disk = json.load(fh)
      gen = GeneratorConfig.from_dict(disk)
      art_rel = disk.get("artifact_path", gen.file)
      art = art_rel if os.path.isabs(art_rel) else os.path.join(self.repo, art_rel)
      if not os.path.isfile(art):
        self.skipTest("generator artifact absent (986 MB GGUF, git-ignored)")
      rb = disk.get("runtime_binaries", {})
      lib_dir = rb.get("lib_dir", "")
      for name, rec in (rb.get("libs") or {}).items():
        target = rec.get("soname_target") or name
        p = os.path.join(lib_dir, target) if lib_dir else target
        if not os.path.isfile(p):
          self.skipTest("runtime binary absent on this host: %s" % name)
      server = (rb.get("llama-server") or {}).get("path")
      if not server or not os.path.isfile(server):
        self.skipTest("llama-server binary absent on this host")
    finally:
      sys.path.remove(self.repo)

  def full_run(self, extra_args=()):
    return _run_verifier(list(extra_args), self.repo, self.priv,
                         tmpdir=self.env_tmp)

  def assertNoDurableRecord(self, where):
    self.assertEqual(
      _freeze_records(self.priv), [],
      "no durable freeze record may exist %s" % where)
    self.assertFalse(
      os.path.isfile(os.path.join(self.priv, "freeze_manifest.json")),
      "no stable freeze pointer may exist %s" % where)
    for dirpath, _dirnames, filenames in os.walk(self.repo):
      for name in filenames:
        self.assertFalse(
          name.startswith("freeze_manifest"),
          "the repository must never carry a freeze record (%s) %s"
          % (os.path.join(dirpath, name), where))


class TestPartialRunsNeverPromote(FreezePromotionBase):
  def test_only8_pass_leaves_no_durable_manifest(self):
    rc, out = _run_verifier(["--only", "8"], self.repo, self.priv,
                            timeout=600, tmpdir=self.env_tmp)
    self.assertEqual(rc, 0, "stage 8 must pass on clean artifacts:\n%s" % out)
    self.assertIn("freeze candidate staged", out)
    self.assertNoDurableRecord("after a passing --only 8 run")

  def test_code_only_run_leaves_no_durable_manifest(self):
    rc, out = _run_verifier(["--code-only"], self.repo, self.priv,
                            timeout=900, tmpdir=self.env_tmp)
    self.assertIn(rc, (0, 1),
                  "--code-only must exit 0 or 1, never crash:\n%s" % out)
    self.assertNotIn("Traceback", out)
    self.assertNoDurableRecord("after a --code-only run")

  def test_failing_stage8_leaves_no_durable_manifest(self):
    census = os.path.join(self.repo, "corpus", "partition_census.json")
    with open(census, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    data["expected"]["total"] = 9999
    with open(census, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = _run_verifier(["--only", "8"], self.repo, self.priv,
                            timeout=600, tmpdir=self.env_tmp)
    self.assertNotEqual(rc, 0, "stage 8 must fail on a broken census:\n%s" % out)
    self.assertNoDurableRecord("after a failing stage 8")


class TestFailedFullRunsNeverPromote(FreezePromotionBase):
  def test_stage9_failure_blocks_promotion(self):
    pins = os.path.join(self.repo, "references", "public_eval_pins.json")
    with open(pins, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    data["total_bytes"] = int(data.get("total_bytes", 0)) + 1
    with open(pins, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = self.full_run()
    self.assertNotEqual(rc, 0,
                        "a full run with broken stage 9 must fail:\n%s" % out[-4000:])
    self.assertIn("STAGE 8 freeze-manifest: PASS", out,
                  "stage 8 must still pass (the record existed mid-run):\n%s"
                  % out[-4000:])
    self.assertIn("STAGE 9 leakage-control-artifacts: FAIL", out)
    self.assertNoDurableRecord("after a full run that failed stage 9")

  def test_stage10_failure_blocks_promotion(self):
    # counts.json is required by stage 10 only: stage 8 binds the seal
    # (seal.sha256) and the question/label digests, never the counts file.
    os.remove(os.path.join(self.priv, "counts.json"))
    rc, out = self.full_run()
    self.assertNotEqual(rc, 0,
                        "a full run with broken stage 10 must fail:\n%s" % out[-4000:])
    self.assertIn("STAGE 8 freeze-manifest: PASS", out,
                  "stage 8 must still pass (the record existed mid-run):\n%s"
                  % out[-4000:])
    self.assertIn("STAGE 10 private-eval-custody: FAIL", out)
    self.assertNoDurableRecord("after a full run that failed stage 10")

  def test_census_pin_mismatch_blocks_promotion(self):
    pin = os.path.join(self.priv, "freeze_census_pin.json")
    with open(pin, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    digest = data["partition_census_sha256"]
    data["partition_census_sha256"] = ("0" if digest[0] != "0" else "1") + digest[1:]
    with open(pin, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = self.full_run()
    self.assertNotEqual(rc, 0,
                        "a census-pin mismatch must fail the run:\n%s" % out[-4000:])
    self.assertNoDurableRecord("after a census-pin mismatch")

  def test_failing_run_preserves_preexisting_record_byte_identical(self):
    old_record = {
      "run_id": "pre-existing-record",
      "commit_sha": "0" * 40,
      "note": "this record predates the run and must survive it untouched",
    }
    old_bytes = (json.dumps(old_record, indent=2, sort_keys=True) + "\n").encode()
    pointer = os.path.join(self.priv, "freeze_manifest.json")
    versioned = os.path.join(self.priv, "freeze_manifest_%s.json" % ("0" * 40))
    for path in (pointer, versioned):
      with open(path, "wb") as fh:
        fh.write(old_bytes)
    # Break stage 9 so the full run fails after stage 8 passed.
    pins = os.path.join(self.repo, "references", "public_eval_pins.json")
    with open(pins, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    data["total_bytes"] = int(data.get("total_bytes", 0)) + 1
    with open(pins, "w", encoding="utf-8") as fh:
      json.dump(data, fh, indent=2, sort_keys=True)
      fh.write("\n")
    rc, out = self.full_run()
    self.assertNotEqual(rc, 0, "the broken full run must fail:\n%s" % out[-4000:])
    for path in (pointer, versioned):
      with open(path, "rb") as fh:
        self.assertEqual(fh.read(), old_bytes,
                         "a failed run must leave the old record byte-identical: %s"
                         % path)
    self.assertEqual(
      [p for p in _freeze_records(self.priv) if os.path.basename(p) != os.path.basename(versioned)],
      [], "a failed run must not install any new versioned record")


class TestSuccessfulFullRunPromotes(FreezePromotionBase):
  def test_successful_full_run_promotes_exactly_one_bound_record(self):
    rc, out = self.full_run()
    self.assertEqual(rc, 0, "the clean full run must pass:\n%s" % out[-4000:])
    self.assertIn("RESULT: all load-bearing stages PASS.", out)
    self.assertIn("FREEZE RECORD: promoted durable record", out)

    versioned = _freeze_records(self.priv)
    self.assertEqual(len(versioned), 1,
                     "a successful full run must leave exactly one versioned "
                     "record, found %r" % versioned)
    pointer = os.path.join(self.priv, "freeze_manifest.json")
    self.assertTrue(os.path.isfile(pointer), "the stable pointer must exist")
    with open(versioned[0], "rb") as fh:
      record_bytes = fh.read()
    with open(pointer, "rb") as fh:
      self.assertEqual(fh.read(), record_bytes,
                       "pointer and versioned record must carry identical bytes")
    data = json.loads(record_bytes.decode("utf-8"))

    # The record must bind the exact revision and the exact verifier.
    expect_sha = subprocess.run(
      ["git", "-C", self.repo, "rev-parse", "HEAD"],
      capture_output=True, text=True, timeout=60).stdout.strip()
    self.assertEqual(len(expect_sha), 40)
    self.assertEqual(data["commit_sha"], expect_sha)
    self.assertIn("freeze_manifest_%s.json" % expect_sha, versioned[0])
    self.assertEqual(data["verifier_sha256"],
                     _sha256_file(os.path.join(self.repo, "scripts", "verify_round0")))
    self.assertEqual(data["verifier_mode"], "full")
    self.assertTrue(data["verified_at_utc"],
                    "the record must carry its verification timestamp")
    self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                                 data["verified_at_utc"]),
                    "verified_at_utc must be UTC ISO-8601: %r"
                    % data["verified_at_utc"])
    self.assertIsInstance(data["working_tree_dirty"], bool)

    # The record must bind what the freeze is about.
    for field in ("corpus_hash", "sealed_labels_sha256", "questions_sha256",
                  "split_map_sha256", "partition_census_sha256",
                  "generator_config_sha256"):
      self.assertEqual(len(data[field]), 64, field)
    with open(os.path.join(self.repo, "corpus", "partition_census.json"),
              "rb") as fh:
      live = hashlib.sha256(fh.read()).hexdigest()
    self.assertEqual(data["partition_census_sha256"], live)
    self.assertTrue(data["regime_a_heldout_groups"])
    self.assertTrue(data["regime_b_document_heldout_groups"])
    self.assertTrue(data["code_hashes"])
    self.assertTrue(data["inventory"])
    self.assertTrue(data["thresholds"])

    # The record must bind every stage result, all PASS. Stage ids are strings
    # in the record, so sort numerically on BOTH sides - sorting only the left
    # and comparing to an already-ascending right list compares ["1","10","2"].
    results = data["stage_results"]
    self.assertEqual(sorted((int(r["stage"]) for r in results)),
                     sorted(int(s) for s in STAGE_IDS))
    for r in results:
      self.assertEqual(r["verdict"], "PASS", "stage %s" % r["stage"])

    # The record must be re-readable through the owning API.
    sys_path = __import__("sys").path
    sys_path.insert(0, REPO_ROOT)
    try:
      from substrate.manifest import RunManifest
      reread = RunManifest.read(versioned[0])
    finally:
      sys_path.remove(REPO_ROOT)
    self.assertEqual(reread.commit_sha, expect_sha)
    self.assertEqual(len(reread.stage_results), 10)

    # Nothing durable may leak into the repository.
    for dirpath, _dirnames, filenames in os.walk(self.repo):
      if ".git" in dirpath.split(os.sep):
        continue
      for name in filenames:
        self.assertFalse(name.startswith("freeze_manifest"),
                         "the repository must never carry a freeze record")


class TestWriterIsLive(unittest.TestCase):
  def test_run_manifest_write_is_not_dead_code(self):
    from substrate.manifest import RunManifest
    from substrate.generator import GeneratorConfig
    from substrate.types import ThresholdPolicy
    self.assertTrue(hasattr(RunManifest, "write"), "RunManifest.write is gone")
    self.assertTrue(callable(RunManifest.write))
    with tempfile.TemporaryDirectory() as tmp:
      path = os.path.join(tmp, "rt.json")
      man = RunManifest(
        run_id="r1", seed=0, corpus_hash="deadbeef",
        code_hashes={"a.py": "h"},
        generator=GeneratorConfig.from_dict({
          "generator_id": "synth-generator-v1",
          "model_id": "synth-model-v1",
          "revision": "r1",
          "prompt_hash": "d" * 64,
          "quantization": "Q4",
          "runtime": "llama.cpp",
          "file": "model.gguf",
          "artifact_sha256": "e" * 64,
          "tokenizer_id": "tok-v1",
          "chat_template_sha256": "c" * 64,
          "sampling": {"temperature": 0.0},
        }),
        thresholds={"stage0": ThresholdPolicy(
          threshold=0.5, interpretation="calibrated_probability", top_k=50,
          min_breadth=10, calibration_method="model_probability",
          score_kind="calibrated_probability")},
        commit_sha="a" * 40, verifier_sha256="b" * 64,
        verified_at_utc="2026-01-01T00:00:00Z", verifier_mode="full",
        stage_results=[{"stage": "1", "verdict": "PASS", "detail": "x"}],
      )
      man.write(path)
      reread = RunManifest.read(path)
      self.assertEqual(reread.run_id, "r1")
      # New bindings round-trip.
      self.assertEqual(reread.commit_sha, "a" * 40)
      self.assertEqual(reread.verifier_sha256, "b" * 64)
      self.assertEqual(reread.verifier_mode, "full")
      self.assertEqual(reread.verified_at_utc, "2026-01-01T00:00:00Z")
      self.assertEqual(reread.stage_results,
                       [{"stage": "1", "verdict": "PASS", "detail": "x"}])


if __name__ == "__main__":
  unittest.main()
