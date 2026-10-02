# Distractor-scale corpus tier 1 — method and status

Scope: `corpus/scale/**` plus this document. Nothing here modifies the frozen
297-article core corpus.

## 1. What this layer is, stated plainly

**The scale layer is distractor material.** It exists only to provide
background mass for scale/regime experiments: extra articles that a retriever
can be made to consider and then reject. The 297-article core corpus (`corpus/corpus.jsonl`)
is the only evidence-bearing semantic base. Scale articles are background
material — they may have surface-level title or keyword overlap with core topics
(confusable_adversarial class) but carry no verified evidence bearings. No result
about answer quality, difficulty, or architecture merit may be derived from scale
articles alone; top confusable retrievals require adjudication against core
annotated evidence (see docs/scale-evaluation-rule.md).

### 1.1 Background vs Confusable distinction

Not all scale articles that retrieve core-related terms are equal. The classifier
distinguishes two categories:

- **background**: General distractor material with no strong confusable overlap.
  These articles have no significant title/keyword match with core corpus
  topics and serve purely as retrieval noise that a system should learn to
  ignore.

- **confusable_adversarial**: Articles whose title or keywords surface-levelly
  overlap with core topics. This class flags retrieval risk — the article may
  cause a retriever to return core-matching results that are not actually
  relevant to the question. However, a retrieved scale passage must NOT
  auto-count as a false positive merely for coming from the distractor layer.
  Top confusable retrievals require adjudication: the passage must be examined
  against core annotated evidence (the ground truth) to determine if it
  genuinely supports or contradicts the query, or if the match is merely
  superficial (same name, different entity).

The adjudication rule is therefore: *a retrieved scale passage is not
automatically a false positive simply because it originates from the distractor
tier*. Instead, it must be evaluated on its actual content relative to core
annotated evidence. Only when a scale article's content is verified as
irrelevant or contradictory to the core evidence can it be classified as a false
positive. Core annotated evidence remains the ground truth for all measured
claims.

### 1.2 Provenance timeline correction

The distractor candidate list (`corpus/scale/distractor_candidates.json`) was
added in commit `814dcc1` (2026-10-01), **after** question work began in commit
`4d924c5` (2026-09-29). Selection independence is procedural curation, not
pre-question independence. The 960-title candidate list was a procedurally
curated list frozen before fetch completion, but it was created after the
question draft authoring commenced. This is recorded as a procedural guarantee
about a curated list, not an empirical independence claim.

**The 297-article core corpus (`corpus/corpus.jsonl`) is the only
evidence-bearing semantic base.** Every measured claim in this project rests on
those 297 articles and their `train`/`dev`/`heldout` split map. Adding 940
distractors does not add 940 evidence articles. The two layers are separate
artifacts with separate manifests and disjoint node-id namespaces.

**All scale measurements are DESKTOP measurements.** Everything here was built
and would be measured on a desktop-class Linux machine. **No Android or
on-device performance claim may be derived from anything in this tier.** Latency,
throughput, memory footprint, or energy figures produced against this corpus are
desktop numbers and must not be reported as mobile results.

## 2. Build result

| Quantity | Value |
| --- | --- |
| Revision | `scale-tier1-940-r1` |
| **Articles built** | **940** |
| ~1000 tier target | **NOT met** (940 of 1000) |
| Core-overlap rejections | 0 |
| Duplicate-pageid rejections | 0 |
| Snapshot load problems | 0 |
| Redirect stubs (disclosed) | 110 |
| Nodes | 300,041 |
| — corpus roots / clusters / articles | 1 / 9 / 940 |
| — sections / paragraphs / sentences | 21,249 / 26,630 / 251,212 |
| `distractor.jsonl` | 117,645,284 bytes |
| Raw snapshot corpus | 100,755,488 bytes (96.09 MiB) |

### The ~1000 tier was not met, and why

The predeclared candidate list `corpus/scale/distractor_candidates.json` holds
**960** titles (seed `scale-v1`, declared target 700). The fetcher retrieved 940
and parked 20 as `not_found`. No re-fetch was performed for this tier, so **940 is
the achievable maximum on disk** and the ~1000 target is unreachable without new
acquisition. 940 is reported as the achieved count, not rounded up. The
`~1000` naming refers to the tier's intended scale, not to a count that was hit.

