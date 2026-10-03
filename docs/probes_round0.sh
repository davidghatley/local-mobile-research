#!/usr/bin/env bash
# MANDATORY ADVERSARIAL PROBES for the Round 0 freeze.
#
# Run from the repository root with the private eval dir exported:
#   export LMR_PRIVATE_EVAL_DIR=/path/to/local-mobile-research-private-eval
#   ./docs/probes_round0.sh
#
# Every probe runs on a THROWAWAY copy under /tmp/opencode/probes. Nothing
# mutates the real repo, and any durable record a probe creates in the real
# private directory is removed at the end.
#
# Current result: 18 checks across 11 probes, all passing.
#
# Two lessons from debugging this harness, kept because they recur:
#   * Symlink the CONTENTS of a git-ignored directory, never the directory. A
#     .gitignore rule with a trailing slash does not match a symlink standing
#     where a directory belongs, so the copy becomes dirty and the dirty-tree
#     rule correctly refuses to freeze - a probe measuring its own scaffolding.
#   * Copy the real .git into probe copies. A synthetic single-commit repo makes
#     every history-dependent check fail for the wrong reason.
set -u

REPO=/home/davidhatley/Projects/testing/local_mobile_research
PRIV=/home/davidhatley/Projects/testing/local_mobile_research-private-eval
WORK=/tmp/opencode/probes
rm -rf "$WORK"; mkdir -p "$WORK"
PASS=0; FAIL=0
say() { printf '%s\n' "$*"; }
ok()  { PASS=$((PASS+1)); say "  PASS  $*"; }
bad() { FAIL=$((FAIL+1)); say "  FAIL  $*"; }

stub_priv() { mkdir -p "$1"; cp "$PRIV/freeze_census_pin.json" "$1/" 2>/dev/null; cp "$PRIV/seal.sha256" "$1/" 2>/dev/null; }

