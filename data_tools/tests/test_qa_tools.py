"""data_tools tests. ALL fixtures SYNTHETIC — not actual QA, not corpus text.

Every verify_draft call below passes EXPLICIT verification context
(article_index, map_groups, article_to_group): there is no context-free
verification path, and omission/malformed context is tested to fail.

Covers: schema validation, tautology guard, type/answerability consistency,
ambiguous readings, bool-offset rejection, code-point offsets, source
coverage, ancestor/descendant negative overlap, candidate-vs-reviewed
negatives, content-bound approvals, seal gating, retriever-input
projection, pinned public import.
"""

import unittest

from data_tools.hard_negatives import mine_hard_negatives
from data_tools.import_public import (check_import_pin, convert_public_entry,
                                      convert_public_file)
from data_tools.qa_schema import to_retriever_input, validate_draft_record
from data_tools.verify import (draft_content_hash, seal_records, verify_draft)

FULL_SHA = "a" * 40
FILE_SHA = "b" * 64


def nodes():
  # SYNTHETIC mini-corpus: g-train has alpha/beta/delta articles; g-dev gamma.
  return [
    {"node_id": "a:alpha", "kind": "article", "text": "Alpha",
     "parent_id": "cl", "links": ["a:beta"], "meta": {"split_group": "g-train"}},
    {"node_id": "a:beta", "kind": "article", "text": "Beta",
     "parent_id": "cl", "links": [], "meta": {"split_group": "g-train"}},
    {"node_id": "a:gamma", "kind": "article", "text": "Gamma",
     "parent_id": "cl", "links": [], "meta": {"split_group": "g-dev"}},
    {"node_id": "a:delta", "kind": "article", "text": "Delta",
     "parent_id": "cl", "links": [], "meta": {"split_group": "g-train"}},
    {"node_id": "s:a:1", "kind": "section", "text": "S",
     "parent_id": "a:alpha", "links": []},
    {"node_id": "p:a:1", "kind": "paragraph", "text": "First fact here.",
     "parent_id": "s:a:1", "links": []},
    {"node_id": "p:a:2", "kind": "paragraph", "text": "Second fact here.",
     "parent_id": "s:a:1", "links": []},
    {"node_id": "t:a:1", "kind": "sentence", "text": "First fact here.",
     "parent_id": "p:a:1", "links": []},
    {"node_id": "t:a:2", "kind": "sentence", "text": "Neighbor words here.",
     "parent_id": "p:a:1", "links": []},
    {"node_id": "t:u:1", "kind": "sentence", "text": "Café au lait.",
     "parent_id": "p:a:2", "links": []},
    {"node_id": "p:b:1", "kind": "paragraph", "text": "Beta ledger quarry zebra.",
     "parent_id": "a:beta", "links": []},
    {"node_id": "p:b:2", "kind": "paragraph", "text": "Beta harbor lantern atlas.",
     "parent_id": "a:beta", "links": []},
    {"node_id": "p:d:1", "kind": "paragraph", "text": "Delta harbor lantern atlas.",
     "parent_id": "a:delta", "links": []},
    {"node_id": "p:g:1", "kind": "paragraph", "text": "Gamma words here.",
     "parent_id": "a:gamma", "links": []},
  ]


MAP = {"g-train": "train", "g-dev": "dev"}
A2G = {"alpha": "g-train", "beta": "g-train", "delta": "g-train", "gamma": "g-dev"}


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


