# Generator live /props template check

SYNTHETIC STATUS QUERY ONLY. Not a benchmark, architecture result, or
model-quality measurement. No benchmark, public-bounty, or held-out
questions were issued. No generation was performed (no `/tokenize`,
`/apply-template`, `/completion`, or `/v1/chat/completions` calls).

## Method

`scripts/generator_template_check.py` (new, owned by this worker):

1. Read `corpus/generator_config.json` (read-only) and snapshot its
   SHA-256.
2. Hash the pinned `llama-server` binary (realpath).
3. Spawn the pinned ephemeral server for the fixed config:
   `llama-server -m <artifact> --port <free> -c 4096 -ngl 0 -t 1
   --log-disable` with `LD_LIBRARY_PATH=<lib_dir>`.
4. Wait on `GET /health`, then issue exactly one status read:
   `GET /props`.
5. Extract the `chat_template` string field, hash it (SHA-256 over
   UTF-8 bytes), and compare against the config expectation.
6. Terminate, reap, and verify the port is closed.

If `/props` lacked a string `chat_template` field, the absence
(keys, field type) would be recorded exactly, never inferred.
On this run the field was present as a string.

## Result: MATCH

| Quantity | Value |
|----------|-------|
| Live `/props` `chat_template` SHA-256 | `55b2f4a26ac9ee719330a61a0c39d9e538b0e9322212f048326318cff4f8674a` |
| Expected `tokenizer_gguf.chat_template_runtime_sha256` | `55b2f4a26ac9ee719330a61a0c39d9e538b0e9322212f048326318cff4f8674a` |
| Top-level `chat_template_sha256` (same runtime string) | `55b2f4a26ac9ee719330a61a0c39d9e538b0e9322212f048326318cff4f8674a` |
| Live template bytes (UTF-8) | `2506` (matches config `chat_template_bytes_runtime_props`) |
| Config snapshot SHA-256 (`corpus/generator_config.json` bytes) | `5f0975d665367bdfa855b5a46bc5c335590277726bd4b4bd8d08bb8be3bda9fc` |
| Server binary SHA-256 (live) | `5a5aa40edb8d5aee3638ff292c1e676b934fdb48a9b50029338e2600da4b128f` |
| Server binary SHA-256 (expected) | `5a5aa40edb8d5aee3638ff292c1e676b934fdb48a9b50029338e2600da4b128f` |
| Server binary match | `true` |
| `/props` keys observed | `bos_token, build_info, chat_template, chat_template_caps, cors_proxy_enabled, default_generation_settings, endpoint_metrics, endpoint_props, endpoint_slots, eos_token, is_sleeping, media_marker, modalities, model_alias, model_ftype, model_path, total_slots, ui, ui_settings` |
| Server spawn | `-c 4096 -ngl 0 -t 1 --log-disable`, fresh ephemeral process |
| Cleanup | `terminated_cleanly=true, reaped=true, port_closed=true, server_process_gone=true` |

This closes the v03 residual gap: the live runtime template
(`what /apply-template actually uses`) now has a measured
cross-check against the pinned config value, on top of the prior
nominal/byte comparisons.

## Artifacts

- Script: `scripts/generator_template_check.py`
- Trace: `generator_runtime/template_check_20260929T130348.json`
  (includes full live template string, exact hashes, server command,
  and close report; script stdout omits the template body)
- This note: `docs/generator-template-check.md`

## Provenance

- Worker model: `opencode/muse-spark-1.3-contributor-free`
  (verified free endpoint; no nested workers spawned).
- Generator: `qwen25-1.5b-q4km-fixed-v1`
  (`bartowski/Qwen2.5-1.5B-Instruct-GGUF`
  @ `9eadc66189c7641e1ddd226b8267a9119b2ce2d4`).
- No endpoint substitutions or startup failures on this run.
- Adapter, config, substrate, and prompts were read-only; nothing
  outside the three owned paths was modified.
- Load timing in the trace is a fresh-process wall time only; OS
  page-cache state was not controlled, so it is not a cold-cache
  measurement. No desktop-to-Android performance claim is made.
