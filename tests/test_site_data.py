"""The Pages explorer's client-side repack must agree with the recorded real packer."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
DATA = os.path.join(ROOT, "site", "data", "explorer.json")


@unittest.skipUnless(os.path.exists(DATA), "site/data/explorer.json absent")
class TestExplorerData(unittest.TestCase):
  def test_size_and_recompute(self):
    from export_site_data import rank_for_k, repack
    self.assertLess(os.path.getsize(DATA), 3_000_000)
    d = json.load(open(DATA, encoding="utf-8"))
    P, same, total = d["paragraphs"], 0, 0
    for q in d["questions"]:
      ids = [n for n, _ in q["bm25"]]
      tok = {n: (P[n]["n"], P[n]["m"]) for n in ids}
      art = {n: P[n]["a"] for n in ids}
      for key, real in q["grid"].items():
        k, b = map(int, key.split(":"))
        mine, _ = repack(rank_for_k(ids, q["rr"], k), tok, art, b)
        total += 1
        same += mine == real
      mine, _ = repack(rank_for_k(ids, q["rr"], 100), tok, art, 1000)
      self.assertEqual(q["grid"]["100:1000"], q["recorded_pack"])
    self.assertGreater(total, 1000)
    self.assertGreaterEqual(same, total - total // 200)


if __name__ == "__main__":
  unittest.main()
