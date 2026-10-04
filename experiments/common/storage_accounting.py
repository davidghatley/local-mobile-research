"""MEASURED storage accounting per system, kept rigorously separate.

An independent review of this run found `storage_bytes: null` in every trace and
correctly flagged it: storage is the LAST element of the preregistered tie-break
chain in `experiments/comparability/CONTRACT.md` §3, so leaving it unmeasured
leaves a hole in the primary metric chain.

Two accounting rules this module exists to enforce, because conflating them is how
storage claims get inflated:

  1. INDEX PAYLOAD vs WEIGHTS are different quantities with different mobile
     meanings. The index payload ships with the app; the weights ARE the app.
     They are reported separately and never summed into one "size" number.
  2. The ~986 MB fixed generator artifact is IDENTICAL for every architecture and
     is excluded from per-system cost, exactly as
     `experiments/baselines/HYPOTHESIS.md` §9 requires. It is reported once, as a
     shared constant, so a reader can add it back deliberately.

Everything here is a real `os.path.getsize` on a real file or a real buffer size.
Nothing is an estimate. If a system has no artifact of some kind, the field is
None ("not applicable"), never 0.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from substrate.telemetry import storage_manifest  # noqa: E402

SHARED_GENERATOR_ARTIFACT = os.path.join(
  "generator_runtime", "artifacts", "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf")

# Per-system weight artifacts: repo -> PINNED revision.
#
# The revision is not decoration. `try_to_load_from_cache(repo, fname)` resolves
# against `main` by default and returns None for a cache populated at a pinned
# revision, which is exactly how this file first reported weights_bytes = None for
# every system and quietly dropped storage from the tie-break chain. Pinning the
# revision is also the scientifically correct thing to record.
#
# Revisions are the ones independently observed and cross-checked by two teams on
# 2026-10-03 (see experiments/baselines/HYPOTHESIS.md sections 4.1 and 5.1).
_WEIGHT_REPOS: dict[str, list[tuple[str, str]]] = {
  "B2_bm25_static_union": [
    ("sentence-transformers/static-retrieval-mrl-en-v1",
     "f60985c706f192d45d218078e49e5a8b6f15283a"),
  ],
  "B3_bm25_plus_68m_rerank": [
    ("cross-encoder/ettin-reranker-68m-v1",
     "d166fa88ddde3c42bc3ee92f7df476d941c8204a"),
  ],
  "C_shared_heads_17m": [
    ("cross-encoder/ettin-reranker-17m-v1",
     "9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6"),
  ],
  "ettin_cascade": [
    ("cross-encoder/ettin-reranker-17m-v1",
     "9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6"),
    ("cross-encoder/ettin-reranker-32m-v1",
     "b33e5ceb5110773ea9cf5e00c9bedc83a8c2afdd"),
    ("cross-encoder/ettin-reranker-68m-v1",
     "d166fa88ddde3c42bc3ee92f7df476d941c8204a"),
  ],
}

# Weight/tokenizer files whose bytes count toward deployable size. Config and
# README bytes are excluded: they are not shipped to a device.
_COUNTED_FILES = ("model.safetensors", "tokenizer.json")


def _hf_cache_weights(repo_id: str, revision: str) -> dict:
  """Total bytes of weight files for a repo in the local HF cache.

  Returns a dict with "bytes", "files", "status" and "revision". `status` is one
  of MEASURED / PARTIAL / NOT_CACHED / HUB_LIBRARY_UNAVAILABLE, so an absent
  measurement is visibly absent rather than silently zero. sha256 is computed
  because a storage number that cannot be tied to a content hash does not
  identify an artefact.
  """
  try:
    from huggingface_hub import try_to_load_from_cache
  except Exception:
    return {"bytes": None, "files": [], "status": "HUB_LIBRARY_UNAVAILABLE",
            "revision": revision}
  import hashlib

  files: list[dict] = []
  total = 0
  # Weight files are not always at the repo root: the static-embedding model puts
  # them under 0_StaticEmbedding/. Only weight/tokenizer files are counted;
  # README and config bytes are excluded because they are not shipped.
  candidates = ["model.safetensors", "tokenizer.json",
                "0_StaticEmbedding/model.safetensors",
                "0_StaticEmbedding/tokenizer.json"]
  for fname in candidates:
    try:
      p = try_to_load_from_cache(repo_id, fname, revision=revision)
    except Exception:
      p = None
    if not (isinstance(p, str) and os.path.isfile(p)):
      continue
    base = os.path.basename(fname)
    if any(f["name"] == base for f in files):
      continue  # already counted the root-level copy
    h = hashlib.sha256()
    with open(p, "rb") as fh:
      for chunk in iter(lambda: fh.read(1 << 20), b""):
        h.update(chunk)
    sz = os.path.getsize(p)
    files.append({"name": fname, "bytes": sz, "sha256": h.hexdigest()})
    total += sz
  if not files:
    return {"bytes": None, "files": [], "status": "NOT_CACHED", "revision": revision}
  status = "MEASURED" if any(
    f["name"].endswith("model.safetensors") for f in files) else "PARTIAL"
  return {"bytes": total, "files": files, "status": status, "revision": revision}


# Per-system ON-DISK index artifacts, by system id.
#
# Attribution is PER SYSTEM and deliberately explicit. An earlier version of this
# file summed every .npy under the repo into every system's index payload, which
# charged BM25 for the static-semantic embedding cache -- precisely the
# conflation this module exists to prevent, committed by the very code written to
# prevent it. A reader who saw B1 at 51.5 MB would have concluded BM25 costs 5x
# what it does.
_ON_DISK_INDEX_ARTIFACTS = {
  "B2_bm25_static_union": ["artifacts/b2_static_embeddings.npy"],
}


def _files_bytes(repo_root: str, relatives: list[str]) -> tuple[int | None, list[str]]:
  """Total real filesize of specific relative paths. None if none exist."""
  files: list[str] = []
  total = 0
  for rel in relatives:
    p = os.path.join(repo_root, rel)
    if os.path.isfile(p):
      files.append(rel)
      total += os.path.getsize(p)
  return (total if files else None), files


def measure_system_storage(repo_root: str, system_id: str) -> dict[str, Any]:
  """MEASURED storage for one system. Index and weights never summed."""
  index_payload = None
  index_files: list[str] = []
  weights = None
  weight_files: list[str] = []
  per_repo: dict[str, Any] = {}

  # EVERY Round 1 system uses the shared BM25 stage-0 index, so every system is
  # charged for it. Listing only some systems here would understate the rest.
  if True:
    # The BM25 index payload is IN-MEMORY (packed arrays), not a file on disk, so
    # its size is a real buffer measurement, not a filesize. Both are reported and
    # labelled for what they are.
    try:
      from experiments.common.bm25 import Bm25Index
      from experiments.common.corpus_view import CorpusView

      view = CorpusView.load(repo_root, tier="core")
      idx = Bm25Index(view)
      index_payload = idx.posting_array_bytes()
    except Exception as exc:  # noqa: BLE001
      index_payload = None
      index_files = [f"unmeasured: {type(exc).__name__}: {exc}"]

  # On-disk index artifacts, attributed to THIS system only.
  disk_bytes, disk_files = _files_bytes(
    repo_root, _ON_DISK_INDEX_ARTIFACTS.get(system_id, []))
  if disk_bytes is not None:
    index_payload = (index_payload or 0) + disk_bytes
    index_files += disk_files

  for repo, rev in _WEIGHT_REPOS.get(system_id, []):
    info = _hf_cache_weights(repo, rev)
    per_repo[repo] = info
    if info["bytes"] is not None:
      weights = (weights or 0) + info["bytes"]
      weight_files.append(f"{repo}@{rev}")

  shared = None
  shared_path = os.path.join(repo_root, SHARED_GENERATOR_ARTIFACT)
  if os.path.isfile(shared_path):
    shared = os.path.getsize(shared_path)

  out: dict[str, Any] = {
    "index_payload_bytes": index_payload,
    "index_payload_basis": (
      "MEASURED buffer sizes of the packed postings arrays, plus any on-disk "
      ".npy embedding caches. Excludes Python object overhead; peak RSS is the "
      "process-level figure and is reported separately."
    ),
    "weights_bytes": weights,
    "weights_basis": (
      "MEASURED os.path.getsize + sha256 of cached model.safetensors and "
      "tokenizer.json at the PINNED revision. Config/README bytes excluded: "
      "they are not shipped to a device."
    ),
    "weights_per_repo": per_repo,
    "shared_generator_artifact_bytes": shared,
    "shared_generator_note": (
      "IDENTICAL for every architecture and therefore EXCLUDED from per-system "
      "cost, per experiments/baselines/HYPOTHESIS.md section 9. Listed so a "
      "reader can add it back deliberately rather than by accident."
    ),
    "index_files": index_files,
    "weight_artifacts": weight_files,
    "never_summed": (
      "index_payload_bytes and weights_bytes are reported separately and MUST NOT "
      "be added into a single 'size' figure: the index ships beside the app, the "
      "weights ARE the app, and a mobile claim needs them apart."
    ),
  }
  if index_payload is None and weights is None:
    out["status"] = "NOT_APPLICABLE_OR_UNMEASURED"
  return out
