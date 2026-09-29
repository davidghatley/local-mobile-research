#!/usr/bin/env python3
"""Reproducible acquisition of the pinned fixed-generator weight file.

Downloads EXACTLY one file (<=2GB budget):
  bartowski/Qwen2.5-1.5B-Instruct-GGUF @ 9eadc66189c7641e1ddd226b8267a9119b2ce2d4
  file: Qwen2.5-1.5B-Instruct-Q4_K_M.gguf (986,048,768 bytes)
into generator_runtime/artifacts/ and verifies size + SHA-256.

No paid generation APIs. No model config is written here (see
corpus/generator_config.json owned by the same worker).

Usage: python3 scripts/generator_download.py [--root .]
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request

REPO = "bartowski/Qwen2.5-1.5B-Instruct-GGUF"
REVISION = "9eadc66189c7641e1ddd226b8267a9119b2ce2d4"
FILENAME = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
EXPECTED_BYTES = 986048768
EXPECTED_SHA256 = "1adf0b11065d8ad2e8123ea110d1ec956dab4ab038eab665614adba04b6c3370"
URL = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{FILENAME}"


def sha256_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def main() -> int:
  root = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv else "."
  dest_dir = os.path.join(root, "generator_runtime", "artifacts")
  os.makedirs(dest_dir, exist_ok=True)
  dest = os.path.join(dest_dir, FILENAME)
  if os.path.isfile(dest) and os.path.getsize(dest) == EXPECTED_BYTES:
    print(f"present: {dest} ({EXPECTED_BYTES} bytes), verifying hash...")
  else:
    print(f"downloading {URL}")
    print(f"  -> {dest} (budget: {EXPECTED_BYTES} bytes, single file)")
    urllib.request.urlretrieve(URL, dest)
  size = os.path.getsize(dest)
  digest = sha256_file(dest)
  print(f"bytes: {size} (expected {EXPECTED_BYTES})")
  print(f"sha256: {digest}")
  ok = size == EXPECTED_BYTES and digest == EXPECTED_SHA256
  print("VERIFY: " + ("PASS" if ok else "FAIL"))
  return 0 if ok else 1


if __name__ == "__main__":
  raise SystemExit(main())
