# Generator Adapter Independent Review

**Reviewer**: Independent subagent (Nemotron 3 Ultra Free, verified zero-cost)
**Date**: 2026-09-28
**Scope**: `generator_runtime/qwen25_adapter.py`, `scripts/generator_adversarial.py`, `scripts/generator_smoke.py`, `corpus/generator_config.json`, preserved raw smoke traces

---

## VERDICT: **REPAIR REQUIRED**

The generator adapter implementation is **structurally sound** with correct contract enforcement, but **four blocking defects** require repair before freeze. Two are script infrastructure bugs; two are config drift items pending shared-substrate integration.

### Provenance Note
This review was conducted on a moving substrate: the shared `substrate/generator.py` was updated from prompt v0.1 to v0.2 *after* the preserved smoke traces were generated, but *before* this review executed its adversarial checks. The preserved traces reflect the v0.1 prompt; the current substrate reflects v0.2. The config file still contains the v0.1 `prompt_hash`. This review initially misattributed the smoke trace's `[node_id]` emission to the v0.2 prompt; that has been corrected below.

---

## PASS — Verified Contract Enforcement

| Check | Evidence |
|-------|----------|
| **Config drift protection** | `ConfigDriftError` raised for: differing values (`drift-value`), unknown keys (`drift-key`), tampered `prompt_hash` (`drift-config`). Identical values accepted (`drift-identical`). Adversarial: 3/3 PASS. |
| **Pinned runtime/model hash enforcement** | `prepare()` verifies: llama-server binary SHA256, 8 shared-library SHA256s, model file size + SHA256. Tampered binary hash rejected (`runtime-bin`: PASS). Missing binary fails fast (`runtime-exe`: PASS). |
| **Chat-template accounting** | Three exact token counts recorded separately: `evidence_tokens` (canonical serialization), `user_prompt_tokens` (rendered prompt), `templated_input_tokens` (`/apply-template` output). Cross-check: `usage.prompt_tokens == templated_input_tokens` enforced at line 405-408. Smoke trace confirms: `usage_matches_templated: true`. |
| **Emitted/unknown citation parser** | `_CITATION_RE` extracts `[id]` tokens from emitted text. `parse_citations()` delegates unknown-id detection to shared `find_unknown_citations()`. Returns `{cited_valid, cited_unknown, available_not_cited}`. Adversarial `citations` check: PASS. |
| **Cleanup on errors** | `generate()` `finally` block calls `session.close()` → `_ServerProc.stop()` → `terminate → wait → kill → wait`, always reaps. `reaped=True`, `port_closed=True` verified in adversarial `cleanup` and smoke `server_process_gone`. |
| **Offline local only** | All `urllib`/`socket` calls target `127.0.0.1` only. No external network access in adapter. Config `download_url` is metadata only. |
| **Warm vs process-cold telemetry** | `server_load_ms` (fresh process) recorded once per session. Per-generation: `http_generate_ms`, `prompt_ms`, `predicted_ms`, `prompt_n`, `predicted_n`. Smoke trace shows distinct `run1_timings_ms` vs `run2_warm_timings_ms`. |
| **Exact evidence cap enforcement** | `_account()` checks `ev_tokens > HARD_EVIDENCE_TOKEN_CAP` (1000) pre-generation, raises `EvidenceOverBudgetError`. Adversarial `overbudget`: PASS. |
| **Usage counts recorded** | `last_token_accounting` captures: `evidence_tokens`, `user_prompt_tokens`, `templated_input_tokens`, `usage_prompt_tokens`, `usage_completion_tokens`. All present in smoke trace `token_accounting_run1`. |
| **Adversarial suite executed this review** | 13/13 checks PASS (drift-value, drift-key, drift-identical, drift-config, exact-guard, exact-id-guard, citations, runtime-bin, runtime-exe, early-exit, overbudget, cap-enforce, cleanup). **Note**: These tests do not exercise the *current* config/substrate `prompt_hash` mismatch (config has v0.1 hash, substrate has v0.2). The `drift-config` test tampered a temp config to `"0"*64`; it did not test the live config file against the live substrate. |

