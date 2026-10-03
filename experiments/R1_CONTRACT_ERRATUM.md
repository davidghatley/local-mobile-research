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
