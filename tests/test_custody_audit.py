"""Tests for HeldoutCustodian custody audit: append-only, required fields, seal hash."""

import json
import os
import tempfile
import unittest

from substrate.splits import HeldoutAccessDenied, HeldoutCustodian


class TestCustodyAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.labels_path = os.path.join(self.tmp.name, "heldout_labels.sealed.json")
        self.audit_path = os.path.join(self.tmp.name, "heldout_access_log.jsonl")

        # Create a sealed labels file with some dummy data
        self.labels_data = {
            "q_heldout_001": {"answer": "A", "sufficient_sets": [["a:article1"]]},
            "q_heldout_002": {"answer": "B", "sufficient_sets": [["a:article2"]]},
            "q_heldout_003": {"answer": "C", "sufficient_sets": [["a:article3"]]},
        }
        with open(self.labels_path, "w", encoding="utf-8") as fh:
            json.dump(self.labels_data, fh)

        # Set custodian env var
        self.old_env = os.environ.get("HELDOUT_CUSTODIAN_MODE")
        os.environ["HELDOUT_CUSTODIAN_MODE"] = "benchmark"

    def tearDown(self):
        if self.old_env is None:
            del os.environ["HELDOUT_CUSTODIAN_MODE"]
        else:
            os.environ["HELDOUT_CUSTODIAN_MODE"] = self.old_env
        self.tmp.cleanup()

    def test_load_labels_requires_accessor(self):
        """Missing accessor fails closed."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied) as cm:
            cust.load_labels(allow_heldout=True, accessor="", role="evaluator", purpose="eval", granted_by="orchestrator")
        self.assertIn("accessor", str(cm.exception))

    def test_load_labels_requires_role(self):
        """Missing role fails closed."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied) as cm:
            cust.load_labels(allow_heldout=True, accessor="runner", role="", purpose="eval", granted_by="orchestrator")
        self.assertIn("role", str(cm.exception))

    def test_load_labels_requires_purpose(self):
        """Missing purpose fails closed."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied) as cm:
            cust.load_labels(allow_heldout=True, accessor="runner", role="evaluator", purpose="", granted_by="orchestrator")
        self.assertIn("purpose", str(cm.exception))

    def test_load_labels_requires_granted_by(self):
        """Missing granted_by fails closed."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied) as cm:
            cust.load_labels(allow_heldout=True, accessor="runner", role="evaluator", purpose="eval", granted_by="")
        self.assertIn("granted_by", str(cm.exception))

    def test_load_labels_whitespace_only_fails(self):
        """Whitespace-only fields fail closed."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied):
            cust.load_labels(allow_heldout=True, accessor="  ", role="evaluator", purpose="eval", granted_by="orchestrator")
        with self.assertRaises(HeldoutAccessDenied):
            cust.load_labels(allow_heldout=True, accessor="runner", role="  ", purpose="eval", granted_by="orchestrator")

    def test_audit_record_has_all_required_fields(self):
        """Audit record includes accessor, role, purpose, timestamp, labels_path, seal_sha256, question_ids, granted_by."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        labels = cust.load_labels(
            allow_heldout=True,
            accessor="benchmark-runner-v1",
            role="evaluator",
            purpose="final-evaluation",
            granted_by="orchestrator",
        )
        self.assertEqual(labels, self.labels_data)

        # Read audit log
        with open(self.audit_path, "r", encoding="utf-8") as fh:
            lines = fh.read().strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])

        # Check all required fields
        self.assertEqual(entry["accessor"], "benchmark-runner-v1")
        self.assertEqual(entry["role"], "evaluator")
        self.assertEqual(entry["purpose"], "final-evaluation")
        self.assertEqual(entry["granted_by"], "orchestrator")
        self.assertIn("timestamp_utc", entry)
        self.assertEqual(entry["labels_path"], self.labels_path)
        self.assertIn("seal_sha256", entry)
        self.assertEqual(entry["seal_sha256"], cust.seal_hash())
        self.assertEqual(set(entry["question_ids"]), set(self.labels_data.keys()))

    def test_audit_append_only_multiple_accesses(self):
        """Multiple accesses append to audit log (no overwrite)."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)

        cust.load_labels(allow_heldout=True, accessor="runner1", role="evaluator", purpose="eval", granted_by="orch")
        cust.load_labels(allow_heldout=True, accessor="runner2", role="auditor", purpose="audit", granted_by="orch")

        with open(self.audit_path, "r", encoding="utf-8") as fh:
            lines = fh.read().strip().splitlines()
        self.assertEqual(len(lines), 2)
        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        self.assertEqual(entry1["accessor"], "runner1")
        self.assertEqual(entry2["accessor"], "runner2")

    def test_seal_hash_in_audit_matches_current_file(self):
        """Audit entry's seal_sha256 matches the sealed file at access time."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        expected_seal = cust.seal_hash()

        cust.load_labels(allow_heldout=True, accessor="runner", role="evaluator", purpose="eval", granted_by="orch")

        with open(self.audit_path, "r", encoding="utf-8") as fh:
            entry = json.loads(fh.read().strip())
        self.assertEqual(entry["seal_sha256"], expected_seal)

    def test_seal_hash_detects_tampering(self):
        """If sealed file changes after audit, seal hash mismatch is detectable."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        original_seal = cust.seal_hash()

        # First access
        cust.load_labels(allow_heldout=True, accessor="runner", role="evaluator", purpose="eval", granted_by="orch")

        # Tamper with sealed file
        with open(self.labels_path, "w", encoding="utf-8") as fh:
            json.dump({"tampered": True}, fh)

        # New custodian instance would see different seal
        cust2 = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        new_seal = cust2.seal_hash()
        self.assertNotEqual(original_seal, new_seal)

        # Audit log still has original seal
        with open(self.audit_path, "r", encoding="utf-8") as fh:
            entry = json.loads(fh.read().strip())
        self.assertEqual(entry["seal_sha256"], original_seal)
        self.assertNotEqual(entry["seal_sha256"], new_seal)

    def test_without_custodian_env_var_fails(self):
        """Access denied without HELDOUT_CUSTODIAN_MODE=benchmark."""
        os.environ["HELDOUT_CUSTODIAN_MODE"] = "not-benchmark"
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied):
            cust.load_labels(allow_heldout=True, accessor="runner", role="evaluator", purpose="eval", granted_by="orch")

    def test_without_allow_heldout_fails(self):
        """Access denied without allow_heldout=True."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        with self.assertRaises(HeldoutAccessDenied):
            cust.load_labels(allow_heldout=False, accessor="runner", role="evaluator", purpose="eval", granted_by="orch")

    def test_expected_sha256_verification(self):
        """expected_sha256 parameter verifies seal matches."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        correct_seal = cust.seal_hash()

        # Correct seal passes
        labels = cust.load_labels(
            allow_heldout=True,
            accessor="runner",
            role="evaluator",
            purpose="eval",
            granted_by="orch",
            expected_sha256=correct_seal,
        )
        self.assertEqual(labels, self.labels_data)

        # Wrong seal fails
        with self.assertRaises(HeldoutAccessDenied) as cm:
            cust.load_labels(
                allow_heldout=True,
                accessor="runner2",
                role="evaluator",
                purpose="eval",
                granted_by="orch",
                expected_sha256="wrong_hash",
            )
        self.assertIn("hash mismatch", str(cm.exception))

    def test_question_ids_in_audit_match_loaded_labels(self):
        """Audit entry question_ids matches the labels actually loaded."""
        cust = HeldoutCustodian(labels_path=self.labels_path, audit_path=self.audit_path)
        cust.load_labels(allow_heldout=True, accessor="runner", role="evaluator", purpose="eval", granted_by="orch")

        with open(self.audit_path, "r", encoding="utf-8") as fh:
            entry = json.loads(fh.read().strip())
        self.assertEqual(set(entry["question_ids"]), set(self.labels_data.keys()))


if __name__ == "__main__":
    unittest.main()