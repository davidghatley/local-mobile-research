# Fixed-Generator Readiness Report (Round 0 worker)

Worker model: `opencode/muse-spark-1.3-contributor-free` — catalog-verified
zero-cost endpoint, explicitly selected (never inherited). No nested spawning.
No paid endpoints used. No paid generation APIs used anywhere.

Status: **REPAIR v3 COMPLETE — narrow shared repair integrated, smoke v3
PASS, adversarial 14/14 PASS, repeat protocol 3/3 identical, 113/113
substrate tests PASS.**
This does NOT freeze Round 0 and is NOT review approval: an independent
reviewer is currently reading the adapter; file hashes below identify the
exact snapshot reviewed. Corpus/questions/labels remain other workers'
scope. No benchmark, public-bounty, or held-out contact — synthetic only.

## 0b. Repair v3 — narrow-repair integration (2026-09-29)

Shared repair landed (`docs/evidence-token-repair.md`, 113 tests):
strict full-serialization packing, prompt v0.2
(`PROMPT_HASH d8580509...`, no `[node_id]` literal), shared
`evidence.parse_citations`. Orchestrator decisions integrated: **threads=1**
for controlled Round 1; single-user-message via pinned chat template as
common delivery. Generator-side changes (owned files only):

1. Config: `prompt_hash` → d8580… (verified `unpinned_fields: []`),
   `runtime_threads_measured` 6 → 1 (+ `threads_decision` note). All other
   pins unchanged; model/binary/lib/template hashes re-verified consistent
   (17/17 checks: model sha+bytes, server path+sha, 8 libs, GGUF template
   sha+bytes, vocab 151936, bos/eos, tokenizer model).
2. Adapter: local bracket regex DELETED; citation extraction delegates to
   shared `parse_citations` (+ shared `find_unknown_citations`). Empty
   packets pass through as abstention outcomes (no crash path).
3. Smoke v3 + adversarial + new `scripts/generator_repeat.py`: argparse
   `--root`/`--runs` with `main(argv)` guards — `--help` verified
   side-effect-free (no server, no hashing, no traces, no files).
4. Repeat protocol (predeclared): N fresh PIDs, one fixed synthetic
   prompt, threads=1/seed 1234/temp 0.0+top_k 1; per-process text sha,
   accounting, citation audit, load-vs-inference timings; process-cold
   only, NO cache-cold claim.

Observed (threads=1, prompt v0.2):
- Repeat 3/3 byte-identical across fresh processes (sha b301a33a…;
  loads 1510/1002/1502 ms — process-cold, page-cache variance visible).
- Counts: evidence 41 / user-prompt 127 / templated 156 (was 104/133
  under v0.1) / usage 156 == templated; completion 35, finish stop.
- v0.2 wording WORKED as intended: no literal `[node_id]` emitted. But the
  model now cites DESCRIPTIVELY ("paragraph two of the synthetic fixture")
  with zero bracketed ids → `cited_valid: []`, `unknown: []`. Fact
  correct ("5 units"); machine-readable citation absent — recorded, Round 1+
  business (extractors cannot rely on generator-emitted brackets).
- ABSTENTION FAILURE (adverse generator behavior, machinery correct):
  empty truncated packet → model answered "…threshold is 0.5." instead of
  stating insufficiency. Infra leg PASSED (no crash, citations empty);
  the generator does NOT reliably abstain — upstream sufficiency gating
  and/or the later generator tournament must handle this.
- Timings (i7-8700, t1): load ~1000–1510 ms fresh process; warm prompt
  ~213–423 ms / 156 tok; decode ~11 tok/s (was ~28 at t6). Client RSS
  ~28 MB; server worker ~1.4–1.6 GB (desktop proxy only).

Reviewer snapshot (sha256, 2026-09-29 post-run):
- `generator_runtime/qwen25_adapter.py` 8c7b9b41…
- `scripts/generator_smoke.py` 91701076…
- `scripts/generator_adversarial.py` 4b29b3ba…
- `scripts/generator_repeat.py` 2960c18f…
- `corpus/generator_config.json` 5f0975d6…
Running review is NOT approval; any further edit invalidates this snapshot.

Preserved history (nothing deleted, renamed, or reattributed): every
trace file found in `generator_runtime/` is intact — v1 trace, all six v2
traces (incl. FAIL runs), the new v3 + repeat traces. Provenance beyond
each file's own `label` field is NOT reconstructed here: in particular,
any prior accidental `--help`-triggered smoke output or substrate-worker
trace with uncertain attribution keeps its bytes and original filename
exactly as found; the argparse guard (§0b.3, verified side-effect-free
above) closes the `--help`-executes-main hole prospectively only.
This does NOT freeze Round 0: corpus/questions/labels belong to other workers
and independent review is an orchestrator decision.

