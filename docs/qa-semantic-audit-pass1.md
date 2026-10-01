# QA Semantic Audit — Pass 1 of 4

**Scope:** 17 drafts in staging/ with question_type in {multihop, comparison}, plus explicit audit of qa-train-42 and qa-pilot-dev-05.
**Reviewer:** opencode/nemotron-3-ultra-free (independent second reader)
**Corpus revision:** pilot-297-r1 (HEAD 3e82aa2)
**Date:** 2026-09-30

---

## Summary Counts (primary decision per draft)

| Decision | Count |
|----------|-------|
| approve | 9 |
| repair-minimality | 2 |
| repair-alternatives | 0 |
| relabel-multihop | 6 |
| reject-replace | 0 |

Note: Some drafts require both repair-minimality AND relabel-multihop (qa-train-21, qa-train-42); the primary decision is listed above. The detailed per-draft findings are authoritative.

---

## Per-Draft Audit

### 1. qa-pilot-dev-03 (multihop) — **relabel-multihop**

**Sufficient set 0:** {t:mercury_automobile:00:000:01, t:mercury_automobile:00:000:02}

**Q1/Q2 per atom:**
- t:mercury_automobile:00:000:01: Q1=yes (atom 2 alone answers "Lincoln-Mercury Division"); Q2=setup (names the brand and its 1938 purpose, but question already states "automobile brand created in 1938 to bridge the gap")
- t:mercury_automobile:00:000:02: Q1=no; Q2=supplies the final property (the division name)

**Genuine multi-hop:** NO. Atom 2 alone determines the answer. The question already identifies the brand by its 1938 creation purpose; atom 1 is setup/background the question gives.

**Decision:** relabel-multihop — drop is_multi_hop=true and the hop chain; this is a factoid (single-atom answerable).

---

### 2. qa-pilot-dev-05 (comparison) — **approve** (with same-split cross-group note)

**Sufficient set 0:** {t:borneo:00:000:00, t:java:00:000:02}

**Q1/Q2 per atom:**
- t:borneo:00:000:00: Q1=no (without it, cannot identify "the third-largest island"); Q2=supplies the first comparison entity (Borneo as third-largest)
- t:java:00:000:02: Q1=no (without it, cannot identify the 159.2M population or the 56% Indonesian stat); Q2=supplies the second entity + the target property (population)

**Genuine multi-hop:** N/A (comparison type, is_multi_hop=false). Requires two distinct entities; neither atom alone suffices.

**Same-split cross-group check:** meta.group=java, source_articles=[a:borneo, a:java]. Both borneo and java articles have split_group="java" (corpus lines 41 and 417), so they resolve to the same split group. The new same-split rule permits this cross-group chain. VALID.

**Decision:** approve.

---

### 3. qa-train-03 (comparison) — **approve**

**Sufficient set 0:** {p:amazon_rainforest:03:000} (single atom)

**Q1/Q2:**
- p:amazon_rainforest:03:000: Q1=N/A (only atom); Q2=supplies both comparison figures (58.4% Brazil, 12.8% Peru) in one passage

**Genuine multi-hop:** N/A (comparison, is_multi_hop=false). Single atom carries both compared values.

**Decision:** approve.

---

### 4. qa-train-05 (multihop) — **approve**

**Sufficient set 0:** {p:steve_jobs:09:000, p:steve_jobs:12:000}

**Q1/Q2 per atom:**
- p:steve_jobs:09:000: Q1=no (without it, no link from "1986 Pixar spinout" to Jobs); Q2=supplies the bridge entity (Jobs as Pixar spinout funder)
- p:steve_jobs:12:000: Q1=no (without it, no link from Jobs to Apple Computer co-founding); Q2=supplies the final property (co-founded Apple Computer in 1976)

**Genuine multi-hop:** YES. Two-hop chain: entity discovery (who funded Pixar spinout → Jobs) → property lookup (what did Jobs co-found a decade earlier → Apple Computer). Neither atom alone answers.

**Decision:** approve.

---

### 5. qa-train-09 (multihop) — **repair-minimality**