A further honest caveat: **110 of the 940 are redirect stubs** — pages whose
entire body is a `#REDIRECT` line. They convert to one degenerate paragraph
whose text is `REDIRECT <target>`, contributing ~1 paragraph and a handful of
sentence nodes each, and no real article prose. Subtracting them gives **830
substantive articles**. Both numbers are recorded in `tier_1k.json`
(`built_articles`, `redirect_stub_articles`,
`substantive_articles_excluding_redirect_stubs`) so neither figure has to be
inferred.

## 3. Acquisition log summary

Source: `corpus/scale/fetch_log.jsonl` (960 records) and `corpus/scale/raw/`
(940 snapshots).

| Outcome | Count |
| --- | --- |
| Candidates submitted | 960 |
| Fetched (`status: fetched`) | 940 |
| Parked `not_found` | 20 |
| Parked `max_retries_exceeded` | 0 |
| Parked `cap_exceeded` (400 MiB cap) | 0 |
| Corrupt / hash-mismatched snapshots | 0 |

Reconciliation is asserted by
`TestSnapshotIntegrity.test_not_found_candidates_are_accounted_for_not_hidden`:
`submitted == built + parked`. Every one of the 940 snapshots re-verifies
`sha256(wikitext) == content_sha256` at build time and again in the test suite.

All 20 parked titles, recorded individually in `tier_1k.json` `order_notes` with
status `no_snapshot_on_disk`: `A-holes`, `Alienore`, `Andy mineo`, `Ankhmahor`,
`Anti-nowhere League`, `Apex fallacy`, `Ar account`, `Arctic Red`, `Argi`,
`Asia Pop`, `Asian Pacific American Heritage`,
`Asian Pacific American,Asian Pacific American`, `Asian immigration`, `Aylos`,
`Azzlack`, `B.oogie`, `Bofe`, `Boketto`, `CELLS`,
`Eruption of Mount Tambora in 1815`.

Several are plausibly real articles under a corrected title — `CELLS` and
`A-holes` in particular look like case-mangling rather than genuinely missing
pages. That is a fetcher defect (no redirect/case normalization), not evidence
that the pages do not exist, and it is why the achievable count is 940 rather
than a higher number.

### Two real defects in the acquisition layer

These are recorded rather than papered over:

1. **`revid` is null in all 940 snapshots.** The fetcher requested
   `rvprop=timestamp|user|comment|content` and omitted `ids`, so no revision id
   was ever returned, and it never fell back to a `revid` field. Attribution is
   therefore pinned by `source_url` + revision `timestamp` + `content_sha256`
   rather than by a permanent `oldid`. `tier_1k.json` `attribution.known_gap`
   states this, and
   `TestTierManifestContent.test_cc_by_sa_attribution_is_declared_with_its_gap`
   asserts `revid_available_count == 0` so the gap cannot be quietly forgotten.
   Fixing it requires a re-fetch, which was out of scope for this tier.

2. **`outlinks` is empty for all 940 snapshots** (placeholder `[]`; the fetcher
   did not request `prop=links`). Article-level DAG edges are therefore absent;
   cross-links exist only at paragraph level, derived from wikitext by the shared
   converter's `para_links`. `article_level_in_corpus_links` in the manifest
   reflects the paragraph-level total.

Additionally, the fetcher wrote the literal string `"distractor"` into every
snapshot's `cluster` field, discarding the predeclared cluster taxonomy. The
builder uses the **predeclared candidate list's** cluster (`cluster_source:
"candidate"`) and records the disagreement; `--cluster-source snapshot` is
available for comparison.

## 4. Methodology

### 4.1 Same converter, same caps, separate namespace

`corpus/scale/scale_build.py` imports the **core converter** (`build_pilot.py`)
and calls the same functions with the same caps as `corpus/build_offline.py`:
`convert_article(..., stats=..., sent_cap=None)`, `split_sentences(..., cap=None)`,
`para_links`, `slugify`, `norm_key`, `MAX_PAR_PER_ART = 250`,
`MAX_LINKS_PER_ART = 2500`, `SKIP_SECTIONS`, `LICENSE = "CC BY-SA 4.0"`.
No converter function is reimplemented. No article hit the 250-paragraph cap.

Pipeline, in order:

```
validate snapshots (keys + content hash)
  -> select in predeclared candidate order
  -> MECHANICAL de-duplication against the frozen core 297
  -> intra-tier pageid de-duplication
  -> convert (build_pilot converter, uncapped sentences, removal stats)
  -> substrate validate_hierarchy
  -> stage into a clean temp dir
  -> re-read staged bytes, re-hash, re-validate, re-check namespace disjointness
  -> atomic publish (copy to dest-dir temp name, then os.replace)