Scope: wrote ONLY `generator_runtime/`, `scripts/generator_*`,
`docs/generator-readiness.md` (this file), and `corpus/generator_config.json`.
`substrate/` files were read-only (note: the shared substrate evolved under
separate review during this session — 88 tests now — and this worker's code
was aligned to it without editing it). No benchmark, public-bounty, or
held-out queries were run or inspected — only synthetic infra fixtures.

## 0. Repair v2 — exact dispositions

1. **Settings hardening + verified runtime.** Constructor overrides must now
   match the config EXACTLY (unknown keys and differing values both raise
   `ConfigDriftError`; identical values accepted). `prepare()` hash-checks
   the server binary + 8 llama-owned shared libs (fast-fail order) and only
   then the ~1GB model (2064 ms, timed separately from load). Config records
   full commit `050dde50…17b2` (not the short version), git-clean flag,
   compiler/target, and all binary hashes. `prepare()` gates `start_session()`
   and ephemeral `generate()`.
2. **Evidence token semantics.** `exact_token_count` on the whole prompt is
   gone. Three counts recorded separately: `evidence_tokens` (canonical
   `serialize_evidence` string, enforced against the 1000 cap via
   `EvidenceOverBudgetError` pre-generation), `user_prompt_tokens`
   (rendered, untemplated), `templated_input_tokens` (`/apply-template`
   output, asserted equal to `usage.prompt_tokens`). `GeneratedAnswer`
   now fills the shared fields honestly: `evidence_token_estimate` =
   whitespace estimate (INFRA unit), `exact_evidence_tokens` = measured,
   `prompt_tokens` = whole templated input, `completion_tokens` = usage.
   The arbitrary `cap*2` bound is removed.
3. **Citations parsed, not copied.** `GeneratedAnswer.citations` = EMITTED
   ids actually present in the text (packet-order); availability stays on
   the packet; unknown ids recorded via shared `find_unknown_citations`.
   No faithfulness claim from existence.
4. **`max_tokens` (supported chat API).** `n_predict` dropped from the
   contract. Verified live: `max_tokens: 4` → `finish_reason: length`,
   exactly 4 completion tokens; adapter raises if the server ever exceeds
   the pinned 256.
5. **Reaped shutdown on all paths.** `terminate → wait → kill → wait` with
   stderr capture; early exits raise `ServerStartupError` with exit code;
   close reports `{reaped, port_closed, returncode}` and tests confirm the
   PID is gone.
6. **Resident session.** `start_session()` times fresh-process load once
   (~1009 ms); warm calls measured distinctly (prompt ~213 ms warm vs
   ~4528 ms cold page cache; decode ~28 tok/s stable). Explicitly NOT
   claimed as true cold-cache.

**Adversarial 13/13** (`scripts/generator_adversarial.py`): drift-value,
drift-key, drift-identical, drift-config, exact-guard, exact-id-guard,
citations, runtime-bin, runtime-exe, early-exit, overbudget (5008 tokens
refused), cap-enforce, cleanup. Original v1 raw trace kept; v2 traces are
new files (two earlier v2 runs honestly record FAIL on the citation
observation before the gate semantics were corrected — history preserved).

**Own config transcription error caught by the new machinery:** the first
`libggml-cpu.so.0` hash written to the config had mangled characters;
`prepare()` refused it, shell re-measurement identified the typo, config
fixed, all 9 binary hashes programmatically re-verified. This is the
hash-check working as designed.

**Determinism scope finding (measured, decision needed):** within-session
repeat is bit-identical (verified repeatedly, temp 0 / top_k 1 / seed 1234).
ACROSS server processes at `-t 6`, three textually distinct (factually
identical: "5 units") outputs were observed for the same prompt+seed —
consistent with multi-threaded reduction nondeterminism flipping a close
argmax. At `-t 1`, two fresh processes produced byte-identical output.
Config keeps pinned `threads: 6` (the measured latency basis); the
determinism claim is therefore scoped to within-session repeat unless
review pins single-threaded inference (decode would drop ~28 → ~5 tok/s).

**Citation-behavior observation (not masked):** current pinned-path output
renders `...provided in [node_id] synth-para-002.` — literal `[node_id]`
placeholder text plus an unbracketed id. The parser correctly yields
`cited_valid: []`, `cited_unknown: ["node_id"]`, and the smoke records (not
gates) this. Answer-fact correct ("5 units"); citation FORM invalid. This is
generator behavior for Round 1+, surfaced rather than hidden.

