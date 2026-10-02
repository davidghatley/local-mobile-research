"""Stage 10 (private-eval custody) must fail closed on an unbound manifest.

An independent freeze review found a vacuous pass: stage 10 printed
"MATCHES in-repo manifest" when the manifest recorded no hash to compare
against, so a manifest stripped of its digests would still pass. These tests
pin the fail-closed behaviour.

"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFIER = os.path.join(REPO_ROOT, "scripts", "verify_round0")
MANIFEST_REL = "corpus/private_test_manifest.json"


def _sha256_file(path: str) -> str:
    """Compute SHA256 hex digest of a file, matching substrate/private_eval.sha256_file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_repo_minimal(target):
    """Copy only the essential repo structure needed for stage 10 verification.

    We must not copy the large git-ignored corpus/data directories ( hitting
    disk quota on CI).  The minimum tree contains: substrate/, scripts/,
    pyproject.toml, AGENTS.md, and __init__.py so that imports work.
    """
    essential_dirs = ("substrate", "scripts", "data_tools")
    essential_files = ("pyproject.toml", "AGENTS.md", "__init__.py", "master_orchestration_prompt.txt")

    if os.path.isdir(REPO_ROOT):
        os.makedirs(target, exist_ok=True)
        for item in os.listdir(REPO_ROOT):
            src = os.path.join(REPO_ROOT, item)
            dst = os.path.join(target, item)
            if item in essential_dirs:
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns(".git", "__pycache__"))
            elif item in essential_files and os.path.isfile(src):
                shutil.copy2(src, dst)
            # Skip everything else (corpus, generator, etc. — too large)

    # stage 10 reads exactly ONE file from corpus/: the opaque manifest. The
    # 42 MB corpus.jsonl is git-ignored and absent on CI, but the manifest is
    # committed, so the directory must exist and the file must be present for
    # the fixture to be well-formed. Create the directory; the tests write the
    # manifest into it per scenario.
    os.makedirs(os.path.join(target, "corpus"), exist_ok=True)


