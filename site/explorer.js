(async function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let D;
  try { D = await (await fetch("data/explorer.json")).json(); }
  catch (e) { $("label").textContent = "Could not load data/explorer.json."; return; }
  const M = D.meta, P = D.paragraphs;
  $("label").innerHTML = "<b>Recorded replay.</b> Scores, token counts and answers were recorded on " + esc(M.machine) + " on " + esc(M.recorded_utc) +
    ". Nothing runs a model in your browser. Only the packing is recomputed live from the stored scores. The recompute matches the real packer in " +
    M.repack_cells_identical + " of " + M.repack_cells_checked + " recorded settings; in the others it differs by a paragraph and the recorded result is shown.";
  const sel = $("q");
  const types = [...new Set(D.questions.map((q) => q.type))];
  types.forEach((t) => {
    const g = document.createElement("optgroup"); g.label = t;
    D.questions.forEach((q, i) => { if (q.type === t) { const o = document.createElement("option"); o.value = i; o.textContent = q.text.length > 90 ? q.text.slice(0, 88) + "…" : q.text; g.appendChild(o); } });
    sel.appendChild(g);
  });
  sel.value = "0";
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  function ranked(q, k) {
    const ids = q.bm25.map((r) => r[0]);
    const head = ids.slice(0, k).sort((a, b) => q.rr[b] - q.rr[a] || cmp(a, b));
    return head.concat(ids.slice(k));
  }
  function repack(order, budget) {
    const per = {}, kept = [], capped = []; let total = 0, stop = null;
    for (const id of order) {
      const a = P[id].a;
      if ((per[a] || 0) >= 3) { capped.push(id); continue; }
      per[a] = (per[a] || 0) + 1;
      const cost = kept.length ? P[id].m : P[id].n;
      if (total + cost > budget) { stop = id; break; }
      kept.push(id); total += cost;
    }
    return { kept, total, stop, capped };
  }
  const colors = ["#2c6fb0", "#b0653a", "#2f7d43", "#7450a3", "#a8731a", "#b0453a", "#2b7a70", "#6b6f77"];
  function render() {
    const q = D.questions[+sel.value], k = +$("k").value, b = +$("b").value;
    $("kv").textContent = k; $("bv").textContent = b;
    const order = ranked(q, k);
    let r = repack(order, b), src = "recomputed in your browser";
    const g = q.grid[k + ":" + b];
    if (g) {
      if (g.join() !== r.kept.join()) {
        r = { kept: g, total: g.reduce((s, id, i) => s + (i ? P[id].m : P[id].n), 0), stop: null, capped: [] };
        src = "exact, from the recorded run";
      } else src = "recomputed; identical to the real packer's recorded output";
    }
    $("packinfo").innerHTML = "<b>" + r.kept.length + "</b> paragraph" + (r.kept.length === 1 ? "" : "s") + ", <b>" + r.total + "</b> / " + b + " tokens <span class=legend>(" + src + ")</span>";
    const arts = [...new Set(r.kept.map((id) => P[id].a))];
    $("bar").innerHTML = r.kept.map((id, i) => {
      const w = ((i ? P[id].m : P[id].n) / b * 100).toFixed(2);
      return '<div title="' + esc(P[id].t + " — " + P[id].h) + '" style="width:' + w + "%;background:" + colors[arts.indexOf(P[id].a) % colors.length] + '"></div>';
    }).join("");
    $("left").textContent = (r.stop ? "Stopped at rank " + (order.indexOf(r.stop) + 1) + ": " + P[r.stop].t + " (" + P[r.stop].n + " tokens) does not fit. " : "") +
      (r.capped.length ? "Skipped for the 3-per-article cap: " + r.capped.length + "." : "");
    const bm = q.bm25.map((x) => x[0]), inPack = new Set(r.kept);
    const row = (id, i, mv) => '<li class="' + (inPack.has(id) ? "in" : "") + '"><span class="mv ' + (mv > 0 ? "up" : mv < 0 ? "dn" : "") + '">' + (i + 1) + (mv ? (mv > 0 ? " ▲" : " ▼") + Math.abs(mv) : "") + '</span><details><summary class="ttl">' + esc(P[id].t) + " — " + esc(P[id].h) + "</summary><p>" + esc(P[id].x) + ' <a href="' + esc(P[id].u) + '">Wikipedia</a></p></details><span class="sc">' + P[id].n + " tok</span></li>";
    $("l1").innerHTML = bm.slice(0, 20).map((id, i) => row(id, i, 0)).join("");
    $("l2").innerHTML = order.slice(0, 20).map((id, i) => row(id, i, bm.indexOf(id) - i)).join("");
    const t = q.timings_ms;
    $("ans").innerHTML = "<p><b>" + esc(q.answer) + "</b></p><p class=legend>Cited paragraphs: " + (q.cited.length ? q.cited.map(esc).join(", ") : "none (a known limitation of the 1.5B model)") +
      ". Recorded at k=" + M.default_k + ", budget " + M.default_budget + " (" + q.recorded_tokens + " tokens, " + q.recorded_pack.length + " paragraphs). Timings: bm25 " + t.bm25 + " ms, rerank " + t.rerank + " ms, generate " + t.generate + " ms.</p>";
  }
  ["q", "k", "b"].forEach((id) => $(id).addEventListener("input", render));
  $("p0").onclick = () => { $("k").value = 0; render(); };
  $("p1").onclick = () => { $("k").value = 100; $("b").value = 1000; render(); };
  render();
})();
