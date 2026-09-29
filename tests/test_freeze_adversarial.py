"""Adversarial freeze-validation tests. All artifacts SYNTHETIC, tmp-only.

Covers reviewer P0/P1 findings with evidence: hash recomputation, fake
hashes, stub rejection, prompt-hash pin, placeholder rejection, opaque seal
verification (content never parsed/printed), question/split consistency.
"""

import hashlib
import json
import os
import tempfile
import unittest

from substrate.corpus import nodes_to_jsonl
from substrate.generator import PROMPT_HASH, GeneratorConfig
from substrate.manifest import (
  REQUIRED_CORPUS_FILE,
  REQUIRED_GENERATOR_FILE,
  REQUIRED_LABELS_FILE,
  REQUIRED_QUESTIONS_FILE,
  RunManifest,
  hash_paths,
  sha256_file,
  validate_freeze,
)
from substrate.types import CorpusNode, ThresholdPolicy
from tests.test_contract import good_trace, pinned_generator, pinned_manifest


def synth_nodes():
  # SYNTHETIC-ONLY mini corpus.
  return [
    CorpusNode(node_id="c0", kind="corpus", text="root"),
    CorpusNode(node_id="cl0", kind="cluster", text="t", parent_id="c0"),
    CorpusNode(node_id="a0", kind="article", text="UPPER", parent_id="cl0"),
    CorpusNode(node_id="s0", kind="section", text="S", parent_id="a0"),
    CorpusNode(node_id="p0", kind="paragraph", text="fact one", parent_id="s0"),
    CorpusNode(node_id="t0", kind="sentence", text="fact one", parent_id="p0"),
  ]


