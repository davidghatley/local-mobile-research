"""Offline converter regression tests (corpus worker scope: corpus/tests/).

Stdlib unittest only. No network: the offline path is proven by
test_offline_path_never_touches_network (monkeypatched api_get + blocked
sockets) and test_source_has_no_network_references (static source scan).
Run: python3 -m unittest discover -s corpus/tests -t .
"""

import collections
import copy
import glob
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "corpus"))
sys.path.insert(0, ROOT)

import build_pilot as bp  # noqa: E402
import build_offline as bo  # noqa: E402


def _convert(wt, **kw):
  return bp.convert_article("T", 1, 2, "ts", wt, **kw)


def _texts(sections):
  return [(h, p[0]) for h, _, paras in sections for p in paras]


class ConverterRegression(unittest.TestCase):
  def test_nested_templates_removed_prose_kept(self):
    wt = "Lead kept.\n\n{{outer|a={{inner|x}}|b=2}}\n\nTail kept."
    texts = [t for _, t in _texts(_convert(wt))]
    self.assertIn("Lead kept.", texts)
    self.assertIn("Tail kept.", texts)
    self.assertFalse(any("{{" in t or "inner" in t for t in texts))

  def test_file_caption_with_nested_links_removed(self):
    wt = ("See [[Real Target|shown]].\n\n"
          "[[File:Img.png|thumb|Caption with [[Nested]] link]]\n\nAfter the image block here.")
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("shown", joined)
    self.assertNotIn("Nested", joined)
    self.assertNotIn("File:", joined)
    self.assertIn("After the image block here.", texts)

  def test_unclosed_layout_table_keeps_prose(self):
    wt = ("== People ==\n\n{|width=\"100%\" |\n|style=\"width:50%\"|\n\n"
          "====A====\n*[[Alice Adams]] (1900-1950), writer\n")
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("Alice Adams", joined)
    self.assertNotIn("{|", joined)

  def test_template_generated_table_rows_removed(self):
    wt = ("== Mayor ==\n\n{{election table}}\n! Votes\n! %\n|-\n"
          "|bgcolor=x|\n|168,166\n|}\n\nProse kept here.")
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("Prose kept here.", joined)
    self.assertNotIn("bgcolor", joined)
    self.assertNotIn("168,166", joined)

  def test_onlyinclude_prefixed_table_removed(self):
    wt = ("== T ==\n\n<onlyinclude>{| class=\"wikitable\"\n|+ Cap\n"
          "|-\n! H\n|-\n| cell\n|}\n\nAfter table.")
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("After table.", texts)
    self.assertNotIn("wikitable", joined)

  def test_html_comments_removed(self):
    wt = "Before.<!-- hidden note -->\n\n<!--multi\nline-->\nAfter."
    texts = [t for _, t in _texts(_convert(wt))]
    self.assertNotIn("hidden", "\n".join(texts))

  def test_h5_folded_h2_sections_kept(self):
    wt = "Lead paragraph here.\n\n== S ==\n\nBody paragraph here.\n\n===== Deep =====\n\nDetail paragraph here."
    heads = [h for h, _, _ in _convert(wt)]
    self.assertIn("(lead)", heads)
    self.assertIn("S", heads)
    self.assertNotIn("Deep", heads)

  def test_long_prose_chunked_without_loss(self):
    sents = ["Sentence number %d with ample content to chew on at length." % i for i in range(200)]
    wt = "== Long ==\n\n" + " ".join(sents)
    st = collections.Counter()
    sects = _convert(wt, stats=st, sent_cap=None)
    texts = [t for _, t in _texts(sects)]
    self.assertGreater(len(texts), 1)
    self.assertTrue(all(len(t) <= 4000 for t in texts))
    for s in sents:
      self.assertTrue(any(s in t for t in texts), s[:40])

  def test_sent_cap_none_preserves_all(self):
    wt = "== S ==\n\n" + " ".join("Fact %d here." % i for i in range(40))
    a = _convert(wt, sent_cap=12)
    b = _convert(wt, sent_cap=None)
    na = sum(len(bp.split_sentences(p[0], cap=12)) for _, _, ps in a for p in ps)
    nb = sum(len(bp.split_sentences(p[0], cap=None)) for _, _, ps in b for p in ps)
    self.assertGreaterEqual(nb, na)
    self.assertEqual(nb, 40)

  def test_default_path_unchanged_signature(self):
    # Default call must work without stats/cap args (run-1 compatible).
    sects = bp.convert_article("T", 1, 2, "ts", "Lead paragraph here.\n\n== S ==\n\nBody paragraph here.")
    self.assertTrue(any(h == "S" for h, _, _ in sects))

  def test_cvt_convert_rescued(self):
    wt = "Radius {{cvt|60,268|km|mi}} versus {{convert|100|ft|abbr=on}} total."
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("60,268 km", joined)
    self.assertIn("100 ft", joined)

  def test_math_mvar_sub_rescued(self):
    wt = "Force {{math|'''F'''}} with {{mvar|d}} digits and F{{sub|n}} terms."
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("F", joined)
    self.assertIn("digits", joined)
    self.assertNotIn("{{", joined)

  def test_gallery_caption_kept_filename_dropped(self):
    wt = ("== People ==\n\n<gallery>\nFile:A.jpg|[[Alice Adams]], writer\n"
          "File:Bare.jpg\n</gallery>\n\nAfter gallery here.")
    texts = [t for _, t in _texts(_convert(wt))]
    joined = "\n".join(texts)
    self.assertIn("Alice Adams", joined)
    self.assertNotIn("File:", joined)
    self.assertNotIn("Bare.jpg", joined)


