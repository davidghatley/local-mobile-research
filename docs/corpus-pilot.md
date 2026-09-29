# Round 0 Wikipedia Pilot Corpus

Status: **REVISION pilot-297-r1 — REBUILT OFFLINE, NOT FROZEN.** Revision 1
(`pilot-247-v0`, 247 articles, preserved in `corpus/archive/pilot-247-v0/`)
was rejected by the orchestrator for QA use: 13.7% markup debris and 24
hard truncations materially confound evidence experiments. This document
describes the authorized offline-only rebuild (297 articles, repaired
converter). No freeze has occurred; this is a revision, not a re-freeze.

Worker model: `opencode/muse-spark-1.3-contributor-free` (explicit, verified
zero-cost catalog entry). No nested spawning was used. No substrate files were
modified (read-only import for validation/hashing). No network requests were
made during the rebuild (proven by test, see §10).

Scope ownership: this worker owns `corpus/` **except**
`corpus/generator_config.json` (generator owner) and any future
`corpus/scripts/corpus_*` paths, plus this document. This pilot creates **no**
`corpus/questions.json` and **no** `corpus/heldout_labels.sealed.json` — those
belong to later steps. No architecture code was written.

## 1. What was built

- `corpus/article_candidates.json` — predeclared candidate title list (frozen
  before any fetch or question creation), with topic cluster and
  confusable-group annotations, fill order, seed, and spare list.
- `corpus/build_pilot.py` — deterministic fetch + convert + split script.
  Re-running it reproduces `corpus.jsonl` byte-identically from `corpus/raw/`
  (resume-safe; skips already-fetched snapshots).
- `corpus/raw/*.json` — one raw MediaWiki API snapshot per article:
  requested/normalized titles, pageid, revision id, revision timestamp,
  full wikitext, outlinks, fetch time. These reproduce the conversion.
- `corpus/corpus.jsonl` — canonical substrate `CorpusNode` DAG
  (`corpus > cluster > article > section > paragraph > sentence`), sorted by
  `node_id`, validated with `substrate.corpus.validate_hierarchy`.
- `corpus/split_map.json` — group-aware seeded reservation of whole articles
  to train/dev/heldout (seed `pilot-v1`, 70/15/15), made BEFORE any question
  creation. Confusable/near-duplicate groups are kept intact in one split.
- `corpus/provenance.json` — per-article revid/timestamp/source URL/license/
  content hash, global hashes, byte counts, caps, gaps, validation errors.

## 2. Selection method and benchmark independence (corrected)

Correction to an earlier overstatement: public benchmark questions **do**
exist (AndroidLM eval sets, boar-app eval set) and a *separate* worker
inspected those repos for the reference audit. Independence here is therefore
a property of the selection procedure, not of the environment, and is stated
exactly:

- The candidate title list (`corpus/article_candidates.json`) was declared
  from general topic coverage (9 clusters) plus deliberately confusable
  near-duplicate sets, **before any fetch and before any question creation**.
  It was not optimized, filtered, or tuned using benchmark answers: no
  benchmark question text was read during selection (only the reference
  audit's aggregate descriptions of eval-set sizes/formats, which contain no
  answers), and no retrieval or QA experiment was run to shape the list.
- Selection provenance: method + seed (`pilot-v1`) are frozen inside
  `article_candidates.json`; fill rule is mechanical (main list in file
  order, then spares in order, stop at 500 successes). `provenance.json`
  records the frozen list's hash inputs (titles fetched, gaps, replacements
  drawn only from the predeclared spares).
- Residual risk (recorded, not waived): the list author (this worker) has
  general awareness that public repos discuss Wikipedia-centric QA. That
  cannot be undone; the mitigation is that the procedure above leaves no
  step where benchmark content could have altered the titles. Any future
  overlap analysis between pilot titles and public dev questions must be
  reported as a measured quantity, not assumed away.

## 3. Source, license, attribution