**Sufficient set 0:** {t:columbia_university:00:000:02, t:columbia_university:00:000:03, t:columbia_university:00:000:00}

**Q1/Q2 per atom:**
- t:columbia_university:00:000:02: Q1=no; Q2=supplies the 1784 rename event (bridge to "institution renamed Columbia College in 1784")
- t:columbia_university:00:000:03: Q1=no; Q2=supplies the 1896 move/rename event (bridge to "moved to its current campus in 1896")
- t:columbia_university:00:000:00: Q1=no; Q2=supplies the final property (location: New York City)

**Genuine multi-hop:** YES. Three-hop chain: event 1 → event 2 → location. All three necessary.

**Minimality issue:** Atoms 02 and 03 are from the same article and could be merged into a single paragraph span (they are adjacent sentences in the corpus). However, the protocol requires atomicity at the sentence/paragraph level; keeping them separate is acceptable. NO REDUNDANCY.

**Wait — re-examining:** The question asks: "The institution renamed Columbia College in 1784 moved to its current campus in 1896; in which city is that campus located?" Atom 00 ("Columbia University... in New York City") alone answers the location. Atoms 02 and 03 are setup that the question already states ("renamed Columbia College in 1784", "moved to current campus in 1896"). Q1 for atom 00: if we remove atoms 02 and 03, atom 00 alone still answers "New York City". But the sufficient set includes all three. The leave-one-out test: remove atom 00 → cannot answer. Remove atom 02 → can still answer from 03+00? Actually 03 says "renamed Columbia University" but doesn't state location; 00 states location. The question already gives the 1784 and 1896 facts. So atoms 02 and 03 are SETUP (background the question already gives).

**Revised Q2:**
- t:columbia_university:00:000:02: Q2=setup (question already states "renamed Columbia College in 1784")
- t:columbia_university:00:000:03: Q2=setup (question already states "moved to its current campus in 1896")
- t:columbia_university:00:000:00: Q2=supplies the final property (New York City)

**Genuine multi-hop:** NO — the question already supplies the bridging events. Only atom 00 is necessary. This should be relabel-multihop (single-atom answerable).

**Decision:** relabel-multihop — the multi-hop label is not genuine; the question pre-states the chain premises. Only t:columbia_university:00:000:00 is needed.

---

### 6. qa-train-12 (comparison) — **approve**

**Sufficient set 0:** {p:river_delta:15:000} (single atom)

**Q1/Q2:**
- p:river_delta:15:000: Q1=N/A; Q2=supplies both the "world's largest delta" (Ganges-Brahmaputra) and the "largest delta emptying into fresh water → Lake Baikal" in one passage

**Decision:** approve.

---

### 7. qa-train-14 (multihop) — **relabel-multihop**

**Sufficient set 0:** {t:lunar_eclipse:00:000:00, t:lunar_eclipse:00:000:01}

**Q1/Q2 per atom:**
- t:lunar_eclipse:00:000:00: Q1=yes (atom 1 alone answers "eclipse season"); Q2=setup (defines blood moon = lunar eclipse, but question already states "blood moon is a kind of lunar eclipse")
- t:lunar_eclipse:00:000:01: Q1=no; Q2=supplies the final property (lunar eclipses occur during eclipse season)

**Genuine multi-hop:** NO. Atom 1 alone determines the answer. Atom 0 is setup the question already gives.

**Decision:** relabel-multihop — drop is_multi_hop=true; this is a factoid.

---

### 8. qa-train-18 (comparison) — **approve**

**Sufficient set 0:** {t:tower_of_london:00:000:02, t:london_bridge:00:000:04}

**Q1/Q2 per atom:**
- t:tower_of_london:00:000:02: Q1=no; Q2=supplies first entity date (1066 founding)
- t:london_bridge:00:000:04: Q1=no; Q2=supplies second entity date (Roman timber bridge AD 50) + enables the comparison inference

**Decision:** approve. Genuine comparison requiring two distinct passages from different articles.

---

### 9. qa-train-21 (multihop) — **repair-minimality**

**Sufficient set 0:** {t:mars_bar:00:000:01, p:mars_bar:01:000}

