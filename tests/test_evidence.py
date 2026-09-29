"""Evidence packet tests. Synthetic spans only; token counts are estimates."""

import unittest

from substrate.evidence import HARD_EVIDENCE_TOKEN_CAP, build_packet, estimate_tokens
from substrate.types import EvidenceSpan


def span(node_id, n_words):
  return EvidenceSpan(node_id=node_id, text=" ".join(["w"] * n_words))


class TestEvidence(unittest.TestCase):
  def test_estimate_is_whitespace_based(self):
    self.assertEqual(estimate_tokens("a b c"), 3)

  def test_cap_enforced_with_truncation_flag(self):
    spans = [span("p1", 600), span("p2", 600), span("p3", 10)]
    packet = build_packet("q1", spans)
    self.assertTrue(packet.truncated)
    self.assertLessEqual(packet.token_estimate, HARD_EVIDENCE_TOKEN_CAP)

  def test_citations_deduplicated_in_order(self):
    spans = [span("p1", 5), span("p1", 5), span("p2", 5)]
    packet = build_packet("q1", spans)
    self.assertEqual(list(packet.citations), ["p1", "p2"])

  def test_empty_spans_gives_empty_packet(self):
    packet = build_packet("q1", [])
    self.assertEqual(packet.token_estimate, 0)
    self.assertEqual(list(packet.citations), [])


if __name__ == "__main__":
  unittest.main()
