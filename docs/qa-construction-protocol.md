# QA Construction Protocol (DRAFT — no real questions exist yet)

Status: **PROTOCOL + TOOLING ONLY. NOT EXECUTED.** No controlled
train/dev questions, no held-out questions, no labels, and no sealed
files have been created under this protocol. `corpus/questions.json` and
any `*heldout*.sealed.json` remain absent. Nothing here authorizes
architecture work or a freeze claim.

Owner: this worker owns `data_tools/`, this document, and
`docs/qa-tooling-repair.md` only. It does not modify `corpus/`,
`substrate/`, `eval/`, `tests/`, `generator_runtime/`, or other docs.
Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested spawning. No online LLM APIs, no paid
endpoints, no calls to the orchestrator model at any step.

Round 0 repair amendment (Lane D, same model): `substrate/splits.py`
provenance gate, `meta.evidence_groups`, `evidence.hop_glosses`, and
`provenance.semantic_audit` are additionally owned here per
`docs/round0-repair-plan.md`. `substrate/types.py`, `substrate/manifest.py`,
`substrate/evidence.py`, `substrate/telemetry.py`, `substrate/corpus.py`,
`eval/`, `tests/`, `corpus/`, and `generator_runtime/` remain untouched.

## 0. Preconditions (orchestrator gate — all must hold before §4)

1. Corpus validated: `corpus/corpus.jsonl` hierarchy-clean, byte-pinned,
   hash recorded in the freeze manifest (corpus owner scope).
2. `corpus/split_map.json` frozen: every confusable/near-duplicate set
   intact in one split; map passes `substrate.splits.validate_group_map`.
3. Fixed generator + prompt pinned (generator owner scope).
4. This protocol + `data_tools/` reviewed and approved.

Note: the derivation substrate is corpus revision `pilot-297-r1`
(297 articles; `corpus/corpus.jsonl` 43,876,251 bytes; canonical semantic
hash `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1`
vs file-bytes SHA-256 `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64`
— distinct by construction, see `docs/qa-gate-decisions.md` §1);
splits train 205 / dev 44 / heldout 48 (seed `pilot-v1`, 218 groups);
`corpus/build_manifest.json` is ground truth for bytes. Revision 1
(`pilot-247-v0`, 247 articles) is archived and superseded, NOT the
derivation substrate. Derivation starts only after the revision passes
independent quality review plus the §0 gate.

## 1. Split discipline (binding)

- **Group before derivation.** A draft's evidence must sit entirely in
  ONE data split, and may span multiple predeclared split-map groups of
  that split. The scaffold (`data_tools/scaffold.py`) draws candidate
  units from one group and records group + split; cross-group evidence
  is author-assembled and declared via `meta.evidence_groups` (sorted
  distinct list of every evidence article's group, including the primary
  `meta.group`). See `docs/qa-semantic-audit-protocol.md`.
- **One shared corpus.** All splits search the same global corpus files.
  Split equality constrains QA declarations, never corpus access.
- **No mixed-split chains.** Every source article of a draft must sit in the
  draft's declared split. Substrate `validate_question_provenance` enforces
  this; `data_tools/verify.py` additionally requires every evidence span's
  article to resolve to a group whose SPLIT equals the declared split.
  Group equality is never required: same-split cross-group chains are
  allowed (train->train ALLOW; train->heldout, dev->heldout, train->dev
  REJECT). Leakage prevention is not weakened.
- **Same-split multi-hop.** Every sufficient-set span of a multi-hop draft
  must resolve to the draft's declared split, and the multi-hop label must
  survive the single-atom answerability test in
  `docs/qa-semantic-audit-protocol.md` (no single atom determines the
  answer alone). Cross-split multi-hop is rejected. Audited multi-hop
  drafts additionally carry one `hop_gloss` per reference chain stating
  the distinct inferential relation each hop contributes.
