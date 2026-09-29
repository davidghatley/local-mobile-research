# Round 0 Experimental Contract (v0.3 — NOT FROZEN)

Status: **IN PROGRESS — NOT FROZEN.** No architecture implementations, held-out
runs, or tournament conclusions are authorized under this version.

Owner (substrate lead): `substrate/`, `eval/`, `tests/`, `pyproject.toml`, this file.
Reference audit, corpus pilot, generator runtime/adapter, and review-criteria
documents are owned by other workers and are not modified here.

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested spawning was used.

v0.3 repairs review `docs/substrate-implementation-review-v02.md` (disposition +
evidence in `docs/substrate-repair-v03.md`): generic artifact-inventory
content hashes (raw byte pins for questions / split-map / generator config,
manifest `ArtifactPin` inventory incl. external runtime binaries with
explicit roles) instead of endless field whitelisting; full group-map
validation (structure, uniqueness, corpus-node resolution, QA consistency);
unified threshold-policy validation (one implementation); `model_probability`
as an evaluable uncalibrated state; binary completion; citation audit that
permits unknown citations as recorded model failures. Prompt and fixed
generator settings unchanged from v0.2.

## 1. Common interface (all Round 1 experiments)

```python
class Retriever(Protocol):
  def prepare(self, corpus: list[CorpusNode]) -> None: ...
  def retrieve(self, question: Question) -> RetrievalOutcome: ...
```

```python
class Generator(Protocol):
  @property
  def generator_id(self) -> str: ...
  @property
  def prompt_hash(self) -> str: ...
  def generate(self, question: Question, packet: EvidencePacket) -> GeneratedAnswer: ...
```