# A throwaway copy that IS a real git checkout (a durable record binds the exact
# commit) but skips the bulk git-ignored artifacts, so many copies still fit.
# Bulk artifacts are git-ignored, so a symlink keeps the tree CLEAN (which the
# dirty-tree rule requires) while giving a full run the real pinned bytes.
link_bulk() {
  local d="$1" rel base
  # Symlink the CONTENTS, not the directory itself: .gitignore rules like
  # "corpus/raw/" have a trailing slash and therefore do NOT match a symlink
  # standing where a directory belongs. Symlinking the directory makes the tree
  # dirty, and the dirty-tree rule then (correctly) refuses to freeze - a probe
  # measuring its own scaffolding.
  for rel in corpus/corpus.jsonl corpus/scale/distractor.jsonl; do
    if [ -e "$REPO/$rel" ]; then
      mkdir -p "$d/$(dirname "$rel")"
      ln -sfn "$REPO/$rel" "$d/$rel"
    fi
  done
  for rel in corpus/raw corpus/scale/raw generator_runtime/artifacts; do
    if [ -d "$REPO/$rel" ]; then
      mkdir -p "$d/$rel"
      for f in "$REPO/$rel"/*; do
        [ -e "$f" ] || continue
        ln -sfn "$f" "$d/$rel/$(basename "$f")"
      done
    fi
  done
}

fresh() {
  local d="$WORK/$1"; rm -rf "$d"; mkdir -p "$d"
  ( cd "$REPO" && tar --exclude='__pycache__' \
      --exclude='corpus/raw' --exclude='generator_runtime/artifacts' \
      --exclude='corpus/scale/raw' --exclude='corpus/scale/distractor.jsonl' \
      -cf - . ) | ( cd "$d" && tar -xf - )
  if [ "${2:-}" = "bulk" ]; then link_bulk "$d"; fi
  # Carry the REAL .git: a synthetic single-commit repo would make every
  # history-dependent check (the preregistration anchor) fail for the wrong
  # reason, which is how a probe ends up measuring its own scaffolding.
  ( cd "$d" && git -c user.name=t -c user.email=t@x commit -q --allow-empty -m probe ) >/dev/null 2>&1
  echo "$d"
}
no_record() { compgen -G "$1/freeze_manifest*.json" >/dev/null 2>&1 && return 1 || return 0; }

say "=== PROBE 1: --only 8 PASS must leave NO durable freeze record ==="
D=$(fresh p1); P="$WORK/p1priv"; stub_priv "$P"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 --only 8 >/dev/null 2>&1 )
if no_record "$P"; then ok "no durable record after --only 8"; else bad "durable record exists after --only 8"; fi

say "=== PROBE 2: stage 8 OK, stage 9 broken => full run fails => NO record ==="
D=$(fresh p2); P="$WORK/p2priv"; stub_priv "$P"
printf '{"corrupt": true}\n' > "$D/references/pins.json"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 >/dev/null 2>&1 ); rc=$?
if [ "$rc" -ne 0 ] && no_record "$P"; then ok "broken stage 9 => failed (exit $rc), no durable record"; else bad "broken stage 9: exit=$rc"; fi

say "=== PROBE 3: stage 8 OK, stage 10 broken => full run fails => NO record ==="
D=$(fresh p3); P="$WORK/p3priv"; stub_priv "$P"
printf '{"seal_sha256": "%064d"}\n' 0 > "$P/seal.sha256"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 >/dev/null 2>&1 ); rc=$?
if [ "$rc" -ne 0 ] && no_record "$P"; then ok "broken seal => failed (exit $rc), no durable record"; else bad "broken seal: exit=$rc"; fi

say "=== PROBE 4: co-edit census+data, external trust root untouched => FAIL, NO record ==="
D=$(fresh p4); P="$WORK/p4priv"; stub_priv "$P"
python3 - "$D" <<'PY'
import json, os, glob, sys
d = sys.argv[1]; keep = set()
for i, f in enumerate(sorted(glob.glob(os.path.join(d, "staging", "qa-*.json")))):
    if i >= 100: os.remove(f)
    else: keep.add(json.load(open(f))["question_id"])
p = os.path.join(d, "corpus", "questions.json"); ent = json.load(open(p))
json.dump([e for e in ent if e["question_id"] in keep], open(p, "w"), indent=2, sort_keys=True)
c = json.load(open(os.path.join(d, "corpus", "partition_census.json"))); bs = {}
for e in ent:
    if e["question_id"] in keep: bs[e["split"]] = bs.get(e["split"], 0) + 1
c["expected"] = {"total": len(keep), "by_split": bs}
c["approved_drafts"] = {"total": len(keep), "by_split": bs}
c["authored_total"] = len(keep) + 3
json.dump(c, open(os.path.join(d, "corpus", "partition_census.json"), "w"), indent=2, sort_keys=True)
PY
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 >/dev/null 2>&1 ); rc=$?
if [ "$rc" -ne 0 ] && no_record "$P"; then ok "co-edit caught by the out-of-repo trust root (exit $rc)"; else bad "co-edit: exit=$rc"; fi

say "=== PROBE 5: pre-existing valid record survives a FAILING run byte-identical ==="
D=$(fresh p5 bulk); P="$PRIV"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 >"$WORK/p5.log" 2>&1 ); rc1=$?
grep -E "FAIL|SKIP |DIRTY|gap:" "$WORK/p5.log" | head -6
REC=$(compgen -G "$PRIV/freeze_manifest_*.json" 2>/dev/null | head -1)
if [ -z "$REC" ]; then bad "no baseline durable record to protect (run1 exit=$rc1)"
else
  before=$(sha256sum "$REC" | cut -d' ' -f1)
  printf '{"corrupt": true}\n' > "$D/references/pins.json"
  ( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 >/dev/null 2>&1 ); rc2=$?
  after=$(sha256sum "$REC" | cut -d' ' -f1)
  if [ "$rc2" -ne 0 ] && [ "$before" = "$after" ]; then ok "failing run (exit $rc2) left the old record byte-identical"
  else bad "run2 exit=$rc2 identical=$([ "$before" = "$after" ] && echo yes || echo no)"; fi
fi

say "=== PROBE 6: successful FULL run => exactly one correct durable record ==="
D=$(fresh p6 bulk); P="$PRIV"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 >"$WORK/p6.log" 2>&1 ); rc=$?
[ "$rc" -ne 0 ] && grep -E "FAIL|SKIP |DIRTY|gap:" "$WORK/p6.log" | head -6
if [ "$rc" -eq 0 ]; then
  SHA=$( cd "$D" && git rev-parse HEAD )
  python3 - "$PRIV" "$D" "$SHA" <<'PY'
import json, glob, hashlib, os, sys
priv, repo, sha = sys.argv[1], sys.argv[2], sys.argv[3]
mine = []
for p in sorted(glob.glob(os.path.join(priv, "freeze_manifest_*.json"))):
    try:
        if json.load(open(p)).get("commit_sha") == sha: mine.append(p)
    except Exception: pass
if not mine:
    print("  FAIL  no durable record binds this probe's commit"); sys.exit(1)
d = json.load(open(mine[0]))
ver = hashlib.sha256(open(os.path.join(repo, "scripts", "verify_round0"), "rb").read()).hexdigest()
checks = [
  ("commit_sha matches verified HEAD", d.get("commit_sha") == sha),
  ("verifier hash matches the script", d.get("verifier_sha256") == ver),
  ("mode is full", d.get("verifier_mode") == "full"),
  ("tree recorded clean", d.get("working_tree_dirty") is False),
  ("census digest present", len(d.get("partition_census_sha256","")) == 64),
  ("private seal digest present", len(d.get("sealed_labels_sha256","")) == 64),
  ("all ten stage results PASS", len(d.get("stage_results",[]))==10 and all(r["verdict"]=="PASS" for r in d["stage_results"])),
  ("regime A groups recorded", bool(d.get("regime_a_heldout_groups"))),
  ("regime B groups recorded", bool(d.get("regime_b_document_heldout_groups"))),
  ("verification timestamp recorded", bool(d.get("verified_at_utc"))),
]
for n, g in checks: print(("  PASS  " if g else "  FAIL  ") + n)
sys.exit(0 if all(g for _,g in checks) else 1)
PY
  [ $? -eq 0 ] && ok "durable record correct and complete" || bad "durable record content wrong"
else bad "full run exit=$rc"; fi

say "=== PROBE 7: review-v6 N-1/N-2 - stripped pin digest, dirty tree ==="
D=$(fresh p7); P="$WORK/p7priv"; stub_priv "$P"
python3 -c "import json,sys; json.dump({'note':'stripped'}, open(sys.argv[1],'w'))" "$P/freeze_census_pin.json"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 --only 8 >"$WORK/p7a.log" 2>&1 )
grep -q 'STAGE 8 freeze-manifest: PASS' "$WORK/p7a.log" && bad "stripped pin digest still PASSED" || ok "stripped pin digest FAILS"
grep -q 'nothing to MATCH' "$WORK/p7a.log" && ok "it states the comparison never happened" || bad "no explicit nothing-to-MATCH"
rm -rf "$P"; stub_priv "$P"
printf '\n# dirty\n' >> "$D/substrate/manifest.py"
( cd "$D" && LMR_PRIVATE_EVAL_DIR="$P" ./scripts/verify_round0 --only 8 >"$WORK/p7b.log" 2>&1 )
grep -q 'DIRTY' "$WORK/p7b.log" && ok "dirty tree detected" || bad "dirty tree not detected"
grep -q 'STAGE 8 freeze-manifest: PASS' "$WORK/p7b.log" && bad "dirty tree still PASSED" || ok "dirty tree FAILS"

say "=== PROBE 8: CI-style clean checkout, no private dir, no bulk artifacts ==="
D=$(fresh p8)
( cd "$D" && env -u LMR_PRIVATE_EVAL_DIR ./scripts/verify_round0 --code-only >"$WORK/p8.log" 2>&1 ); rc=$?
[ "$rc" -eq 0 ] && ok "code-only passes in a CI-style checkout (exit 0)" || { bad "code-only failed (exit $rc)"; tail -5 "$WORK/p8.log"; }
grep -q 'THIS IS NOT A FREEZE PASS' "$WORK/p8.log" && ok "CI log disclaims a freeze pass" || bad "no not-a-freeze-pass banner"
grep -q 'RESULT: all load-bearing stages PASS' "$WORK/p8.log" && bad "CI claimed a freeze pass" || ok "CI did not claim a freeze pass"
grep -q 'STAGE 10' "$WORK/p8.log" && bad "stage 10 ran in code-only" || ok "stage 10 excluded from code-only"

say "=== PROBE 9: leakage gate, one-shot enforcement, information boundary ==="
python3 - "$REPO" <<'PY'
import json, os, sys, tempfile, hashlib, itertools
repo = sys.argv[1]; sys.path.insert(0, repo)
priv = tempfile.mkdtemp()
q = [{"question_id":"qa-private-001","text":"Which river flows through Cairo?","labels":{"answer_text":"the Nile"}}]
def canon(o): return json.dumps(o,sort_keys=True,separators=(",",":")).encode()
open(f"{priv}/questions.json","wb").write(canon(q))
open(f"{priv}/labels.json","wb").write(canon({"qa-private-001":{"answer_text":"the Nile"}}))
open(f"{priv}/counts.json","w").write(json.dumps({"counts":{"total":1}}))
open(f"{priv}/seal.sha256","w").write(hashlib.sha256(open(f"{priv}/questions.json","rb").read()).hexdigest())
os.environ["LMR_PRIVATE_EVAL_DIR"] = priv
for m in list(sys.modules):
    if m.startswith("substrate"): del sys.modules[m]
from substrate import private_eval as pe
sess = itertools.count(1)
cases = [
  ("exact duplicate",       [{"synthetic_id":"s1","text":"Which river flows through Cairo?"}], "REJECT"),
  ("normalisation variant", [{"synthetic_id":"s2","text":"which  river flows through   cairo"}], "REJECT"),
  ("near duplicate",        [{"synthetic_id":"s3","text":"Which river flows through the city of Cairo?"}], "REJECT"),
  ("unrelated",             [{"synthetic_id":"s4","text":"How many legs does a spider have?"}], "PASS"),
  ("mixed batch",           [{"synthetic_id":"s5","text":"What is the boiling point of lead at sea level?"},
                              {"synthetic_id":"s6","text":"Which river flows through Cairo?"},
                              {"synthetic_id":"s7","text":"Who wrote the Odyssey?"}], "REJECT"),
]
bad = 0
for name, recs, expect in cases:
    v = pe.check_training_overlap(recs, session="p-%d" % next(sess)).to_dict()
    m = "PASS" if v["verdict"] == expect else "FAIL"
    if v["verdict"] != expect: bad += 1
    print(f"  {m}  {name}: {v['verdict']} flagged={v['flagged_ids']}")
blob = json.dumps(pe.check_training_overlap([{"synthetic_id":"s6","text":"Which river flows through Cairo?"}], session="p-blob").to_dict())
leak = [s for s in ("Cairo","Nile","qa-private-001") if s in blob]
print(("  FAIL  " if leak else "  PASS  ") + f"no private content in result (found {leak})")
if leak: bad += 1
pe.check_training_overlap([{"synthetic_id":"x","text":"zzz"}], session="p-one")
again = pe.check_training_overlap([{"synthetic_id":"x","text":"zzz"}], session="p-one").to_dict()
m = "PASS" if again["verdict"]=="REJECT" and "one-shot" in again["reason"] else "FAIL"
print(f"  {m}  one-shot: second call in a session is refused")
if m == "FAIL": bad += 1
nos = pe.check_training_overlap([{"synthetic_id":"x","text":"zzz"}]).to_dict()
m = "PASS" if nos["verdict"]=="REJECT" else "FAIL"
print(f"  {m}  a call with no session id is refused")
if m == "FAIL": bad += 1
sys.exit(1 if bad else 0)
PY
[ $? -eq 0 ] && ok "leakage gate verdict + one-shot + information boundary" || bad "leakage gate wrong"

say "=== PROBE 10: fake architecture sees no label metadata ==="
python3 - "$REPO" <<'PY'
import json, sys, dataclasses
repo = sys.argv[1]; sys.path.insert(0, repo)
from substrate.query import to_model_query
entry = json.load(open(repo + "/corpus/questions.json"))[0]
entry = dict(entry)
entry.update({"question_type":"unanswerable","split":"shadow_dev",
              "meta":{"group":"leak","source_articles":["Some Article"]},
              "labels":{"answerability":"unanswerable","answer_text":"SECRET"},
              "evidence":{"sufficient_sets":[["p:x"]]}})
seen = {}
def fake(q): seen["q"] = q
fake(to_model_query(entry))
surface = sorted(f.name for f in dataclasses.fields(type(seen["q"])))
blob = json.dumps(dataclasses.asdict(seen["q"]))
forbidden = ["question_type","answerability","split","group","source_articles",
             "evidence","answer_text","sufficient_sets","labels","hard_negatives"]
bad = [f for f in forbidden if f in surface or f in blob]
good = surface == sorted(["question_id","text"])
print(("  PASS  " if good else "  FAIL  ") + f"model surface is exactly {surface}")
print(("  FAIL  " if bad else "  PASS  ") + f"no forbidden field reachable (found {bad})")
sys.exit(0 if good and not bad else 1)
PY
[ $? -eq 0 ] && ok "model-facing query contract clean" || bad "model-facing leak"

say "=== PROBE 11: Regime-B worker exclusion list resists a symlink decoy ==="
mkdir -p "$WORK/p11"
( cd "$REPO" && tar --exclude='__pycache__' -cf - substrate corpus ) | ( cd "$WORK/p11" && tar -xf - )
printf '{"articles":["DECOY"],"scope":"adaptation-only, query-time corpus unchanged","split_map_sha256":"x"}' > "$WORK/decoy.json"
rm -f "$WORK/p11/corpus/regime_b_excluded_articles.json"
ln -s "$WORK/decoy.json" "$WORK/p11/corpus/regime_b_excluded_articles.json"
( cd "$WORK/p11" && python3 -c "
import sys; sys.path.insert(0,'.')
from substrate.query import worker_regime_b_exclusions as w
try:
    w(); print('  FAIL  symlink decoy accepted'); sys.exit(1)
except ValueError as e: print('  PASS  symlink decoy refused:', str(e)[:55]); sys.exit(0)
" ) && ok "symlink decoy refused" || bad "symlink decoy accepted"

say "=== cleanup ==="
rm -f "$PRIV"/freeze_manifest_*.json "$PRIV"/freeze_manifest.json
no_record "$PRIV" && ok "real private dir left with no durable record" || bad "probe left a record in the real private dir"
rm -rf "$WORK"
say ""
say "================================================"
say " PROBES: $PASS passed, $FAIL failed"
say "================================================"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)