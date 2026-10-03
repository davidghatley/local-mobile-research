# Round 1 Baselines — Hypothesis and Readiness Report (Baseline Lead)

Status: MISE-EN-PLACE READINESS ONLY. No implementation, no training, no private
evaluation, no synthetic data. Frozen substrate: tag `round0-freeze-r1`
(commit `a0e753410dfc1ba3f5ae37e0c187b943fe1faa49`).
Worker endpoint: `openrouter/qwen/qwen3.8-27b:free` (verified zero-cost).
No subagents spawned. No paid fallback used.
All measurements and predictions below are DESKTOP. No Android or on-device
claim may be derived from any of this.

Companion file: `experiments/baselines/PLAN.md` (the ordered how, with gates).
This file is the spec: the four baseline systems at implementation level,
pinned model identities, exact tie-breaking, and the preregistered reading of
what each system is expected to do.

## 0. Why baselines exist (and the kill condition)

Neural cascade teams are already building. If the simple systems are weak, a
complex architecture wins by default and the tournament is decoration. These
baselines must therefore be specified strongly enough that complexity has to
be earned. The load-bearing statement of this report:

> **KILL CONDITION.** If baseline B4 (deterministic BM25 + fixed generator,
> no reranker, no semantic model) matches the full cascade on
> required-evidence completion and final evidence recall on dev +
> shadow-dev within Wilson-CI overlap, at a tiny fraction of its storage
> and latency, the cascade is unnecessary on this corpus and that is the
> headline result.

Every number below is labelled: **VERIFIED** (checked against a primary source
on the date given), **DERIVED** (arithmetic from verified facts), **ESTIMATE**
(to be replaced by a `substrate.telemetry` measurement in PLAN.md), or
**PREDICTION** (an honest expectation, not a result). Predictions are made
now, before any neural team is finished, so they cannot be reshaped after
seeing the cascade's numbers.

## 1. Shared corpus facts (VERIFIED locally against frozen artifacts)

| Fact | Value |
|---|---|
| Core corpus | `corpus/corpus.jsonl`, revision `pilot-297-r1`, sha256 `98e1237e74a40574ed9a41104bc7ae9612cfbed656e2240cea6ee9d5e98d5f64`, 43,876,251 B |
| Core nodes | 113,951 = 1 corpus root + 9 clusters + 297 articles + 8,146 sections + 9,979 paragraphs + 95,519 sentences |
| Paragraph words (core) | 2,103,768 total, mean 210.8 / paragraph |
| Section text | headings only (mean 2.1 words); exactly 297 sections carry the literal placeholder text `(lead)` (one per article) |
| Scale tier | `corpus/scale/distractor.jsonl` (sha256 `516463e340de8c53…` per `scale_build_manifest.json`), 940 articles, 26,630 paragraphs, 5,494,137 words, mean 206.3 / paragraph; 110 redirect-stub articles (102 stub paragraphs of the form `REDIRECT <target>`) |
| Merged core+scale | 36,609 paragraph documents, 7,597,905 words |
| Worker-visible questions | 206 items (train 60 / dev 59 / shadow_dev 87), `corpus/questions.json` only |
| Support atoms | leaf sentence nodes; retrieving an ancestor paragraph SATISFIES support (`eval/support.py::covers`, ancestry-aware) |
| Packet contract | `build_packet` ranked-prefix, strict 1000-token cap, `exact=True` with the pinned generator tokenizer, no partial-span truncation (`substrate/evidence.py`) |
| Fixed generator | `qwen25-1.5b-q4km-fixed-v1` (Qwen2.5-1.5B-Instruct Q4_K_M GGUF, pinned by the generator owner; shared by ALL architectures; ~1 GB artifact, excluded from per-baseline cost because identical everywhere) |

Scale-tier status (governing): `docs/scale-method.md` — the 940 articles are
distractor material, never evidence; recall-style metrics range over known
core support only; `eval/scale_adjudication.py` is NOT yet consumed by
`eval/metrics.py` (accepted risk 6). Consequence for baselines: the PRIMARY
index is core-only (9,979 docs); the merged core+scale index (36,609 docs) is
a SEPARATE declared measurement (PLAN.md Phase 5), reported through
`eval/scale_analysis.compare_scale_tiers` with `unjudged_top_k` and
`limitations` attached. Both configurations are specified here because the
brief requires indexing cost at BOTH the 297-article and 940-article scale
tiers.

## 2. Shared pipeline contract (identical across all four baselines)

1. **Retrieval unit: the paragraph node** (`kind == "paragraph"`).
   - Justification (vs alternatives):
     - **Not sentence level** (95,519 docs): support atoms are sentence leaves,
       but the packet packs WHOLE nodes only (no partial-span truncation);
       22-word fragments degrade the fixed 1.5B generator (anaphora, missing
       context), and BM25 over 95k docs makes top-K recall harsher
       (K of 95,519 vs K of 9,979) for the same evidence budget.
     - **Not article/section level**: an article's full text is thousands of
       tokens; the strict 1000-token cap would hold 0–2 articles, and
       section nodes carry no prose.
     - Paragraph is the smallest self-contained context that fits the budget
       (mean 210.8 words ≈ 240–280 generator tokens), and ancestor coverage
       makes paragraph retrieval satisfy leaf-sentence atoms by construction.
   - Consequence: a required sentence "survives" a stage iff its host
     PARAGRAPH is in that stage's candidate set. All survival metrics below
     are stated at paragraph granularity.