Unchanged in v0.2 (generator adapter compatibility preserved; verified by
import + the generator worker's smoke script running against this substrate).
Canonical schemas in `substrate/types.py`. Round 1 is a retrieval/evidence
tournament, not a generator tournament.

## 2. Corpus and hierarchy

- Node kinds: `corpus > cluster > article > section > paragraph > sentence`.
- Primary hierarchy edge via `parent_id`; cross-links via `links` (DAG).
- `node_id` is CANONICAL: alias/redirect/title/entity routes resolve to it
  upstream of scoring. Genuinely different sufficient passages are separate ids.
- Format: canonical JSONL sorted by `node_id`; hash = SHA-256 of canonical form.
  Strict loader (`load_corpus_file`, `hash_corpus_file`) raises on malformed
  lines or hierarchy violations — fail closed.
- The **real pinned corpus artifact is still building** (pilot worker scope);
  `corpus/corpus.jsonl` absent ⇒ freeze fails (gap #1, external).

## 3. Splits and held-out custody (procedural, documented limitation)

- Deterministic seeded-hash assignment (`assign_split`): 70/15/15 over
  `sha256(seed + question_id)`. One master seed; per-component seeds derived
  via `derive_seed(master, component)` with the derivation logged in the manifest.
- Controlled train/dev/heldout QA MUST carry explicit provenance in question
  metadata — no implicit exemption for absent meta. Required:
  `meta.source_articles` (nonempty list of canonical article node ids, or
  pilot title identifiers with unambiguous resolution) AND `meta.group`
  (nonempty, resolvable). Freeze validates: every source resolves to a real
  corpus article node (unknown/ambiguous rejected); every source belongs to
  the claimed group (group-only claims rejected as insufficient); the group
  resolves via the split map (group-map mode) or deterministic derivation
  corroborated by corpus node metadata (seeded-hash mode); group split ==
  declared QA split; cross-split source sets rejected. Errors carry question
  ids/counts only, never content.
- Explicit `public_reference` category (`meta.category`): dev/reference use
  ONLY, never training or heldout. Requires `meta.source_benchmark` +
  `meta.source_revision` + `meta.original_question_id`. `source_articles`
  optional; absent/unresolvable sources mean retrieval ground truth is
  UNKNOWN (metrics None), never zero. Controlled/public separation preserved
  in the validation result interface (`results[qid].category/ground_truth`).
- The searchable corpus is SHARED across splits: resolution never filters by
  split; split equality constrains QA declarations, not corpus access.
- Sealed labels live in a separate file. `HeldoutCustodian.load_labels()`
  raises unless `allow_heldout=True` AND `HELDOUT_CUSTODIAN_MODE=benchmark`;
  optional opaque expected-hash check; every grant audit-logged.
- Opaque seal verification (`verify_seal_opaque`, `seal_hash`) hashes raw
  bytes WITHOUT parsing or printing labels — freeze uses this, never inspection.
- **Honest limitation (unchanged):** same OS user ⇒ no kernel boundary, no
  encryption theater. True isolation = orchestrator withholds the sealed file
  from dev workers.
- No real questions/labels exist yet (gaps #2, #3, external). Question files
  are schema-checked (`validate_questions_file`: unique ids, non-empty text,
  valid splits) and split consistency is verified against the manifest's
  `split_seed`/`split_method` without touching labels. Public bounty questions
  are development/reference only, never training examples.

## 4. Evidence packet, serialization, citations, tokens

- Canonical serializer `serialize_evidence(spans)` → `[node_id] text` lines;
  the prompt renderer and the exact tokenizer consume this exact string.
- Token units: empirical budgets are enforced on EXACT model tokens
  (`exact_evidence_tokens`, tokenizer callable + id required,
  `exact=True` required; estimates raise). `token_estimate` + method
  `"whitespace-estimate"` are INFRA-ONLY. Budget band 300–800, cap 1000, on
  the governing (exact) unit.
- Citations: packet `citations` = AVAILABLE (backing node ids);
  answer `citations` = EMITTED (claimed); `find_unknown_citations` diagnoses
  emitted-without-evidence; `parse_citations` extracts bracketed candidates.
  Unknown/hallucinated emitted citations are VALID recorded model failures:
  traces carry an optional `citation_audit` {available, emitted, unknown}
  that must be internally consistent (unknown == emitted − available) but is
  never rejected for containing unknowns. Failed answers preserved raw.

- Packet records `exact_evidence_tokens` and whole `prompt_tokens`
  (incl. template/system) separately; answer records completion tokens separately.

## 5. Fixed generator (v3 stable; adapter/config owned elsewhere)

- Fixed prompt v0.2 (`PROMPT_HASH = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63`);
  unchanged in v0.3. Any change requires re-freeze.
- `GeneratorConfig` full contract now incl. `chat_template_sha256`.
  Raw config BYTES pinned (`generator_config_sha256`): every raw field
  (license, download_url, verification, tokenizer detail, runtime_full,
  thread decisions, budgets...) is hash-pinned generically. The semantic
  compare covers the fields the substrate acts on (identity, revision,
  prompt, quantization, runtime, file, artifact bytes/hash, generator_id,
  tokenizer_id, chat template, context window, sampling).
- Runtime executables/libraries declared in the config (`runtime_binaries`:
  `llama-server` + libs with sha256) are hash-verified at their declared
  paths — including absolute out-of-tree paths under explicit
  `external-runtime-*` inventory roles — and must each be pinned in the
  manifest `ArtifactPin` inventory (verified live against v3 config: 9/9).
- NOTE: the on-disk `corpus/generator_config.json` (generator owner) currently
  lacks `tokenizer_id`, so `is_pinned()` reads False until their concurrent
  repair adds it — flagged handoff, not a substrate defect.
- `DeterministicStubGenerator` (`stub-infra-only-v0`) is infra-only; freeze
  and benchmark trace validation reject stub ids (opt-in flags for infra tests).

## 6. Evaluation and telemetry schemas

- Traditional `recall_at_k` (single required set, canonical ids), MRR, nDCG:
  PRESERVED unchanged.
- Separate `sufficient_set_completion`: BINARY 1.0 iff ANY sufficient set is
  fully present (0.0 otherwise, None without ground truth); best fractional
  coverage exposed separately as a diagnostic, never as completion.
- Survival vocabulary: uninterrupted `survival_curve` lineage (pruned stays
  pruned), direct per-stage `stage_coverage`, `conditional_retention` WITH
  numerator/denominator (None rate when denominator is 0 — undefined, not
  zero), `lost_and_recovered` spans. Compound claims use direct cumulative
  coverage; NEVER products of unconditional marginal recalls
  (`compound_survival` REMOVED).
- Calibration states: `none_ranking_only` (ranking/top-K only, never
  probability-thresholded), `model_probability` (native probabilistic output:
  ECE/Brier-evaluable, dev-thresholdable WITHOUT forced fitted calibration,
  but NOT certified calibrated), fitted methods (temperature/platt/isotonic/
  beta/other: certified claims REQUIRE `calibration_partition` provenance).
  Raw absolute/percentile thresholds legal with any score_kind. Trace
  threshold validation is the ONE shared `ThresholdPolicy.validate()`
  implementation (bare floats migrate fail-closed; policy/track score_kind
  mismatch rejected; ranking-only stages declare explicit policies).
- ECE/Brier accept ONLY finite [0, 1] probabilities with binary labels;
  logits/non-finite/non-binary raise. No sigmoid helper. `wilson_ci`
  qualifies rates with binomial intervals.
- Trace schema (26 required fields): scores + `score_kind` (raw logits legal
  iff labeled), per-stage latencies, model-loading/inference latencies,
  peak RSS, storage, adaptive decision, token method + count, prompt hash,
  generator id, citations + available citations, grader result. Unmeasured
  telemetry must be explicit null. Semantic validation rejects: negative
  latencies, mislabeled logits, prompt-hash drift, stubs, estimate budgets,
  unknown emitted citations.
- Measurement scope/units explicit: ms timings via `timed_phase` (callers
  separate load vs inference); `peak_rss_mb` = calling-process MB;
  subprocess (server) memory via `proc_rss_mb(pid)`, reported distinctly;
  categorized `storage_manifest` with roles; missing storage = explicit None.
- No LLM judge in substrate; judge model + prompt pinned separately at
  benchmark time.

## 7. Reproducibility and freeze validation (fail-closed, recomputing)

- `RunManifest`: master `seed`, `seed_derivation_log`, `phase`
  (`round0-substrate`; Round 0 records threshold-policy DECLARATIONS, never
  learned fits — those come from Round 1 teams), corpus hash, code hashes,
  full generator contract, `thresholds: dict[str, ThresholdPolicy]`,
  `sealed_labels_sha256`, `questions_sha256`, `split_seed`/`split_method`/
  `split_map_path`/`split_map_sha256`, `generator_config_sha256`,
  generic `ArtifactPin` `inventory` (incl. external runtime roles).
- `validate_freeze` RECOMPUTES every hash above plus per-file code hashes and
  runtime binary bytes; validates group-map structure/disjointness/resolution
  and QA consistency; checks citation-audit rules only in traces (not freeze).
  Malformed artifacts yield structured gaps, never crashes; gap text carries
  ids/counts/hashes only — never question/answer/label/article text.
- Tests: stdlib `unittest` only, zero third-party deps.
  `python3 -m unittest discover -s tests` → **147 tests, all passing**.

## 8. API changes (breaking only where compat would hide invalid data)

v0.1 → v0.2: REMOVED `compound_survival`; thresholds → `ThresholdPolicy`;
full generator contract + strict pin; additive token/score/hop/telemetry
fields; strict `hash_paths`; semantic trace validation; calibrated-only ECE/Brier.

v0.2 → v0.3:
| Change | Compat |
| --- | --- |
| `sufficient_set_completion`: binary `completion` + `best_fractional_coverage` (was: fractional `completion`) | Breaking, documented; recall untouched |
| Trace unknowns permitted + optional `citation_audit` consistency (was: rejection) | Intended per finding A; `allow_unknown_citations` kept as no-op |
| `ThresholdPolicy` gains `calibration_partition`; `model_probability` state; fitted claims need provenance | Additive; bare-sigmoid probability policies still rejected |
| `GeneratorConfig` gains `chat_template_sha256` (pinned) | Additive; v3 disk config stays pinned |
| `RunManifest` gains `phase`, `questions_sha256`, `split_map_sha256`, `generator_config_sha256`, `inventory` | Additive with fail-closed defaults |
| New `ArtifactPin`, `validate_group_map`, `validate_qa_group_consistency`, `norm_title` | Additive |

v0.1 → v0.2 detail (retained for provenance):
| Change | Compat |
| --- | --- |
| REMOVED `compound_survival` (product of marginals is invalid) | Breaking, documented |
| `thresholds: dict[str, float]` → `dict[str, ThresholdPolicy]` (`from_dict` migrates floats to fail-closed "unspecified") | Migrating |
| `GeneratorConfig` gains file/artifact/tokenizer/sampling fields; `is_pinned()` strict | `from_dict` tolerates superset; old minimal configs now correctly unpinned |
| `EvidencePacket`/`StageRecord`/`RetrievalOutcome`/`GeneratedAnswer` gain optional fields (token methods, exact counts, score kinds, hop records, phase latencies) | Additive, backward readable |
| `Candidate` gains `score_kind` (default calibrated) | Additive |
| `hash_paths` raises on missing paths (was: silent skip) | Fail-closed by design |
| `validate_trace` requires 26 fields + semantics (flags for infra opt-ins) | Old traces fail closed, intended |
| `brier_score`/`expected_calibration_error` validate domain | Invalid inputs now raise |
| `build_packet(..., tokenizer, tokenizer_id, exact)` | Additive kwargs; old calls = infra estimate path |

## 9. Readiness gaps (freeze blockers; owners in parentheses)

1. No pinned corpus artifact (`corpus/corpus.jsonl` absent; pilot fetch ongoing, do not poll).
2. No pinned questions (`corpus/questions.json` absent; later step, no QA generation in substrate scope).
3. No sealed held-out labels (orchestrator custody; dev workers must not inspect or parse).
4. Generator v3 stable on disk and substrate-pinned (verified live: `is_pinned()` true, 9/9 runtime binaries resolve); no substrate-side generator work remains.
5. Independent re-review of THESE v0.3 repairs (orchestrator decision).
6. Custodian separation remains procedural (same-user limitation, §3).

## 10. Concrete next steps for freeze

1. Pilot corpus lands → `corpus/corpus.jsonl` (+ `split_map.json` per pilot builder).
2. Questions + sealed labels pinned by later steps (labels withheld from dev).
3. Run `python3 -m unittest discover -s tests` (must pass) + `validate_freeze` on a real manifest (must pass).
4. Independent reviewer PASS on contract v0.3 + repairs.
5. Orchestrator records freeze (commit, hashes, seeds); only then Round 1.

## 11. What this contract forbids

- Architecture implementations, held-out runs, or conclusions before freeze.
- Training on public bounty questions; inspecting held-out labels in dev.
- Presenting synthetic fixtures, stub output, or estimates as research results.
- Probability thresholds on ranking-only or unprovenanced scores; ECE/Brier on logits; fitted-calibration claims without partition provenance.
- Compound-survival products; Android claims from desktop measurements.
- Post-freeze changes to corpus/generator/prompt/thresholds without re-freeze.
