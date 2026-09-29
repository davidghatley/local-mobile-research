"""QA record schema for controlled train/dev/heldout derivation (Round 0).

No real questions or labels are created by this module. It defines the
draft record shape, validation rules, and file layout used AFTER the
corpus is validated and frozen. All fixtures in tests are SYNTHETIC.

Layout (staging dir, human-authored drafts):
  <staging>/<qid>.json  — one draft record per question (question + evidence
                          + answer together for authoring convenience).

Sealed layout (produced ONLY by the custodian seal step):
  questions.json                — qid/text/split/meta (no answers)
  labels.json                   — qid -> answer/sufficient sets (train/dev)
  heldout_labels.sealed.json    — qid -> answer/sufficient sets (heldout, sealed)

Question types: factoid | multihop | comparison | unanswerable | ambiguous.
Answerability: answerable | unanswerable | ambiguous (in labels, not questions).

CANONICAL RUNTIME INPUT: the retriever under test receives ONLY
``{"question_id", "text"}`` (see ``to_retriever_input``). Source articles,
group, question type, and answerability are evaluator-side provenance used
for the substrate provenance check — never retriever input.

Negative-type vocabulary note: ``token_overlap_nearmiss`` is a stdlib
token-overlap lexical proxy. It is NOT BM25 and must never be described
as such.

Verification status is content-bound: ``provenance.content_hash`` must equal
``draft_content_hash`` (see data_tools.verify); any content change after
approval invalidates the approval. Code checks code-point-exact span
equality only — it never proves an answer correct, sufficient, or truly
unanswerable; those judgments belong to the human author and the
independent verifier named in ``provenance``.
"""

from __future__ import annotations

QUESTION_TYPES = ("factoid", "multihop", "comparison", "unanswerable", "ambiguous")
ANSWERABILITY = ("answerable", "unanswerable", "ambiguous")
NEGATIVE_TYPES = (
  "sibling_paragraph",
  "neighbor_sentence",
  "linked_article",
  "token_overlap_nearmiss",
  "entity_confusion",
  "same_group_distractor",
)
# Miner-emitted negatives are CANDIDATES. A negative counts as evidence-grade
# only with reviewed=True set by a human who confirmed it does not answer
# the question. Lexical mining alone never establishes non-answering status.
NEGATIVE_REVIEW_REQUIRED = True
SPLITS = ("train", "dev", "heldout")
RETRIEVER_INPUT_FIELDS = ("question_id", "text")

REQUIRED_DRAFT_FIELDS = (
  "question_id", "text", "split", "question_type",
  "meta", "evidence", "hard_negatives", "labels", "provenance",
)
REQUIRED_META_FIELDS = ("source_articles", "group")
REQUIRED_EVIDENCE_FIELDS = ("sufficient_sets", "is_multi_hop")
REQUIRED_LABEL_FIELDS = ("answer_text", "answerability")
REQUIRED_READING_FIELDS = ("reading_text", "answer", "sufficient_set")
REQUIRED_PROVENANCE_FIELDS = (
  "author", "author_model", "verifier", "verifier_model",
  "decision", "rationale", "content_hash",
)
PROVENANCE_DECISIONS = ("approve", "reject", "pending")


