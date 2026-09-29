"""Timing / memory / storage measurement methodology (stdlib only).

SCOPE AND UNITS (all readings carry these explicitly):
- Timing: ``time.perf_counter`` deltas, reported in MILLISECONDS.
- Memory ``peak_rss_mb`` on schemas: CALLING-PROCESS peak RSS in MEBIBYTES.
  Linux ``ru_maxrss`` is KiB (converted); other platforms differ and the
  source is recorded. Desktop RSS is a development proxy ONLY; never claim
  Android RAM from it.
- Runtime subprocess memory (e.g. an ephemeral ``llama-server`` owning the
  weights) is DISTINCT from client RSS and must be measured at that process
  (``proc_rss_mb(pid)`` on Linux ``/proc/<pid>/status``) or from the
  server's own accounting; never folded silently into client RSS.
- Phase separation (model-load vs inference) is done by CALLERS timing each
  phase with ``timed_phase``; a single span cannot separate them.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryReading:
  value_mb: float | None  # None = explicitly not measured
  scope: str  # e.g. "calling-process-peak", "process:<pid>-rss"
  unit: str = "MB"
  source: str = "unknown"


def peak_rss_mb() -> float | None:
  """Calling-process peak RSS in MB (``resource.ru_maxrss``).

  Scope: RUSAGE_SELF (calling process only, not children/subprocesses).
  Returns None where unavailable. Desktop proxy only.
  """
  try:
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes. Heuristic: huge values are bytes.
    if peak > 10**9:
      return peak / (1024 * 1024)
    return peak / 1024.0
  except Exception:
    return None


def peak_rss_reading() -> MemoryReading:
  value = peak_rss_mb()
  try:
    import resource  # noqa: F401

    source = "resource.ru_maxrss(RUSAGE_SELF)"
  except Exception:
    source = "unavailable"
  return MemoryReading(value_mb=value, scope="calling-process-peak", source=source)


def proc_rss_mb(pid: int) -> float | None:
  """Resident RSS in MB of an explicit OTHER process (Linux /proc).

  Use for runtime subprocesses (e.g. the inference server pid) so server
  memory is reported distinctly from client RSS. Returns None off-Linux or
  when the pid is unreadable. VmRSS is a point sample, not a peak.
  """
  try:
    with open(f"/proc/{int(pid)}/status", "r", encoding="utf-8") as fh:
      for line in fh:
        if line.startswith("VmRSS:"):
          kb = int(line.split()[1])
          return kb / 1024.0
  except Exception:
    return None
  return None


def proc_rss_reading(pid: int) -> MemoryReading:
  return MemoryReading(
    value_mb=proc_rss_mb(pid),
    scope=f"process:{int(pid)}-rss",
    source="/proc/<pid>/status:VmRSS",
  )


@contextmanager
def timed_phase(phase: str):
  """Time one labeled phase (e.g. "model_load", "inference", "stage_1").

  Yields a holder receiving ``phase`` and ``elapsed_ms`` (perf_counter delta).
  """
  start = time.perf_counter()
  holder: dict[str, object] = {"phase": phase}
  try:
    yield holder
  finally:
    holder["elapsed_ms"] = (time.perf_counter() - start) * 1000.0


@contextmanager
def timed_stage():
  """Legacy single-span timer. Prefer ``timed_phase`` with an explicit phase.

  Kept for backward compatibility; CANNOT separate model-load from inference.
  """
  with timed_phase("stage") as holder:
    yield holder


@dataclass
class StorageReport:
  paths: dict[str, int]
  total_bytes: int

  def to_dict(self) -> dict:
    return {"paths": dict(self.paths), "total_bytes": self.total_bytes}


def measure_storage(paths: list[str]) -> StorageReport:
  sizes: dict[str, int] = {}
  total = 0
  for path in paths:
    size = 0
    if os.path.isfile(path):
      size = os.path.getsize(path)
    elif os.path.isdir(path):
      for root, _, files in os.walk(path):
        for name in files:
          try:
            size += os.path.getsize(os.path.join(root, name))
          except OSError:
            continue
    sizes[path] = size
    total += size
  return StorageReport(paths=sizes, total_bytes=total)


def storage_manifest(entries: list[tuple[str, str]]) -> dict:
  """Categorized storage manifest: (path, role) entries with byte sizes.

  Roles name the budget component, e.g. "weights", "index", "corpus",
  "preencoded", "tokenizer", "config". Missing paths are recorded with
  size None (explicitly unmeasured), never silently zero.
  """
  components = []
  total = 0
  for path, role in entries:
    size: int | None = None
    if os.path.isfile(path):
      size = os.path.getsize(path)
    elif os.path.isdir(path):
      size = 0
      for root, _, files in os.walk(path):
        for name in files:
          try:
            size += os.path.getsize(os.path.join(root, name))
          except OSError:
            continue
    components.append({"path": path, "role": role, "size_bytes": size})
    total += size or 0
  return {"components": components, "total_bytes": total}
