"""THE GENERATOR-FLOOR PROBE -- the hard gate of Round 1.

`experiments/comparability/CONTRACT.md` §5, with the orchestrator correction of
2026-10-03 that `experiments/R1_CONTRACT_ERRATUM.md` records. This module
implements the probe exactly as specified and refuses to emit a verdict it cannot
support.

Why this gate exists
--------------------
The whole tournament assumes that better evidence produces better answers from a
fixed Qwen2.5-1.5B Q4_K_M generator. If that generator cannot express the
difference, the retrieval tournament measures nothing above its own floor and
every architecture number is noise around a constant. The probe is cheap and its
asymmetry is what makes it worth running early: a LARGE oracle delta is easy to
detect, so the probe can prove the generator is NOT floored even though it cannot
resolve small effects.

Arms (PAIRED -- same items, same generator, same prompt, same decoding, same
1000-token exact-token budget; ONLY the span selection differs):

  oracle     the custodian's minimal complete sufficient set of host
             paragraphs, packed by the shared policy
  B4         BM25 top-500 through the shared packing policy. This is the
             preregistered baseline arm from HYPOTHESIS.md §6.
  degraded   BM25's WORST-ranked paragraphs with every required host excluded.
             A negative control: it establishes that the generator DOES
             discriminate when evidence quality differs, so a null
             oracle-vs-B4 result can be read as "no ceiling to detect" rather
             than "the generator cannot see evidence at all".

The decision rule, three-way, from CONTRACT.md §5 as corrected
-------------------------------------------------------------
Let ``I`` be the McNemar interval for the oracle's advantage over B4.

  * ``I`` excludes 0                                -> NOT FLOORED, proceed
  * ``I`` includes 0 and its upper bound < MMD       -> FLOORED, STOP
  * ``I`` includes 0 and its upper bound >= MMD      -> UNDERPOWERED / INCONCLUSIVE

The superseded rule was "floor if the delta is <= 5%". 5% is below what this
probe can measure, so that rule would have declared a floor on the basis of a
difference it could not detect. It is recorded in the erratum and is NOT used
here. "UNDERPOWERED" is a distinct outcome and is never collapsed into either
neighbour.
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.answer_scoring import exact_match, normalize_answer  # noqa: E402

# Minimum meaningful difference, from experiments/comparability/CONTRACT.md §4.
# This is the THRESHOLD REGISTER (R1_CONTRACT_ERRATUM.md E-1b): one number, one
# place. It is copied here as a named constant so a reader can see the probe is
# gating on the registered value, but it is NOT a tunable and nothing in this run
# may substitute a different one.
MMD_BY_SPLIT_SET = {
  "dev": {"n": 59, "mmd_items": 13, "mmd_pp": 22.0},
  "dev+shadow_dev": {"n": 146, "mmd_items": 18, "mmd_pp": 12.3},
  "shadow_dev": {"n": 87, "mmd_items": 15, "mmd_pp": 17.2},
}

ALPHA = 0.05


@dataclass
class ArmResult:
  question_id: str
  arm: str
  scored: bool
  correct: bool | None
  abstain_outcome: str | None
  answer_text: str | None
  exact_evidence_tokens: int | None
  n_spans: int
  truncated: bool
  latency_ms: float
  reason_unscored: str | None = None


@dataclass
class FloorProbe:
  split_set: str
  arms: dict[str, list[ArmResult]] = field(default_factory=dict)
  n_paired_scored: int = 0
  b: tuple[int, int, int, int] | None = None  # (n01, n10, n00_disc, n11) see below
  notes: list[str] = field(default_factory=list)

  # -- paired analysis --------------------------------------------------

  def mcnemar(self, arm_a: str, arm_b: str) -> dict:
    """Exact McNemar on the paired per-item correctness of two arms.

    Table convention, stated explicitly because getting it backwards flips the
    sign of the conclusion:

      n10 = A correct, B incorrect   (A's advantage)
      n01 = A incorrect, B correct   (B's advantage)
      discordant d = n10 + n01

    Exact two-sided binomial p on ``n10`` under H0: p = 0.5. The interval for the
    oracle's advantage is the Wilson interval on ``n10 / d`` mapped into
    proportions of the PAIRED SET (so it is comparable with the MMD, which is
    stated in items over n), which is why it is also reported as an item count.
    """
    A = {r.question_id: r for r in self.arms[arm_a]}
    B = {r.question_id: r for r in self.arms[arm_b]}
    common = sorted(set(A) & set(B))
    n10 = n01 = 0
    n_both = n_neither = 0
    for qid in common:
      a, b = A[qid], B[qid]
      if not (a.scored and b.scored):
        continue
      if a.correct and not b.correct:
        n10 += 1
      elif b.correct and not a.correct:
        n01 += 1
      elif a.correct and b.correct:
        n_both += 1
      else:
        n_neither += 1
    d = n10 + n01
    n = n_both + n_neither + d
    p = _mcnemar_exact_two_sided(n10, d)
    # Interval for the oracle's advantage, as a PROPORTION of the paired set.
    #
    # Why a proportion and not an item count: the registered MMD is stated in
    # items over the FULL split (e.g. 13 items of 59). Converting the observed
    # interval to items by multiplying by the OBSERVED n makes a small run look
    # precise -- a Wilson upper bound of 1.0 at n=3 becomes "3 items", which
    # sits below a 13-item MMD and would declare a floor on three observations.
    # Both quantities are therefore kept as proportions and compared there.
    if d > 0:
      lo, hi = _wilson(n10, d, z=1.96)
      basis = "wilson_on_discordant"
    else:
      # Zero discordant pairs: the observed advantage rate is 0, but the
      # UNCERTAINTY is not. Reporting [0, 0] here would be the exact error the
      # erratum warns about -- reading "we measured nothing" as "we bounded the
      # effect at nothing". Use the exact Clopper-Pearson one-sided 95% upper
      # bound for 0 successes in d trials instead, which is the honest statement.
      lo, hi = 0.0, _cp_upper_zero_successes(n if n else 1)
      basis = "clopper_pearson_upper_zero_discordant"
    return {
      "arm_a": arm_a,
      "arm_b": arm_b,
      "n_paired_scored": n,
      "concordant_both_correct": n_both,
      "concordant_both_wrong": n_neither,
      "discordant": d,
      "discordant_a_better": n10,
      "discordant_b_better": n01,
      "discordance_rate": (d / n) if n else None,
      "favour_a_share_of_discordant": (n10 / d) if d else None,
      "exact_mcnemar_p_two_sided": p,
      "advantage_interval_basis": basis,
      "advantage_interval_lower": lo,
      "advantage_interval_upper": hi,
      "advantage_items_at_observed_n": {
        "lower": lo * n if n else None,
        "upper": hi * n if n else None,
      },
    }


def _wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
  if n == 0:
    return (0.0, 0.0)
  p = hits / n
  z2 = z * z
  center = (p + z2 / (2 * n)) / (1 + z2 / n)
  half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
  return (max(0.0, center - half), min(1.0, center + half))


def _binom_cdf(k: int, n: int, p: float) -> float:
  """P(X <= k) for X ~ Binomial(n, p). Exact via summation, stdlib only."""
  if k < 0:
    return 0.0
  if k >= n:
    return 1.0
  total = 0.0
  for i in range(k + 1):
    total += math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
  return total


def _mcnemar_exact_two_sided(n10: int, d: int) -> float | None:
  """Exact two-sided McNemar p-value. None when there are no discordant pairs.

  Under H0 the discordant pairs are a fair coin, so n10 ~ Binomial(d, 0.5). The
  two-sided p doubles the smaller tail, capped at 1. With d == 0 the test has no
  information and returns None rather than a misleading p == 1.0, because "no
  discordant pairs observed" is not the same claim as "measured and found null".
  """
  if d == 0:
    return None
  k = min(n10, d - n10)
  return min(1.0, 2.0 * _binom_cdf(k, d, 0.5))


def _cp_upper_zero_successes(n: int, alpha: float = 0.05) -> float:
  """Exact one-sided (1 - alpha) upper bound on p for 0 observed successes in n.

  Solves ``P(X <= 0 | p, n) = alpha`` for p, i.e. ``(1-p)^n = alpha``, by bisection
  on the exact binomial CDF so the bound does not depend on scipy. For n = 59 this
  is ~0.0498, the familiar rule-of-three neighbourhood; for n = 3 it is ~0.634,
  which is the whole reason it must be used instead of a hard 0.
  """
  if n <= 0:
    return 1.0
  lo, hi = 0.0, 1.0
  # We want the largest p with P(X<=0) <= alpha, i.e. (1-p)^n <= alpha.
  for _ in range(200):
    mid = (lo + hi) / 2.0
    if (1.0 - mid) ** n > alpha:
      lo = mid
    else:
      hi = mid
  return hi


def decide(stat: dict, mmd_items: int, mmd_n: int) -> dict:
  """The three-way rule. Never collapses UNDERPOWERED into either neighbour.

  The registered MMD is an ITEM COUNT (13 items on dev), so that is the unit the
  verdict is expressed in, and the interval is converted back to items by
  multiplying by the number of ANALYSABLE pairs actually scored.

  Two guards, in order, because each exists to stop a specific wrong verdict:

  1. Fewer analysable pairs than the MMD's item count -> INCONCLUSIVE. You cannot
     bound a 13-item effect from fewer than 13 observations. This is deliberately
     NOT ``n >= mmd_n``: ``mmd_n`` is the SPLIT size (59), while the paired test
     only ever sees items that have a gold answer string. On dev, 4 of the 59
     items are ambiguous or unanswerable and carry no ``answer_text``, so only
     55 are analysable and a guard of ``n >= 59`` would refuse a verdict on a
     complete, correctly-run dev sweep forever. Gating on ``n >= mmd_items`` is
     the correct invariant, and the analysable-n shortfall is reported explicitly
     instead of being hidden inside the threshold.
  2. Interval excludes 0 (exact McNemar significant, lower bound > 0) -> NOT
     FLOORED.
  3. Otherwise the interval's UPPER bound decides, against the MMD.

  The superseded rule was "floor if the delta is <= 5%", which is below what this
  probe can measure. It is recorded in `experiments/R1_CONTRACT_ERRATUM.md` and is
  deliberately not used.
  """
  n = stat["n_paired_scored"]
  if n == 0:
    return {
      "verdict": "INCONCLUSIVE",
      "reason": "no paired scorable items; the probe could not run",
      "may_proceed": False,
    }
  if n < mmd_items:
    return {
      "verdict": "INCONCLUSIVE",
      "reason": (
        f"only {n} analysable paired items but the registered MMD is "
        f"{mmd_items} items: fewer observations than the effect being tested "
        f"for. A partial run cannot bound a {mmd_items}-item effect."
      ),
      "may_proceed": False,
    }
  hi = stat["advantage_interval_upper"]
  lo = stat["advantage_interval_lower"]
  p = stat["exact_mcnemar_p_two_sided"]
  hi_items = hi * n
  lo_items = lo * n
  caveat = (
    f" The registered MMD is {mmd_items} items over a split of n={mmd_n}; only "
    f"{n} of those {mmd_n} items are analysable (the rest carry no gold answer "
    f"string), so the effective analysable-n is {n} rather than {mmd_n}. That "
    f"REDUCES power relative to the registered calculation and this verdict is "
    f"correspondingly conservative."
  ) if n < mmd_n else ""
  if p is not None and p < ALPHA and lo_items > 0.0:
    return {
      "verdict": "GENERATOR NOT FLOORED",
      "reason": (
        f"exact McNemar p={p:.4g} < {ALPHA} and the oracle's advantage interval "
        f"[{lo_items:.1f}, {hi_items:.1f}] of {n} analysable items excludes 0; "
        f"registered MMD is {mmd_items} items.{caveat}"
      ),
      "may_proceed": True,
    }
  if hi_items < mmd_items:
    return {
      "verdict": "GENERATOR FLOORED",
      "reason": (
        f"the advantage interval includes 0 and its upper bound ({hi_items:.1f} "
        f"items of {n}) is below the registered minimum meaningful difference "
        f"({mmd_items} items): the benefit of perfect evidence is bounded below "
        f"anything this corpus could call real. Interval basis: "
        f"{stat['advantage_interval_basis']}.{caveat}"
      ),
      "may_proceed": False,
      "action": "STOP the main tournament and report the floor",
    }
  return {
    "verdict": "UNDERPOWERED / INCONCLUSIVE",
    "reason": (
      f"the advantage interval includes 0 and its upper bound ({hi_items:.1f} "
      f"items of {n}) reaches or exceeds the registered MMD ({mmd_items} "
      f"items): this probe cannot distinguish 'floored' from 'not floored' at "
      f"this sample size. The remedy is more items or a more sensitive probe, "
      f"NOT a verdict. Interval basis: {stat['advantage_interval_basis']}.{caveat}"
    ),
    "may_proceed": True,
    "caveat": (
      "continue retrieval-primary experiments, whose objective evidence metrics "
      "remain interpretable; do NOT over-interpret final-answer differences"
    ),
  }


def score_answer(arm_text: str | None, gold: str | None) -> tuple[bool, bool, str | None]:
  """Deterministic scoring. Returns (scored, correct, reason_unscored).

  Uses only `eval/answer_scoring`, which is stdlib-only and pure. No judge, no
  model, no fuzzy matching: a floor probe decided by a judge would be measuring
  the judge.
  """
  if gold is None or not str(gold).strip():
    return (False, None, "no_gold_answer_text")
  if arm_text is None:
    return (False, None, "abstained_or_no_generation")
  return (True, exact_match(arm_text, gold), None)


def containment(arm_text: str | None, gold: str | None) -> bool | None:
  """EXPLORATORY, NOT PREREGISTERED. Is the gold answer contained in the output?

  Why this exists, stated as a confound rather than as a better metric:

  the fixed prompt makes the generator append a citation justification, and the
  length of that appendage grows with the size of the evidence packet. Under
  strict `exact_match`, a verbose answer that names the right entity SCORES WRONG.
  So a smaller evidence packet can raise the answer score purely by making the
  generator terser, with no improvement in relevance whatsoever.

  That confound is real and it runs in BOTH directions: it can manufacture an
  apparent oracle advantage (oracle packets are tighter), and it can hide a real
  one. So both numbers are recorded and the preregistered one stays primary.

  It is deliberately NOT promoted to primary: it has no registered threshold, it
  is trivially gamed by any system that emits the whole packet back, and calling
  it preregistered after seeing that it moves would be exactly the kind of
  post-hoc threshold invention this repository exists to prevent.
  """
  if arm_text is None or gold is None or not str(gold).strip():
    return None
  return normalize_answer(gold) in normalize_answer(arm_text)


def summarize_arms(results: dict[str, list[ArmResult]]) -> dict:
  """Per-arm accuracy over scorable items. Counts, never a story."""
  out = {}
  for arm, rows in results.items():
    scored = [r for r in rows if r.scored]
    correct = sum(1 for r in scored if r.correct)
    toks = [r.exact_evidence_tokens for r in rows if r.exact_evidence_tokens is not None]
    out[arm] = {
      "n_items": len(rows),
      "n_scored": len(scored),
      "n_correct": correct,
      "accuracy": (correct / len(scored)) if scored else None,
      "n_unscored": len(rows) - len(scored),
      "abstentions": sum(1 for r in rows if r.answer_text is None),
      "mean_exact_evidence_tokens": (sum(toks) / len(toks)) if toks else None,
      "max_exact_evidence_tokens": max(toks) if toks else None,
      "mean_latency_ms": (sum(r.latency_ms for r in rows) / len(rows)) if rows else None,
    }
  return out


def write_report(path: str, payload: dict) -> None:
  os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
  with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
