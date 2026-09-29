"""Focused QA-provenance adversarial tests. All fixtures SYNTHETIC.

Proves Decision A+B: no-provenance bypass closed, public_reference dev-only
exception, strict source/group validation, shared-corpus access across splits.
"""

import unittest

from substrate.splits import (
  build_article_index,
  validate_group_map,
  validate_question_provenance,
)
from substrate.types import CorpusNode


def article(nid, title, group=None):
  meta = {"split_group": group} if group else {}
  return CorpusNode(node_id=nid, kind="article", text=title,
                    parent_id="cl0", meta=meta)


def corpus_train_dev_held():
  # SYNTHETIC corpus: one article per split-group, titles unambiguous.
  return [
    CorpusNode(node_id="c0", kind="corpus", text="root"),
    CorpusNode(node_id="cl0", kind="cluster", text="c", parent_id="c0"),
    article("a1", "Alpha", "g-train"),
    article("a2", "Beta", "g-dev"),
    article("a3", "Gamma", "g-held"),
  ]


MAP_3WAY = {
  "seed": "s",
  "groups": {
    "g-train": {"split": "train", "articles": ["Alpha"]},
    "g-dev": {"split": "dev", "articles": ["Beta"]},
    "g-held": {"split": "heldout", "articles": ["Gamma"]},
  },
}

MAP_GROUPS = {"g-train": "train", "g-dev": "dev", "g-held": "heldout"}


def controlled(qid, split, sources, group):
  return {"question_id": qid, "text": "synthetic?", "split": split,
          "meta": {"source_articles": sources, "group": group}}


def public(qid, split, **meta):
  base = {"source_benchmark": "bench", "source_revision": "rev1",
          "original_question_id": "orig-1", "category": "public_reference"}
  base.update(meta)
  return {"question_id": qid, "text": "synthetic?", "split": split, "meta": base}


def check(questions, **kw):
  params = {"article_index": build_article_index(corpus_train_dev_held()),
            "map_groups": MAP_GROUPS,
            "article_to_group": {"alpha": "g-train", "beta": "g-dev", "gamma": "g-held"},
            "split_seed": "s",
            "use_map_splits": True}
  params.update(kw)
  return validate_question_provenance(questions, **params)


class TestNoProvenanceBypass(unittest.TestCase):
  def test_missing_meta_rejected(self):
    out = check([{"question_id": "q", "text": "t?", "split": "train"}])
    self.assertTrue(out["errors"])
    self.assertNotIn("q", out["results"])

  def test_empty_meta_rejected(self):
    out = check([{"question_id": "q", "text": "t?", "split": "dev", "meta": {}}])
    self.assertTrue(out["errors"])

  def test_group_only_without_sources_rejected(self):
    q = {"question_id": "q", "text": "t?", "split": "train", "meta": {"group": "g-train"}}
    out = check([q])
    self.assertTrue(any("source_articles" in e for e in out["errors"]))

  def test_sources_only_without_group_rejected(self):
    q = {"question_id": "q", "text": "t?", "split": "train",
         "meta": {"source_articles": ["Alpha"]}}
    out = check([q])
    self.assertTrue(any("explicit group" in e for e in out["errors"]))

  def test_unknown_group_rejected(self):
    out = check([controlled("q", "train", ["Alpha"], "g-nope")])
    self.assertTrue(any("unknown group" in e for e in out["errors"]))


class TestSourceValidation(unittest.TestCase):
  def test_sources_not_list_rejected(self):
    q = {"question_id": "q", "text": "t?", "split": "train",
         "meta": {"source_articles": "Alpha", "group": "g-train"}}
    self.assertTrue(check([q])["errors"])

  def test_empty_sources_rejected(self):
    q = {"question_id": "q", "text": "t?", "split": "train",
         "meta": {"source_articles": [], "group": "g-train"}}
    self.assertTrue(check([q])["errors"])

  def test_empty_string_source_rejected(self):
    out = check([controlled("q", "train", [""], "g-train")])
    self.assertTrue(out["errors"])

  def test_nonstring_source_rejected(self):
    out = check([controlled("q", "train", [42], "g-train")])
    self.assertTrue(out["errors"])

  def test_unknown_source_rejected(self):
    out = check([controlled("q", "train", ["Zzz Nonexistent"], "g-train")])
    self.assertTrue(any("unknown source" in e for e in out["errors"]))

  def test_ambiguous_title_rejected(self):
    nodes = corpus_train_dev_held() + [article("a9", "ALPHA", "g-dev")]
    index = build_article_index(nodes)
    out = validate_question_provenance(
      [controlled("q", "train", ["Alpha"], "g-train")],
      article_index=index, map_groups=MAP_GROUPS,
      article_to_group={"alpha": "g-train", "beta": "g-dev", "gamma": "g-held"},
      split_seed="s", use_map_splits=True)
    self.assertTrue(any("ambiguous" in e for e in out["errors"]))

  def test_canonical_node_id_accepted(self):
    out = check([controlled("q", "dev", ["a2"], "g-dev")])
    self.assertEqual(out["errors"], [])
    self.assertEqual(out["results"]["q"]["sources"], ["a2"])

  def test_inconsistent_group_rejected(self):
    out = check([controlled("q", "dev", ["Alpha"], "g-dev")])
    self.assertTrue(any("inconsistent group" in e for e in out["errors"]))

  def test_cross_split_multihop_rejected(self):
    out = check([controlled("q", "train", ["Alpha", "Beta"], "g-train")])
    self.assertTrue(any("multiple splits" in e for e in out["errors"]))

  def test_wrong_declared_split_rejected(self):
    out = check([controlled("q", "dev", ["Alpha"], "g-train")])
    self.assertTrue(any("declared split" in e for e in out["errors"]))

  def test_valid_controlled_accepted(self):
    out = check([controlled("q", "heldout", ["Gamma"], "g-held")])
    self.assertEqual(out["errors"], [])
    res = out["results"]["q"]
    self.assertEqual((res["category"], res["group"], res["ground_truth"]),
                     ("controlled", "g-held", "known"))


