# Scale Evaluation Rule — Adjudication Procedure

## Purpose

This document defines the adjudication procedure for distinguishing
non-core-but-supporting text from irrelevant distractor text in scale-tier
retrieval results. It ensures that scale articles are not auto-counted as
false positives merely for originating from the distractor layer.

## Adjudication Rule

**A retrieved scale passage must NOT auto-count as a false positive merely for
coming from the distractor layer.**

Instead, the following procedure applies:

1. **Identify the retrieval**: A scale article is returned as a retrieval result
   for a given query.

2. **Check for core annotated evidence**: Examine the core corpus (`corpus/corpus.jsonl`)
   for annotated evidence related to the query. Core annotated evidence is the
   ground truth for all measured claims.

3. **Evaluate the scale passage**:
   - If the scale article's content **supports** or **contradicts** the query
     with verified content from the core corpus, evaluate it as a normal retrieval
     result (true positive or false negative depending on relevance).
   - If the scale article's content is **superficially similar** (e.g., same
     name, different entity; same keyword without substantive overlap) or
     **irrelevant** to the query given core evidence, it is not a false positive
     merely due to its distractor-tier origin. It is simply a non-relevant
     retrieval.

4. **Classify the outcome**:
   - **Supported**: Scale article content is verified as relevant to the query
     via core annotated evidence.
   - **Unsupported**: Scale article content is verified as irrelevant or
     contradictory to the query via core annotated evidence.
   - **Unknown**: Insufficient core evidence to determine relevance; default to
     "not a false positive due to distractor origin."

## Distractor vs Confusable Distinction

- **Background distractor**: Article has no significant overlap with core topics.
  Retrieval of such articles should be ignored in evaluation; they are noise.
- **Confusable adversarial**: Article has surface-level title/keyword overlap
  with core topics. These require adjudication per the rule above — the match
  must be examined on substance, not auto-rejected because of the distractor tag.

## Minimal Hook: eval/scale_adjudication.py

An optional tiny adjudication helper is provided at `eval/scale_adjudication.py`:

```python
# eval/scale_adjudication.py — tiny adjudication hook
def needs_adjudication(article_class, has_core_evidence):
    """Return True if the article requires adjudication against core evidence."""
    # Only confusable adversarial articles need adjudication;
    # redirect_stub and background articles do not.
    return article_class == "confusable_adversarial" and has_core_evidence
```

This hook is minimal and optional — the core principle is the adjudication
rule stated above, not the code hook.

## Relation to docs/scale-method.md

The background-vs-confusable distinction and adjudication rule documented in
Section 1.1 of `docs/scale-method.md` are derived from this evaluation rule.