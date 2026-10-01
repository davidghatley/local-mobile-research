"""Distractor-scale tier 1 verification tests (corpus/scale worker scope).

Stdlib unittest only. Proves the four properties the scale layer is load-bearing
for, plus the honesty gates:

  1. ZERO core overlap on pageid / normalized title / content sha256, and the
     core artifacts are still byte-identical to corpus/build_manifest.json
     after the scale build (the core is frozen; the scale build must not touch
     it, and must never be cited by it).
  2. Deterministic double-build: two independent builds are BYTE-IDENTICAL.
  3. Node-id namespace disjointness from the core, and
     substrate.corpus.validate_hierarchy passes on the MERGED view.
  4. No scale article appears in the frozen core split_map.json, so distractor
     mass cannot leak into a measured split.

Honesty gates:
  5. The tier manifest states the achieved article count, states plainly that the
     ~1000 target was or was not met, and labels the material as irrelevant
     distractor material with DESKTOP-only measurement scope.
  6. The builder performs no network I/O (static source scan + socket block).

No test here inspects question or answer content.

Run: python3 -m unittest discover -s corpus/scale/tests -t .
"""

import atexit
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))          # corpus/scale/tests
SCALE_DIR = os.path.dirname(HERE)                          # corpus/scale
ROOT = os.path.dirname(os.path.dirname(SCALE_DIR))         # project root

sys.path.insert(0, os.path.join(ROOT, "corpus"))
sys.path.insert(0, ROOT)
sys.path.insert(0, SCALE_DIR)

import build_pilot as bp  # noqa: E402
import scale_build as sb  # noqa: E402

from substrate.corpus import (  # noqa: E402
  corpus_hash,
  load_corpus_file,
  nodes_from_jsonl,
  validate_hierarchy,
)

CORE_DIR = os.path.join(ROOT, "corpus")
CORE_CORPUS = os.path.join(CORE_DIR, "corpus.jsonl")
TIER = os.path.join(SCALE_DIR, "tier_1k.json")
DISTRACTOR = os.path.join(SCALE_DIR, "distractor.jsonl")
BUILDER = os.path.join(SCALE_DIR, "scale_build.py")

PUBLISHED = ("distractor.jsonl", "scale_provenance.json",
             "scale_input_manifest.json", "tier_1k.json",
             "scale_build_manifest.json")


def sha256_file(path):
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def _tier():
  with open(TIER, encoding="utf-8") as fh:
    return json.load(fh)


# ---------------------------------------------------------------------------
# Shared loaders and build cache.
#
# distractor.jsonl is ~118 MB / 300k nodes and a full build takes ~40 s, so
# each of these is computed at most once per test session. Tests that need a
# fresh build share the staged directories produced here rather than paying for
# their own; the determinism property genuinely needs two independent builds and
# gets exactly that.
# ---------------------------------------------------------------------------

_CACHE = {}


def core_nodes():
  if "core" not in _CACHE:
    _CACHE["core"] = load_corpus_file(CORE_CORPUS)
  return _CACHE["core"]


def scale_nodes():
  if "scale" not in _CACHE:
    _CACHE["scale"] = nodes_from_jsonl(
      open(DISTRACTOR, encoding="utf-8").read())
  return _CACHE["scale"]


def fresh_builds(count=2, block_network=False):
  """Build the tier `count` independent times and return the staged dirs.

  The dirs are created once and reused; cleanup happens at interpreter exit so
  a single expensive pair of builds serves every test that needs a rebuild.
  """
  key = ("builds", count, block_network)
  if key in _CACHE:
    return _CACHE[key]
  atexit_dirs = []
  if block_network:
    import socket as socket_mod
    real_socket, real_conn = socket_mod.socket, socket_mod.create_connection

    def _blocked(*a, **kw):
      raise AssertionError("scale build attempted a network connection")

    socket_mod.socket = _blocked
    socket_mod.create_connection = _blocked
    try:
      dirs = _build_n(count)
    finally:
      socket_mod.socket = real_socket
      socket_mod.create_connection = real_conn
  else:
    dirs = _build_n(count)
  atexit_dirs.extend(dirs)
  atexit.register(lambda: [shutil.rmtree(d, ignore_errors=True) for d in atexit_dirs])
  _CACHE[key] = dirs
  return dirs