---

## REPAIR REQUIRED — Blocking Defects

### 1. Script `--help` Side Effect (CRITICAL)
**Files**: `scripts/generator_adversarial.py`, `scripts/generator_smoke.py`
**Symptom**: Both scripts execute their full `main()` when passed `--help` instead of printing usage and exiting.
```
$ python3 scripts/generator_adversarial.py --help
[PASS] drift-value ...
[PASS] drift-key ...
...  # entire adversarial suite runs
```
**Root cause**: No `argparse`/`sys.argv` guard; `--root` parsing uses `sys.argv.index("--root")` which throws `ValueError` if absent, but `--help` is silently ignored and falls through to default root `"."`.
**Impact**: Prior worker "accidentally ran smoke via --help". CI/help invocations produce synthetic runs and pollute trace directory.
**Fix**: Add proper argument parsing with `--help` handling before any side effects.

### 2. Config Drift: `prompt_hash` Mismatch (BLOCKING)
**File**: `corpus/generator_config.json` (line 27)
**Current config**: `"prompt_hash": "dfe7b0a67f83e8e5b0bad2accb7893754271c1d2cf6da571c85646955d90df45"` (v0.1 prompt)
**Substrate `PROMPT_HASH`**: `d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63` (v0.2 prompt)
**Adapter behavior**: `ConfigDriftError: config prompt_hash does not match substrate PROMPT_HASH` — correctly rejects.
**Context**: Shared substrate lead updated prompt to v0.2 (rewrote citation instruction to avoid literal `[node_id]` emission). Config not synced. **Do not revert substrate** — update config to new hash after validation.
**Preserved smoke trace provenance**: `smoke_trace_v2_20260928T231234.json` records `"prompt_hash": "dfe7b0a67f83e8e5b0bad2accb7893754271c1d2cf6da571c85646955d90df45"` (line 49) and `"prompt_hash_matches_substrate": true` (line 50). This confirms the trace was generated with the v0.1 prompt, when substrate and config matched. The `[node_id]` emission observed in that trace is from the v0.1 prompt, NOT the current v0.2 prompt.

### 3. Config Drift: `runtime_threads_measured` (BLOCKING)
**File**: `corpus/generator_config.json` (line 83)
**Current config**: `"runtime_threads_measured": 6`
**Orchestrator ruling**: Fixed generator → `threads=1` (based on worker cross-process variance).
**Adapter behavior**: Reads config value at line 269. Config drift error would be raised if caller overrides, but config itself is stale.
**Impact**: Benchmark reproducibility requires `threads=1` freeze. Config must be updated before freeze.

### 4. `chat_template_sha256` Field Naming Ambiguity (Not a Duplicate Key Defect)
**File**: `corpus/generator_config.json` (lines 5, 94-95)
- Top-level `"chat_template_sha256": "55b2f4a26ac9ee719330a61a0c39d9e538b0e9322212f048326318cff4f8674a"` — matches `tokenizer_gguf.chat_template_runtime_sha256` (llama-server `/props` string, GGUF bytes minus trailing newline).
- `tokenizer_gguf.chat_template_sha256: "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"` — GGUF-header raw bytes (pinned in adapter as `PINNED_GGUF_TEMPLATE_SHA256`).
**Issue**: Two different SHA256s labeled `chat_template_sha256` in same file (top-level vs nested). This is a **naming ambiguity** (raw-GGUF vs runtime-normalized), not a JSON duplicate-key defect. Adapter pins the GGUF-header value (line 60-61). **Rename top-level field** to `chat_template_runtime_sha256` for clarity.

---

## MEASURED MODEL LIMITATIONS (Not Defects — Record Honestly)