- Source: English Wikipedia via the MediaWiki Action API
  (`https://en.wikipedia.org/w/api.php`), fetched 2026-09-29, polite
  single-request pacing with a research User-Agent.
- Per-article revision id + timestamp + canonical URL are stored in both the
  raw snapshot and the article node's `meta` (`pageid`, `revid`,
  `timestamp`, `source_url`, `content_sha256`).
- License: article text under **CC BY-SA 4.0** (individual revisions may
  carry older dual terms — see per-article revid). Attribution = per-article
  source URL + revision id. No places data (ODbL) or other licensed corpora
  are mixed in.
- Full-corpus alternatives (e.g. ~21 GB wiki.db) were deliberately not
  downloaded: inappropriate for ~33 GB free disk and unnecessary for a pilot.

## 4. Conversion (wikitext → DAG, audited)

- Sections from `== h2 ==`–`==== h4 ====` headings; lead content under a
  `(lead)` section; h5+ headings folded into the parent section. Reference /
  see-also / external-link / bibliography sections are excluded from node
  text (their outlinks are still captured at article level from the API).
- Block-level stripping runs on full section text BEFORE paragraph splitting
  (templates nesting-aware, File/Image/Category namespace links via balanced
  scanning, `{| |}` tables line-anchored, HTML comments and
  onlyinclude/includeonly/noinclude tags, refs). Unbalanced constructs are
  KEPT as visible residue rather than eating to end of text — no silent
  content loss by construction. Unclosed layout tables drop only the opener
  line (content kept); unclosed data tables additionally drop
  markup-looking lines (`|-`, `|}`, `|+`, `!`-headers, `|`-cells) but keep
  prose/list lines. Orphan rows from template-generated tables (e.g.
  `{{election table}}`, which emits rows with no `{|` opener) are removed
  per-line with the same prose protection.
- Paragraphs split on blank lines (cap 250/article); overlong blocks are
  chunked on sentence boundaries (single boundary-less runs hard-split on
  whitespace), so no source text is truncated away. Sentences by a
  punctuation heuristic (cap 12/paragraph; documented imperfection on
  abbreviations such as "Dr.").
- Residue audit on the first 247 snapshots: iterative measurement drove
  markup debris from ~2900 affected paragraphs (naive per-paragraph regexes)
  to zero confirmed debris in 9242 paragraphs. The only remaining detector
  hits (3) are LaTeX-notation false positives (`|-\rangle`,
  `\frac{1}{4\pi|\mathbf x|}`, `\mathbb{R^{|A|}`), inherent to regex
  scanning of math — not conversion defects.
- Cross-links: article-level edges from the complete API outlink list
  resolved into the corpus; paragraph-level edges from parsed `[[links]]`
  resolved the same way (table-debris links excluded by the orphan-line
  filter). Sentence nodes carry no links (documented choice).
- Caps and exclusions are recorded in `provenance.json:conversion_caps`.

## 5. Splits and contamination (read before question creation)

- `split_map.json` reserves whole articles to train/dev/heldout by seeded
  hash of the **group key** (seed `pilot-v1`, 70/15/15): every confusable /
  near-duplicate group is assigned intact to a single split, so no group is
  ever divided across splits. Ungrouped articles form singleton groups and
  are assigned individually. This reservation happens BEFORE any question
  creation; whole evidence groups stay intact where defined.
- No held-out (or any) QA pairs, evidence anchors, or labels were created by
  this worker: `corpus/` contains no `questions.json` and no sealed labels
  file. (Note: `corpus/generator_config.json` present in the directory is
  the generator owner's file, not this worker's, and was left untouched.)
- The corpus files themselves remain **shared searchable knowledge across
  all splits**; only future QA supervision (questions/labels) is disjoint.
  Reading corpus text during development is therefore **not** held-out-label
  leakage (no labels exist yet).
