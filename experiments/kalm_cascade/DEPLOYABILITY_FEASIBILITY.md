# Deployability & Feasibility Audit — KaLM Cascade and Adapter/PEFT Families

Status: FEASIBILITY ASSESSMENT ONLY. No implementation, no training, no private
data, no generator runs. All desktop. No Android performance claim anywhere in
this document.

Auditor endpoint: opencode/muse-spark-1.3-contributor-free (verified free).
No subagents spawned (nested spawning disabled). No paid fallback used.
Date: 2026-10-04. Read-only sources: `substrate/`, `eval/`, `corpus/`,
`tests/`, `scripts/`, `docs/`, `experiments/common/`,
`experiments/baselines/`, `experiments/kalm-cascade/`,
`experiments/adapter-peft/`. Writes only to `experiments/kalm_cascade/` and
`experiments/reviews/`. Private eval directory never touched; no custodian
token set.

Claim labels used throughout: **MEASURED** (a number produced by execution on
this host during this audit), **VERIFIED-BY-HUB-API** (live Hugging Face Hub
API observation, 2026-10-04), **VERIFIED-BY-DOCUMENT** (read in the cited
primary document during this audit), **REPORTED-IN-TEAM-DOC** (taken from the
cited team's mise-en-place report, corroborated where stated, not
independently re-verified), **DERIVED** (arithmetic from labelled facts),
**ESTIMATED** (the originating team's estimate, not re-measured),
**UNMEASURED** (could not be determined in this audit, with reason given).

---

## TASK 1 — KaLM: is the deployability blocker real?

### 1a. Model identity, revisions, and export artifacts (Hub API)

Model named in `experiments/kalm-cascade/HYPOTHESIS.md` §2:
`KaLM-Embedding/KaLM-Reranker-V1-Nano-R2`.

**VERIFIED-BY-HUB-API** (2026-10-04, `HfApi.model_info(..., files_metadata=True)`
plus `GET https://huggingface.co/api/models/KaLM-Embedding/KaLM-Reranker-V1-Nano-R2`):

- Head SHA `32b242bb7fd7ad6fd404154c09560d249ffe017f`, lastModified
  2026-09-23. Matches the SHA pinned in HYPOTHESIS.md §2 exactly.
- `safetensors.total = 786,029,296` params; `model.safetensors` size =
  **1,572,182,264 bytes** (~1.46 GiB BF16). Matches the team's figure byte-for-byte.
- Full sibling file listing: `.gitattributes`, `README.md`, 8× `assets/*.jpg`,
  `config.json`, `config_sentence_transformers.json`, `generation_config.json`,
  `kalm_cross_encoder.py`, `kalm_cross_encoder_config.json`, `kalm_reranker.py`,
  `kalm_reranker_utils.py`, `model.safetensors`, `modules.json`,
  `tokenizer.json`, `tokenizer_config.json`, `vllm_support/` (README, examples,
  `pyproject.toml`, plugin sources). **No `onnx/` directory, no `*.onnx` file,
  no `*.gguf` file, no ExecuTorch/CoreML/TFLite artifact of any kind.**
- Model tags include `t5gemma2`, `encoder-decoder`, `matryoshka`;
  `model_type: t5gemma2`, architecture `T5Gemma2ForConditionalGeneration`,
  license `apache-2.0`, base model `google/t5gemma-2-270m-270m`.

GGUF search **VERIFIED-BY-HUB-API** (`list_models`, 2026-10-04):

- Search `KaLM-Reranker-V1-Nano-R2-GGUF`: **zero results**. No R2 GGUF exists
  anywhere on the Hub.
- Search `KaLM GGUF`: only official V1 (non-R2) conversions exist —
  `KaLM-Embedding/KaLM-Reranker-V1-Nano-Q8_0-GGUF`,
  `...-V1-Nano-Q4_K_M-GGUF`, plus Small/Large equivalents. This corroborates
  HYPOTHESIS.md §4 point 2 (GGUFs are V1-only).
- The vendor's torch-only stance ("Only the PyTorch inference backend is
  currently supported; training, ONNX, and OpenVINO are not included in this
  release"; `backend != "torch"` raises `ValueError`) is
  **REPORTED-IN-TEAM-DOC** (HYPOTHESIS.md §4, quoted from the model card and
  `kalm_cross_encoder.py`). I did not re-download the card Python files in this
  audit; the corroborating evidence I independently verified is the complete
  absence of any non-PyTorch artifact in the repo file listing above.

Conclusion of 1a: the prior team's artifact inventory is **CONFIRMED
byte-for-byte** (SHA, weight size, file listing). There is nothing to export:
no single-ratio serialised R2 graph exists, so the multi-rate question is moot
at the artifact layer.

### 1b. Structural reason: what multi-rate compression needs vs what runtimes offer

KaLM's mechanism (REPORTED-IN-TEAM-DOC, HYPOTHESIS.md §3, from
`kalm_reranker_utils.py:pool_encoder_chunks`): mask-aware mean-pooling over
consecutive groups of `chunk_size` encoder hidden states, switched at test time
(`chunk_size=None/1/2/4/8/16/32/64/128` on one checkpoint). Structurally this
demands a runtime that can EITHER:

