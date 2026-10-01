"""Lane C gate tests: first-class EvidenceDecision + shared run_question gate.

Synthetic/infra fixtures only (hand-built packets, counting mocks). Never
real sealed labels. Trace-shape assertions mirror
docs/abstention-and-telemetry-notes.md so the run_format worker can rely on
(run_question returns (outcome, decision, response)); the rule predicates
here assert the documented relations on those outputs.
"""

import unittest

from eval.metrics import abstention_outcome, abstention_summary
from substrate import evidence as ev
from substrate.types import (
  EvidenceDecision, EvidencePacket, EvidenceSpan, GeneratedAnswer, Question,
  RetrievalOutcome, ThresholdPolicy,
)


def _packet(spans=(), truncated=False):
  return EvidencePacket(
    question_id="q-synth-1",
    spans=tuple(spans),
    citations=tuple(s.node_id for s in spans),
    token_estimate=0,
    truncated=truncated,
  )


def _outcome(packet):
  return RetrievalOutcome(
    question_id="q-synth-1", packet=packet, stages=(), total_latency_ms=0.0)


def _span(node_id="n1"):
  return EvidenceSpan(node_id=node_id, text="synthetic fixture text")


class FakeRetriever:
  def __init__(self, outcome):
    self._outcome = outcome
    self.calls = 0

  def retrieve(self, question):
    self.calls += 1
    return self._outcome


class CountingGenerator:
  generator_id = "counting-mock-v0"
  prompt_hash = "mock"

  def __init__(self):
    self.calls = 0

  def generate(self, question, packet):
    self.calls += 1
    return GeneratedAnswer(
      question_id=question.question_id,
      answer_text="synthetic answer",
      citations=(),
      generator_id=self.generator_id,
      prompt_hash=self.prompt_hash,
      evidence_token_estimate=0,
    )


def _trace_dict(decision, response):
  invoked = response is not None
  return {
    "evidence_decision": decision.decision,
    "generation_action": decision.generation_action,
    "generator_invoked": invoked,
    "generator_response": None if response is None else response.to_dict(),
    "sufficiency_score": decision.sufficiency_score,
    "sufficiency_score_kind": decision.sufficiency_score_kind,
    "sufficiency_policy": None
    if decision.sufficiency_policy is None
    else decision.sufficiency_policy.to_dict(),
    "decision_reason": decision.reason,
  }


class TestEvidenceDecisionInvariant(unittest.TestCase):
  def test_mismatch_abstain_without_insufficient_raises(self):
    with self.assertRaises(ValueError):
      EvidenceDecision(decision="sufficient", generation_action="abstain")

  def test_mismatch_insufficient_without_abstain_raises(self):
    with self.assertRaises(ValueError):
      EvidenceDecision(decision="insufficient", generation_action="generate")

  def test_matched_pairs_construct(self):
    ok_abstain = EvidenceDecision(
      decision="insufficient", generation_action="abstain", reason="zero-spans")
    ok_gen = EvidenceDecision(
      decision="sufficient", generation_action="generate",
      reason="nonempty-packet")
    self.assertEqual(ok_abstain.decision, "insufficient")
    self.assertEqual(ok_gen.generation_action, "generate")

  def test_score_without_kind_domain_raises(self):
    with self.assertRaises(ValueError):
      EvidenceDecision(
        decision="sufficient", generation_action="generate",
        sufficiency_score=0.7, sufficiency_score_kind="unspecified",
        reason="nonempty-packet")

  def test_scored_decision_round_trips(self):
    policy = ThresholdPolicy(
      threshold=0.5, interpretation="calibrated_probability",
      calibration_method="model_probability", score_kind="model_probability")
    d = EvidenceDecision(
      decision="sufficient", generation_action="generate",
      sufficiency_score=0.7, sufficiency_score_kind="model_probability",
      sufficiency_policy=policy, reason="arch-policy")
    back = EvidenceDecision.from_dict(d.to_dict())
    self.assertEqual(back, d)