def _build_n(count):
  dirs = []
  for _ in range(count):
    stage = tempfile.mkdtemp(prefix="scale_build_")
    sb.run_offline(os.path.join(SCALE_DIR, "raw"), stage,
                   sb.SCALE_REVISION_DEFAULT)
    dirs.append(stage)
  return dirs


class TestZeroCoreOverlap(unittest.TestCase):
  """Property 1a: the mechanical de-duplication against the frozen core 297."""

  @classmethod
  def setUpClass(cls):
    cls.core = core_nodes()
    cls.scale = scale_nodes()
    cls.core_articles = [n for n in cls.core if n.kind == "article"]
    cls.scale_articles = [n for n in cls.scale if n.kind == "article"]
    cls.tier = _tier()

  def test_core_has_the_297_articles(self):
    self.assertEqual(len(self.core_articles), 297)

  def test_no_pageid_collision(self):
    core = {str(n.meta["pageid"]) for n in self.core_articles}
    scale = {str(n.meta["pageid"]) for n in self.scale_articles}
    self.assertEqual(core & scale, set())

  def test_no_normalized_title_collision(self):
    core = {bp.norm_key(n.text) for n in self.core_articles}
    scale = {bp.norm_key(n.text) for n in self.scale_articles}
    self.assertEqual(core & scale, set())

  def test_no_content_hash_collision(self):
    core = {n.meta["content_sha256"] for n in self.core_articles}
    scale = {n.meta["content_sha256"] for n in self.scale_articles}
    self.assertEqual(core & scale, set())

  def test_tier_manifest_records_zero_overlap_and_no_silent_exclusions(self):
    self.assertEqual(self.tier["article_counts"]["rejected_core_overlap"], 0)
    self.assertEqual(self.tier["excluded_core_overlap"], [])
    self.assertEqual(self.tier["excluded_duplicate_pageid"], [])
    self.assertEqual(self.tier["snapshot_load_problems"], [])
    verified = self.tier["selection_independence"]["verified_core_overlap_count"]
    self.assertEqual(verified, 0)

  def test_de_dup_is_mechanical_not_fuzzy(self):
    """The rejection predicate must be exact-set membership on three keys."""
    index, info = sb.core_index(CORE_DIR)
    self.assertEqual(info["article_count"], 297)
    self.assertEqual(len(index["pageid"]), 297)
    self.assertEqual(len(index["normalized_title"]), 297)
    self.assertEqual(len(index["content_sha256"]), 297)
    # A synthetic snapshot colliding on exactly one key must be rejected, and
    # the rejection must name that key.
    probe = {"_file": "probe.json", "pageid": self.core_articles[0].meta["pageid"],
             "normalized_title": "Zzz Definitely Not A Core Article",
             "requested_title": "Zzz Definitely Not A Core Article",
             "content_sha256": "0" * 64}
    kept, rejected = sb.reject_core_overlap([probe], index)
    self.assertEqual(kept, [])
    self.assertEqual(len(rejected), 1)
    self.assertEqual(rejected[0]["colliding_fields"], ["pageid"])

  def test_core_split_map_contains_no_scale_article(self):
    """Property 4: distractor mass cannot enter a measured split."""
    with open(os.path.join(CORE_DIR, "split_map.json"), encoding="utf-8") as fh:
      split_map = json.load(fh)
    measured = set()
    for rec in split_map["groups"].values():
      for t in rec["articles"]:
        measured.add(bp.norm_key(t))
    scale_titles = {bp.norm_key(n.text) for n in self.scale_articles}
    self.assertEqual(measured & scale_titles, set())


