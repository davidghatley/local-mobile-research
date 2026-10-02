"""Regression: shadow_dev groups must resolve in the data tooling.

An independent freeze review found a functional regression: after the
split-map migration (heldout -> shadow_dev), data_tools.derive.group_articles
still accepted only the pre-migration vocabulary and raised on all 32 shadow_dev
groups. These tests pin the current vocabulary.
"""

import json
import os
import unittest

from data_tools.derive import group_articles
from substrate.splits import SPLITS, norm_title

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT_MAP = os.path.join(REPO_ROOT, "corpus", "split_map.json")
REGIME_B_GROUPS = ("cambridge", "corona", "jaguar", "lincoln", "washington")


def load_split_map():
  with open(SPLIT_MAP, "r", encoding="utf-8") as fh:
    return json.load(fh)


class TestGroupArticlesAcceptsCurrentVocabulary(unittest.TestCase):
  def setUp(self):
    self.sm = load_split_map()

  def test_every_split_map_group_resolves(self):
    """No group in the live split map may be rejected by group_articles."""
    failures = []
    for gk in self.sm["groups"]:
      try:
        articles, split = group_articles(self.sm, gk)
      except ValueError as exc:
        failures.append(f"{gk}: {exc}")
        continue
      self.assertTrue(articles, gk)
      self.assertEqual(split, self.sm["groups"][gk]["split"], gk)
    self.assertEqual(failures, [], f"group_articles rejected live groups: {failures}")

  def test_shadow_dev_groups_accepted(self):
    shadow = [gk for gk, r in self.sm["groups"].items() if r["split"] == "shadow_dev"]
    self.assertGreater(len(shadow), 0, "split map has no shadow_dev groups")
    for gk in shadow:
      articles, split = group_articles(self.sm, gk)
      self.assertEqual(split, "shadow_dev", gk)
      self.assertTrue(articles, gk)

  def test_regime_b_groups_resolve(self):
    for gk in REGIME_B_GROUPS:
      _articles, split = group_articles(self.sm, gk)
      self.assertEqual(split, "shadow_dev", gk)

  def test_train_and_dev_still_accepted(self):
    for want in ("train", "dev"):
      groups = [gk for gk, r in self.sm["groups"].items() if r["split"] == want]
      self.assertGreater(len(groups), 0, want)
      for gk in groups:
        _a, split = group_articles(self.sm, gk)
        self.assertEqual(split, want, gk)

  def test_unknown_group_still_rejected(self):
    with self.assertRaises(ValueError):
      group_articles(self.sm, "no-such-group")

  def test_group_with_invalid_split_still_rejected(self):
    bad = {"groups": {"g": {"split": "private_test", "articles": ["X"]}}}
    with self.assertRaises(ValueError):
      group_articles(bad, "g")

  def test_legacy_heldout_name_still_accepted(self):
    """Backward compatibility with pre-migration split maps."""
    legacy = {"groups": {"g": {"split": "heldout", "articles": ["X"]}}}
    _a, split = group_articles(legacy, "g")
    self.assertEqual(split, "heldout")

  def test_splits_vocabulary_matches_live_map(self):
    used = {r["split"] for r in self.sm["groups"].values()}
    unknown = used - set(SPLITS)
    self.assertEqual(unknown, set(),
                     f"split map uses splits absent from SPLITS: {unknown}")
    self.assertIn("shadow_dev", SPLITS)
    self.assertNotIn("heldout", SPLITS)

  def test_norm_title_roundtrip_for_group_articles(self):
    """group_articles returns titles that norm_title keys stably."""
    for gk in ("cambridge", "washington"):
      articles, _s = group_articles(self.sm, gk)
      keys = [norm_title(a) for a in articles]
      self.assertEqual(len(keys), len(set(keys)), gk)


if __name__ == "__main__":
  unittest.main()