## 1. Pinned generator identity (verified, not claimed)

| Field | Value |
| --- | --- |
| Repo | `bartowski/Qwen2.5-1.5B-Instruct-GGUF` |
| Immutable revision | `9eadc66189c7641e1ddd226b8267a9119b2ce2d4` (live HF Hub API, 2026-09-29) |
| File | `Qwen2.5-1.5B-Instruct-Q4_K_M.gguf` |
| Bytes | 986,048,768 (local `stat` == HF `x-linked-size` == audit claim) |
| SHA-256 | `1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370` — computed locally, exact match to HF `x-linked-etag` header and to the `docs/reference-audit.md` §7 claim (which was unverified until now: **now verified**) |
| License | Apache-2.0 (live HF tags `license:apache-2.0` + repo README license_link; ungated, public) |
| Quant toolchain | llama.cpp release b3772 imatrix (repo README claim, not independently verified) |
| Local path | `generator_runtime/artifacts/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf` |
| Provenance | `generator_runtime/artifacts/PROVENANCE.json` |

HF verification method (connector-preferred): `hub_repo_details` overview +
`hf_fs ls/stat` + Hub REST `/api/models/...` (repo sha, license, gated flags)
+ `curl -sI` on the pinned `resolve/<sha>/` URL (commit/size/ETag headers).
No fallback generator was acquired; none is proposed.

## 2. Budget compliance (measured)

- Download: 986 MB single file, budget <= 2 GB. **PASS.**
- Total disk (`generator_runtime/`): 941 MB weights dir + ~8 KB code/traces;
  repo-wide addition ≈ 0.99 GB, budget <= 4 GB. **PASS.** 32 GB free at close.
- RAM/disk figures below are desktop-CPU proxies only; no Android claim.

## 3. Runtime: inspected existing build, no rebuild

Existing llama.cpp install inspected BEFORE any build decision:
`/home/davidhatley/Work/tools/llama.cpp/build/bin/` (`llama-cli`,
`llama-server`, `llama-bench`), version `0.4.0-dev build 1 commit 050dde5`,
symlinked in `~/.local/bin`. `--version` runs clean. Build is CPU+Vk;
all generator work forces CPU-only (`-ngl 0`). **No build was needed, none
was performed, no system packages were modified.** Source tree
`~/Work/tools/llama.cpp` left untouched.

## 4. Adapter (`generator_runtime/qwen25_adapter.py`, stdlib only)

`LlamaCppGenerator` implements the substrate `Generator` protocol via
read-only imports (`render_prompt`, `PROMPT_HASH`, types). Ephemeral
`llama-server` subprocess per `generate()` call (free loopback port,
`--log-disable`), always terminated afterwards — **no persistent service**.
Pinned settings (`PINNED_SETTINGS`, constructor refuses unpinned keys):
`n_ctx 4096, -ngl 0, threads 6, temperature 0.0, top_k 1, top_p 1.0,
seed 1234, n_predict 256, cache_prompt False`. Full rendered substrate
prompt is sent as ONE user message through the model's embedded Jinja
ChatML template (verbatim, 2506 bytes, sha256
`55b2f4a2…8674a`; BOS `<|endoftext|>`, EOS `<|im_end|>`; default Qwen
system message applies). Tokenizer quirk logged by the server and preserved:
``control-looking token 128247 '</s>' was not control-type; type overridden``
(benign metadata issue, recorded for review).

## 5. Exact tokenizer evidence (model counts, not estimates)

Via the model's own `/tokenize` on a synthetic fixture prompt:
**100 model tokens vs 67 whitespace-estimate tokens (ratio ≈ 1.49×).**
Smoke-trace prompt (templated): 133 model tokens. This confirms review
criterion §7.1: whitespace estimates must never be reported as measurements.
Budget implication flagged in §8.

## 6. Deterministic synthetic smoke test (INFRA ONLY)

`scripts/generator_smoke.py` → `generator_runtime/smoke_trace_*.json`.
**SMOKE: PASS** (5/5: prompt-hash match, generator-id pinned, config
compat via `GeneratorConfig.from_dict().is_pinned()`, citation substring
present, bit-identical repeat under seed 1234). Synthetic answer:
"The synthetic widget tolerance threshold is 5 units… [synth-para-002]".
Honest observation: the model rendered the citation awkwardly as
`[node_id] synth-para-002` (literal placeholder text + id). Fixture answered,
citation machine-present; generator style is Round 1+ business, not a gate
failure — recorded so reviewers see raw behavior, not a summary.

## 7. Load / generation timing (actual local CPU: i7-8700, 6 threads)