**Q1/Q2 per atom:**
- t:mars_bar:00:000:01: Q1=yes (this atom alone states "modelled after his father's Milky Way bar"); Q2=supplies the bridge (Forrest Mars Sr. modelled Mars bar after father's Milky Way) — but the question already states "Forrest Mars Sr. first manufactured the Mars bar in 1932"
- p:mars_bar:01:000: Q1=no (this atom alone answers: "son of American candy maker Frank C. Mars... modelled the Mars bar after his father's Milky Way bar"); Q2=supplies the relationship (father) and name (Frank C. Mars)

**Genuine multi-hop:** NO. Atom t:mars_bar:00:000:01 alone gives "modelled after his father's Milky Way bar" — but doesn't give the father's name. Atom p:mars_bar:01:000 alone gives BOTH the modelling fact AND the father's name/relationship. The question asks: "after whose candy bar did he model it, and what was that person's relationship to him?" Atom p:mars_bar:01:000 alone answers completely: "his father Frank C. Mars's Milky Way bar".

**Minimality violation:** t:mars_bar:00:000:01 is redundant (entailed by p:mars_bar:01:000). The sufficient set is non-minimal.

**Decision:** repair-minimality — drop t:mars_bar:00:000:01; keep only p:mars_bar:01:000. Also relabel-multihop (single atom suffices).

---

### 10. qa-train-24 (multihop) — **relabel-multihop**

**Sufficient set 0:** {t:aswan_high_dam:00:000:03, t:aswan_high_dam:00:000:00}

**Q1/Q2 per atom:**
- t:aswan_high_dam:00:000:03: Q1=yes (atom 00 alone states "across the Nile in Aswan, Egypt"); Q2=setup (mentions Low Dam 1902, but question already states this)
- t:aswan_high_dam:00:000:00: Q1=no; Q2=supplies the final property (Egypt)

**Genuine multi-hop:** NO. Atom 00 alone determines the answer (location Egypt). Atom 03 is setup the question already gives.

**Decision:** relabel-multihop.

---

### 11. qa-train-27 (comparison) — **approve**

**Sufficient set 0:** {p:eiffel_tower:09:000, p:eiffel_tower:10:000}

**Q1/Q2 per atom:**
- p:eiffel_tower:09:000: Q1=no (without it, cannot verify "first floor hosts Le 58 Tour Eiffel" though question states it); Q2=confirms the premise (Le 58 on first floor) — setup the question gives
- p:eiffel_tower:10:000: Q1=no; Q2=supplies the target property (Le Jules Verne on second floor, Michelin-starred)

**Wait — re-examining:** The question states "The first floor of the tower hosts Le 58 Tour Eiffel" as a premise. Atom 09 confirms this but is not strictly necessary. Atom 10 alone answers "Le Jules Verne". However, this is a comparison question (implicit comparison of restaurants across floors), and both atoms are from the same article. The comparison structure is valid.

**Q2 revised:**
- p:eiffel_tower:09:000: Q2=setup (premise the question already states)
- p:eiffel_tower:10:000: Q2=supplies the answer (Le Jules Verne)

**Minimality:** Atom 09 is setup. But the sufficient set includes both. This is a comparison-type question where the premise entity is given in the question; only the target entity needs evidence. However, the protocol doesn't forbid including setup atoms in sufficient sets for comparison — it's not multihop. The set is sufficient but not minimal. But comparison questions don't have the minimality requirement in the same way (they're not multihop). The protocol says: for each sufficient set and each atom, do Q1/Q2. If an atom is setup, that's noted.

**Decision:** approve (comparison type; setup atom noted but not a minimality violation per protocol — comparison sets can include premise-confirming atoms).

---

### 12. qa-train-32 (multihop) — **approve**

**Sufficient set 0:** {t:guido_van_rossum:00:000:01, p:python_programming_language:21:000}

**Q1/Q2 per atom:**
- t:guido_van_rossum:00:000:01: Q1=no; Q2=supplies the bridge entity (Guido van Rossum as Python creator)
- p:python_programming_language:21:000: Q1=no; Q2=supplies the final property (name inspired by Monty Python)