2. **Query surface**: `QueryInput(question_id, text)` via
   `to_model_query` ONLY. No split / question_type / meta / provenance may
   reach any component (`assert_no_label_metadata` fail-closed).
3. **Packet packing policy (shared, deterministic)**:
   - Input to packing = the system's final ranked paragraph list.
   - Spans are whole paragraph nodes (`EvidenceSpan(node_id, node.text)`,
     offsets None, `hop=0`).
   - **Per-article cap: at most 3 spans from one article** per packet
     (deterministic skip; prevents one article's strong lexical match from
     eating the entire budget on multi-hop/comparison items). Ablation
     without the cap is recorded, not substituted.
   - `build_packet(question_id, spans, exact=True, tokenizer=<pinned
     generator tokenizer>, cap=HARD_EVIDENCE_TOKEN_CAP)`; the strict
     ranked-prefix semantics (first overflow stops; empty packet +
     `truncated=True` when the first span alone overflows) are the
     substrate's, not ours.
   - Expectation (PREDICTION): packets hold ~3–4 paragraphs.
4. **Sufficiency**: `decide_default` (the safe floor) for ALL four baselines.
   No tuned sufficiency gate: that is complexity, and the floor must not
   hide behind one. Consequence (stated plainly): unanswerable items
   (nonempty packet → "generate") produce `unsupported_generation`; that is
   the honest floor behavior and is reported as such.
5. **Generation**: the pinned fixed generator via
   `substrate.evidence.run_question` — the ONLY path to the generator. No
   prompt variation, no sampling variation, no generator tuning (the
   tournament is retrieval/evidence, not generation).
6. **Regime B**: the baselines use NO synthetic training or adaptation data
   (BM25 is untuned per §3; static and reranker are off-the-shelf pins; no
   fine-tuning anywhere). Therefore Regime A ≡ Regime B BY CONSTRUCTION and
   the 21-document exclusion list
   (`substrate.query.worker_regime_b_exclusions()`) is vacuously satisfied.
   The 21 articles REMAIN in the query-time retrieval corpus (verified
   behavior: they are excluded from adaptation data only). No Regime
   metadata ever enters a retriever. This is recorded so the A/B protocol
   still applies to the baselines without any work: both regime runs produce
   byte-identical outputs.
7. **Seeds**: no component uses randomness. The master seed and
   `derive_seed` derivation are logged in the run manifest (contract §0)
   even though they are unused; any discovered randomness is a bug.
8. **Trace**: one `StageRecord` per stage (names: `bm25`, `static_union`,
   `rerank_68m`, `packet` as applicable) with `candidate_ids`, raw `scores`,
   `score_kind`, `ThresholdPolicy` (v0: top-K only — `threshold=None`,
   `top_k` set, `calibration_method="none_ranking_only"`, declared
   `interpretation` per §5.3 — never a probability claim on a
   logit), `latency_ms`, `peak_rss_mb`, `model_loading_latency_ms`,
   `inference_latency_ms`; `None` = explicitly not measured.
   `RetrievalOutcome.storage_bytes` only when `storage_manifest` is
   `complete=true`.

## 3. B1 — BM25 / lexical only (exact specification)

A vague "BM25" is not a specification. Every parameter is pinned below.
Deviations are legal only as recorded dev-selected ablations (PLAN.md
Phase 4), never as silent substitutions.

### 3.1 Unit of retrieval and corpus preprocessing

- **Document set**: every `kind == "paragraph"` node. Core: N = 9,979.
  Merged scale tier: N = 36,609. Document order = byte order of the pinned
  corpus file (core `corpus/corpus.jsonl`; scale `corpus/scale/distractor.jsonl`);
  document index `i` is the position in that order. Deterministic by pin.
- **Index document string** `D(p)` (the ONLY text BM25 sees for paragraph `p`):

  ```
  D(p) = article_title + " " + section_heading + " " + paragraph_text
  ```

  with exactly one exception: if the parent section's text (stripped) is the
  literal placeholder `(lead)` — the converter's lead-section marker, present
  in exactly 297 sections (VERIFIED) — the heading is OMITTED:
  `D(p) = article_title + " " + paragraph_text`.
  - Title = `text` of the paragraph's article ancestor, byte-exact.
  - Heading = `text` of the paragraph's section parent, byte-exact.
  - Paragraph text = `text` of the paragraph node, byte-exact (the frozen
    corpus is already cleaned; no re-cleaning, no whitespace folding beyond
    tokenization).
  - Why heading prefix: the title + heading put the entity and topic terms
    into every paragraph of that article, concentrating candidates in the
    right article for entity-style questions while leaving within-article
    ranking to paragraph content. It is corpus-derived (no labels) and
    identical for every architecture that uses BM25, so it cannot favour us.
  - Why omit `(lead)`: it is a construction artifact, not prose, and it would
    inject the content word "lead" into 297 documents. One deterministic,
    documented exception; applied identically at index time and recorded in
    the index manifest (count of affected docs = 297, asserted in a test).
- **Sentence and section nodes are never retrieved** (headings enter only via
  `D(p)`); article nodes are never retrieved (title enters only via `D(p)`).

### 3.2 Tokenizer (index and query, identical)

```
tokenize(text):
  1. u = unicodedata.normalize("NFKC", text)
  2. c = u.casefold()
  3. return all matches of the regular expression [a-z0-9]+ in c
```