class OfflinePath(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp(prefix="corpus-offline-test-")
    raws = sorted(glob.glob(os.path.join(ROOT, "corpus", "raw", "*.json")))
    picks = []
    for want in ("munich", "pi", "monty_python"):
      hit = [r for r in raws if os.path.basename(r) == want + ".json"]
      picks.extend(hit)
    assert len(picks) == 3, picks
    cls.fixture_dir = os.path.join(cls.tmp, "raw")
    os.makedirs(cls.fixture_dir)
    for r in picks:
      shutil.copy(r, cls.fixture_dir)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp, ignore_errors=True)

  def test_source_has_no_network_references(self):
    # Usage scan (docstring disclaimers excluded by requiring call syntax).
    src = open(os.path.join(ROOT, "corpus", "build_offline.py"), encoding="utf-8").read()
    for token in ("bp.api_get", "api_get(", "fetch_article(", "urlopen",
                  "import urllib", "import socket", "import requests",
                  "http.client"):
      self.assertNotIn(token, src, token)

  def test_offline_path_never_touches_network(self):
    import socket
    real_socket, real_api = socket.socket, bp.api_get
    calls = []

    def _blocked(*a, **k):
      calls.append("socket")
      raise RuntimeError("network blocked in test")

    def _noapi(*a, **k):
      calls.append("api_get")
      raise RuntimeError("api_get must never be called offline")
    socket.socket, bp.api_get = _blocked, _noapi
    try:
      stage = os.path.join(self.tmp, "stage-netproof")
      summary = bo.run_offline(self.fixture_dir, stage, "test-netproof")
    finally:
      socket.socket, bp.api_get = real_socket, real_api
    self.assertEqual(calls, [])
    self.assertEqual(summary["articles"], 3)

  def test_offline_build_deterministic(self):
    a = os.path.join(self.tmp, "stage-a")
    b = os.path.join(self.tmp, "stage-b")
    sa = bo.run_offline(self.fixture_dir, a, "test-det")
    sb = bo.run_offline(self.fixture_dir, b, "test-det")
    self.assertEqual(sa["corpus_hash"], sb["corpus_hash"])
    for name in ("corpus.jsonl", "split_map.json", "input_manifest.json"):
      with open(os.path.join(a, name), "rb") as f1, open(os.path.join(b, name), "rb") as f2:
        self.assertEqual(f1.read(), f2.read(), name)
    pa = json.load(open(os.path.join(a, "provenance.json"), encoding="utf-8"))
    pb = json.load(open(os.path.join(b, "provenance.json"), encoding="utf-8"))
    pa.pop("built_utc", None)
    pb.pop("built_utc", None)
    self.assertEqual(pa, pb)

  def test_offline_staged_outputs_validate(self):
    from substrate.corpus import (corpus_hash, nodes_from_jsonl,
                                  validate_hierarchy)
    stage = os.path.join(self.tmp, "stage-validate")
    summary = bo.run_offline(self.fixture_dir, stage, "test-val")
    nodes = nodes_from_jsonl(open(os.path.join(stage, "corpus.jsonl"), encoding="utf-8").read())
    self.assertEqual(validate_hierarchy(nodes), [])
    self.assertEqual(corpus_hash(nodes), summary["corpus_hash"])
    kinds = collections.Counter(n.kind for n in nodes)
    self.assertEqual(kinds["article"], 3)
    self.assertGreater(kinds["sentence"], kinds["paragraph"])


if __name__ == "__main__":
  unittest.main()
