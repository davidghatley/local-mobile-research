# Round 0 — Model Feasibility Evidence

Worker: Round 0 model-feasibility researcher (explicit free endpoint; no nested spawning).
Live verification date (UTC): 2026-09-29. Connector: live Hugging Face Hub (search/details/filesystem).
No weights downloaded. Metadata read only (cards/configs/listings, far below 20 MB budget).
Machine-readable companion: `references/model-catalog.json` (owned by this worker).
`references/pins.json` is owned by another worker and was NOT read or touched.

Status vocabulary: **VERIFIED_EXISTS** (live Hub lookup returned repo + files on access
date) vs **ADVERTISED_NOT_VERIFIED** (claimed on a card/paper, not confirmed by us) vs
**EXPERIMENTALLY_VERIFIED** (measured in our harness — nothing below has this status).
This is shared feasibility evidence, not a model-selection decision and not an
architecture advantage claim. Architecture teams may not start until the Round 0 freeze.

## 1. Ettin reranker family — all six official sizes VERIFIED

Live search `hf://models/cross-encoder` for `ettin` (2026-09-29) returned six official
checkpoints (an early assumption that no official 1B existed was wrong; corrected by search):

- `cross-encoder/ettin-reranker-17m-v1` (~17M; Hub-computed 16.8M)
- `cross-encoder/ettin-reranker-32m-v1` (~32M)
- `cross-encoder/ettin-reranker-68m-v1` (~68M)
- `cross-encoder/ettin-reranker-150m-v1` (~150M)
- `cross-encoder/ettin-reranker-400m-v1` (Hub-computed 394.8M)
- `cross-encoder/ettin-reranker-1b-v1` (Hub-computed 1028.1M)

Common wiring (verified from 17m card/config excerpts): base `jhu-clsp/ettin-encoder-*`
(MIT-tagged; all six encoder repos VERIFIED to exist), MSELoss, single-logit head
`Pooling(cls) -> Dense(256,256,GELU,no-bias) -> LayerNorm -> Dense(->1)`, max 7999 tokens,
license apache-2.0, sentence-transformers CrossEncoder. Output is a raw logit: it is NOT a
calibrated probability; every cascade stage needs calibration work in Round 1.
Revisions are UNPINNED — commit SHAs must be recorded at the Round 3 freeze.

Runtime facts: 17m/32m/68m/150m/400m tags advertise `onnx` + `openvino`, and the 17m file
listing shows `onnx/` and `openvino/` directories. The 1b listing shows NO `onnx/` or
`openvino/` directory and its tags lack both — the 1B is a desktop teacher/reference only
(4.1 GB safetensors), not a mobile candidate. Disk: 17m safetensors ~67 MB (config dtype
float32, so int8/quantized sizing is still open). ARM/Android execution is UNMEASURED for
all sizes — do not claim mobile latency until on-device measurement.
Community variants (`tomaarsen/ms-marco-ettin-*-reranker`, `bansalaman18/*-{bce,ranknet,
listnet}`, `kdhole/*1b*`) exist but are low-download and quality-unverified; the official
`-v1` line plus `cross-encoder/ettin-reranker-v1-data` (training-data ID, revision still to
pin) is the provenance to cite.

## 2. KaLM-Reranker-V1-Nano-R2 — exists; compression range partly verified; mobile blocked on export

`KaLM-Embedding/KaLM-Reranker-V1-Nano-R2` VERIFIED (apache-2.0, base
`google/t5gemma-2-270m-270m`, 0.27B activated = 100M non-embedding + 168M embedding;
safetensors ~1.57 GB). Card excerpts support, as ADVERTISED (not verified by us):

- Matryoshka embedding pooling (MEP) range 1x–128x; at 128x retains >=92% of 2x nDCG@10.
- Default output P(yes); `activation_fn=Identity` gives yes_logit − no_logit margin.
- Default chunk_size=4; query truncation 512, document 1024; custom `trust_remote_code=True`
  loader (`kalm_reranker.py`, `kalm_cross_encoder.py` present in repo).
- Stage siblings `Yuki131/KaLM-Reranker-V1-{Nano,Small,Large}-R2-{Stage1,Stage2-r64-a32,
  Stage2-r96-a48}` all VERIFIED to exist.

