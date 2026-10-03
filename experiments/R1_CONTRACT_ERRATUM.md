# Round 1 Contract Erratum 1 — post-freeze corrections

Status: **POST-FREEZE ERRATUM.** Issued 2026-10-03, after
`round0-freeze-r1` (commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`).

`experiments/R1_TRAINING_CONTRACT.md` is a preregistered Round 0 closure
artifact. It is **deliberately left byte-identical to its frozen state.** This
document supersedes specific sentences in it, and says which. Editing a
preregistered contract after the fact without marking it as an edit would defeat
the point of preregistering it; so the correction lives here, is dated, and is
visible to anyone who reads the contract.

Anything in `R1_TRAINING_CONTRACT.md` not listed below stands unaltered.

---

## E-1. §5, lines 118-120 — the leakage gate is no longer unable to issue PASS

**The frozen text says:**

> Honest current limitation (carried from Round 0 status): the gate's hash-only
> comparison is not yet bound to the seal; until it is, the gate correctly
> refuses to issue PASS.

**That is stale.** It describes the gate *before* the Round 0 closure repairs.
Independent review v6 found the hash-only comparison was in fact an adaptive
membership oracle, and the closure replaced it with a three-layer overlap check
(`substrate/private_eval.py`, thresholds `OVERLAP_JACCARD_THRESHOLD = 0.80` and
`OVERLAP_CHAR_RATIO_THRESHOLD = 0.80`, the ratio derived from a measured
separation table rather than guessed), bound to the private seal and enforced
one-shot per clearance session.

**Verified behaviour against the real sealed private set, 2026-10-03:**

| synthetic batch (author-invented strings, no private content) | verdict |
| --- | --- |
| "What is the boiling point of lead at sea level?" | `PASS` |
| "Who wrote the Odyssey and when?" | `PASS` |
| exact duplicate of a private question | `REJECT` + the synthetic id to drop |
| whitespace/case/punctuation variant | `REJECT` |
| near duplicate | `REJECT` |
| second call in the same session | `REJECT` (one-shot) |
| call with no session id | `REJECT` (fails closed) |

**Superseded reading:** teams may request a clearance session and can receive a
`PASS`. The gate is not a permanent blocker on adaptation data.

**What still stands, and is unchanged:** the verdict is `PASS` or `REJECT` plus
the synthetic ids to remove. It never discloses the matched private id, text,
answer or evidence. Regime B teams must still exclude the public 21 documents
from adaptation data.

### Why this erratum exists at all

Round 1 lead D (adapter/PEFT) read §5, took it at face value, and reported the
leakage gate as a blocker that would stall its entire training plan. That is the
correct behaviour on a false premise, and the failure mode is worth naming: **a
preregistered document that no longer matches the code stops being a contract
and becomes a rumour.** §5 was frozen at a moment when the statement was true.
Freezing a true statement does not keep it true.

The durable fix is not "remember to update docs" — it is that the gate's real
behaviour is testable, so a reader can check §5 against
`tests/test_leakage_one_shot.py` instead of trusting it. Do that.

---

## E-1b. THE THRESHOLD REGISTER — one number, one place

Teams must not each pick their own "meaningful difference". There is exactly one
authoritative source, and it is `experiments/comparability/CONTRACT.md` §4,
mirrored in `docs/STATUS.md` accepted risk #2. Computed 2026-10-03, Wilson 95%
non-overlap, stronger system at a 90% operating point, independently cross-checked
by a two-proportion z-test at α=0.05 / 80% power:

| split | n | **minimum meaningful difference** |
| --- | --- | --- |
| dev | 59 | **13 items = 22.0 pp** |
| shadow_dev | 87 | **15 items = 17.2 pp** |
| dev + shadow_dev | 146 | **18 items = 12.3 pp** |
| private (sealed) | 116 | **16 items = 13.8 pp** |
| all worker-visible | 206 | **21 items = 10.2 pp** |

**Any gap below the applicable row is a NULL RESULT, never a win.**

Where each team's report stands as of this erratum:

| team | states a number? | value |
| --- | --- | --- |
| comparability | yes — owns it | 18 items / 12.3 pp on n=146 |
| hybrid-fusion | yes | 18 items / 12.3 pp on n=146 |
| adapter-peft | via STATUS risk 2 | ~22 / ~12 / ~10 pp |
| baselines | via STATUS risk 2 | ~22 / ~12 / ~10 pp |
| ettin-cascade | via STATUS risk 2 | ~22 / ~12 / ~10 pp |
| kalm-cascade | via STATUS risk 2 | ~22 / ~12 / ~10 pp |

Three teams defer rather than restate. That is the correct arrangement — a
restated number is a second number that can drift — but it means the register has
to be checked whenever a team writes a kill condition, or a team will quietly
gate on a threshold it invented.

### The generator-floor rule, which four teams originally got wrong

Four of the six reports carried a "≤ 5% oracle delta ⇒ generator has floored"
rule. 5% is *below what the probe can measure*, so that rule declares a floor on
the basis of a difference it cannot detect — it would have reported "floored"
when the truth was "underpowered", and stopped a tournament that was fine.

The comparison is **paired** (both arms answer the same items; only the packet
differs), so it needs McNemar's exact test, not an unpaired Wilson comparison.
Discordance needed for 80% power at n=146: **23%** at a 3:1 split favouring the
oracle packet, **16%** at 4:1, **9%** at 9:1.

The rule is three-way. Let `I` be the McNemar interval for the oracle's advantage:

- `I` excludes 0 → **no floor**, proceed.
- `I` includes 0 and its upper bound is below the MMD → **floor**. You have bounded
  the benefit of perfect evidence below anything this corpus could call real.
  Stop and report.
- `I` includes 0 and its upper bound exceeds the MMD → **INCONCLUSIVE /
  UNDERPOWERED**. This is the case the old rule silently collapsed into "floor".
  It is its own outcome and must be recorded as such. The remedy is more items or
  a more sensitive probe, not a verdict.

---

## E-2. §0 evidence-budget row — the enforcement is real, and here is the proof

The comparability lead cited `substrate/evidence.py` for the rule that empirical
runs must count tokens with the pinned tokenizer. Spot-checked by behaviour, not
by reading the source:

| check | result |
| --- | --- |
| `build_packet(exact=True, tokenizer=None)` | raises `ValueError` — whitespace estimates are refused for empirical runs |
| `build_packet(exact=False)` | packet self-labels `token_count_method="whitespace-estimate"` |
| tokenizer callable with empty `tokenizer_id` | raises `ValueError` |

So a team cannot report a whitespace token count as a measurement without the
packet carrying the `whitespace-estimate` label that gives it away.

**One clarification that matters for teams.** `GeneratorConfig.is_pinned()` only
rejects placeholder *strings* (`TBD`, `unspecified`, empty, `SYNTHETIC`). It does
**not** compare `prompt_hash` against the real `PROMPT_HASH` — a wrong-but-
non-placeholder prompt hash passes `is_pinned()`. The comparison against the
fixed prompt lives one layer up, in `validate_freeze` (`substrate/manifest.py:653`),
which also diffs the on-disk config field by field (`artifact_bytes`, `sampling`,
`artifact_sha256` against the actual file). Both layers are real; a team must
satisfy both, and running only `is_pinned()` locally is not sufficient evidence
that the generator is pinned.