class TestSharedCorpus(unittest.TestCase):
  def test_same_article_set_serves_all_splits(self):
    # One shared corpus validates train/dev/heldout QA alike; resolution
    # never filters the corpus by split.
    questions = [
      controlled("q1", "train", ["Alpha"], "g-train"),
      controlled("q2", "dev", ["Beta"], "g-dev"),
      controlled("q3", "heldout", ["Gamma"], "g-held"),
    ]
    out = check(questions)
    self.assertEqual(out["errors"], [])
    self.assertEqual(set(out["results"]), {"q1", "q2", "q3"})

  def test_error_text_carries_no_content(self):
    out = check([{"question_id": "q", "text": "SECRET-TEXT", "split": "train"}])
    self.assertTrue(out["errors"])
    self.assertFalse(any("SECRET-TEXT" in e for e in out["errors"]))


class TestPublicReference(unittest.TestCase):
  def test_valid_public_dev_accepted(self):
    out = check([public("q", "dev")])
    self.assertEqual(out["errors"], [])
    self.assertEqual(out["results"]["q"]["category"], "public_reference")

  def test_public_train_rejected(self):
    self.assertTrue(check([public("q", "train")])["errors"])

  def test_public_heldout_rejected(self):
    self.assertTrue(check([public("q", "heldout")])["errors"])

  def test_public_missing_benchmark_fields_rejected(self):
    q = {"question_id": "q", "text": "t?", "split": "dev",
         "meta": {"category": "public_reference"}}
    out = check([q])
    self.assertTrue(any("source_benchmark" in e or "missing" in e for e in out["errors"]))

  def test_public_without_sources_unknown_not_zero(self):
    out = check([public("q", "dev")])
    self.assertEqual(out["results"]["q"]["ground_truth"], "unknown")

  def test_public_unresolvable_sources_accepted_unknown(self):
    out = check([public("q", "dev", source_articles=["Not In Corpus"])])
    self.assertEqual(out["errors"], [])
    self.assertEqual(out["results"]["q"]["ground_truth"], "unknown")

  def test_public_resolvable_sources_known(self):
    out = check([public("q", "dev", source_articles=["Beta"])])
    self.assertEqual(out["errors"], [])
    self.assertEqual(out["results"]["q"]["ground_truth"], "known")

  def test_unknown_category_rejected(self):
    q = {"question_id": "q", "text": "t?", "split": "dev",
         "meta": {"category": "mystery", "source_articles": ["Beta"], "group": "g-dev"}}
    self.assertTrue(any("unknown question category" in e for e in check([q])["errors"]))


class TestSeededMode(unittest.TestCase):
  def test_derived_group_split_enforced(self):
    from substrate.splits import assign_split

    index = build_article_index(corpus_train_dev_held())
    want = assign_split("g-seed", "seed1")
    other = "dev" if want != "dev" else "train"
    ok_q = controlled("q1", want, ["Alpha"], "g-seed")
    # Node Alpha carries split_group g-train; question claims g-seed.
    out = validate_question_provenance(
      [ok_q], article_index=index, map_groups={}, article_to_group={},
      split_seed="seed1", use_map_splits=False)
    self.assertTrue(any("inconsistent group" in e for e in out["errors"]))
    bad_q = controlled("q2", other, ["Alpha"], "g-train")
    out2 = validate_question_provenance(
      [bad_q], article_index=index, map_groups={}, article_to_group={},
      split_seed="seed1", use_map_splits=False)
    # Node corroboration passes (g-train); derived split decides.
    want2 = assign_split("g-train", "seed1")
    if other == want2:
      self.assertEqual(out2["errors"], [])
    else:
      self.assertTrue(any("declared split" in e for e in out2["errors"]))

  def test_mapless_nodes_without_group_meta_gap(self):
    nodes = [CorpusNode(node_id="c0", kind="corpus", text="r"),
             CorpusNode(node_id="cl0", kind="cluster", text="c", parent_id="c0"),
             CorpusNode(node_id="a1", kind="article", text="Solo", parent_id="cl0")]
    out = validate_question_provenance(
      [controlled("q", "train", ["Solo"], "g-x")],
      article_index=build_article_index(nodes), map_groups={}, article_to_group={},
      split_seed="seed1", use_map_splits=False)
    # Explicit claim stands in seeded mode; derived split decides pass/fail.
    from substrate.splits import assign_split

    if assign_split("g-x", "seed1") == "train":
      self.assertEqual(out["errors"], [])
    else:
      self.assertTrue(any("declared split" in e for e in out["errors"]))


if __name__ == "__main__":
  unittest.main()
