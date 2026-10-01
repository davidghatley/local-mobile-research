"""Tests for regime metadata: machine-readability, round-trip, cross-regime refusal."""

import json
import os
import tempfile
import unittest

from substrate.regime_metadata import (
    REGIME_A,
    REGIME_B,
    RegimeMetadata,
    aggregate_across_regimes,
    derive_regime_metadata,
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

        # Regime B groups must be subset of heldout groups with >=4 articles
        for g in meta.regime_b_groups:
            self.assertEqual(g.regime, REGIME_B)
            self.assertEqual(g.split, "heldout")
            self.assertGreaterEqual(g.article_count, 4)

        # Regime A groups are the remaining heldout groups
        for g in meta.regime_a_groups:
            self.assertEqual(g.regime, REGIME_A)
            self.assertEqual(g.split, "heldout")

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

    def test_regime_b_subset_of_heldout_never_train_dev(self):
        """Regime B groups are strictly a subset of heldout groups."""
        meta = derive_regime_metadata(self.split_map_path)

        # Load split map to verify
        with open(self.split_map_path, "r", encoding="utf-8") as fh:
            split_map = json.load(fh)

        groups = split_map.get("groups", {})
        for g in meta.regime_b_groups:
            self.assertIn(g.group_key, groups)
            self.assertEqual(groups[g.group_key].get("split"), "heldout")

        # No regime B group should be train or dev
        for g in meta.regime_b_groups:
            self.assertNotEqual(groups[g.group_key].get("split"), "train")
            self.assertNotEqual(groups[g.group_key].get("split"), "dev")

    def test_regime_a_and_b_disjoint(self):
        """Regime A and B groups are disjoint."""
        meta = derive_regime_metadata(self.split_map_path)
        a_keys = {g.group_key for g in meta.regime_a_groups}
        b_keys = {g.group_key for g in meta.regime_b_groups}
        self.assertEqual(a_keys & b_keys, set())

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
        # The split map has several non-solo heldout groups with >=4 articles
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


if __name__ == "__main__":
    unittest.main()