class TestDecideDefault(unittest.TestCase):
  def test_zero_spans_abstains(self):
    d = ev.decide_default(_packet())
    self.assertEqual((d.decision, d.generation_action, d.reason),
                     ("insufficient", "abstain", "zero-spans"))

  def test_over_budget_empty_has_distinct_code(self):
    d = ev.decide_default(_packet(truncated=True))
    self.assertEqual((d.decision, d.generation_action, d.reason),
                     ("insufficient", "abstain", "over-budget-empty"))

  def test_nonempty_packet_generates(self):
    d = ev.decide_default(_packet(spans=[_span()]))
    self.assertEqual((d.decision, d.generation_action, d.reason),
                     ("sufficient", "generate", "nonempty-packet"))


class TestRunQuestionGate(unittest.TestCase):
  def test_insufficient_evidence_generator_not_invoked(self):
    q = Question(question_id="q-synth-1", text="synthetic?")
    gen = CountingGenerator()
    outcome, decision, response = ev.run_question(
      FakeRetriever(_outcome(_packet())), gen, q)
    self.assertEqual(gen.calls, 0)
    self.assertIsNone(response)
    self.assertEqual(decision.generation_action, "abstain")
    trace = _trace_dict(decision, response)
    self.assertFalse(trace["generator_invoked"])
    self.assertIsNone(trace["generator_response"])
    # Cross-field rules from the notes: abstain + invoked => reject;
    # not-invoked + non-null response => reject. Neither fires here.
    self.assertFalse(
      trace["generation_action"] == "abstain" and trace["generator_invoked"])
    self.assertFalse(
      not trace["generator_invoked"] and trace["generator_response"] is not None)

  def test_over_budget_empty_generator_not_invoked(self):
    q = Question(question_id="q-synth-1", text="synthetic?")
    gen = CountingGenerator()
    _, decision, response = ev.run_question(
      FakeRetriever(_outcome(_packet(truncated=True))), gen, q)
    self.assertEqual(gen.calls, 0)
    self.assertIsNone(response)
    self.assertEqual(decision.reason, "over-budget-empty")

  def test_sufficient_evidence_generator_invoked_once(self):
    q = Question(question_id="q-synth-1", text="synthetic?")
    gen = CountingGenerator()
    _, decision, response = ev.run_question(
      FakeRetriever(_outcome(_packet(spans=[_span()]))), gen, q)
    self.assertEqual(gen.calls, 1)
    self.assertIsNotNone(response)
    trace = _trace_dict(decision, response)
    self.assertTrue(trace["generator_invoked"])
    self.assertIsNotNone(trace["generator_response"])


class TestAbstentionMetrics(unittest.TestCase):
  def test_answerable_abstain_is_false_abstention_failure(self):
    self.assertEqual(
      abstention_outcome(answerable=True, abstained=True), "false_abstention")
    summary = abstention_summary([{"answerable": True, "abstained": True}])
    self.assertEqual(summary["false_abstention"], {"n": 1, "den": 1, "rate": 1.0})
    self.assertEqual(summary["sufficiency_accuracy"]["rate"], 0.0)

  def test_unanswerable_abstain_is_correct_abstention_success(self):
    self.assertEqual(
      abstention_outcome(answerable=False, abstained=True),
      "correct_abstention")
    summary = abstention_summary([{"answerable": False, "abstained": True}])
    self.assertEqual(
      summary["correct_abstention"], {"n": 1, "den": 1, "rate": 1.0})
    self.assertEqual(summary["sufficiency_accuracy"]["rate"], 1.0)

  def test_unlabeled_input_yields_none_never_zero(self):
    self.assertIsNone(abstention_outcome(answerable=None, abstained=True))
    self.assertIsNone(abstention_outcome(answerable=None, abstained=False))
    summary = abstention_summary([
      {"answerable": None, "abstained": True},
      {"answerable": None, "abstained": False},
    ])
    for key in ("correct_abstention", "false_abstention",
                "unsupported_generation", "sufficiency_accuracy"):
      self.assertIsNone(summary[key]["rate"], key)
      self.assertEqual(summary[key]["den"], 0, key)
    self.assertEqual(summary["n_unlabeled"], 2)
    self.assertEqual(summary["n_labeled"], 0)

  def test_unsupported_generation_detected(self):
    self.assertEqual(
      abstention_outcome(answerable=False, abstained=False),
      "unsupported_generation")


if __name__ == "__main__":
  unittest.main()