- Known limitation: articles link across split boundaries (shared-DAG
  cross-links are intentional for retrieval redundancy). Reported metric:
  article-level cross-split link count vs total (see §7). Future question
  authors must additionally keep multi-hop evidence chains' articles in mind
  and must never train on public bounty questions.
- Same-OS-user sealing caveat from the experimental contract applies to all
  future sealed files; custody is procedural, not a kernel boundary.

## 0. Current revision: pilot-297-r1 (final, pending independent review)

- Inputs: 297 validated raw snapshots (distinct pageids, content hashes
  verified), predeclared candidate order, repaired converter, zero network.
- Outputs (verified from bytes): `corpus/corpus.jsonl` 43,876,251 B,
  canonical hash `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1`;
  297 articles, 113,951 nodes; splits train 205 / dev 44 / heldout 48.
- Full record: §9 (method) – §11 (losses, inspection, tests).
  Sections 6–8 are the **superseded pilot-247-v0 record** (artifacts in
  `corpus/archive/pilot-247-v0/`).

## 9. Revision pilot-297-r1: method (current)

- Scope: offline-only rebuild incorporating the 247 snapshot raws + 50
  further raws acquired (then halted) by the paced resume before the
  no-network order. **No network requests were made during this revision.**
  Proof: `corpus/build_offline.py` contains no socket/urllib/requests usage
  (static test) and the full build succeeds with `api_get` monkeypatched to
  raise and `socket.socket` blocked (behavioral test,
  `corpus/tests/test_converter_offline.py::OfflinePath`).
- Exact build command (run twice for determinism):
  `python3 corpus/build_offline.py --stage <tmpdir> --revision pilot-297-r1`
  Staging dirs: `/tmp/opencode/offline_stageA` (published),
  `/tmp/opencode/offline_stageB` (comparison only).
- Input manifest (`corpus/input_manifest.json`): candidate list
  (`article_candidates.json`, seed `pilot-v1`), builder file hash,
  per-snapshot file sha256 (297 files, all included, 0 load problems, 0
  pageid duplicates — pageids distinct 297/297, no duplicate source texts).
- Selection: predeclared candidate order (main list then spares); all 297
  raws matched in order. Split assignment reuses the identical seeded
  group hash (`pilot-v1`, 70/15/15): **all 247 v0 assignments preserved
  (0 changed)**; 50 added articles map through their predeclared groups
  (6 new spare singleton groups → 218 total).
- Atomic publish: staged outputs verified (re-read + hash + hierarchy +
  group-map) then copied to temp names in `corpus/` and `os.replace()`d as
  a consistent set; `corpus/build_manifest.json` records per-artifact
  sha256/bytes (all re-verified post-publish: match).
- Determinism (TWO full builds, same inputs): `corpus.jsonl`,
  `split_map.json`, `input_manifest.json` **byte-identical**;
  `provenance.json` identical excluding `built_utc`; `build_manifest.json`
  differs only in the provenance sha (timestamp-caused, expected).
- Converter vs v0: balanced-span scanners (templates, keep-if-unbalanced),
  line-anchored tables (unclosed wrappers keep content), namespace-link
  scanner, orphan rows from template-generated tables dropped with
  prose protection, **sentence-boundary chunking instead of truncation**
  (no 4,000-char cut; `max_sentences_per_paragraph: null` — ALL sentences
  preserved as nodes, 0 omitted-descendant flags needed), flat inline-data
  template rescue (`cvt/convert→"60,268 km"`, `math/mvar/sub/sup/frac/
  lang/transl/lit/coord`), gallery `File:name|caption` → caption.
  250-paragraph/article safety cap retained, never hit (max 106).

## 10. Revision pilot-297-r1: measured results

- Articles: **297** (target was 500; remaining 260 candidates never fetched —
  network halted by order, not by cap).
- Nodes: **113,951** = 1 corpus + 9 clusters + 297 articles + 8,146
  sections + 9,979 paragraphs + 95,519 sentences.
