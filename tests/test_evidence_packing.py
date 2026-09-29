"""Evidence packing, prompt, and citation-parser tests. All SYNTHETIC."""

import unittest

from substrate.evidence import (
  HARD_EVIDENCE_TOKEN_CAP,
  build_packet,
  find_unknown_citations,
  parse_citations,
  serialize_evidence,
)
from substrate.generator import FIXED_GENERATION_PROMPT, PROMPT_HASH, render_prompt
from substrate.types import EvidenceSpan, Question, sha256_text


def span(node_id, text):
  return EvidenceSpan(node_id=node_id, text=text)


class TestFullSerializationCounting(unittest.TestCase):
  def test_separator_tokens_counted(self):
    seen = []

    def tok(text):
      seen.append(text)
      return len(text.split())

    packet = build_packet("q", [span("p1", "aa bb"), span("p2", "cc")],
                          cap=1000, tokenizer=tok, tokenizer_id="t", exact=True)
    # Baseline empty serialization first, then full serializations each step.
    self.assertEqual(seen[0], "")
    self.assertEqual(seen[1], "[p1] aa bb")
    self.assertIn("[p1] aa bb\n[p2] cc", seen[2])
    self.assertEqual(packet.exact_evidence_tokens, len("[p1] aa bb\n[p2] cc".split()))

  def test_nonadditive_tokenizer_honored(self):
    # SYNTHETIC subadditive tokenizer: shared prefix discounted once.
    def tok(text):
      return max(0, len(text.split()) - 2)

    a = build_packet("q", [span("p1", "aa bb"), span("p2", "cc dd")],
                     cap=1000, tokenizer=tok, tokenizer_id="t", exact=True)
    separate_sum = tok(serialize_evidence([span("p1", "aa bb")])) + tok(
      serialize_evidence([span("p2", "cc dd")]))
    self.assertNotEqual(a.exact_evidence_tokens, separate_sum)
    self.assertEqual(a.exact_evidence_tokens, tok(serialize_evidence(a.spans)))

  def test_strict_cap_never_exceeded_exact(self):
    def tok(text):
      return len(text.split())

    packet = build_packet("q", [span("p1", "a b"), span("p2", "c d e")],
                          cap=5, tokenizer=tok, tokenizer_id="t", exact=True)
    self.assertLessEqual(packet.exact_evidence_tokens, 5)
    self.assertTrue(packet.truncated)


class TestFirstSpanOverflow(unittest.TestCase):
  def test_first_oversize_yields_empty_truncated(self):
    def tok(text):
      return len(text.split())

    big = " ".join(["w"] * 2000)
    packet = build_packet("q", [span("p1", big), span("p2", "y")],
                          tokenizer=tok, tokenizer_id="t", exact=True)
    self.assertEqual(list(packet.spans), [])
    self.assertEqual(list(packet.citations), [])
    self.assertTrue(packet.truncated)
    self.assertEqual(packet.exact_evidence_tokens, 0)

  def test_first_oversize_estimate_path(self):
    packet = build_packet("q", [span("p1", " ".join(["w"] * 2000))])
    self.assertEqual(list(packet.spans), [])
    self.assertTrue(packet.truncated)

  def test_empty_input_is_not_truncated(self):
    packet = build_packet("q", [])
    self.assertEqual(list(packet.spans), [])
    self.assertFalse(packet.truncated)


class TestCapValidation(unittest.TestCase):
  def test_zero_cap_rejected(self):
    with self.assertRaises(ValueError):
      build_packet("q", [span("p1", "x")], cap=0)

  def test_negative_cap_rejected(self):
    with self.assertRaises(ValueError):
      build_packet("q", [span("p1", "x")], cap=-5)

  def test_bool_cap_rejected(self):
    with self.assertRaises(ValueError):
      build_packet("q", [span("p1", "x")], cap=True)

  def test_nonint_cap_rejected(self):
    with self.assertRaises(ValueError):
      build_packet("q", [span("p1", "x")], cap=10.5)


class TestTokenizerValidation(unittest.TestCase):
  def _packet(self, ret):
    return build_packet("q", [span("p1", "x")], tokenizer=lambda t: ret,
                        tokenizer_id="t", exact=True)

  def test_bool_return_rejected(self):
    with self.assertRaises(ValueError):
      self._packet(True)

  def test_float_return_rejected(self):
    with self.assertRaises(ValueError):
      self._packet(3.0)

  def test_nan_return_rejected(self):
    with self.assertRaises(ValueError):
      self._packet(float("nan"))

  def test_negative_return_rejected(self):
    with self.assertRaises(ValueError):
      self._packet(-1)

  def test_zero_return_accepted(self):
    self.assertEqual(self._packet(0).exact_evidence_tokens, 0)


class TestPromptV02(unittest.TestCase):
  def test_no_node_id_placeholder_literal(self):
    self.assertNotIn("[node_id]", FIXED_GENERATION_PROMPT)

  def test_example_and_placeholder_ban_present(self):
    self.assertIn("[source-7]", FIXED_GENERATION_PROMPT)
    self.assertIn("Do not write placeholder identifiers.", FIXED_GENERATION_PROMPT)

  def test_hash_matches_prompt(self):
    self.assertEqual(PROMPT_HASH, sha256_text(FIXED_GENERATION_PROMPT))

  def test_render_still_works(self):
    q = Question(question_id="q", text="synthetic?")
    packet = build_packet("q", [span("s1", "fact")])
    rendered = render_prompt(q, packet)
    self.assertIn("[s1] fact", rendered)
    self.assertIn("synthetic?", rendered)

  def test_hard_cap_preserved(self):
    self.assertEqual(HARD_EVIDENCE_TOKEN_CAP, 1000)


class TestParseCitations(unittest.TestCase):
  def test_extracts_dedup_appearance_order(self):
    self.assertEqual(parse_citations("A [p2] then [p1] again [p2]."), ["p2", "p1"])

  def test_skips_empty_and_nested(self):
    self.assertEqual(parse_citations("x [] y"), [])
    self.assertNotIn("", parse_citations("x [ ] y"))

  def test_strips_whitespace(self):
    self.assertEqual(parse_citations("[ p1 ]"), ["p1"])

  def test_unknown_not_auto_credited(self):
    emitted = parse_citations("Claim [ghost-9] and [p1].")
    unknown = find_unknown_citations(emitted, ["p1"])
    self.assertEqual(unknown, ["ghost-9"])

  def test_no_brackets_empty(self):
    self.assertEqual(parse_citations("plain text"), [])


if __name__ == "__main__":
  unittest.main()