- (i) hold decoder/graph implementations for several sequence-compression
  rates and select among them at runtime (dynamic sequence axes per rate), OR
- (ii) support runtime switching of effective bit-width / sequence shape in a
  single exported graph.

What I checked, and what it shows:

1. **ONNX Runtime quantization model** — VERIFIED-BY-DOCUMENT
   (`onnxruntime.ai/docs/performance/model-optimizations/quantization.html`,
   read 2026-10-04): "Quantization in ONNX Runtime refers to 8 bit linear
   quantization of an ONNX model," producing ONE fixed artifact. Static
   quantization bakes scale/zero-point constants into the model; dynamic
   quantization computes activation parameters on the fly per forward pass but
   the model is still a single fixed int8 graph — not a menu of selectable
   bit-widths. There is no per-layer dynamic bit-width selection mechanism in
   the documented quantization API. Int4 block-wise weight-only quantization
   exists (MatMul/Gather, opset ≥ 21) — again a fixed export-time choice, not
   runtime switching.
2. **ONNX Runtime adapter support scope** — VERIFIED-BY-DOCUMENT (same site's
   navigation, read 2026-10-04): the only LoRA-adapter documentation lives
   under "Generate API (Preview) → Tutorials → Run with LoRA adapters", i.e.
   scoped to the generative-LLM API, not the general encoder/graph path and
   not ORT Mobile's reduced-op-set encoder path.
3. **llama.cpp conversion coverage** — VERIFIED-BY-DOCUMENT (raw sources from
   `github.com/ggml-org/llama.cpp`, master, read 2026-10-04):
   `conversion/` contains `bert.py` (registers `BertModel`,
   `BertForSequenceClassification`, DistilBERT, RoBERTa, NomicBERT, NeoBERT,
   EuroBERT, JinaBERT → BERT-family encoders ARE convertible) and `t5.py`
   (registers ONLY `T5WithLMHeadModel`, `T5ForConditionalGeneration`,
   `MT5ForConditionalGeneration`, `UMT5ForConditionalGeneration`, `UMT5Model`,
   `T5EncoderModel`). There is **no `modernbert.py`** and **no `t5gemma2`
   registration anywhere in `conversion/`**. So stock llama.cpp can convert
   neither the KaLM T5Gemma2 architecture nor ModernBERT-based ettin
   checkpoints. This independently corroborates the team's "patched
   llama.cpp at pinned commit `277a105d` … stock frontends are not supported"
   finding for the V1 GGUF (REPORTED-IN-TEAM-DOC).
4. **llama.cpp LoRA flags** — VERIFIED-BY-DOCUMENT (server README, master):
   `--lora FNAME`, `--lora-scaled FNAME:SCALE`, `--lora-init-without-apply`
   ("apply later via POST /lora-adapters") exist, i.e. runtime adapter
   load/scale/switch machinery EXISTS on the generative server path. Whether
   it applies to the `--embedding`/`--rerank` endpoints or to BERT-arch
   encoders is UNMEASURED (not documented in what I checked).