def run_verifier(root, *args, env=None):
    """Run the verifier with optional env overrides for subprocess only.

    Crucially, LMR_PRIVATE_EVAL_DIR is passed via *env* so it affects only
    the verifier subprocess, never the parent process or ambient environment.
    """
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
    """Stage 10 must fail closed: every scenario with missing/wrong data
    or a mis-pointed private directory must result in a non-zero exit code.
    """

    def setUp(self):
        self.base_tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base_tmp, ignore_errors=True)
        self.repo = os.path.join(self.base_tmp, "repo")
        _copy_repo_minimal(self.repo)
        # Ensure the substrate package is importable from the repo copy
        self._ensure_substrate_importable()

    def _ensure_substrate_importable(self):
        """Make sure the repo copy's parent is on sys.path so substrate.* imports work."""
        import sys
        # Insert the repo root at the front so it shadows the installed package
        if REPO_ROOT not in sys.path:
            sys.path.insert(0, REPO_ROOT)

    def _write_manifest(self, data):
        with open(os.path.join(self.repo, MANIFEST_REL), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")

    def _read_manifest(self):
        path = os.path.join(self.repo, MANIFEST_REL)
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _create_synthetic_private_dir(self, counts_data=None, questions_data=None,
                                       labels_data=None, seal_override=None):
        """Build a synthetic private-eval directory under tmp and write a
        matching in-repo manifest.  The caller may override any component
        (counts, questions, labels, seal) to test a specific failure mode.

        Returns the path to the synthetic private directory.
        """
        private_dir = tempfile.mkdtemp(prefix="private_eval_", dir=self.base_tmp)

        # --- questions.json ---
        if questions_data is None:
            questions_data = {
                "questions": [
                    {
                        "question_id": "synthetic-001",
                        "split": "public_test",
                        "meta": {},
                    }
                ]
            }
        questions_path = os.path.join(private_dir, "questions.json")
        with open(questions_path, "w", encoding="utf-8") as fh:
            json.dump(questions_data, fh, indent=2)

        # --- labels.json ---
        if labels_data is None:
            labels_data = {"labels": [{"label_id": "synthetic-label-001"}]}
        labels_path = os.path.join(private_dir, "labels.json")
        with open(labels_path, "w", encoding="utf-8") as fh:
            json.dump(labels_data, fh, indent=2)

        # --- counts.json ---
        if counts_data is None:
            counts_data = {"total": 1, "by_type": {"factoid": 1}}
        counts_path = os.path.join(private_dir, "counts.json")
        with open(counts_path, "w", encoding="utf-8") as fh:
            json.dump(counts_data, fh, indent=2)

        # --- seal.sha256 ---
        questions_sha256 = _sha256_file(questions_path)
        if seal_override is not None:
            with open(os.path.join(private_dir, "seal.sha256"), "w", encoding="utf-8") as fh:
                fh.write(seal_override + "\n")
        else:
            with open(os.path.join(private_dir, "seal.sha256"), "w", encoding="utf-8") as fh:
                fh.write(questions_sha256 + "\n")

        # --- Build the in-repo manifest matching the synthetic fixture ---
        manifest_data = {
            "revision": "private-test-r1",
            "counts": counts_data,
            "hashes": {
                "questions_json_sha256": questions_sha256,
                "labels_json_sha256": _sha256_file(labels_path),
                "aggregate_content_sha256": _sha256_file(
                    os.path.join(private_dir, "questions.json")
                ),
            },
            "seal_sha256": questions_sha256,
        }
        self._write_manifest(manifest_data)

        return private_dir

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------

    def test_baseline_passes(self):
        """Stage 10 passes when the synthetic fixture is well-formed and
        LMR_PRIVATE_EVAL_DIR points to it (subprocess env only).
        """
        private_dir = self._create_synthetic_private_dir()
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertEqual(rc, 0, "stage 10 must pass on the synthetic artifacts:\n%s" % out)
        self.assertIn("MATCHES in-repo manifest", out)

    def test_missing_recorded_questions_hash_fails(self):
        """An unbound question set (hash removed from manifest) must FAIL.
        This is the fail-closed case that CI broke because the test relied on
        the real developer private directory.
        """
        private_dir = self._create_synthetic_private_dir()
        # Remove the recorded questions hash from the manifest,
        # while keeping the synthetic private dir with questions.json.
        man = self._read_manifest()
        man["hashes"].pop("questions_json_sha256", None)
        self._write_manifest(man)
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertNotEqual(rc, 0, "an unbound question set must fail:\n%s" % out)
        self.assertIn("no questions_json_sha256", out)
        self.assertNotIn("questions.json sha256 MATCHES", out)

    def test_missing_recorded_labels_hash_fails(self):
        """An unbound label set (hash removed from manifest) must FAIL."""
        private_dir = self._create_synthetic_private_dir()
        man = self._read_manifest()
        man["hashes"].pop("labels_json_sha256", None)
        self._write_manifest(man)
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertNotEqual(rc, 0, "unbound label set must fail:\n%s" % out)
        self.assertIn("no labels_json_sha256", out)
        self.assertNotIn("labels.json sha256 MATCHES", out)

    def test_missing_seal_fails(self):
        """No seal digest in the manifest must FAIL (fail-closed)."""
        private_dir = self._create_synthetic_private_dir()
        # Now wipe seal_sha256 from the manifest while keeping the synthetic dir
        man = self._read_manifest()
        man.pop("seal_sha256", None)
        self._write_manifest(man)
        # The synthetic dir still has seal.sha256 but the manifest disowns it
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertNotEqual(rc, 0, "no seal digest must fail:\n%s" % out)
        self.assertIn("no seal_sha256", out)

    def test_wrong_recorded_hash_fails(self):
        """A hash mismatch between manifest and private content must FAIL."""
        private_dir = self._create_synthetic_private_dir()
        # Plant a wrong questions_json_sha256 in the manifest
        man = self._read_manifest()
        man["hashes"]["questions_json_sha256"] = "0" * 64
        self._write_manifest(man)
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertNotEqual(rc, 0, "hash mismatch must fail:\n%s" % out)
        self.assertIn("MISMATCH", out)

    def test_manifest_with_private_content_fails(self):
        """Private content (e.g. a question id prefix) leaking into the in-repo
        manifest must FAIL."""
        private_dir = self._create_synthetic_private_dir()
        # Leak private content into the counts inside the in-repo manifest
        man = self._read_manifest()
        man["counts"]["sample_question"] = "qa-private-01"
        self._write_manifest(man)
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertNotEqual(rc, 0, "private content in the manifest must fail:\n%s" % out)
        self.assertIn("PRIVATE CONTENT", out)

    def test_missing_manifest_fails(self):
        """Absent in-repo manifest must fail closed."""
        # Remove the manifest from the repo copy
        manifest_path = os.path.join(self.repo, MANIFEST_REL)
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
        # Even without LMR_PRIVATE_EVAL_DIR set, the absent manifest must fail
        rc, out = run_verifier(self.repo)
        self.assertNotEqual(rc, 0, "absent manifest must fail closed:\n%s" % out)
        self.assertIn("private_test_manifest.json", out)

    def test_private_dir_pointing_into_repo_fails(self):
        """LMR_PRIVATE_EVAL_DIR resolving inside the repository must FAIL."""
        # Build the fixture FIRST so the in-repo manifest exists. Without it,
        # stage 10 stops at the manifest check and never reaches the custody
        # check this test is actually about.
        self._create_synthetic_private_dir()
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": os.path.join(self.repo, "staging")},
        )
        self.assertNotEqual(rc, 0, "an in-repo private dir must fail:\n%s" % out)
        self.assertIn("outside the repository", out)

    def test_private_dir_entirely_absent_fails(self):
        """LMR_PRIVATE_EVAL_DIR pointing to a nonexistent directory must FAIL."""
        # As above: the manifest must exist so the run reaches the
        # private-directory existence check rather than stopping earlier.
        # The absent path must be OUTSIDE the repo copy, otherwise the
        # "resolves inside the repository" check fires first and this test
        # would pass for the wrong reason.
        self._create_synthetic_private_dir()
        absent = os.path.join(self.base_tmp, "no-such-private-dir-12345")
        self.assertFalse(
            os.path.abspath(absent).startswith(os.path.abspath(self.repo) + os.sep),
            "the absent fixture path must not live inside the repo copy",
        )
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": absent},
        )
        self.assertNotEqual(rc, 0, "absent private dir must fail closed:\n%s" % out)
        self.assertIn("private eval dir ABSENT", out)

    def test_private_content_leaking_into_manifest_fails(self):
        """Any private question id or answer text in the in-repo manifest must
        FAIL (the manifest is audit-only, counts/hashes only)."""
        private_dir = self._create_synthetic_private_dir()
        man = self._read_manifest()
        # Inject a private-test-style id into the counts
        man["counts"]["private_question_id"] = "qa-private-099"
        self._write_manifest(man)
        rc, out = run_verifier(
            self.repo,
            env={"LMR_PRIVATE_EVAL_DIR": private_dir},
        )
        self.assertNotEqual(rc, 0, "private content leak in manifest must fail:\n%s" % out)
        self.assertIn("PRIVATE CONTENT", out)


if __name__ == "__main__":
  unittest.main()