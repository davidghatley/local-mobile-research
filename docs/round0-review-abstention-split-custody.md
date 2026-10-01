# Round 0 Repair — Phase 3 Independent Adversarial Review: Abstention / Split / Custody / Memory Telemetry

Reviewer: independent (did not write the repaired code).
Repo HEAD: `230e7d5`. Scope: BLOCKER 8 (abstention), BLOCKER 5 (split policy),
BLOCKER 7 (custody/leakage), BLOCKER 11 (memory telemetry).
All probes below were EXECUTED (python3), not read-only.

Verdict: **PASS** — no load-bearing defect found. Two non-blocking
observations are recorded in Sections 7 and 8.

## 1. Abstention bypass — PASS

- `EvidenceDecision(decision="sufficient", generation_action="abstain")` raises
  `ValueError` (`substrate/types.py:364-369`, insufficient-iff-abstain gate).
- `EvidenceDecision(decision="insufficient", generation_action="generate")`
  raises identically.
- `EvidenceDecision.from_dict` with either mismatch also raises, because it
  routes through the constructor (`substrate/types.py:404-411`), so
  `__post_init__` is not skippable via the deserialization path.
- `run_question` with an empty packet and a counting mock generator that
  raises if called: generator calls == 0, response is None
  (`substrate/evidence.py:222-223` returns before touching the generator).
- Generate path sanity: a nonempty packet invokes the generator exactly once
  and returns a non-None response.
- Residual (accepted, not a defect): a caller-supplied `decide` callable is
  trusted to return an `EvidenceDecision`; duck-typed fakes are outside the
  threat model, and the constructor plus the wire validator close the real
  paths.

## 2. Empty-packet floor — PASS

- `decide_default` on zero-span `truncated=False` packet returns
  insufficient/abstain with reason `"zero-spans"`.
- Zero-span `truncated=True` (first-span overflow via `build_packet` with a
  tiny cap: 0 spans kept, `truncated=True`) returns insufficient/abstain with
  reason `"over-budget-empty"` — distinct from `"zero-spans"`, so a packing
  failure is never recorded as a clean retrieval decision
  (`substrate/evidence.py:178-195`).
- Nonempty packet returns sufficient/generate with reason `"nonempty-packet"`
  and score None / kind `"unspecified"` / policy None: the floor is minimal
  and forces no sufficiency judgment beyond span presence.

## 3. Unknown vs zero — PASS

- `abstention_summary([])`: every rate is None (never 0.0).
- All-unlabeled input: every rate None, `n_unlabeled` counted, no rate invented.
- Single-record inputs behave per denominator: e.g. one answerable+abstain
  yields `false_abstention` rate 1.0 while `correct_abstention` and
  `unsupported_generation` stay None (denominator 0), not 0.0.
- `abstention_outcome(answerable=None, ...)` returns None for both abstained
  values (`eval/metrics.py:150-151`).

## 4. Split leakage (BLOCKER 5) — PASS

Executed against `substrate/splits.py:validate_question_provenance`:

| Chain | Result |
|---|---|
| train grpA -> train grpB (multi-group, one split) | ALLOWED |
| train -> heldout | REJECT (cross-split chain) |
| dev -> heldout | REJECT (cross-split chain) |
| train -> dev | REJECT (cross-split chain) |
| declared split != evidence split | REJECT |
| declared group split != declared split | REJECT |
| empty `source_articles` | REJECT (nonempty required) |
| `evidence_groups` missing declared group | REJECT |
| `evidence_groups` outside declared split | REJECT |

Relaxation did NOT weaken leakage prevention:

- `substrate/splits.py:528-552` enforces the same-split rule (splits
  compared, never groups); group equality is never required.
- `data_tools/verify.py:189-209` re-enforces split equality per evidence
  span independently, and additionally requires every evidence article to be
  declared in `source_articles` (executed: omitted declaration rejected;
  train->heldout span rejected; train->train multi-group allowed).
- Retriever projection: `to_retriever_input` returns exactly
  `{question_id, text}` and raises `ValueError` on any extra key
  (`data_tools/qa_schema.py:379-390`), so group/`evidence_groups`/
  `source_articles` cannot reach retrieval.

