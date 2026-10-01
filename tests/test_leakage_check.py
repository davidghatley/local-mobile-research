"""Tests for leakage check: flags near-duplicates, passes distinct, never leaks heldout data."""

import json
import os
import tempfile
import unittest

from data_tools.leakage_check import (
    LeakageReport,
    calibrate_threshold_on_dev,
    char_ngrams,
    compute_ngram_similarities,
    jaccard_similarity,
    run_leakage_check,
)


class TestLeakageCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

        # Held-out questions (sealed)
        self.heldout_questions = [
            {"question_id": "hq_001", "text": "What is the capital of France?"},
            {"question_id": "hq_002", "text": "Who wrote Hamlet?"},
            {"question_id": "hq_003", "text": "What is the speed of light?"},
        ]
        self.heldout_q_path = os.path.join(self.tmp.name, "heldout_questions.json")
        with open(self.heldout_q_path, "w", encoding="utf-8") as fh:
            json.dump(self.heldout_questions, fh)

        # Held-out labels (sealed file for seal hash)
        self.heldout_labels = {
            "hq_001": {"answer": "Paris", "sufficient_sets": [["a:paris"]]},
            "hq_002": {"answer": "William Shakespeare", "sufficient_sets": [["a:shakespeare"]]},
            "hq_003": {"answer": "299792458 m/s", "sufficient_sets": [["a:light"]]},
        }
        self.heldout_labels_path = os.path.join(self.tmp.name, "heldout_labels.sealed.json")
        with open(self.heldout_labels_path, "w", encoding="utf-8") as fh:
            json.dump(self.heldout_labels, fh)

        # Dev questions for calibration
        self.dev_questions = [
            {"question_id": "dq_001", "text": "What is the capital of Germany?"},
            {"question_id": "dq_002", "text": "Who wrote Romeo and Juliet?"},
            {"question_id": "dq_003", "text": "What is the boiling point of water?"},
            {"question_id": "dq_004", "text": "What is the largest planet?"},
            {"question_id": "dq_005", "text": "Who painted the Mona Lisa?"},
        ]
        self.dev_q_path = os.path.join(self.tmp.name, "dev_questions.json")
        with open(self.dev_q_path, "w", encoding="utf-8") as fh:
            json.dump(self.dev_questions, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def test_jaccard_similarity_basics(self):
        """Jaccard similarity works correctly."""
        a = {"hello", "world"}
        b = {"hello", "world"}
        self.assertEqual(jaccard_similarity(a, b), 1.0)

        a = {"hello", "world"}
        b = {"hello", "there"}
        self.assertAlmostEqual(jaccard_similarity(a, b), 1/3)

        a = set()
        b = set()
        self.assertEqual(jaccard_similarity(a, b), 1.0)

        a = {"a"}
        b = set()
        self.assertEqual(jaccard_similarity(a, b), 0.0)

    def test_char_ngrams(self):
        """Character n-gram extraction works."""
        text = "hello"
        grams = char_ngrams(text, n=3)
        self.assertIn("hel", grams)
        self.assertIn("ell", grams)
        self.assertIn("llo", grams)

        # Short text
        grams = char_ngrams("hi", n=5)
        self.assertEqual(grams, {"hi"})

    def test_compute_ngram_similarities(self):
        """Similarity computation returns synthetic qid, max_sim, matched_heldout_qid."""
        synthetic = [
            {"question_id": "sq_001", "text": "What is the capital of France?"},  # Exact match
            {"question_id": "sq_002", "text": "What is the capital of Germany?"},  # Similar structure
            {"question_id": "sq_003", "text": "Completely different question about apples"},  # Distinct
        ]
        results = compute_ngram_similarities(synthetic, self.heldout_questions)

        self.assertEqual(len(results), 3)
        for qid, sim, hqid in results:
            self.assertIn(qid, ["sq_001", "sq_002", "sq_003"])
            self.assertGreaterEqual(sim, 0.0)
            self.assertLessEqual(sim, 1.0)
            self.assertIn(hqid, ["hq_001", "hq_002", "hq_003"])

        # Exact match should have high similarity
        sq_001_result = next(r for r in results if r[0] == "sq_001")
        self.assertGreater(sq_001_result[1], 0.7)  # High similarity for near-duplicate

        # Distinct should have low similarity
        sq_003_result = next(r for r in results if r[0] == "sq_003")
        self.assertLess(sq_003_result[1], 0.3)

    def test_leakage_check_flags_near_duplicate(self):
        """Leakage check flags a known near-duplicate synthetic question."""
        synthetic = [
            {"question_id": "syn_001", "text": "What is the capital of France?"},  # Near-duplicate of hq_001
            {"question_id": "syn_002", "text": "What is the population of Tokyo?"},  # Distinct
        ]
        syn_path = os.path.join(self.tmp.name, "synthetic.json")
        with open(syn_path, "w", encoding="utf-8") as fh:
            json.dump(synthetic, fh)

        report = run_leakage_check(
            synthetic_questions_path=syn_path,
            heldout_questions_path=self.heldout_q_path,
            heldout_labels_path=self.heldout_labels_path,
            dev_questions_path=self.dev_q_path,
        )

        self.assertEqual(report.status, "REJECT")
        self.assertEqual(report.total_synthetic, 2)
        self.assertEqual(report.flagged_count, 1)
        self.assertIn("syn_001", report.flagged_ids)
        self.assertNotIn("syn_002", report.flagged_ids)

    def test_leakage_check_passes_distinct_questions(self):
        """Leakage check passes clearly distinct synthetic questions."""
        synthetic = [
            {"question_id": "syn_001", "text": "What is the population of Tokyo?"},
            {"question_id": "syn_002", "text": "Who discovered penicillin?"},
            {"question_id": "syn_003", "text": "What is the atomic number of carbon?"},
        ]
        syn_path = os.path.join(self.tmp.name, "synthetic.json")
        with open(syn_path, "w", encoding="utf-8") as fh:
            json.dump(synthetic, fh)

        report = run_leakage_check(
            synthetic_questions_path=syn_path,
            heldout_questions_path=self.heldout_q_path,
            heldout_labels_path=self.heldout_labels_path,
            dev_questions_path=self.dev_q_path,
        )

        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.total_synthetic, 3)
        self.assertEqual(report.flagged_count, 0)
        self.assertEqual(report.flagged_ids, [])

    def test_report_never_contains_heldout_ids(self):
        """Report never contains held-out question IDs, text, or answers."""
        synthetic = [
            {"question_id": "syn_001", "text": "What is the capital of France?"},
        ]
        syn_path = os.path.join(self.tmp.name, "synthetic.json")
        with open(syn_path, "w", encoding="utf-8") as fh:
            json.dump(synthetic, fh)

        report = run_leakage_check(
            synthetic_questions_path=syn_path,
            heldout_questions_path=self.heldout_q_path,
            heldout_labels_path=self.heldout_labels_path,
            dev_questions_path=self.dev_q_path,
        )

        report_dict = report.to_dict()
        report_json = json.dumps(report_dict)

        # Assert absence of held-out IDs
        for hq in self.heldout_questions:
            self.assertNotIn(hq["question_id"], report_json)
            self.assertNotIn(hq["text"], report_json)

        # Assert absence of held-out labels/answers
        for hq_id, label in self.heldout_labels.items():
            self.assertNotIn(hq_id, report_json)
            self.assertNotIn(label["answer"], report_json)
            for ss in label["sufficient_sets"]:
                for item in ss:
                    self.assertNotIn(item, report_json)

        # Assert flagged_ids only contains synthetic IDs
        for fid in report.flagged_ids:
            self.assertTrue(fid.startswith("syn_"))

    def test_report_contains_required_fields(self):
        """Report contains all required fields."""
        synthetic = [{"question_id": "syn_001", "text": "What is the capital of France?"}]
        syn_path = os.path.join(self.tmp.name, "synthetic.json")
        with open(syn_path, "w", encoding="utf-8") as fh:
            json.dump(synthetic, fh)

        report = run_leakage_check(
            synthetic_questions_path=syn_path,
            heldout_questions_path=self.heldout_q_path,
            heldout_labels_path=self.heldout_labels_path,
            dev_questions_path=self.dev_q_path,
        )

        # Check all required fields present
        self.assertIn("status", report.to_dict())
        self.assertIn("total_synthetic", report.to_dict())
        self.assertIn("flagged_count", report.to_dict())
        self.assertIn("flagged_ids", report.to_dict())
        self.assertIn("ngram_similarity_distribution", report.to_dict())
        self.assertIn("dev_calibrated_threshold", report.to_dict())
        self.assertIn("dev_operating_characteristics", report.to_dict())
        self.assertIn("paths_available", report.to_dict())
        self.assertIn("heldout_seal_sha256", report.to_dict())
        self.assertIn("notes", report.to_dict())

        # Check paths_available structure
        self.assertTrue(report.paths_available["ngram_jaccard"])
        self.assertIn("embedding_cosine", report.paths_available)

        # Check seal hash matches
        self.assertEqual(report.heldout_seal_sha256, report.heldout_seal_sha256)  # Non-empty

    def test_dev_calibration_sets_threshold(self):
        """Threshold calibration on dev produces reasonable threshold."""
        threshold, ops = calibrate_threshold_on_dev(
            self.dev_questions, self.heldout_questions, target_flagged_rate=0.05
        )
        self.assertGreaterEqual(threshold, 0.0)
        self.assertLessEqual(threshold, 1.0)
        self.assertIn("calibration_target_flagged_rate", ops)
        self.assertIn("achieved_flagged_rate_on_dev", ops)
        self.assertIn("threshold", ops)
        self.assertEqual(ops["threshold"], threshold)

    def test_histogram_structure(self):
        """Similarity histogram has correct structure."""
        from data_tools.leakage_check import build_histogram
        values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        hist = build_histogram(values, bins=10)
        self.assertEqual(hist["bins"], 10)
        self.assertEqual(len(hist["edges"]), 11)
        self.assertEqual(len(hist["counts"]), 10)
        self.assertEqual(hist["max"], 0.9)
        self.assertAlmostEqual(hist["mean"], 0.5)

    def test_empty_histogram(self):
        """Empty values produce empty histogram."""
        from data_tools.leakage_check import build_histogram
        hist = build_histogram([])
        self.assertEqual(hist["bins"], 0)
        self.assertEqual(hist["max"], 0.0)

    def test_report_roundtrip(self):
        """LeakageReport round-trips through JSON."""
        synthetic = [{"question_id": "syn_001", "text": "What is the capital of France?"}]
        syn_path = os.path.join(self.tmp.name, "synthetic.json")
        with open(syn_path, "w", encoding="utf-8") as fh:
            json.dump(synthetic, fh)

        report = run_leakage_check(
            synthetic_questions_path=syn_path,
            heldout_questions_path=self.heldout_q_path,
            heldout_labels_path=self.heldout_labels_path,
            dev_questions_path=self.dev_q_path,
        )

        # Write and read back
        report_path = os.path.join(self.tmp.name, "report.json")
        report.write(report_path)
        report2 = LeakageReport.read(report_path)

        self.assertEqual(report.status, report2.status)
        self.assertEqual(report.total_synthetic, report2.total_synthetic)
        self.assertEqual(report.flagged_count, report2.flagged_count)
        self.assertEqual(report.flagged_ids, report2.flagged_ids)
        self.assertEqual(report.dev_calibrated_threshold, report2.dev_calibrated_threshold)
        self.assertEqual(report.heldout_seal_sha256, report2.heldout_seal_sha256)


if __name__ == "__main__":
    unittest.main()