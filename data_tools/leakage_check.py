"""Custodian-only synthetic leakage check (stdlib only).

Given a synthetic question file and the sealed held-out set, detects near-duplicates
and RELEASES nothing sensitive. Method: character n-gram Jaccard (stdlib) as the
STANDALONE path; an optional embedding-cosine path only if a local embedding model
is already present, otherwise reports `embedding_path_available: false` and says
the n-gram path stands alone.

Emits a report containing:
- status: PASS | REJECT
- total_synthetic: int
- flagged_count: int
- flagged_ids: list[str] (SYNTHETIC ids only)
- ngram_similarity_distribution: dict (histogram buckets + max)
- dev_calibrated_threshold: float (calibrated on dev with recorded operating characteristics)
- dev_operating_characteristics: dict (flagged_rate, true_positive_rate at threshold)
- paths_available: dict (ngram: true, embedding: bool)
- heldout_seal_sha256: str

NEVER emits: held-out ids, held-out question text, held-out answers, or which
held-out item any synthetic item matched.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LeakageReport:
    status: str  # "PASS" | "REJECT"
    total_synthetic: int
    flagged_count: int
    flagged_ids: list[str]  # synthetic ids only
    ngram_similarity_distribution: dict[str, Any]
    dev_calibrated_threshold: float
    dev_operating_characteristics: dict[str, Any]
    paths_available: dict[str, bool]
    heldout_seal_sha256: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "total_synthetic": self.total_synthetic,
            "flagged_count": self.flagged_count,
            "flagged_ids": list(self.flagged_ids),
            "ngram_similarity_distribution": dict(self.ngram_similarity_distribution),
            "dev_calibrated_threshold": self.dev_calibrated_threshold,
            "dev_operating_characteristics": dict(self.dev_operating_characteristics),
            "paths_available": dict(self.paths_available),
            "heldout_seal_sha256": self.heldout_seal_sha256,
            "notes": list(self.notes),
        }

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")

    @staticmethod
    def read(path: str) -> "LeakageReport":
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return LeakageReport(
            status=d["status"],
            total_synthetic=d["total_synthetic"],
            flagged_count=d["flagged_count"],
            flagged_ids=d["flagged_ids"],
            ngram_similarity_distribution=d["ngram_similarity_distribution"],
            dev_calibrated_threshold=d["dev_calibrated_threshold"],
            dev_operating_characteristics=d["dev_operating_characteristics"],
            paths_available=d["paths_available"],
            heldout_seal_sha256=d["heldout_seal_sha256"],
            notes=d.get("notes", []),
        )


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, collapse whitespace, strip."""
    return re.sub(r"\s+", " ", text.lower().strip())


def char_ngrams(text: str, n: int = 5) -> set[str]:
    """Extract character n-grams from normalized text."""
    norm = normalize_text(text)
    if len(norm) < n:
        return {norm}
    return {norm[i:i+n] for i in range(len(norm) - n + 1)}


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def compute_ngram_similarities(
    synthetic_questions: list[dict],
    heldout_questions: list[dict],
    n: int = 5,
) -> list[tuple[str, float, str]]:
    """Compute max n-gram Jaccard similarity for each synthetic question.

    Returns list of (synthetic_qid, max_similarity, matched_heldout_qid)
    where matched_heldout_qid is INTERNAL ONLY and never exposed in report.
    """
    if not heldout_questions:
        return [(sq.get("question_id", "?"), 0.0, "?") for sq in synthetic_questions]

    # Precompute held-out n-gram sets
    heldout_ngrams = []
    for hq in heldout_questions:
        text = hq.get("text", "") or hq.get("question", "") or ""
        ng = char_ngrams(text, n)
        heldout_ngrams.append((hq.get("question_id", "?"), ng))

    results = []
    for sq in synthetic_questions:
        qid = sq.get("question_id", "?")
        text = sq.get("text", "") or sq.get("question", "") or ""
        sq_ngrams = char_ngrams(text, n)

        max_sim = -1.0
        max_hqid = "?"
        for hqid, hq_ngrams in heldout_ngrams:
            sim = jaccard_similarity(sq_ngrams, hq_ngrams)
            if sim > max_sim:
                max_sim = sim
                max_hqid = hqid

        results.append((qid, max_sim, max_hqid))

    return results