| Limitation | Evidence | Grading |
|------------|----------|---------|
| **Model emits literal `[node_id]` under v0.1 prompt** | Preserved trace `smoke_trace_v2_20260928T231234.json`: `"answer_text": "...provided in [node_id] synth-para-002."` → `citation_audit.cited_unknown: ["node_id"]`, `"prompt_hash": "dfe7b0a67f83e8e5b0bad2accb7893754271c1d2cf6da571c85646955d90df45"` (v0.1). | Trace generated with v0.1 prompt (config and substrate matched at that time). Adapter correctly flags `node_id` as `cited_unknown`. **Not an adapter bug.** Current v0.2 prompt behavior untested in preserved traces. |
| **Empty `cited_valid` on synthetic fixture** | Smoke trace: `cited_valid: []`, `available_not_cited: ["synth-para-001", "synth-para-002"]` | Model cites placeholder `[node_id]` instead of actual node ids under v0.1 prompt. Adapter records honestly. |
| **Deterministic repeat identical** | Smoke trace: `deterministic_repeat_identical: true` | Expected for greedy (temp=0, seed=1234). Confirmed. |

---

## PENDING INTEGRATION ITEMS (Tracked, Not Duplicated)

Per orchestrator: shared substrate lead owns these; do not require old hashes to stay.

| Item | Location | Status |
|------|----------|--------|
| Evidence packet nonadditive full-serialization token counting | `substrate/evidence.py:91` (`serialize_evidence(kept + [span])` re-tokenizes prefix each step) | **Delivered** — 113 tests independently run by shared substrate lead |
| Oversize first span → empty packet + `truncated=True` | `substrate/evidence.py:92-94` | **Documented behavior** (valid abstention outcome), not an active bug |
| Prompt `[node_id]` confusion | v0.2 prompt rewrite in substrate; preserved traces used v0.1 | Integration underway by lead (threads=1, new config hash, `--help` guards, shared emitted-citation parser). Do not execute scripts during integration. |

---

## RAW REPRODUCIBLE EVIDENCE

### Adversarial Run (Executed This Review: 2026-09-28)
**Command**: `python3 scripts/generator_adversarial.py --root .`
**Exit code**: 0
**Config hash at execution** (corpus/generator_config.json): `prompt_hash = dfe7b0a67f83e8e5b0bad2accb7893754271c1d2cf6da571c85646955d90df45` (v0.1)
**Substrate hash at execution** (substrate/generator.py): `PROMPT_HASH = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63` (v0.2)
**Note**: Adversarial tests do not instantiate `LlamaCppGenerator` with the live config/substrate mismatch. The `drift-config` test creates a temp config with `"prompt_hash": "0"*64`; the live config file's v0.1 hash vs live substrate's v0.2 hash is not exercised by these tests.
```
ADVERSARIAL: PASS (13/13)
[PASS] drift-value differing temperature rejected
[PASS] drift-key unknown key rejected
[PASS] drift-identical identical values accepted
[PASS] drift-config tampered prompt_hash rejected
[PASS] exact-guard exact=True without tokenizer refused
[PASS] exact-id-guard tokenizer without id refused
[PASS] citations audit={'cited_valid': ['synth-para-001'], 'cited_unknown': ['ghost-node-999'], 'available_not_cited': ['synth-para-002']}
[PASS] runtime-bin tampered binary hash rejected
[PASS] runtime-exe fast failure: server binary missing: /nonexistent/llama-server
[PASS] early-exit diagnosed+reaped: llama-server exited early with code 1: 
[PASS] overbudget refused pre-generation: exact evidence tokens 5008 exceed cap 1000
[PASS] cap-enforce finish=length completion=4
[PASS] cleanup close_report={'reaped': True, 'port_closed': True, 'terminated_cleanly': True, 'returncode': 0} gone=True
```