class TestCoreArtifactsUnchanged(unittest.TestCase):
  """Property 1b: the frozen core is byte-identical after the scale build."""

  def test_core_artifacts_match_build_manifest(self):
    with open(os.path.join(CORE_DIR, "build_manifest.json"), encoding="utf-8") as fh:
      manifest = json.load(fh)
    self.assertTrue(manifest["artifacts"], "core build manifest lists no artifacts")
    for art in manifest["artifacts"]:
      path = os.path.join(ROOT, art["path"])
      self.assertTrue(os.path.isfile(path), f"missing core artifact {art['path']}")
      self.assertEqual(sha256_file(path), art["sha256"],
                       f"core artifact mutated: {art['path']}")
      self.assertEqual(os.path.getsize(path), art["bytes"],
                       f"core artifact size changed: {art['path']}")

  def test_core_corpus_hash_matches_its_provenance(self):
    with open(os.path.join(CORE_DIR, "provenance.json"), encoding="utf-8") as fh:
      prov = json.load(fh)
    self.assertEqual(corpus_hash(load_corpus_file(CORE_CORPUS)),
                     prov["corpus_hash_sha256"])

  def test_tier_cites_core_but_core_cites_nothing_about_scale(self):
    """One-directional cross-referencing is load-bearing."""
    with open(TIER, encoding="utf-8") as fh:
      tier = fh.read()
    self.assertIn("corpus/corpus.jsonl", tier)
    ref = _tier()["core_reference"]
    self.assertEqual(ref["core_corpus_sha256"], sha256_file(CORE_CORPUS))
    # The core must not MENTION the scale layer. corpus.jsonl is 44 MB of
    # article text in which the substring "scale" occurs incidentally, so scan
    # the machine-generated sidecars verbatim and the corpus itself for the
    # layer's identifying tokens only (node-id prefix and root id).
    for name in ("provenance.json", "split_map.json", "input_manifest.json",
                 "build_manifest.json"):
      path = os.path.join(CORE_DIR, name)
      with open(path, encoding="utf-8") as fh:
        body = fh.read()
      for token in ("scale", "corpus/scale", "distractor", sb.SCALE_ROOT_NODE_ID,
                    sb.NS_ARTICLE, sb.NS_PARAGRAPH, sb.NS_SENTENCE):
        self.assertNotIn(token, body,
                         f"core artifact {name} references the scale layer "
                         f"via {token!r}")
    with open(CORE_CORPUS, encoding="utf-8") as fh:
      core_jsonl = fh.read()
    for token in (sb.SCALE_ROOT_NODE_ID, "corpus/scale", "distractor_candidates"):
      self.assertNotIn(token, core_jsonl,
                       f"core corpus.jsonl references the scale layer via {token!r}")


class TestDeterministicDoubleBuild(unittest.TestCase):
  """Property 2: two independent builds must be BYTE-IDENTICAL."""

  def test_double_build_is_byte_identical(self):
    a, b = fresh_builds(2)
    hashes = [{n: sha256_file(os.path.join(d, n)) for n in PUBLISHED}
              for d in (a, b)]
    self.assertEqual(hashes[0], hashes[1],
                     "scale build is not deterministic; byte-identity is load-bearing")

  def test_published_artifacts_match_a_fresh_build(self):
    stage = fresh_builds(2)[0]
    for name in PUBLISHED:
      self.assertEqual(sha256_file(os.path.join(stage, name)),
                       sha256_file(os.path.join(SCALE_DIR, name)),
                       f"published {name} does not match a fresh build")

  def test_no_wall_clock_in_published_artifacts(self):
    """A clock field would silently break double-build byte-identity."""
    for name in PUBLISHED:
      with open(os.path.join(SCALE_DIR, name), encoding="utf-8") as fh:
        body = fh.read()
      self.assertNotIn("built_utc\": \"20", body,
                       f"{name} embeds a wall-clock build time")

  def test_published_manifest_pins_its_own_artifacts(self):
    with open(os.path.join(SCALE_DIR, "scale_build_manifest.json"),
              encoding="utf-8") as fh:
      manifest = json.load(fh)
    self.assertTrue(manifest["revision"], "manifest carries no revision id")
    pinned = {os.path.basename(a["path"]): a for a in manifest["artifacts"]}
    for name in PUBLISHED:
      if name == "scale_build_manifest.json":
        continue
      self.assertIn(name, pinned, f"{name} is not pinned in the build manifest")
      self.assertEqual(pinned[name]["sha256"],
                       sha256_file(os.path.join(SCALE_DIR, name)))
      self.assertEqual(pinned[name]["bytes"],
                       os.path.getsize(os.path.join(SCALE_DIR, name)))