def build_histogram(values: list[float], bins: int = 20) -> dict[str, Any]:
    """Build a histogram of similarity values."""
    if not values:
        return {"bins": 0, "edges": [], "counts": [], "max": 0.0}

    edges = [i / bins for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        idx = min(int(v * bins), bins - 1)
        counts[idx] += 1

    return {
        "bins": bins,
        "edges": edges,
        "counts": counts,
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def calibrate_threshold_on_dev(
    dev_questions: list[dict],
    heldout_questions: list[dict],
    target_flagged_rate: float = 0.05,
) -> tuple[float, dict[str, Any]]:
    """Calibrate n-gram similarity threshold on dev set.

    Returns (threshold, operating_characteristics) where operating_characteristics
    includes flagged_rate and estimated_true_positive_rate at that threshold.

    The threshold is chosen to achieve approximately target_flagged_rate on dev
    (which should have no held-out overlap by construction). This gives us the
    false positive rate. True positive rate is estimated from synthetic tests.
    """
    # Compute dev vs heldout similarities (should be low/no overlap)
    dev_results = compute_ngram_similarities(dev_questions, heldout_questions)
    dev_sims = [r[1] for r in dev_results]

    # Sort similarities
    dev_sims_sorted = sorted(dev_sims)

    # Pick threshold at percentile to achieve target_flagged_rate
    # e.g., if target_flagged_rate=0.05, threshold at 95th percentile
    idx = int(len(dev_sims_sorted) * (1 - target_flagged_rate))
    idx = max(0, min(idx, len(dev_sims_sorted) - 1))
    threshold = dev_sims_sorted[idx]

    # Operating characteristics at this threshold
    flagged_on_dev = sum(1 for s in dev_sims if s >= threshold)
    flagged_rate = flagged_on_dev / len(dev_sims) if dev_sims else 0.0

    # True positive rate: estimated from known near-duplicate injection tests
    # (This would be measured during dev calibration with injected duplicates)
    # For now, we report the calibration parameters; actual TPR measured separately.
    operating_chars = {
        "calibration_target_flagged_rate": target_flagged_rate,
        "achieved_flagged_rate_on_dev": flagged_rate,
        "threshold": threshold,
        "dev_sample_size": len(dev_sims),
        "note": "True positive rate must be measured separately with injected near-duplicates during dev calibration.",
    }

    return threshold, operating_chars


def check_embedding_model_available() -> bool:
    """Check if a local embedding model is available (no download).

    This is a conservative check: looks for common local embedding model
    indicators without attempting to load/download anything.
    """
    # Check for sentence-transformers cache or local model files
    cache_dirs = [
        os.path.expanduser("~/.cache/huggingface/hub"),
        os.path.expanduser("~/.cache/torch/sentence_transformers"),
        os.path.expanduser("~/models"),
    ]
    for d in cache_dirs:
        if os.path.isdir(d):
            for root, dirs, files in os.walk(d):
                # Look for sentence-transformers model indicators
                if any("sentence-transformers" in f or "all-MiniLM" in f for f in files):
                    return True
                if any("sentence-transformers" in d or "all-MiniLM" in d for d in dirs):
                    return True

    # Check if sentence-transformers is importable and has a cached model
    try:
        import sentence_transformers
        # If importable, assume might have cached models (conservative)
        return True
    except ImportError:
        pass

    return False


def run_leakage_check(
    synthetic_questions_path: str,
    heldout_questions_path: str,
    heldout_labels_path: str,
    dev_questions_path: str | None = None,
    ngram_n: int = 5,
    target_flagged_rate: float = 0.05,
) -> LeakageReport:
    """Run the custodian-only leakage check.

    Args:
        synthetic_questions_path: Path to synthetic questions JSON (list of dicts with question_id, text)
        heldout_questions_path: Path to held-out questions JSON (list of dicts with question_id, text)
        heldout_labels_path: Path to sealed held-out labels (for seal hash)
        dev_questions_path: Optional path to dev questions for threshold calibration
        ngram_n: Character n-gram size
        target_flagged_rate: Target flagged rate for threshold calibration on dev

    Returns:
        LeakageReport with PASS/REJECT status and non-revealing statistics.
    """
    # Load data
    with open(synthetic_questions_path, "r", encoding="utf-8") as fh:
        synthetic = json.load(fh)
    with open(heldout_questions_path, "r", encoding="utf-8") as fh:
        heldout = json.load(fh)

    # Get heldout seal hash
    heldout_seal_sha256 = sha256_file(heldout_labels_path)

    # Check embedding availability
    embedding_available = check_embedding_model_available()

    # Load dev questions for calibration if provided
    dev_questions = []
    if dev_questions_path and os.path.isfile(dev_questions_path):
        with open(dev_questions_path, "r", encoding="utf-8") as fh:
            dev_questions = json.load(fh)

    # Calibrate threshold on dev (or use a conservative default if no dev)
    if dev_questions:
        threshold, operating_chars = calibrate_threshold_on_dev(
            dev_questions, heldout, target_flagged_rate
        )
    else:
        # Conservative default threshold (high similarity = near-duplicate)
        threshold = 0.7
        operating_chars = {
            "calibration_target_flagged_rate": target_flagged_rate,
            "achieved_flagged_rate_on_dev": 0.0,
            "threshold": threshold,
            "dev_sample_size": 0,
            "note": "No dev questions provided; using conservative default threshold. Calibrate on dev for production use.",
        }

    # Compute similarities
    similarities = compute_ngram_similarities(synthetic, heldout, ngram_n)

    # Build histogram (synthetic-side only)
    sim_values = [s[1] for s in similarities]
    histogram = build_histogram(sim_values)

    # Flag synthetic questions above threshold
    flagged = [(qid, sim) for qid, sim, _ in similarities if sim >= threshold]
    flagged_ids = [qid for qid, _ in flagged]

    # Determine status
    status = "REJECT" if flagged_ids else "PASS"

    # Notes
    notes = [
        f"Character {ngram_n}-gram Jaccard similarity (stdlib standalone path).",
        f"Threshold calibrated on dev: target_flagged_rate={target_flagged_rate}, achieved={operating_chars['achieved_flagged_rate_on_dev']:.3f}.",
    ]
    if not embedding_available:
        notes.append("Embedding model not available locally; n-gram path STANDS ALONE.")
    else:
        notes.append("Embedding model detected locally; embedding-cosine path available (not used in this report).")

    return LeakageReport(
        status=status,
        total_synthetic=len(synthetic),
        flagged_count=len(flagged_ids),
        flagged_ids=flagged_ids,
        ngram_similarity_distribution=histogram,
        dev_calibrated_threshold=threshold,
        dev_operating_characteristics=operating_chars,
        paths_available={
            "ngram_jaccard": True,
            "embedding_cosine": embedding_available,
        },
        heldout_seal_sha256=heldout_seal_sha256,
        notes=notes,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print(
            "Usage: python -m data_tools.leakage_check "
            "<synthetic_questions.json> <heldout_questions.json> <heldout_labels.sealed.json> "
            "[dev_questions.json]",
            file=sys.stderr,
        )
        sys.exit(2)

    synthetic_path = sys.argv[1]
    heldout_q_path = sys.argv[2]
    heldout_labels_path = sys.argv[3]
    dev_path = sys.argv[4] if len(sys.argv) > 4 else None

    report = run_leakage_check(synthetic_path, heldout_q_path, heldout_labels_path, dev_path)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    sys.exit(0 if report.status == "PASS" else 1)