"""Same-split cross-group policy tests. ALL fixtures SYNTHETIC.

Multi-group chains are ALLOWED iff every involved group sits in the SAME
data split (train->train ALLOW; train->heldout, dev->heldout, train->dev
REJECT). Split equality — never group equality — is the leakage gate.
"""

import json
import unittest

from data_tools.qa_schema import draft_to_question_entry, to_retriever_input
from data_tools.verify import draft_content_hash, verify_draft
from substrate.splits import validate_question_provenance


def nodes():
  # SYNTHETIC mini-corpus: two train groups, two dev groups, one heldout.
  return [
    {"node_id": "a:alpha", "kind": "article", "text": "Alpha",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gA-train"}},
    {"node_id": "a:beta", "kind": "article", "text": "Beta",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gB-train"}},
    {"node_id": "a:gamma", "kind": "article", "text": "Gamma",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gC-dev"}},
    {"node_id": "a:eps", "kind": "article", "text": "Epsilon",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gE-dev"}},
    {"node_id": "a:delta", "kind": "article", "text": "Delta",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gD-held"}},
    {"node_id": "a:dup1", "kind": "article", "text": "Ditto",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gA-train"}},
    {"node_id": "a:dup2", "kind": "article", "text": "ditto ",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gB-train"}},
    {"node_id": "p:a:1", "kind": "paragraph", "text": "First fact here.",
     "parent_id": "a:alpha", "links": []},
    {"node_id": "p:b:1", "kind": "paragraph", "text": "Beta ledger quarry zebra.",
     "parent_id": "a:beta", "links": []},
    {"node_id": "p:g:1", "kind": "paragraph", "text": "Gamma words here.",
     "parent_id": "a:gamma", "links": []},
    {"node_id": "p:e:1", "kind": "paragraph", "text": "Epsilon harbor atlas.",
     "parent_id": "a:eps", "links": []},
    {"node_id": "p:d:1", "kind": "paragraph", "text": "Delta harbor lantern atlas.",
     "parent_id": "a:delta", "links": []},
    {"node_id": "p:a:2", "kind": "paragraph", "text": "Second fact here.",
     "parent_id": "a:alpha", "links": []},
  ]


MAP = {"gA-train": "train", "gB-train": "train", "gC-dev": "dev",
       "gE-dev": "dev", "gD-held": "heldout"}
A2G = {"alpha": "gA-train", "beta": "gB-train", "gamma": "gC-dev",
       "epsilon": "gE-dev", "delta": "gD-held",
       "ditto": "gA-train"}


def article_index():
  from substrate.splits import build_article_index
  from substrate.types import CorpusNode
  ns = [CorpusNode(node_id=n["node_id"], kind=n["kind"], text=n["text"],
                   parent_id=n.get("parent_id"),
                   meta=n.get("meta", {})) for n in nodes()
        if n["kind"] == "article"]
  return build_article_index(ns)


def ctx(**kw):
  params = {"article_index": article_index(), "map_groups": MAP,
            "article_to_group": A2G}
  params.update(kw)
  return params


TEXT = {"p:a:1": "First fact here.", "p:b:1": "Beta ledger quarry zebra.",
        "p:g:1": "Gamma words here.", "p:e:1": "Epsilon harbor atlas.",
        "p:d:1": "Delta harbor lantern atlas."}


def draft(qid, split, group, sources, span_ids, neg_id="p:a:2",
          evidence_groups=None):
  meta = {"source_articles": list(sources), "group": group}
  if evidence_groups is not None:
    meta["evidence_groups"] = list(evidence_groups)
  d = {
    "question_id": qid, "text": "Which item is described first?",
    "split": split, "question_type": "factoid",
    "meta": meta,
    "evidence": {"sufficient_sets": [
      [{"node_id": s, "text": TEXT[s]} for s in span_ids]],
      "is_multi_hop": False, "reference_hop_chains": []},
    "hard_negatives": [{"node_id": neg_id,
                        "negative_type": "sibling_paragraph",
                        "reviewed": True}],
    "labels": {"answer_text": "the first item", "answerability": "answerable"},
    "provenance": {"author": "synthetic-author", "author_model": "synthetic-1",
                   "verifier": "synthetic-verifier",
                   "verifier_model": "synthetic-2",
                   "decision": "approve",
                   "rationale": "synthetic approval rationale",
                   "content_hash": ""},
  }
  d["provenance"]["content_hash"] = draft_content_hash(d)
  return d


def verify(d):
  return verify_draft(d, nodes(), **ctx())


class TestSameSplitCrossGroup(unittest.TestCase):
  def test_train_to_train_allow(self):
    d = draft("q", "train", "gA-train", ["Alpha", "Beta"], ["p:a:1", "p:b:1"],
              evidence_groups=["gA-train", "gB-train"])
    self.assertEqual(verify(d), [])

  def test_train_to_train_needs_evidence_groups(self):
    # Same-split cross-group WITHOUT a declared evidence_groups list is
    # rejected on coverage: absent means [meta.group] only.
    d = draft("q", "train", "gA-train", ["Alpha", "Beta"], ["p:a:1", "p:b:1"])
    self.assertTrue(any("evidence_groups" in e for e in verify(d)))

  def test_dev_to_dev_allow(self):
    d = draft("q", "dev", "gC-dev", ["Gamma", "Epsilon"], ["p:g:1", "p:e:1"],
              neg_id="p:a:1",
              evidence_groups=["gC-dev", "gE-dev"])
    self.assertEqual(verify(d), [])

  def test_train_to_heldout_reject(self):
    d = draft("q", "train", "gA-train", ["Alpha", "Delta"], ["p:a:1", "p:d:1"],
              evidence_groups=["gA-train", "gD-held"])
    errs = verify(d)
    self.assertTrue(any("split" in e for e in errs))

  def test_dev_to_heldout_reject(self):
    d = draft("q", "dev", "gC-dev", ["Gamma", "Delta"], ["p:g:1", "p:d:1"],
              neg_id="p:a:1",
              evidence_groups=["gC-dev", "gD-held"])
    errs = verify(d)
    self.assertTrue(any("split" in e for e in errs))

  def test_train_to_dev_reject(self):
    d = draft("q", "train", "gA-train", ["Alpha", "Gamma"], ["p:a:1", "p:g:1"],
              evidence_groups=["gA-train", "gC-dev"])
    errs = verify(d)
    self.assertTrue(any("split" in e for e in errs))

  def test_declared_split_mismatch_reject(self):
    # Evidence sits in train but the draft declares dev.
    d = draft("q", "dev", "gA-train", ["Alpha"], ["p:a:1"])
    self.assertTrue(any("declared split" in e for e in verify(d)))

  def test_declared_group_split_mismatch_reject(self):
    # Declared group gC-dev sits in dev but the draft declares train.
    d = draft("q", "train", "gC-dev", ["Alpha"], ["p:a:1"])
    self.assertTrue(any("declared split" in e for e in verify(d)))

  def test_missing_source_reject(self):
    # Beta evidence article not declared: group membership alone is
    # insufficient, the article itself must be listed.
    d = draft("q", "train", "gA-train", ["Alpha"], ["p:b:1"])
    self.assertTrue(any("missing" in e and "source_articles" in e
                        for e in verify(d)))

  def test_unresolvable_source_reject(self):
    d = draft("q", "train", "gA-train", ["Zzz Nonexistent"], ["p:a:1"])
    self.assertTrue(any("unresolvable or ambiguous" in e for e in verify(d)))

  def test_ambiguous_source_reject(self):
    d = draft("q", "train", "gA-train", ["Ditto"], ["p:a:1"])
    self.assertTrue(any("ambiguous" in e for e in verify(d)))


class TestSubstrateGate(unittest.TestCase):
  def gate(self, split, sources, group, **meta_kw):
    meta = {"source_articles": sources, "group": group}
    meta.update(meta_kw)
    q = {"question_id": "q", "text": "synthetic?", "split": split,
         "meta": meta}
    return validate_question_provenance([q], **ctx(), split_seed="",
                                        use_map_splits=True)

  def test_same_split_multigroup_passes_with_audit_fields(self):
    out = self.gate("train", ["Alpha", "Beta"], "gA-train",
                    evidence_groups=["gA-train", "gB-train"])
    self.assertEqual(out["errors"], [])
    res = out["results"]["q"]
    self.assertEqual(res["source_groups"], ["gA-train", "gB-train"])
    self.assertEqual(res["source_splits"], ["train"])
    self.assertEqual(res["evidence_groups"], ["gA-train", "gB-train"])

  def test_cross_split_multigroup_rejected(self):
    out = self.gate("train", ["Alpha", "Delta"], "gA-train")
    self.assertTrue(any("multiple splits" in e for e in out["errors"]))

  def test_evidence_groups_must_include_declared_group(self):
    out = self.gate("train", ["Alpha", "Beta"], "gA-train",
                    evidence_groups=["gB-train"])
    self.assertTrue(any("declared group" in e for e in out["errors"]))

  def test_evidence_groups_outside_split_rejected(self):
    out = self.gate("train", ["Alpha"], "gA-train",
                    evidence_groups=["gA-train", "gD-held"])
    self.assertTrue(any("declared split" in e for e in out["errors"]))


class TestRetrieverProjection(unittest.TestCase):
  def test_projection_strips_all_hints(self):
    d = draft("q", "train", "gA-train", ["Alpha", "Beta"], ["p:a:1", "p:b:1"],
              evidence_groups=["gA-train", "gB-train"])
    d["meta"]["semantic_status"] = "pending"
    runtime = to_retriever_input(draft_to_question_entry(d))
    self.assertEqual(set(runtime), {"question_id", "text"})
    blob = json.dumps(runtime)
    for hint in ("Alpha", "Beta", "gA-train", "gB-train", "factoid",
                 "evidence_groups", "source_articles", "pending"):
      self.assertNotIn(hint, blob)


if __name__ == "__main__":
  unittest.main()