### Preserved Smoke Trace v2 (`smoke_trace_v2_20260928T231234.json`) — NOT RE-RUN THIS REVIEW
**Generated**: 2026-09-28T23:12:34 (prior worker)
**Recorded `prompt_hash`**: `dfe7b0a67f83e8e5b0bad2accb7893754271c1d2cf6da571c85646955d90df45` (v0.1)
**Recorded `prompt_hash_matches_substrate`**: `true` (substrate matched config at generation time)
**Recorded `answer_text`**: `"The synthetic widget tolerance threshold is 5 units. This information is provided in [node_id] synth-para-002."`
**Recorded `citation_audit.cited_unknown`**: `["node_id"]`
**Key fields**:
```json
{
  "generator_id_pinned": true,
  "prompt_hash_matches_substrate": true,
  "config_pinned_compat": true,
  "evidence_text_matches_render_prompt": true,
  "packet_method_is_exact_tokenizer": true,
  "packet_exact_matches_adapter": true,
  "answer_exact_matches_packet": true,
  "answer_estimate_is_whitespace": true,
  "answer_prompt_tokens_match_usage": true,
  "answer_completion_tokens_match_usage": true,
  "evidence_within_cap": true,
  "usage_matches_templated": true,
  "completion_within_max_tokens": true,
  "parser_complete_all_emitted_ids_classified": true,
  "answer_citations_mapping_correct": true,
  "citations_subset_of_packet": true,
  "deterministic_repeat_identical": true,
  "session_close_report": {"reaped": true, "port_closed": true, "terminated_cleanly": true, "returncode": 0},
  "server_process_gone": true,
  "token_accounting_run1": {
    "evidence_tokens": 41,
    "templated_input_tokens": 133,
    "usage_completion_tokens": 28,
    "usage_prompt_tokens": 133,
    "user_prompt_tokens": 104
  },
  "citation_audit": {
    "cited_valid": [],
    "cited_unknown": ["node_id"],
    "available_not_cited": ["synth-para-001", "synth-para-002"]
  }
}
```

### Preserved v1 Smoke Trace (`smoke_trace_20260928T225743.json`)
- Different timing profile (cold `http_generate_ms`: 5542 vs warm 1214)
- Same `[node_id]` emission observed
- `exact_model_evidence_tokens: 104` (whitespace estimate: 20)
- Also records v0.1 `prompt_hash` (implicit via `prompt_hash_matches_substrate: true` at that time)

---

## REQUIRED REPAIRS BEFORE FREEZE

1. **Fix `--help` handling** in both scripts (add `argparse`, exit 0 on `--help`).
2. **Update `corpus/generator_config.json`**:
   - `prompt_hash` → `d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63` (v0.2 substrate hash)
   - `runtime_threads_measured` → `1` (orchestrator ruling)
   - Rename top-level `chat_template_sha256` → `chat_template_runtime_sha256` (disambiguate from `tokenizer_gguf.chat_template_sha256` = raw GGUF header)
3. **Re-run adversarial + smoke** after config sync; verify `PASS` with new hashes.
4. **Preserve new raw traces** alongside existing v1/v2 traces (do not overwrite).

**Integration status**: Generator integration currently underway by lead (threads=1, new config hash, `--help` guards, shared emitted-citation parser). Do not execute scripts while being edited or request progress. This review only provides factual corrections; a new re-review on stable snapshot follows integration.

---

## SIGN-OFF

**Adapter implementation**: PASS on all contract enforcement, token accounting, citation parsing, cleanup, offline-only, telemetry separation, evidence cap, usage counts.

**Blocking defects**: 4 (2 script bugs, 2 config drift items).

**Model limitations**: Documented honestly; no blanket citation correctness claimed. Preserved traces reflect v0.1 prompt; v0.2 prompt behavior untested.

**Ready for freeze**: **NO** — config sync and script `--help` fixes required first.

**Evidence gaps**: No preserved trace with v0.2 prompt (substrate updated after traces generated). No adversarial test exercises live config/substrate prompt_hash mismatch. New re-review required on stable post-integration snapshot.

---
*Review conducted per master_orchestration_prompt.txt scientific gates. No held-out data inspected. No paid endpoints used.*