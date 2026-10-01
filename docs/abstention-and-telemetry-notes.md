# Abstention and Telemetry Trace Contract (Lane C → run_format worker)

This note specifies EXACTLY which trace fields the `eval/run_format.py`
worker must add. Lane C owns the semantics; the run_format worker owns the
wire format. Key names below are normative — implement them verbatim so no
guessing is needed.

## 1. Required per-question trace fields (abstention)

Every per-question trace record MUST carry these keys, sourced from
`substrate.evidence.run_question`, which returns
`(outcome, decision, response)`:

| JSON key | Type | Source | Notes |
|---|---|---|---|
| `evidence_decision` | string | `decision.decision` | `"sufficient"` or `"insufficient"` only |
| `generation_action` | string | `decision.generation_action` | `"generate"` or `"abstain"` only |
| `generator_invoked` | bool | `response is not None` | MUST be false on abstain |
| `generator_response` | object or null | `response.to_dict()` or null | null iff abstain; non-null iff invoked |
| `sufficiency_score` | number or null | `decision.sufficiency_score` | null when no score computed (safe floor) |
| `sufficiency_score_kind` | string | `decision.sufficiency_score_kind` | e.g. `"unspecified"` from the floor; a real score_kind when scored |
| `sufficiency_policy` | object or null | `decision.sufficiency_policy.to_dict()` or null | null from the safe floor; architectures attach their policy |
| `decision_reason` | string | `decision.reason` | short code: `"zero-spans"`, `"over-budget-empty"`, `"nonempty-packet"`, or an architecture-supplied code |

Legacy traces that lack a decision MUST fail closed (reject or mark
invalid) — NEVER silently default `evidence_decision` to `"sufficient"`.

## 2. Required telemetry fields

| JSON key | Type | Source | Notes |
|---|---|---|---|
| `agent_rss_mb` | number or null | `telemetry.proc_rss_mb(pid)` | point VmRSS sample; null = not measured |
| `agent_peak_rss_mb` | number or null | `telemetry.proc_peak_rss_mb(pid)` | VmHWM high-water; DISTINCT from point RSS |
| `storage_complete` | bool | `telemetry.storage_manifest(...)["complete"]` | false when any required artifact missing |
| `storage_bytes` | integer or null | `...["total_bytes"]` | integer ONLY when `storage_complete` is true, else null |

`agent_rss_mb` and `agent_peak_rss_mb` must be recorded as SEPARATE keys
with their distinct sources (`/proc/<pid>/status:VmRSS` vs `:VmHWM`).
Never fold them into one number.

## 3. Cross-field validation rules (validator MUST reject on violation)

1. `generation_action == "abstain"` AND `generator_invoked == true` → REJECT.
   An abstained question must never touch the generator.
2. `generator_invoked == false` AND `generator_response != null` → REJECT.
   No response may exist without invocation.
3. `generator_invoked == true` AND `generator_response == null` → REJECT.
   An invocation must produce a recorded response.
4. `evidence_decision == "insufficient"` AND `generation_action != "abstain"`
   → REJECT (and the symmetric mismatch). The substrate enforces this in
   `EvidenceDecision.__post_init__`; the wire validator re-checks it.
5. `storage_complete == false` AND `storage_bytes` is an integer → REJECT.
   A missing artifact must yield `storage_bytes: null` (fail-closed total).
6. `storage_complete == true` AND `storage_bytes == null` → REJECT.
   A complete manifest must carry its integer total.

## 4. Metrics wiring (eval/metrics.py, Lane C owned)

- `abstention_outcome(*, answerable: bool | None, abstained: bool)` maps one
  traced question to `"correct_abstention"` (unanswerable + abstain:
  success), `"false_abstention"` (answerable + abstain: failure),
  `"unsupported_generation"` (unanswerable + generated: failure),
  `"answered_answerable"` (answerable + generated), or None when
  `answerable` is None (unlabeled — no outcome invented).
- `abstention_summary(records)` aggregates with `{n, den, rate}` per
  outcome plus `sufficiency_accuracy`; `rate` is None (NOT 0.0) when the
  denominator is 0 or labels are absent.
- `abstained` for metrics = `generator_invoked == false` on a traced
  question (the gate is the only path to the generator, so non-invocation
  IS abstention).
