"""Support-semantics tests. All fixtures SYNTHETIC (no real corpus reads).

Chain fixture: R(corpus) -> C(cluster) -> A(article) -> S(section)
-> P(paragraph) -> {a, a_sib}(sentences); S also -> Q(paragraph) -> {b}.
Every parent text is the whitespace-joined concatenation of its children.
"""

import unittest

from eval.support import (
  atom_satisfaction,
  context_precision_report,
  covers,
  sufficient_set_completion_support,
)
from substrate.support_index import build_support_index
from substrate.types import CorpusNode, SupportAtom


def _node(node_id, kind, text, parent_id=None):
  return CorpusNode(node_id=node_id, kind=kind, text=text, parent_id=parent_id)


def _chain_nodes():
  a = "alpha beta gamma"
  a_sib = "delta epsilon zeta"
  b = "theta iota kappa"
  p = a + " " + a_sib
  q = b
  s = p + "\n" + q
  return [
    _node("R", "corpus", s),
    _node("C", "cluster", s, "R"),
    _node("A", "article", s, "C"),
    _node("S", "section", s, "A"),
    _node("P", "paragraph", p, "S"),
    _node("Q", "paragraph", q, "S"),
    _node("a", "sentence", a, "P"),
    _node("a_sib", "sentence", a_sib, "P"),
    _node("b", "sentence", b, "Q"),
  ]


def _words(text):
  return len(text.split())


def _setup():
  nodes = _chain_nodes()
  index = build_support_index(nodes)
  by_id = {n.node_id: n for n in nodes}
  return index, by_id


def _leaf(node_id, text):
  return SupportAtom(node_id=node_id, text=text, atom_kind="leaf")


class TestSupportIndexBasics(unittest.TestCase):
  def test_leaf_sets(self):
    index, _ = _setup()
    self.assertEqual(index.leaf_set("a"), frozenset({"a"}))
    self.assertEqual(index.leaf_set("P"), frozenset({"a", "a_sib"}))
    self.assertEqual(index.leaf_set("S"), frozenset({"a", "a_sib", "b"}))
    self.assertEqual(index.leaf_set("R"), frozenset({"a", "a_sib", "b"}))

  def test_atom_validation(self):
    with self.assertRaises(ValueError):
      SupportAtom(node_id="a", text="x", char_start=0, char_end=1, atom_kind="leaf")
    with self.assertRaises(ValueError):
      SupportAtom(node_id="a", text="x", atom_kind="phrase")
    with self.assertRaises(ValueError):
      SupportAtom(node_id="a", text="x", char_start=2, char_end=1, atom_kind="subspan")
    rt = SupportAtom.from_dict(_leaf("a", "alpha beta gamma").to_dict())
    self.assertEqual(rt, _leaf("a", "alpha beta gamma"))


class TestSupportSatisfaction(unittest.TestCase):
  def test_t1_direct_leaf_is_satisfied_exact(self):
    index, by_id = _setup()
    atom = _leaf("a", "alpha beta gamma")
    self.assertTrue(covers("a", atom, index, by_id))
    out = atom_satisfaction(["a"], [atom], index, by_id)
    self.assertEqual(out["satisfied_count"], 1)
    entry = out["per_atom"][0]
    self.assertTrue(entry["satisfied"])
    self.assertEqual(entry["covering_id"], "a")
    self.assertTrue(entry["exact"])
    self.assertFalse(entry["imprecise"])

  def test_t2_parent_satisfies_but_imprecise_with_worse_precision(self):
    index, by_id = _setup()
    atom = _leaf("a", "alpha beta gamma")
    self.assertTrue(covers("P", atom, index, by_id))
    out = atom_satisfaction(["P"], [atom], index, by_id)
    self.assertTrue(out["per_atom"][0]["satisfied"])
    self.assertEqual(out["per_atom"][0]["covering_id"], "P")
    self.assertFalse(out["per_atom"][0]["exact"])
    self.assertTrue(out["per_atom"][0]["imprecise"])
    rep_leaf = context_precision_report(["a"], [atom], index, by_id, _words)
    rep_par = context_precision_report(["P"], [atom], index, by_id, _words)
    self.assertLess(rep_par["leaf_precision"], rep_leaf["leaf_precision"])
    self.assertGreater(rep_par["total_tokens"], rep_leaf["total_tokens"])
    self.assertEqual(rep_leaf["overshoot_tokens"], 0)
    self.assertGreater(rep_par["overshoot_tokens"], 0)

  def test_t3_sibling_does_not_satisfy(self):
    index, by_id = _setup()
    atom = _leaf("a", "alpha beta gamma")
    self.assertFalse(covers("a_sib", atom, index, by_id))
    out = atom_satisfaction(["a_sib"], [atom], index, by_id)
    self.assertFalse(out["per_atom"][0]["satisfied"])
    self.assertIsNone(out["per_atom"][0]["covering_id"])

  def test_t4_unrelated_branch_excluded_true_ancestor_maximally_imprecise(self):
    index, by_id = _setup()
    atom = _leaf("a", "alpha beta gamma")
    for rid in ("Q", "b"):
      self.assertFalse(covers(rid, atom, index, by_id))
      out = atom_satisfaction([rid], [atom], index, by_id)
      self.assertFalse(out["per_atom"][0]["satisfied"])
    self.assertTrue(covers("S", atom, index, by_id))
    out = atom_satisfaction(["S"], [atom], index, by_id)
    self.assertTrue(out["per_atom"][0]["satisfied"])
    self.assertTrue(out["per_atom"][0]["imprecise"])
    rep_s = context_precision_report(["S"], [atom], index, by_id, _words)
    rep_p = context_precision_report(["P"], [atom], index, by_id, _words)
    self.assertEqual(rep_s["leaf_precision"], 0.0)
    self.assertGreater(rep_s["total_tokens"], rep_p["total_tokens"])


