#!/usr/bin/env python3
"""Live /props chat-template cross-check (SYNTHETIC STATUS QUERY ONLY).

Starts the pinned ephemeral llama-server for the fixed Qwen2.5-1.5B
Q4_K_M config, performs exactly two status reads (GET /health for
readiness, GET /props for the template string), hashes the live
template, and compares it against
corpus/generator_config.json
``tokenizer_gguf.chat_template_runtime_sha256`` (primary) and the
top-level ``chat_template_sha256`` (recorded for disambiguation).

No benchmark, public-bounty, or held-out questions. No generation:
no /tokenize, /apply-template, /completion, or /v1/chat/completions
calls. If /props lacks a template field, that absence is recorded
exactly -- never inferred.

Writes generator_runtime/template_check_<UTC-ts>.json.
Usage: python3 scripts/generator_template_check.py [--root .]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

CONFIG_REL = os.path.join("corpus", "generator_config.json")
EXPECTED_KEY_NESTED = ("tokenizer_gguf", "chat_template_runtime_sha256")
TEMPLATE_FIELD = "chat_template"


def sha256_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def sha256_str(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8")).hexdigest()


def free_port() -> int:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    return int(sock.getsockname()[1])


def port_closed(port: int) -> bool:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(2.0)
    return sock.connect_ex(("127.0.0.1", port)) != 0


def http_get(base: str, path: str, timeout_s: int = 30) -> bytes:
  with urllib.request.urlopen(base + path, timeout=timeout_s) as resp:
    return resp.read()


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    description="Synthetic live /props template cross-check.")
  parser.add_argument("--root", default=".",
                      help="repository root (default: .)")
  parser.add_argument("--timeout-s", type=float, default=120.0,
                      help="server readiness timeout (default: 120)")
  args = parser.parse_args(argv)
  root = args.root

  config_path = os.path.join(root, CONFIG_REL)
  with open(config_path, "rb") as fh:
    config_bytes = fh.read()
  config_snapshot_sha256 = hashlib.sha256(config_bytes).hexdigest()
  config = json.loads(config_bytes.decode("utf-8"))

  expected_runtime = (config.get("tokenizer_gguf") or {}).get(
    "chat_template_runtime_sha256")
  expected_top = config.get("chat_template_sha256")
  expected_bytes_cfg = (config.get("tokenizer_gguf") or {}).get(
    "chat_template_bytes_runtime_props")

  model_path = os.path.join(root, config["artifact_path"])
  lib_dir = config["runtime_binaries"]["lib_dir"]
  bin_path_cfg = config["runtime_binaries"]["llama-server"]["path"]
  expected_bin_sha = config["runtime_binaries"]["llama-server"]["sha256"]
  real_bin = os.path.realpath(bin_path_cfg)
  live_bin_sha = sha256_file(real_bin)
  bin_match = live_bin_sha == expected_bin_sha

  n_ctx = int(config["context_window_pinned"])
  threads = int(config["runtime_threads_measured"])
  port = free_port()
  base = f"http://127.0.0.1:{port}"
  cmd = [real_bin, "-m", model_path, "--port", str(port),
         "-c", str(n_ctx), "-ngl", "0", "-t", str(threads),
         "--log-disable"]
  env = dict(os.environ)
  env["LD_LIBRARY_PATH"] = lib_dir + ":" + env.get("LD_LIBRARY_PATH", "")

  proc: subprocess.Popen[bytes] | None = None
  load_ms: float | None = None
  props_raw: bytes | None = None
  props_keys: list[str] = []
  template_present = False
  template_field_type: str | None = None
  live_template = ""
  live_sha: str | None = None
  live_bytes: int | None = None
  startup_error: str | None = None
  server_pid: int | None = None
  t0 = time.perf_counter()
  try:
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE)
    assert proc.stderr is not None
    server_pid = proc.pid
    deadline = time.perf_counter() + float(args.timeout_s)
    last_err: str | None = None
    ready = False
    while time.perf_counter() < deadline:
      if proc.poll() is not None:
        try:
          _, err = proc.communicate(timeout=10)
          tail = (err or b"").decode("utf-8", "replace")[-2000:]
        except (subprocess.TimeoutExpired, ValueError):
          tail = ""
        startup_error = (f"llama-server exited early with code "
                         f"{proc.returncode}: {tail}")
        break
      try:
        with urllib.request.urlopen(base + "/health", timeout=5) as resp:
          if resp.status == 200:
            ready = True
            break
      except OSError as exc:
        last_err = str(exc)
        time.sleep(0.5)
    if not ready and startup_error is None:
      startup_error = (f"llama-server not ready after "
                       f"{float(args.timeout_s)}s (last error: {last_err})")
    if startup_error is None:
      load_ms = (time.perf_counter() - t0) * 1000.0
      # SYNTHETIC STATUS QUERY ONLY: single GET /props, no generation.
      props_raw = http_get(base, "/props", timeout_s=60)
      try:
        props_doc = json.loads(props_raw.decode("utf-8"))
      except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        props_doc = None
        startup_error = f"/props did not return JSON: {exc}"
      if props_doc is not None:
        if isinstance(props_doc, dict):
          props_keys = sorted(str(k) for k in props_doc.keys())
          val = props_doc.get(TEMPLATE_FIELD, None)
          template_field_type = type(val).__name__
          if isinstance(val, str):
            template_present = True
            live_template = val
            live_sha = sha256_str(val)
            live_bytes = len(val.encode("utf-8"))
        else:
          props_keys = []
          template_field_type = f"non-dict-doc:{type(props_doc).__name__}"
  finally:
    close_report: dict[str, object] = {}
    if proc is not None:
      proc.terminate()
      try:
        proc.wait(timeout=15)
        close_report["terminated_cleanly"] = True
      except subprocess.TimeoutExpired:
        proc.kill()
        close_report["terminated_cleanly"] = False
        try:
          proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
          close_report["reap_error"] = "process survived SIGKILL wait"
      try:
        _, err = proc.communicate(timeout=10)
        close_report["stderr_tail"] = (err or b"").decode(
          "utf-8", "replace")[-2000:]
      except (subprocess.TimeoutExpired, ValueError):
        pass
      close_report["returncode"] = proc.returncode
      close_report["reaped"] = proc.poll() is not None
    close_report["port_closed"] = port_closed(port)

  gone = True
  if server_pid is not None:
    try:
      os.kill(server_pid, 0)
      gone = False
    except (ProcessLookupError, PermissionError):
      gone = True

  if startup_error is not None:
    match: bool | None = None
    result = f"ERROR: {startup_error}"
  elif not template_present:
    match = None
    result = (f"NO_TEMPLATE_FIELD: /props lacks a string "
              f"'{TEMPLATE_FIELD}' field (type={template_field_type}; "
              f"keys={props_keys}) -- recorded exactly, not inferred")
  else:
    match = (live_sha == expected_runtime)
    result = "MATCH" if match else "MISMATCH"

  trace = {
    "label": ("SYNTHETIC-STATUS-QUERY-ONLY: live /props template "
              "cross-check; not a benchmark or architecture result"),
    "generator_id": config.get("generator_id"),
    "worker_model": "opencode/muse-spark-1.3-contributor-free",
    "config_path": CONFIG_REL,
    "config_snapshot_sha256": config_snapshot_sha256,
    "expected_chat_template_runtime_sha256": expected_runtime,
    "expected_top_level_chat_template_sha256": expected_top,
    "expected_top_equals_expected_runtime": (expected_top == expected_runtime),
    "expected_runtime_bytes_props": expected_bytes_cfg,
    "server_binary_cfg_path": bin_path_cfg,
    "server_binary_realpath": real_bin,
    "server_binary_sha256_live": live_bin_sha,
    "server_binary_sha256_expected": expected_bin_sha,
    "server_binary_match": bin_match,
    "server_cmd": cmd,
    "server_port": port,
    "server_pid": server_pid,
    "server_n_ctx": n_ctx,
    "server_threads": threads,
    "server_ngl": 0,
    "session_load_ms_fresh_process": load_ms,
    "load_note": ("fresh ephemeral process; OS page-cache state not "
                  "controlled, NOT a cold-cache measurement"),
    "props_endpoint": "/props",
    "props_raw_bytes": len(props_raw) if props_raw is not None else None,
    "props_keys": props_keys,
    "template_field": TEMPLATE_FIELD,
    "template_present_as_string": template_present,
    "template_field_type": template_field_type,
    "live_template_bytes": live_bytes,
    "live_template_sha256": live_sha,
    "live_template": live_template if template_present else "",
    "match_expected_runtime": match,
    "result": result,
    "generation_performed": False,
    "queries_issued": ["GET /health (readiness)", "GET /props (status)"],
    "session_close_report": close_report,
    "server_process_gone": gone,
  }
  out_name = f"template_check_{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}.json"
  out_path = os.path.join(root, "generator_runtime", out_name)
  with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(trace, fh, indent=2, sort_keys=True)
    fh.write("\n")
  print(json.dumps({k: v for k, v in trace.items()
                    if k != "live_template"}, indent=2, sort_keys=True))
  print("trace:", out_path)
  print("RESULT: " + result)
  if startup_error is not None:
    return 2
  if match is True and bin_match:
    return 0
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
