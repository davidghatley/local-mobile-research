"""Shared Round 1 implementation substrate.

Created after the Round 0 freeze (`round0-freeze-r1`) because at least two Round
1 experiments genuinely require each piece. Nothing here is architecture-specific
and nothing here makes a scientific claim.

Design rules, taken from the frozen contracts rather than invented here:

- The frozen `substrate/` and `eval/` packages are READ-ONLY inputs. This package
  imports them and never patches them.
- Retrieval unit is the PARAGRAPH node (`experiments/baselines/HYPOTHESIS.md`
  §2.1). A required sentence "survives" a stage iff its host paragraph is in that
  stage's candidate set.
- One canonical index document string ``D(p)`` per paragraph, so the lexical and
  semantic channels can never diverge (`HYPOTHESIS.md` §3.1, §4.2).
- Every ranked list is a TOTAL order by ``(score_key, node_id)`` with ``node_id``
  compared as a UTF-8 byte string ascending (`HYPOTHESIS.md` §8). Ties are broken
  deterministically, so two implementations cannot disagree.
- ``None`` in telemetry means EXPLICITLY NOT MEASURED. Never 0, never absent.
- Token budgets are enforced on EXACT pinned-generator tokens. Whitespace
  estimates are refused for empirical runs by the frozen `build_packet`; this
  module does not provide a whitespace shortcut.
- Nothing model-facing ever crosses `substrate.query`'s boundary. Workers call
  `to_model_query`, and the guard `assert_no_label_metadata` is exercised here.

Module map:

``corpus_view``   corpus load, hierarchy/ancestry, ``D(p)``, alias+title lookup
``bm25``          the pinned BM25 of HYPOTHESIS.md §3.2-§3.4
``tokenizer``     exact pinned-generator token counts (resident llama-server)
``packer``        ranked paragraph list -> EvidencePacket under the shared policy
``trace``         the wire trace schema of docs/stage-score-semantics-notes.md
``runner``        run a system over a split, preserve raw per-question traces
``oracle``        CUSTODIAN-ONLY oracle evidence packets for the floor probe
"""

from __future__ import annotations

__all__ = [
  "bm25",
  "corpus_view",
  "oracle",
  "packer",
  "runner",
  "tokenizer",
  "trace",
]