class TestSupportCompletion(unittest.TestCase):
  def test_t5_alternatives_and_partial_never_completes(self):
    index, by_id = _setup()
    a = _leaf("a", "alpha beta gamma")
    b = _leaf("b", "theta iota kappa")
    full = sufficient_set_completion_support(["P", "Q"], [[a, b]], index, by_id)
    self.assertEqual(full["completion"], 1.0)
    self.assertEqual(full["complete_sets"], [0])
    self.assertEqual(full["coverage_mode"], "support")
    alt = sufficient_set_completion_support(["Q"], [[a], [b]], index, by_id)
    self.assertEqual(alt["completion"], 1.0)
    self.assertEqual(alt["complete_sets"], [1])
    self.assertEqual(alt["best_set_index"], 1)
    partial = sufficient_set_completion_support(["a"], [[a, b]], index, by_id)
    self.assertEqual(partial["completion"], 0.0)
    self.assertEqual(partial["complete_sets"], [])
    self.assertAlmostEqual(partial["best_fractional_coverage"], 0.5)
    self.assertIsNone(sufficient_set_completion_support(["a"], [], index, by_id)["completion"])


class TestAntiRegression(unittest.TestCase):
  def test_t6_sentence_system_not_dominated_by_paragraph_system(self):
    index, by_id = _setup()
    atom = _leaf("a", "alpha beta gamma")
    sup_sent = atom_satisfaction(["a"], [atom], index, by_id)
    sup_par = atom_satisfaction(["P"], [atom], index, by_id)
    rep_sent = context_precision_report(["a"], [atom], index, by_id, _words)
    rep_par = context_precision_report(["P"], [atom], index, by_id, _words)
    self.assertGreaterEqual(sup_sent["satisfaction_rate"], sup_par["satisfaction_rate"])
    self.assertGreater(rep_sent["leaf_precision"], rep_par["leaf_precision"])
    self.assertLess(rep_sent["total_tokens"], rep_par["total_tokens"])

  def test_dual_metric_gaming_is_dominated(self):
    # Retrieving both a and P keeps support but loses exactness and costs more.
    index, by_id = _setup()
    atom = _leaf("a", "alpha beta gamma")
    sup_both = atom_satisfaction(["a", "P"], [atom], index, by_id)
    rep_both = context_precision_report(["a", "P"], [atom], index, by_id, _words)
    rep_sent = context_precision_report(["a"], [atom], index, by_id, _words)
    self.assertEqual(sup_both["satisfaction_rate"], 1.0)
    self.assertLess(rep_both["leaf_precision"], rep_sent["leaf_precision"])
    self.assertGreater(rep_both["total_tokens"], rep_sent["total_tokens"])


class TestSubspanAtoms(unittest.TestCase):
  def test_t7_subspan_containment(self):
    index, by_id = _setup()
    atom = SupportAtom(
      node_id="a", text="beta", char_start=6, char_end=10, atom_kind="subspan"
    )
    self.assertTrue(covers("a", atom, index, by_id))
    self.assertTrue(covers("P", atom, index, by_id))
    self.assertFalse(covers("a_sib", atom, index, by_id))
    self.assertFalse(covers("Q", atom, index, by_id))
    out = atom_satisfaction(["a"], [atom], index, by_id)
    self.assertTrue(out["per_atom"][0]["satisfied"])
    self.assertFalse(out["per_atom"][0]["exact"])


class TestIndexInvariant(unittest.TestCase):
  def test_t8_corrupted_fixture_raises(self):
    nodes = _chain_nodes()
    by_id = {n.node_id: n for n in nodes}
    # Non-whitespace gap between children.
    bad = _node(
      "P", "paragraph", by_id["a"].text + "!" + by_id["a_sib"].text, "S"
    )
    with self.assertRaises(ValueError):
      build_support_index([n for n in nodes if n.node_id != "P"] + [bad])
    # Absent child text.
    missing = _node("P", "paragraph", by_id["a"].text, "S")
    with self.assertRaises(ValueError):
      build_support_index([n for n in nodes if n.node_id != "P"] + [missing])


if __name__ == "__main__":
  unittest.main()
