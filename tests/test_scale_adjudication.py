"""Tests for the scale-tier adjudication rule (Issue 4).

The invariant under test: a retrieved SCALE passage is not automatically a
false positive, and a retrieved CORE passage is never sent to adjudication.
"""

import json
import os
import unittest

from eval.scale_adjudication import (
  ADJUDICATED_CLASSES,
  MECHANICAL_CLASSES,
  adjudicate,
  is_scale_node,
  needs_adjudication,
  scale_class_for,
)
from eval.scale_adjudication import _slugify as scale_slug

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSIFICATION = os.path.join(REPO_ROOT, "corpus", "scale", "scale_classification.json")


class TestNamespaceDetection(unittest.TestCase):
  def test_scale_prefixes_detected(self):
    for nid in ("d:world_war_ii", "ds:world_war_ii:00:000", "dp:world_war_ii:00:000",
                "dt:world_war_ii:00:000:00", "dc:history"):
      self.assertTrue(is_scale_node(nid), nid)

  def test_core_prefixes_not_detected(self):
    for nid in ("a:world_war_ii", "s:a:b:00", "p:a:b:00:000", "t:a:b:00:000:00",
                "cluster:history", "corpus:pilot", "corpus:scale-distractors"):
      # corpus:scale-distractors is the scale ROOT, not a retrievable passage;
      # it must not be adjudicated as a passage.
      if nid == "corpus:scale-distractors":
        self.assertFalse(is_scale_node(nid))
      else:
        self.assertFalse(is_scale_node(nid), nid)

  def test_empty_is_not_scale(self):
    self.assertFalse(is_scale_node(""))


class TestCoreIsNeverAdjudicated(unittest.TestCase):
  def test_core_nodes_score_mechanically(self):
    for nid in ("p:superconductivity:01:000", "t:saturn:00:000:00"):
      verdict = adjudicate(nid)
      self.assertEqual(verdict.layer, "core")
      self.assertFalse(verdict.needs_adjudication, nid)
      self.assertIsNone(verdict.scale_class)
      self.assertFalse(needs_adjudication(nid))

  def test_core_nodes_have_no_scale_class(self):
    self.assertIsNone(scale_class_for("p:superconductivity:01:000"))


class TestConfusableScaleRequiresAdjudication(unittest.TestCase):
  def test_confusable_examples_require_adjudication(self):
    # These are the deliberate confusables named in the tier's candidate list.
    for title in ("World War II", "Nile", "Roman Empire", "Lion", "Tiger"):
      scale_nid = f"dp:{scale_slug(title)}:00:000"
      self.assertTrue(is_scale_node(scale_nid))
      self.assertTrue(needs_adjudication(scale_nid),
                      f"{title} is a documented confusable and must be adjudicated")

  def test_verdict_explains_itself(self):
    v = adjudicate("dp:world_war_ii:00:000")
    self.assertEqual(v.layer, "scale")
    self.assertTrue(v.needs_adjudication)
    self.assertIn("false positive", v.reason)
    self.assertIn("layer membership alone", v.reason)

  def test_unclassified_scale_node_fails_safe(self):
    v = adjudicate("dp:definitely_not_in_classification_xyz:00:000")
    self.assertEqual(v.layer, "scale")
    self.assertIsNone(v.scale_class)
    self.assertTrue(v.needs_adjudication,
                    "unknown scale node must adjudicate, never assume irrelevant")
    self.assertIn("no classification entry", v.reason)


class TestClassificationArtifactConsistency(unittest.TestCase):
  @unittest.skipUnless(os.path.isfile(CLASSIFICATION), "scale classification absent")
  def test_counts_sum_to_940(self):
    with open(CLASSIFICATION, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    counts = data["counts"]
    self.assertEqual(sum(counts.values()), 940)
    self.assertEqual(counts.get("redirect_stub"), 110)
    self.assertEqual(counts.get("unknown"), 0)
    for cls in counts:
      self.assertIn(cls, ADJUDICATED_CLASSES + MECHANICAL_CLASSES, cls)

  @unittest.skipUnless(os.path.isfile(CLASSIFICATION), "scale classification absent")
  def test_every_listed_article_resolves(self):
    with open(CLASSIFICATION, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    # Resolve via the tier manifest's AUTHORITATIVE node ids, not a title
    # slug: "ABBA" and "Abba" are distinct articles whose titles collide on
    # one slug, and the builder disambiguates with a ~<pageid> suffix. A
    # title-derived lookup cannot tell them apart; a node-id lookup can.
    tier_path = os.path.join(REPO_ROOT, "corpus", "scale", "tier_1k.json")
    if not os.path.isfile(tier_path):
      self.skipTest("tier manifest absent")
    with open(tier_path, "r", encoding="utf-8") as fh:
      tier = json.load(fh)
    by_title = {a["title"]: a["class"] for a in data["articles"]}
    seen = set()
    for snap in tier.get("snapshots", []):
      node_id = snap.get("node_id", "")
      title = snap.get("normalized_title", "")
      if not node_id.startswith("d:") or title not in by_title:
        continue
      seen.add(title)
      expected = by_title[title]
      self.assertEqual(scale_class_for(f"{node_id}:00:000"), expected, title)
      self.assertEqual(needs_adjudication(f"{node_id}:00:000"),
                       expected in ADJUDICATED_CLASSES, title)
    # Every classified article must have a real node id, or it is unreachable.
    self.assertEqual(len(seen), len(by_title),
                     f"classified but unnodeable: {sorted(set(by_title) - seen)[:5]}")

  @unittest.skipUnless(os.path.isfile(CLASSIFICATION), "scale classification absent")
  def test_pageid_suffixed_slug_resolves(self):
    """Collision-decorated slugs must resolve to their OWN article's class.

    ``d:abba`` is ABBA (background); ``d:abba~17270720`` is Abba (a redirect
    stub). A title-slug map collapses these and silently mislabels one.
    """
    self.assertEqual(scale_class_for("dp:abba:00:000"), "background")
    self.assertEqual(scale_class_for("dp:abba~17270720:00:000"), "redirect_stub")

  @unittest.skipUnless(os.path.isfile(CLASSIFICATION), "scale classification absent")
  def test_at_least_one_confusable_exists(self):
    with open(CLASSIFICATION, "r", encoding="utf-8") as fh:
      data = json.load(fh)
    self.assertGreater(data["counts"].get("confusable_adversarial", 0), 0,
                       "a tier with no confusables would make this rule untestable")


if __name__ == "__main__":
  unittest.main()
