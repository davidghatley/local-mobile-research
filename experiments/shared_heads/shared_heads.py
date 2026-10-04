"""Family C: shared encoder + multiple heads (zero-shot run).

One shared backbone forward per (query, paragraph) pair, reused by ALL heads.
Backbone: ``cross-encoder/ettin-reranker-17m-v1`` @ pinned revision
``9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6`` (ModernBERT 7L, hidden 256),
CPU, ``torch.set_num_threads(1)``, eval mode, ``torch.inference_mode()``.

Spec: ``experiments/shared_heads/HYPOTHESIS.md``. Zero-shot only: no
adapters, no LoRA, no fine-tuning. Heads implemented here:

  fine        the model's OWN native scoring head (trained, 66,305 params),
              raw logit -- score_kind "logit", NEVER a probability.
  coarse      tertile bucket of the fine order (1 = top tertile), a pure
              readout of the shared forward, 0 params -- score_kind "rank".
  sufficiency fine logit per paragraph word, a pure allocation-density
              readout of the shared forward, 0 params -- score_kind "similarity".

evidence_presence and entailment are DELIBERATELY DEFERRED (HYPOTHESIS §2):
they need trained heads, and there is no training in this run.

The candidate SET is fixed by the shared BM25 stage-0 top-500. Heads reorder
only; no head adds candidates. See HYPOTHESIS §5 for why this bound is
stated plainly rather than tuned around.
"""

from __future__ import annotations

import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import torch  # noqa: E402

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

from experiments.common.bm25 import STAGE0_K, Bm25Index  # noqa: E402
from experiments.common.corpus_view import CorpusView  # noqa: E402
from experiments.common.trace import stage_entry, topk_policy  # noqa: E402
from substrate.telemetry import peak_rss_mb  # noqa: E402

MODEL_ID = "cross-encoder/ettin-reranker-17m-v1"
MODEL_REVISION = "9e4aa35321a6dd1a43ca313f500c4b4f7cfb5cc6"
BACKBONE_SPEC = "backbone=ModernBert-7L-h256-shared"

BACKBONE_IDENTITY = f"{MODEL_ID}:revision={MODEL_REVISION}:{BACKBONE_SPEC}"
FINE_IDENTITY = (
  f"{BACKBONE_IDENTITY}:head=native-Dense256-GELU-LN-Dense1-66305params")
COARSE_IDENTITY = (
  f"{BACKBONE_IDENTITY}:head=coarse-tertile-readout-zero-shot-proxy-0params")
SUFFICIENCY_IDENTITY = (
  f"{BACKBONE_IDENTITY}:head=sufficiency-logit-per-word-readout"
  "-zero-shot-proxy-0params")
BM25_IDENTITY = (
  "bm25-okapi-stdlib:k1=1.2,b=0.75,tokenizer=NFKC-casefold-[a-z0-9]+")

# Backbone sub-batches. Batching is NOT bit-neutral: different padding
# shapes change fp accumulation at the ~1e-6 level (measured 2026-10-04),
# so the batch composition must match the reference path exactly -- which
# is why _shared_forward replicates predict's length sort (see below).
# Recorded, not tuned.
BACKBONE_BATCH = 32

# Backbone modules (sentence-transformers CrossEncoder children '0','1')
# vs native head modules ('2','3','4'). Partition asserted at load.
BACKBONE_MODULES = ("0", "1")
HEAD_MODULES = ("2", "3", "4")

# Packing-head priority, preregistered (HYPOTHESIS §2): the final ranked list
# comes from the highest-priority EMITTED head.
PACK_PRIORITY = ("fine", "sufficiency", "coarse")

HEAD_STAGES = {
  "coarse": ("heads_coarse", "rank", COARSE_IDENTITY),
  "fine": ("heads_fine", "logit", FINE_IDENTITY),
  "sufficiency": ("heads_sufficiency", "similarity", SUFFICIENCY_IDENTITY),
}