- Stdlib only (`re`, `unicodedata`) — zero third-party dependencies, zero
  version drift; two implementations that follow this produce byte-identical
  token streams.
- **Stemming: NONE.** Justification: (a) the corpus is encyclopedic and
  questions mention entity names and exact terms; stemmer collisions
  (e.g. `corona`/`coronavirus`-adjacent stems, proper-noun suffix stripping)
  do more harm than inflectional variance on a fixed 297-article collection;
  (b) a small corpus makes IDF collisions from over-stemming more damaging,
  not less; (c) third-party stemmers (porter/snowball variants) are version
  drift between implementations; (d) Round 0's recorded lesson (a one-letter
  spelling-variant hard negative evaded every lexical check) shows lexical
  robustness has limits that stemming does not touch. A stemming ablation is
  legal only as a recorded dev-selected variant, off by default.
- **Stopwords: NONE.** No stopword list of any kind. Justification: a fixed
  list is another version-pinning surface, and on a small collection
  terms like "was"/"which"/"does" carry weak-but-real signal on comparison
  and multi-hop question phrasings. Terms present in (nearly) every document
  get `idf ≈ ln((N−0.5)/(N+0.5)) ≈ 0.5/N` and contribute ~nothing
  automatically — the IDF, not a list, does the stopping. No IDF floor, no
  document-frequency threshold; a term in all N documents still has a
  defined, tiny positive idf and stays in the index.

### 3.3 Scoring (exact formula, double precision)

Standard Okapi BM25, natural logarithm, IEEE-754 double throughout:

```
N        = number of index documents (9,979 core; 36,609 merged)
|d_i|    = number of tokens of D(p_i)  (computed at index time)
avgdl    = (1/N) * Σ_i |d_i|           (index-time constant, recorded)
df(t)    = number of documents containing t
idf(t)   = ln((N - df(t) + 0.5) / (df(t) + 0.5))
tf(t,i)  = term frequency of t in D(p_i)
score(q, d_i) = Σ over UNIQUE query terms t, in first-occurrence order:
                    idf(t) * ( tf(t,i) * (k1 + 1) )
                             / ( tf(t,i) + k1 * (1 - b + b * |d_i| / avgdl) )
k1 = 1.2
b  = 0.75
```

- **k1 = 1.2, b = 0.75** (VERIFIED as the canonical Robertson/Zurick defaults;
  PREDICTION: adequate for a ~210-word-document collection; a dev-selected
  grid `{k1 ∈ {0.9, 1.2, 1.5}, b ∈ {0.5, 0.75}}` may be run ONLY as a
  recorded ablation — the frozen baseline values remain 1.2 / 0.75).
- Query-side: tokenize `QueryInput.text`; collapse to UNIQUE terms in
  first-occurrence order (query-term multiplicity contributes ONCE — a
  pinned, documented deviation from Lucene-style multiplicity counting,
  negligible for short questions, exact for implementations).
- Documents with no overlap with the query have score 0 and are NOT ranked
  (they are not "ties at zero"; they are outside the positive set).
- **Stage-0 candidate set: top K = 500** documents by the total order of
  §6 (matches the cascade team's stage-0 K for direct comparability).
  If fewer than 500 documents have positive overlap, the candidate set is
  all positive documents.
- **Recall grid (custodian-scored)**: K ∈ {10, 50, 100, 200, 500}, reported
  as required-paragraph recall@K per item and per split, plus
  `stage_coverage` at K = 500.

### 3.4 Index representation and determinism

- Packed binary artifact (stdlib `array`/`struct`): terms sorted by UTF-8
  byte order; each term records `df` and a postings array of
  (doc_index: uint32, tf: uint16) pairs in doc-index order; plus a header
  carrying `N`, `avgdl`, corpus sha256, revision, spec hash. JSON export for
  audit. The binary is the artifact; its sha256 goes in the run manifest
  (a missing/perturbed index blocks any run — substrate discipline).
- **Index size (ESTIMATE, replace with `storage_manifest`)**:
  core ≈ 15–40 MB; merged ≈ 60–160 MB. (2.1 M core postings ≈ 13 MB at
  6 B/pair, before term strings and overhead.)
- **Index build time (ESTIMATE)**: core 10–120 s pure-Python; merged ≈ 3.6×.
- **Query latency (ESTIMATE)**: < 10 ms per query (a few thousand posting
  operations); class: MILLISECONDS. This is the cost bar.
- **RAM resident (ESTIMATE)**: 25–80 MB (packed arrays + Python overhead).

## 4. B2 — Lexical + static semantic (pinned, and the honest read)

### 4.1 The pinned model (VERIFIED via Hub API, 2026-10-03)

| Field | Value |
|---|---|
| Repo | `sentence-transformers/static-retrieval-mrl-en-v1` |
| Revision (main head, re-resolve at implementation) | `f60985c706f192d45d218078e49e5a8b6f15283a` |
| Last modified | 2025-01-17T10:54:17Z (stable ≥ 20 months at observation) |
| License | apache-2.0 (API tag + card) |
| Architecture | a single `sentence_transformers.models.StaticEmbedding` module (`modules.json`, VERIFIED by reading it) — zero transformer, verified from primary source |
| Weights | `0_StaticEmbedding/model.safetensors` = **125,018,208 B** (VERIFIED, LFS oid `164fc63ee9f9267be7378fcbd7df99d09788a2f45244c92aa99ae5a574925716`) |
| Tokenizer | `0_StaticEmbedding/tokenizer.json` = **711,396 B** (VERIFIED; BERT-uncased WordPiece fast tokenizer) |
| Table geometry | DERIVED: 125,018,208 B − 96 B safetensors header = 30,522 × 1024 × 4 B. 30,522 = BERT-uncased vocab size; 1024 = `embedding_dim` in the repo's own `train.py` (VERIFIED by reading `train.py`: `StaticEmbedding(AutoTokenizer.from_pretrained("google-bert/bert-base-uncased"), embedding_dim=1024)`, trained with MNRL + Matryoshka dims `[32,64,128,256,512,1024]`). PLAN.md Phase 2 asserts the loaded tensor shape `(30522, 1024)` fp32; mismatch = STOP |
| ONNX variants (VERIFIED sizes) | `onnx/model.onnx` 125,022,572 B; `model_fp16.onnx` 62,513,753 B; `model_int8.onnx` = `model_quantized.onnx` = `model_uint8.onnx` = **31,259,319 B** (the genuinely reduced variants); `model_q4f16.onnx` 62,513,772 B; `model_q4.onnx` = `model_bnb4.onnx` = 125,022,591 B — same size as fp32: NOT reduced, do not use for storage claims |
| Provenance caveat | Hub API `downloads: 0` — a low-usage release. Quality claims below rest on its self-reported model-index (unverified in our harness until Phase 4) |
| Self-reported NanoBEIR mean (model-index, card) | cosine ndcg@10 0.503, mrr@10 0.548, map@100 0.420, recall@10 0.573 |

Revision status: this is a moving-head observation, not a freeze pin, in the
same sense as the ettin repos. It has been stable since 2025-01-17, which
makes it the most stable pin in this report. The implementer MUST re-resolve
the SHA and record the weight-file sha256 in the run manifest before use
(PLAN.md Phase 0). No weight bytes were downloaded for this report.

### 4.2 Exact retrieval semantics (pinned)

- Document input = the SAME `D(p)` string as B1's index document (one
  canonical document string, two channels — no re-derivation, no divergence
  between the two retrieval channels).