- `corpus/corpus.jsonl`: **43,876,251 bytes**, canonical
  `08aa2c53ddee6f35b8139de0010e6aa20a4504ea881941b3ec20a5d747f089d1`;
  `validate_hierarchy`: 0 errors; `validate_group_map`: 0 errors, 297/297.
- Other artifacts: `provenance.json` 341,364 B (`e6e33910…89761e`),
  `split_map.json` 25,219 B (`b80a774d…ec89ec1`),
  `input_manifest.json` 94,270 B (`685ca5c0…141b4`),
  `build_manifest.json` 785 B (`5647f794…e997`). Raw dir (297 files):
  41,458,400 B. Run-1 HTTP download was 80,619,003/200,000,000; resume
  addition estimated ≈ +18 MB by the observed 2.4× body/raw ratio (≈99 MB
  total, under cap — ESTIMATE, method stated, not measured).
- Splits: **train 205 / dev 44 / heldout 48** (218 groups). Confusable
  groups intact: **20/30** (amazon, apes, apple, berlin, cambridge,
  columbia, corona, delta, eclipse, jaguar, java, lincoln, london, mercury,
  paris, python, saturn, shell, venus, washington). Still incomplete (never
  fetched, no snapshot exists): bears (Polar/Brown bear), bigcats (all 4),
  mars (chocolate bar), nile (Nile, Aswan Dam, Pyramids of Giza),
  orange (Orange S.A.), peaks (Kilimanjaro), revolutions (French
  Revolution), rome (Roman Empire, Colosseum), tesla (Light bulb),
  worldwars (all 4).
- Links: article-level in-corpus edges **1,748**, cross-split **775
  (44.3%)** — shared-DAG design; QA supervision disjointness unaffected,
  multi-hop authors must mind cross-split chains.
- Provenance per article (297/297): pageid, revid, timestamp, source URL,
  CC BY-SA 4.0 license, cluster, split_group, content sha256. Redirects
  resolved with aliases: 9. Outlink caps (2,500) hit by 3 articles
  (truncation flags per article in provenance).
- Removal accounting (measured, totals): 26,784 templates removed
  (2,573,049 chars) + **6,854 rescued with values intact**; 5,950
  namespace/File links removed (917,739 chars); 53,222 refs;
  364 tables closed + 1 unclosed; 295 orphan rows; 1,107 gallery captions
  kept; 1 paragraph chunked, 1 sentence hard-split; 0 overlong nodes.
- Markup-debris re-scan of final bytes: **3 paragraphs flagged, all three
  LaTeX-notation false positives** (`|-\rangle`, `\frac{…|\mathbf x|}`,
  `\mathbb{R^{|A|}`) — zero confirmed debris in 9,979 paragraphs.
- No questions, labels, generator config, or architecture code. No freeze;
  this revision awaits independent quality review.

## 11. Revision pilot-297-r1: semantic-preservation audit (not just regex)

Regex-zero-debris ≠ semantic preservation. Findings from a stratified
20-paragraph inspection (long/chunked, list-heavy, math, table-adjacent,
confusable articles) against raw wikitext, plus full-corpus template
census:

- Prose conversion: excellent — 20/20 sampled paragraphs read as clean
  prose/lists with refs, hatnotes, captions, and file markup correctly
  gone (e.g. Everest timeline, Suva/Australia lists, Jaguar/Apple prose).
- Inline data templates: **systematically rescued** — verified on bytes:
  Rio "58 km of track" (was "of track"), Saturn "60,268 km versus
  54,364 km" (was "versus ."), UW gallery captions without filenames.
  6,854 rescues (cvt/convert/math/mvar/sub/sup/frac/lang/transl/lit/
  coord) measured in removal stats.