```

Publish is atomic per file and refuses to write anything if any staged artifact
is missing. The builder performs **no network I/O** — proven by a static source
scan and by a full build executed with `socket.socket` and
`socket.create_connection` replaced by tripwires.

### 4.2 Disjoint node-id namespace

| Layer | Root | Cluster | Article | Section | Paragraph | Sentence |
| --- | --- | --- | --- | --- | --- | --- |
| Core (297) | `corpus:pilot` | `cluster:<slug>` | `a:<slug>` | `s:…` | `p:…` | `t:…` |
| **Scale (940)** | **`corpus:scale-distractors`** | **`dc:<slug>`** | **`d:<slug>`** | **`ds:…`** | **`dp:…`** | **`dt:…`** |

No scale prefix is a prefix of another, so ids are unambiguous. The two roots
coexist in the merged view without interference. Tests assert: the node-id sets
are disjoint; every scale node carries the right prefix for its kind; **no scale
cross-link points at a core node**; and `substrate.corpus.validate_hierarchy`
passes on both the standalone scale DAG and the merged `core + scale` view.

Slug collisions are disambiguated with a `~<pageid>` suffix. Article identity is
keyed on the **exact** Wikipedia title, not on `norm_key` — `ABBA` and `Abba`
are distinct articles and `norm_key` would merge them. (The previous draft of
`scale_build.py` keyed on `norm_key` and silently dropped one of the two.) The
casefolded index is used only for cross-link resolution, and ambiguous casefolded
keys are dropped rather than resolved arbitrarily.

### 4.3 Mechanical de-duplication against the core

Three exact-key set intersections against all 297 core article nodes:

| Key | Core collisions found |
| --- | --- |
| `pageid` | **0** |
| normalized title (`bp.norm_key`) | **0** |
| `content_sha256` | **0** |

The rejection predicate is mechanical — exact set membership, no fuzzy or
semantic matching, no tolerance. A synthetic probe colliding on exactly one key
is rejected with that key named, which is asserted directly. Every rejection
would be recorded in `tier_1k.json` `excluded_core_overlap`; the list is
**empty**. The candidate list's own claim that it "excludes core 297 titles" is
therefore *verified*, not merely asserted.

**Cross-referencing is one-directional.** The tier manifest cites the core
corpus sha256, the core corpus hash, and the core build manifest sha256. A test
scans all four core sidecars and `corpus/corpus.jsonl` and asserts none of them
contains the scale root id, a scale node-id prefix, or `corpus/scale`. (The
literal word "scale" is *not* banned in `corpus.jsonl`: it occurs incidentally
in 44 MB of English article text, so banning it would be a false positive. The
test bans the layer's identifying tokens instead.)

### 4.4 No split map is emitted — deliberately

All 940 snapshots carry `split_group = "distractor"`. The distractor tier is
never evaluated, never used as evidence, and never enters a measured
`train`/`dev`/`heldout` question set. A group map here would be a single group
whose `assign_split()` label is an arbitrary hash artifact implying a
measurement partition that does not exist — fabricating a split. Instead
`tier_1k.json` records `split_assignment.split_map_emitted: false` and
`measured_splits: []`, and a test asserts that **no scale article appears in the
frozen core `split_map.json`**. That is the property that actually matters:
distractor mass cannot leak into a measured split.

### 4.5 Determinism

Determinism is load-bearing, so every published artifact is a pure function of:
raw snapshot bytes + candidate-list bytes + builder bytes + core corpus bytes +
the revision string. No wall clock, no PRNG, no dict-order dependence, no
network.

`built_utc` is deliberately `null` in `scale_provenance.json`; embedding a clock
would silently break byte-identity. Wall-clock times belong in the excluded
`build_run_log.jsonl`, not in a pinned artifact. Two independent builds produce
**byte-identical** output for all five published artifacts, and the published
artifacts match a fresh build. Both are asserted.

The stage directory is deleted and recreated at the start of each build, so a
stale artifact from an earlier run cannot be measured or published.

## 5. Artifacts and hashes

`corpus/scale/scale_build_manifest.json` (revision `scale-tier1-940-r1`) pins
every other artifact by sha256 and byte size:

| Artifact | Bytes | sha256 (first 16) |
| --- | --- | --- |
| `corpus/scale/distractor.jsonl` | 117,645,284 | `516463e340de8c53` |
| `corpus/scale/scale_provenance.json` | 1,059,336 | `edfcf961f4a5663e` |
| `corpus/scale/scale_input_manifest.json` | 246,455 | `69d5c16d23bb1ee7` |
| `corpus/scale/tier_1k.json` | 758,883 | `3252ed1bb42e8fc5` |

Core reference cited by the tier:

| Quantity | Value |
| --- | --- |
| `corpus/corpus.jsonl` sha256 | `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64` |
| Core corpus hash | `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1` |
| `corpus/build_manifest.json` sha256 | `5647f794b813ae11c05f2b56e1ec3fcd60ffe69aa8d939bb31c78ee0b5e0e997` |
| Core articles / nodes | 297 / 113,951 |
| Scale articles / nodes | 940 / 300,041 |

Disk footprint: **96.09 MiB** of raw snapshots dominate. `corpus/scale/raw/` and
`corpus/scale/distractor.jsonl` are git-ignored and pinned by hash; recovery
depends on the per-file hashes in `tier_1k.json` still matching. The core
artifacts are likewise git-ignored but byte-verified against
`corpus/build_manifest.json` on every test run.

## 6. Verification

`python3 -m unittest discover -s corpus/scale/tests -t .` — **38 tests, all
passing**, ~150 s (two full builds plus the blocked-socket build).

Proven:

- zero core overlap on pageid / normalized title / content hash, and the
  de-duplication predicate itself is exercised with a synthetic collision;
- core artifacts still byte-identical to `corpus/build_manifest.json` after the
  scale build, and the core cites nothing about scale;
- deterministic double-build (byte-identical) and published-vs-fresh agreement;
- node-id namespaces disjoint, prefixes unambiguous, no scale→core links, and
  `validate_hierarchy` passing on the merged view;
- no scale article in the frozen core split map;
- no wall clock in any published artifact; no network reachable from the build;
- tier target reported honestly, with the shortfall explained;
- all 940 snapshots re-verify their content hashes; the 960-candidate ledger
  reconciles; redirect stubs are disclosed rather than hidden.

`corpus/tests` (17 tests) still passes — the scale builder did not perturb the
core converter.

## 7. Open items and limits

1. **The ~1000 tier was not met: 940 built, 830 substantive after removing 110
   redirect stubs.** Closing the gap needs new acquisition (the candidate list
   is exhausted at 960) and a fetcher that resolves redirects rather than storing
   `#REDIRECT` stubs.
2. **`revid` is absent for every article.** Attribution rests on
   `source_url` + timestamp + content hash. A `prop=revisions&rvprop=ids`
   re-fetch would close this.
3. **No article-level DAG edges**, because the fetcher stored empty `outlinks`.
4. **No 5k or 10k tier was attempted**, by instruction. Tier 1 alone does not
   produce a scaling curve; the stopping rule (saturate or cleanly extrapolate)
   cannot be evaluated from a single point.
5. **No empirical scale measurement has been run.** This tier is built and
   verified, not measured. Any future scale measurement is a desktop
   measurement and carries no Android implication.
6. **Selection independence is procedural, not statistical.** The 960-title list
   was frozen before any fetch and before any question construction, and no
   benchmark answer informed it. That is a process guarantee about a curated
   list, not an independence test.