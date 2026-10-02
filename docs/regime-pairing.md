# Regime Pairing (Phase 3, Issue 3)

Regime B is a TAGGED PAIRED CONDITION over the SAME questions, not an
exclusive population.

## Paired design

- Regime A (`query_heldout_corpus_known`) covers the FULL shadow_dev
  population (32 groups): adaptation MAY include any corpus document.
- Regime B (`document_heldout`) re-evaluates a PAIRED SUBSET of those same
  question ids (56 staging shadow-dev drafts in 5 diverse groups:
  cambridge, corona, jaguar, lincoln, washington) under document-heldout:
  their source documents are excluded from ADAPTATION data.
- Conditions per question: `corpus_known` (A) vs `document_heldout` (B).
  Same `question_id`, two adaptation postures.
- B groups OVERLAP A by design. Disjointness is NOT asserted anywhere;
  `aggregate_across_regimes` still refuses unpaired A/B pooling, and
  `pair_conditions` refuses to join mismatched id sets (masquerade-proof).

## Invariants

1. QUERY-TIME corpus is UNCHANGED under B. Excluded documents leave
   adaptation/training data only, NEVER the retrieval corpus.
   Enforced by `verify_query_corpus_unchanged` (every excluded doc must
   resolve to a live corpus article) and `verify_adaptation_exclusion`
   (no excluded doc may appear in an adaptation-data manifest).
2. Corpus, candidate interface, generator, prompt, splits, and measurement
   stay comparable: pairing changes no question bytes, no corpus bytes,
   no prompt, no split of any non-migrated group.
3. Raw traces + provenance preserved: `corpus/regime_b_paired.json`
   records the selection rule, per-pair source mapping, and split-map hash.

## Reporting format

Per paired question: `{question_id, group, corpus_known: {...metrics},
document_heldout: {...metrics}}` via `evaluate_paired` / `pair_conditions`.
Aggregate via `aggregate_paired_delta` ->
`{n_paired, question_ids, metrics: {name: {mean_corpus_known,
mean_document_heldout, mean_delta}}}` where
`delta = mean(document_heldout) - mean(corpus_known)`.
Report A-on-paired, B-on-same-paired, and delta TOGETHER; never pool A
and B as independent samples.

## Artifacts

- `corpus/regime_b_paired.json` — paired subset (deterministic;
  regenerate with `derive_paired_subset` in `substrate/regime_metadata.py`).
- `corpus/regime_b_excluded_articles.json` — sorted union of
  B-excluded articles; `verify_round0` stage 9 checks set-equality
  against the Regime B group articles. Scope is adaptation-data
  exclusion ONLY (see `scope` field in the file).

## Migration note (split_map heldout -> shadow_dev, Phase 3)

`corpus/split_map.json` group splits migrated from legacy `heldout` to
`shadow_dev` (32 groups; no other bytes changed):

- old sha256: `b80a774dc9bbb799eb88d5b31975a22073ab054de93f9c5c02d562d32ec89ec1` (25219 B)
- new sha256: `d0879ac4801cd09c162761d1502376804ea6ad7efb4fce435f4feb44a2e1f7ff` (25315 B)

`corpus/build_manifest.json` split_map pin updated to match (bytes +
sha256). Historical hash records in `docs/corpus-pilot.md` and
`docs/corpus-quality-review-r1.md` intentionally left as history.
Validators still ACCEPT legacy `heldout` tokens (backward compat for
synthetic fixtures); no new item may use the retired name.

Effect on `data_tools.validate_qa`: the 87 `declared group split heldout
!= declared split shadow_dev` + 133 `evidence split != declared split`
residue errors (220 of 311) are map-mismatch artifacts of the stale map
and clear after migration (+ `data_tools/verify.py` accepting
`shadow_dev` as a mappable evidence split).