5. **NCNN / MNN / TFLite / ExecuTorch / ONNX Runtime Mobile operator coverage
   for T5Gemma2 encoder-decoder, and any per-layer dynamic bit-width
   selection in any of them** — UNMEASURED. I did not survey these runtimes'
   op registries in this audit, and I assert nothing about them beyond the
   ORT findings above. The verdict below does not depend on them: the blocker
   bites one layer earlier (no exportable graph at ANY ratio).

Structural summary: even design (i) — shipping N fixed-ratio graphs — is
impossible today because the count of available R2 graphs is zero (vendor
torch-only, §1a). Design (ii) — one graph with runtime rate switching — has no
supporting artifact either, and ORT's documented quantization model is
fixed-graph, not rate-switchable. The KaLM pooling itself is encoder-side
sequence-shape switching, which ONNX dynamic axes could in principle express,
but with no exporter and no T5Gemma2 mobile kernel, that possibility is
purely hypothetical. The prior team's "nothing to export it TO" is CONFIRMED.

### 1c. Contrast: what IS available (ettin `onnx/model_qint8_arm64.onnx`)

**VERIFIED-BY-HUB-API** (2026-10-04, `files_metadata=True` sizes):

| Repo (SHA re-verified, matches adapter-peft doc) | `onnx/model_qint8_arm64.onnx` size |
|---|---|
| `cross-encoder/ettin-reranker-17m-v1` (`9e4aa353…`) | **17,127,704 B** (~16.3 MiB) |
| `cross-encoder/ettin-reranker-32m-v1` (`b33e5ceb…`) | **32,416,083 B** (~30.9 MiB) |
| `cross-encoder/ettin-reranker-68m-v1` (`d166fa88…`) | **69,276,379 B** (~66.1 MiB) |

Each repo also ships `onnx/model.onnx` (fp32), `model_O1`–`O4.onnx`,
`model_qint8_avx512*.onnx`, `model_quint8_avx2.onnx`, and OpenVINO artifacts —
i.e. a genuine multi-backend export story, the opposite of KaLM's.

Local-snapshot presence check — MEASURED (this host, 2026-10-04): the three
local HF cache snapshots contain ONLY config/tokenizer stub files (11–13
files, ~60 KB each; weight `.safetensors` stubs of 76 bytes). **`onnx/` is
absent from all three local snapshots.** So the requested FILE-PRESENCE check
FAILS locally and SUCCEEDS on the Hub. This is a file-presence finding only:
no parity measurement, no runtime load test, and no inference-quality claim is
made or implied. Notably, the task brief's "70.8 MB" (C) and "276.2 MB" (B3)
figures are consistent with the Hub fp32 sizes measured here (17m:
67,193,928 B + heads ≈ 64.3 MiB; 68m: 272,589,832 B + heads ≈ 260.6 MiB),
which corroborates the experiment weight accounting without re-running it.

### 1d. Verdict — TASK 1

**MOBILE DEPLOYABILITY (KaLM-Reranker-V1-Nano-R2 multi-rate cascade) = BLOCKED.**

Evidence chain (each link labelled above): pinned SHA + 1,572,182,264-byte
weights (VERIFIED-BY-HUB-API) → zero non-PyTorch artifacts in the complete
repo file listing (VERIFIED-BY-HUB-API) → zero R2 GGUFs Hub-wide; V1-only
GGUFs (VERIFIED-BY-HUB-API) → stock llama.cpp conversion covers neither
T5Gemma2 nor ModernBERT (VERIFIED-BY-DOCUMENT) → ORT quantization is
fixed-graph, with LoRA adapters scoped to the GenAI LLM path
(VERIFIED-BY-DOCUMENT). The prior team was RIGHT, and the blocker is
artifact-layer (nothing to export at any ratio), not merely rate-switching
machinery. Desktop tournament work is unaffected by this verdict.
Phone-side index-size estimates (~38 MB core at 128x bf16) are ESTIMATED
(team doc, not re-measured) and in any case useless without a decoder runtime,
which does not exist. What I could NOT determine: mobile op coverage for
T5Gemma2 in NCNN/MNN/TFLite/ExecuTorch/ORT-Mobile (UNMEASURED — unneeded for
the verdict, since there is no graph to run).

