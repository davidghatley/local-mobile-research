"""Lane C storage/memory tests: fail-closed manifest + distinct RSS readings.

Synthetic fixtures only (temp dirs, live /proc self-reads, monkeypatched
platform dispatch). No sealed data, no model artifacts.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

from substrate import telemetry as tel


class TestStorageManifestFailClosed(unittest.TestCase):
  def test_missing_path_yields_none_total_and_incomplete(self):
    with tempfile.TemporaryDirectory() as tmp:
      present = os.path.join(tmp, "present.bin")
      with open(present, "wb") as fh:
        fh.write(b"x" * 64)
      missing = os.path.join(tmp, "absent.bin")
      manifest = tel.storage_manifest(
        [(present, "corpus"), (missing, "weights")])
    self.assertFalse(manifest["complete"])
    self.assertIsNone(manifest["total_bytes"])
    self.assertEqual(manifest["known_bytes"], 64)
    self.assertEqual(manifest["missing"], [missing])
    by_path = {c["path"]: c for c in manifest["components"]}
    self.assertIsNone(by_path[missing]["size_bytes"])
    self.assertEqual(by_path[present]["size_bytes"], 64)
    # complete=false paired with an integer total is invalid: the fixed
    # manifest must never produce that combination.
    self.assertFalse(manifest["complete"] and isinstance(
      manifest["total_bytes"], int))

  def test_complete_manifest_carries_integer_total(self):
    with tempfile.TemporaryDirectory() as tmp:
      a = os.path.join(tmp, "a.bin")
      b = os.path.join(tmp, "b.bin")
      with open(a, "wb") as fh:
        fh.write(b"x" * 10)
      with open(b, "wb") as fh:
        fh.write(b"y" * 20)
      manifest = tel.storage_manifest([(a, "index"), (b, "corpus")])
    self.assertTrue(manifest["complete"])
    self.assertEqual(manifest["total_bytes"], 30)
    self.assertEqual(manifest["known_bytes"], 30)
    self.assertEqual(manifest["missing"], [])

  def test_complete_false_with_integer_bytes_is_invalid(self):
    # Rule predicate from docs/abstention-and-telemetry-notes.md §3 rule 5:
    # storage_complete=false + integer storage_bytes => reject.
    def valid(trace):
      if trace["storage_complete"] is False and isinstance(
          trace["storage_bytes"], int):
        return False
      return True
    self.assertFalse(valid({"storage_complete": False, "storage_bytes": 123}))
    self.assertTrue(valid({"storage_complete": False, "storage_bytes": None}))
    self.assertTrue(valid({"storage_complete": True, "storage_bytes": 123}))


class TestProcMemoryDistinct(unittest.TestCase):
  @unittest.skipUnless(sys.platform.startswith("linux"), "requires Linux /proc")
  def test_point_and_peak_read_distinct_sources(self):
    pid = os.getpid()
    rss = tel.proc_rss_mb(pid)
    peak = tel.proc_peak_rss_mb(pid)
    self.assertIsNotNone(rss)
    self.assertIsNotNone(peak)
    # High-water mark is monotonic: peak >= live point sample.
    self.assertGreaterEqual(peak, rss)
    point = tel.proc_rss_reading(pid)
    high = tel.proc_peak_rss_reading(pid)
    self.assertNotEqual(point.scope, high.scope)
    self.assertIn("VmRSS", point.source)
    self.assertIn("VmHWM", high.source)
    self.assertNotIn("VmHWM", point.source)
    self.assertNotIn("VmRSS", high.source)
    mem = tel.proc_memory(pid)
    self.assertEqual(mem["pid"], pid)
    # Same-call values are self-consistent (peak high-water >= point);
    # cross-sample equality is NOT asserted: VmRSS is a live point sample.
    self.assertIsNotNone(mem["rss_mb"])
    self.assertIsNotNone(mem["peak_rss_mb"])
    self.assertGreaterEqual(mem["peak_rss_mb"], mem["rss_mb"])
    self.assertNotEqual(mem["rss_source"], mem["peak_source"])


class TestRuMaxrssDispatch(unittest.TestCase):
  def _fake_getrusage(self, value):
    ru = mock.Mock()
    ru.ru_maxrss = value
    return mock.Mock(return_value=ru)

  def test_linux_divides_kib_no_heuristic(self):
    # 3e9 KiB: the old magnitude heuristic would misread this as bytes.
    with mock.patch.object(sys, "platform", "linux"), \
        mock.patch("resource.getrusage", self._fake_getrusage(3 * 10 ** 9)):
      self.assertEqual(tel.peak_rss_mb(), 3 * 10 ** 9 / 1024.0)

  def test_darwin_divides_bytes(self):
    # 512000 bytes: the old heuristic (< 1e9) would misread this as KiB.
    with mock.patch.object(sys, "platform", "darwin"), \
        mock.patch("resource.getrusage", self._fake_getrusage(512000)):
      self.assertAlmostEqual(tel.peak_rss_mb(), 512000 / (1024.0 * 1024.0))

  def test_unknown_platform_returns_none(self):
    with mock.patch.object(sys, "platform", "win32"), \
        mock.patch("resource.getrusage", self._fake_getrusage(10 ** 6)):
      self.assertIsNone(tel.peak_rss_mb())

  def test_reading_records_platform_and_unit(self):
    reading = tel.peak_rss_reading()
    self.assertIn(sys.platform, reading.source)
    self.assertIn("unit=", reading.source)
    self.assertEqual(reading.scope, "calling-process-peak")


if __name__ == "__main__":
  unittest.main()