**Genuine multi-hop:** YES. Cross-article entity linking: article A names creator, article B gives naming inspiration. Neither alone suffices.

**Decision:** approve.

---

### 13. qa-train-33 (comparison) — **approve**

**Sufficient set 0:** {p:pythonidae:06:000, p:python_genus:00:000}

**Q1/Q2 per atom:**
- p:pythonidae:06:000: Q1=no; Q2=supplies the comparison premise (pythons oviparous vs boas viviparous)
- p:python_genus:00:000: Q1=no; Q2=supplies the target fact (10 recognized species)

**Decision:** approve. Genuine comparison requiring two passages from different articles (pythonidae vs python_genus).

---

### 14. qa-train-36 (multihop) — **relabel-multihop**

**Sufficient set 0:** {p:ancient_rome:08:000, p:ancient_rome:17:000}

**Q1/Q2 per atom:**
- p:ancient_rome:08:000: Q1=yes (atom 17 alone answers population range); Q2=setup (Octavian→Augustus 27 BC, question already states this)
- p:ancient_rome:17:000: Q1=no; Q2=supplies the final property (population 450K–1M)

**Genuine multi-hop:** NO. Atom 17 alone determines the answer. Atom 08 is setup the question already gives.

**Decision:** relabel-multihop.

---

### 15. qa-train-42 (multihop) — **KNOWN SUSPECT — repair-minimality + relabel-multihop**

**Sufficient set 0:** {p:seashell:11:000, p:seashell:01:000}

**Q1/Q2 per atom:**
- p:seashell:11:000: Q1=yes (atom 01 alone answers "conchology"); Q2=setup (hermit crabs wear gastropod shells — question already states "Hermit crabs wear empty marine gastropod shells")
- p:seashell:01:000: Q1=no; Q2=supplies the final property (studying seashells of marine mollusks is conchology)

**Genuine multi-hop:** NO. Atom 01 alone determines the answer. Atom 11 is setup the question already gives verbatim.

**Minimality violation:** p:seashell:11:000 is redundant (setup duplicate of question premise). The sufficient set is non-minimal.

**Decision:** repair-minimality (drop p:seashell:11:000) AND relabel-multihop (single atom p:seashell:01:000 suffices).

---

### 16. qa-train-44 (multihop) — **repair-minimality**

**Sufficient set 0:** {p:nikola_tesla:16:000, p:nikola_tesla:08:000}

**Q1/Q2 per atom:**
- p:nikola_tesla:16:000: Q1=no (without it, no link from "telautomaton boat 1898" to Tesla); Q2=supplies the bridge event (Tesla demonstrated telautomaton in 1898)
- p:nikola_tesla:08:000: Q1=no (without it, no link from Tesla to AC patents wealth); Q2=supplies the final property (AC patents made him independently wealthy)

**Genuine multi-hop:** YES. Two-hop chain: event → property. Both atoms necessary.

**Minimality issue:** None — both atoms do distinct inferential work. However, both atoms are from the same article (p:nikola_tesla). The question asks "licensing which patents had made him independently wealthy?" Atom 08 states "The money Tesla made from licensing his AC patents made him independently wealthy". Atom 16 establishes it's the same Tesla who demonstrated the telautomaton. The question already states "Tesla demonstrated the telautomaton boat in 1898" — so atom 16 is SETUP (premise the question gives).

**Revised Q2:**
- p:nikola_tesla:16:000: Q2=setup (question already states "Tesla demonstrated the telautomaton boat in 1898")
- p:nikola_tesla:08:000: Q2=supplies the final property (AC patents)

**Genuine multi-hop:** NO — the question pre-states the first hop. Only atom 08 is needed.

**Decision:** relabel-multihop (single atom suffices) — the multi-hop label is not genuine because the question supplies the first hop premise.

---

### 17. qa-train-48 (comparison) — **approve**

**Sufficient set 0:** {t:venus_mythology:00:000:01, t:venus_mythology:00:000:02}

