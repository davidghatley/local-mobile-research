# Phase 4 Semantic Audit — Independent Re-Verification of 11 Repaired Drafts

**Reviewer:** opencode/nemotron-3-ultra-free (independent second reader; did NOT author the repairs)
**Corpus revision:** HEAD 3e82aa2 (pilot-297-r1)
**Date:** 2026-09-30
**Scope:** Exactly 11 files in `staging/` with `decision=pending` and cleared content hashes:
`qa-pilot-dev-03`, `qa-pilot-dev-09`, `qa-train-02`, `qa-train-09`, `qa-train-14`, `qa-train-21`, `qa-train-24`, `qa-train-28`, `qa-train-36`, `qa-train-42`, `qa-train-44`

---

## Method

For each draft I independently:
1. Fetched the ACTUAL corpus text for every support atom and every hard negative from `corpus/corpus.jsonl` by `node_id` — never trusted the draft's stored copy.
2. Verified the repair matches the ledger exactly (relabel, minimality, alternatives).
3. Applied leave-one-out to the remaining sufficient sets to confirm minimality.
4. Checked for new defects: tautology, hard negative containing answer, ancestor/descendant overlap, span text mismatch (NBSP!), cross-split leakage, ambiguous readings breaking distinctness, reading pointing at wrong set index.
5. Confirmed the question remains clear and answerable.

Verdict per file: **APPROVE** or **REPAIR-REQUIRED**, with per-atom leave-one-out results and any defect found.
Content hashes computed via `data_tools.verify.draft_content_hash(json.load(open(file)))`.

---

## 1. qa-pilot-dev-03 — **APPROVE**

**Ledger repair:** relabel-multihop (was multihop → factoid; drop `is_multi_hop`, clear `reference_hop_chains`; single atom suffices).

**Corpus verification:**
- `t:mercury_automobile:00:000:02` = "From 1945 until its closure, it formed half of the Lincoln-Mercury Division of the company." → **MATCHES draft text exactly.**
- `t:mercury_automobile:00:000:01` = "Created by Edsel Ford in 1938, Mercury was established to bridge the gap between the Ford and Lincoln model lines within the Ford Motor Company." (Setup atom — question already states this.)
- Hard negative `t:mercury_mythology:00:000:02` = Roman mythology; no overlap.

**Leave-one-out on repaired set `{t:mercury_automobile:00:000:02}`:**
- Only atom: Q1=N/A (single atom), Q2=supplies final property (Lincoln-Mercury Division). **Minimal ✓**

**No new defects:** `is_multi_hop=false`, no hop chains, question_type=factoid, hard negative reviewed, no tautology, no cross-split leakage (single article a:mercury_automobile, group mercury, split dev).

**Content hash:** `0736661b73dced01cc1aabf1b53fbb0098b375864bba7dad1de29a22293f2088`

---

## 2. qa-pilot-dev-09 — **APPROVE**

**Ledger repair:** repair-alternatives — add `{p:gorilla:08:000}` to reading 0 (gorilla), `{p:chimpanzee:10:000}` to reading 1 (chimpanzee). Draft now has 4 sufficient sets; readings 0 and 1 still point to sets 0 and 1 (original atoms). Alternatives are additional independent sets.

**Corpus verification:**
- Set 0 (reading 0): `{t:gorilla:00:000:04}` = "They tend to live in troops, with the leader being called a silverback." → MATCH.
- Set 1 (reading 1): `{t:chimpanzee:00:000:06, t:chimpanzee:00:000:07}` → both MATCH.
- Set 2 (alt for reading 0): `{p:gorilla:08:000}` = full paragraph on gorilla troops/silverback/harem → **different passage (section 08 vs lead), independently determines gorilla reading** ✓
- Set 3 (alt for reading 1): `{p:chimpanzee:10:000}` = full paragraph on chimpanzee communities/200+ members/male hierarchy → **different passage (section 10 vs lead), independently determines chimpanzee reading** ✓
- Hard negative `t:gorilla:00:000:05` = fur colour; no overlap with evidence.

