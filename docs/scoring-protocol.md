# Answer Scoring Protocol — PREREGISTERED

**Status: PREREGISTERED / FROZEN (policy freeze, see "FROZEN AT" below).**
This document defines the secondary generated-answer metrics. It was written
and frozen BEFORE any architecture produced private outputs, and MUST NEVER
be modified after private results are visible. Any later change is a protocol
violation and invalidates comparability.

**FROZEN AT:** commit `88aa1776eda01b87d014d235bbc84004d8dc7b78`
(Round 0 closure run; this doc + `eval/answer_scoring.py` are frozen at this
commit — a later diff to either file after private outputs exist is
detectable via `git log` / `git diff` and must be treated as a freeze break).

## 0. Metric hierarchy (unchanged)

PRIMARY metrics remain objective retrieval/evidence metrics — the first
tournament's primary question is which architecture produces the best
evidence packet:

- required-evidence / support completion
- evidence survival by stage
- Stage-0 recall
- candidate reduction
- final evidence recall
- evidence token cost
- context precision
- abstention / sufficiency accuracy
- latency, RAM, storage

SECONDARY generated-answer metrics are defined below. They never override a
primary metric and never repair a failed evidence packet.

## 1. Deterministic normalization + exact/accepted-answer matching

Applies to **answerable** questions (factoid, comparison with a short gold
form, single-hop with an extractable gold string).

### 1.1 `normalize_answer` (exact, implemented in `eval/answer_scoring.py`)

1. Unicode-normalize with **NFKC**.
2. Unicode **casefold**.
3. Replace every character that is not a word character or whitespace with a
   space (strips punctuation, symbols, hyphens, slashes).
4. Collapse all whitespace runs to one space; strip ends.
5. Remove English articles **`a` / `an` / `the`** as whole tokens wherever
   they occur (subsumes stripping a leading "the").
6. Re-collapse whitespace; strip ends.

Reference: `eval/answer_scoring.py:normalize_answer`. Non-string input
raises `TypeError` (fail closed).

### 1.2 Matching

- `exact_match(pred, gold)`: normalized equality; empty-after-normalization
  never matches (emptiness is scored as abstention/empty-generation, not as
  a wrong answer).
- `match_any_variant(pred, answer_text, accepted_variants)`: gold first,
  then caller-ordered accepted variants. Returns match flag + matched
  variant + normalized prediction for audit.
- Accepted variants come ONLY from the private label record
  (`labels.answer_text` plus any privately recorded variant list); workers
  and scorers never invent variants.

## 2. FREE judge for non-exact answers (comparison / multi-hop / free-form)

Exact matching is unsuitable where the answer is a comparison verdict, a
composed multi-hop statement, or free-form text with many surface forms.
Those cases use ONE fixed preregistered judge. The judge model is IDENTICAL
across all architectures.

- **Judge model id:** `google/flan-t5-large`
- **Temperature:** `0.0` (greedy decoding; `do_sample=false`)
- **Decoding (fixed):** greedy, `max_new_tokens=64`, `num_beams=1`,
  `early_stopping=true`. No sampling, no top-k/top-p, no system-prompt
  variation. Tokenizer: the model's own tokenizer, input truncated to 2048
  tokens (question + gold + prediction + evidence citation block).
- **Prompt (verbatim):**

```text
You are an exact answer judge. Compare PREDICTION to GOLD for QUESTION.
GOLD is authoritative. Mark CORRECT only if PREDICTION states the same
fact/claim as GOLD with no contradiction and no unsupported extra claim
that changes the answer. Minor rewording is CORRECT. A different entity,
number, date, negation flip, or hedged non-answer is INCORRECT.
Respond with exactly one JSON object, no other text:
{"verdict": "CORRECT" | "INCORRECT", "reason": "<=20 words>"}
QUESTION: {question}
GOLD: {gold}
PREDICTION: {prediction}
```

- **Decision schema (verbatim JSON schema):**

```json
{
  "type": "object",
  "required": ["verdict", "reason"],
  "properties": {
    "verdict": {"type": "string", "enum": ["CORRECT", "INCORRECT"]},
    "reason": {"type": "string", "maxLength": 200}
  },
  "additionalProperties": false
}
```

- Non-conforming judge output (unparseable JSON, wrong enum, extra keys
  with `additionalProperties` violated) is scored as **judge-absent for
  that item**, not retried with a different prompt or model.
- **Unavailability rule:** if `google/flan-t5-large` is unavailable in the
  scoring environment, the deterministic metric (§1) is reported as primary
  and judge metrics are simply ABSENT (empty column with an explicit
  "judge unavailable" note). NEVER silently substitute another model,
  another temperature, or an edited prompt.

## 3. UNANSWERABLE questions

Primary success is the correct **abstention / insufficient-evidence
decision** (see `abstention_outcome` in `eval/answer_scoring.py`, mirroring
`eval/metrics.py` semantics). A fabricated answer is FAILURE
(`unsupported_generation`). Claiming to answer while emitting no substantive
text is also failure (`empty_generation` — kept distinct so telemetry
distinguishes clean abstentions from empty generations).

## 4. AMBIGUOUS questions

Do NOT require a single nonexistent `answer_text`. Success = recognizing
ambiguity AND grounding the valid readings in evidence:

- The private harness holds the privately recorded `readings`; workers never
  see them. The harness passes only counts/flags to
  `score_ambiguous_response` (`claimed_ambiguity`, `n_gold_readings`,
  `n_grounded_readings`).
- Success outcome `grounded_ambiguity` requires an explicit ambiguity claim
  PLUS at least `min(n_gold_readings, 2)` readings each backed by cited
  evidence (default threshold 2).
- `single_answer_only` (one reading asserted, ambiguity unmentioned) and
  `ungrounded_ambiguity` (ambiguity claimed, readings uncited) are failures.

## 5. Hard rules

1. No scoring-rule modification after private outputs exist — including
   normalization, variant lists, judge model/prompt/decoding/schema, and
   thresholds. Fix forward only in a NEW tournament round with a new freeze
   commit.
2. The scorer reads NO private files; it takes already-extracted records
   from the private harness (which is outside this repo).
3. Deterministic parts are stdlib-only and pure (`eval/answer_scoring.py`);
   same input twice yields identical output (covered by test).
4. Judge outputs and normalizations are preserved in raw traces with exact
   provenance (model id, prompt hash, decoding params per item).
