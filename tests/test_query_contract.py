"""Tests for the model-facing query contract (substrate.query, blocker 5).

corpus/questions.json is a STORED artifact; the model-facing surface is
exactly {question_id, text}. These tests pin the boundary:

  * a fake architecture that records every key/attribute it can see on a
    QueryInput never sees a forbidden field;
  * a partition entry carrying question_type="unanswerable" yields a
    QueryInput that exposes ONLY question_id and text;
  * the guard raises if forbidden metadata is attached (dict payloads,
    nested payloads, attributes smuggled onto the frozen dataclass);
  * to_model_query never copies split / question_type / meta / provenance;
  * the worker Regime-B exclusion list equals the public 21 and is derived
    from the public artifact only -- never from a private artifact;
  * the committed corpus entries all convert cleanly and carry no answer
    location in meta (verified structural fact: group / evidence_groups /
    source_articles are dropped by the builder in every entry).
"""

import inspect
import json
import os
import re
import unittest
from unittest import mock

from substrate.query import (
  FORBIDDEN_MODEL_FIELDS,
  MODEL_FACING_FIELDS,
  REGIME_B_EXCLUSION_ARTIFACT,
  ForbiddenMetadataError,
  QueryInput,
  assert_no_label_metadata,
  model_visible_payload,
  to_model_query,
  worker_regime_b_exclusions,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _partition_entry(
  qid,
  text,
  split="shadow_dev",
  qtype="unanswerable",
  meta=None,
  provenance=None,
):
  """A realistic stored partition entry, including the forbidden fields."""
  entry = {
    "question_id": qid,
    "text": text,
    "split": split,
    "question_type": qtype,
    "meta": {
      "group": "corona",
      "source_articles": ["Coronavirus", "Corona (beer)"],
    }
    if meta is None
    else meta,
    "provenance": {
      "author": "round0-qa-dev-author",
      "verifier": "independent-ultra-verifier",
      "decision": "approve",
    }
    if provenance is None
    else provenance,
  }
  return entry


class FakeArchitecture:
  """Stand-in architecture: a callable that receives a QueryInput and
  records exactly which keys/attributes it can see on it (its public input
  surface), the way a real architecture's code would.
  """

  def __init__(self):
    self.seen_surfaces = []

  def __call__(self, query):
    visible = set()
    for name in dir(query):
      if not name.startswith("__") and hasattr(query, name):
        visible.add(name)
    visible.update(vars(query).keys())
    self.seen_surfaces.append(visible)
    return {"generation": "fake", "citations": []}


class TestFakeArchitectureSurface(unittest.TestCase):
  def test_fake_architecture_sees_no_forbidden_field(self):
    entry = _partition_entry(
      "qa-fake-unanswerable",
      "Which of these cannot be determined from the corpus?",
      qtype="unanswerable",
    )
    arch = FakeArchitecture()
    result = arch(to_model_query(entry))
    self.assertIn("generation", result)
    self.assertEqual(len(arch.seen_surfaces), 1)
    surface = arch.seen_surfaces[0]
    self.assertTrue(
      FORBIDDEN_MODEL_FIELDS.isdisjoint(surface),
      f"forbidden field visible to the model: "
      f"{sorted(FORBIDDEN_MODEL_FIELDS & surface)}",
    )

  def test_fake_architecture_surface_contains_the_allowlist(self):
    entry = _partition_entry("qa-fake-2", "What country leads 2024 apple production?")
    arch = FakeArchitecture()
    arch(to_model_query(entry))
    self.assertTrue(MODEL_FACING_FIELDS.issubset(arch.seen_surfaces[0]))

  def test_fake_architecture_on_real_unanswerable_corpus_entry(self):
    with open(os.path.join(REPO_ROOT, "corpus", "questions.json"), encoding="utf-8") as fh:
      entries = json.load(fh)
    unanswerable = [e for e in entries if e["question_type"] == "unanswerable"]
    self.assertTrue(unanswerable, "corpus must contain unanswerable entries")
    for entry in unanswerable:
      with self.subTest(qid=entry["question_id"]):
        arch = FakeArchitecture()
        arch(to_model_query(entry))
        surface = arch.seen_surfaces[0]
        self.assertTrue(FORBIDDEN_MODEL_FIELDS.isdisjoint(surface))
        self.assertNotIn("unanswerable", json.dumps([sorted(s) for s in arch.seen_surfaces]))
        # stored-state inspection: only the two allowlisted fields exist
        self.assertEqual(
          set(vars(to_model_query(entry))),
          {"question_id", "text"},
        )


class TestUnanswerableEntrySurface(unittest.TestCase):
  def test_unanswerable_entry_exposes_only_question_id_and_text(self):
    entry = _partition_entry(
      "qa-u9",
      "Which of these cannot be determined from the corpus?",
      qtype="unanswerable",
      meta={
        "group": "corona",
        "source_articles": ["Coronavirus", "Corona (beer)"],
        "original_id": "qa-heldout-01",
        "exposure_note": "exposed in git history; reclassified; never sealed",
      },
    )
    q = to_model_query(entry)
    # stored state: exactly the two fields, nothing smuggled
    self.assertEqual(
      vars(q),
      {"question_id": "qa-u9", "text": entry["text"]},
    )
    # helper surface: exactly MODEL_FACING_FIELDS
    payload = model_visible_payload(entry)
    self.assertEqual(sorted(payload.keys()), ["question_id", "text"])
    blob = json.dumps(payload)
    self.assertNotIn("unanswerable", blob)
    self.assertNotIn("corona", blob.lower())
    self.assertNotIn("qa-heldout-01", blob)
    self.assertNotIn("exposed in git history", blob)
    assert_no_label_metadata(payload)

  def test_to_model_query_never_copies_split_type_meta_provenance(self):
    entry = {
      "question_id": "qa-sentinel",
      "text": "SENTINEL-TEXT-42",
      "split": "SENTINEL-SPLIT-42",
      "question_type": "SENTINEL-TYPE-42",
      "meta": {
        "group": "SENTINEL-GROUP-42",
        "source_articles": ["SENTINEL-ARTICLE-42"],
      },
      "provenance": {"author": "SENTINEL-AUTHOR-42", "decision": "approve"},
    }
    q = to_model_query(entry)
    payload = q.to_dict()
    blob = json.dumps(payload)
    for sentinel in (
      "SENTINEL-SPLIT-42",
      "SENTINEL-TYPE-42",
      "SENTINEL-GROUP-42",
      "SENTINEL-ARTICLE-42",
      "SENTINEL-AUTHOR-42",
      "SENTINEL-TEXT-42",
    ):
      if sentinel == "SENTINEL-TEXT-42":
        self.assertIn(sentinel, blob)  # the question text is allowed
      else:
        self.assertNotIn(sentinel, blob)
    self.assertEqual(
      vars(q), {"question_id": "qa-sentinel", "text": "SENTINEL-TEXT-42"}
    )

  def test_to_model_query_is_idempotent(self):
    entry = _partition_entry("qa-idem", "A question.")
    q1 = to_model_query(entry)
    q2 = to_model_query(q1)
    self.assertEqual(q1, q2)

  def test_to_model_query_rejects_entries_without_id_or_text(self):
    with self.assertRaises(ValueError):
      to_model_query({"question_id": "", "text": "t"})
    with self.assertRaises(ValueError):
      to_model_query({"question_id": "q", "text": ""})
    with self.assertRaises(ValueError):
      to_model_query({"text": "t"})


class TestGuardRaisesOnForbiddenMetadata(unittest.TestCase):
  def test_guard_passes_clean_payloads(self):
    self.assertIsNone(assert_no_label_metadata({"question_id": "q", "text": "t"}))
    self.assertIsNone(assert_no_label_metadata(to_model_query(
      {"question_id": "q", "text": "t"}
    )))

  def test_guard_raises_on_dict_payload_with_forbidden_field(self):
    with self.assertRaises(ForbiddenMetadataError):
      assert_no_label_metadata(
        {"question_id": "q", "text": "t", "labels": {"answer": "Paris"}}
      )

  def test_guard_raises_on_smuggled_attribute(self):
    q = to_model_query({"question_id": "q", "text": "t"})
    object.__setattr__(q, "question_type", "unanswerable")
    with self.assertRaises(ForbiddenMetadataError):
      assert_no_label_metadata(q)

  def test_guard_raises_on_nested_metadata(self):
    with self.assertRaises(ForbiddenMetadataError):
      assert_no_label_metadata({"model_input": {"context": {"split": "shadow_dev"}}})
    with self.assertRaises(ForbiddenMetadataError):
      assert_no_label_metadata({"packs": [{"meta": {"group": "g"}}]})

  def test_guard_raises_on_each_forbidden_field(self):
    for field in sorted(FORBIDDEN_MODEL_FIELDS):
      with self.subTest(field=field):
        with self.assertRaises(ForbiddenMetadataError):
          assert_no_label_metadata({field: "leak"})

  def test_guard_catches_a_whole_stored_entry(self):
    entry = _partition_entry("qa-whole", "A stored entry.")
    with self.assertRaises(ForbiddenMetadataError):
      assert_no_label_metadata(entry)


class TestWorkerRegimeBExclusions(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    with open(
      os.path.join(REPO_ROOT, "corpus", "regime_b_excluded_articles.json"),
      encoding="utf-8",
    ) as fh:
      cls.public_doc = json.load(fh)

  def test_worker_list_equals_public_21(self):
    ex = worker_regime_b_exclusions()
    self.assertEqual(len(self.public_doc["articles"]), 21)
    self.assertEqual(list(ex.articles), self.public_doc["articles"])
    self.assertEqual(ex.split_map_sha256, self.public_doc["split_map_sha256"])
    self.assertEqual(ex.source_artifact, "corpus/regime_b_excluded_articles.json")
    self.assertTrue(all(a.strip() for a in ex.articles))

  def test_worker_list_derived_from_public_artifact_only(self):
    opened = []
    real_open = open

    def spy(path, *args, **kwargs):
      opened.append(os.fspath(path))
      return real_open(path, *args, **kwargs)

    with mock.patch("builtins.open", spy):
      ex = worker_regime_b_exclusions()
    self.assertEqual(len(ex.articles), 21)
    private_touches = [
      p for p in opened
      if re.search(r"private|sealed|labels|regime_b_paired", str(p), re.IGNORECASE)
    ]
    self.assertEqual(private_touches, [])
    expected = [p for p in opened if "regime_b_excluded_articles.json" in str(p)]
    self.assertEqual(len(expected), 1)

  def test_worker_function_source_reads_no_private_metadata(self):
    src = inspect.getsource(worker_regime_b_exclusions)
    for needle in (
      "private_test_manifest",
      "regime_b_paired",
      "LMR_PRIVATE_EVAL_DIR",
      "check_training_overlap",
    ):
      self.assertNotIn(needle, src)
    self.assertIn(REGIME_B_EXCLUSION_ARTIFACT, src)

  def test_in_repo_private_manifest_has_no_article_data_to_derive_from(self):
    with open(
      os.path.join(REPO_ROOT, "corpus", "private_test_manifest.json"),
      encoding="utf-8",
    ) as fh:
      manifest = json.load(fh)
    paired = manifest["paired_regime_b"]
    # Opaque manifest: the private paired-regime metadata present in the
    # repo is counts + group names only. No article names, no item ids --
    # nothing from which a worker exclusion list could be derived.
    self.assertNotIn("articles", paired)
    self.assertNotIn("excluded_articles", paired)
    self.assertNotIn("question_ids", paired)
    self.assertEqual(
      set(paired["groups"]),
      {"cambridge", "corona", "jaguar", "lincoln", "washington"},
    )
    # The private counts stay under the public superset.
    self.assertEqual(manifest["counts"]["paired_regime_b_items"], 15)
    self.assertLessEqual(
      manifest["counts"]["paired_regime_b_excluded_articles"],
      len(self.public_doc["articles"]),
    )

  def test_refuses_private_labeled_source(self):
    with self.assertRaises(ValueError):
      worker_regime_b_exclusions(
        repo_root=os.path.join(REPO_ROOT, "corpus", "private_eval")
      )


class TestCommittedCorpusContract(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    with open(os.path.join(REPO_ROOT, "corpus", "questions.json"), encoding="utf-8") as fh:
      cls.entries = json.load(fh)

  def test_all_entries_convert_and_expose_only_allowed_fields(self):
    self.assertEqual(len(self.entries), 206)
    for entry in self.entries:
      with self.subTest(qid=entry["question_id"]):
        q = to_model_query(entry)
        payload = model_visible_payload(entry)
        self.assertEqual(sorted(payload.keys()), ["question_id", "text"])
        assert_no_label_metadata(payload)
        blob = json.dumps(payload)
        for field in FORBIDDEN_MODEL_FIELDS:
          self.assertNotIn(f'"{field}"', blob)

  def test_no_entry_meta_carries_answer_location(self):
    # Verified against the committed artifact: the builder drops the
    # answer's LOCATION (group / evidence_groups / source_articles) from
    # meta in EVERY entry. 119 of 206 entries have meta == {}; the 87
    # shadow_dev reclassifications carry only original_id + exposure_note.
    seen_nonempty = 0
    allowed_meta_keys = set()
    for entry in self.entries:
      meta = entry.get("meta")
      self.assertIsInstance(meta, dict)
      if meta:
        seen_nonempty += 1
        allowed_meta_keys.update(meta.keys())
      for key in ("group", "evidence_groups", "source_articles", "paired_regime"):
        self.assertNotIn(key, meta)
    self.assertEqual(allowed_meta_keys, {"original_id", "exposure_note"})
    self.assertEqual(seen_nonempty, 87)


if __name__ == "__main__":
  unittest.main()
