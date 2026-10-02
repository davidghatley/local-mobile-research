# Provenance Correction

## Timeline correction for scale distractor candidates

The following factual correction records the git-level provenance of the
distractor candidate list relative to question work initialization.

| Event | Commit | Date | Notes |
|-------|--------|------|-------|
| Question work began | `4d924c5` | 2026-09-29 | "Round 0: experimental substrate, corpus, fixed generator, and QA tooling". Common experimental substrate initiated, including 297-article corpus, QA protocol, and train/dev/heldout split design. |
| Distractor candidates added | `814dcc1` | 2026-10-01 | "Phase 5a: dev expanded 10 -> 60; Phase 7 scale scaffolding started". `corpus/scale/distractor_candidates.json` was created. This is **2 days after** question work began. |

## Key point

- **Selection independence is procedural curation, NOT pre-question independence.**
- The 960-title candidate list was frozen in `corpus/scale/distractor_candidates.json` *after* question draft authoring had already commenced (4d924c5).
- The list's method string ("PROCEDURAL, NOT EMPIRICAL") in the build manifest attests to its procedural nature: it was a curated list, not an empirical independence test.
- No scale title was chosen by looking at a held-out answer, and no scale article is evidence-bearing. The independence guarantee is about the *list curation process*, not about statistical independence from question content.

## Do not rewrite pinned JSON text

- `corpus/scale/scale_provenance.json` and `corpus/scale/tier_1k.json` contain
  pinned hashes and timestamps that must not be modified. This correction file
  (`PROVENANCE-CORRECTION.md`) is the place to record the timeline discrepancy,
  not by editing the pinned JSON artifacts.