**Leave-one-out:**
- Set 0: single atom → minimal ✓
- Set 1: remove :06 → loses 200-member fact (Q1=no); remove :07 → loses hierarchy (Q1=no) → both necessary → minimal ✓
- Set 2: single paragraph atom → minimal ✓
- Set 3: single paragraph atom → minimal ✓

**Readings distinct:** Set 0 answers "troops led by a silverback" (gorilla), Set 1 answers "groups of over 200 members with a male-dominated hierarchy" (chimpanzee). Sets 2/3 independently give same answers. No reading points at wrong index.

**No new defects:** ambiguous type preserved, both readings have distinct answers/sets, hard negative reviewed, no cross-split leakage (a:gorilla and a:chimpanzee both group=apes, split=dev).

**Content hash:** `d51ef4698f18162eba97715b18d466ea058f018f9dfc20f6cce5d2c6e7884329`

---

## 3. qa-train-02 — **APPROVE**

**Ledger repair:** repair-alternatives — add `{p:amazon_company:00:000}` as additional sufficient set for reading 0 (company). Reading 0 still points to set 0 (`t:jeff_bezos:00:000:00`). `t:amazon_company:00:000:01` (descendant sentence) correctly NOT added.

**Corpus verification:**
- Set 0 (reading 0): `{t:jeff_bezos:00:000:00}` = "Jeffrey Preston Bezos... founder... of Amazon, the world's largest e-commerce and cloud computing company." → MATCH.
- Set 1 (reading 1): `{t:amazon_rainforest:00:000:00}` = "The Amazon rainforest... moist broadleaf tropical rainforest... South America." → MATCH.
- Set 2 (alt for reading 0): `{p:amazon_company:00:000}` = full article lead paragraph on Amazon.com, Inc., e-commerce, cloud, founded 1994 by Jeff Bezos → **different article/passage from Bezos node, independently determines reading 0** ✓
- Hard negative `p:amazons:08:000` = Hippolyte Amazon queen; no overlap.

**Leave-one-out:**
- Set 0: single atom → minimal ✓
- Set 1: single atom → minimal ✓
- Set 2: single paragraph → minimal ✓

**Readings distinct:** Reading 0 = company (e-commerce/cloud), Reading 1 = rainforest (South America). Set 2 supports reading 0. No reading points at wrong index.

**No new defects:** ambiguous type preserved, hard negative reviewed, no cross-split leakage (a:amazon_company, a:amazon_rainforest, a:jeff_bezos all group=amazon, split=train).

**Content hash:** `05dedcf476fdfe692b4c4ae850929b7f44ced514bad67535c1ddebf8fa03c5e9`

---

## 4. qa-train-09 — **APPROVE**

**Ledger repair:** relabel-multihop (was multihop → factoid; drop `is_multi_hop`, clear hop chains; single atom suffices).

**Corpus verification:**
- `t:columbia_university:00:000:00` = "Columbia University in the City of New York... is a private Ivy League research university in New York City, United States." → MATCH.
- `t:columbia_university:00:000:02` = 1784 rename to Columbia College (setup — question states this).
- `t:columbia_university:00:000:03` = 1896 move to current campus (setup — question states this).
- Hard negative `t:space_shuttle_columbia:00:000:00` = Space Shuttle; no overlap.

**Leave-one-out on repaired set `{t:columbia_university:00:000:00}`:**
- Only atom supplies location "New York City" → Q1=N/A, Q2=supplies answer. **Minimal ✓**

**No new defects:** `is_multi_hop=false`, question_type=factoid, hard negative reviewed, no tautology, no cross-split leakage (a:columbia_university, group=columbia, split=train).

**Content hash:** `b014f37404dae303627d0db41e7c06f7209ae8d644c0d194bb0017d317fbe8da`