---

## TASK 2 — Adapter/PEFT: does merging destroy the storage argument?

### 2a. True storage cost: merged vs shared-base (arithmetic with real sizes)

Setup: A task-specific adapters over one shared base B. |B| = merged fp32
weight bytes; |aᵢ| = adapter weight bytes.

- Dynamic swapping ships: |B| + Σᵢ|aᵢ|.
- Merged deployment ships: A × |B| (one full dense copy per task).
- Sharing wins ⟺ |B| + Σᵢ|aᵢ| < A×|B| ⟺ **Σᵢ|aᵢ| < (A−1)×|B|** (crossover condition).

Real sizes VERIFIED-BY-HUB-API (2026-10-04, `files_metadata=True`):

| Base | Params (Hub metadata) | `model.safetensors` (fp32) | Heads/misc | Deployed fp32 total ≈ |
|---|---|---|---|---|
| ettin-17m (`9e4aa353…`) | 16,797,440 | 67,193,928 B (64.1 MiB) | 2_Dense 262,232 + LN 2,200 + 4_Dense 1,172 B | ≈ 67.46 MB |
| ettin-32m (`b33e5ceb…`) | 31,883,136 | 127,538,496 B (121.6 MiB) | ≈ 0.59 MB | ≈ 128.13 MB |
| ettin-68m (`d166fa88…`) | 68,144,640 | 272,589,832 B (260.0 MiB) | ≈ 1.05 MB | ≈ 273.64 MB |
| bge-small-en-v1.5 (`5c38ec7c…`) | 33,360,512 | 133,466,304 B (127.3 MiB) | — (single-file BERT) | ≈ 133.47 MB |

Adapter sizes DERIVED (LoRA tariff, REPORTED-IN-TEAM-DOC §2 table,
re-arithmetic-verified: per-layer 2×(h·r + r·h); bge-small h=384/L=12/r=8 →
12×2×6,144 = 147,456 params ≈ 0.59 MB fp32; ettin-17m h=256/L=7/r=8 →
7×2×4,096 = 57,344 params ≈ 0.22 MB fp32). No adapter weights exist in-repo;
these are configuration tariffs, not measurements.

Worked example DERIVED (A=3 task adapters on ettin-17m, r=8):

- Dynamic: 67.46 + 3×0.22 ≈ **68.1 MB**.
- Merged: 3 × 67.46 ≈ **202.4 MB**.
- Crossover check: Σ|aᵢ| ≈ 0.66 MB ≪ (A−1)×|B| ≈ 134.9 MB → sharing wins by
  two orders of magnitude **wherever swapping is supported**.
- Merged-vs-C comparison (the brief's mandatory check): 202.4 MB merged ≫
  **70.8 MB** for family C's single shared 17M encoder + 3 heads (MEASURED
  experiment figure, settled per brief §TASK 3). Even A=2 merged (134.9 MB)
  is ~1.9× C. **Stated plainly: under forced merging, the multi-adapter
  deployment costs strictly more than C's single shared encoder for every
  A ≥ 2, before counting any per-task quality difference.** The crossover
  condition only fails (sharing loses) if Σ|aᵢ| ≥ (A−1)×|B|, i.e. adapters
  totalling >~135 MB at A=3 — roughly 600× larger than the r=8 LoRA tariff;
  full fine-tune copies are the only realistic way to reach that regime, and
  those are not adapters at all.

Second comparison (single-task reading, the weak sense): one merged LoRA
ettin-17m (≈ 67.5 MB fp32, ≈ 17.1 MB int8 via the shipped qint8 onnx,
VERIFIED-BY-HUB-API size) vs the larger frozen comparator bge-base 109.5M
(≈ 438 MB fp32 DERIVED). That 6.5× ratio survives merging — but it is a claim
about LoRA *training* reaching large-model quality at small-model size, and
it is void if the adapter shows no transferable gain (the team's own kill
condition §0.1; quality status is UNMEASURED — no adapter has been trained).

