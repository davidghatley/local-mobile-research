# Evidence-Token Packing + Prompt Repair (narrow scope)

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested agents. Scope: `substrate/evidence.py`,
prompt block of `substrate/generator.py`, `substrate/__init__.py` export line,
`tests/test_evidence_packing.py` (new), one updated test in
`tests/test_semantics_adversarial.py`, this report. Manifest/trace/types left
untouched (independent re-review underway). No generator_runtime or
corpus/generator_config.json modifications.

## 1. Packing repair (`substrate/evidence.py`)

Orchestrator observation (confirmed on v0.2 code): `build_packet` summed
per-span counts (`count(serialize_evidence([span]))`) and the `and kept`
guard let an oversize first span through. Fixed policy now implemented:

- Every step counts the FULL serialization `serialize_evidence(kept + [span])`
  (baseline `serialize_evidence([])` first): separators and non-additive
  tokenization are counted as the model sees them.
- Strict cap, never exceeded, including the first span. Deterministic
  ranked-prefix: stop before first overflow, `truncated=True`; first-span
  overflow yields an EMPTY packet with `truncated=True`.
- No partial-span truncation (no exact offsets exist); empty/short packets
  are valid abstention outcomes. `truncated=True` records a PACKING outcome,
  distinct from upstream retrieval survival (stage traces / survival metrics);
  `truncated=False` + zero spans means upstream supplied nothing.
- `cap` validated: positive int, bool rejected. Every tokenizer return
  validated: nonnegative int, bool/float/nan/negative rejected (fail closed).
- `HARD_EVIDENCE_TOKEN_CAP = 1000` preserved as the PILOT PREREGISTERED
  protocol choice, not a universal requirement (module docstring).

## 2. Prompt fix (`substrate/generator.py`, prompt block only)

v0.1 wording "cite its evidence id in [node_id] form" produced a literal
`[node_id]` citation in synthetic smoke output. Replaced with:

> Cite the exact bracketed identifier printed before the supporting evidence.
> For example, evidence labeled [source-7] must be cited as [source-7].
> Do not write placeholder identifiers.

One common prompt, no benchmark tuning. Exact new identity:

- `PROMPT_HASH = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63`
- No `[node_id]` literal remains in the prompt (tested).

Generator worker: please sync `corpus/generator_config.json` prompt_hash to
the above after this work (not modified here).

## 3. Shared citation parser (new API)

`substrate.evidence.parse_citations(text) -> list[str]` (also exported from
`substrate`): extracts `[...]` contents in first-appearance order, deduped,
whitespace-stripped, empties skipped. Brackets are NOT necessarily sources:
results must go through `find_unknown_citations` against packet available
citations; unmatched ids are UNKNOWN, never auto-credited (tested).

## 4. Tests

`python3 -m unittest discover -s tests` → **113 tests, all passing**
(88 before; +25 new in `tests/test_evidence_packing.py`). New coverage:
full-serialization counting incl. baseline empty-string call, separator
tokens, subadditive tokenizer honored exactly, strict cap on exact counts,
first-span overflow → empty + truncated (exact and estimate paths),
empty input → not truncated, zero/negative/bool/float caps rejected,
bool/float/nan/negative tokenizer returns rejected, zero accepted, prompt
hash/pins/render, `parse_citations` extraction/dedup/unknown handling.
One pre-existing test (`test_exact_budget_enforced_on_model_tokens`) updated
from constant-return to scaled tokenizer to match full-serialization counting.
Two new-test fixture errors during development (baseline-call indexing,
degenerate constant tokenizer) fixed in test code; implementation unchanged.
All fixtures SYNTHETIC.