**Q1/Q2 per atom:**
- t:venus_mythology:00:000:01: Q1=no (without it, no link from Venus to Aeneas/Roman people); Q2=supplies the premise entity chain (Venus → Aeneas → Roman people)
- t:venus_mythology:00:000:02: Q1=no; Q2=supplies the target fact (Julius Caesar claimed her as ancestor)

**Decision:** approve. Genuine comparison requiring two distinct facts from the same article.

---

## Detailed Findings for KNOWN SUSPECTS

### qa-train-42 (Hermit crabs / conchology)
- **Corpus text verified:** p:seashell:11:000 states hermit crabs wear gastropod shells. p:seashell:01:000 states studying seashells of marine mollusks is conchology.
- **Question text:** "Hermit crabs wear empty marine gastropod shells; which field studies the seashells of marine mollusks?"
- **Finding:** The question's first clause is a verbatim restatement of p:seashell:11:000's main proposition. That atom is pure setup. Only p:seashell:01:000 is necessary. The multihop label is not genuine.
- **Required repairs:** (1) Drop p:seashell:11:000 from sufficient set (repair-minimality). (2) Set is_multi_hop=false, remove reference_hop_chains (relabel-multihop).

### qa-pilot-dev-05 (Borneo vs Java population)
- **Corpus text verified:** t:borneo:00:000:00 gives Borneo as third-largest, 23M pop. t:java:00:000:02 gives Java as most populous, 159.2M, 56% of Indonesia.
- **meta.group=java**, source_articles=[a:borneo, a:java].
- **Split check:** Both a:borneo (line 41) and a:java (line 417) have split_group="java". The new same-split rule permits cross-group evidence within the same split. This is VALID.
- **Necessity:** Both atoms genuinely necessary — Borneo atom identifies the first comparison referent, Java atom identifies the second referent AND supplies the target population figure. Neither alone suffices.
- **Decision:** approve (no repair needed).

---

## Genuine Multi-Hop Classification Summary

| Draft | Labeled multihop? | Genuine? | Reason |
|-------|-------------------|----------|--------|
| qa-pilot-dev-03 | yes | NO | Q gives first hop; single atom answers |
| qa-train-05 | yes | YES | Creator→co-founding chain |
| qa-train-09 | yes | NO | Q gives both bridge events; single atom answers |
| qa-train-14 | yes | NO | Q gives blood moon=lunar eclipse; single atom answers |
| qa-train-21 | yes | NO | Single atom (p:mars_bar:01:000) answers fully |
| qa-train-24 | yes | NO | Q gives Low Dam date; single atom answers |
| qa-train-32 | yes | YES | Cross-article: creator → naming |
| qa-train-36 | yes | NO | Q gives Augustus date; single atom answers |
| qa-train-42 | yes | NO | Q gives hermit crab fact; single atom answers |
| qa-train-44 | yes | NO | Q gives telautomaton demo; single atom answers |

**Total genuine multihop:** 2/10 (qa-train-05, qa-train-32)

---

## Notes on Alternatives (Q3)

No genuinely different sufficient sets (different node_ids) were found for any draft. All alternatives would be re-phrasings of the same passages or ancestor/descendant spans — not distinct evidence.

---

## Hard Negative Review Status

All 17 drafts have hard negatives with reviewed=true. No issues found.

---

## Provenance Check

All drafts have provenance.decision="approve" with verifier != author and content_hash matching. No stale approvals detected.

---

## Action Items for Repair Phase

1. **relabel-multihop (6 drafts):** qa-pilot-dev-03, qa-train-09, qa-train-14, qa-train-24, qa-train-36, qa-train-44 — set is_multi_hop=false, clear reference_hop_chains, clear hop_glosses.
2. **repair-minimality (2 drafts):** qa-train-21 (drop t:mars_bar:00:000:01), qa-train-42 (drop p:seashell:11:000). Note: qa-train-44 also needs atom 16 dropped but this is covered by its relabel-multihop repair.
3. **Combined repair-minimality + relabel-multihop (2 drafts):** qa-train-21, qa-train-42 — both atoms dropped and multihop label removed.
4. **Re-verify and re-approve** each repaired draft with new content hashes.

End of Pass 1 audit.