---

## 5. qa-train-14 — **APPROVE**

**Ledger repair:** relabel-multihop (was multihop → factoid; single atom suffices).

**Corpus verification:**
- `t:lunar_eclipse:00:000:01` = "Lunar eclipses occur during eclipse season, when the Moon's orbital plane is approximately in line with Earth and the Sun." → MATCH.
- `t:lunar_eclipse:00:000:00` = "A lunar eclipse, also called a blood moon..." (setup — question states "blood moon is a kind of lunar eclipse").
- Hard negative `t:eclipse_software:00:000:00` = Eclipse IDE; no overlap.

**Leave-one-out on repaired set `{t:lunar_eclipse:00:000:01}`:**
- Only atom supplies "eclipse season" → minimal ✓

**No new defects:** `is_multi_hop=false`, question_type=factoid, hard negative reviewed, no cross-split leakage (a:lunar_eclipse, group=eclipse, split=train).

**Content hash:** `3c0db24c9a925467294dc49ab7349cdbc90cdbb82941ccdaf92c7f072928ac8c`

---

## 6. qa-train-21 — **APPROVE**

**Ledger repair:** repair-minimality + relabel-multihop — drop `t:mars_bar:00:000:01` (redundant), keep only `p:mars_bar:01:000`; set `is_multi_hop=false`, question_type=factoid.

**Corpus verification:**
- `p:mars_bar:01:000` = "The Mars bar was first manufactured in Slough, England, in 1932 by Forrest Mars Sr., son of American candy maker Frank C. Mars. He modelled the Mars bar after his father's Milky Way bar..." → **MATCHES draft text exactly.**
- `t:mars_bar:00:000:01` = "It was first manufactured in 1932 in England by Forrest Mars Sr., modelled after his father's Milky Way bar." (Redundant — entailed by paragraph atom.)
- Hard negative `p:mars_inc:09:000` = product list; no overlap.

**Leave-one-out on repaired set `{p:mars_bar:01:000}`:**
- Single paragraph atom supplies BOTH the modelled-after fact AND the father's name/relationship (Frank C. Mars, father) → Q1=N/A, Q2=complete answer. **Minimal ✓**

**No new defects:** `is_multi_hop=false`, no hop chains, question_type=factoid, hard negative reviewed, no tautology, no cross-split leakage (a:mars_bar, group=mars, split=train).

**Content hash:** `09d30d6c8cfe432b4a6e9579da0466771fe05d7f55191a18f556245cc4aa9295`

---

## 7. qa-train-24 — **APPROVE**

**Ledger repair:** relabel-multihop (was multihop → factoid; single atom suffices).

**Corpus verification:**
- `t:aswan_high_dam:00:000:00` = "The Aswan High Dam... was built between 1960 and 1970 across the Nile in Aswan, Egypt." → MATCH.
- `t:aswan_high_dam:00:000:03` = "Like the Aswan Low Dam, which had been completed in 1902, the High Dam has changed the economy and culture of Egypt." (Setup — question states Low Dam 1902.)
- Hard negative `p:giza_pyramid_complex:05:000` = Menkaure pyramid; no overlap.

**Leave-one-out on repaired set `{t:aswan_high_dam:00:000:00}`:**
- Only atom supplies "Egypt" → minimal ✓

**No new defects:** `is_multi_hop=false`, question_type=factoid, hard negative reviewed, no cross-split leakage (a:aswan_high_dam, group=nile, split=train).

**Content hash:** `ec0aab91e45e10996842e4a152d3cb2619f992a96a256343a5b9bbf3f72579b7`

---

## 8. qa-train-28 — **APPROVE**

**Ledger repair:** repair-alternatives — add `{t:k2:03:000:00}` as second sufficient set. **Critical check:** use SENTENCE atom `t:k2:03:000:00`, NOT parent `p:k2:03:000` (whose continuation cites conflicting 8609.02 m expedition figure).