- **Public bounty questions are dev/reference only.** Imported via
  `data_tools/import_public.py` from byte-pinned input (full 40-hex commit
  SHA as `source_revision`, 64-hex SHA-256 of the exact import-file bytes
  as `source_file_sha256`, both format-validated; byte mismatches refused),
  forced `split=dev`, `category=public_reference`. Never training, never
  held-out, never with controlled evidence spans or imported answers.

## 2. Ground-truth requirements per question

Each draft (`data_tools/qa_schema.py`) carries:

1. **Exact spans (code-point equality).** Every sufficient-set entry is
   `{node_id, text}` plus optional `{char_start, char_end}`. Verification
   re-reads the corpus node and requires Python-str equality: offset slices
   count Unicode code points, NOT bytes/UTF-8 length, NOT grapheme
   clusters. Equality proves the draft quotes the corpus exactly — it does
   NOT prove the span answers the question, entails the answer, or is
   sufficient. Those judgments belong to the named human author and the
   independent verifier, never to the code.
2. **Sufficient alternative sets.** `sufficient_sets` is a LIST of sets: any
   one fully present set suffices. Genuinely different sufficient passages
   are separate node ids — never collapsed into one "article-level" claim.
3. **Complete declared provenance.** `meta.source_articles` (nonempty
   canonical ids or unambiguously resolving titles) AND `meta.group`
   (nonempty, in-map). Group-only or source-only drafts are rejected, and
   same-group membership alone is insufficient: EVERY evidence span's
   article must appear in the declared `source_articles` (machine-checked).
   Drafts under semantic audit additionally declare `meta.evidence_groups`
   (sorted distinct list covering every evidence article's group); the
   split gate compares SPLITS, never groups — see §1 and
   `docs/qa-semantic-audit-protocol.md`.
4. **Reference hop chain.** Multi-hop drafts record ≥ 1 ordered
   `reference_hop_chains[]`. Systems retrieving a sufficient set by a
   shorter path get evidence credit without the iterative-hop flag (per
   review criteria §1.2).
5. **Source-grounded, not tautological.** The question must be answerable
   only by reading the spans; the answer string must not appear verbatim in
   the question (machine-checked). Template-only derivation is rejected at
   review: each draft needs a reviewer judgment that a retriever cannot
   match it by surface overlap alone. At least one hard negative must come
   from the same group.
6. **Hard negatives (candidates vs reviewed).** ≥ 1 entry of
   `{node_id, negative_type, reviewed}` covering, per question set, all six
   strata: `sibling_paragraph | neighbor_sentence | linked_article |
   token_overlap_nearmiss | entity_confusion | same_group_distractor`.
   `token_overlap_nearmiss` is a stdlib token-overlap lexical proxy — it is
   NOT BM25 and is never labeled as such. Miner output is CANDIDATE
   material (`reviewed=False`); a negative is evidence-grade only with
   `reviewed=True` set by a human who confirmed it does not answer the
   question. Overlap with evidence is checked by identity AND
   ancestor/descendant containment (a negative containing, contained in, or
   identical to an evidence span is rejected).
7. **Unanswerable vs ambiguous (distinct, consistency-enforced).**
   `question_type` and `labels.answerability` must agree: unanswerable ⟺
   unanswerable, ambiguous ⟺ ambiguous — mismatches are rejected.
   - *Unanswerable*: `sufficient_sets=[]` + `evidence.absent_reason`
     (which corpus fact is missing) + `answerability=unanswerable`.
     The correct behavior is abstention, not a guess.
   - *Ambiguous*: ≥ 2 `labels.readings`, each with nonempty
     `reading_text`, nonempty `answer`, and its OWN `sufficient_set`
     index (distinct, in range; all referenced sets pass the same exact
     span and provenance checks). The correct behavior is clarification or
     enumerated readings, not a single guess.

## 3. Roles, identity, and content-bound approval

- **Authors** (experiment builders): write drafts from scaffolds, self-check
  with `validate_qa.py` on train/dev. Recorded as `provenance.author` +
  `provenance.author_model` (exact worker/model string).
- **Independent verifier**: a DIFFERENT person/model from the author
  (`provenance.verifier` + `provenance.verifier_model`), who re-runs
  verification, spot-reads the corpus nodes behind ≥ 20% of sufficient
  sets, and records `decision=approve` + nonempty `rationale` + the
  `content_hash` of the exact draft reviewed. Tooling never fabricates
  approvals: the actual reviewer determines sufficiency, ambiguity,
  absence, and negative correctness. Code passing is NOT correctness —
  tests prove only that the gates reject the listed defect classes.
- **Content binding.** `provenance.content_hash` must equal
  `draft_content_hash` (SHA-256 over the draft's semantic contents,
  excluding scaffolding and the approval block itself). Any content change
  after approval invalidates it ("stale approval" failure). Missing,
  non-approve, self-reviewed (`verifier == author`), rationale-free, or
  stale approvals fail verification and block sealing.
- **Held-out custodian** (separate from builders): the ONLY role that runs
  `--allow-heldout` with `HELDOUT_CUSTODIAN_MODE=benchmark`, holds
  `heldout_labels.sealed.json`, and records the opaque SHA-256. Limitation,
  stated honestly: all workers share one OS user, so there is no kernel
  boundary — custody is procedural (separate file, access gate, opaque
  hash, audit log), not filesystem enforcement. True isolation = the
  orchestrator withholds the sealed file from development workers.
- **Developers never see held-out labels or held-out questions.**
  `scaffold.py` and `validate_qa.py` refuse held-out drafts without the
  custodian flag + env var; `HeldoutCustodian.load_labels()` (substrate)
  raises without both. Held-out question/provenance files are never placed
  in dev-visible paths. Manifests and error strings carry ids/counts/hashes
  only.

## 4. Retriever input discipline (binding)

- The CANONICAL runtime input to a retrieval architecture is
  `{"question_id", "text"}` ONLY (`to_retriever_input()` in
  `data_tools/qa_schema.py`). Source articles, group, question type,
  split, and answerability are evaluator-side provenance, never retriever
  input. The projection raises on any unexpected field (fail closed).
- Evaluator-private question entries retain `meta` ONLY for the substrate
  provenance check. Raw `meta` is never passed to architecture code.
- `validate_qa.py` emits `runtime_projection_sha256` proving the runtime
  inputs hash with zero hint fields; tests assert no group/source/type
  strings appear in the runtime projection.

## 5. Executable workflow (after §0 gate)

```bash
# 1. Scaffold one group (human authors Q/A from candidate_units afterwards)
python3 -m data_tools.scaffold --corpus corpus/corpus.jsonl \
    --split-map corpus/split_map.json --group mercury --n 0 \
    --out staging/qa-dev-<id>.json

# 2. Author fills text/answer/sufficient_sets/hard_negatives/provenance.

# 3. Validate the staging dir (train/dev default; ids/counts only in output)
python3 -m data_tools.validate_qa --staging staging/ \
    --corpus corpus/corpus.jsonl --split-map corpus/split_map.json

# 4. Independent verifier (different identity) re-runs step 3, spot-reads
#    corpus nodes, records approve + rationale + content hash.

# 5. Custodian seals: seal_records() re-verifies EVERY record at its current
#    hash (duplicates / missing-stale approvals / reviewer==author all fail)
#    and only then partitions questions / train-dev labels / sealed heldout.
HELDOUT_CUSTODIAN_MODE=benchmark python3 -m data_tools.validate_qa \
    --staging staging/ --corpus corpus/corpus.jsonl \
    --split-map corpus/split_map.json --allow-heldout
```

Public-reference import (pinned bytes → dev-only entries, no answers):

```bash
# import file pinned by exact SHA-256; revision must be a full commit SHA
python3 -c "from data_tools.import_public import convert_public_file, check_import_pin; ..."
```

Tests (synthetic fixtures only — never real QA):

```bash
python3 -m unittest discover -s data_tools/tests   # 77 tests, passing
python3 -m unittest discover -s tests              # 249 tests, passing
```

## 6. Artifacts produced (only after the §0 gate)

| Artifact | Contents | Who sees it |
| --- | --- | --- |
| `staging/<qid>.json` | draft (Q + evidence + labels + provenance) | author + verifier |
| `questions.json` | qid/text/split/meta (no answers; evaluator-private) | all non-heldout |
| runtime projection | qid/text only (derived, hashed) | architectures |
| `labels.json` | train/dev answers + sufficient sets + provenance | builders (never in logs) |
| `heldout_labels.sealed.json` | heldout answers + sufficient sets | custodian only |
| validation manifest | counts, ids, approval tallies, hashes, error tally | all (no Q/A text) |

## 7. Decisions needed from the orchestrator (status recorded in `docs/qa-gate-decisions.md`)

1. **Corpus substrate**: revision `pilot-297-r1` (297 articles, splits
    205/44/48, canonical hash
    `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1`,
    `corpus/build_manifest.json` as byte ground truth) supersedes the
    247-article `pilot-247-v0`. **DECIDED — see gate-decisions §1.**
    Independent quality review of the revision is still pending
    (a revision, not a freeze).
2. **Question volume per split**: **DECIDED 60 train / 30 dev / 30
    held-out**, quotas of at least 10% unanswerable-or-ambiguous and at
    least 20% multi-hop — see gate-decisions §2.
3. **Public-import byte pin**: **PINNED** — 4 exact eval files at their
   audited HEADs in `references/public_eval_pins.json` (URL + revision
   + bytes + SHA-256 per file; 38,834 B total; import dry run passes
   with no answers imported). See gate-decisions §5.
4. **Custodian assignment**: **DECIDED — orchestrator-held procedural
    custody with dual gate** (no kernel boundary on a shared OS user;
    seal requires custodian flag + env var AND full re-verification).
    See gate-decisions §4.
5. **Grouping amendment or not**: **AMENDED by Round 0 repair (Lane D,
    per `docs/round0-repair-plan.md`) — same-split multi-hop replaces
    one-group multi-hop**; the authoritative gate stays in
    `substrate/splits.py` and leakage prevention is not weakened. Original
    decision (superseded): keep one-group multi-hop; cross-group exclusion
    is a documented limitation (shared-DAG cross-split links are common by
    design). See gate-decisions §3 and `docs/qa-semantic-audit-protocol.md`.

## 8. Real blockers (no freeze, no architecture work)

- Corpus revision `pilot-297-r1` (297 articles; 500-target shortfall stands:
  260 candidates never fetched, network halted by order) awaits independent
  quality review; derivation substrate is decided (see §7) but no freeze.
- No questions, labels, or sealed files exist yet — by design. Public
  eval files are pinned (`references/public_eval_pins.json`) but no
  public entries have been imported.
- Generator config `tokenizer_id` gap is a generator-owner repair (noted in
  contract v0.3 §4); derivation tooling does not depend on it.
- Independent review of this protocol + `data_tools/` still pending.

## 9. Unresolved logical limits (what code does NOT prove)

- Exact-span equality does not prove a span answers the question, entails
  the answer, or suffices alone or in combination — human judgment only.
- A `reviewed=True` negative is a recorded human claim, not a proof of
  non-answering; adversarial re-review can overturn it.
- `absent_reason` for unanswerable drafts asserts corpus absence the author
  could have missed; sampling + second-reader spot checks bound the risk
  but do not eliminate it.
- Ambiguous readings enumerate the interpretations the author found;
  further valid readings may exist undiscovered.
- Content-hash binding proves the approved bytes are unchanged, not that
  the approval was careful — reviewer identity + rationale exist so future
  audits can weight approvals, not so code can certify diligence.
