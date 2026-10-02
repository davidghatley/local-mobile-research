"""Tests for paired regime conditions: same questions under A and B, never pooled."""

import json
import os
import tempfile
import unittest

from substrate.regime_metadata import (
    CONDITION_A,
    CONDITION_B,
    CONDITIONS,
    REGIME_A,
    REGIME_B,
    RegimeMetadata,
    RegimePairing,
    aggregate_across_regimes,
    aggregate_paired_delta,
    derive_paired_subset,
    derive_regime_metadata,
    evaluate_paired,
    pair_conditions,
    verify_adaptation_exclusion,
    verify_query_corpus_unchanged,
)


class TestRegimeMetadata(unittest.TestCase):
    def setUp(self):
        self.split_map_path = "corpus/split_map.json"

    def test_derive_regime_metadata_roundtrip(self):
        """Regime metadata derives from split map and round-trips via JSON."""
        meta = derive_regime_metadata(self.split_map_path)
        self.assertIsInstance(meta, RegimeMetadata)
        self.assertEqual(meta.split_map_sha256, meta.split_map_sha256)  # non-empty
        self.assertTrue(len(meta.split_map_sha256) == 64)

        # Both regimes should have groups
        self.assertGreater(len(meta.regime_a_groups), 0)
        self.assertGreater(len(meta.regime_b_groups), 0)

        # Regime B groups key on the forward shadow_dev split (legacy heldout accepted)
        for g in meta.regime_b_groups:
            self.assertEqual(g.regime, REGIME_B)
            self.assertIn(g.split, ("shadow_dev", "heldout"))
            self.assertGreaterEqual(g.article_count, 4)

        # Regime A covers the full regime-split population
        for g in meta.regime_a_groups:
            self.assertEqual(g.regime, REGIME_A)
            self.assertIn(g.split, ("shadow_dev", "heldout"))

        # Round-trip through JSON
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "regime_meta.json")
            meta.write(path)
            meta2 = RegimeMetadata.read(path)
            self.assertEqual(meta.split_map_sha256, meta2.split_map_sha256)
            self.assertEqual(len(meta.regime_a_groups), len(meta2.regime_a_groups))
            self.assertEqual(len(meta.regime_b_groups), len(meta2.regime_b_groups))
            for g1, g2 in zip(meta.regime_a_groups, meta2.regime_a_groups):
                self.assertEqual(g1.group_key, g2.group_key)
                self.assertEqual(g1.regime, g2.regime)
            for g1, g2 in zip(meta.regime_b_groups, meta2.regime_b_groups):
                self.assertEqual(g1.group_key, g2.group_key)
                self.assertEqual(g1.regime, g2.regime)

    def test_regime_b_subset_of_shadow_dev_never_train_dev(self):
        """Regime B paired-condition groups are shadow_dev/heldout groups only."""
        meta = derive_regime_metadata(self.split_map_path)

        # Load split map to verify
        with open(self.split_map_path, "r", encoding="utf-8") as fh:
            split_map = json.load(fh)

        groups = split_map.get("groups", {})
        for g in meta.regime_b_groups:
            self.assertIn(g.group_key, groups)
            self.assertIn(groups[g.group_key].get("split"), ("shadow_dev", "heldout"))

        # No regime B group should be train, dev, or private_test
        for g in meta.regime_b_groups:
            self.assertNotIn(
                groups[g.group_key].get("split"), ("train", "dev", "private_test"))

    def test_regime_b_overlaps_a_by_design(self):
        """Paired design: B groups overlap A (NOT a disjoint population)."""
        meta = derive_regime_metadata(self.split_map_path)
        a_keys = {g.group_key for g in meta.regime_a_groups}
        b_keys = {g.group_key for g in meta.regime_b_groups}
        # B is a tagged paired condition over the same population: every B
        # group is also an A group.
        self.assertTrue(b_keys)
        self.assertEqual(b_keys - a_keys, set())

    def test_cross_regime_aggregation_refused(self):
        """aggregate_across_regimes raises on mixed regimes."""
        metrics_a = [
            {"regime": REGIME_A, "accuracy": 0.9, "latency_ms": 100},
            {"regime": REGIME_A, "accuracy": 0.85, "latency_ms": 120},
        ]
        metrics_b = [
            {"regime": REGIME_B, "accuracy": 0.8, "latency_ms": 150},
        ]
        mixed = metrics_a + metrics_b

        # Same regime works
        agg_a = aggregate_across_regimes(metrics_a)
        self.assertEqual(agg_a["regime"], REGIME_A)
        self.assertEqual(agg_a["count"], 2)
        self.assertAlmostEqual(agg_a["accuracy"], 0.875)

        agg_b = aggregate_across_regimes(metrics_b)
        self.assertEqual(agg_b["regime"], REGIME_B)
        self.assertEqual(agg_b["count"], 1)

        # Mixed regimes raises
        with self.assertRaises(ValueError) as cm:
            aggregate_across_regimes(mixed)
        self.assertIn("Refusing to aggregate across regimes", str(cm.exception))
        self.assertIn(REGIME_A, str(cm.exception))
        self.assertIn(REGIME_B, str(cm.exception))

    def test_empty_metrics_returns_empty(self):
        """Aggregating empty list returns empty dict."""
        result = aggregate_across_regimes([])
        self.assertEqual(result, {})

    def test_unknown_regime_raises(self):
        """Unknown regime value raises."""
        with self.assertRaises(ValueError):
            aggregate_across_regimes([{"regime": "unknown_regime", "score": 1.0}])

    def test_regime_b_diverse_topics(self):
        """Regime B selects diverse topics (non-solo preferred, then diverse solo)."""
        meta = derive_regime_metadata(self.split_map_path)
        b_keys = {g.group_key for g in meta.regime_b_groups}

        # Should have at least some non-solo groups if available
        non_solo_b = [k for k in b_keys if not k.startswith("solo:")]
        # The split map has several non-solo shadow_dev groups with >=4 articles
        # (cambridge, corona, jaguar, lincoln, etc.)
        self.assertGreater(len(non_solo_b), 0)

        # Should have diverse domains
        domains = set()
        for k in b_keys:
            if k.startswith("solo:"):
                domains.add(k[5:].split()[0])
            else:
                domains.add(k)
        self.assertGreaterEqual(len(domains), 3)  # At least 3 distinct domains

    def test_manifest_fields_exist(self):
        """RunManifest has the new regime fields."""
        from substrate.manifest import RunManifest
        # Just verify the fields exist in the dataclass
        import dataclasses
        fields = {f.name for f in dataclasses.fields(RunManifest)}
        self.assertIn("regime_a_heldout_groups", fields)
        self.assertIn("regime_b_document_heldout_groups", fields)
        self.assertIn("public_reference_pins_sha256", fields)

    # --- Paired-condition tests (Phase 3) ---

    def test_paired_subset_same_ids_both_conditions(self):
        """Paired subset: the SAME question ids are evaluable under A and B."""
        pairings, _notes = derive_paired_subset(self.split_map_path, "staging")
        self.assertGreater(len(pairings), 0)
        for p in pairings:
            self.assertEqual(tuple(p.conditions), CONDITIONS)
            self.assertTrue(p.question_id)
            self.assertTrue(p.excluded_adaptation_docs)

        # Same ids score under both conditions via one paired evaluation.
        seen = []

        def score_fn(qid, condition):
            seen.append((qid, condition))
            return 1.0 if condition == CONDITION_A else 0.75

        results = evaluate_paired(pairings, score_fn)
        self.assertEqual(len(results), len(pairings))
        by_qid = {r["question_id"]: r for r in results}
        self.assertEqual(set(by_qid), {p.question_id for p in pairings})
        for r in results:
            self.assertIn(CONDITION_A, r)
            self.assertIn(CONDITION_B, r)
        # Every pairing produced exactly one score per condition.
        self.assertEqual(len(seen), 2 * len(pairings))

    def test_paired_subset_selection_rule(self):
        """Paired subset = shadow_dev drafts in Regime B groups, sorted by qid."""
        pairings, _notes = derive_paired_subset(self.split_map_path, "staging")
        meta = derive_regime_metadata(self.split_map_path)
        b_set = {g.group_key for g in meta.regime_b_groups}
        qids = [p.question_id for p in pairings]
        self.assertEqual(qids, sorted(qids))
        self.assertEqual(len(set(qids)), len(qids))
        for p in pairings:
            self.assertIn(p.group, b_set)

    def test_b_docs_excluded_from_adaptation_but_present_at_query_time(self):
        """B source docs excluded from adaptation data, never from retrieval."""
        pairings, _notes = derive_paired_subset(self.split_map_path, "staging")
        self.assertGreater(len(pairings), 0)
        excluded = {t for p in pairings for t in p.excluded_adaptation_docs}

        # Clean adaptation manifest (no excluded docs): no violations.
        self.assertEqual(verify_adaptation_exclusion(pairings, ["unrelated doc"]), [])

        # Leaked adaptation manifest: every leaked pairing flagged.
        leaked = verify_adaptation_exclusion(pairings, list(excluded))
        self.assertGreater(len(leaked), 0)

        # Query-time corpus MUST still contain every excluded doc. The
        # hermetic stand-in for the retrieval corpus here is the full
        # split-map article set (no git-ignored artifacts in unit tests).
        with open(self.split_map_path, "r", encoding="utf-8") as fh:
            split_map = json.load(fh)
        corpus_titles = [
            t for rec in split_map["groups"].values() for t in rec["articles"]
        ]
        self.assertEqual(verify_query_corpus_unchanged(pairings, corpus_titles), [])

        # A corpus missing an excluded doc is an invariant violation.
        pruned = [t for t in corpus_titles
                  if t != pairings[0].excluded_adaptation_docs[0]]
        bad = verify_query_corpus_unchanged(pairings, pruned)
        self.assertGreater(len(bad), 0)

    def test_paired_delta_reporting(self):
        """A-on-paired, B-on-same-paired, and delta reported together."""
        results_a = [
            {"question_id": "q1", "accuracy": 1.0},
            {"question_id": "q2", "accuracy": 0.5},
        ]
        results_b = [
            {"question_id": "q1", "accuracy": 0.75},
            {"question_id": "q2", "accuracy": 0.25},
        ]
        joined = pair_conditions(results_a, results_b)
        self.assertEqual([j["question_id"] for j in joined], ["q1", "q2"])
        report = aggregate_paired_delta(joined)
        self.assertEqual(report["n_paired"], 2)
        self.assertAlmostEqual(report["metrics"]["accuracy"]["mean_corpus_known"], 0.75)
        self.assertAlmostEqual(
            report["metrics"]["accuracy"]["mean_document_heldout"], 0.5)
        self.assertAlmostEqual(report["metrics"]["accuracy"]["mean_delta"], -0.25)

    def test_unrelated_populations_cannot_masquerade_as_paired_delta(self):
        """Mismatched id sets are refused (no masquerading as paired delta)."""
        results_a = [{"question_id": "q1", "accuracy": 1.0}]
        results_other = [{"question_id": "qX", "accuracy": 0.0}]
        with self.assertRaises(ValueError) as cm:
            pair_conditions(results_a, results_other)
        self.assertIn("mismatched populations", str(cm.exception))

        # Duplicate ids within one side are refused too.
        dupes = [
            {"question_id": "q1", "accuracy": 1.0},
            {"question_id": "q1", "accuracy": 0.5},
        ]
        with self.assertRaises(ValueError):
            pair_conditions(dupes, [{"question_id": "q1", "accuracy": 0.0}])

        # aggregate_paired_delta refuses empty input and missing conditions.
        with self.assertRaises(ValueError):
            aggregate_paired_delta([])
        with self.assertRaises(ValueError):
            aggregate_paired_delta([{"question_id": "q1", CONDITION_A: {"acc": 1.0}}])

    def test_pairing_roundtrip(self):
        """RegimePairing enforces the two-condition contract on deserialization."""
        p = RegimePairing(
            question_id="q1",
            group="cambridge",
            conditions=CONDITIONS,
            source_articles=["a:cambridge"],
            excluded_adaptation_docs=["Cambridge"],
        )
        p2 = RegimePairing.from_dict(p.to_dict())
        self.assertEqual(p, p2)
        bad = p.to_dict()
        bad["conditions"] = ["corpus_known"]
        with self.assertRaises(ValueError):
            RegimePairing.from_dict(bad)


if __name__ == "__main__":
    unittest.main()
