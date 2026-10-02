#!/usr/bin/env python3
"""
Deterministic classifier for scale corpus articles.

Labels each of the 940 scale articles as one of:
  background     — general distractor material, no strong confusable overlap
  confusable_adversarial — title/keyword overlaps with core topics/questions
  redirect_stub  — #REDIRECT stub (disclosed in tier_1k.json redirect_stub_titles)
  unknown        — fallback (should not occur if all articles are classified)

Heuristic for confusable_adversarial:
  1. Title keyword match against core corpus article titles (normalized key via bp.norm_key)
  2. Title keyword match against known confusable themes:
     - Roman Empire variants (Rome, imperial, Augustus, etc.)
     - Nile (Nile River, related geographic)
     - World War I/II (WWI, WWII, war, 1914-1918, 1939-1945)
     - Big cat species (Lion, Tiger, Leopard, Jaguar, etc.)
     - Disambiguation-heavy titles (same name, different entities)
  3. Heuristic is prefix/substring matching on norm_key; does NOT imply semantic
     relatedness, only surface‑level retrieval risk.
  4. Heuristic limits documented honestly in method field.

Output: corpus/scale/scale_classification.json
  { revision, method, counts, articles: [{title, class, reason}] }
"""

import json
import os
import sys
import hashlib

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE_DIR = os.path.join(PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "corpus"))

import build_pilot as bp  # noqa: E402


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_scale_articles(scale_dir):
    """Load all 940 scale article nodes from distractor.jsonl."""
    articles = []
    distractor_path = os.path.join(scale_dir, "distractor.jsonl")
    with open(distractor_path, encoding="utf-8") as f:
        for line in f:
            node = json.loads(line)
            # Only include article-kind nodes (not corpus root, not paragraph/sentence)
            if node.get("kind") == "article":
                articles.append(node)
    return articles


def load_redirect_stub_titles(tier_1k_path):
    """Load the list of redirect stub titles from tier_1k.json."""
    with open(tier_1k_path, encoding="utf-8") as f:
        tier = json.load(f)
    return set(tier["redirect_stub_titles"])


def is_redirect_stub(node, redirect_titles):
    """Check if a node is a redirect stub via wikitext #REDIRECT or title in known list."""
    wikitext = node.get("wikitext", "")
    title = node.get("requested_title", "").strip()
    # Check for #REDIRECT in wikitext
    if "#REDIRECT" in wikitext.upper() or "#redirect" in wikitext.lower():
        return True
    # Check title against known redirect stub list
    if title in redirect_titles:
        return True
    return False


def classify_article(node, core_norm_keys, redirect_titles):
    """
    Classify a single scale article.

    Returns (class_name, reason_string).
    Priority: redirect_stub > confusable_adversarial > background > unknown
    """
    title = node.get("requested_title", "").strip()
    wikitext = node.get("wikitext", "")

    # 1. Redirect stub check (highest priority)
    if is_redirect_stub(node, redirect_titles):
        return "redirect_stub", f"redirect_stub: wikitext contains #REDIRECT or title in tier_1k.json redirect_stub_titles list"

    # 2. Confusable adversarial check
    # Normalize the title the same way the core corpus does
    norm_title = bp.norm_key(title)

    # Check against core normalized title keys (surface-level overlap)
    # If this article's norm_key matches a core article's norm_key, it's confusable
    # (this catches case-variants, spelling variants that normalize the same)
    if norm_title in core_norm_keys:
        return "confusable_adversarial",
                f"confusable_adversarial: normalized title '{norm_title}' matches core corpus normalized key"

    # Check for keyword-based confusable themes
    # Roman Empire variants
    roman_keywords = ["rome", "roman", "imperial", "augustus", "nero", "caesar", "spqr"]
    # Nile-related
    nile_keywords = ["nile", "nile river", "egyptian", "khnum", "hapi"]
    # World War themes
    war_keywords = ["wwi", "wwii", "world war", "1914", "1918", "1939", "1945", "battle", "front"]
    # Big cat species
    bigcat_keywords = ["lion", "tiger", "leopard", "jaguar", "cheetah", "panther", "cat"]
    # Disambiguation-style indicators
    disambig_indicators = ["(disambiguation)", " (other)", " (film)", " (book)", " (album)"]

    title_lower = title.lower()

    # Check each confusable category
    for kw in roman_keywords:
        if kw in title_lower:
            return "confusable_adversarial",
                    f"confusable_adversarial: title contains Roman Empire keyword '{kw}'"

    for kw in nile_keywords:
        if kw in title_lower:
            return "confusable_adversarial",
                    f"confusable_adversarial: title contains Nile-related keyword '{kw}'"

    for kw in war_keywords:
        if kw in title_lower:
            return "confusable_adversarial",
                    f"confusable_adversarial: title contains war-related keyword '{kw}'"

    for kw in bigcat_keywords:
        if kw in title_lower:
            return "confusable_adversarial",
                    f"confusable_adversarial: title contains big cat keyword '{kw}'"

    # Check for disambiguation indicators that suggest multiple entities
    for kw in disambig_indicators:
        if kw in title_lower:
            return "confusable_adversarial",
                    f"confusable_adversarial: title contains disambiguation indicator '{kw}'"

    # 3. Fallback to background
    return "background", f"background: no confusable keyword or core title overlap detected"


