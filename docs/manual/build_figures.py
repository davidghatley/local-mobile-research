"""Render the data-driven figures in docs/manual/index.html from docs/manual/data/*.json.

Each figure replaces the block between <!-- FIG:name --> and <!-- /FIG:name -->
(or a bare <!-- FIG:name --> marker on first run), so re-running after a new
`lmr bench` or example run updates the book without hand-typed numbers.

  python3 docs/manual/build_figures.py
"""

from __future__ import annotations

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def _load(name):
  path = os.path.join(DATA, name)
  return json.load(open(path)) if os.path.exists(path) else None


def fig_sweep() -> str:
  import math
  splits = [(n, _load(f"bench_{n}.json")) for n in ("dev", "shadow_dev")]
  splits = [(n, d) for n, d in splits if d]
  ks = [r["rerank_k"] for r in splits[0][1]["rows"]]
  cls = {"dev": "k-rerank", "shadow_dev": "k-retrieve"}
  scls = {"dev": "s-rerank", "shadow_dev": "s-retrieve"}
  x0, x1, a0, a1 = 56, 300, 410, 650
  X = {k: x0 + i * (x1 - x0) / (len(ks) - 1) for i, k in enumerate(ks)}
  Xr = {k: a0 + i * (a1 - a0) / (len(ks) - 1) for i, k in enumerate(ks)}
  yc = lambda v: 196 - (v * 100 - 60) / 35 * 166
  yl = lambda ms: 196 - (math.log10(max(ms, 10)) - 1) / 3 * 166
  o = ['<svg viewBox="0 0 700 250" role="img" aria-label="Packet completion and median retrieval time against rerank depth k, for dev and shadow_dev.">']
  o.append(f'<text x="{x0}" y="14" class="tl">Required evidence in the packet</text>')
  for v in (60, 70, 80, 90):
    y = yc(v / 100)
    o.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" class="grid"/><text x="{x0 - 6}" y="{y + 4:.1f}" class="ts" text-anchor="end">{v}%</text>')
  o.append(f'<line x1="{X[100]:.1f}" y1="22" x2="{X[100]:.1f}" y2="200" class="dash"/><text x="{X[100] + 4:.1f}" y="206" class="ts">default</text>')
  for n, d in splits:
    pts = [(X[r["rerank_k"]], yc(r["completion"])) for r in d["rows"]]
    o.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="none" class="{scls[n]}" stroke-width="2"/>')
    dy = -10 if n == "dev" else 18
    for (x, y), r in zip(pts, d["rows"]):
      o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" class="{cls[n]}"/><text x="{x:.1f}" y="{y + dy:.1f}" class="t" text-anchor="middle">{r["found"]}/{r["required"]}</text>')
  for k in ks:
    o.append(f'<text x="{X[k]:.1f}" y="220" class="t" text-anchor="middle">{k if k else "BM25"}</text>')
  o.append(f'<text x="{(x0 + x1) / 2:.0f}" y="240" class="ts" text-anchor="middle">rerank depth k</text>')
  o.append(f'<text x="{a0}" y="14" class="tl">Median retrieval time · log scale</text>')
  for ms, lab in ((10, "10 ms"), (100, "100 ms"), (1000, "1 s"), (10000, "10 s")):
    y = yl(ms)
    o.append(f'<line x1="{a0}" y1="{y:.1f}" x2="{a1}" y2="{y:.1f}" class="grid"/><text x="{a0 - 6}" y="{y + 4:.1f}" class="ts" text-anchor="end">{lab}</text>')
  for n, d in splits:
    pts = [(Xr[r["rerank_k"]], yl(r["median_retrieval_ms"])) for r in d["rows"]]
    o.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="none" class="{scls[n]}" stroke-width="2"/>')
    for (x, y), r in zip(pts, d["rows"]):
      o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="{cls[n]}"/>')
  for r in dict(splits)["dev"]["rows"]:
    v = r["median_retrieval_ms"]
    x, y = Xr[r["rerank_k"]], yl(v)
    lab = f"{v:.0f} ms" if v < 1000 else f"{v / 1000:.1f} s"
    o.append(f'<text x="{x - 8:.1f}" y="{y - 10:.1f}" class="t" text-anchor="middle">{lab}</text>')
  for k in ks:
    o.append(f'<text x="{Xr[k]:.1f}" y="220" class="t" text-anchor="middle">{k if k else "BM25"}</text>')
  o.append(f'<text x="{(a0 + a1) / 2:.0f}" y="240" class="ts" text-anchor="middle">rerank depth k · both splits overlap</text>')
  o.append("</svg>")
  legend = "".join(f'<li style="--dot:var(--c-{"rerank" if n == "dev" else "retrieve"})">{n} · {d["rows"][0]["required"]} required</li>' for n, d in splits)
  return (f'<div class="plate">\n<header><span><b>Fig. 5.2</b> · Completion and latency against rerank depth</span>'
          f'<span>Measured · lmr bench · desktop CPU</span></header>\n'
          f'<ul class="legend" style="margin-bottom:.6rem">{legend}</ul>'
          f'<div class="body solo"><div class="svgwrap">{"".join(o)}</div></div>\n'
          f'<p class="cap">Fig. 5.2 — Most of the gain arrives by k = 20; k = 100 matches the full 500 within one paragraph per split at about a quarter of the time. '
          f'Retrieval only (BM25 + rerank); generation adds about 4 s. Source: <code>docs/manual/data/bench_*.json</code>.</p>\n</div>')