class TestNamespaceDisjointAndMergedView(unittest.TestCase):
  """Property 3: disjoint namespaces; merged view validates."""

  @classmethod
  def setUpClass(cls):
    cls.core = core_nodes()
    cls.scale = scale_nodes()

  def test_node_id_sets_are_disjoint(self):
    core_ids = {n.node_id for n in self.core}
    scale_ids = {n.node_id for n in self.scale}
    overlap = core_ids & scale_ids
    self.assertEqual(overlap, set(), f"node-id collision: {sorted(overlap)[:5]}")

  def test_both_roots_coexist_and_are_distinct(self):
    roots = [n.node_id for n in self.scale if n.kind == "corpus"]
    self.assertEqual(roots, [sb.SCALE_ROOT_NODE_ID])
    core_roots = [n.node_id for n in self.core if n.kind == "corpus"]
    self.assertNotIn(sb.SCALE_ROOT_NODE_ID, core_roots)

  def test_every_scale_node_uses_a_scale_prefix(self):
    prefixes = {"cluster": sb.NS_CLUSTER, "article": sb.NS_ARTICLE,
                "section": sb.NS_SECTION, "paragraph": sb.NS_PARAGRAPH,
                "sentence": sb.NS_SENTENCE}
    for n in self.scale:
      if n.kind == "corpus":
        self.assertTrue(n.node_id.startswith(sb.NS_ROOT))
        continue
      prefix = prefixes[n.kind]
      self.assertTrue(n.node_id.startswith(prefix),
                      f"{n.node_id} does not use the {n.kind} prefix {prefix}")

  def test_scale_prefixes_are_mutually_unambiguous(self):
    """No scale prefix may be a prefix of another, or ids become ambiguous."""
    prefixes = [sb.NS_ROOT, sb.NS_CLUSTER, sb.NS_ARTICLE, sb.NS_SECTION,
                sb.NS_PARAGRAPH, sb.NS_SENTENCE]
    for a in prefixes:
      for b in prefixes:
        if a is not b:
          self.assertFalse(a.startswith(b),
                           f"{a!r} is a prefix of {b!r}; namespaces are ambiguous")

  def test_no_scale_link_points_at_a_core_node(self):
    core_ids = {n.node_id for n in self.core}
    for n in self.scale:
      self.assertEqual(set(n.links) & core_ids, set(),
                       f"scale node {n.node_id} cross-links into the core")

  def test_merged_view_validates_and_hashes(self):
    errors = validate_hierarchy(self.core + self.scale)
    self.assertEqual(errors, [], f"merged view invalid: {errors[:5]}")
    merged = corpus_hash(self.core + self.scale)
    self.assertEqual(len(merged), 64)
    # Distinct roots, distinct node sets => merged hash differs from both parts.
    self.assertNotEqual(merged, corpus_hash(self.core))
    self.assertNotEqual(merged, corpus_hash(self.scale))

  def test_scale_hierarchy_validates_standalone(self):
    self.assertEqual(validate_hierarchy(self.scale), [])