def good_draft():
  d = {
    "question_id": "q1", "text": "Which item is described first?",
    "split": "train", "question_type": "factoid",
    "meta": {"source_articles": ["Alpha"], "group": "g-train"},
    "evidence": {"sufficient_sets": [
      [{"node_id": "t:a:1", "text": "First fact here."}]],
      "is_multi_hop": False, "reference_hop_chains": []},
    "hard_negatives": [{"node_id": "p:a:2",
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


class TestSchema(unittest.TestCase):
  def test_good_passes(self):
    self.assertEqual(validate_draft_record(good_draft()), [])
    self.assertEqual(verify(good_draft()), [])

  def test_missing_provenance_rejected(self):
    d = good_draft()
    del d["provenance"]
    self.assertTrue(validate_draft_record(d))

  def test_tautology_rejected(self):
    d = good_draft()
    d["text"] = "Is the answer the first item here?"
    self.assertTrue(any("tautological" in e for e in validate_draft_record(d)))

  def test_unanswerable_shape(self):
    d = good_draft()
    d["question_type"] = "unanswerable"
    d["evidence"] = {"sufficient_sets": [], "is_multi_hop": False,
                     "absent_reason": "no corpus passage states this"}
    d["labels"] = {"answer_text": "", "answerability": "unanswerable"}
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertEqual(validate_draft_record(d), [])
    self.assertEqual(verify(d), [])

  def test_unanswerable_mismatch_rejected(self):
    d = good_draft()
    d["question_type"] = "unanswerable"  # labels still answerable
    self.assertTrue(any("mismatch" in e for e in validate_draft_record(d)))
    d = good_draft()
    d["labels"] = {"answer_text": "", "answerability": "unanswerable"}
    self.assertTrue(any("mismatch" in e for e in validate_draft_record(d)))

  def test_ambiguous_mismatch_rejected(self):
    d = good_draft()
    d["question_type"] = "ambiguous"
    self.assertTrue(any("mismatch" in e for e in validate_draft_record(d)))

  def test_ambiguous_readings_validated(self):
    def amb():
      d = good_draft()
      d["question_type"] = "ambiguous"
      d["evidence"]["sufficient_sets"] = [
        [{"node_id": "t:a:1", "text": "First fact here."}],
        [{"node_id": "p:a:2", "text": "Second fact here."}]]
      # t:a:2 is adjacent to t:a:1 but in neither sufficient set.
      d["hard_negatives"] = [{"node_id": "t:a:2",
                              "negative_type": "neighbor_sentence",
                              "reviewed": True}]
      d["labels"] = {"answer_text": "unclear", "answerability": "ambiguous",
                     "readings": [
                       {"reading_text": "first reading",
                        "answer": "first answer", "sufficient_set": 0},
                       {"reading_text": "second reading",
                        "answer": "second answer", "sufficient_set": 1}]}
      d["provenance"]["content_hash"] = draft_content_hash(d)
      return d
    self.assertEqual(validate_draft_record(amb()), [])
    self.assertEqual(verify(amb()), [])
    bad = amb()
    bad["labels"]["readings"] = [{"reading_text": "only one",
                                  "answer": "a", "sufficient_set": 0}]
    self.assertTrue(validate_draft_record(bad))
    bad = amb()
    del bad["labels"]["readings"][0]["answer"]
    self.assertTrue(any("answer" in e for e in validate_draft_record(bad)))
    bad = amb()
    bad["labels"]["readings"][1]["sufficient_set"] = 0  # reused set
    self.assertTrue(any("reuses" in e for e in validate_draft_record(bad)))
    bad = amb()
    bad["labels"]["readings"][1]["sufficient_set"] = 7  # out of range
    self.assertTrue(any("range" in e for e in validate_draft_record(bad)))
    bad = amb()
    bad["labels"]["readings"][1]["sufficient_set"] = True  # bool, not int
    self.assertTrue(validate_draft_record(bad))

  def test_bool_offsets_rejected(self):
    d = good_draft()
    d["evidence"]["sufficient_sets"][0][0] = {
      "node_id": "t:a:1", "text": "First fact here.",
      "char_start": True, "char_end": 5}
    self.assertTrue(any("must be int" in e for e in validate_draft_record(d)))

  def test_bm25_name_rejected(self):
    d = good_draft()
    d["hard_negatives"] = [{"node_id": "p:a:2", "negative_type": "bm25_nearmiss",
                            "reviewed": True}]
    self.assertTrue(any("bad negative_type" in e for e in validate_draft_record(d)))
    d["hard_negatives"][0]["negative_type"] = "token_overlap_nearmiss"
    self.assertEqual(validate_draft_record(d), [])

  def test_reviewed_flag_required(self):
    d = good_draft()
    del d["hard_negatives"][0]["reviewed"]
    self.assertTrue(any("reviewed" in e for e in validate_draft_record(d)))

  def test_multihop_needs_chain(self):
    d = good_draft()
    d["question_type"] = "multihop"
    d["evidence"]["is_multi_hop"] = True
    self.assertTrue(any("hop_chain" in e for e in validate_draft_record(d)))
    d["evidence"]["reference_hop_chains"] = [["t:a:1", "p:b:1"]]
    self.assertEqual(validate_draft_record(d), [])


class TestVerifyContext(unittest.TestCase):
  def test_missing_context_raises(self):
    with self.assertRaises(TypeError):
      verify_draft(good_draft(), nodes())

  def test_empty_map_fails_closed(self):
    errs = verify_draft(good_draft(), nodes(), **ctx(map_groups={}))
    self.assertTrue(any("map_groups" in e for e in errs))

  def test_none_index_fails_closed(self):
    errs = verify_draft(good_draft(), nodes(), **ctx(article_index=None))
    self.assertTrue(any("article_index" in e for e in errs))

  def test_empty_group_table_fails_closed(self):
    errs = verify_draft(good_draft(), nodes(), **ctx(article_to_group={}))
    self.assertTrue(any("article_to_group" in e for e in errs))


class TestVerifyEvidence(unittest.TestCase):
  def test_exact_span_mismatch_rejected(self):
    d = good_draft()
    d["evidence"]["sufficient_sets"][0][0]["text"] = "Tampered words here."
    self.assertTrue(any("text" in e for e in verify(d)))

  def test_codepoint_offsets(self):
    # "Café au lait.": é is 1 code point but 2 UTF-8 bytes. Offsets are
    # code points: text[0:4] == "Café" (byte slicing would split é).
    d = good_draft()
    d["evidence"]["sufficient_sets"] = [
      [{"node_id": "t:u:1", "text": "Café", "char_start": 0, "char_end": 4}]]
    # t:a:2 shares no ancestor/descendant relation with t:u:1.
    d["hard_negatives"] = [{"node_id": "t:a:2",
                            "negative_type": "neighbor_sentence",
                            "reviewed": True}]
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertEqual(verify(d), [])
    bad = good_draft()
    bad["evidence"]["sufficient_sets"] = [
      [{"node_id": "t:u:1", "text": "Caf", "char_start": 0, "char_end": 4}]]
    bad["provenance"]["content_hash"] = draft_content_hash(bad)
    self.assertTrue(any("mismatch" in e for e in verify(bad)))

  def test_cross_group_span_rejected(self):
    d = good_draft()
    d["evidence"]["sufficient_sets"] = [
      [{"node_id": "t:a:1", "text": "First fact here."}],
      [{"node_id": "p:g:1", "text": "Gamma words here."}]]
    d["meta"] = {"source_articles": ["Alpha", "Gamma"], "group": "g-train"}
    self.assertTrue(verify(d))

  def test_undeclared_same_group_article_rejected(self):
    # Beta is in g-train, but sources declare only Alpha: same group alone
    # is insufficient — the actual evidence article must be declared.
    d = good_draft()
    d["evidence"]["sufficient_sets"] = [
      [{"node_id": "p:b:1", "text": "Beta ledger quarry zebra."}]]
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertTrue(any("missing" in e and "source_articles" in e
                        for e in verify(d)))

  def test_ancestor_negative_rejected(self):
    # p:a:1 is the PARENT paragraph of evidence sentence t:a:1.
    d = good_draft()
    d["hard_negatives"] = [{"node_id": "p:a:1",
                            "negative_type": "sibling_paragraph",
                            "reviewed": True}]
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertTrue(any("overlaps evidence" in e for e in verify(d)))

  def test_descendant_negative_rejected(self):
    # Evidence is paragraph p:a:1; t:a:1 is a sentence INSIDE it.
    d = good_draft()
    d["evidence"]["sufficient_sets"] = [
      [{"node_id": "p:a:1", "text": "First fact here."}]]
    d["hard_negatives"] = [{"node_id": "t:a:1",
                            "negative_type": "neighbor_sentence",
                            "reviewed": True}]
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertTrue(any("overlaps evidence" in e for e in verify(d)))

  def test_unreviewed_negative_rejected(self):
    d = good_draft()
    d["hard_negatives"][0]["reviewed"] = False
    d["provenance"]["content_hash"] = draft_content_hash(d)
    self.assertTrue(any("not independently reviewed" in e for e in verify(d)))


class TestApproval(unittest.TestCase):
  def test_pending_rejected(self):
    d = good_draft()
    d["provenance"]["decision"] = "pending"
    self.assertTrue(any("decision" in e for e in verify(d)))

  def test_self_review_rejected(self):
    d = good_draft()
    d["provenance"]["verifier"] = d["provenance"]["author"]
    self.assertTrue(any("differ from author" in e for e in verify(d)))

  def test_stale_hash_rejected(self):
    d = good_draft()
    d["text"] = "Edited after approval?"
    # content_hash left at the pre-edit value -> stale.
    self.assertTrue(any("stale" in e for e in verify(d)))

  def test_empty_rationale_rejected(self):
    d = good_draft()
    d["provenance"]["rationale"] = ""
    self.assertTrue(any("rationale" in e for e in verify(d)))


class TestSeal(unittest.TestCase):
  def seal_ctx(self, records, **kw):
    params = {"nodes": nodes(), **ctx()}
    params.update(kw)
    return seal_records(records, **params)

  def test_good_seals(self):
    out = self.seal_ctx([good_draft()])
    self.assertEqual(out["manifest"]["splits"]["train"], 1)
    self.assertEqual(out["heldout_sealed"], {})
    self.assertIn("q1", out["manifest"]["content_hashes"])

  def test_duplicates_fail(self):
    with self.assertRaises(ValueError):
      self.seal_ctx([good_draft(), good_draft()])

  def test_unverified_fails(self):
    d = good_draft()
    d["provenance"]["decision"] = "pending"
    with self.assertRaises(ValueError):
      self.seal_ctx([d])

  def test_empty_list_fails(self):
    with self.assertRaises(ValueError):
      self.seal_ctx([])

  def test_heldout_gated(self):
    import os
    d = good_draft()
    d["split"] = "heldout"
    d["meta"] = {"source_articles": ["Gamma"], "group": "g-dev"}
    d["evidence"]["sufficient_sets"] = [
      [{"node_id": "p:g:1", "text": "Gamma words here."}]]
    d["hard_negatives"] = [{"node_id": "t:a:1",
                            "negative_type": "neighbor_sentence",
                            "reviewed": True}]
    d["provenance"]["content_hash"] = draft_content_hash(d)
    with self.assertRaises(PermissionError):
      self.seal_ctx([d])
    os.environ.pop("HELDOUT_CUSTODIAN_MODE", None)
    with self.assertRaises(PermissionError):
      self.seal_ctx([d], allow_heldout=True)


class TestNegatives(unittest.TestCase):
  def test_strata_present(self):
    out = mine_hard_negatives(nodes(), {"t:a:1"}, {"a:alpha", "a:beta", "a:delta"})
    types = {o["negative_type"] for o in out}
    self.assertIn("sibling_paragraph", types)
    self.assertIn("neighbor_sentence", types)
    self.assertNotIn("bm25_nearmiss", types)
    self.assertTrue({"entity_confusion", "same_group_distractor"} & types)
    self.assertNotIn("t:a:1", [o["node_id"] for o in out])

  def test_candidates_unreviewed(self):
    out = mine_hard_negatives(nodes(), {"t:a:1"}, {"a:alpha"})
    self.assertTrue(out)
    self.assertTrue(all(o["reviewed"] is False for o in out))


class TestRetrieverInput(unittest.TestCase):
  def test_only_qid_and_text(self):
    from data_tools.qa_schema import draft_to_question_entry
    entry = draft_to_question_entry(good_draft())
    runtime = to_retriever_input(entry)
    self.assertEqual(set(runtime), {"question_id", "text"})
    import json
    blob = json.dumps(runtime)
    for hint in ("Alpha", "g-train", "factoid", "answerable"):
      self.assertNotIn(hint, blob)

  def test_unexpected_field_raises(self):
    with self.assertRaises(ValueError):
      to_retriever_input({"question_id": "q", "text": "t?",
                          "answer": "leaked"})


class TestPublicImport(unittest.TestCase):
  def kw(self):
    return {"source_benchmark": "androidlm", "source_revision": FULL_SHA,
            "source_file_sha256": FILE_SHA}

  def test_dev_only(self):
    q = convert_public_entry(
      {"original_question_id": "o1", "text": "synthetic?"}, **self.kw())
    self.assertEqual((q["split"], q["meta"]["category"]), ("dev", "public_reference"))
    self.assertEqual(q["meta"]["source_file_sha256"], FILE_SHA)

  def test_short_revision_rejected(self):
    kw = self.kw()
    kw["source_revision"] = "ed3d51a"
    with self.assertRaises(ValueError):
      convert_public_entry(
        {"original_question_id": "o1", "text": "t?"}, **kw)

  def test_bad_file_sha_rejected(self):
    kw = self.kw()
    kw["source_file_sha256"] = "zz"
    with self.assertRaises(ValueError):
      convert_public_entry(
        {"original_question_id": "o1", "text": "t?"}, **kw)

  def test_pin_verified(self):
    import hashlib
    raw = b"synthetic-import-bytes"
    pin = hashlib.sha256(raw).hexdigest()
    check_import_pin(raw, pin)  # matching bytes pass
    with self.assertRaises(ValueError):
      check_import_pin(b"other-bytes", pin)  # mismatched bytes fail
    entries = [{"original_question_id": "o1", "text": "t?"}]
    with self.assertRaises(ValueError):
      convert_public_file(entries, source_bytes=b"actual-bytes", **self.kw())

  def test_train_refused(self):
    with self.assertRaises(ValueError):
      convert_public_entry(
        {"original_question_id": "o1", "text": "t?", "split": "train"},
        **self.kw())

  def test_answers_refused(self):
    with self.assertRaises(ValueError):
      convert_public_entry(
        {"original_question_id": "o1", "text": "t?", "answer": "secret"},
        **self.kw())


if __name__ == "__main__":
  unittest.main()
