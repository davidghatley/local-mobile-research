# QA Gate Decisions (orchestrator rulings recorded by protocol-refresh worker)

Status: **DECISIONS RECORDED — NOT A FREEZE.** 70 controlled drafts exist in staging (60 train, 10 dev); no held-out questions, no labels, and no sealed files exist. `corpus/questions.json` and any `*heldout*.sealed.json` remain absent. These rulings authorize derivation planning only; architecture work starts after the Round 0 common substrate passes independent review and is frozen.

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified zero-cost catalog entry). No nested spawning. No online LLM APIs, no paid endpoints. No QA authored, no labels inspected or created, no architecture work. `references/pins.json` treated as read-only (not modified).

## 1. Corpus substrate: pilot-297-r1 (supersedes the 247-article assumption)

- Revision `pilot-297-r1`: **297 articles**, 113,951 nodes, `corpus/corpus.jsonl` 43,876,251 bytes.
- Two hashes, distinct by construction — do not conflate:
  - Canonical (semantic) corpus hash `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1` (`substrate.corpus.corpus_hash` over canonical JSON-array text; recorded as `provenance.json:corpus_hash_sha256`; recomputed from bytes by this worker: match).
  - File-bytes SHA-256 `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64` (recorded in `corpus/build_manifest.json`; `sha256sum` of the file: match).
- Ground truth for bytes is `corpus/build_manifest.json` (self-consistent: all four per-artifact SHA-256/byte counts re-verified against files).
- Splits (seed `pilot-v1`, group-aware 70/15/15, 218 groups, counted from `corpus/split_map.json` by this worker): **train 205 / dev 44 / heldout 48 articles**. All 247 v0 group assignments preserved; the 50 added articles map through predeclared groups.
- Revision 1 (`pilot-247-v0`, 247 articles) is archived under `corpus/archive/pilot-247-v0/` and is NOT the derivation substrate.
- Corpus is a revision, not a freeze: independent quality review of pilot-297-r1 is still pending per `docs/corpus-pilot.md`.

## 2. Question volume and quotas (orchestrator decision — REVISED per Lane E Phase 2)

- **Controlled total: 240** (60 train / 60 dev / 120 SEALED held-out).
- Previous target (60/30/30 = 120 total) was statistically insufficient for high-accuracy claims.
- **Statistical reasoning for n=120 held-out**:
  - n=30 is insufficient: 30/30 successes gives a Wilson 95% CI of roughly [88%, 100%], which cannot support a ~99% accuracy claim.
  - n=120 narrows the Wilson 95% CI to roughly [97%, 100%] for 120/120 successes, enabling credible high-accuracy claims.
  - If the corpus cannot yield 120 GOOD held-out items, REPORT the shortfall with evidence — do NOT fill with weak questions and do NOT silently revert to 30.
- Quotas (binding on the final set, per split as applicable):
  - **≥ 10% ambiguous-or-unanswerable retained** (the two types distinct and consistency-enforced per protocol §2.7).
  - **Target ~≥ 25% genuine multi-hop** with substantial cross-article AND same-split cross-group representation; do not manufacture cross-group hops to hit a quota.
  - Multi-hop defined by single-atom answerability test (Lane D): a question is multi-hop iff no single support atom alone suffices to answer it.
  - Same-split cross-group: multiple groups allowed iff they all sit in ONE split (Lane D ruling).
- Derivation starts only after the §0 gate (corpus validated, split map frozen, generator + prompt pinned, protocol + tooling approved).

## 3. Multi-hop scope: same-split rule (Lane D ruling, supersedes one-group KEPT)

- The one-group multi-hop rule (protocol §1: every sufficient-set span of a multi-hop draft resolves to the SAME split-map group; cross-group multi-hop rejected by default) is **REPLACED** by the same-split rule.
- **Same-split rule**: multiple GROUPS are allowed in a multi-hop question iff they all sit in ONE split. Only genuinely cross-SPLIT source sets are rejected.
- **Documented limitation**: article-level cross-split links are common by shared-DAG design (pilot-297-r1: 775/1,748 article-level in-corpus edges cross split boundaries, 44.3%), so confusable-group reasoning that would naturally chain across groups is excluded from the controlled set. Results therefore under-represent cross-group multi-hop difficulty; this must be stated alongside any multi-hop claim, not silently generalized past.
- Widening groups still requires an orchestrator-approved grouping-protocol amendment BEFORE freeze — never a silent relaxation.

## 4. Custodian: orchestrator-held procedural custody with dual gate