class TestScaleBuilderIsOffline(unittest.TestCase):
  """Property 6: the build must not touch the network."""

  def test_builder_source_has_no_network_references(self):
    with open(BUILDER, encoding="utf-8") as fh:
      src = fh.read()
    for bad in ("urllib", "requests", "http://", "https://", "socket",
                "api_get(", "fetch_article(", "urlopen"):
      self.assertNotIn(bad, src, f"scale_build.py references {bad}")

  def test_offline_path_survives_blocked_sockets(self):
    # A full build with socket.socket and socket.create_connection replaced by
    # tripwires: if the offline path reached for the network it would raise.
    stage = fresh_builds(1, block_network=True)[0]
    for name in PUBLISHED:
      self.assertTrue(os.path.isfile(os.path.join(stage, name)),
                      f"network-blocked build did not produce {name}")
    # And the network-blocked build must equal the unblocked one exactly.
    unblocked = fresh_builds(2)[0]
    for name in PUBLISHED:
      self.assertEqual(sha256_file(os.path.join(stage, name)),
                       sha256_file(os.path.join(unblocked, name)),
                       f"{name} differs when sockets are blocked")


class TestTierManifestContent(unittest.TestCase):
  """Requirements 3 and 6: the manifest must carry the stated facts."""

  @classmethod
  def setUpClass(cls):
    cls.tier = _tier()

  def test_reports_article_counts(self):
    counts = self.tier["article_counts"]
    for key in ("submitted_candidates", "raw_snapshots_on_disk",
                "passed_core_dedup", "built_articles",
                "rejected_core_overlap", "rejected_duplicate_pageid"):
      self.assertIn(key, counts)
    self.assertEqual(counts["built_articles"],
                     len(self.tier["snapshots"]))

  def test_per_snapshot_provenance_fields_present(self):
    self.assertTrue(self.tier["snapshots"])
    for rec in self.tier["snapshots"]:
      for key in ("file", "sha256", "pageid", "revid", "timestamp",
                  "source_url", "license", "bytes", "content_sha256",
                  "node_id"):
        self.assertIn(key, rec, f"snapshot record missing {key}")
      self.assertTrue(os.path.isfile(os.path.join(SCALE_DIR, "raw", rec["file"])))
      self.assertEqual(sha256_file(os.path.join(SCALE_DIR, "raw", rec["file"])),
                       rec["sha256"], f"raw snapshot hash drift: {rec['file']}")

  def test_cc_by_sa_attribution_is_declared_with_its_gap(self):
    attr = self.tier["attribution"]
    self.assertEqual(attr["license"], "CC BY-SA 4.0")
    self.assertIn("source_url", attr["per_article_fields"])
    self.assertIn("revid", attr["per_article_fields"])
    # revid is genuinely absent from every tier-1 snapshot; the manifest must
    # say so rather than implying a revision id exists.
    self.assertEqual(attr["revid_available_count"], 0)
    self.assertTrue(attr["known_gap"])

  def test_merged_corpus_hash_present_and_correct(self):
    core, scale = core_nodes(), scale_nodes()
    self.assertEqual(self.tier["merged_view"]["scale_nodes"], len(scale))
    self.assertEqual(self.tier["merged_view"]["core_nodes"], len(core))
    merged, ncore, nscale = sb.merged_view_hash()
    self.assertEqual((ncore, nscale), (len(core), len(scale)))
    self.assertEqual(merged, corpus_hash(core + scale))
    self.assertNotEqual(merged, corpus_hash(core))
    self.assertNotEqual(merged, corpus_hash(scale))

  def test_byte_sizes_and_node_counts_and_disk_footprint_present(self):
    self.assertIn("distractor_jsonl_bytes", self.tier["byte_sizes"])
    self.assertIn("raw_dir_bytes", self.tier["disk_footprint"])
    self.assertEqual(self.tier["byte_sizes"]["distractor_jsonl_bytes"],
                     os.path.getsize(DISTRACTOR))
    self.assertEqual(sum(self.tier["node_counts"].values()), self.tier["node_ids"]["total"])

  def test_builder_and_candidate_hashes_pinned(self):
    self.assertEqual(self.tier["builder"]["sha256"], sha256_file(BUILDER))
    self.assertEqual(
      self.tier["selection_independence"]["candidate_list_sha256"],
      sha256_file(os.path.join(SCALE_DIR, "distractor_candidates.json")))

  def test_selection_independence_attestation_is_labeled_procedural(self):
    att = self.tier["selection_independence"]["attestation"]
    self.assertIn("PROCEDURAL", att.upper())
    self.assertIn("NOT EMPIRICAL", att.upper())

  def test_role_and_measurement_scope_are_explicit(self):
    self.assertIn("IRRELEVANT DISTRACTOR MATERIAL", self.tier["role"].upper())
    self.assertIn("297", self.tier["role"])
    scope = self.tier["measurement_scope"].upper()
    self.assertIn("DESKTOP", scope)
    self.assertIn("NO ANDROID", scope)

  def test_no_split_map_is_emitted_or_claimed(self):
    split = self.tier["split_assignment"]
    self.assertFalse(split["split_map_emitted"])
    self.assertEqual(split["measured_splits"], [])
    self.assertFalse(os.path.exists(os.path.join(SCALE_DIR, "scale_split_map.json")))


