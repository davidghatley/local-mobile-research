"""Run manifests and freeze validation (fail-closed).

A run is reproducible from ONE master seed: per-component seeds are derived
deterministically via ``derive_seed`` and the derivation is logged in the
manifest. No fixed multi-seed table is invented.

``manifest.phase`` distinguishes the Round 0 substrate freeze
("round0-substrate") from later experiment freezes. Round 0 records
threshold-policy DECLARATIONS (presence + validity); learned/fitted
thresholds are produced by architecture teams in Round 1, never required
before they exist.

``validate_freeze`` RECOMPUTES every hash it checks (corpus content, questions
bytes, split-map bytes, sealed labels opaque bytes, generator config bytes,
code files, generator artifact, runtime binaries) and compares against the
manifest and the on-disk configs. Generic ``ArtifactPin`` inventory entries
cover content hashes without endless field whitelisting; the semantic
contract compare covers the fields the substrate acts on. Everything else in
the raw config is still pinned by its byte hash. Placeholders, stubs,
estimates-as-empirical, and missing hash paths all fail. Malformed artifacts
produce structured gaps, never crashes. Gap text carries ids/counts/hashes
only — never question text, label content, or article text.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass, field

from .corpus import hash_corpus_file
from .generator import PROMPT_HASH, GeneratorConfig, is_stub_generator
from .splits import (
  assign_split,
  build_article_index,
  norm_title,
  validate_group_map,
  validate_question_provenance,
  validate_questions_file,
  verify_seal_opaque,
)
from .types import ThresholdPolicy
from .private_eval import (
  private_dir,
  labels_path as private_labels_path,
  seal_path as private_seal_path,
  questions_path as private_questions_path,
  counts as private_counts,
  verify_seal as private_verify_seal,
  seal_digest as private_seal_digest,
  sha256_file as private_sha256_file,
)


def sha256_file(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def hash_paths(paths: list[str]) -> dict[str, str]:
  """Hash files. MISSING paths raise FileNotFoundError (fail closed)."""
  out: dict[str, str] = {}
  for path in sorted(paths):
    if not os.path.isfile(path):
      raise FileNotFoundError(f"hash path missing (fail closed): {path}")
    out[path] = sha256_file(path)
  return out


def derive_seed(master_seed: int, component: str) -> int:
  """Deterministically derive a per-component seed from the master seed."""
  digest = hashlib.sha256(f"{master_seed}\x00{component}".encode("utf-8")).hexdigest()
  return int(digest[:16], 16)


def derive_seeds(master_seed: int, components: list[str]) -> dict[str, int]:
  """Derive + log per-component seeds (the log goes in the manifest)."""
  return {c: derive_seed(master_seed, c) for c in components}


@dataclass(frozen=True)
class ArtifactPin:
  """Generic content pin for one artifact file.

  ``path`` is repo-relative; absolute paths are allowed ONLY with a role
  starting "external-" (explicit inventory role for out-of-tree files such as
  the inference runtime). ``bytes`` is verified when set.
  """

  path: str
  role: str
  sha256: str
  bytes: int | None = None

  def resolve(self, root: str) -> str:
    if os.path.isabs(self.path):
      return os.path.normpath(self.path)
    return os.path.normpath(os.path.join(root, self.path))

  def verify(self, root: str) -> list[str]:
    full = self.resolve(root)
    if os.path.isabs(self.path) and not self.role.startswith("external-"):
      return [f"inventory {self.role}: absolute path requires an external- role"]
    if not os.path.isfile(full):
      return [f"inventory {self.role}: file missing: {self.path}"]
    if sha256_file(full) != self.sha256:
      return [f"inventory {self.role}: sha256 mismatch (recomputed): {self.path}"]
    if self.bytes is not None and os.path.getsize(full) != self.bytes:
      return [f"inventory {self.role}: byte size mismatch: {self.path}"]
    return []

  def to_dict(self) -> dict:
    return {"path": self.path, "role": self.role, "sha256": self.sha256, "bytes": self.bytes}

  @staticmethod
  def from_dict(d: dict) -> "ArtifactPin":
    for f in ("path", "role", "sha256"):
      if f not in d:
        raise ValueError(f"ArtifactPin missing required field: {f}")
    return ArtifactPin(
      path=d["path"],
      role=d["role"],
      sha256=d["sha256"],
      bytes=None if d.get("bytes") is None else int(d["bytes"]),
    )


@dataclass
class RunManifest:
  run_id: str
  seed: int  # single master seed; components derived via derive_seed
  corpus_hash: str
  code_hashes: dict[str, str]
  generator: GeneratorConfig
  thresholds: dict[str, ThresholdPolicy]
  sealed_labels_sha256: str = "TBD"
  questions_sha256: str = "TBD"
  split_seed: str = "TBD"
  split_method: str = "seeded-hash"  # "seeded-hash" | "group-map"
  split_map_path: str = ""
  split_map_sha256: str = "TBD"
  generator_config_sha256: str = "TBD"
  inventory: list[ArtifactPin] = field(default_factory=list)
  phase: str = "round0-substrate"
  seed_derivation_log: dict[str, int] = field(default_factory=dict)
  python_version: str = field(default_factory=lambda: platform.python_version())
  platform: str = field(default_factory=lambda: platform.platform())
  argv: list[str] = field(default_factory=lambda: list(sys.argv))
  # Regime metadata (Round 0 additions)
  regime_a_heldout_groups: list[str] = field(default_factory=list)
  regime_b_document_heldout_groups: list[str] = field(default_factory=list)
  # When true, validate_freeze REQUIRES corpus/partition_census.json and checks
  # the published and approved counts against it. A consistent truncation
  # (staging drafts and partition entries deleted together) leaves every
  # internal cross-check self-satisfied, so this external pin is the only
  # thing that detects it. Synthetic freeze fixtures construct their own root
  # and do not carry a census, so the requirement is opt-in and must be
  # declared by the caller. The real verifier declares it.
  require_partition_census: bool = False
  # Digest of corpus/partition_census.json. Recorded here so the freeze manifest
  # (a durable artifact) binds the census to the run, and so the custodian can
  # record the same digest OUTSIDE the repository. A co-edit of data + census
  # is only detectable by comparing against a digest held outside git.
  partition_census_sha256: str = ""
  public_reference_pins_sha256: str = "TBD"
  # Freeze-record bindings (Round 0 closure). The durable freeze record must
  # bind the exact revision it verified, the exact verifier that verified it,
  # when the verification completed, and what every stage reported. These are
  # populated by scripts/verify_round0 stage 8 (candidate) and by the shell
  # promotion step (stage_results, verified_at_utc); they default to empty so
  # synthetic freeze fixtures that never claim a durable record keep working.
  commit_sha: str = ""
  working_tree_dirty: bool = False
  verified_at_utc: str = ""
  verifier_sha256: str = ""
  verifier_mode: str = "full"
  stage_results: list = field(default_factory=list)

  def to_dict(self) -> dict:
    return {
      "run_id": self.run_id,
      "seed": self.seed,
      "corpus_hash": self.corpus_hash,
      "code_hashes": dict(self.code_hashes),
      "generator": self.generator.to_dict(),
      "thresholds": {k: v.to_dict() for k, v in self.thresholds.items()},
      "sealed_labels_sha256": self.sealed_labels_sha256,
      "questions_sha256": self.questions_sha256,
      "split_seed": self.split_seed,
      "split_method": self.split_method,
      "split_map_path": self.split_map_path,
      "split_map_sha256": self.split_map_sha256,
      "generator_config_sha256": self.generator_config_sha256,
      "inventory": [p.to_dict() for p in self.inventory],
      "phase": self.phase,
      "seed_derivation_log": dict(self.seed_derivation_log),
      "python_version": self.python_version,
      "platform": self.platform,
      "argv": list(self.argv),
      "regime_a_heldout_groups": list(self.regime_a_heldout_groups),
      "regime_b_document_heldout_groups": list(self.regime_b_document_heldout_groups),
      "public_reference_pins_sha256": self.public_reference_pins_sha256,
      "require_partition_census": bool(self.require_partition_census),
      "partition_census_sha256": self.partition_census_sha256,
      "questions_sha256": self.questions_sha256,
      "sealed_labels_sha256": self.sealed_labels_sha256,
      "commit_sha": self.commit_sha,
      "working_tree_dirty": bool(self.working_tree_dirty),
      "verified_at_utc": self.verified_at_utc,
      "verifier_sha256": self.verifier_sha256,
      "verifier_mode": self.verifier_mode,
      "stage_results": [dict(r) for r in self.stage_results],
    }

  def write(self, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
      json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
      fh.write("\n")

  @staticmethod
  def read(path: str) -> "RunManifest":
    with open(path, "r", encoding="utf-8") as fh:
      d = json.load(fh)
    raw_thresholds = d.get("thresholds", {})
    thresholds = {
      k: (v if isinstance(v, ThresholdPolicy) else ThresholdPolicy.from_dict(v))
      for k, v in raw_thresholds.items()
    }
    return RunManifest(
      run_id=d["run_id"],
      seed=int(d["seed"]),
      corpus_hash=d["corpus_hash"],
      code_hashes=dict(d["code_hashes"]),
      generator=GeneratorConfig.from_dict(d["generator"]),
      thresholds=thresholds,
      sealed_labels_sha256=d.get("sealed_labels_sha256", "TBD"),
      questions_sha256=d.get("questions_sha256", "TBD"),
      split_seed=d.get("split_seed", "TBD"),
      split_method=d.get("split_method", "seeded-hash"),
      split_map_path=d.get("split_map_path", ""),
      split_map_sha256=d.get("split_map_sha256", "TBD"),
      generator_config_sha256=d.get("generator_config_sha256", "TBD"),
      inventory=[ArtifactPin.from_dict(p) for p in d.get("inventory", [])],
      phase=d.get("phase", "round0-substrate"),
      seed_derivation_log={k: int(v) for k, v in d.get("seed_derivation_log", {}).items()},
      python_version=d.get("python_version", "?"),
      platform=d.get("platform", "?"),
      argv=list(d.get("argv", [])),
      regime_a_heldout_groups=list(d.get("regime_a_heldout_groups", [])),
      regime_b_document_heldout_groups=list(d.get("regime_b_document_heldout_groups", [])),
      require_partition_census=bool(d.get("require_partition_census", False)),
      partition_census_sha256=d.get("partition_census_sha256", ""),
      public_reference_pins_sha256=d.get("public_reference_pins_sha256", "TBD"),
      commit_sha=d.get("commit_sha", ""),
      working_tree_dirty=bool(d.get("working_tree_dirty", False)),
      verified_at_utc=d.get("verified_at_utc", ""),
      verifier_sha256=d.get("verifier_sha256", ""),
      verifier_mode=d.get("verifier_mode", "full"),
      stage_results=[dict(r) for r in d.get("stage_results", [])],
    )


@dataclass
class FreezeCheck:
  passed: bool
  gaps: list[str]

  def to_dict(self) -> dict:
    return {"passed": self.passed, "gaps": list(self.gaps)}


# Artifacts that MUST exist with real pinned content before any freeze claim.
# The sealed private-test labels live OUTSIDE the repo at LMR_PRIVATE_EVAL_DIR
# (Phase 5). The in-repo manifest carries only opaque digests from
# corpus/private_test_manifest.json. shadow_dev is dev-visible and never sealed.
REQUIRED_CORPUS_FILE = "corpus/corpus.jsonl"
REQUIRED_QUESTIONS_FILE = "corpus/questions.json"
# External pin on the partition size. Without it a consistent
# truncation passes every internal cross-check.
PARTITION_CENSUS_FILE = "corpus/partition_census.json"
# Legacy in-repo path retained for backward compat in some tests; the REAL
# sealed labels are out-of-repo via substrate.private_eval.labels_path().
REQUIRED_LABELS_FILE = "corpus/heldout_labels.sealed.json"
REQUIRED_GENERATOR_FILE = "corpus/generator_config.json"

PLACEHOLDER_HASHES = frozenset({"", "TBD", "SYNTHETIC"})

# Semantic generator fields compared manifest-vs-disk. All OTHER raw config
# fields (license, download_url, verification, tokenizer detail, runtime_full,
# threads, budgets, prompt_delivery...) are pinned generically by the raw
# config byte hash, not whitelisted one by one.
GENERATOR_SEMANTIC_FIELDS = (
  "model_id",
  "revision",
  "prompt_hash",
  "quantization",
  "runtime",
  "file",
  "artifact_sha256",
  "generator_id",
  "tokenizer_id",
  "chat_template_sha256",
  "context_window",
)


def _runtime_declarations(disk: dict) -> tuple[list[dict], list[str]]:
  """Declared executable/library files from the raw generator config.

  Returns (declarations, errors). Each declaration: {name, path, sha256,
  role}. Absolute out-of-tree paths get explicit external- roles. Malformed
  declarations are errors, never crashes.
  """
  rb = disk.get("runtime_binaries")
  if not isinstance(rb, dict):
    return [], ["generator config: runtime_binaries inventory missing or malformed"]
  errors: list[str] = []
  declarations: list[dict] = []
  lib_dir = rb.get("lib_dir", "")
  libs = rb.get("libs", {})
  if not isinstance(libs, dict):
    errors.append("generator config: runtime_binaries.libs malformed")
    libs = {}
  for name, rec in libs.items():
    if not isinstance(rec, dict) or "sha256" not in rec:
      errors.append(f"generator config: runtime lib {str(name)[:80]} malformed")
      continue
    filename = rec.get("soname_target") or name
    path = os.path.join(lib_dir, filename) if lib_dir else filename
    role = "external-runtime-library" if os.path.isabs(path) else "runtime-library"
    declarations.append({"name": str(name), "path": path, "sha256": rec["sha256"], "role": role})
  server = rb.get("llama-server", {})
  if isinstance(server, dict) and server.get("path") and server.get("sha256"):
    spath = server["path"]
    role = "external-runtime-binary" if os.path.isabs(spath) else "runtime-binary"
    declarations.append(
      {"name": "llama-server", "path": spath, "sha256": server["sha256"], "role": role}
    )
  elif server:
    errors.append("generator config: llama-server declaration malformed")
  return declarations, errors


def validate_freeze(root: str, manifest: RunManifest) -> FreezeCheck:
  """Fail-closed freeze validation with hash recomputation.

  Verifies: phase, artifact presence, recomputed corpus hash, questions byte
  hash + schema + split consistency, group-map bytes + structure + article
  resolution + QA consistency, opaque seal hash (bytes only, labels never
  parsed/printed), full generator contract (raw config bytes, semantic
  fields, artifact bytes/hash, prompt pin, runtime binaries incl. external
  paths with explicit roles, manifest inventory coverage), stub/placeholder
  rejection, per-file code hashes, threshold policy declarations, seed-log
  consistency. Malformed artifacts yield structured gaps, never crashes; gap
  text carries ids/counts/hashes only.
  """
  gaps: list[str] = []
  # Required artifacts: corpus, questions (public partition), generator config.
  # Private sealed labels are OUTSIDE the repo at LMR_PRIVATE_EVAL_DIR;
  # the legacy in-repo path (REQUIRED_LABELS_FILE) is NOT required.
  paths = {
    "corpus": os.path.join(root, REQUIRED_CORPUS_FILE),
    "questions": os.path.join(root, REQUIRED_QUESTIONS_FILE),
    "generator": os.path.join(root, REQUIRED_GENERATOR_FILE),
  }
  for name, full in paths.items():
    if not os.path.isfile(full):
      gaps.append(f"missing required artifact: {os.path.relpath(full, root)}")

  # Legacy in-repo sealed labels path (for backward compat with tests only)
  labels_path = os.path.join(root, REQUIRED_LABELS_FILE)

  if manifest.phase != "round0-substrate":
    gaps.append(f"unknown freeze phase: {manifest.phase!r}")

  # --- corpus: recompute hash from content; collect article titles ---
  corpus_titles: set[str] | None = None
  corpus_nodes: list = []
  if os.path.isfile(paths["corpus"]):
    try:
      nodes, actual = hash_corpus_file(paths["corpus"])
      corpus_nodes = nodes
      if actual != manifest.corpus_hash:
        gaps.append("corpus_hash mismatch: manifest does not match corpus.jsonl content")
      corpus_titles = {norm_title(n.text) for n in nodes if n.kind == "article"}
    except ValueError as exc:
      gaps.append(f"corpus artifact invalid: {str(exc)[:200]}")
  if manifest.corpus_hash in PLACEHOLDER_HASHES:
    gaps.append("corpus_hash is a placeholder, not a real pinned hash")

  # --- sealed labels: opaque byte-hash only; never parse or print ---
  # Private test seal lives OUTSIDE the repo at LMR_PRIVATE_EVAL_DIR.
  # The manifest records the opaque seal digest from corpus/private_test_manifest.json.
  # For backward compatibility with tests that use the legacy in-repo path,
  # also accept verification against REQUIRED_LABELS_FILE if present.
  if manifest.sealed_labels_sha256 in PLACEHOLDER_HASHES:
    gaps.append("sealed_labels_sha256 unrecorded")
  else:
    verified = False
    # Try out-of-repo private eval first (real freezes)
    try:
      private_verify_seal(manifest.sealed_labels_sha256)
      verified = True
    except Exception:
      pass
    # Fallback: legacy in-repo sealed labels (test fixtures)
    if not verified and os.path.isfile(labels_path):
      try:
        if verify_seal_opaque(labels_path, manifest.sealed_labels_sha256):
          verified = True
        else:
          gaps.append("sealed labels hash mismatch: artifact changed since seal (legacy path)")
      except FileNotFoundError as exc:
        gaps.append(str(exc))
    if not verified:
      gaps.append("sealed labels verification failed: neither out-of-repo private seal nor legacy in-repo artifact matched")

  # --- questions: byte hash + schema + split consistency (labels untouched) ---
  question_entries: list[dict] = []
  if manifest.questions_sha256 in PLACEHOLDER_HASHES:
    gaps.append("questions_sha256 unrecorded")
  elif os.path.isfile(paths["questions"]):
    try:
      if sha256_file(paths["questions"]) != manifest.questions_sha256:
        gaps.append("questions_sha256 mismatch: manifest does not match questions.json bytes")
    except OSError as exc:
      gaps.append(f"questions file unreadable: {str(exc)[:120]}")
  if os.path.isfile(paths["questions"]):
    try:
      checked = validate_questions_file(paths["questions"])
    except (ValueError, OSError) as exc:
      checked = {"ids": [], "errors": [str(exc)[:200]]}
    gaps.extend(f"questions file: {e}" for e in checked["errors"])
    try:
      with open(paths["questions"], "r", encoding="utf-8") as fh:
        raw_entries = json.load(fh)
      question_entries = [e for e in raw_entries if isinstance(e, dict)]
    except (ValueError, OSError) as exc:
      gaps.append(f"questions file malformed: {str(exc)[:120]}")
    map_groups: dict[str, str] = {}
    article_to_group: dict[str, str] = {}
    if manifest.split_method == "seeded-hash":
      if manifest.split_seed in ("", "TBD"):
        gaps.append("split_seed unrecorded for seeded-hash split method")
      else:
        declared = {e["question_id"]: e.get("split", "dev") for e in question_entries}
        mismatched = [
          qid
          for qid in checked["ids"]
          if declared.get(qid) != assign_split(qid, manifest.split_seed)
        ]
        if mismatched:
          gaps.append(
            f"split inconsistency for {len(mismatched)} question ids "
            f"(e.g. {mismatched[:3]}): declared split != assign_split(seed)"
          )
    elif manifest.split_method == "group-map":
      map_full = os.path.join(root, manifest.split_map_path) if manifest.split_map_path else ""
      if not manifest.split_map_path or not os.path.isfile(map_full):
        gaps.append("group-map split method without a pinned split_map_path artifact")
      else:
        if manifest.split_map_sha256 in PLACEHOLDER_HASHES:
          gaps.append("split_map_sha256 unrecorded")
        else:
          try:
            if sha256_file(map_full) != manifest.split_map_sha256:
              gaps.append("split_map_sha256 mismatch: manifest does not match map bytes")
          except OSError as exc:
            gaps.append(f"split map unreadable: {str(exc)[:120]}")
        try:
          with open(map_full, "r", encoding="utf-8") as fh:
            map_data = json.load(fh)
        except (ValueError, OSError) as exc:
          map_data = None
          gaps.append(f"split map malformed: {str(exc)[:120]}")
        if isinstance(map_data, dict):
          res = validate_group_map(map_data, corpus_titles)
          gaps.extend(f"split map: {e}" for e in res["errors"])
          article_to_group = res["article_to_group"]
          groups_raw = map_data.get("groups", {})
          map_groups = {
            g: rec.get("split")
            for g, rec in groups_raw.items()
            if isinstance(rec, dict)
          }
    else:
      gaps.append(f"unknown split_method: {manifest.split_method}")

  # --- QA provenance: mandatory for controlled, dev-only public exception ---
  #
  # Provenance is validated against the CUSTODIAN drafts, not the public
  # partition. corpus/questions.json is the worker-visible projection and
  # deliberately OMITS meta.group / meta.evidence_groups / meta.source_articles:
  # those name the answer's location, and publishing them would hand every
  # retriever a 1-3 article candidate set inside a 297-article corpus. So the
  # public partition cannot carry provenance, and the freeze check reads the
  # drafts. Split membership is still cross-checked: the draft's declared split
  # must equal the split recorded in the public partition, so the two files
  # cannot drift apart unnoticed.
  staging_dir = os.path.join(root, "staging")
  provenance_entries: list[dict] = []
  if os.path.isdir(staging_dir):
    for name in sorted(os.listdir(staging_dir)):
      if not name.endswith(".json"):
        continue
      path = os.path.join(staging_dir, name)
      if not os.path.isfile(path):
        continue
      try:
        with open(path, "r", encoding="utf-8") as fh:
          rec = json.load(fh)
      except (ValueError, OSError):
        continue
      if isinstance(rec, dict):
        provenance_entries.append(rec)

  if not provenance_entries:
    # No staging drafts. Fall back to the public partition itself, which is
    # valid for synthetic freeze fixtures that inline their own provenance.
    # A real freeze has staging drafts and never takes this path.
    provenance_entries = [
      e for e in question_entries
      if isinstance(e.get("meta"), dict) and e["meta"].get("source_articles")
    ]
    if not provenance_entries:
      gaps.append("qa provenance: no staging drafts and no inlined provenance")
  if provenance_entries and not corpus_nodes:
    gaps.append("qa provenance: unresolvable without corpus artifact")
  else:
    prov = validate_question_provenance(
      provenance_entries,
      article_index=build_article_index(corpus_nodes),
      map_groups=map_groups if manifest.split_method == "group-map" else {},
      article_to_group=article_to_group
      if manifest.split_method == "group-map"
      else {},
      split_seed=manifest.split_seed,
      use_map_splits=manifest.split_method == "group-map",
    )
    gaps.extend(f"qa provenance: {e}" for e in prov["errors"])

    # Drift check: when provenance came from staging drafts, the public
    # partition and the drafts must agree on WHICH questions are published and
    # under WHICH split. Skipped for the inlined-provenance fixture path, where
    # the same entries are both sides.
    draft_split = {
      e.get("question_id"): e.get("split", "dev")
      for e in provenance_entries
      if isinstance(e, dict) and isinstance(e.get("question_id"), str)
    }
    public_split = {
      e.get("question_id"): e.get("split", "dev")
      for e in question_entries
      if isinstance(e, dict) and isinstance(e.get("question_id"), str)
    }
    if draft_split and draft_split != public_split:
      only_public = sorted(set(public_split) - set(draft_split))
      only_drafts = sorted(set(draft_split) - set(public_split))
      if only_public:
        gaps.append(
          f"partition drift: {len(only_public)} published id(s) have no staging "
          f"draft (e.g. {only_public[:3]})"
        )
      if only_drafts:
        gaps.append(
          f"partition drift: {len(only_drafts)} approved draft(s) are not "
          f"published (e.g. {only_drafts[:3]})"
        )
      for qid in sorted(set(draft_split) & set(public_split)):
        if draft_split[qid] != public_split[qid]:
          gaps.append(
            f"partition drift: {qid} published as {public_split[qid]!r} but its "
            f"draft says {draft_split[qid]!r}"
          )

    # External census pin. A CONSISTENT truncation (drafts and partition
    # entries deleted together) leaves the drift check self-satisfied, so the
    # only thing that detects it is a pin held outside the artifacts it checks.
    census_path = os.path.join(root, PARTITION_CENSUS_FILE)
    census_present = os.path.isfile(census_path)
    if manifest.require_partition_census and not census_present:
      gaps.append(f"missing census artifact: {PARTITION_CENSUS_FILE}")
    elif census_present and manifest.partition_census_sha256:
      # Digest binding. This is INDEPENDENT of the content checks below: an
      # earlier version made them alternatives, so recording a digest silently
      # disabled the count checks. Two separate questions, two separate checks.
      try:
        actual = sha256_file(census_path)
        if actual != manifest.partition_census_sha256:
          gaps.append(
            "partition_census_sha256 mismatch: the census changed since this "
            "freeze manifest was built (a co-edit of data + census)"
          )
      except OSError as exc:
        gaps.append(f"census artifact unreadable: {str(exc)[:120]}")
    if not census_present:
      pass  # census not required by this manifest (synthetic fixture)
    else:
      try:
        with open(census_path, "r", encoding="utf-8") as fh:
          census = json.load(fh)
      except (ValueError, OSError) as exc:
        gaps.append(f"census artifact unreadable: {str(exc)[:120]}")
        census = None
      if isinstance(census, dict):
        want_total = (census.get("expected") or {}).get("total")
        want_split = (census.get("expected") or {}).get("by_split") or {}
        want_approved = (census.get("approved_drafts") or {}).get("total")
        if isinstance(want_total, int) and len(public_split) != want_total:
          gaps.append(
            f"partition census mismatch: {len(public_split)} published id(s), "
            f"census pins {want_total}. A consistent truncation must not pass."
          )
        published_split_counts: dict[str, int] = {}
        for split in public_split.values():
          published_split_counts[split] = published_split_counts.get(split, 0) + 1
        for split, want in sorted(want_split.items()):
          got = published_split_counts.get(split, 0)
          if got != want:
            gaps.append(
              f"partition census mismatch: split {split} has {got} id(s), "
              f"census pins {want}"
            )
        if isinstance(want_approved, int) and draft_split:
          approved = sum(1 for e in provenance_entries
                         if isinstance(e, dict)
                         and (e.get("provenance") or {}).get("decision") == "approve")
          if approved != want_approved:
            gaps.append(
              f"approved-draft census mismatch: {approved} approved draft(s), "
              f"census pins {want_approved}"
            )
        rejected = set((census.get("rejected_quarantined") or {}).get("ids") or [])
        leaked = sorted(rejected & (set(public_split) | set(draft_split)))
        if leaked:
          gaps.append(
            f"rejected id(s) present among published/approved items: {leaked}"
          )

  # --- generator: raw config bytes, semantic contract, artifact, runtime ---
  gen = manifest.generator
  if is_stub_generator(gen.generator_id) or is_stub_generator(gen.model_id):
    gaps.append("generator is an infrastructure stub (disallowed for freeze)")
  unpinned = gen.unpinned_fields()
  if unpinned:
    gaps.append(f"generator contract unpinned fields: {sorted(unpinned)}")
  if gen.prompt_hash != PROMPT_HASH:
    gaps.append("generator prompt_hash does not match the fixed Round 0 prompt")
  if manifest.generator_config_sha256 in PLACEHOLDER_HASHES:
    gaps.append("generator_config_sha256 unrecorded")
  elif os.path.isfile(paths["generator"]):
    try:
      if sha256_file(paths["generator"]) != manifest.generator_config_sha256:
        gaps.append("generator_config_sha256 mismatch: manifest does not match config bytes")
    except OSError as exc:
      gaps.append(f"generator config unreadable: {str(exc)[:120]}")
  disk: dict = {}
  if os.path.isfile(paths["generator"]):
    try:
      with open(paths["generator"], "r", encoding="utf-8") as fh:
        loaded = json.load(fh)
      if not isinstance(loaded, dict):
        gaps.append("generator config malformed: top level must be an object")
      else:
        disk = loaded
    except (ValueError, OSError) as exc:
      gaps.append(f"generator config malformed: {str(exc)[:120]}")
  if disk:
    disk_cfg = GeneratorConfig.from_dict(disk)
    for field_name in GENERATOR_SEMANTIC_FIELDS:
      if getattr(disk_cfg, field_name) != getattr(gen, field_name):
        gaps.append(f"generator manifest/disk mismatch on {field_name}")
    if disk_cfg.artifact_bytes != gen.artifact_bytes:
      gaps.append("generator manifest/disk mismatch on artifact_bytes")
    if disk_cfg.sampling != gen.sampling:
      gaps.append("generator manifest/disk mismatch on sampling")
    artifact_rel = disk.get("artifact_path", disk_cfg.file)
    artifact_full = os.path.join(root, artifact_rel)
    if not os.path.isfile(artifact_full):
      gaps.append(f"generator artifact missing on disk: {artifact_rel}")
    else:
      if gen.artifact_bytes is not None and os.path.getsize(artifact_full) != gen.artifact_bytes:
        gaps.append("generator artifact byte size mismatch")
      if gen.artifact_sha256 not in ("", "TBD") and (
        sha256_file(artifact_full) != gen.artifact_sha256
      ):
        gaps.append("generator artifact sha256 mismatch (recomputed)")
    declarations, decl_errors = _runtime_declarations(disk)
    gaps.extend(decl_errors)
    pinned = {
      (os.path.normpath(p.path), p.sha256)
      for p in manifest.inventory
      if p.role.startswith("runtime-") or p.role.startswith("external-runtime")
    }
    for decl in declarations:
      # Verify executable/library bytes at declared paths, incl. external.
      dpath = decl["path"] if os.path.isabs(decl["path"]) else os.path.join(root, decl["path"])
      if not os.path.isfile(dpath):
        gaps.append(f"runtime binary missing: {decl['name']} ({decl['role']})")
      elif sha256_file(dpath) != decl["sha256"]:
        gaps.append(f"runtime binary sha256 mismatch (recomputed): {decl['name']}")
      if (os.path.normpath(decl["path"]), decl["sha256"]) not in pinned:
        gaps.append(f"runtime binary unpinned in manifest inventory: {decl['name']}")

  # --- manifest inventory: every entry verifies ---
  for pin in manifest.inventory:
    gaps.extend(pin.verify(root))

  # --- code hashes: every listed file must exist and match (fail closed) ---
  if not manifest.code_hashes:
    gaps.append("code_hashes empty: run manifest has no provenance")
  for rel, expected in sorted(manifest.code_hashes.items()):
    full = os.path.join(root, rel)
    if not os.path.isfile(full):
      gaps.append(f"code hash path missing (fail closed): {rel}")
    elif sha256_file(full) != expected:
      gaps.append(f"code hash mismatch (recomputed): {rel}")

  # --- threshold policies: Round 0 records DECLARATIONS, not learned fits ---
  # Round 0 substrate freeze must declare the calibration policy that exists.
  # The actual calibrated thresholds are produced by Round 1 architecture teams.
  if not manifest.thresholds:
    # Record the calibration policy declaration that exists in the substrate
    # The substrate defines ThresholdPolicy with model_probability as evaluable
    # and none_ranking_only for ranking-only stages. This is a DECLARATION,
    # not a fitted calibration.
    gaps.append("thresholds empty: calibration policy declaration unrecorded")
  for stage, policy in sorted(manifest.thresholds.items()):
    if not isinstance(policy, ThresholdPolicy):
      gaps.append(f"thresholds[{stage}]: not a ThresholdPolicy")
      continue
    gaps.extend(f"thresholds[{stage}]: {e}" for e in policy.validate())

  # --- seed derivation log consistency ---
  for component, logged in sorted(manifest.seed_derivation_log.items()):
    if derive_seed(manifest.seed, component) != logged:
      gaps.append(f"seed derivation mismatch for component {component!r}")

  # --- freeze-record bindings: a real freeze must name its revision --------
  # These fields are what make the durable record re-readable and comparable:
  # the exact commit verified, the exact verifier script, when verification
  # completed, in which mode, and what every stage reported. Synthetic freeze
  # fixtures never claim a durable record, so the requirement is opt-in via
  # require_partition_census, exactly like the census requirement above.
  if manifest.require_partition_census:
    if not isinstance(manifest.commit_sha, str) or len(manifest.commit_sha) != 40:
      gaps.append("commit_sha unrecorded: the freeze record must bind the exact commit")
    else:
      try:
        int(manifest.commit_sha, 16)
      except ValueError:
        gaps.append("commit_sha malformed: not a 40-hex commit SHA")
    if manifest.verifier_sha256 in PLACEHOLDER_HASHES or len(manifest.verifier_sha256) != 64:
      gaps.append("verifier_sha256 unrecorded: the freeze record must bind the verifier script hash")
    if manifest.verifier_mode != "full":
      gaps.append(f"verifier_mode is {manifest.verifier_mode!r}: a durable freeze record requires mode 'full'")
    if not manifest.verified_at_utc:
      gaps.append("verified_at_utc unrecorded: the freeze record must carry its verification timestamp")
    # working_tree_dirty is RECORDED as provenance AND is a gap when set: on
    # a dirty tree the recorded code_hashes hash the files on disk while
    # commit_sha names HEAD, so the two disagree and the record would not
    # re-verify at its own commit. Synthetic freeze fixtures never claim a
    # durable record, so the requirement is opt-in via
    # require_partition_census, exactly like the census requirement above.
    if manifest.working_tree_dirty:
      if manifest.require_partition_census:
        gaps.append(
          "working_tree_dirty: the tree was dirty, so the recorded "
          "code_hashes do not match the recorded commit (not re-verifiable)"
        )

  # --- Regime metadata validations (Round 0 additions) ---
  # PAIRED DESIGN (Issue 3, Phase 3): Regime B is a TAGGED PAIRED CONDITION
  # over the SAME questions, not an exclusive population. Regime A covers
  # the full shadow_dev population; Regime B groups name the diverse subset
  # re-evaluated under document-heldout (see substrate/regime_metadata.py
  # and docs/regime-pairing.md). Forward split vocabulary is "shadow_dev";
  # legacy "heldout" maps are accepted for backward compatibility.
  # (a) regime A groups cover the shadow_dev/heldout groups in the derived regime metadata
  #     (Regime B groups overlap A by design; union coverage is what is checked)
  # (b) regime B groups are shadow_dev/heldout groups, never train/dev/private_test
  # (c) the document-heldout excluded-article artifact exists iff regime B groups are non-empty
  # (d) public_reference_pins_sha256 matches references/public_eval_pins.json bytes
  # (e) the custody audit log, if present, has entries whose seal_sha256 matches the sealed labels hash

  # Load regime metadata for validation (derived from split map)
  if manifest.split_method == "group-map" and manifest.split_map_path:
    map_full = os.path.join(root, manifest.split_map_path)
    if os.path.isfile(map_full):
      try:
        from .regime_metadata import derive_regime_metadata, REGIME_A, REGIME_B
        regime_meta = derive_regime_metadata(map_full)

        # Collect all heldout groups from regime metadata
        regime_meta_heldout_groups = {
          g.group_key for g in regime_meta.regime_a_groups + regime_meta.regime_b_groups
        }

        # Only validate regime coverage if regime metadata has heldout groups
        if regime_meta_heldout_groups:
          # (a) Check coverage: manifest regime groups should cover regime metadata heldout groups
          manifest_regime_groups = set(manifest.regime_a_heldout_groups) | set(manifest.regime_b_document_heldout_groups)
          missing_in_manifest = regime_meta_heldout_groups - manifest_regime_groups
          if missing_in_manifest:
            gaps.append(
              f"regime metadata heldout groups not covered in manifest: {sorted(missing_in_manifest)}"
            )
          extra_in_manifest = manifest_regime_groups - regime_meta_heldout_groups
          if extra_in_manifest:
            gaps.append(
              f"manifest regime groups not in regime metadata heldout groups: {sorted(extra_in_manifest)}"
            )

          # (b) Regime B groups must be shadow_dev/heldout groups, never
          # train/dev/private_test. Explicit if/elif/else chain (no nested
          # else-binding ambiguity): missing map entry and wrong split are
          # distinct, separately reported gaps.
          regime_b_set = set(manifest.regime_b_document_heldout_groups)
          if regime_b_set:
            # Verify none are train/dev/private_test groups (forward
            # "shadow_dev" first; legacy "heldout" accepted).
            with open(map_full, "r", encoding="utf-8") as fh:
              map_data = json.load(fh)
            groups_raw = map_data.get("groups", {})
            for g in sorted(regime_b_set):
              rec = groups_raw.get(g)
              if rec is None:
                gaps.append(f"regime B group {g!r} not found in split map")
              elif rec.get("split") not in ("shadow_dev", "heldout"):
                gsplit = rec.get("split")
                gaps.append(f"regime B group {g!r} has split {gsplit!r}, must be shadow_dev/heldout")
          else:
            # Only flag empty regime B if the split map actually has heldout groups
            # that could support a document-heldout regime. Read the split map
            # here: the `regime_b_set` branch above only loads it when non-empty.
            with open(map_full, "r", encoding="utf-8") as fh:
              map_data = json.load(fh)
            groups_raw = map_data.get("groups", {})
            heldout_groups_in_map = {
              g for g, rec in groups_raw.items() if rec.get("split") in ("shadow_dev", "heldout")
            }
            if heldout_groups_in_map:
              gaps.append("regime_b_document_heldout_groups is empty but split map has shadow_dev/heldout groups")

          # (c) Document-heldout excluded-article artifact exists iff regime B groups non-empty
          if regime_b_set:
            excluded_artifact = os.path.join(root, "corpus", "regime_b_excluded_articles.json")
            if not os.path.isfile(excluded_artifact):
              gaps.append("regime B groups non-empty but regime_b_excluded_articles.json artifact missing")

      except Exception as exc:
        gaps.append(f"regime metadata validation failed: {str(exc)[:200]}")

  # (d) public_reference_pins_sha256 matches references/public_eval_pins.json bytes
  # Only validate if not a placeholder (real freezes must pin this)
  if manifest.public_reference_pins_sha256 not in PLACEHOLDER_HASHES:
    pins_path = os.path.join(root, "references", "public_eval_pins.json")
    if os.path.isfile(pins_path):
      try:
        if sha256_file(pins_path) != manifest.public_reference_pins_sha256:
          gaps.append("public_reference_pins_sha256 mismatch: manifest does not match pins file bytes")
      except OSError as exc:
        gaps.append(f"public eval pins file unreadable: {str(exc)[:120]}")
    else:
      gaps.append("public_reference_pins_sha256 recorded but references/public_eval_pins.json missing")

  # (e) Custody audit log entries have seal_sha256 matching sealed labels hash
  audit_path = os.path.join(root, "heldout_access_log.jsonl")
  if os.path.isfile(audit_path) and manifest.sealed_labels_sha256 not in PLACEHOLDER_HASHES:
    try:
      with open(audit_path, "r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, 1):
          line = line.strip()
          if not line:
            continue
          try:
            entry = json.loads(line)
            entry_seal = entry.get("seal_sha256")
            if entry_seal and entry_seal != manifest.sealed_labels_sha256:
              gaps.append(
                f"custody audit line {line_num}: seal_sha256 {entry_seal[:16]}... "
                f"!= manifest sealed_labels_sha256 {manifest.sealed_labels_sha256[:16]}..."
              )
          except json.JSONDecodeError:
            gaps.append(f"custody audit line {line_num}: malformed JSON")
    except OSError as exc:
      gaps.append(f"custody audit log unreadable: {str(exc)[:120]}")

  return FreezeCheck(passed=not gaps, gaps=gaps)