def validate_draft_record(rec: dict) -> list[str]:
  """Validate one draft record. Errors carry ids/counts, never Q/A text."""
  errors: list[str] = []
  qid = rec.get("question_id", "?") if isinstance(rec, dict) else "?"
  if not isinstance(rec, dict):
    return ["record is not an object"]
  for f in REQUIRED_DRAFT_FIELDS:
    if f not in rec:
      errors.append(f"{qid}: missing draft field {f}")
  if errors:
    return errors
  if not isinstance(rec["question_id"], str) or not rec["question_id"].strip():
    errors.append("record: missing/empty question_id")
  if not isinstance(rec["text"], str) or not rec["text"].strip():
    errors.append(f"{qid}: missing/empty text")
  if rec.get("split") not in SPLITS:
    errors.append(f"{qid}: invalid split {rec.get('split')!r}")
  if rec.get("question_type") not in QUESTION_TYPES:
    errors.append(f"{qid}: invalid question_type {rec.get('question_type')!r}")
  meta = rec.get("meta", {})
  if not isinstance(meta, dict):
    errors.append(f"{qid}: meta must be an object")
    meta = {}
  for f in REQUIRED_META_FIELDS:
    if f not in meta:
      errors.append(f"{qid}: missing meta field {f}")
  srcs = meta.get("source_articles", [])
  if not isinstance(srcs, list) or not srcs or any(
      not isinstance(s, str) or not s.strip() for s in srcs):
    errors.append(f"{qid}: meta.source_articles must be a nonempty string list")
  if not isinstance(meta.get("group"), str) or not meta.get("group", "").strip():
    errors.append(f"{qid}: meta.group must be a nonempty string")
  ev = rec.get("evidence", {})
  if not isinstance(ev, dict):
    errors.append(f"{qid}: evidence must be an object")
    ev = {}
  for f in REQUIRED_EVIDENCE_FIELDS:
    if f not in ev:
      errors.append(f"{qid}: missing evidence field {f}")
  sets = ev.get("sufficient_sets", None)
  qtype = rec.get("question_type")
  lab = rec.get("labels", {})
  if not isinstance(lab, dict):
    errors.append(f"{qid}: labels must be an object")
    lab = {}
  for f in REQUIRED_LABEL_FIELDS:
    if f not in lab:
      errors.append(f"{qid}: missing labels field {f}")
  if lab.get("answerability") not in ANSWERABILITY:
    errors.append(f"{qid}: bad labels.answerability")
  answerability = lab.get("answerability")
  # Type/answerability consistency: unanswerable and ambiguous must agree in
  # both places. A factoid/multihop/comparison draft is always answerable.
  if (qtype == "unanswerable") != (answerability == "unanswerable"):
    errors.append(f"{qid}: question_type/labels.answerability unanswerable mismatch")
  if (qtype == "ambiguous") != (answerability == "ambiguous"):
    errors.append(f"{qid}: question_type/labels.answerability ambiguous mismatch")
  if qtype == "unanswerable" or answerability == "unanswerable":
    if sets not in (None, []):
      errors.append(f"{qid}: unanswerable must have empty sufficient_sets")
    if not isinstance(ev.get("absent_reason", ""), str) or not ev.get(
        "absent_reason", "").strip():
      errors.append(f"{qid}: unanswerable requires evidence.absent_reason")
  else:
    if not isinstance(sets, list) or not sets:
      errors.append(f"{qid}: need >= 1 sufficient set")
    else:
      for i, s in enumerate(sets):
        if not isinstance(s, list) or not s:
          errors.append(f"{qid}: sufficient set {i} must be a nonempty list")
          continue
        for j, span in enumerate(s):
          if not isinstance(span, dict):
            errors.append(f"{qid}: set {i} span {j} not an object")
            continue
          if not isinstance(span.get("node_id"), str) or not span["node_id"]:
            errors.append(f"{qid}: set {i} span {j} missing node_id")
          if not isinstance(span.get("text"), str) or not span["text"].strip():
            errors.append(f"{qid}: set {i} span {j} missing text")
          for edge in ("char_start", "char_end"):
            if edge in span and span[edge] is not None and (
                isinstance(span[edge], bool) or not isinstance(span[edge], int)):
              errors.append(f"{qid}: set {i} span {j} {edge} must be int")
  if not isinstance(ev.get("is_multi_hop"), bool):
    errors.append(f"{qid}: evidence.is_multi_hop must be bool")
  if ev.get("is_multi_hop") and qtype not in ("multihop", "comparison"):
    errors.append(f"{qid}: is_multi_hop=true needs multihop/comparison type")
  if qtype == "multihop" and not ev.get("is_multi_hop"):
    errors.append(f"{qid}: multihop type needs is_multi_hop=true")
  chains = ev.get("reference_hop_chains", [])
  if chains and (not isinstance(chains, list) or not all(
      isinstance(c, list) and c for c in chains)):
    errors.append(f"{qid}: reference_hop_chains must be a list of nonempty lists")
  if ev.get("is_multi_hop") is True and not chains:
    errors.append(f"{qid}: multi-hop needs >= 1 reference_hop_chain")
  negs = rec.get("hard_negatives", [])
  if not isinstance(negs, list) or not negs:
    errors.append(f"{qid}: need >= 1 hard negative")
  else:
    for i, n in enumerate(negs):
      if not isinstance(n, dict):
        errors.append(f"{qid}: hard negative {i} not an object")
        continue
      if not isinstance(n.get("node_id"), str) or not n["node_id"]:
        errors.append(f"{qid}: hard negative {i} missing node_id")
      if n.get("negative_type") not in NEGATIVE_TYPES:
        errors.append(f"{qid}: hard negative {i} bad negative_type")
      # Candidate negatives are staging-only. Evidence-grade negatives carry
      # reviewed=True from a human who confirmed non-answering status.
      if not isinstance(n.get("reviewed"), bool):
        errors.append(f"{qid}: hard negative {i} missing reviewed bool")
  if lab.get("answerability") == "answerable" and (
      not isinstance(lab.get("answer_text"), str) or not lab["answer_text"].strip()):
    errors.append(f"{qid}: answerable needs nonempty labels.answer_text")
  if lab.get("answerability") == "ambiguous":
    readings = lab.get("readings")
    if not isinstance(readings, list) or len(readings) < 2:
      errors.append(f"{qid}: ambiguous needs >= 2 labels.readings")
    else:
      seen_sets: set[int] = set()
      n_sets = len(sets) if isinstance(sets, list) else 0
      for i, r in enumerate(readings):
        if not isinstance(r, dict):
          errors.append(f"{qid}: reading {i} not an object")
          continue
        for f in REQUIRED_READING_FIELDS:
          if f not in r:
            errors.append(f"{qid}: reading {i} missing {f}")
        if not isinstance(r.get("reading_text"), str) or not r.get(
            "reading_text", "").strip():
          errors.append(f"{qid}: reading {i} needs nonempty reading_text")
        if not isinstance(r.get("answer"), str) or not r.get("answer", "").strip():
          errors.append(f"{qid}: reading {i} needs nonempty answer")
        idx = r.get("sufficient_set")
        if isinstance(idx, bool) or not isinstance(idx, int):
          errors.append(f"{qid}: reading {i} sufficient_set must be int")
        elif not 0 <= idx < n_sets:
          errors.append(f"{qid}: reading {i} sufficient_set out of range")
        elif idx in seen_sets:
          errors.append(f"{qid}: reading {i} reuses sufficient set")
        else:
          seen_sets.add(idx)
  # Tautology guard: answer span must not appear verbatim in the question.
  qtext = rec.get("text", "")
  atext = lab.get("answer_text", "")
  if (isinstance(qtext, str) and isinstance(atext, str) and atext.strip()
      and lab.get("answerability") == "answerable"):
    import re
    norm = lambda s: re.sub(r"\s+", " ", s.strip().lower())
    if len(norm(atext)) >= 4 and norm(atext) in norm(qtext):
      errors.append(f"{qid}: question contains answer verbatim (tautological)")
  prov = rec.get("provenance", {})
  if not isinstance(prov, dict):
    errors.append(f"{qid}: provenance must be an object")
    prov = {}
  for f in REQUIRED_PROVENANCE_FIELDS:
    if f not in prov:
      errors.append(f"{qid}: missing provenance field {f}")
  for f in ("author", "author_model", "verifier", "verifier_model"):
    if f in prov and (
        not isinstance(prov[f], str) or not prov[f].strip()):
      errors.append(f"{qid}: provenance.{f} must be a nonempty string")
  if "decision" in prov and prov["decision"] not in PROVENANCE_DECISIONS:
    errors.append(f"{qid}: bad provenance.decision")
  return errors