def main():
    scale_dir = os.path.join(PROJECT_ROOT, "corpus", "scale")
    tier_1k_path = os.path.join(scale_dir, "tier_1k.json")

    # Load data
    articles = load_scale_articles(scale_dir)
    redirect_titles = load_redirect_stub_titles(tier_1k_path)

    # Build set of core normalized title keys
    core_corpus_path = os.path.join(PROJECT_ROOT, "corpus", "corpus.jsonl")
    with open(core_corpus_path, encoding="utf-8") as f:
        core_lines = f.readlines()
    core_norm_keys = set()
    for line in core_lines:
        article = json.loads(line)
        # Try various title fields
        title = article.get("requested_title") or article.get("norm_key") or ""
        if isinstance(title, str) and title.strip():
            core_norm_keys.add(bp.norm_key(title.strip()))

    # Classify each article
    classification = []
    counts = {"redirect_stub": 0, "confusable_adversarial": 0, "background": 0, "unknown": 0}

    for node in articles:
        title = node.get("requested_title", "N/A")
        cls, reason = classify_article(node, core_norm_keys, redirect_titles)
        classification.append({
            "title": title,
            "class": cls,
            "reason": reason
        })
        counts[cls] += 1

    # Build output
    output = {
        "revision": "scale-tier1-940-r1-classifier-v1",
        "method": {
            "name": "deterministic key-match + keyword heuristic",
            "description": (
                "Each scale article is classified in priority order:\n"
                "1. redirect_stub: wikitext contains #REDIRECT or title in "
                "tier_1k.json redirect_stub_titles list.\n"
                "2. confusable_adversarial: normalized title (via bp.norm_key) matches "
                "a core corpus normalized key, OR title contains keyword from "
                "defined confusable categories (Roman Empire, Nile, WWI/WWII, "
                "big cat species, disambiguation indicators).\n"
                "3. background: fallback — no match detected.\n"
                "4. unknown: fallback (should not occur).\n\n"
                "Heuristic limits honestly:\n"
                "- Surface‑level keyword/substring matching only; does NOT imply "
                "semantic relatedness to core topics.\n"
                "- confusable_adversarial flags retrieval risk, not factual overlap.\n"
                "- Keyword lists are finite and may miss edge cases; new confusable "
                "categories require manual update.\n"
                "- Matching on norm_key catches case/casing variants but may produce "
                "false positives on unrelated titles that normalize identically.\n"
                "- No article should be auto-counted as a false positive merely for "
                "coming from the distractor layer; top confusable retrievals must be "
                "adjudicated (see docs/scale-evaluation-rule.md)."
            )
        },
        "counts": counts,
        "articles": classification
    }

    # Write output
    output_path = os.path.join(scale_dir, "scale_classification.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote classification to {output_path}")
    print(f"Counts: {json.dumps(counts, indent=2)}")
    print(f"Total articles: {sum(counts.values())}")

    # Verify
    assert sum(counts.values()) == len(articles), \
        f"Count mismatch: {sum(counts.values())} != {len(articles)}"
    assert counts["redirect_stub"] == 110, \
        f"Expected 110 redirect_stub, got {counts['redirect_stub']}"

    return output


if __name__ == "__main__":
    main()