- The sealed held-out file (`heldout_labels.sealed.json`) is held by the **orchestrator** (withheld from development workers).
- Custody is **procedural, not filesystem enforcement**: all workers share one OS user, so there is no kernel boundary. Separation rests on a separate sealed file, the `HELDOUT_CUSTODIAN_MODE=benchmark` + `--allow-heldout` access gate, the opaque SHA-256 record, and the audit log (protocol §3).
- **Dual gate**: sealing requires (a) the custodian flag + env var AND (b) re-verification of EVERY record at its current hash (duplicates, missing/stale approvals, reviewer==author all fail) before partition. Developers never see held-out labels or held-out questions.
- **Custody audit (Round 0 addition, Lane E)**: `HeldoutCustodian.load_labels` now REQUIRES accessor identity, role, and purpose (fail closed on empty/unknown). Every granted access appends an audit record with: accessor, role, purpose, timestamp_utc, labels_path, seal_sha256 at access time, question_ids actually read, granted_by. Append-only: no delete/overwrite path. Seal hash in audit record enables post-seal tampering detection.

## 5. Public questions: dev/reference only (orchestrator decision)

- All public bounty / AndroidLM / boar questions are **development / reference only**: never training examples, never held-out, never with controlled evidence spans or imported answers.
- Import only via `data_tools/import_public.py` from the byte-pinned files in `references/public_eval_pins.json` (4 files, 38,834 bytes total, under the 5 MB budget), forced `split=dev`, `category=public_reference`. Byte mismatches are refused by `check_import_pin`; the dry run in the pins file confirms acceptance without importing any answers.
- No benchmark question text was used to shape corpus selection or this protocol; any future title-overlap analysis must be reported as a measured quantity.

## 6. Generalization regimes (Lane E Phase 2 — machine-readable, never conflated)

Two regimes, disjoint and separately reported. Every result MUST state its regime.

### REGIME A — `query_heldout_corpus_known` (PRIMARY)
- Corpus documents MAY be known during architecture adaptation.
- Benchmark questions/labels/phrasing unseen.
- Architecture MAY generate synthetic training from any corpus text including documents later used to answer benchmark questions.
- This is the primary regime for architecture comparison.

### REGIME B — `document_heldout`
- Source documents for the evaluation slice are EXCLUDED from architecture-specific fine-tuning/example generation.
- Regime B groups are a small subset of held-out groups with ≥4 articles each and diverse topics.
- Regime B groups are ALWAYS a subset of held-out groups, never train/dev.
- Document-heldout excluded-article artifact (`corpus/regime_b_excluded_articles.json`) exists iff regime B groups are non-empty.

**Cross-regime aggregation is FORBIDDEN**: `aggregate_across_regimes()` helper refuses to pool mixed-regime metrics (raises `ValueError`) rather than silently aggregating. Regime metadata lives in a separate Round 0 artifact derived from `corpus/split_map.json` WITHOUT modifying it (split map hash stays pinned).

## 7. Synthetic leakage check (Lane E Phase 2 — custodian-only, stdlib only)

- New `data_tools/leakage_check.py`: given a synthetic question file and the sealed held-out set, detects near-duplicates and RELEASES nothing sensitive.
- Method: character n-gram Jaccard (stdlib) as the STANDALONE path; an optional embedding-cosine path only if a local embedding model is already present, otherwise reports `embedding_path_available: false` and says the n-gram path stands alone.
- Emits a report containing: status PASS|REJECT, total_synthetic, flagged_count, flagged_ids (SYNTHETIC ids only), n-gram similarity distribution/histogram and max, the dev-calibrated threshold AND the dev operating characteristics it was calibrated to, which paths were available, and the heldout seal sha256.
- NEVER emits held-out ids, held-out question text, held-out answers, or which held-out item any synthetic item matched.
- Thresholds are calibrated on dev with recorded operating characteristics (flagged/true-positive rate at the chosen threshold), not asserted from an external default (Ruling R1).

## 8. Manifest + freeze additions (Lane E Phase 2)

`RunManifest` gains:
- `regime_a_heldout_groups`: list of group keys for Regime A
- `regime_b_document_heldout_groups`: list of group keys for Regime B
- `public_reference_pins_sha256`: hash of `references/public_eval_pins.json`

`validate_freeze` additionally verifies:
- (a) regime A and B held-out groups together cover the held-out groups in the derived regime metadata
- (b) regime B groups are a subset of held-out groups, never train/dev
- (c) the document-heldout excluded-article artifact exists iff regime B groups are non-empty
- (d) `public_reference_pins_sha256` matches `references/public_eval_pins.json` bytes
- (e) the custody audit log, if present, has entries whose `seal_sha256` matches the sealed labels hash

Fail closed with explicit gaps.

## 9. Blockers unchanged

- Independent review of the protocol + `data_tools/` still pending.
- No held-out questions, labels, sealed files, or freeze claim exist — by design.
- `tokenizer_id` generator-config gap remains a generator-owner repair.