## 5. Semantic-automation forbidden — PASS

- `validate_semantic_audit` (`data_tools/qa_schema.py:98-139`) checks
  structure/vocabulary only: required-field presence, `set_index` int,
  nonempty reviewer/corpus fields, closed `decision_token` vocabulary
  (executed: `"looks-good"` rejected), yes/no vote, `reviewer != author`
  (executed: self-review rejected), and missing `corpus_revision` rejected.
  Absent block returns no errors (pending, never auto-approved).
- Grep over `substrate/`, `data_tools/`: no substring/token-overlap/Jaccard
  heuristic decides sufficiency, minimality, or answerability. The only
  overlap machinery is `mine_hard_negatives` (candidate proposal, still
  requires `reviewed=True` human confirmation) and the custodian-side
  n-gram leakage detector — neither writes any audit decision.
- No code path populates an `approve` decision or a `semantic_audit` record;
  approvals are human-authored data validated downstream.

## 6. Custody audit — PASS

Executed against `HeldoutCustodian` (`substrate/splits.py:129-227`):

- `load_labels` fails closed on empty, whitespace-only, and missing
  `accessor`/`role`/`purpose`/`granted_by` (each raises `HeldoutAccessDenied`),
  on `allow_heldout=False`, and on missing `HELDOUT_CUSTODIAN_MODE=benchmark`.
- Each granted access appends one JSONL record carrying the seal hash at
  access time (verified equal to `seal_hash()`); audit file is opened
  append-only (`"a"`); no delete/overwrite path exists on the class.
- The audit record carries `question_ids` and the seal hash but never label
  content — it cannot be used to read sealed answers.
- Note (non-blocking): the custodian-internal audit log necessarily lists
  held-out question ids. This is a local custody artifact, not a published
  report; it must stay out of dev-visible outputs (see Section 7 boundary,
  which holds).

## 7. Leakage-check disclosure boundary — PASS (with observation)

Executed `run_leakage_check` on synthetic fixtures with known held-out ids,
text, and answers:

- Report contains NO held-out question id, NO held-out text, NO held-out
  answer, and no per-item match pointer (`compute_ngram_similarities`
  keeps `matched_heldout_qid` internal-only; only synthetic ids and the
  aggregate histogram/max/mean are emitted).
- Threshold is labeled dev-calibrated with recorded operating
  characteristics (`dev_calibrated_threshold`,
  `dev_operating_characteristics`), not an asserted constant; the no-dev
  fallback (0.7) is explicitly labeled "conservative default ... Calibrate
  on dev for production use."
- With no local embedding model, `paths_available` reports
  `embedding_cosine: false` and the notes state "n-gram path STANDS ALONE."
- Observation (non-blocking): with a degenerate tiny dev sample (n=2, all
  sims 0.0) calibration yields threshold 0.0 and `>=` flags everything
  (status REJECT on clean data). This is a small-sample artifact of the
  probe fixture, not a production defect, but calibrators should guard
  against non-positive thresholds or document a minimum dev sample size.

## 8. Memory telemetry — PASS

- `proc_rss_mb` reads `VmRSS`; `proc_peak_rss_mb` reads `VmHWM`
  (`substrate/telemetry.py:82-125`); distinctly named, never conflated, with
  distinct sources in `proc_memory` (`rss_source` vs `peak_source`).
- Live Linux process: point 20.30 MB, peak 20.36 MB, peak >= point.
- Old `ru_maxrss` magnitude heuristic is gone: no `1e9` literal; explicit
  `sys.platform` dispatch in `_ru_maxrss_divisor` (linux KiB / darwin bytes /
  unknown None). Monkeypatched `sys.platform="win32"` yields
  `('unknown-platform', None)` and `peak_rss_mb() is None` (fail closed, no
  guessing); bogus pid returns None on both readers.

## Verdict

**PASS.** All eight attack lines hold under executed probes. No repair
required. Sections 7 (minimum dev-sample guard for calibration) and 6
(audit-log id hygiene) are advisories for the freeze checklist, not blockers.
