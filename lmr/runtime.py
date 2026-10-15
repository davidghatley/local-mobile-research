"""Local runtime: a pinned llama.cpp CPU build and the pinned generator GGUF.

Everything lands in ``$LMR_HOME`` (default ``~/.cache/lmr``), outside the repo.
Downloads are verified by sha256 before use. After setup nothing here touches
the network: llama-server is bound to 127.0.0.1 and started per session.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import socket
import subprocess
import tarfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.environ.get("LMR_HOME", os.path.expanduser("~/.cache/lmr"))

LLAMA_TAG = "b11227"
LLAMA_URL = (f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/"
             f"llama-{LLAMA_TAG}-bin-ubuntu-x64.tar.gz")


def generator_config() -> dict:
  with open(os.path.join(ROOT, "corpus", "generator_config.json"), encoding="utf-8") as fh:
    return json.load(fh)


def _sha256(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def _download(url: str, dest: str, log=print) -> None:
  tmp = dest + ".part"
  req = urllib.request.Request(url, headers={"User-Agent": "lmr-setup"})
  with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
    total = int(resp.headers.get("Content-Length") or 0)
    done, last = 0, 0.0
    while chunk := resp.read(1 << 20):
      out.write(chunk)
      done += len(chunk)
      if total and time.time() - last > 2:
        log(f"  {os.path.basename(dest)}: {done * 100 // total}%")
        last = time.time()
  os.replace(tmp, dest)


def model_path() -> str:
  return os.environ.get("LMR_MODEL") or os.path.join(HOME, generator_config()["file"])


def server_bin() -> str:
  if os.environ.get("LMR_LLAMA_SERVER"):
    return os.environ["LMR_LLAMA_SERVER"]
  for dirpath, _, files in os.walk(os.path.join(HOME, "llama.cpp")):
    if "llama-server" in files:
      return os.path.join(dirpath, "llama-server")
  return ""


def setup(log=print) -> None:
  os.makedirs(HOME, exist_ok=True)
  if not server_bin():
    log(f"llama.cpp {LLAMA_TAG} (CPU build)")
    tgz = os.path.join(HOME, "llama.tar.gz")
    _download(LLAMA_URL, tgz, log)
    with tarfile.open(tgz) as tf:
      tf.extractall(os.path.join(HOME, "llama.cpp"), filter="data")
    os.remove(tgz)
  cfg = generator_config()
  path = model_path()
  if not os.path.exists(path):
    log(f"generator {cfg['file']} ({cfg['bytes'] / 1e9:.2f} GB)")
    _download(cfg["download_url"], path, log)
  if path == os.path.join(HOME, cfg["file"]) and _sha256(path) != cfg["sha256"]:
    raise RuntimeError(f"{path}: sha256 does not match corpus/generator_config.json")
  log(f"ready: {server_bin()}\n       {path}")


def _free_port() -> int:
  with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    return s.getsockname()[1]


class LlamaServer:
  """One llama-server subprocess on localhost, used for tokenizing and generating."""

  def __init__(self, threads: int | None = None, ctx: int = 4096):
    if not server_bin() or not os.path.exists(model_path()):
      raise RuntimeError("runtime missing: run `lmr setup` first")
    self.port = _free_port()
    self.threads = threads or max(1, (os.cpu_count() or 4) // 2)
    cmd = [server_bin(), "-m", model_path(), "--host", "127.0.0.1",
           "--port", str(self.port), "-c", str(ctx), "-ngl", "0",
           "-t", str(self.threads), "--no-webui"]
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.dirname(server_bin()))
    self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, env=env)
    atexit.register(self.close)  # never leave a server behind after a crash
    deadline = time.time() + 120
    while time.time() < deadline:
      try:
        if self._get("/health").get("status") == "ok":
          return
      except OSError:
        pass
      if self.proc.poll() is not None:
        raise RuntimeError("llama-server exited during startup")
      time.sleep(0.25)
    self.close()
    raise RuntimeError("llama-server did not become healthy in 120 s")

  def _get(self, path: str) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
      return json.loads(r.read())

  def _post(self, path: str, body: dict, timeout: float = 600) -> dict:
    req = urllib.request.Request(
      f"http://127.0.0.1:{self.port}{path}", data=json.dumps(body).encode(),
      headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
      return json.loads(r.read())

  def count_tokens(self, text: str) -> int:
    return len(self._post("/tokenize", {"content": text})["tokens"])

  def chat(self, prompt: str, max_tokens: int = 256) -> dict:
    g = generator_config()["generation"]
    return self._post("/v1/chat/completions", {
      "messages": [{"role": "user", "content": prompt}],
      "max_tokens": max_tokens, "temperature": g["temperature"],
      "top_k": g["top_k"], "top_p": g["top_p"], "seed": g["seed"],
      "cache_prompt": False,
    })

  def close(self) -> None:
    if self.proc.poll() is None:
      self.proc.terminate()
      try:
        self.proc.wait(10)
      except subprocess.TimeoutExpired:
        self.proc.kill()

  def __enter__(self):
    return self

  def __exit__(self, *exc):
    self.close()