VALID_HEADS = ("coarse", "fine", "sufficiency")


def _get_model():
  from sentence_transformers import CrossEncoder
  m = CrossEncoder(MODEL_ID, revision=MODEL_REVISION)
  m.eval()
  return m


def _count_params(model) -> dict:
  """MEASURED resident params, partitioned into shared vs per-head."""
  backbone = 0
  head = 0
  for name, p in model.named_parameters():
    top = name.split(".")[0]
    if top in BACKBONE_MODULES:
      backbone += p.numel()
    elif top in HEAD_MODULES:
      head += p.numel()
    else:
      raise RuntimeError(f"unpartitioned parameter {name!r}: "
                         "weight accounting is incomplete, refusing to guess")
  return {"backbone_params": backbone, "native_head_params": head,
          "total_params": backbone + head}


class SharedHeads:
  """One backbone forward per pair; every head reads the cached output."""

  system_id = "C_shared_heads_17m"

  def __init__(self, view: CorpusView, bm25_index: Bm25Index,
               heads: tuple[str, ...] = ("coarse", "fine", "sufficiency"),
               stage0_k: int = STAGE0_K) -> None:
    unknown = [h for h in heads if h not in VALID_HEADS]
    if unknown:
      raise ValueError(f"unknown heads {unknown!r}; valid: {VALID_HEADS}")
    if not heads:
      raise ValueError("at least one head must be emitted")
    self.view = view
    self.bm25_index = bm25_index
    self.heads = tuple(heads)
    self.stage0_k = stage0_k
    self._model = None
    self._load_ms: float | None = None
    self._weight_accounting: dict | None = None

  def _get_model(self):
    if self._model is None:
      t0 = time.perf_counter()
      self._model = _get_model()
      self._load_ms = (time.perf_counter() - t0) * 1000.0
      self._weight_accounting = _count_params(self._model)
    return self._model

  @property
  def weight_accounting(self) -> dict:
    self._get_model()
    assert self._weight_accounting is not None
    return dict(self._weight_accounting)

  @property
  def load_ms(self) -> float | None:
    self._get_model()
    return self._load_ms

  def _shared_forward(self, model, pairs: list[tuple[str, str]]):
    """ONE backbone forward per pair. Returns (pooled, backbone_ms).

    Batching replicates the single-head reference path
    (``CrossEncoder.predict``) EXACTLY: plain descending-length sort with
    the model's own ``_input_length`` (no interleave -- predict only
    interleaves when ``_can_flatten_inputs()``, which is False for text
    pairs; adding an interleave here was measured to perturb batches and
    inject 5.2e-6 fp noise), sub-batches of BACKBONE_BATCH=32, then unsort
    back to candidate order. Same batches + same padding shapes = same
    floats: the parity probe requires max abs diff 0.0 vs the reference
    path. Length-homogeneous batches also avoid the ~3x padding waste of
    ragged BM25-order batching (measured 2026-10-04: 60.2s ragged vs
    22.3s sorted on the same 500).
    The pooled matrix is the single shared representation every head reads.
    No head may call this twice.
    """
    import numpy as np

    mods = dict(model.named_children())
    backbone0, pool1 = mods["0"], mods["1"]
    order = np.argsort([-model._input_length(p) for p in pairs])
    back = np.argsort(order)
    sorted_pairs = [pairs[i] for i in order]
    pooled_chunks = []
    t0 = time.perf_counter()
    with torch.inference_mode():
      for s in range(0, len(sorted_pairs), BACKBONE_BATCH):
        chunk = sorted_pairs[s:s + BACKBONE_BATCH]
        batch = model.preprocess(inputs=chunk)
        tok = backbone0(batch)
        pooled = pool1(tok)["sentence_embedding"]
        pooled_chunks.append(pooled.clone())
    backbone_ms = (time.perf_counter() - t0) * 1000.0
    pooled_sorted = torch.cat(pooled_chunks, dim=0) if pooled_chunks \
      else torch.empty(0, 256)
    back = torch.as_tensor(np.asarray(back))
    pooled_all = pooled_sorted[back]
    return pooled_all, backbone_ms, pooled_sorted, back

  @staticmethod
  def _fine_sorted_from_pooled(model, pooled_sorted: torch.Tensor):
    """Native head applied per BACKBONE_BATCH block in sorted order.

    The head MUST be applied in the same 32-row blocks as the reference
    path: one (500, 256) matmul accumulates in a different order than
    sixteen (32, 256) matmuls, which is fp-noise (measured 5.2e-6) that
    the parity probe refuses to carry. Same blocks = same floats.
    """
    import numpy as np

    out = []
    mods = dict(model.named_children())
    with torch.inference_mode():
      for s in range(0, pooled_sorted.shape[0], BACKBONE_BATCH):
        blk = pooled_sorted[s:s + BACKBONE_BATCH]
        x = {"sentence_embedding": blk}
        x = mods["2"](x)
        x = mods["3"](x)
        x = mods["4"](x)
        out.append(x["scores"].flatten().cpu().clone())
    return torch.cat(out, dim=0).numpy() if out \
      else np.empty(0, dtype=float)

  @staticmethod
  def _fine_from_pooled(model, pooled: torch.Tensor):
    """Native trained head on the cached pooled vector. Returns logits."""
    mods = dict(model.named_children())
    with torch.inference_mode():
      x = {"sentence_embedding": pooled}
      x = mods["2"](x)
      x = mods["3"](x)
      x = mods["4"](x)
    return x["scores"].flatten().cpu().numpy()

  def retrieve(self, query, tokenizer, tokenizer_id: str):
    model = self._get_model()
    qtext = query.text

    # -- stage 0: shared pinned BM25 -------------------------------------
    t0 = time.perf_counter()
    hits = self.bm25_index.search(qtext, k=self.stage0_k)
    bm25_ms = (time.perf_counter() - t0) * 1000.0
    bm25_ids = [h.node_id for h in hits]
    bm25_scores = [h.score for h in hits]

    stages = [stage_entry(
      stage="bm25",
      candidate_ids=bm25_ids,
      scores=bm25_scores,
      score_kind="similarity",
      model_identity=BM25_IDENTITY,
      threshold_policy=topk_policy(self.stage0_k, "similarity"),
      kept=[True] * len(bm25_ids),
      latency_ms=bm25_ms,
      model_loading_latency_ms=None,
      inference_latency_ms=None,
      peak_rss_mb=peak_rss_mb(),
    )]

    n = len(bm25_ids)
    if n == 0:
      pack_report = {"heads": list(self.heads),
                     "note": "stage-0 returned no candidates; heads idle"}
      return stages, [], pack_report

    # -- ONE shared backbone forward ------------------------------------
    pairs: list[tuple[str, str]] = []
    for nid in bm25_ids:
      p_node = self.view.by_id.get(nid)
      if p_node is None:
        raise ValueError(f"paragraph node {nid} not found in view")
      pairs.append((qtext, p_node.text))
    pooled, backbone_ms, pooled_sorted, back = self._shared_forward(
      model, pairs)

    # -- head readouts (pure functions of the cache; no encoder pass) ---
    t0 = time.perf_counter()
    import numpy as np

    logits_sorted = self._fine_sorted_from_pooled(model, pooled_sorted)
    logits = [float(v) for v in logits_sorted[np.asarray(back)]]
    fine_readout_ms = (time.perf_counter() - t0) * 1000.0
    for v in logits:
      if not math.isfinite(v):
        raise ValueError("non-finite fine logit: refusing to rank on it")

    # fine order: (logit desc, node_id asc utf-8) -- the trained ranking
    fine_order = sorted(range(n),
                        key=lambda i: (-logits[i],
                                       bm25_ids[i].encode("utf-8")))
    fine_rank_of = [0] * n
    for r, i in enumerate(fine_order):
      fine_rank_of[i] = r

    head_data: dict[str, tuple[list[str], list[float], float]] = {}

    t0 = time.perf_counter()
    # coarse: tertile bucket 1/2/3 (1 = top tertile). Zero trained params.
    buckets = [1 + (3 * fine_rank_of[i]) // n for i in range(n)]
    coarse_idx = sorted(range(n),
                        key=lambda i: (buckets[i], -logits[i],
                                       bm25_ids[i].encode("utf-8")))
    coarse_ms = (time.perf_counter() - t0) * 1000.0
    head_data["coarse"] = ([bm25_ids[i] for i in coarse_idx],
                           [float(buckets[i]) for i in coarse_idx],
                           coarse_ms)

    t0 = time.perf_counter()
    head_data["fine"] = ([bm25_ids[i] for i in fine_order],
                         [logits[i] for i in fine_order],
                         fine_readout_ms)

    t0 = time.perf_counter()
    # sufficiency: gain-per-token density. Word count via split() is ONLY a
    # length normalizer for this ranking score -- it is never reported as an
    # evidence token measurement (the governing count is the exact pinned
    # tokenizer in the packer). Zero trained params.
    densities = []
    for i, nid in enumerate(bm25_ids):
      words = len(self.view.by_id[nid].text.split())
      densities.append(logits[i] / max(1, words))
    for v in densities:
      if not math.isfinite(v):
        raise ValueError("non-finite density: refusing to rank on it")
    suff_idx = sorted(range(n),
                      key=lambda i: (-densities[i],
                                     bm25_ids[i].encode("utf-8")))
    suff_ms = (time.perf_counter() - t0) * 1000.0
    head_data["sufficiency"] = ([bm25_ids[i] for i in suff_idx],
                               [densities[i] for i in suff_idx],
                               suff_ms)

    readout_ms = {"fine": fine_readout_ms, "coarse": coarse_ms,
                  "sufficiency": suff_ms}

    # -- emit one stage per requested head; first emitted pays backbone ---
    first = True
    packing_ids: list[str] | None = None
    packing_head = next(h for h in PACK_PRIORITY if h in self.heads)
    for h in ("coarse", "fine", "sufficiency"):
      if h not in self.heads:
        continue
      ids, scores, rms = head_data[h]
      stage_name, kind, identity = HEAD_STAGES[h]
      lat = (backbone_ms + rms) if first else rms
      stages.append(stage_entry(
        stage=stage_name,
        candidate_ids=ids,
        scores=scores,
        score_kind=kind,
        model_identity=identity,
        threshold_policy=topk_policy(50, kind),
        kept=[True] * len(ids),
        latency_ms=lat,
        model_loading_latency_ms=None,
        inference_latency_ms=rms,
        peak_rss_mb=peak_rss_mb(),
      ))
      first = False
    packing_ids = head_data[packing_head][0]

    pack_report = {
      "heads": list(self.heads),
      "packing_head": packing_head,
      "packing_policy": ("final ranked list = packing-head total order; "
                         "shared 1000-token budget applied on top by packer"),
      "shared_backbone_ms": backbone_ms,
      "head_readout_ms": {h: readout_ms[h] for h in self.heads},
      # Head-switch cost: wall time to produce head B's scores given the
      # cached shared representation (pure readout -- this number replaces
      # a weight swap in family D).
      "head_switch_ms": {h: readout_ms[h] for h in self.heads},
      "backbone_batches": (n + BACKBONE_BATCH - 1) // BACKBONE_BATCH,
      "weight_accounting": self.weight_accounting,
      "note": ("ONE backbone forward per pair reused by all heads; "
               "no head triggered an encoder pass"),
    }
    return stages, packing_ids, pack_report