Gaps Experiment B must close in Round 1: (a) the vLLM adapter lists supported chunk sizes
1,2,4,8,16,32 — how ratios above 32x are selected is UNVERIFIED, confirm in code;
(b) document pre-encoding is ARCHITECTURE-IMPLIED (FBNL encodes `<Document>:{passage}`
independently of the query/decoder prompt) but no pre-encoded cache/save-load API was found
in the card — confirm in `kalm_reranker.py` before designing around it; (c) P(yes) is an
advertised score, not a calibrated probability; (d) card states ONLY the PyTorch backend is
supported — "training, ONNX, and OpenVINO are not included in this release." No ONNX export
is a material mobile blocker: Nano at ~1.57 GB bf16 with a custom-code loader does not fit
the Experiment B on-device story until an export path is demonstrated. Small (1B) and Large
(4B) siblings are desktop references only.

## 3. Static retrieval — VERIFIED zero-transformer

`sentence-transformers/static-retrieval-mrl-en-v1` VERIFIED (apache-2.0). `modules.json`
contains exactly one module of type `sentence_transformers.models.StaticEmbedding` — zero
transformer confirmed from primary source, not inferred. Static embedding safetensors ~125 MB;
`onnx/` directory present; cosine similarity; Matryoshka + MNRL losses. Portable by
construction (lookup + cosine), but ARM/Android execution is still UNMEASURED.

## 4. Compact GLiNER — 2.5-small VERIFIED; LoRA story unverified

`fastino/gliner2.5-small-v1` VERIFIED (apache-2.0, Hub-computed 73.9M, card 74M, backbone
`microsoft/deberta-v3-xsmall`, safetensors ~295 MB). Card excerpts: `boundary` architecture
loaded via `AutoExtractor` (legacy `GLiNER2.from_pretrained` span loader will NOT dispatch
this checkpoint), max_len 4096, entities/classification/records/relations/span-attributes in
one schema, CPU/CUDA/MPS via `gliner2[local]`. Family: base (194M), multi (287M,
multilingual). Two gaps: (a) NO LoRA-adapter mechanism is documented on the card, so
Experiment D's "GLiNER2-style shared backbone + LoRA" is custom work, not an off-the-shelf
feature — record as hypothesis; (b) no first-party ONNX export found, but
`litert-community/GLiNER2.5-Small-LiteRT` exists (Android-relevant, ADVERTISED_NOT_VERIFIED).
The `-small-v1` vs `-small-v1-onnx` (`nicolasembleton/…`, ADVERTISED) distinction matters at
freeze-time pinning.

## 5. Laya / Jev decision models — Laya VERIFIED; Jev has no single official checkpoint

`convaiinnovations/laya` VERIFIED (apache-2.0, 421.3M ModernBERT-large, safetensors ~842 MB,
context 512). Card's load-bearing excerpt: "It never generates text, so there is nothing to
parse and nothing to hallucinate" — non-autoregressive single-forward-pass behavior is
primary-source supported. Typed outputs (choice/score/noul) with RLCD-trained probabilities;
calibration is ADVERTISED and must be measured. Latency "~33 ms" is an advertised figure,
not ours. Siblings: `laya-multilingual` (321.9M, VERIFIED), `laya-typed-decisions` (0.766 vs
0.362 advertised — ADVERTISED). Runtime variants (`receptron/laya-onnx`, GGUF/llama.cpp,
`litert-community/Laya-Multilingual-LiteRT`) all ADVERTISED_NOT_VERIFIED. At 421M, Laya is
not "tiny" — its role is sufficiency/stop/route decisions, never passage ranking while a
17–68M reranker suffices (per prompt).
Jev: no official `Jev` checkpoint found (query `laya decision model` returned nothing; `jev
decision` returned community builds). `chaoliangUNSW/Jev-Style-{0.8B,2B}-Decision-v3`
(Qwen3.5-based, +GGUF/MLX) and `abidlabs/jev-typed-decisions-causal-0.6b` (LoRA on
Qwen3-0.6B) VERIFIED to exist. Jev reads as a community System-1/decision effort overlapping
Laya (shared leaderboards/tags); treat as alternatives. Do NOT invent an official Jev ID.

## 6. Strong reranker teacher — verified options, choice left open

`Qwen/Qwen3-Reranker-0.6B` (595.8M) and `Qwen/Qwen3-Reranker-4B` (4021.8M) VERIFIED
(apache-2.0, causal-LM architecture — desktop distillation/upper-bound only, never mobile
candidates). The prompt does not name a teacher; BGE/Jina are cited as inspiration on the
KaLM card but no specific teacher ID was verified here. Teacher selection is a Round 1
decision, not made in this file.

