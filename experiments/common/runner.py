"""Run harness: drive a system over a split and preserve every raw trace.

A "system" here is anything that turns a :class:`substrate.query.QueryInput` into
(a) an ordered list of stage traces and (b) a final ranked paragraph list. That
is deliberately the narrowest useful interface: it lets the lexical baseline, a
cascade, a shared-head model and the oracle condition all be driven by the same
code, so a difference in their numbers cannot be an artefact of the harness.

What the harness guarantees, because these are the things that go missing:

  - the model-facing surface is exactly ``{question_id, text}``, produced by
    ``to_model_query`` and guarded by ``assert_no_label_metadata``;
  - retrieval latency is measured with ``time.perf_counter`` and EXCLUDES the
    tokenizer service and the generator, both of which are accounted separately;
  - peak RSS is sampled, and ``None`` is written when it is not;
  - a failure on one question is RECORDED and the run continues, because
    "do not summarize away failures" is a protocol requirement and a run that
    aborts on the first exception reports nothing about the other questions;
  - the raw traces are written before any metric is computed from them.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Protocol

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from substrate.query import to_model_query  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402


class System(Protocol):
  """The narrow retrieval interface every Round 1 system implements."""

  system_id: str

  def retrieve(
    self, query, tokenizer, tokenizer_id: str
  ) -> tuple[list[dict], list[str], dict]:
    """Return ``(stage_entries, final_ranked_node_ids, pack_report)``.

    ``stage_entries`` are wire stage dicts from ``experiments.common.trace``.
    ``final_ranked_node_ids`` is the system's final total order, already capped
    and policy-filtered -- the packer still applies the shared budget on top, so
    no system can buy quality with extra text.
    """


@dataclass
class RunResult:
  system_id: str
  split: str
  tier: str
  n_questions: int
  n_ok: int
  n_failed: int
  traces: list[dict] = field(default_factory=list)
  failures: list[dict] = field(default_factory=list)
  wall_ms: float = 0.0
  index_stats: dict = field(default_factory=dict)
  model_identity: dict = field(default_factory=dict)

  def summary(self) -> dict:
    return {
      "system_id": self.system_id,
      "split": self.split,
      "tier": self.tier,
      "n_questions": self.n_questions,
      "n_ok": self.n_ok,
      "n_failed": self.n_failed,
      "wall_ms": self.wall_ms,
      "index_stats": self.index_stats,
      "model_identity": self.model_identity,
    }


def run_split(
  *,
  system: System,
  split: str,
  tier: str,
  tokenizer,
  tokenizer_id: str,
  packer_ctx,
  run_id: str,
  seed: int,
  out_dir: str,
  index_stats: dict | None = None,
  model_identity: dict | None = None,
  question_ids: list[str] | None = None,
  limit: int | None = None,
  generator: Any | None = None,
  progress_every: int = 10,
  log: Any | None = None,
) -> RunResult:
  """Drive ``system`` over one split.

  ``packer_ctx`` is an object exposing ``node_text`` and ``node_article`` maps for
  the tier, so packet construction is identical for every system.

  ``generator`` is optional. When present it is called for every item that the
  shared ``decide_default`` gate sends to generation, through the same frozen
  path the tournament mandates; when absent the run is retrieval-only and every
  ``generator_response`` is None (which the trace records as an abstention-free
  no-generation run, and the grader must not read as an empty generation).
  """
  from experiments.common.packer import build_ranked_packet
  from experiments.common.trace import build_trace
  from substrate.evidence import decide_default
  from substrate.generator import PROMPT_HASH

  entries = packer_ctx.entries
  if question_ids is not None:
    entries = [e for e in entries if e["question_id"] in set(question_ids)]
  if limit is not None:
    entries = entries[:limit]

  res = RunResult(
    system_id=system.system_id,
    split=split,
    tier=tier,
    n_questions=len(entries),
    n_ok=0,
    n_failed=0,
    index_stats=index_stats or {},
    model_identity=model_identity or {},
  )
  t_start = time.perf_counter()
  for n, entry in enumerate(entries, 1):
    q = to_model_query(entry)  # the ONLY model-facing conversion
    try:
      t0 = time.perf_counter()
      stage_entries, ranked, pack_report = system.retrieve(q, tokenizer, tokenizer_id)
      retrieval_ms = (time.perf_counter() - t0) * 1000.0

      packet, pack = build_ranked_packet(
        question_id=q.question_id,
        ranked_node_ids=ranked,
        node_text=packer_ctx.node_text,
        tokenizer=tokenizer,
        tokenizer_id=tokenizer_id,
        node_article=packer_ctx.node_article,
        per_article_cap=packer_ctx.per_article_cap,
      )
      decision = decide_default(packet)
      answer_text: str | None = None
      citations: list[str] = []
      audit = None
      gen_ms: float | None = None
      if generator is not None and decision.generation_action == "generate":
        t1 = time.perf_counter()
        gen = generator.generate(entry_for_gen(entry), packet)
        gen_ms = (time.perf_counter() - t1) * 1000.0
        answer_text = gen.answer_text
        citations = list(gen.citations)
        audit = generator.last_citation_audit

      tr = build_trace(
        run_id=run_id,
        architecture=system.system_id,
        seed=seed,
        query=q.to_dict(),
        stages=stage_entries,
        evidence_packet=packet.to_dict(),
        evidence_token_count=int(packet.exact_evidence_tokens or 0),
        evidence_token_method=packet.token_count_method,
        retrieval_latency_ms=retrieval_ms,
        model_loading_latency_ms=None,
        inference_latency_ms=gen_ms,
        peak_rss_mb=peak_rss_mb(),
        storage_bytes=None,
        adaptive_compute_decision=None,
        generator_id=(generator.generator_id if generator is not None else "none-retrieval-only"),
        generator_prompt_hash=PROMPT_HASH,
        generator_response=answer_text,
        citations=citations,
        available_citations=list(packet.citations),
        grader_result=None,
        citation_audit=audit,
        extra={
          "decision": decision.to_dict(),
          "pack_report": pack_report.__dict__ if hasattr(pack_report, "__dict__") else pack_report,
          "pack": pack.__dict__,
          "generator_invoked": bool(generator is not None and decision.generation_action == "generate"),
        },
      )
      res.traces.append(tr)
      res.n_ok += 1
    except Exception as exc:  # noqa: BLE001 -- recorded, never swallowed
      res.n_failed += 1
      res.failures.append({
        "question_id": entry.get("question_id"),
        "error_type": type(exc).__name__,
        "error": str(exc)[:2000],
        "traceback": traceback.format_exc()[-4000:],
      })
    if log is not None and n % progress_every == 0:
      log(f"  [{system.system_id}/{split}] {n}/{len(entries)} ok={res.n_ok} fail={res.n_failed}")
  res.wall_ms = (time.perf_counter() - t_start) * 1000.0

  # Raw traces land on disk BEFORE any metric is computed from them.
  os.makedirs(out_dir, exist_ok=True)
  safe = system.system_id.replace("/", "_")
  traces_path = os.path.join(out_dir, f"traces_{safe}_{split}_{tier}.jsonl")
  with open(traces_path, "w", encoding="utf-8") as fh:
    for t in res.traces:
      fh.write(json.dumps(t, sort_keys=True) + "\n")
  with open(os.path.join(out_dir, f"failures_{safe}_{split}_{tier}.json"), "w",
            encoding="utf-8") as fh:
    json.dump(res.failures, fh, indent=2, sort_keys=True)
  return res


def entry_for_gen(entry: dict):
  """A substrate.types.Question for the generator.

  The generator needs ``question_id``/``text`` only; ``Question`` carries a
  ``split`` field, so it is filled from the STORED entry. That value never
  reaches the model -- the generator adapter passes only the rendered prompt,
  and ``render_prompt`` uses question id and text.
  """
  from substrate.types import Question

  return Question(
    question_id=entry["question_id"],
    text=entry["text"],
    split=entry.get("split", "dev"),
    meta={},
  )


@dataclass
class PackerContext:
  """Node text and node->article maps for one tier, shared by every system.

  ``per_article_cap`` is the shared packing policy knob from
  `experiments/baselines/HYPOTHESIS.md` §2.3, defaulting to the PREREGISTERED
  value of 3. Setting it to 0 disables the cap, which §2.3 explicitly permits as a
  RECORDED ABLATION ("Ablation without the cap is recorded, not substituted").
  It is a parameter here, not a substitution, so a cap-ablated run is labelled
  as such in its trace rather than being mistaken for the baseline.
  """

  node_text: dict[str, str]
  node_article: dict[str, str]
  entries: list[dict]
  per_article_cap: int = 3

  @staticmethod
  def from_view(view, entries: list[dict], per_article_cap: int = 3) -> "PackerContext":
    return PackerContext(
      node_text={p.node_id: p.text for p in view.paragraphs},
      node_article={p.node_id: a for p, a in zip(view.paragraphs, view.parent_article)},
      entries=entries,
      per_article_cap=per_article_cap,
    )
