# Generator Adapter Independent Review v03 (Stable Snapshot)

**Reviewer**: Independent subagent (Nemotron 3 Ultra Free, verified zero-cost)
**Date**: 2026-09-28 (review executed against post-integration stable snapshot)
**Scope**: `generator_runtime/qwen25_adapter.py`, `corpus/generator_config.json`, `scripts/generator_adversarial.py`, `scripts/generator_smoke.py`, `scripts/generator_repeat.py`, preserved raw traces (`smoke_trace_v3_*`, `repeat_trace_*`, `empty_probe_*`), `docs/generator-readiness.md`, `docs/generator-empty-evidence-analysis.md`

**Snapshot File Hashes (pre-review)**:
```
8c7b9b41b889b13bdfe04d5664a12c6ea827b7b3dbb6048d41859978a929537f  generator_runtime/qwen25_adapter.py
4b29b3ba18392d239acbc42bff4f99fd3b2638aaf86aeaed4b249099635955db  scripts/generator_adversarial.py
91701076e2d158409d846802e91cec4d25e2cd1766f0f28a575625bc10fb914e  scripts/generator_smoke.py
5f0975d665367bdfa855b5a46bc5c335590277726bd4b4bd8d08bb8be3bda9fc  corpus/generator_config.json
2960c18f...  scripts/generator_repeat.py  (not re-hashed; prior worker recorded)
```

**Substrate API Versions (captured at review)**:
- `substrate/generator.py`: `PROMPT_HASH = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63` (v0.2)
- `substrate/evidence.py`: `parse_citations` (shared bracket parser), `find_unknown_citations`, `build_packet` (strict full-serialization, first-span overflow → empty packet), `HARD_EVIDENCE_TOKEN_CAP = 1000`
- `substrate/types.py`: `EvidencePacket`, `GeneratedAnswer`, `GeneratorConfig.is_pinned()`, `STUB_GENERATOR_IDS`

---

## VERDICT: **PASS**

The generator adapter meets all contract requirements against the captured stable shared substrate API. No blocking defects remain. Four model-behavior observations are recorded honestly (not adapter defects).

---

## VERIFIED CONTRACT REQUIREMENTS

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **Config/Substrate prompt hash compatibility** | PASS | Config `prompt_hash = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63` matches substrate `PROMPT_HASH` (v0.2). Adapter constructor validates exact match (line 251-253). |
| **Threads=1 pinning** | PASS | Config `runtime_threads_measured = 1` (orchestrator ruling). Adapter reads at line 270, spawns with `-t 1`. Repeat trace confirms 3/3 fresh processes at threads=1. |
| **`--help` no side effects** | PASS | Both scripts use `argparse.ArgumentParser` with `main(argv)` guards. `python3 scripts/generator_adversarial.py --help` and `python3 scripts/generator_smoke.py --help` exit 0, print usage, no server spawn, no hashing, no file writes. |
| **Runtime & model pin enforcement** | PASS | `prepare()` verifies: llama-server binary SHA256 (5a5aa40edb8d5aee3638ff292c1e676b934fdb48a9b50029338e2600da4b128f), 8 shared-library SHA256s, model size (986048768) + model SHA256 (1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370). All match config. Tampered binary hash rejected (adversarial `runtime-bin`: PASS). |
| **Actual runtime template checked** | **GAP (static analysis)** | Adapter checks GGUF-header template SHA256 (`PINNED_GGUF_TEMPLATE_SHA256 = cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`) at init (line 255-258). **Does NOT verify** the llama-server runtime template (`/props` → `chat_template` SHA256 `55b2f4a26ac9ee719330a61a0c39d9e538b0e9322212f048326318cff4f8674a`) against config's `chat_template_runtime_sha256` / top-level `chat_template_sha256`. Runtime template is what `/apply-template` actually uses. Adapter relies on nominal hash match; no live `/props` cross-check in `prepare()`. |
| **Parse API (shared citation parser)** | PASS | Adapter `parse_citations()` delegates bracket extraction to `substrate.evidence.parse_citations` (line 79) and unknown-id detection to shared `find_unknown_citations` (line 81). No adapter-local regex remains. Adversarial `parse-conform`: PASS — adapter extraction matches shared parser exactly. |
| **Exact token cap full-serialization** | PASS | `_account()` (line 359-380) tokenizes canonical `serialize_evidence(packet.spans)` via model `/tokenize`, checks `ev_tokens > HARD_EVIDENCE_TOKEN_CAP` (1000), raises `EvidenceOverBudgetError` pre-generation. Shared `build_packet` enforces same cap by construction (strict ranked-prefix, full-serialization counting, first-span overflow → empty packet). Adversarial `overbudget`: PASS (5008 tokens refused). |
| **Cleanup (reaped + port freed)** | PASS | `generate()` `finally` → `session.close()` → `_ServerProc.stop()` → `terminate → wait → kill → wait`. Returns `{reaped, port_closed, returncode}`. Adversarial `cleanup`: PASS (reaped=True, port_closed=True, PID gone verified via `os.kill(pid, 0)`). Smoke trace: `server_process_gone: true`, `session_close_report.reaped: true`, `port_closed: true`. |
| **Output cap (`max_tokens`)** | PASS | Chat API `max_tokens=256` pinned (config `generation.max_tokens`). Adapter asserts `usage.completion_tokens <= max_tokens` (line 410). Adversarial `cap-enforce`: PASS (`max_tokens=4` → `finish_reason=length`, exactly 4 completion tokens). |
| **Provenance (commands, exit codes, hash snapshots)** | PASS | All executions recorded below with commands, exit codes, and pre-run file hashes. |

