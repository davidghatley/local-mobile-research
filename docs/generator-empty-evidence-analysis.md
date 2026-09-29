# Empty-Evidence Diagnostic: Model Behavior vs Session Contamination

Worker: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost). No nested agents. Scope: `scripts/generator_empty_probe.py`,
`generator_runtime/empty_probe_*`, this file. The adapter, fixed
generator/model/prompt/settings were NOT modified and NOT tuned; the probe
is diagnostic only, not an acceptance gate or generator tournament.

## Predeclared design (paired synthetic comparison)

Fixed synthetic question ("synthetic widget tolerance threshold"),
threads=1, seed 1234, temp 0.0/top_k 1, prompt v0.2 (d8580509…):
- Leg A (fresh): 3 independent fresh `llama-server` processes answer the
  zero-span packet. Baseline.
- Leg B (resident-after-evidence): 2 fresh processes answer the
  evidence-bearing query first, then the identical empty question.
- Leg C (resident-empty-first): 2 fresh processes, reversed order.
Attribution rule: A-identical + B==A → intrinsic; B systematically ≠ A →
possible contamination; variance everywhere → no attribution.

Per-request verified (not assumed): rendered messages logged + sha'd,
evidence block byte-empty, exactly one user message (no history),
`cache_prompt=false` read from live settings, usage vs `/apply-template`
token equality checked.

## Observation (raw: `generator_runtime/empty_probe_20260928T232340.json`)

All 7 empty-question answers — 3 fresh PIDs (1673908/1673938/1673974),
2 post-evidence (1674017/1674079), 2 pre-evidence (1674152/1674202) — are
BYTE-IDENTICAL (sha `c3cd974d…`):

> The synthetic widget tolerance threshold is 0.5.

Request integrity (leg A run 0, representative of all): evidence block
empty (`EVIDENCE:\n\n\nQUESTION`), single user message, cache_prompt
false, seed 1234, threads 1. Accounting: evidence 0 / user-prompt 86 /
templated 115 / usage 115 (equal) / completion 12, finish stop.
Citations emitted: none; available: none; unknown: none.

Control legs confirm healthy sessions: B-first and C-second
evidence-bearing answers both correctly state "5 units" (usage 156 ==
templated 156). Prior evidence did not alter the empty answer; prior
emptiness did not alter the evidence answer. No order effect either way.

## Interpretation: failure reproduced without prior session evidence

Observed: B == A == C exactly across 7 fresh process IDs. The unsupported
answer occurs even without a preceding evidence-bearing request, so prior
session evidence is not necessary to produce this failure. No order effect
was detected in this probe. This supports a model/prompt behavior explanation
for this configuration; output equality alone does not prove the absence of
all possible cache or session-state defects. With zero evidence the pinned
generator repeatedly asserts a precise unsupported number instead of stating
insufficiency as the fixed prompt instructs.

## Unsupported-claim record (objective)

Zero-evidence answer claims "threshold is 0.5": available citations = ∅,
emitted citations = ∅, evidence tokens = 0. The claim has no backing
whatsoever — not a citation-format failure (as in the v0.1 `[node_id]`
case) but an unsupported factual assertion. Its numerical resemblance to the
evidence-bearing fixture's "5 units" does not establish a causal connection;
the same output appears in fresh processes that have not received that fixture.

## Limits

Single synthetic prompt, single seed, single model/quant, threads=1,
prompt v0.2. Result probes THIS configuration's reproducibility, not a
universal guarantee. No remedy is implemented here (no adapter forcing,
no suppression): candidate responses belong to upstream sufficiency
gating / the later generator tournament / orchestrator decision.

## Reproduce

`python3 scripts/generator_empty_probe.py --fresh 3 --resident 2`
(`--help` exits cleanly, no side effects). Raw output:
`generator_runtime/empty_probe_20260928T232340.json`.