- Tokenization: the model's own fast tokenizer, `encode_batch(texts,
  add_special_tokens=False)`, no padding (VERIFIED semantics: the
  `StaticEmbedding` class in sentence-transformers 3.3.0 — the version the
  repo was built with per `config_sentence_transformers.json` — tokenizes
  exactly this way).
- Embedding: mean over the token-embedding rows (the class is an
  `nn.EmbeddingBag`, default mode = mean), dimension 1024, NO L2
  normalization inside; retrieval score = cosine = inner product of
  L2-normalized vectors (`config_sentence_transformers.json`:
  `similarity_fn_name = "cosine"`).
- **No truncation**: `max_seq_length = inf` for this module (VERIFIED from
  source) — full `D(p)` is embedded; longest core `D(p)` is well under any
  practical limit.
- **Dimension choice**: full 1024 (default). MRL truncation to 512/256/128
  halves/quarters/eighths vector storage at unknown quality cost on THIS
  corpus —
  recorded as an option, off by default; any truncation requires a recorded
  dev quality check.
- **Quantization choice**: reference = fp32 safetensors via
  sentence-transformers 3.3.0 (the pinned build path). `onnx/model_int8.onnx`
  (31,259,319 B) is a deployment variant requiring the same parity gate as
  §5.4.
- Static channel candidate set: top 500 documents by cosine over ALL N
  paragraph documents (no threshold; the cosine can be ~0 or negative).

### 4.3 Fusion rule (B2 stage-0 set)

```
union      = BM25 top-500  ∪  static top-500          (≤ 1000 docs)
r_bm25(c)  = 1-based rank of c in the BM25 total order, or 501 if c is absent
r_static(c)= 1-based rank of c in the static total order, or 501 if c is absent
fused(c)   = r_bm25(c) + r_static(c)                  (integer, exact)
rank by (fused ascending, node_id ascending)          → B2 stage-0 list
```

Borda-sum over ranks is exact integer arithmetic — the only fusion rule that
is bit-exactly reproducible across implementations without floating point.

### 4.4 Indexing cost at the two tiers (weights vs index, dimensions, quantization)

Document-vector cache (the per-document static embeddings, the only
per-tier artifact):

| Tier | Docs | fp32 vectors | int8 vectors |
|---|---|---|---|
| Core 297 (9,979) | 9,979 | 9,979 × 1024 × 4 B = 40,873,984 B (DERIVED, ≈ 39.0 MiB) | 10,218,496 B (≈ 9.75 MiB) |
| Merged 940 (36,609) | 36,609 | 36,609 × 1024 × 4 B = 149,950,464 B (DERIVED, ≈ 143.1 MiB) | 37,487,616 B (≈ 35.7 MiB) |

Weights (tier-independent): fp32 table 125,018,208 B (VERIFIED) or int8 ONNX
31,259,319 B (VERIFIED). Tokenizer 711,396 B (VERIFIED).

Indexing compute (ESTIMATE, measured in Phase 2): the core `D(p)` strings
hold 2.10 M words ≈ 2.3–2.7 M WordPiece tokens (each title/heading adds a
few); every token is a table lookup plus a 1024-dim accumulate, so ≈
2–3×10⁹ accumulates (order: a few GFLOP) → seconds to a minute on desktop
numpy/torch (fp32 table, CPU). Merged tier ≈ 7.60 M words → ≈ 3.6× the core
time. Query-side compute: embed ~25 query tokens (≈
microseconds–1 ms) + 9,979 × 1024 inner products ≈ 10.2 M mults → ~5–20 ms
numpy (ESTIMATE); merged ≈ 4× the dot-product work. "Near-zero query
compute" is thus TRUE in the sense that no neural forward pass runs at query
time — only table lookups and one GEMV — but it is NOT free: ~10–50 ms/query
plus 125 MB–165 MB resident.

### 4.5 The honest read (stated now, before the neural team is finished)

**PREDICTION: the static stage adds little to nothing over well-specified
BM25 on this corpus.** Expected B2−B1 delta in final completion: 0–2 points,
probably inside the Wilson CIs at n = 59/87 (accepted risk 2: no power
calculation exists). Reasons, in order of weight:

1. **Question–corpus lexical overlap is high.** The 206 worker-visible
   questions are generated from this corpus's own text (evidence atoms are
   byte-exact corpus sentences). Entity terms, dates, and named facts recur
   verbatim; that is precisely the regime where tuned BM25 with heading
   context is strongest.
2. **The static model is a hashed bag-of-words with mean-pooled learned
   embeddings** — a smoothed, learned tf-idf. It wins on synonymy/paraphrase
   robustness, but its training mix (gooaq, msmarco, squad, s2orc, paq,
   trivia-qa, all-nli, miracl, mldr, mr-tydi — VERIFIED from `train.py`)
   is generic web/academic QA, not Wikipedia factoids over a 297-article
   entity set. Its self-reported NanoBEIR ndcg@10 (0.503) is below even the
   17M ettin CROSS-ENCODER (0.673) and far below a 68M cross-encoder
   (0.690) — weak evidence, directionally, that a cheap semantic channel
   will not out-punch lexical matching at K = 500 of 9,979 docs.
3. **The heading prefix pushes both channels in the same direction.**
   Because B2 embeds the same `D(p)` (title + heading + paragraph), the
   static channel's ranking is also entity-term-dominated, which reduces
   the disjoint recall available to the union.
4. **Cost asymmetry.** 125 MB fp32 (or 31 MB int8) + a second runtime +
   40.9 MB / 149.9 MB of vector cache, in exchange for a predicted 0–5
   points of stage-0 disjoint recall that must then survive the ~4-slot
   packet budget to matter at all.

What would change this read: a MEASURED static-disjoint recall (host
paragraphs whose required evidence the static channel ranks ≤ 500 but BM25
ranks > 500, or not at all) of ≥ ~5% of dev/shadow-dev required
paragraphs. That measurement is preregistered as the arbiter (PLAN.md
Phase 2 step 4). **If it does not fire, the recorded finding of Round 1 is:
the cheapest available semantic channel adds nothing measurable over
specified BM25 on this corpus — a prior that any cascade's stage-1 semantic
value must also beat, at 5–100× the storage.**

## 5. B3 — One strong reranker as the expensive-but-simple ceiling

### 5.1 Pinned model (VERIFIED via Hub API, 2026-10-03)

| Field | Value |
|---|---|
| Repo | `cross-encoder/ettin-reranker-68m-v1` |
| Revision (main head, re-resolve at implementation) | `d166fa88ddde3c42bc3ee92f7df476d941c8204a` |
| Last modified | 2026-05-19T13:59:10Z (stable ≥ 4.5 months at observation) |
| License | apache-2.0 (API tag + card) |
| Params | 68,144,640 F32 (Hub safetensors metadata, VERIFIED) → `model.safetensors` ≈ 272,578,560 B (DERIVED = params × 4; exact bytes + sha256 recorded at download) |
| Repo `usedStorage` | 1,845,309,911 B (all files incl. every ONNX/OpenVINO variant, VERIFIED — NOT the deployment size) |
| Architecture | ModernBERT encoder, single-logit head (MSELoss, raw logit — NOT a probability); `score_kind="logit"` everywhere; `max 7999 tokens` per card (never binding on ~250-token paragraphs) |
| Self-reported NanoBEIR mean (model-index, card) | map 0.635, mrr@10 0.750, ndcg@10 0.690 |
| Why 68M and not 17M as the ceiling | The cascade team's OWN refutation baseline is "68M applied to the full Stage-0 set" (their §1/§12); the ceiling must be the strongest single member of the official `-v1` line that still fits a mobile-class budget story, so the cascade's final stage is not winning by being the only 68M in the building. 17M is separately pinned below as the cheap single-reranker data point; 150M is recorded as the stronger alternative if 68M-alone proves too weak to be a meaningful bound (not pinned here: same revision line, one Hub lookup away, no extra risk) |

**Peer cross-check (recorded):** the peer ettin-cascade team reports the same
2026-10-03 head SHAs for 17m (`9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6`),
32m (`b33e5ceb5110773ea9cf5e00c9bedc83a8c2afdd`) and 68m
(`d166fa88ddde3c42bc3ee92f7df476d941c8204a`). My independent Hub API
observation of all three repos on 2026-10-03 returns EXACTLY these SHAs.
**No disagreement to record.** All three remain UNPINNED moving heads;
re-resolve + weight sha256 at implementation (PLAN.md Phase 0).

Also pinned, for the record: `cross-encoder/ettin-reranker-17m-v1` @
`9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6` (apache-2.0, 16,797,440 F32
params, usedStorage 455,213,212 B, NanoBEIR ndcg@10 0.673 self-reported) —
the peer team's stage-1 model, usable by the orchestrator as a
"single tiny reranker" baseline; and `cross-encoder/ettin-reranker-32m-v1` @
`b33e5ceb5110773ea9cf5e00c9bedc83a8c2afdd` (31,883,136 F32, usedStorage
863,597,989 B).

### 5.2 The peer's `model_qint8_arm64.onnx` claim — verification result

**VERIFIED AT FILE-LISTING LEVEL, NOT EXECUTED.** The 2026-10-03 Hub file
listings for 17m, 32m AND 68m each contain `onnx/model_qint8_arm64.onnx`
(siblings: `model.onnx`, `model_O1…O4.onnx`, `model_qint8_avx512.onnx`,
`model_qint8_avx512_vnni.onnx`, `model_quint8_avx2.onnx`; all three repos
also ship `openvino/` full + qint8 variants). The peer team's claim is
TRUE. What remains UNVERIFIED, exactly as the peer team states: no inference
has been run in any runtime for this report, ARM/Android execution is
unmeasured, and quantized-quality parity (qint8 vs fp32 rankings) is an
implementation-time measurement (PLAN.md Phase 3 step 3). The on-disk bytes
of the arm64 artifact are recorded at download.

### 5.3 Pipeline and score semantics

```
B1 stage-0 (BM25 top-500)
  → score ALL 500 with the 68M cross-encoder
     query input  = QueryInput.text (verbatim)
     document input = the PARAGRAPH NODE TEXT verbatim (p:text), NOT D(p):
     the cross-encoder was trained on standalone (query, passage) pairs, and
     the heading prefix is a BM25-specific trick; each channel uses its
     canonical input. Recorded, ablatable.
  → logit per candidate, score_kind="logit"
  → total order (logit descending, node_id ascending)
  → top 50 → shared packing policy (§2.3: per-article cap 3, strict 1000-token
    cap, exact generator tokenizer, ranked prefix) → packet