class FixtureRoot:
  """SYNTHETIC freeze-fixture root with CONSISTENT pinned content."""

  def __init__(self, tmp):
    self.tmp = tmp
    os.makedirs(os.path.join(tmp, "corpus"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "src"), exist_ok=True)
    self.corpus_text = nodes_to_jsonl(synth_nodes())
    self.write(REQUIRED_CORPUS_FILE, self.corpus_text)
    self.questions = [
      {"question_id": "qa", "text": "synthetic q a?", "split": "train",
       "meta": {"source_articles": ["UPPER"], "group": "g-qa"}},
      {"question_id": "qb", "text": "synthetic q b?", "split": "train",
       "meta": {"source_articles": ["a0"], "group": "g-qb"}},
    ]
    self.write(REQUIRED_QUESTIONS_FILE, json.dumps(self.questions))
    self.labels_bytes = b'{"qa": ["t0"], "qb": ["t0"]}'
    self.write(REQUIRED_LABELS_FILE, self.labels_bytes, binary=True)
    self.artifact_bytes = b"FAKE-MODEL-BYTES-SYNTHETIC"
    self.write("models/model.gguf", self.artifact_bytes, binary=True)
    self.server_bytes = b"FAKE-SERVER-BINARY-SYNTHETIC"
    self.write("bin/llama-server", self.server_bytes, binary=True)
    self.lib_bytes = b"FAKE-LIB-SYNTHETIC"
    self.write("bin/libtest.so.0", self.lib_bytes, binary=True)
    self.write("src/code.py", "x = 1\n")
    self.runtime_binaries = {
      "lib_dir": os.path.join(tmp, "bin"),
      "libs": {
        "libtest.so.0": {
          "sha256": hashlib.sha256(self.lib_bytes).hexdigest(),
          "soname_target": "libtest.so.0",
        }
      },
      "llama-server": {
        "path": os.path.join(tmp, "bin/llama-server"),
        "sha256": hashlib.sha256(self.server_bytes).hexdigest(),
      },
    }
    self.gen_dict = {
      "model_id": "org/model",
      "revision": "abc123",
      "prompt_hash": PROMPT_HASH,
      "prompt_version": "synthetic",
      "quantization": "Q4_K_M",
      "runtime": "test-cpu",
      "runtime_binaries": self.runtime_binaries,
      "file": "model.gguf",
      "artifact_path": "models/model.gguf",
      "sha256": hashlib.sha256(self.artifact_bytes).hexdigest(),
      "bytes": len(self.artifact_bytes),
      "tokenizer_id": "synth-tok",
      "chat_template_sha256": "c" * 64,
      "context_window": 4096,
      "generation": {"temperature": 0.0},
      "generator_id": "synth-generator-v1",
    }
    self.write(REQUIRED_GENERATOR_FILE, json.dumps(self.gen_dict))

  def write(self, rel, content, binary=False):
    full = os.path.join(self.tmp, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    mode = "wb" if binary else "w"
    with open(full, mode) as fh:
      fh.write(content)
    return full

  def align_questions(self, seed):
    """Rewrite fixture questions with explicit provenance consistent seeding.

    Declared split = assign_split(qid, seed) (seeded-hash check); group key
    pool-searched so the derived group split matches the declared split.
    Sources resolve against the fixture corpus ("UPPER" title, "a0" node).
    """
    from substrate.splits import assign_split

    def pool_group(want):
      for i in range(10000):
        g = f"gpool-{i}"
        if assign_split(g, seed) == want:
          return g
      raise AssertionError("group pool exhausted")

    self.questions = [
      {"question_id": q["question_id"], "text": q["text"],
       "split": assign_split(q["question_id"], seed),
       "meta": {"source_articles": [q["meta"]["source_articles"][0]],
                "group": pool_group(assign_split(q["question_id"], seed))}}
      for q in self.questions
    ]
    self.write(REQUIRED_QUESTIONS_FILE, json.dumps(self.questions))
    return self

  def manifest(self, **overrides):
    from substrate.corpus import corpus_hash
    from substrate.manifest import ArtifactPin, sha256_file

    def raw_sha(rel):
      return sha256_file(os.path.join(self.tmp, rel))

    params = {
      "run_id": "synth-freeze",
      "seed": 11,
      "phase": "round0-substrate",
      "corpus_hash": corpus_hash(synth_nodes()),
      "code_hashes": {"src/code.py": raw_sha("src/code.py")},
      "generator": GeneratorConfig.from_dict(self.gen_dict),
      "thresholds": {
        "stage0": ThresholdPolicy(
          threshold=0.2,
          interpretation="calibrated_probability",
          top_k=10,
          calibration_method="model_probability",
          score_kind="calibrated_probability",
        )
      },
      "sealed_labels_sha256": hashlib.sha256(self.labels_bytes).hexdigest(),
      "questions_sha256": raw_sha(REQUIRED_QUESTIONS_FILE),
      "split_seed": "fixture-seed",
      "split_method": "seeded-hash",
      "generator_config_sha256": raw_sha(REQUIRED_GENERATOR_FILE),
      "inventory": [
        ArtifactPin(
          path=os.path.join(self.tmp, "bin/llama-server"),
          role="external-runtime-binary",
          sha256=hashlib.sha256(self.server_bytes).hexdigest(),
          bytes=len(self.server_bytes),
        ),
        ArtifactPin(
          path=os.path.join(self.tmp, "bin/libtest.so.0"),
          role="external-runtime-library",
          sha256=hashlib.sha256(self.lib_bytes).hexdigest(),
          bytes=len(self.lib_bytes),
        ),
      ],
    }
    params.update(overrides)
    return RunManifest(**params)


class TestFreezeAdversarial(unittest.TestCase):
  def test_consistent_fixture_freezes(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp).align_questions("fixture-seed")
      check = validate_freeze(tmp, root.manifest())
      self.assertTrue(check.passed, f"expected freeze pass, gaps={check.gaps}")

  def test_wrong_corpus_content_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      root.write(REQUIRED_CORPUS_FILE, root.corpus_text + '{"bad": 1}\n')
      check = validate_freeze(tmp, root.manifest())
      self.assertFalse(check.passed)

  def test_wrong_manifest_corpus_hash_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      check = validate_freeze(tmp, root.manifest(corpus_hash="0" * 64))
      self.assertFalse(check.passed)
      self.assertTrue(any("corpus_hash mismatch" in g for g in check.gaps))

  def test_fake_code_hash_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      check = validate_freeze(tmp, root.manifest(code_hashes={"src/code.py": "fake"}))
      self.assertFalse(check.passed)
      self.assertTrue(any("code hash mismatch" in g for g in check.gaps))

  def test_missing_code_path_fails_closed(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      check = validate_freeze(tmp, root.manifest(code_hashes={"src/ghost.py": "x"}))
      self.assertFalse(check.passed)
      self.assertTrue(any("fail closed" in g for g in check.gaps))

  def test_hash_paths_raises_on_missing(self):
    with self.assertRaises(FileNotFoundError):
      hash_paths(["/nonexistent-synth-path"])

  def test_tampered_artifact_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      root.write("models/model.gguf", b"TAMPERED", binary=True)
      check = validate_freeze(tmp, root.manifest())
      self.assertFalse(check.passed)
      self.assertTrue(any("artifact" in g for g in check.gaps))

  def test_prompt_hash_mismatch_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      gen = pinned_generator(prompt_hash="0" * 64)
      check = validate_freeze(tmp, root.manifest(generator=gen))
      self.assertFalse(check.passed)
      self.assertTrue(any("prompt_hash" in g for g in check.gaps))

  def test_unpinned_quantization_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      gen = pinned_generator(quantization="unspecified")
      check = validate_freeze(tmp, root.manifest(generator=gen))
      self.assertFalse(check.passed)
      self.assertTrue(any("unpinned fields" in g for g in check.gaps))

  def test_seal_tamper_fails_without_reading_labels(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp)
      root.write(REQUIRED_LABELS_FILE, b'{"qa": ["OTHER"]}', binary=True)
      check = validate_freeze(tmp, root.manifest())
      self.assertFalse(check.passed)
      self.assertTrue(any("sealed labels hash mismatch" in g for g in check.gaps))
      # Labels content must never leak into gap messages.
      self.assertFalse(any("OTHER" in g for g in check.gaps))

  def test_split_inconsistency_fails(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = FixtureRoot(tmp).align_questions("fixture-seed")
      from substrate.splits import assign_split

      qa = dict(root.questions[0])
      if assign_split("qa", "fixture-seed") == "heldout":
        self.skipTest("seed assigns qa to heldout; inconsistency untestable")
      qa["split"] = "heldout"  # provenance group split now disagrees too
      root.write(REQUIRED_QUESTIONS_FILE, json.dumps([qa, root.questions[1]]))
      manifest = root.manifest(split_seed="fixture-seed")
      check = validate_freeze(tmp, manifest)
      self.assertFalse(check.passed)
      self.assertTrue(any("split inconsistency" in g for g in check.gaps))
      self.assertTrue(any("qa provenance" in g for g in check.gaps))

  def test_trace_fixture_is_benchmark_valid(self):
    from eval.run_format import validate_trace

    self.assertEqual(validate_trace(good_trace()), [])


if __name__ == "__main__":
  unittest.main()