def draft_to_question_entry(rec: dict) -> dict:
  """Evaluator-private question entry (no answers/labels/evidence spans).

  Retains meta (source articles, group, type) ONLY for the substrate
  provenance check. NEVER pass this entry to a retrieval architecture —
  use to_retriever_input() for runtime input.
  """
  return {
    "question_id": rec["question_id"],
    "text": rec["text"],
    "split": rec["split"],
    "meta": {
      "source_articles": rec["meta"]["source_articles"],
      "group": rec["meta"]["group"],
      "question_type": rec["question_type"],
    },
  }


def to_retriever_input(question_entry: dict) -> dict:
  """CANONICAL runtime input to the retriever: qid + text ONLY.

  Strips every hint (source articles, group, type, split, labels). Any key
  beyond RETRIEVER_INPUT_FIELDS raises — fail closed against hint leakage.
  """
  if set(question_entry) - {"question_id", "text", "split", "meta"}:
    raise ValueError("unexpected question entry field")
  return {
    "question_id": question_entry["question_id"],
    "text": question_entry["text"],
  }


def draft_to_label_entry(rec: dict) -> dict:
  """Label entry (answers + ground truth). NEVER log its contents."""
  return {
    "answer_text": rec["labels"]["answer_text"],
    "answerability": rec["labels"]["answerability"],
    "readings": rec["labels"].get("readings", []),
    "sufficient_sets": rec["evidence"]["sufficient_sets"],
    "is_multi_hop": rec["evidence"]["is_multi_hop"],
    "reference_hop_chains": rec["evidence"].get("reference_hop_chains", []),
    "absent_reason": rec["evidence"].get("absent_reason", ""),
    "hard_negatives": rec["hard_negatives"],
    "provenance": rec["provenance"],
  }