- Known factual-content removals (documented, by design of a text-first
  pilot): **infoboxes wholesale** — 206 articles carry `{{Infobox…}}`
  (260 opens; top: settlement 33, UNESCO 14, company 11, person 9,
  country 8, mountain 7 — populations, dates, coordinates in infoboxes
  are NOT in node text); **wikitables wholesale** (364 closed + 1
  unclosed; election results, tributary lists, records tables gone —
  prose summaries of the same facts usually remain, cell-level facts do
  not); nav/citation templates (sfn/harv 6.6k, inside already-removed
  refs); `{{chem}}` formulas (76, removed not rescued); `{{coord}}`
  rescued as bare numbers (210); birth/death-date templates (28) rescued
  only when flat, else removed.
- Reference/see-also/external-link sections excluded by design (outlinks
  retained at article level).
- Math kept as LaTeX source (readable, not rendered); `{{math}}` symbols
  rescued as plain text (electromagnetism F/q/v now present).
- Sentence segmentation remains heuristic (abbreviations); nodes carry
  `char_len` but no intra-parent offsets — anchors must be search-derived
  at QA time against node text.
- Tests: **17/17 corpus converter/offline tests pass**
  (`python3 -m unittest discover -s corpus/tests -t .`), covering
  nesting, layout captions, unclosed tables, orphan rows, headings, long
  prose without loss, sentence preservation, no-network proof (static +
  behavioral), full-pipeline determinism on fixtures, staged-output
  validation. Repo suite re-run at finalization (see report).

## 6. Measured results (pilot-247-v0 — SUPERSEDED, preserved for audit)

- Articles fetched: **247 of 500 target** (310 gaps, all HTTP 429 — see §8).
- Nodes: **109,704** total = 1 corpus + 9 clusters + 247 articles +
  6,862 sections + 21,353 paragraphs + 81,232 sentences.
- `corpus/corpus.jsonl`: **39,622,343 bytes**, canonical hash
  `ead3d771122c05e1499b06ca1393bfa4e5963bc7f532a5639554337b2d5a64f0`
  (recomputed from bytes: match). `substrate.validate_hierarchy`: **0
  errors**. `substrate.validate_group_map` (current substrate): **0 errors,
  247/247 articles mapped**.
- Raw snapshots (in-snapshot): **33,761,340 bytes** (247 files, all present,
  all parse). HTTP download: **80,619,003 bytes** of the 200,000,000 cap.
- Provenance file: 197,287 bytes at build, **199,092 bytes** after the
  metadata-only claim amendment (sha256 `62def4f1…d475fa` →
  `429432f3…87481e`; corpus content bytes untouched, hash unchanged).
- Splits (group-aware, seed `pilot-v1`): **train 174 / dev 37 / heldout 36
  articles** across 154 / 26 / 32 groups. All 30 confusable-group keys kept
  intact (never divided), but see §8: 23 of 30 groups are INCOMPLETE in the
  snapshot (members missing to 429s).
- Per-article provenance: pageid/revid/timestamp/source URL/license/
  content-sha256 present **247/247**; `split_group` present 247/247;
  redirect aliases recorded for all 9 requested≠normalized resolutions;
  pageids distinct 247/247 (no duplicate-article collapse).