**Corpus verification:**
- Set 0: `{t:k2:00:000:00}` = "K2... at 8611 metres above sea level, is the second-highest mountain on Earth..." → MATCH.
- Set 1 (added alternative): `{t:k2:03:000:00}` = "K2's height given on maps and encyclopaedias is 8611 metres." → **MATCHES draft exactly; different section (03 vs 00), different node_id, independently determines answer** ✓
- Parent `p:k2:03:000` = same first sentence + "In the summer of 2014, a Pakistani-Italian expedition... was organised..." (contains conflicting 8609.02 m figure in continuation) — **correctly NOT used** ✓
- Hard negative `p:mount_everest:07:000` = nearby peaks; no overlap.

**Leave-one-out:**
- Set 0: single atom → minimal ✓
- Set 1: single sentence atom → minimal ✓

**No new defects:** Both sets genuinely alternative (different node_ids, different passages), sentence atom used not conflicting paragraph, question_type=factoid, hard negative reviewed, no cross-split leakage (a:k2, group=peaks, split=train).

**Content hash:** `bb55452056ff867fa53b58a05c752f74d7b5cce48b596d506f0fb29eed8c8d46`

---

## 9. qa-train-36 — **APPROVE**

**Ledger repair:** relabel-multihop (was multihop → factoid; single atom suffices).

**Corpus verification:**
- `p:ancient_rome:17:000` = "The imperial city of Rome was the largest urban centre in the empire, with a population variously estimated from 450,000 to close to one million." → MATCH.
- `p:ancient_rome:08:000` = "In 27 BC and at the age of 36, Octavian was the sole Roman leader... took the name Augustus." (Setup — question states this.)
- Hard negative `t:rome:00:000:03` = modern Rome metro population; no overlap.

**Leave-one-out on repaired set `{p:ancient_rome:17:000}`:**
- Only atom supplies population range "450,000 to close to one million" → minimal ✓

**No new defects:** `is_multi_hop=false`, question_type=factoid, hard negative reviewed, no cross-split leakage (a:ancient_rome, group=rome, split=train).

**Content hash:** `39052169accbe77c07ccf165f9c7bb44362d411c1abb97db352961f104d0c527`

---

## 10. qa-train-42 — **APPROVE**

**Ledger repair:** repair-minimality + relabel-multihop — drop `p:seashell:11:000` (redundant setup), keep only `p:seashell:01:000`; set `is_multi_hop=false`, question_type=factoid.

**Corpus verification:**
- `p:seashell:01:000` = "When the word 'seashells' refers only to the shells of marine mollusks, then studying seashells is part of conchology..." → MATCH.
- `p:seashell:11:000` = "Almost all genera of hermit crabs use or 'wear' empty marine gastropod shells..." (Setup — question states "Hermit crabs wear empty marine gastropod shells" verbatim.)
- Hard negative `p:shell_plc:14:000` = Brunei Shell Petroleum; no overlap.

**Leave-one-out on repaired set `{p:seashell:01:000}`:**
- Single paragraph atom supplies "conchology" → Q1=N/A, Q2=answer. **Minimal ✓**

**No new defects:** `is_multi_hop=false`, no hop chains, question_type=factoid, hard negative reviewed, no tautology (question states hermit crab fact, not "conchology"), no cross-split leakage (a:seashell, group=shell, split=train).

**Content hash:** `34f05a5f1895e5c2229d332f17f7b6dcef51ff7bbd17b101f44c110722c8d008`

---

## 11. qa-train-44 — **APPROVE**

**Ledger repair:** relabel-multihop (was multihop → factoid; single atom suffices — question pre-states telautomaton demo).

**Corpus verification:**
- `p:nikola_tesla:08:000` = "The money Tesla made from licensing his AC patents made him independently wealthy..." → MATCH.
- `p:nikola_tesla:16:000` = "In 1898, Tesla demonstrated a boat that used a coherer-based radio control—which he dubbed 'telautomaton'..." (Setup — question states this.)
- Hard negative `p:tesla_inc:15:000` = Tesla Roadster; no overlap.