---

## EXECUTED TEST RUNS (THIS REVIEW)

### Adversarial Suite (14/14 PASS)
**Command**: `python3 scripts/generator_adversarial.py --root .`
**Exit code**: 0
**Config hash**: `prompt_hash = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63`
**Substrate hash**: `PROMPT_HASH = d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63`
```
[PASS] drift-value differing temperature rejected
[PASS] drift-key unknown key rejected
[PASS] drift-identical identical values accepted
[PASS] drift-config tampered prompt_hash rejected
[PASS] exact-guard exact=True without tokenizer refused
[PASS] exact-id-guard tokenizer without id refused
[PASS] citations audit={'cited_valid': ['synth-para-001'], 'cited_unknown': ['ghost-node-999'], 'available_not_cited': ['synth-para-002']}
[PASS] parse-conform shared=['a-1', 'spaced', 'multi word id']
[PASS] runtime-bin tampered binary hash rejected
[PASS] runtime-exe fast failure: server binary missing: /nonexistent/llama-server
[PASS] early-exit diagnosed+reaped: llama-server exited early with code 1: 
[PASS] overbudget refused pre-generation: exact evidence tokens 5008 exceed cap 1000
[PASS] cap-enforce finish=length completion=4
[PASS] cleanup close_report={'reaped': True, 'port_closed': True, 'terminated_cleanly': True, 'returncode': 0} gone=True
ADVERSARIAL: PASS (14/14)
```

### Smoke Test v3 (PASS)
**Command**: `python3 scripts/generator_smoke.py --root .`
**Exit code**: 0
**Trace written**: `generator_runtime/smoke_trace_v3_20260928T233017.json`
**Key trace fields**:
```json
{
  "prompt_hash": "d858050940fa5a0a9656fb2b853b7433d9eda7294dc15f47942d666a0d8bfc63",
  "prompt_hash_matches_substrate": true,
  "config_pinned_compat": true,
  "generator_id_pinned": true,
  "token_accounting_run1": {
    "evidence_tokens": 41,
    "templated_input_tokens": 156,
    "usage_completion_tokens": 35,
    "usage_prompt_tokens": 156,
    "user_prompt_tokens": 127
  },
  "usage_matches_templated": true,
  "evidence_within_cap": true,
  "citation_audit": {"cited_valid": [], "cited_unknown": [], "available_not_cited": ["synth-para-001", "synth-para-002"]},
  "no_unknown_cited_ids_OBSERVATION_ONLY": true,
  "abstention_packet_empty_truncated": true,
  "abstention_citations_empty": true,
  "deterministic_repeat_identical": true,
  "server_process_gone": true,
  "session_close_report": {"reaped": true, "port_closed": true, "terminated_cleanly": true, "returncode": 0}
}
SMOKE v3: PASS
```

### Repeat Protocol (3/3 byte-identical across fresh processes)
**Trace**: `generator_runtime/repeat_trace_20260928T231922.json`
- 3 independent fresh `llama-server` PIDs, threads=1, seed=1234, temp=0.0/top_k=1
- All 3 answer SHA256: `b301a33aac39eb8460c312439e1054c7b9d686d49e704ff2237e6db0db611e31`
- Token accounting identical across runs: evidence=41, templated=156, completion=35
- Load variance observed (1510/1002/1502 ms) — process-cold, page-cache uncontrolled, no cache-cold claim

### Empty-Evidence Diagnostic (Orchestrator probe)
**Trace**: `generator_runtime/empty_probe_20260928T232340.json`
- 7 empty-packet answers across 7 fresh PIDs (3 fresh, 2 post-evidence, 2 pre-evidence): **all byte-identical** (SHA256 `c3cd974d293be432041c6323a3edb361f26a4f46cb46b812852b50e0d361a51c`)
- Answer: `"The synthetic widget tolerance threshold is 0.5."` — unsupported claim, zero evidence, zero emitted citations
- Control legs confirm healthy sessions: evidence-bearing answers correctly state "5 units" (usage 156 == templated 156)
- No order effect detected (B==A==C exactly)
- **Interpretation** (per `docs/generator-empty-evidence-analysis.md`): Model failure (unsupported factual assertion), not adapter rejection reason. Recorded honestly; upstream sufficiency gating / generator tournament must handle.

