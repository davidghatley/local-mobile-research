"""Semantic-audit machinery tests. ALL fixtures SYNTHETIC.

Code enforces STRUCTURE and PROVENANCE only: field presence, closed
decision vocabulary, reviewer != author, corpus_revision present, hop
gloss presence/alignment. It NEVER auto-decides sufficiency, minimality,
or answerability — no substring/overlap heuristic appears here by design.
"""

import json
import unittest

from data_tools.qa_schema import validate_draft_record
from data_tools.verify import draft_content_hash, verify_draft


def nodes():
  # SYNTHETIC mini-corpus: two same-split train groups.
  return [
    {"node_id": "a:alpha", "kind": "article", "text": "Alpha",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gA-train"}},
    {"node_id": "a:beta", "kind": "article", "text": "Beta",
     "parent_id": "cl", "links": [], "meta": {"split_group": "gB-train"}},
    {"node_id": "p:a:1", "kind": "paragraph", "text": "First fact here.",
     "parent_id": "a:alpha", "links": []},
    {"node_id": "p:a:2", "kind": "paragraph", "text": "Second fact here.",
     "parent_id": "a:alpha", "links": []},
    {"node_id": "p:b:1", "kind": "paragraph", "text": "Beta ledger quarry zebra.",
     "parent_id": "a:beta", "links": []},
  ]


MAP = {"gA-train": "train", "gB-train": "train"}
A2G = {"alpha": "gA-train", "beta": "gB-train"}


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


def audit_record(**kw):
  rec = {"set_index": 0, "atom_node_id": "p:a:1",
         "leave_one_out_answerable": "no",
         "necessity_note": "names the ledger entity the answer depends on",
         "decision_token": "approve", "reviewer_id": "synthetic-reviewer",
         "reviewer_model": "synthetic-3", "corpus_revision": "rev-1",
         "reviewed_utc": "2026-01-01T00:00:00+00:00"}
  rec.update(kw)
  return rec


def factoid(semantic=False, evidence_groups=None, audits=None):
  meta = {"source_articles": ["Alpha"], "group": "gA-train"}
  if semantic:
    meta["semantic_status"] = "pending"
  if evidence_groups is not None:
    meta["evidence_groups"] = list(evidence_groups)
  prov = {"author": "synthetic-author", "author_model": "synthetic-1",
          "verifier": "synthetic-verifier", "verifier_model": "synthetic-2",
          "decision": "approve", "rationale": "synthetic approval rationale",
          "content_hash": ""}
  if audits is not None:
    prov["semantic_audit"] = audits
  d = {
    "question_id": "q", "text": "Which item is described first?",
    "split": "train", "question_type": "factoid",
    "meta": meta,
    "evidence": {"sufficient_sets": [
      [{"node_id": "p:a:1", "text": "First fact here."}]],
      "is_multi_hop": False, "reference_hop_chains": []},
    "hard_negatives": [{"node_id": "p:a:2",
                        "negative_type": "sibling_paragraph",
                        "reviewed": True}],
    "labels": {"answer_text": "the first item", "answerability": "answerable"},
    "provenance": prov,
  }
  d["provenance"]["content_hash"] = draft_content_hash(d)
  return d


def multihop(semantic=False, glosses=None):
  # Semantic drafts exercise the cross-group path (Alpha + Beta spans);
  # the pre-audit migration shape stays single-group (both spans Alpha),
  # which is the only multihop shape the old one-group rule ever allowed.
  if semantic:
    spans = [{"node_id": "p:a:1", "text": "First fact here."},
             {"node_id": "p:b:1", "text": "Beta ledger quarry zebra."}]
    chains = [["p:a:1", "p:b:1"]]
    sources = ["Alpha", "Beta"]
    groups: list[str] | None = ["gA-train", "gB-train"]
    neg = "p:a:2"
  else:
    spans = [{"node_id": "p:a:1", "text": "First fact here."},
             {"node_id": "p:a:2", "text": "Second fact here."}]
    chains = [["p:a:1", "p:a:2"]]
    sources = ["Alpha"]
    groups = None
    neg = "p:b:1"
  meta = {"source_articles": sources, "group": "gA-train"}
  if semantic:
    meta["semantic_status"] = "pending"
  if groups is not None:
    meta["evidence_groups"] = groups
  ev: dict = {"sufficient_sets": [spans], "is_multi_hop": True,
              "reference_hop_chains": chains}
  if glosses is not None:
    ev["hop_glosses"] = list(glosses)
  d = {
    "question_id": "q", "text": "Which item is described first?",
    "split": "train", "question_type": "multihop",
    "meta": meta, "evidence": ev,
    "hard_negatives": [{"node_id": neg,
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


def check_schema(d):
  return validate_draft_record(d)


def check_verify(d):
  return verify_draft(d, nodes(), **ctx())


class TestEvidenceGroups(unittest.TestCase):
  def test_optional_without_semantic_status(self):
    self.assertEqual(check_schema(factoid()), [])
    self.assertEqual(check_verify(factoid()), [])

  def test_required_with_semantic_status(self):
    d = factoid(semantic=True)
    self.assertTrue(any("requires meta.evidence_groups" in e
                        for e in check_schema(d)))

  def test_well_formed_passes(self):
    d = factoid(semantic=True, evidence_groups=["gA-train"])
    self.assertEqual(check_schema(d), [])
    self.assertEqual(check_verify(d), [])

  def test_must_include_primary_group(self):
    d = factoid(semantic=True, evidence_groups=["gB-train"])
    self.assertTrue(any("include meta.group" in e for e in check_schema(d)))

  def test_must_be_sorted(self):
    d = factoid(semantic=True, evidence_groups=["gB-train", "gA-train"])
    self.assertTrue(any("sorted" in e for e in check_schema(d)))

  def test_must_be_distinct(self):
    d = factoid(semantic=True, evidence_groups=["gA-train", "gA-train"])
    self.assertTrue(any("distinct" in e for e in check_schema(d)))

  def test_must_cover_evidence_articles(self):
    d = multihop(semantic=True, glosses=["first hop names the item"])
    d["meta"]["evidence_groups"] = ["gA-train"]  # drops the Beta span group
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertTrue(any("not in meta.evidence_groups" in e
                        for e in check_verify(d)))


class TestSemanticAuditRecords(unittest.TestCase):
  def test_absent_means_pending(self):
    # No semantic_audit block: the audit is still pending, and the draft
    # validates (migration grace for pre-audit drafts).
    d = factoid(semantic=True, evidence_groups=["gA-train"])
    self.assertEqual(check_schema(d), [])
    self.assertEqual(check_verify(d), [])

  def test_well_formed_record_accepted(self):
    d = factoid(semantic=True, evidence_groups=["gA-train"],
                audits=[audit_record()])
    self.assertEqual(check_schema(d), [])
    self.assertEqual(check_verify(d), [])

  def test_bad_vocabulary_rejected(self):
    d = factoid(audits=[audit_record(decision_token="maybe")])
    self.assertTrue(any("bad decision_token" in e for e in check_schema(d)))

  def test_self_review_rejected(self):
    d = factoid(audits=[audit_record(reviewer_id="synthetic-author")])
    self.assertTrue(any("differ from author" in e for e in check_schema(d)))

  def test_missing_corpus_revision_rejected(self):
    rec = audit_record()
    del rec["corpus_revision"]
    d = factoid(audits=[rec])
    self.assertTrue(any("missing corpus_revision" in e
                        for e in check_schema(d)))

  def test_answerability_vote_closed(self):
    d = factoid(audits=[audit_record(leave_one_out_answerable="sometimes")])
    self.assertTrue(any("yes/no" in e for e in check_schema(d)))

  def test_each_closed_decision_accepted_structurally(self):
    for token in ("approve", "repair-minimality", "repair-alternatives",
                  "relabel-multihop", "reject-replace"):
      d = factoid(audits=[audit_record(decision_token=token)])
      self.assertEqual(check_schema(d), [],
                       f"decision token {token} should validate structurally")

  def test_validation_is_pure_no_autopopulate(self):
    # Structural validation must never invent audit content: the record is
    # byte-identical before and after validation.
    d = factoid()
    before = json.dumps(d, sort_keys=True)
    check_schema(d)
    self.assertEqual(json.dumps(d, sort_keys=True), before)
    self.assertNotIn("semantic_audit", d["provenance"])


class TestHopGloss(unittest.TestCase):
  def test_migration_grace_without_semantic_status(self):
    # Pre-audit multihop shape (chains, no glosses) still validates.
    self.assertEqual(check_schema(multihop()), [])
    self.assertEqual(check_verify(multihop()), [])

  def test_missing_gloss_rejected_for_semantic_draft(self):
    d = multihop(semantic=True)
    self.assertTrue(any("hop_glosses" in e for e in check_schema(d)))

  def test_gloss_passes_structurally(self):
    d = multihop(semantic=True,
                 glosses=["hop one names the item, hop two gives its ledger"])
    self.assertEqual(check_schema(d), [])
    # Structural pass only: code never decides the hop is genuine.
    self.assertEqual(check_verify(d), [])

  def test_gloss_chain_misalignment_rejected(self):
    d = multihop(semantic=True, glosses=["only gloss"])
    d["evidence"]["reference_hop_chains"].append(["p:b:1"])
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertTrue(any("align" in e for e in check_schema(d)))

  def test_empty_gloss_rejected(self):
    d = multihop(semantic=True, glosses=["  "])
    self.assertTrue(any("hop_glosses" in e for e in check_schema(d)))


if __name__ == "__main__":
  unittest.main()
