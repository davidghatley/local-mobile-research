"""lmr: an offline research assistant over a pinned Wikipedia corpus.

  lmr setup                 download llama.cpp (CPU) + the generator GGUF, build the corpus
  lmr ask "question"        answer from local evidence, with citations
  lmr serve                 local web UI that shows every stage of an answer
  lmr bench                 evidence completion + latency on the public dev split
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import textwrap
import time

from . import fetch, runtime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIM, BOLD, CYAN, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[0m"


def _cmd_setup(args) -> int:
  runtime.setup()
  fetch.ensure_corpus()
  return 0


def _print_answer(a) -> None:
  w = min(100, os.get_terminal_size().columns if sys.stdout.isatty() else 100)
  print(f"\n{BOLD}{textwrap.fill(a.text, w)}{RESET}\n")
  print(f"{DIM}evidence ({a.budget['used']}/{a.budget['cap']} tokens, "
        f"{len(a.packet)} paragraph{'' if len(a.packet) == 1 else 's'}):{RESET}")
  for s in a.packet:
    mark = f"{CYAN}●{RESET}" if s["cited"] else f"{DIM}○{RESET}"
    print(f" {mark} [{s['id']}] {s['title']} — {s['heading']}")
  t = a.timings_ms
  print(f"\n{DIM}bm25 {t['bm25']:.0f} ms · rerank {t.get('rerank', 0):.0f} ms · "
        f"generate {t['generate']:.0f} ms · offline{RESET}")


def _cmd_ask(args) -> int:
  from .pipeline import Assistant
  a = Assistant(rerank_k=args.rerank_k, use_reranker=not args.no_rerank, log=lambda m: None)
  try:
    ans = a.ask(" ".join(args.question))
    if args.json:
      print(json.dumps(ans.to_dict(), indent=2))
    else:
      _print_answer(ans)
  finally:
    a.close()
  return 0


def _cmd_serve(args) -> int:
  from .server import serve
  serve(args.port, rerank_k=args.rerank_k)
  return 0


def _cmd_bench(args) -> int:
  """Required-paragraph completion of the final packet, the research's primary metric."""
  sys.path.insert(0, ROOT)
  from experiments.common.custodian_truth import (atom_to_host_paragraph,
                                                  host_paragraphs_for, load_ground_truth)
  from experiments.common.packer import build_ranked_packet
  from .pipeline import Assistant
  a = Assistant(rerank_k=max(args.k), log=lambda m: None)
  gts = load_ground_truth(ROOT, args.split)
  hosts = atom_to_host_paragraph(a.view)
  rows = []
  try:
    for k in args.k:
      a.rerank_k = k
      a_rr = a.reranker
      if k == 0:
        a.reranker = None
      need = got = 0
      lat = []
      for gt in gts.values():
        req = host_paragraphs_for(gt, hosts)
        if not req:
          continue
        t = time.perf_counter()
        ranked, _, _ = a.retrieve(gt.text)
        lat.append((time.perf_counter() - t) * 1000)
        packet, _ = build_ranked_packet("b", ranked, a.node_text, a.llm.count_tokens,
                                        "q", node_article=a.node_article)
        ids = {s.node_id for s in packet.spans}
        need += len(req)
        got += sum(1 for r in req if r in ids)
      a.reranker = a_rr
      rows.append({"rerank_k": k, "completion": got / need, "found": got, "required": need,
                   "median_retrieval_ms": statistics.median(lat)})
      print(f"k={k:>4}  completion {got}/{need} = {got / need:.4f}  "
            f"median retrieval {statistics.median(lat):.0f} ms", flush=True)
  finally:
    a.close()
  if args.out:
    with open(args.out, "w") as fh:
      json.dump({"split": args.split, "rows": rows, "threads": a.llm.threads}, fh, indent=2)
  return 0


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(prog="lmr", description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  sub = ap.add_subparsers(dest="cmd", required=True)
  sub.add_parser("setup").set_defaults(fn=_cmd_setup)
  p = sub.add_parser("ask")
  p.add_argument("question", nargs="+")
  p.add_argument("--rerank-k", type=int, default=100)
  p.add_argument("--no-rerank", action="store_true")
  p.add_argument("--json", action="store_true")
  p.set_defaults(fn=_cmd_ask)
  p = sub.add_parser("serve")
  p.add_argument("--port", type=int, default=8765)
  p.add_argument("--rerank-k", type=int, default=100)
  p.set_defaults(fn=_cmd_serve)
  p = sub.add_parser("bench")
  p.add_argument("--split", default="dev", choices=["dev", "shadow_dev"])
  p.add_argument("--k", type=int, nargs="+", default=[0, 20, 50, 100, 500])
  p.add_argument("--out")
  p.set_defaults(fn=_cmd_bench)
  args = ap.parse_args(argv)
  return args.fn(args)


if __name__ == "__main__":
  sys.exit(main())
