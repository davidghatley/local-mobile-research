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
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MemoryReading:
  value_mb: float | None  # None = explicitly not measured
  scope: str  # e.g. "calling-process-peak", "process:<pid>-rss"
  unit: str = "MB"
  source: str = "unknown"


def _ru_maxrss_divisor() -> tuple[str, float | None]:
  """Explicit platform dispatch for ``resource.ru_maxrss`` units.

  Returns (unit_label, divisor-to-MB). Linux reports KiB; macOS (darwin)
  reports bytes. Any other platform returns None: unknown units are
  reported as unmeasured, NEVER guessed by magnitude. Linux is the
  measurement target; other platforms are best-effort or None.
  """
  if sys.platform.startswith("linux"):
    return ("linux:KiB", 1024.0)
  if sys.platform == "darwin":
    return ("darwin:bytes", 1024.0 * 1024.0)
  return ("unknown-platform", None)


def peak_rss_mb() -> float | None:
  """Calling-process peak RSS in MB (``resource.ru_maxrss``).

  Scope: RUSAGE_SELF (calling process only, not children/subprocesses).
  Units come from explicit ``sys.platform`` dispatch (see
  ``_ru_maxrss_divisor``); unknown platforms return None. No magnitude
  heuristic: a small byte count must never be misread as KiB or vice
  versa. Returns None where unavailable. Desktop proxy only.
  """
  try:
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    _label, divisor = _ru_maxrss_divisor()
    if divisor is None:
      return None
    return peak / divisor
  except Exception:
    return None


def peak_rss_reading() -> MemoryReading:
  value = peak_rss_mb()
  try:
    import resource  # noqa: F401

    label, _ = _ru_maxrss_divisor()
    source = f"resource.ru_maxrss(RUSAGE_SELF);platform={sys.platform};unit={label}"
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


def proc_peak_rss_mb(pid: int) -> float | None:
  """High-water RSS in MB of an explicit OTHER process (Linux /proc).

  Reads ``VmHWM`` from ``/proc/<pid>/status``: the PEAK resident set, kept
  by the kernel and monotonic within the process lifetime. This is
  DISTINCT from the point sample ``VmRSS`` (see ``proc_rss_mb``): never
  conflate or substitute one for the other. Returns None off-Linux or
  when the pid is unreadable.
  """
  try:
    with open(f"/proc/{int(pid)}/status", "r", encoding="utf-8") as fh:
      for line in fh:
        if line.startswith("VmHWM:"):
          kb = int(line.split()[1])
          return kb / 1024.0
  except Exception:
    return None
  return None


def proc_peak_rss_reading(pid: int) -> MemoryReading:
  return MemoryReading(
    value_mb=proc_peak_rss_mb(pid),
    scope=f"process:{int(pid)}-peak",
    source="/proc/<pid>/status:VmHWM",
  )


def proc_memory(pid: int) -> dict:
  """Point + peak RSS of one explicit process, distinctly named.

  Returns {"pid", "rss_mb" (point VmRSS sample), "peak_rss_mb" (VmHWM
  high-water), "rss_source", "peak_source"}. Either value may be None
  (explicitly unmeasured); the two are never merged into one number.
  """
  pid = int(pid)
  return {
    "pid": pid,
    "rss_mb": proc_rss_mb(pid),
    "peak_rss_mb": proc_peak_rss_mb(pid),
    "rss_source": "/proc/<pid>/status:VmRSS",
    "peak_source": "/proc/<pid>/status:VmHWM",
  }


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
  total_bytes: int | None
  known_bytes: int = 0
  complete: bool = True
  missing: list[str] = field(default_factory=list)

  def to_dict(self) -> dict:
    return {
      "paths": dict(self.paths),
      "total_bytes": self.total_bytes,
      "known_bytes": self.known_bytes,
      "complete": self.complete,
      "missing": list(self.missing),
    }


def measure_storage(paths: list[str]) -> StorageReport:
  """Per-path byte sizes with FAIL-CLOSED totals.

  A path that does not exist (or is unreadable) yields ``None`` — never 0.
  ``total_bytes`` is ``None`` whenever any required component is unmeasured, so
  a partial measurement can never masquerade as a complete storage total.
  ``known_bytes`` carries the sum of measured components for diagnostics only.
  """
  sizes: dict[str, int | None] = {}
  total = 0
  complete = True
  for path in paths:
    size: int | None = None
    if os.path.isfile(path):
      size = os.path.getsize(path)
    elif os.path.isdir(path):
      acc = 0
      for root, _, files in os.walk(path):
        for name in files:
          try:
            acc += os.path.getsize(os.path.join(root, name))
          except OSError:
            continue
      size = acc
    sizes[path] = size
    if size is None:
      complete = False
    else:
      total += size
  return StorageReport(
    paths=sizes,
    total_bytes=total if complete else None,
    known_bytes=total,
    complete=complete,
    missing=[p for p, s in sizes.items() if s is None],
  )


def storage_manifest(entries: list[tuple[str, str]]) -> dict:
  """Categorized storage manifest: (path, role) entries with byte sizes.

  Roles name the budget component, e.g. "weights", "index", "corpus",
  "preencoded", "tokenizer", "config". FAIL-CLOSED: a missing path yields
  ``size_bytes`` None (explicitly unmeasured, never silent zero);
  ``total_bytes`` is None whenever ``complete`` is False, and ``known_bytes``
  sums only measured components. A consumer MUST reject
  ``complete=false`` paired with an integer ``total_bytes``.
  """
  components = []
  known_bytes = 0
  missing: list[str] = []
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
    if size is None:
      missing.append(path)
    else:
      known_bytes += size
  complete = not missing
  return {
    "components": components,
    "total_bytes": known_bytes if complete else None,
    "complete": complete,
    "known_bytes": known_bytes,
    "missing": missing,
  }