```

- **v0 policy only**: top-K (50) on raw logits. No threshold, no sigmoid, no
  probability language, no ECE/Brier — the stage carries
  `ThresholdPolicy(threshold=None, top_k=50, score_kind="logit",
  calibration_method="none_ranking_only", interpretation="raw_score_absolute")`
  (top-K-only; with `threshold=None` the interpretation is inert, but it
  must be a declared value — `validate()` fails closed on "unspecified" —
  and "raw_score_absolute" is the honest label for a logit domain with no
  threshold in play). A bare sigmoid is NOT
  calibration (substrate invariant). Any threshold work is the cascade
  teams' problem; the ceiling must stand on ranking alone.
- Top-50 sizing: the packet holds ~4 paragraphs; 50 leaves 12× slack under
  the per-article cap of 3, enough for second-atom recovery on multi-hop
  items. Pinned; rationale recorded.

### 5.4 Expected resources (this is the "expensive" in expensive-but-simple)

| Quantity | fp32 PyTorch reference (reportable) | int8 ONNX deployment variant |
|---|---|---|
| Weights storage | ~272,578,560 B `model.safetensors` (DERIVED; exact at download) + committed `tokenizer.json` (bytes at download) | `onnx/model_qint8_avx512.onnx` (desktop) — existence VERIFIED; bytes at download (~68–90 MB ESTIMATE incl. int8 tables) |
| RAM resident | ~300–380 MB (ESTIMATE: 272.6 MB weights + torch overhead + activations at ~320-token cards) | ~70–100 MB (ESTIMATE) |
| Latency per query (500 cards, ~320 tokens each, desktop i7-8700-class) | ESTIMATE ~10²–10³ s single-threaded fp32 (the determinism pin of §8.4 forces single-threading on the reference; ≈ 68M × 2 FLOP/param/token × 320 tokens × 500 cards ≈ 22 TFLOP per query, at a realistic single-core fp32 throughput of ~10–30 GFLOPS on this class of CPU) | ESTIMATE ~10¹–10² s multi-threaded ORT int8 |
| Index storage | B1 index (~15–40 MB ESTIMATE core) | same |

The number above is the whole point: **the ceiling is slow enough on
desktop that a millisecond-class BM25 system matching it is a dramatic
result**, and the cascade (500×17M + 200×32M + 50×68M ≈ 270 "68M-card
units" vs 500 — barely more than half the ceiling's card work, counted
proportionally to parameters) can only win on cost if it actually removes
work. A 146-item dev+shadow-dev run at ~10²–10³ s/query single-threaded is
≈ 1–3 days; that is acceptable for a ceiling baseline and is itself a
reported cost datum (a first pass on dev alone, 59 items, is ≈ half a day). The int8 ORT variant is
for deployment-cost claims only; it must pass the parity gate before any
number from it is reported as the ceiling's quality:
top-100 rank correlation (Spearman) ≥ 0.99 against the fp32 reference AND
final-completion delta ≤ 1 item on 10 dev items, else it stays
deployment-only and the fp32 reference remains the reportable baseline.

## 6. B4 — Deterministic retrieval + fixed generator, no reranker (the true floor)

B4 is not a new retriever. **B4 = B1's stage-0 (exactly as §3 specifies) +
the shared packing policy (§2.3) + `decide_default` (§2.4) + the fixed
generator through `substrate.evidence.run_question` (§2.5), with full
`StageRecord`/`RetrievalOutcome` telemetry.** It is the true floor because
it contains zero learned components: no weights at all, only the pinned
corpus, a stdlib index, and the shared fixed generator.

B4 is also the **generator-floor probe** (STATUS.md accepted risk 3, owned by
this team). Protocol (PLAN.md Phase 4 step 1), custodian-scored:

1. Run B4 end-to-end on dev FIRST.
2. Custodian oracle run: the SAME fixed generator over an ORACLE packet
   (minimal complete sufficient set, packed by the same `build_packet`
   semantics) per item.
3. If answer-quality delta (oracle vs B4 packet) is ≈ 0 within CI, the
   generator FLOORS: good evidence packets do not produce better answers
   than B4's, so the retrieval tournament measures nothing above the floor.
   **STOP and report** before burning any rerank effort. A degraded-packet
   control (BM25 bottom-ranked paragraphs) confirms the generator at least
   discriminates when it should.

B4 is the configuration named in the kill condition (§0). It is also the
Regime-A ≡ Regime-B baseline by construction (§2.6).

## 7. Evidence-survival profiles (PREDICTION, preregistered)

All estimates at paragraph granularity (a required sentence survives iff its
host paragraph is in the stage's candidate set). None of these are
measurements; each is replaced by custodian-scored `stage_coverage` /
`survival_curve` / `conditional_retention` (with denominators) in Phase 4.

| System | Stage-0 survival (top-500) | After rerank → packet (~4 slots) |
|---|---|---|
| B1 / B4 | PREDICTED 0.88–0.97 on dev/shadow-dev. 500/9,979 = 5% of the corpus; entity-heavy questions + heading context concentrate the right article; the risk is the multi-hop second atom ranking 100–500 | PREDICTED 0.70–0.90 final completion. Loss concentrates on multi-hop/comparison items whose second required paragraph falls outside the ~4-slot strict budget; factoids ≈ high |
| B2 | PREDICTED 0.88–0.97, i.e. B1 ± (0.00–0.05 union gain). The static channel is a differentiator only on synonym/paraphrase items; §4.5 predicts it rarely fires | PREDICTED ≈ B1 (the union gain must survive the packet budget to show) |
| B3 | Stage-0 set = B1's, by construction (the reranker adds no candidates, only reorders) → stage-0 survival IDENTICAL to B1 | PREDICTED B1 + (0–5 pts). The 68M card's value is reordering: it helps when a required paragraph is at BM25 rank 30–100 and must be lifted into the top ~4 after the per-article cap. If the BM25 top-10 is already near-optimal, the ceiling adds little — which is precisely the finding B4's kill condition monetizes |

Abstention profile (PREDICTION, all four systems, identical): unanswerable
items → nonempty packet → generate → `unsupported_generation` (the floor
cannot abstain without a tuned gate, §2.4). Comparison/ambiguous items:
best-effort generation under the fixed prompt. This shared failure mode is a
property of the floor, reported identically for every system, and is NOT a
reason to add sufficiency complexity to a baseline.

## 8. Tie-breaking and determinism (the exact rule)

The rule is: **every ranked list is a total order by (score_key, node_id),
where `node_id` is compared as its UTF-8 byte string ascending, and the
score key is computed with the exact arithmetic prescribed per stage.**
`node_id` is unique, so the order is total: no two implementations that
follow the spec can disagree about the order.

1. **B1 BM25 — bit-exact.** All arithmetic IEEE-754 double
   (Python `float`, `math.log`). Prescribed order: (i) tokenize exactly per
   §3.2; (ii) unique query terms in first-occurrence order; (iii) per-document
   score = the §3.3 sum evaluated in that term order, each summand computed
   as `idf(t) * (tf*(k1+1)) / (tf + k1*(1 - b + b*dl/avgdl))` with the
   denominator evaluated left-to-right as written; (iv) index-time constants
   (`N`, `avgdl`, `df`, `tf`) are exact integers/rationals from the pinned
   corpus. Same operations, same order, same input → same double, on any
   implementation. `test_bm25_bit_exact` (PLAN.md) enforces it against a
   hand-computed fixture.
2. **B2 static — reference-pinned, fixture-enforced.** Embeddings are the
   fp32 library reference (sentence-transformers 3.3.0, pinned revision,
   CPU, single-threaded). Cross-language bit-equality between, e.g., numpy
   and torch is NOT claimed (BLAS differences); instead: (a) the reference
   run is deterministic across two runs on the same machine (same top-500
   list byte-for-byte); (b) ANY re-implementation must match the reference's
   top-500 SET on the 20-question fixture or it is rejected. Score values
   are reported from the reference only.
3. **B2 fusion — integer-exact.** Borda ranks are integers (§4.3); the fused
   sum and the (fused, node_id) total order are exact on any implementation.
4. **B3 reranker — reference-pinned, parity-enforced.** Reference runtime:
   sentence-transformers `CrossEncoder` on the fp32 checkpoint,
   `torch.set_num_threads(1)`, `batch_size=1`, CPU, document order = stage-0
   rank order (fixed input order). Determinism claimed for RE-RUNS of the
   same reference (identical logit list → identical total order), not across
   runtimes. Any deployment runtime (ORt int8, multi-thread) must clear the
   §5.4 parity gate before its rankings are reported. (logit descending,
   node_id ascending).
5. **Packing** introduces no new ordering: spans are consumed in final-rank
   order; `build_packet` is a pure function (substrate, frozen).
6. **No randomness anywhere.** Seeds are logged, unused. Corpus document
   order = pinned byte order. Every index artifact (binary + JSON) is
   sha256-pinned into the run manifest; a build that differs from the pin
   blocks the run.
7. **Floating-point honesty (stated once, for all systems):** within one
   team's pipeline on one machine, re-runs are bit-identical (rules 1, 3, 6,
   plus 2/4 by reference pinning). ACROSS teams, comparability rests on the
   recorded ranked lists (`candidate_ids` + raw `scores` in the trace, wire
   schema per `docs/stage-score-semantics-notes.md`) and on the fixture/parity
   gates, NOT on cross-runtime bit equality — which is impossible for model
   runtimes and not required.

## 9. Resource summary (four systems; index vs weights separated)

Storage/latency: ESTIMATE unless labelled VERIFIED/DERIVED; RAM: ESTIMATE.
All replaced by `storage_manifest` / `timed_phase` / `proc_peak_rss_mb` in
PLAN.md. The ~1 GB fixed generator is shared by all systems and excluded from
per-baseline cost.

| System | Index storage (core) | Weights storage | RAM resident | Latency class / query |
|---|---|---|---|---|
| B1 (BM25) | EST 15–40 MB packed binary (sha256-pinned) | **none** | EST 25–80 MB | MILLISECONDS (EST < 10 ms) |
| B4 (floor) | same as B1 | none (+ shared 1 GB generator) | EST 25–80 MB (+ generator) | ms retrieval + seconds generation (fixed) |
| B2 (BM25 + static) | B1 index + doc-vector cache: DERIVED 40,873,984 B fp32 core / 149,950,464 B merged (int8: 10,218,496 B / 37,487,616 B) | VERIFIED 125,018,208 B fp32 table (or VERIFIED 31,259,319 B int8 ONNX) + 711,396 B tokenizer | EST 160–230 MB (fp32) | ~10–50 ms retrieval (EST) |
| B3 (68M ceiling) | B1 index | DERIVED ~272.6 MB fp32 safetensors (exact at download) or int8 ONNX EST 68–90 MB | EST 300–380 MB (fp32, single-threaded) | ~10²–10³ s fp32 single-threaded (EST); ~10¹–10² s int8 ORT multi-threaded (EST) |

Merged-tier index deltas: B1 index EST 60–160 MB; B2 doc cache 149.9 MB
fp32 / 37.5 MB int8 (DERIVED); B3 unchanged (weights are tier-independent).
Indexing TIME at both tiers is a Phase 1/2/3 measurement, not an estimate.

## 10. Contract ambiguities (precedent-setting, for the orchestrator)

1. **Worker-measured dev survival metrics.** Workers cannot see labels; the
   custodian-scored harness must return per-item covered/not-covered FLAGS
   plus aggregate rates (never atoms, answers, or source ids). This matches
   the ettin team's §13.1 proposal; the baselines support it. Without it,
   Phase 4's kill attribution cannot run.
2. **Scale adjudication unwired** (accepted risk 6): until `eval/metrics.py`
   consumes `eval/scale_adjudication.py`, Phase 5 reports BOTH series (raw
   and adjudicated via the standalone script) with the break annotated.
3. **Judge digest unpinned** (accepted risk 4): secondary generated-answer
   metrics are ABSENT for all baselines; readiness and the kill condition
   rest on deterministic primary metrics only.
4. **Ambiguity/abstention grading undefined** (STATUS.md honest limitation 4):
   the floor (`decide_default`) abstains on zero spans only; any
   orchestrator-defined ambiguity scoring applies identically to all four
   systems (same generator, same prompt, same decision floor).
5. **Where the pinned revisions live**: these files record the
   baseline team's verified observations (date 2026-10-03). The canonical
   pin artifact belongs to the custodian/freeze inventory; PLAN.md Phase 0
   produces the re-resolution record (revision + weight sha256) for it.

## 11. Verification log (this report)

- 2026-10-03, Hub API: `static-retrieval-mrl-en-v1` (sha, lastModified,
  license, file listing + LFS oids/sizes, `modules.json`,
  `config_sentence_transformers.json`, `README.md` model-index, `train.py`)
  — all VERIFIED; table geometry DERIVED, shape-assertion pending download.
- 2026-10-03, Hub API: `cross-encoder/ettin-reranker-{17m,32m,68m}-v1`
  (sha, lastModified, license, params, usedStorage, siblings incl.
  `onnx/model_qint8_arm64.onnx` presence in all three) — all VERIFIED;
  SHAs identical to the peer team's 2026-10-03 observations; no
  disagreement recorded.
- 2026-10-03, local: corpus geometry (node counts, word counts, `(lead)`
  count = 297, scale paragraph/word counts) computed from the byte-pinned
  `corpus/corpus.jsonl` and `corpus/scale/distractor.jsonl`; manifest hashes
  cross-checked against `corpus/build_manifest.json` and
  `corpus/scale/scale_build_manifest.json`.
- No weight bytes were downloaded; no sha256 of any weight file is claimed in
  this report. No private question, label, review, or authored artifact was
  read; `corpus/private_test_manifest.json` (opaque, counts+hashes) is fine
  and was not even needed. No Android claim anywhere in this file.
