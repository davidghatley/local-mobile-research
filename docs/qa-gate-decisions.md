# QA Gate Decisions (orchestrator rulings recorded by protocol-refresh worker)

Status: **DECISIONS RECORDED — NOT A FREEZE.** No controlled train/dev
questions, no held-out questions, no labels, and no sealed files exist.
`corpus/questions.json` and any `*heldout*.sealed.json` remain absent.
These rulings authorize derivation planning only; architecture work starts
after the Round 0 common substrate passes independent review and is frozen.

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested spawning. No online LLM APIs, no paid
endpoints. No QA authored, no labels inspected or created, no architecture
work. `references/pins.json` treated as read-only (not modified).

## 1. Corpus substrate: pilot-297-r1 (supersedes the 247-article assumption)

- Revision `pilot-297-r1`: **297 articles**, 113,951 nodes,
  `corpus/corpus.jsonl` 43,876,251 bytes.
- Two hashes, distinct by construction — do not conflate:
  - Canonical (semantic) corpus hash `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1`
    (`substrate.corpus.corpus_hash` over canonical JSON-array text;
    recorded as `provenance.json:corpus_hash_sha256`; recomputed from
    bytes by this worker: match).
  - File-bytes SHA-256 `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64`
    (recorded in `corpus/build_manifest.json`; `sha256sum` of the file:
    match).
- Ground truth for bytes is `corpus/build_manifest.json` (self-consistent:
  all four per-artifact SHA-256/byte counts re-verified against files).
- Splits (seed `pilot-v1`, group-aware 70/15/15, 218 groups, counted from
  `corpus/split_map.json` by this worker): **train 205 / dev 44 /
  heldout 48 articles**. All 247 v0 group assignments preserved; the 50
  added articles map through predeclared groups.
- Revision 1 (`pilot-247-v0`, 247 articles) is archived under
  `corpus/archive/pilot-247-v0/` and is NOT the derivation substrate.
- Corpus is a revision, not a freeze: independent quality review of
  pilot-297-r1 is still pending per `docs/corpus-pilot.md`.

## 2. Question volume and quotas (orchestrator decision)

- Volume: **60 train / 30 dev / 30 held-out** (120 total).
- Quotas (binding on the final set, per split as applicable):
  - **≥ 10% unanswerable-or-ambiguous** (the two types distinct and
    consistency-enforced per protocol §2.7).
  - **≥ 20% multi-hop** (reference hop chains recorded per protocol §2.4).
- Derivation starts only after the §0 gate (corpus validated, split map
  frozen, generator + prompt pinned, protocol + tooling approved).

## 3. Multi-hop scope: one-group KEPT (orchestrator decision)

- The one-group multi-hop rule (protocol §1: every sufficient-set span of
  a multi-hop draft resolves to the SAME split-map group; cross-group
  multi-hop rejected by default) is **KEPT**.
- **Documented limitation:** article-level cross-split links are common
  by shared-DAG design (pilot-297-r1: 775/1,748 article-level in-corpus
  edges cross split boundaries, 44.3%), so confusable-group reasoning
  that would naturally chain across groups is excluded from the
  controlled set. Results therefore under-represent cross-group
  multi-hop difficulty; this must be stated alongside any multi-hop
  claim, not silently generalized past.
- Widening groups still requires an orchestrator-approved
  grouping-protocol amendment BEFORE freeze — never a silent relaxation.

## 4. Custodian: orchestrator-held procedural custody with dual gate

- The sealed held-out file (`heldout_labels.sealed.json`) is held by the
  **orchestrator** (withheld from development workers).
- Custody is **procedural, not filesystem enforcement**: all workers
  share one OS user, so there is no kernel boundary. Separation rests on
  a separate sealed file, the `HELDOUT_CUSTODIAN_MODE=benchmark` +
  `--allow-heldout` access gate, the opaque SHA-256 record, and the audit
  log (protocol §3).
- **Dual gate:** sealing requires (a) the custodian flag + env var AND
  (b) re-verification of EVERY record at its current hash (duplicates,
  missing/stale approvals, reviewer==author all fail) before partition.
  Developers never see held-out labels or held-out questions.

## 5. Public questions: dev/reference only (orchestrator decision)

- All public bounty / AndroidLM / boar questions are **development /
  reference only**: never training examples, never held-out, never with
  controlled evidence spans or imported answers.
- Import only via `data_tools/import_public.py` from the byte-pinned
  files in `references/public_eval_pins.json` (4 files, 38,834 bytes
  total, under the 5 MB budget), forced `split=dev`,
  `category=public_reference`. Byte mismatches are refused by
  `check_import_pin`; the dry run in the pins file confirms acceptance
  without importing any answers.
- No benchmark question text was used to shape corpus selection or this
  protocol; any future title-overlap analysis must be reported as a
  measured quantity.

## 6. Blockers unchanged

- Independent review of the protocol + `data_tools/` still pending.
- No questions, labels, sealed files, or freeze claim exist — by design.
- `tokenizer_id` generator-config gap remains a generator-owner repair.