**Leave-one-out on repaired set `{p:nikola_tesla:08:000}`:**
- Only atom supplies "AC patents" → minimal ✓

**No new defects:** `is_multi_hop=false`, question_type=factoid, hard negative reviewed, no cross-split leakage (a:nikola_tesla, group=tesla, split=train).

**Content hash:** `5b0d4ceb453edfa2ab48244c45986244c65077ec7720c676e9798af16366710a`

---

## Summary Table

| Draft | Verdict | Repair Type | Content Hash (64 hex) |
|-------|---------|-------------|----------------------|
| qa-pilot-dev-03 | **APPROVE** | relabel-multihop | 0736661b73dced01cc1aabf1b53fbb0098b375864bba7dad1de29a22293f2088 |
| qa-pilot-dev-09 | **APPROVE** | repair-alternatives | d51ef4698f18162eba97715b18d466ea058f018f9dfc20f6cce5d2c6e7884329 |
| qa-train-02 | **APPROVE** | repair-alternatives | 05dedcf476fdfe692b4c4ae850929b7f44ced514bad67535c1ddebf8fa03c5e9 |
| qa-train-09 | **APPROVE** | relabel-multihop | b014f37404dae303627d0db41e7c06f7209ae8d644c0d194bb0017d317fbe8da |
| qa-train-14 | **APPROVE** | relabel-multihop | 3c0db24c9a925467294dc49ab7349cdbc90cdbb82941ccdaf92c7f072928ac8c |
| qa-train-21 | **APPROVE** | repair-minimality + relabel-multihop | 09d30d6c8cfe432b4a6e9579da0466771fe05d7f55191a18f556245cc4aa9295 |
| qa-train-24 | **APPROVE** | relabel-multihop | ec0aab91e45e10996842e4a152d3cb2619f992a96a256343a5b9bbf3f72579b7 |
| qa-train-28 | **APPROVE** | repair-alternatives | bb55452056ff867fa53b58a05c752f74d7b5cce48b596d506f0fb29eed8c8d46 |
| qa-train-36 | **APPROVE** | relabel-multihop | 39052169accbe77c07ccf165f9c7bb44362d411c1abb97db352961f104d0c527 |
| qa-train-42 | **APPROVE** | repair-minimality + relabel-multihop | 34f05a5f1895e5c2229d332f17f7b6dcef51ff7bbd17b101f44c110722c8d008 |
| qa-train-44 | **APPROVE** | relabel-multihop | 5b0d4ceb453edfa2ab48244c45986244c65077ec7720c676e9798af16366710a |

---

## Overall Conclusion

**All 11 repaired drafts APPROVED.** Every repair matches the ledger exactly:

- 6 relabel-multihop repairs correctly reduced to single-atom factoid sets with `is_multi_hop=false` and cleared hop chains.
- 2 minimality repairs correctly removed redundant atoms (verified by leave-one-out on the remaining set).
- 3 alternative-set repairs correctly added genuinely independent sufficient sets with distinct node_ids; for qa-train-28 the sentence atom `t:k2:03:000:00` was used (not the conflicting paragraph `p:k2:03:000`); for qa-train-02 the descendant `t:amazon_company:00:000:01` was correctly NOT added.

No new defects introduced in any draft: no tautologies, no hard negative leakage, no ancestor/descendant overlap, no span text mismatches, no cross-split leakage, no ambiguous reading confusion, no reading pointing at wrong set index.

All questions remain clear and answerable after changes.

Each draft's content hash is recorded above. The approval provenance blocks in each file (author=round0-qa-*-author, verifier=independent-ultra-verifier, decision=pending) are ready for fresh approval binding to these new hashes.

---

*End of re-verification report.*