## 7. Encoder LoRA / multi-head support — hypothesis, not finding

No Ettin/ModernBERT-specific LoRA adapter release was found. LoRA on these encoders (PEFT on
attention projections) is standard-practice plausible but EXPERIMENTALLY UNVERIFIED here, as
is the heads-vs-LoRA-vs-separate-checkpoints question — that comparison IS Experiment C-vs-D
and must be run, not assumed. Known concrete facts favoring feasibility: the Ettin reranker
head is tiny (256→256→1), so per-task heads are cheap; base encoders are MIT-tagged, so
adapter training has no license friction. Adapter switching cost, resident-RAM behavior, and
ONNX-exportability of PEFT-modified ModernBERT are all open measurements.

## 8. CPU/ARM runtime and export feasibility (desktop knowledge, NOT on-device claims)

- Ettin 17m–400m: prebuilt ONNX + OpenVINO advertised; ONNX Runtime ships Android/ARM builds
  (ecosystem fact, not a measurement). Best near-term on-device story of the set.
- Ettin 1B: no prebuilt ONNX/OpenVINO found — desktop only.
- KaLM Nano: no ONNX/OpenVINO per card ("not included in this release") + custom remote code
  + ~1.57 GB — BLOCKED for mobile until an export path is demonstrated in Round 1.
- Static retrieval: ONNX dir present; lookup+cosine trivially portable.
- GLiNER2.5-small: CPU path advertised; LiteRT community build exists but unverified.
- Laya: ONNX/GGUF/LiteRT builds exist only as unverified community artifacts.
- Nothing in this section substitutes for real Android hardware measurement (per prompt).

## 9. Engram explicit-memory implications (brief; primary source only; no MoE proposal)

Primary source: DeepSeek-AI, "Conditional Memory via Scalable Lookup: A New Axis of
Sparsity for Large Language Models" (arXiv 2601.07372, 2026-01-12; Hub paper
`hf://papers/2601.07372`, metadata + abstract read 2026-09-29). Verified excerpts: Engram
"modernizes classic N-gram embedding for O(1) lookup" as conditional memory complementing
MoE conditional computation; a "U-shaped scaling law" allocates budget between MoE compute
and Engram memory (scaled to 27B, beating iso-param/iso-FLOPs MoE); "deterministic
addressing enables runtime prefetching from host memory, incurring negligible overhead."
Implications for us: (a) Engram is LEARNED opaque memory (n-gram → embedding table, with
hash collisions), not source-addressable text — it cannot supply citations, so it cannot
replace the explicit corpus; (b) the transferable ideas are deterministic addressable
structures (n-gram/entity → corpus-node lookup tables), prefetching, and host-memory
offloading — i.e. cheap candidate generation and index design, exactly the non-invasive
reading the prompt asks for; (c) adjacent work (`TF-Engram`, 2607.07388: train-free
SSD-backed phrase memory with prefetching) supports the same conclusion. NO invasive MoE or
generator-internal routing change is proposed; no Engram code or weights were pulled.

## 10. Material availability blockers for the freeze gate

1. No commit-SHA revisions recorded for ANY model (tooling exposed listings/cards, not git
   SHAs). Every Experiment readiness report must pin exact revisions/hashes; `pins.json`
   belongs to another worker.
2. KaLM Nano has no ONNX/OpenVINO export and a ~1.57 GB footprint — Experiment B has no
   credible on-device path until Round 1 demonstrates one (or scopes B to desktop with an
   explicit mobile-risk flag).
3. KaLM chunk-size↔compression mapping above 32x and any pre-encoded cache API are
   unconfirmed in code — read `kalm_reranker.py` / `kalm_cross_encoder.py` before freezing
   Experiment B's design.
4. GLiNER2-style LoRA sharing is a hypothesis with no off-the-shelf artifact — Experiment D
   must budget custom adapter work or drop the GLiNER leg.
5. Laya/Jev community runtime builds (ONNX/GGUF/LiteRT) are unverified; Laya at 421M needs
   resident-RAM justification for any mobile claim.
6. No calibration, latency, RAM, or retrieval-quality number in this file is a measurement —
   all advertised figures (Laya ~33 ms, KaLM retention tables, NanoBEIR scores) are attr
...[2283 chars truncated]