### 2b. Which mobile runtimes support adapter swapping at inference

Checked in this audit (VERIFIED-BY-DOCUMENT where stated):

- **llama.cpp**: `--lora` / `--lora-scaled` / `--lora-init-without-apply`
  ("apply later via POST /lora-adapters") flags exist in the current server
  README → per-request adapter switching EXISTS, but on the generative-LLM
  server path. BERT encoders are convertible (`conversion/bert.py`); ModernBERT
  is not (no registration); T5Gemma2 is not (`t5.py` lacks it). Applicability
  of `--lora` to the `--embedding`/`--rerank` endpoints, to BERT-arch
  encoders, and on quantised bases: UNMEASURED (not documented in the sources
  checked). Net: llama.cpp preserves the swapping advantage only for
  generative LLMs, not demonstrated for this family's retrievers.
- **ONNX Runtime (incl. Mobile)**: only documented LoRA surface is the GenAI
  LLM API tutorial ("Run with LoRA adapters"); no adapter mechanism on the
  general encoder/session path or ORT Mobile's reduced op set, in the docs
  checked. Swapping NOT preserved for bi-encoder/cross-encoder deployment.
- **ExecuTorch**: no PEFT/adapter runtime hook found in this audit; export is
  single-graph (`torch.export`). Merged-model export follows the base path but
  BERT/ModernBERT encoder support there is unestablished. UNMEASURED in this
  audit (not independently surveyed); the team's ASSUMED-BLOCKED stands
  unrefuted and unconfirmed.
- **MNN / NCNN / TFLite**: UNMEASURED in this audit (not surveyed). No
  evidence of a PEFT adapter runtime was found in this audit for any of them.

Structural point (DERIVED, uncontroversial): an unmerged PEFT wrapper is not
the base `AutoModel` graph, so standard ONNX/export tooling takes the
merge-then-export path (`merge_and_unload()` → base export; ettin ships that
base path in-repo, VERIFIED-BY-HUB-API). Merging is therefore mandatory for
every export route, and the merged artifact is indistinguishable from the
plain small base at runtime.

### 2c. Verdict — TASK 2

**Storage advantage: REAL at training time, NEUTRALISED at mobile deployment
for every runtime checked, UNKNOWN-UNMEASURED for the runtimes not surveyed.**

- REAL (training-time): adapters are 100–1000× smaller than larger-model
  weights (0.22–0.59 MB vs 438 MB fp32, DERIVED). No runtime preserves this
  as a *deployment* artifact on the evidence checked.
- NEUTRALISED (deployment): all checked mobile paths require merging; with
  A ≥ 2 task adapters the shipped bytes (A×|B|) exceed both the swapping
  design (|B|+Σ|aᵢ|) and family C's single 70.8 MB shared encoder (MEASURED
  brief figure). The only surviving deployment claim is the weak sense —
  "one LoRA-trained small ≈ large-model quality at small-model cost" — whose
  quality premise is UNMEASURED.
- Which runtimes preserve swapping: on the evidence checked, NONE for
  BERT/ModernBERT retrievers (llama.cpp swapping exists only on the
  generative path; ORT adapters only under GenAI; ExecuTorch/MNN/NCNN/TFLite
  not surveyed — UNMEASURED). The prior team was RIGHT.
- Could NOT determine: measured merge-parity numerics (no adapters trained);
  int8 merged quality parity (UNMEASURED — an int8 drop would erase the weak
  claim too); per-request adapter latency on any mobile runtime (UNMEASURED).

---

## Settled-numbers consistency check (brief TASK 3 — MUST NOT contradict)

All figures below are restated from the brief as settled MEASURED facts; my
assessments are checked against them:

- Retrieval is saturated (BM25 stage-0 survival 0.9589 dev / 0.9836
  shadow_dev) and the 1000-token budget binds (completion 0.7397 / 0.6557).
  Consistent with: my finding that KaLM's honest phone-side design needs the
  two-stage collapse (128x → 4x → packet) — a cascade that loses nothing at
  stage 0 is the only kind worth shipping, and BM25 already shows stage-0 is
  nearly free.
