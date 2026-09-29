# Round 0 Reference Audit — AndroidLM & boar-app (replacement audit)

Status: **AUDIT COMPLETE — findings below. Round 0 NOT FROZEN** (freeze needs
pinned corpus/generator artifacts + independent review; see §9 blockers).

Worker model: `opencode/muse-spark-1.3-contributor-free` — catalog-verified
zero-cost (input 0, output 0, cache-read 0, cache-write 0, status active) via
live `tools.opencode.models` query on 2026-09-29. No nested spawning was used.
No model, corpus, or weight files were downloaded. No sealed held-out answers
were created or inspected (none exist yet).

## 0. Endpoint substitution record (mandatory)

- The prior reference worker (`opencode/nemotron-3.5-lightning-free`) completed
  without a text response and produced neither `references/` nor
  `docs/reference-audit.md`. The orchestrator log already records this as an
  execution failure, not a completed audit.
- This session re-executes the identical scope under
  `opencode/muse-spark-1.3-contributor-free`. No paid endpoint was used as a
  fallback. Machine-readable pins: `references/pins.json`.

## 1. Sources inspected (pinned)

| Repo | Remote | Pinned HEAD | Date | Code license |
| --- | --- | --- | --- | --- |
| AndroidLM | `https://github.com/Phineas1500/AndroidLM` | `ed3d51a27b0027f300e7d57ba82f4a8249c95457` ("INSTALL points at the v1.2.0 APK") | 2026-09-28 -0700 | Apache-2.0 (`LICENSE`) |
| boar-app | `https://github.com/rferrari/boar-app` | `0dda83f27a5d95094243c2d11d049172f3854144` (merge PR #15 rag-precision) | 2026-09-28 -0300 | MIT (`LICENSE`, aoair contributors) |

Method: `git clone` of both remotes to scratch space, read-only inspection of
files listed in §2. SHA-256 of key files at the pinned HEADs is recorded in
`references/pins.json`. Manifest-claimed artifact hashes (model/corpus bytes)
were **not** independently re-verified (files not downloaded) — see §8.

## 2. Exact source paths relied on

AndroidLM (all under the pinned clone):
`README.md`, `INSTALL.md`, `TESTING.md`, `NOTICE.md`, `assets/manifest.json`,
`assets/hf_dataset_card.md`, `scripts/rag.py` (pipeline prototype),
`scripts/build_corpus.py`, `scripts/build_redirects.py`, `scripts/build_df.py`,
`scripts/build_places.py`, `scripts/build_pack.py`, `scripts/finish_pack.py`,
`scripts/run_eval.py`, `scripts/eval_models.sh`, `scripts/install.sh`,
`scripts/make_sample_db.py`, `scripts/answer_pairs.py`, `scripts/ratio_grades.py`,
`app-android/README.md`, `eval/questions_vitalik.jsonl`,
`eval/LICENSE-boar-questions.txt`, `notes/2026-09-19-eval-v0.md`,
`notes/2026-09-28-vitalik-bar.md`, `notes/2026-09-28-ethereum-pack.md`,
`submission/questions.md`.

boar-app: `README.md`, `ARCHITECTURE.md`, `AGENTS.md`, `package.json`,
`src/eval/evalSet.ts`, `src/eval/evalHarness.ts`, `src/rag/retrieve.ts`,
`src/rag/pure.ts`, `src/rag/db.ts`, `src/rag/packs.ts`,
`src/models/manifest.ts`, `scripts/build-corpus.mjs`,
`scripts/build-corpus-tier.mjs`, `scripts/build-knowledge-pack.mjs`,
`docs/EVAL_QUERIES.md`, `docs/MODELS.md`, `docs/DEVICE_EVALUATION.md`,
`docs/COMPLIANCE.md`, `docs/KNOWLEDGE_PACKS.md`, `assets/corpus/corpus.json`.

## 3. Public bounty questions / benchmark methodology

- Bounty: POIDH "Build the Best Offline AI Research App for Android"
  (`https://poidh.xyz/mainnet/bounty/31`, linked from both READMEs). **VERIFIED:**
  both repos link it and describe the same bar (>50% as good as internet +
  frontier AI; ≤12 GB RAM; ≤50 GB storage; offline; GrapheneOS-compatible).
  **UNKNOWN:** live bounty-page text could not be verified — direct fetch on
  2026-09-29 returned a JS shell with no bounty content. Do not cite bounty
  wording beyond what the two repos quote.
- AndroidLM eval sets (`eval/questions_*.jsonl`, 494 questions total across
  files): general/travel/tail/obscure-subject splits plus
  `questions_vitalik.jsonl` (61 questions). Grading: **Claude-family LLM judges,
  0–10 single rubric, mostly blind pairwise** (`answer_pairs.py`,
  `ratio_grades.py`); early rounds graded from the judge's own knowledge with
  **no web checks**; the vitalik-bar round used web-checking graders. Fixed
  sampling (`temperature 0.7, top_p 0.8, top_k 20, presence_penalty 1.5,
  seed 1234` in `run_eval.py`). No calibration (ECE/Brier), no survival
  accounting, no per-stage traces — **not comparable** to our substrate metrics
  without re-grading. Their headline numbers (e.g. 64% of reference, 7.0 vs 2.6
  vs 1.7B) are **reference context only, never training data, never targets**.
- boar-app eval (`src/eval/evalSet.ts`, `EVAL_SET_VERSION = "1"`, 17 queries):
  greeting/factual/explanation/comparison/synthesis/reasoning/grounded/no-kb
  categories with `expectedKbTitles` and per-query `gradingNotes`. Harness runs
  each config on-device recording TTFT, tok/s, peak RSS, residency, retrieval
  hits (`evalHarness.ts`); grading is **manual** — there is deliberately no
  automated judge. Reproducible shape, but 17 queries is too small and too easy
  to serve as our benchmark.
- **Leakage rule (binding):** all public bounty/AndroidLM/boar questions are
  **development/reference only**. They must never be training examples and must
  never appear in our sealed held-out set.

## 4. Corpus: versions, licenses, acquisition, size

AndroidLM (authoritative per `assets/manifest.json`, `hf_dataset_card.md`):
- `wiki.db` 21.3 GB — English Wikipedia via **FineWiki August 2025**
  (`HuggingFaceFW/finewiki`, 36 GB shards), tiered by pageviews (2M most-read
  in full per README; dataset card says 1.87M in full of 6.05M articles; 38.9M
  passages, 31.9M BM25-indexed), + Wikipedia redirect table (Sep 2026 dumps) +
  pageviews. **CC BY-SA 4.0.** Build: `build_corpus.py` (zstd blocks, FTS5
  `detail=full`, porter tokenizer), ~4 h on 4 cores, ~80 GB disk needed.
- `wiki_df.db` 1.7 MB — df word counts derived from the index (same license).
- `voyage.db` 0.3 GB — English Wikivoyage Sep 2026, 34,004 guides. CC BY-SA 4.0.
- `places.db` 2.9 GB — 21.1M places: Overture Maps 2026-09-23.1
  (CDLA-Permissive-2.0; Foursquare Apache-2.0; AllThePlaces CC0) + OSM diet tags
  (ODbL 1.0) + GeoNames (CC BY 4.0) + Wikivoyage listings. Published under
  **ODbL 1.0** (`rammingaway/androidlm-places`).
- `ethereum.db` 19 MB, shipped in APK — EIPs/ERCs + consensus specs (CC0),
  ethereum.org (MIT), Upgrading Ethereum (CC BY-SA 4.0 → pack as a whole
  CC BY-SA 4.0), NIST publications (US public domain).
- Full corpora need ~37 GB download + adb push; **infeasible and unnecessary**
  for Round 0 on this machine. The repo provides `make_sample_db.py` (named
  articles + N random, same schema/chunk ids, seed 11) — the right pattern for
  a small local corpus, but it requires the full `wiki.db` as input, which we
  do not have.

boar-app (per `docs/MODELS.md`, `src/models/manifest.ts`):
- Bundled `assets/corpus/corpus.json` 193 KB — ~300 Wikipedia summary extracts
  (CC BY-SA 4.0, per-article `source` URL kept for citation); Standard +1,000
  topics (~600 KB); Full +4,000 more (~2.5 MB total); optional
  `wiki-vital5.sqlite` ~164 MB (~50k Vital Articles intros, FTS5 + int8
  embeddings, sha-pinned in manifest). Built dev-machine-side via
  `build-corpus*.mjs` (MediaWiki API) — small, fast, reproducible pattern.
- **This is the feasible Round 0 template** (see §7).

## 5. Generator / runtime dependencies

- AndroidLM generator: `unsloth/Qwen3.6-35B-A3B-GGUF`, file
  `Qwen3.6-35B-A3B-UD-Q2_K_XL.gguf`, 12.3 GB, sha
  `96b9c0af…70dad7` (manifest claim), Apache-2.0. Runtime: BigMoeOnEdge
  expert-streaming engine on llama.cpp (+ ik_llama.cpp ARM kernels via
  `patches/`), Pixel 8 Pro measured: ~7.9 GB RAM, 4–6 tok/s, ~28 s load.
  **Wholly unsuitable as our fixed Round 1 generator** (12 GB file, MoE
  streaming engine, phone-only performance claims).
- boar-app generators (all GGUF via `llama.rn` = llama.cpp bindings):
  Qwen2.5-1.5B-Instruct Q4_K_M (~0.99 GB, Apache-2.0, required `fast` role),
  Phi-3.5-mini Q4_K_M (~2.4 GB, MIT), Qwen2.5-7B (~4.7 GB), LFM2.5-8B-A1B MoE
  (~5.2 GB, LFM license), Gemma 4 E4B (~5.2 GB); embedding bge-small-en-v1.5
  Q8 (~37 MB, MIT). Retrieval: SQLite FTS5 + brute-force cosine over float32
  embeddings; pack prefilter is keyword→400 candidates. Measured on Xiaomi
  (Dimensity 8300): Qwen-1.5B ~11–18 tok/s class, Phi ~4 tok/s.
- Our substrate needs **zero third-party deps** today; any generator must be a
  separately pinned artifact (`corpus/generator_config.json`), not a substrate
  dependency.

## 6. Reproducibility and comparability limitations

1. AndroidLM grades are Claude-judge scores with known grader-family bias
   (reference and graders same family), single-run noise (their own A/B notes
   show ±7 preferences/58 on re-grade), and mixed protocols across rounds.
   **Do not compare our metrics against their scores.**
2. AndroidLM phone-vs-server equivalence was spot-checked on small samples
   (e.g. 24 obscure questions, 84 vs 85 key facts) — indicative, not a license
   to claim Android performance from desktop runs. **Our rule stands: desktop
   measurements are desktop measurements.**
3. boar-app has no automated judge; its 17-query set is a smoke harness, not a
   benchmark. Its per-row telemetry schema (TTFT/load/RSS/residency/retrieval
   hits) is, however, a good model for our trace fields.
4. Neither repo does threshold calibration, evidence-survival accounting, or
   seeded frozen splits — all three are ours to enforce, not theirs to inherit.
5. Corpus mismatch is total: 21 GB tiered Wikipedia + places + packs
   (AndroidLM) vs 300-summary bootstrap (boar). Any "published AndroidLM
   results where reproducible/comparable" comparison must be explicitly scoped
   as reference context with the corpus delta stated, never as a controlled
   baseline.

## 7. Recommendations

### Feasible real Round 0 corpus (small, local, licensed-clean)

- **Do not vendor either repo's corpus.** wiki.db (21 GB) is too large to
  download/build here; boar's `corpus.json` is too small/easy and keyed to
  their demo questions.
- **Recommended:** build `corpus/corpus.jsonl` with N = 500–1000 short
  Wikipedia-derived documents (lead-section extracts, ~1–3 KB each, total a few
  MB), fetched once via the MediaWiki API exactly as boar's
  `scripts/build-corpus.mjs` does, with per-document `source` URL retained for
  CC BY-SA 4.0 attribution and citation. Record fetch date, title list, script
  revision, and corpus SHA-256 in the freeze manifest. Keep the substrate's
  canonical JSONL + hierarchy mapping (`article > section > paragraph >
  sentence`) on top of it.
- License handling: corpus artifact as a whole under **CC BY-SA 4.0** with
  source URLs per chunk (same pattern as boar `source` field); keep
  `NOTICE.md`-style attribution. Never mix ODbL places data into it.
- Article-disjointness (see split procedure) must be designed in from the
  start: reserve whole articles for dev vs held-out.

### Fixed small local generator

- **Recommended:** `bartowski/Qwen2.5-1.5B-Instruct-GGUF`,
  `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`, 986,048,768 bytes, sha256
  `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370`
  (values per boar `src/models/manifest.ts`; verify by download hash before
  freeze), **Apache-2.0**, served via local llama.cpp/`llama-server`.
  Rationale: smallest Apache-2.0 instruct model both repos actually measured
  on phones; ~1 GB is downloadable and desktop-runnable here; instruction
  template ships in the GGUF.
- Pin in `corpus/generator_config.json`: repo, file, bytes, sha256, quant,
  runtime (`llama.cpp` version + server flags), chat template, fixed prompt
  hash, sampling (`temperature/top_p/top_k/seed`, mirroring AndroidLM's
  `run_eval.py` precedent), `max_tokens`, context window. Any change ⇒
  re-freeze. Fallback if the file proves unusable: Phi-3.5-mini Q4_K_M (MIT,
  ~2.4 GB) — larger, slower, record the substitution.
- **Do not use** Qwen3.6-35B-A3B, 7–8B models, or any MoE for Round 1: they
  confound retrieval quality with generator capability and exceed practical
  local iteration cost.

### Leakage-resistant split procedure

1. Partition at the **article level first**: assign whole corpus articles to
   train/dev/held-out (e.g. 70/15/15 by seeded hash of article id) *before*
   deriving any questions, so no training question shares a source article
   with a dev or held-out question.
2. Derive training questions only from train articles (synthetic/template QA
   with known evidence spans; neighboring/sibling passages as hard negatives).
   Derive dev questions from dev articles. Held-out questions + labels go
   straight into `corpus/heldout_labels.sealed.json`, withheld from dev
   workers per the custodian protocol.
3. Public bounty/AndroidLM/boar questions: **dev/reference only**, never
   training, never held-out; keep them in a separate file with provenance tags.
4. Record split seed + algorithm + article assignments in the run manifest;
   re-running with the same seed must reproduce identical splits (substrate
   `splits.py` already provides the question-level mechanism — extend the
   freeze to include the article map).

## 8. Verified vs unknown

- VERIFIED (read at pinned HEADs): repo structure, pipeline logic
  (`rag.py --mode auto`: plan ≤4 titles → redirect resolution → lead+sections
  → BM25 backfill; boar hybrid FTS5+vector with term-coverage gate),
  all eval-set sizes and formats, grading scripts' existence and judge setup,
  manifest byte counts/URLs/licenses, runtime stacks, file hashes in
  `references/pins.json`.
- NOT independently verified (no downloads performed, per task constraints):
  model/corpus byte/sha claims in either manifest, HF dataset contents,
  on-device latency/RAM figures quoted in either README, live bounty-page text
  (JS-only fetch result), FineWiki shard contents.
- UNKNOWN / out of scope: BigMoeOnEdge engine internals beyond the documented
  interface; GeoNames/Overture per-record licensing edge cases (covered at the
  dataset level by ODbL publication, sufficient for our purposes since we
  vendor no places data).

## 9. Blockers and handoff

- **No blockers produced by this audit.** Findings + pins + recommendations are
  complete and written.
- Freeze still requires (substrate lead / orchestrator, not this worker):
  1. `corpus/corpus.jsonl` built per §7 + hash; 2. `corpus/questions.json`;
  3. `corpus/heldout_labels.sealed.json` (withheld from dev workers);
  4. `corpus/generator_config.json` (recommendation §7; hash-verify the GGUF
  before pinning); 5. independent review PASS of substrate + this audit.
- Suggested review checks on this audit: confirm HEAD hashes against the live
  remotes, confirm no held-out material was created, confirm every factual
  claim traces to a §2 path or is labeled UNKNOWN.