- No `corpus/questions.json`, no sealed labels, no generator config were
  created by this worker. (`corpus/generator_config.json` is another
  worker's file, untouched. `corpus/__pycache__/` left as found.)

## 7. Link/contamination stats (pilot-247-v0 — SUPERSEDED, preserved for audit)

- Article-level in-corpus edges (API outlinks resolved into corpus):
  **1,222**, of which **533 (43.6%) cross split boundaries**.
- Cross-split edges are INTENTIONAL (shared searchable DAG; only QA
  supervision is disjoint) but future multi-hop question authors must treat
  chains crossing splits as a contamination lens, not assume isolation.
- Paragraph-level in-corpus `[[link]]` edges exist per paragraph node;
  sentence nodes carry none (documented choice).
- Citation-offset readiness (limitation, not a result): nodes record
  `char_len` but **no intra-parent character offsets**; future evidence
  anchors must derive spans by substring search at QA-creation time. The 24
  truncated paragraphs (§8) additionally lack their tail sentences entirely,
  so anchors must never point past node text — validate by search-hit, not
  by assumption.

## 8. Gaps, losses, and selection bias (pilot-247-v0 — SUPERSEDED, preserved for audit)

- **Acquisition shortfall: 247/500.** All 310 gaps are
  `fetch / RuntimeError: HTTPError: HTTP Error 429: Too Many Requests`
  (exact strings in `provenance.json:gaps`). No missing/invalid titles, no
  cap events (80.6 MB of 200 MB download cap used), no other error class.
  A paced resume fetched 50 further snapshots before the orchestrator
  ordered NO further network activity; those 50 files are parseable but
  **explicitly excluded** from the snapshot (not in `corpus.jsonl`,
  provenance articles, `split_map`, or the hash). They are reported, not
  used. Raw error logs preserved at `/tmp/opencode/pilot_build.log` and
  `/tmp/opencode/pilot_build2.log`; build script preserved at
  `corpus/build_pilot.py` (note: the script was further edited during the
  residue audit AFTER the snapshot — the snapshot reflects the pre-audit
  converter; the audit findings below describe snapshot bytes as built).
- **Selection bias is severe and directional.** Fetched/missing by cluster
  (candidates → fetched): confusable 121→57, geography 115→44, science
  78→37, biology 50→29, history 48→16, longtail 52→26, culture 44→15,
  medicine 27→14, misc 22→9. Only **7 of 30 confusable groups are intact**
  (apes, eclipse, london, mars, mercury, orange, peaks); the other 23 are
  broken — eight reduced to zero members in the snapshot (berlin, bigcats,
  columbia, java, rome, shell, venus, worldwars); remaining partial groups:
  amazon, apple, bears, cambridge, corona, delta, jaguar, lincoln, nile,
  paris, python, revolutions, saturn, tesla, washington).
  The 50 excluded extras would fully repair 16 broken groups and partially
  repair 2 more (rome, tesla) — structural fact for the orchestrator's next
  decision, computed from filenames only, no content converted.
- **Conversion losses in snapshot bytes** (pre-audit converter):
  24 paragraphs hard-truncated at 4,000 chars with tail text lost
  (`p:amazon_river:18:000`, `:31:000`, `p:bucharest:05:000`,
  `p:city_of_london:29:002`, `p:dissolution_of_the_soviet_union:40:001`,
  `p:eclipse_software:04:002`, `p:franklin_s_lost_expedition:21:000`,
  `p:k2:07:000`, `p:light_emitting_diode:15:000`,
  `p:mars_mythology:25:001`, `p:munich:08:008`,
  `p:my_lai_massacre:14:000`, `:15:000`,
  `p:natural_language_processing:14:000`,
  `p:orange_county_california:08:000`, `:24:001`, `p:oslo:14:002`,
  `p:red_fox:05:003`, `p:shogun:03:000`, `p:star_wars:08:000`,
  `p:taipei:07:000`, `p:tokyo:10:000`, `p:transistor:18:000`,
  `p:vienna:14:003`); markup debris in **2,936 of 21,353 paragraphs
  (13.7%)** — `[[`/`]]` remnants 2,488 (mostly File-caption fragments,
  e.g. `p:alternating_current:18:002`), template remnants 200 (e.g.
  `p:abraham_lincoln:14:000` Infobox), table remnants 266 (e.g. Munich
  election rows). The post-snapshot audit converter (in `build_pilot.py`,
  NOT applied to the snapshot) reduces confirmed debris to zero on the
  same raws — available to an authorized rebuild, not silently applied.
- Sentence segmentation is heuristic (abbreviations, LaTeX); reference/
  see-also sections excluded by design (outlinks kept at article level).
- Pilot scale and the above biases support pipeline development and
  synthetic infrastructure checks only. **No claims** of ~99% general
  evidence survival or AndroidLM comparability are made from this pilot.
- Desktop measurements only; nothing here authorizes Android performance
  claims.