- B2 (0.7260, −1 paragraph vs B1, +166.6 MB) shows dead weight is punished;
  KaLM at 1.57 GB weights with no export path is dead weight raised to a
  blocker, and any merged-adapter stack heavier than C repeats the B2 mistake.
- B3 (0.8904, 77,369 ms, 276.2 MB) vs C (0.8767, 39,636 ms, 70.8 MB): ONE
  paragraph apart (65 vs 64 of 73), C at ~1/2 latency and ~1/4 weights.
  Consistent with: merged multi-adapter deployments (≥134.9 MB at A=2 on the
  17m base) cannot beat C on storage, so the adapter family must beat C on
  quality-per-byte or stand refuted — exactly the cascade-family kill
  condition the adapter team already accepted.
- C's cost anatomy (shared encode = 99.8%; 3 readouts = 10.9 ms) is the
  strongest structural precedent FOR shared-base designs and AGAINST merged
  copies: one encode amortised over heads/adapters is what makes C cheap, and
  merging reinstates the per-task full-encode cost the design was built to avoid.
- MMD floors (dev 22.0 pp / shadow_dev 17.2 pp / combined 12.3 pp): every
  quality delta cited in this audit's forward guidance (B3−C = 1 paragraph;
  any future LoRA-small vs base-small claim) sits inside NULL-RESULT territory
  unless powered beyond these floors. In particular the weak adapter claim
  ("LoRA-small ≈ large") cannot be established on dev (n=59/73-item scale)
  except as an underpowered null — REPORTED-IN-TEAM-DOC §0 already prices
  this in; I concur.

## Family table (quality status → deployability status → evidence)

| Family | Quality status | Deployability status | Specific evidence |
|---|---|---|---|
| KaLM-R2 multi-rate cascade | UNMEASURED (no runs; BEIR/MIRACL retention is out-of-corpus prior, not evidence) | **BLOCKED** | Zero non-torch artifacts in full Hub file listing; no R2 GGUF Hub-wide; stock llama.cpp converts neither t5gemma2 nor ModernBERT; ORT quantization is fixed-graph |
| Adapter/PEFT (swapping design) | UNMEASURED (no adapters trained) | **BLOCKED as designed** (swapping unsupported on all checked mobile paths) | llama.cpp LoRA flags generative-only; ORT LoRA GenAI-only; merge-then-export mandatory; ExecuTorch/MNN/NCNN/TFLite unsurveyed |
| Adapter/PEFT (single merged small) | UNMEASURED (quality premise untested) | **SUPPORTED wherever the base runs** (it IS the base) | ettin ships onnx+qint8+OpenVINO in-repo (Hub sizes verified); bge-small ships fp32 onnx in-repo |
| BM25 + static / B1–B3 / C | MEASURED (settled per brief) | SUPPORTED (desktop-measured; mobile UNMEASURED) | Brief TASK 3 figures; no Android claim made |

## What I could NOT determine and why

1. Mobile op coverage for T5Gemma2/BERT/ModernBERT in NCNN, MNN, TFLite,
   ExecuTorch, ORT Mobile — not surveyed (verdict does not depend on it).
2. Whether llama.cpp `--lora` works on the embedding/rerank endpoints or on
   quantised BERT bases — not documented in sources checked; would need a
   build-and-run experiment (CPU-only host can do this; out of scope for a
   read-only audit).
3. Any adapter quality number (gain, merge parity, int8 parity) — no adapters
   exist yet; training-gated.
4. KaLM 128x sufficient-set turnover on dev (the §1 falsifier) — needs the
  pinned weights + custodian-scored runs; the highest-value *desktop*
   experiment for that family and entirely unaffected by the mobile BLOCKED
   verdict.
5. Local `onnx/model_qint8_arm64.onnx` bytes — absent from the partial local
   snapshots; Hub presence verified instead. No parity/runtime inference is
   claimed from presence.