class TestTierTargetHonesty(unittest.TestCase):
  """The ~1000 tier must be reported truthfully, not rounded up."""

  def test_achieved_count_is_stated_and_matches_disk(self):
    tier = _tier()
    target = tier["tier_target"]
    self.assertEqual(target["achieved"], tier["article_counts"]["built_articles"])
    self.assertEqual(target["requested"], 1000)
    self.assertEqual(target["met"], target["achieved"] >= target["requested"])
    self.assertEqual(target["shortfall"],
                     max(0, target["requested"] - target["achieved"]))

  def test_unmet_target_carries_an_explanation(self):
    target = _tier()["tier_target"]
    if not target["met"]:
      self.assertTrue(target["shortfall_reason"],
                      "unmet tier target must state why")

  def test_achieved_count_equals_article_nodes_on_disk(self):
    scale = scale_nodes()
    self.assertEqual(sum(1 for n in scale if n.kind == "article"),
                     _tier()["article_counts"]["built_articles"])


class TestSnapshotIntegrity(unittest.TestCase):
  """The 940 on-disk snapshots must be internally consistent."""

  def test_every_referenced_raw_snapshot_parses_and_matches_its_hash(self):
    tier = _tier()
    for rec in tier["snapshots"]:
      with open(os.path.join(SCALE_DIR, "raw", rec["file"]), encoding="utf-8") as fh:
        d = json.load(fh)
      actual = hashlib.sha256(d["wikitext"].encode("utf-8")).hexdigest()
      self.assertEqual(actual, d["content_sha256"], rec["file"])
      self.assertEqual(actual, rec["content_sha256"], rec["file"])

  def test_not_found_candidates_are_accounted_for_not_hidden(self):
    """940 fetched + 20 parked must reconcile against the 960 submitted."""
    tier = _tier()
    submitted = tier["article_counts"]["submitted_candidates"]
    parked = [n for n in tier["order_notes"] if n["status"] == "no_snapshot_on_disk"]
    self.assertEqual(submitted,
                     tier["article_counts"]["built_articles"] + len(parked))

  def test_redirect_stubs_are_disclosed(self):
    tier = _tier()
    self.assertEqual(tier["article_counts"]["redirect_stub_articles"],
                     len(tier["redirect_stub_titles"]))
    counts = tier["article_counts"]
    self.assertEqual(
      counts["substantive_articles_excluding_redirect_stubs"],
      counts["built_articles"] - counts["redirect_stub_articles"])


if __name__ == "__main__":
  unittest.main()