| Measurement | Value |
| --- | --- |
| Model load, fresh process → "model loaded" (server log) | **0.86 s** (986 MB mmap, local SSD) |
| Ephemeral spawn → `/health` ready | 1009 ms cold / 1002 ms warm page cache |
| Prompt processing, 133 tok | cold 4528 ms (~29 tok/s) / warm 213 ms (~625 tok/s, page-cache resident) |
| Generation, 28 tok | ~1000 ms (~28 tok/s), stable both runs |
| Independent probe, 39 tok (cache_prompt False) | cold total 9.79 s / warm total 1.86 s; warm decode 25.5 tok/s, encode 92 tok/s |
| Server worker RSS (4 slots × ctx 4096) | peak 1.58 GB / resident 1.46 GB — desktop proxy ONLY |
| Client adapter RSS | 28 MB |

Cold/warm deltas are dominated by OS page cache, reported as such.

## 8. Shared-schema needs — status after substrate evolution (NOT modified)

The shared substrate evolved under separate review during this session and
resolved three of the four v1 needs; this worker aligned without editing it:

1. ~~Config lacks file/bytes/sha/sampling/tokenizer fields~~ RESOLVED by
   review: `GeneratorConfig` now carries `file`, `artifact_sha256`,
   `artifact_bytes`, `tokenizer_id`, `sampling`, `context_window`,
   `generator_id`, with fail-closed `is_pinned()` + `unpinned_fields()`.
   This worker's config reports `unpinned_fields: []`. `from_dict`
   explicitly tolerates this worker's `sha256`/`bytes`/`generation` keys.
2. ~~Estimate/exact unit confusion~~ RESOLVED by review: `GeneratedAnswer`
   now has `exact_evidence_tokens`, `prompt_tokens`, `completion_tokens`;
   `EvidencePacket` has `exact_evidence_tokens`, `prompt_tokens`,
   `token_count_method`; `build_packet(exact=True)` + `packet_within_budget`
   govern on exact tokens. This adapter populates all of them (§0.2).
3. Budget unit: review ruled EXACT tokens govern (code comments + cap
   semantics). Outstanding only in that corpus/questions scale against the
   300–800 exact band is other workers' business. On the fixture:
   evidence 41 exact tokens (whitespace 20) — small fixtures sit far below
   the band; that is expected for infra fixtures, not a finding.
4. Prompt delivery (single user message + default system message + template
   tokens) vs raw `/completion`: still pinned the former, still needs review
   confirmation. Now precisely measurable: user-prompt 104 vs templated 133
   (+29 template/system tokens) on the fixture.

REMAINING shared needs (documented, not edited):
a. No shared emitted-text citation parser (adapter-local regex +
   shared `find_unknown_citations`); a `substrate.parse_emitted_citations`
   would remove the last duplication.
b. `build_packet` keeps a first oversize span (`... and kept` guard) while
   this adapter's `generate()` refuses over-cap evidence outright — the two
   layers disagree by design (builder truncates, generator refuses);
   review should rule which governs the benchmark path.
c. Cross-process determinism at `-t 6` is not bit-exact (see §0); if the
   tournament needs bit-exact reruns, review must pin threads or scope the
   claim to within-session repeat.

## 9. Blockers / handoff

- **No blockers in generator scope.** No fallback was needed; per brief, none
  is adopted without orchestrator decision.
- Freeze still needs (other owners): `corpus/corpus.jsonl`,
  `corpus/questions.json`, `corpus/heldout_labels.sealed.json`, plus
  independent review PASS.
- Reproduce: `python3 scripts/generator_download.py` (verify-only),
  `python3 scripts/generator_adversarial.py` (13 checks, ~40 s, includes
  live-server cap/cleanup tests), `python3 scripts/generator_smoke.py`
  (~15 s). `python3 -m unittest discover -s tests` → 88 pass.

## 10. Artifact inventory (this worker)

`generator_runtime/artifacts/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf`,
`generator_runtime/artifacts/PROVENANCE.json`,
`generator_runtime/qwen25_adapter.py`,
`generator_runtime/smoke_trace_20260928T225743.json` (v1 raw, kept),
`generator_runtime/smoke_trace_v2_*.json` (repair history + current PASS),
`scripts/generator_download.py`, `scripts/generator_smoke.py` (v3, argparse),
`scripts/generator_adversarial.py` (14 checks, argparse),
`scripts/generator_repeat.py` (fresh-process protocol, argparse),
`generator_runtime/smoke_trace_v3_*.json`,
`generator_runtime/repeat_trace_*.json` (plus all preserved older traces),
`corpus/generator_config.json`, `docs/generator-readiness.md`.
