"""Corpus hierarchy tests. Fixtures are SYNTHETIC infrastructure checks, not research data."""

import unittest

from substrate.corpus import corpus_hash, nodes_from_jsonl, nodes_to_jsonl, validate_hierarchy
from substrate.types import CorpusNode


def synthetic_mini_corpus():
  # SYNTHETIC-ONLY fixture for schema validation.
  return [
    CorpusNode(node_id="c0", kind="corpus", text="root"),
    CorpusNode(node_id="cl0", kind="cluster", text="places", parent_id="c0"),
    CorpusNode(node_id="a0", kind="article", text="Springfield", parent_id="cl0",
               aliases=("Springfld",)),
    CorpusNode(node_id="s0", kind="section", text="History", parent_id="a0"),
    CorpusNode(node_id="p0", kind="paragraph", text="Founded in 1820.", parent_id="s0"),
    CorpusNode(node_id="t0", kind="sentence", text="Founded in 1820.", parent_id="p0"),
  ]


class TestHierarchy(unittest.TestCase):
  def test_valid_mini_corpus(self):
    self.assertEqual(validate_hierarchy(synthetic_mini_corpus()), [])

  def test_wrong_parent_kind_rejected(self):
    nodes = synthetic_mini_corpus()
    bad = CorpusNode(node_id="sX", kind="section", text="x", parent_id="p0")
    errors = validate_hierarchy(nodes + [bad])
    self.assertTrue(any("expected parent kind article" in e for e in errors))

  def test_missing_parent_rejected(self):
    nodes = synthetic_mini_corpus()
    bad = CorpusNode(node_id="pX", kind="paragraph", text="x", parent_id="nope")
    self.assertTrue(validate_hierarchy(nodes + [bad]))

  def test_dangling_cross_link_rejected(self):
    nodes = synthetic_mini_corpus()
    broken = CorpusNode(node_id="a0", kind="article", text="Springfield",
                        parent_id="cl0", links=("ghost",))
    rest = [n for n in nodes if n.node_id != "a0"] + [broken]
    self.assertTrue(any("cross-link" in e for e in validate_hierarchy(rest)))

  def test_hash_deterministic_and_order_independent(self):
    nodes = synthetic_mini_corpus()
    self.assertEqual(corpus_hash(nodes), corpus_hash(list(reversed(nodes))))

  def test_jsonl_roundtrip(self):
    nodes = synthetic_mini_corpus()
    self.assertEqual(nodes_from_jsonl(nodes_to_jsonl(nodes)), sorted(nodes, key=lambda n: n.node_id))


if __name__ == "__main__":
  unittest.main()