def fig_example() -> str:
  a = _load("example_answer.json")
  if not a:
    return ""
  cap = a["budget"]["cap"]
  W = 760
  seg, x = [], 20
  palette = ["k-retrieve", "k-rerank", "k-pack", "k-generate", "k-corpus", "k-eval"]
  col = {}
  for s in a["packet"]:
    col.setdefault(s["title"], palette[len(col) % len(palette)])
  bar_w = W - 40
  for s in a["packet"]:
    w = s["tokens"] / cap * bar_w
    seg.append(f'<rect x="{x:.1f}" y="40" width="{w - 2:.1f}" height="34" class="{col[s["title"]]}" opacity=".85"/>'
               f'<text x="{x + 6:.1f}" y="61" class="ts" style="fill:var(--paper)">{s["tokens"]}</text>')
    x += w
  rows = []
  y = 110
  for i, c in enumerate(a["candidates"][:8]):
    inp = any(s["id"] == c["id"] for s in a["packet"])
    lab = html.escape(f'{c["title"]} · {c["heading"]}'[:46])
    rows.append(f'<text x="20" y="{y}" class="ts" text-anchor="start">#{c["bm25_rank"] + 1}</text>'
                f'<path d="M64 {y - 4}H120" class="{"ln" if inp else "lm"}"/>'
                f'<text x="128" y="{y}" class="t">{i + 1}. {lab}</text>'
                + (f'<rect x="500" y="{y - 10}" width="12" height="12" class="{col[c["title"]]}"/><text x="518" y="{y}" class="ts">in packet</text>' if inp else ""))
    y += 22
  t = a["timings_ms"]
  svg = (f'<svg viewBox="0 0 {W} {y + 6}" role="img" aria-label="A real answer: the packet budget filled by paragraph, and the top reranked candidates with their BM25 ranks.">'
         f'<text x="20" y="30" class="tl">Packet · {a["budget"]["used"]} of {cap} tokens · {a["budget"]["skipped_per_article_cap"]} skipped by the per-article cap</text>'
         f'<rect x="20" y="40" width="{bar_w}" height="34" class="f-faint"/>' + "".join(seg) +
         f'<text x="20" y="96" class="tl">BM25 rank → reranked order (top 8)</text>' + "".join(rows) + "</svg>")
  answer = html.escape(a["text"])
  return (f'<div class="plate">\n<header><span><b>Fig. 2.2</b> · One real answer, every stage</span>'
          f'<span>lmr ask --json · bm25 {t["bm25"]:.0f} ms · rerank {t.get("rerank", 0):.0f} ms · generate {t["generate"] / 1000:.1f} s</span></header>\n'
          f'<p style="margin:.2rem 0 .8rem"><b>Q.</b> {html.escape(a["question"])}<br><b>A.</b> {answer}</p>'
          f'<div class="body solo"><div class="svgwrap">{svg}</div></div>\n'
          f'<p class="cap">Fig. 2.2 — The web UI draws this live for every question. Source: <code>docs/manual/data/example_answer.json</code>.</p>\n</div>')


def main() -> None:
  path = os.path.join(HERE, "index.html")
  s = open(path, encoding="utf-8").read()
  for name, fn in (("sweep", fig_sweep), ("example", fig_example)):
    block = f"<!-- FIG:{name} -->\n{fn()}\n<!-- /FIG:{name} -->"
    pat = re.compile(rf"<!-- FIG:{name} -->(.*?<!-- /FIG:{name} -->)?", re.S)
    s = pat.sub(lambda m: block, s, count=1)
  open(path, "w", encoding="utf-8").write(s)
  print("figures updated")


if __name__ == "__main__":
  main()