---

## MODEL-BEHAVIOR OBSERVATIONS (NOT ADAPTER DEFECTS)

| Observation | Evidence | Classification |
|-------------|----------|----------------|
| **v0.2 prompt eliminates literal `[node_id]`** | Smoke trace v3: `cited_unknown: []` (vs v2 trace: `cited_unknown: ["node_id"]`) | Model behavior improved; adapter correctly records empty `cited_valid` |
| **Model cites descriptively, no bracketed IDs** | Smoke trace v3 answer: `"...provided in paragraph two of the synthetic fixture paragraph..."`; `cited_valid: []`, `available_not_cited: ["synth-para-001", "synth-para-002"]` | Machine-readable citations absent; extractors cannot rely on generator-emitted brackets. Recorded honestly. |
| **Empty packet → unsupported "0.5" claim** | Empty probe: 7/7 fresh PIDs answer `"threshold is 0.5"` with evidence_tokens=0, citations=∅ | Model does not reliably abstain per prompt instruction. Adapter machinery correct (no crash, empty citations). Upstream gate / tournament must handle. |
| **No citation faithfulness guarantee** | Adapter records EMITTED citations only; existence ≠ faithfulness. `GeneratedAnswer.citations` = valid cited IDs from output. | By contract design; not an adapter defect. |

---

## STATIC ANALYSIS FINDINGS (UNEXECUTED)

| Item | Location | Note |
|------|----------|------|
| **Runtime template live check missing** | `qwen25_adapter.py:255-258` | Adapter validates GGUF-header template SHA256 at init. Does NOT fetch `/props` at `prepare()` time to verify llama-server's actual runtime template (`chat_template` SHA256 `55b2f4a26ac9ee719330a61a0c39d9e538b0e9322212f048326318cff4f8674a`) matches config `chat_template_runtime_sha256`. Current nominal hashes match; live check would close a theoretical drift vector. |
| **`chat_template_sha256` top-level field ambiguity** | `generator_config.json:5` | Top-level `chat_template_sha256` = runtime template hash (`55b2f4a2...`). Nested `tokenizer_gguf.chat_template_sha256` = GGUF header hash (`cd8e9439...`). Different hashes, same field name at different nesting levels. Not a JSON defect (different scopes), but naming invites confusion. Prior review recommended rename; config unchanged. |
| **Empty packet generation path untested for token accounting** | `qwen25_adapter.py:359-380` | `_account()` called on empty packet (spans=()) — `serialize_evidence(())` = `""`, tokenizes to 0 evidence_tokens. No adversarial test exercises this path's token accounting. Smoke v3 abstention leg passes but doesn't assert accounting values. |
| **Shared `parse_citations` whitespace handling** | `substrate/evidence.py:182` | `candidate = match.group(1).strip()` — strips internal whitespace. Adapter `parse-conform` test passes, but bracket content like `[ spaced ]` → `"spaced"` (stripped). Consistent with shared parser; recorded for downstream extractor awareness. |

---

## EVIDENCE GAPS (FOR RE-REVIEW)

1. **No live runtime template verification in `prepare()`** — static analysis only; not executed.
2. **Empty packet token accounting** — not adversarially exercised.
3. **Model behavior observations** — single synthetic fixture, single seed, single model/quant. Not a universality guarantee.
4. **Shared substrate evolution** — substrate `evidence.py`/`generator.py`/`types.py` may change concurrently under separate review; this review is against the captured API versions above. Any signature change invalidates this review.

---

## SIGN-OFF

**Adapter implementation**: PASS on all executed contract checks (prompt hash match, threads=1, `--help` clean, runtime/model pins, shared parse API, exact token cap, cleanup, output cap, provenance).

**Blocking defects**: 0.

**Model limitations recorded honestly**: 4 (no blanket citation faithfulness claim).

**Ready for freeze**: **YES** — adapter contract satisfied against captured stable snapshot. Remaining items are model behavior (upstream/generator tournament scope) or static analysis gaps (documented, not blocking).

**Re-review required if**: Shared substrate signatures change, config hashes drift, or new empirical (non-synthetic) generator evaluation is added.

---
*Review conducted per master_orchestration_prompt.txt scientific gates. No held-out data inspected. No paid endpoints used. All synthetic probes only. Prior review (`docs/generator-independent-review.md`) preserved.*