"""The worker-visible public partition must not leak answers or answer locations.

corpus/questions.json is the ONLY question file a Round 1 architecture worker
may read. These tests pin the contract:

  * no evidence atoms, sufficient sets, hard negatives, answer text, readings;
  * no private_test entries, no retired `heldout` entries, no qa-private- ids;
  * no rejected/quarantined items;
  * no answer LOCATION: group / evidence_groups / source_articles would hand a
    retriever a 1-3 article candidate set inside a 297-article corpus;
  * no prose leak: a multi-word answer must not appear verbatim anywhere.

The last two are the ones that bite. A field-by-field allowlist is not enough
on its own: auditor rationales and metadata names both carried answer text and
answer location respectively.
"""

import glob
import json
import os
import unittest

from data_tools.build_public_partition import (
  ALLOWED_FIELDS,
  ALLOWED_PROVENANCE,
  FORBIDDEN_KEYS,
  _assert_clean,
  _project,
  main,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGING = os.path.join(REPO_ROOT, "staging")
REJECTED = os.path.join(STAGING, "rejected")
PUBLIC = os.path.join(REPO_ROOT, "corpus", "questions.json")

FORBIDDEN_META = ("group", "evidence_groups", "source_articles", "paired_regime")


def _public():
  with open(PUBLIC, "r", encoding="utf-8") as fh:
    return json.load(fh)


def _drafts(pattern="qa-*.json"):
  out = {}
  for path in sorted(glob.glob(os.path.join(STAGING, pattern))):
    with open(path, "r", encoding="utf-8") as fh:
      rec = json.load(fh)
    out[rec["question_id"]] = rec
  return out


class TestPublicPartitionContract(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    if not os.path.isfile(PUBLIC):
      raise unittest.SkipTest("corpus/questions.json absent")
    cls.public = _public()
    cls.drafts = _drafts()

  def test_partition_is_non_empty(self):
    self.assertGreater(len(self.public), 100)

  def test_no_forbidden_fields(self):
    for entry in self.public:
      blob = json.dumps(entry, sort_keys=True)
      for bad in FORBIDDEN_KEYS:
        self.assertNotIn(f'"{bad}"', blob,
                         f"{entry['question_id']}: carries {bad}")

  def test_no_answer_text_anywhere(self):
    for entry in self.public:
      draft = self.drafts.get(entry["question_id"])
      if draft is None:
        continue
      ans = str((draft.get("labels") or {}).get("answer_text") or "").strip()
      if len(ans) <= 8:
        continue
      self.assertNotIn(
        ans.lower(), json.dumps(entry, sort_keys=True).lower(),
        f"{entry['question_id']}: answer {ans[:30]!r} leaks into the partition")

  def test_no_answer_location(self):
    for entry in self.public:
      for bad in FORBIDDEN_META:
        self.assertNotIn(bad, entry.get("meta", {}),
                         f"{entry['question_id']}: meta.{bad} reveals the answer location")

  def test_no_evidence_atom_text(self):
    for entry in self.public:
      blob = json.dumps(entry, sort_keys=True)
      draft = self.drafts.get(entry["question_id"])
      if draft is None:
        continue
      for s in draft["evidence"]["sufficient_sets"]:
        for atom in s:
          snippet = atom["text"][:80]
          if len(snippet) > 40:
            self.assertNotIn(snippet, blob,
                             f"{entry['question_id']}: evidence atom text leaked")

  def test_splits_are_publishable_only(self):
    for entry in self.public:
      self.assertIn(entry["split"], ("train", "dev", "shadow_dev"),
                    entry["question_id"])
      self.assertNotEqual(entry["split"], "private_test")
      self.assertNotEqual(entry["split"], "heldout")

  def test_no_private_ids(self):
    for entry in self.public:
      self.assertNotIn("qa-private-", json.dumps(entry))

  def test_rejected_items_excluded(self):
    rejected = set()
    for path in glob.glob(os.path.join(REJECTED, "qa-*.json")):
      with open(path, "r", encoding="utf-8") as fh:
        rejected.add(json.load(fh)["question_id"])
    self.assertTrue(rejected, "no rejected items recorded")
    published = {e["question_id"] for e in self.public}
    self.assertEqual(published & rejected, set(),
                     "rejected items must not be published")

  def test_every_published_item_is_approved(self):
    for entry in self.public:
      draft = self.drafts.get(entry["question_id"])
      if draft is None:
        continue
      self.assertEqual(draft["provenance"]["decision"], "approve",
                       f"{entry['question_id']} published without approval")

  def test_no_duplicate_ids(self):
    ids = [e["question_id"] for e in self.public]
    self.assertEqual(len(ids), len(set(ids)))

  def test_allowlists_are_narrow(self):
    self.assertNotIn("rationale", ALLOWED_PROVENANCE,
                     "rationales name the answer in prose")
    for f in FORBIDDEN_META:
      self.assertNotIn(f, ALLOWED_FIELDS)


class TestBuilderFailsClosed(unittest.TestCase):
  def test_rationale_answer_leak_is_prevented_by_projection(self):
    """A rationale naming the answer must not survive projection.

    The leak is stopped at the projection layer (rationale is not an allowed
    provenance field), so the emitted entry is already clean. The checker is
    the backstop for a leak that arrives some other way.
    """
    draft = {
      "question_id": "qa-x-01", "text": "Q?", "split": "dev",
      "question_type": "factoid",
      "labels": {"answer_text": "the University of Cambridge"},
      "meta": {"group": "g", "source_articles": ["A"]},
      "provenance": {"author": "a", "verifier": "v", "decision": "approve",
                     "rationale": "the atom states the University of Cambridge"},
    }
    entry = _project(draft)
    self.assertNotIn("rationale", entry.get("provenance", {}))
    self.assertNotIn("university of cambridge",
                     json.dumps(entry, sort_keys=True).lower())
    # And the backstop passes the already-clean entry.
    _assert_clean(entry, "qa-x-01", draft)

  def test_prose_leak_from_any_field_is_caught(self):
    """If a leak DOES reach the emitted entry, the checker rejects it."""
    draft = {
      "question_id": "qa-x-01b", "text": "Q?", "split": "dev",
      "question_type": "factoid",
      "labels": {"answer_text": "the University of Cambridge"},
      "meta": {},
      "provenance": {"author": "a", "verifier": "v", "decision": "approve"},
    }
    entry = _project(draft)
    # Simulate a leak introduced after projection.
    entry["meta"]["exposure_note"] = "atom states the University of Cambridge"
    with self.assertRaises(SystemExit) as cm:
      _assert_clean(entry, "qa-x-01b", draft)
    self.assertIn("prose leak", str(cm.exception))

  def test_private_split_is_caught(self):
    draft = {"question_id": "qa-x-02", "split": "private_test", "text": "Q?"}
    with self.assertRaises(SystemExit):
      _assert_clean(_project(draft), "qa-x-02", draft)

  def test_retired_split_is_caught(self):
    draft = {"question_id": "qa-x-03", "split": "heldout", "text": "Q?"}
    with self.assertRaises(SystemExit):
      _assert_clean(_project(draft), "qa-x-03", draft)

  def test_short_answer_coinciding_with_metadata_is_allowed(self):
    draft = {
      "question_id": "qa-x-04", "text": "Which planet?", "split": "dev",
      "question_type": "factoid",
      "labels": {"answer_text": "Mercury"},
      "meta": {"group": "mercury", "source_articles": ["Mercury (planet)"]},
      "provenance": {"author": "a", "verifier": "v", "decision": "approve"},
    }
    _assert_clean(_project(draft), "qa-x-04", draft)  # must not raise

  def test_builder_output_matches_committed_file(self):
    """Regenerating must reproduce the committed partition byte for byte."""
    if not os.path.isfile(PUBLIC):
      self.skipTest("corpus/questions.json absent")
    import hashlib
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
      out = os.path.join(tmp, "questions.json")
      rc = main(["--staging", STAGING, "--out", out], quiet=True)
      self.assertEqual(rc, 0)
      with open(out, "rb") as fh:
        rebuilt = fh.read()
    with open(PUBLIC, "rb") as fh:
      committed = fh.read()
    self.assertEqual(
      hashlib.sha256(rebuilt).hexdigest(),
      hashlib.sha256(committed).hexdigest(),
      "corpus/questions.json is stale; regenerate it with "
      "python3 -m data_tools.build_public_partition",
    )


if __name__ == "__main__":
  unittest.main()
