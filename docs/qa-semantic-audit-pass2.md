# QA Semantic Audit — Pass 2 of 4

**Scope:** 53 drafts in staging/ with question_type in {factoid, unanswerable, ambiguous} (multihop/comparison covered in Pass 1, not re-audited).
**Reviewer:** independent second reader (subagent), model `opencode/muse-spark-1.3-contributor-free`
**Corpus revision:** HEAD 3e82aa2 (same as Pass 1, `pilot-297-r1` line numbering assumed stable; all node texts below were fetched live from `corpus/corpus.jsonl` by node_id).
**Date:** 2026-09-30
**Method:** for every draft, the actual corpus text of every support atom and every hard negative was read and quoted/checked. Draft-copy match verified (all `MATCH` except where noted). Absence claims for unanswerable items were tested with corpus-wide searches, not sampling. Q3 alternative searches used distinctive-phrase corpus grep plus same-article passage enumeration.

## Summary Counts (primary decision per draft)

| Decision | Count | Drafts |
|----------|-------|--------|
| approve | 50 | all factoids except qa-train-28; all 5 unanswerable; ambiguous qa-train-08, -20, -26, -38 |
| repair-minimality | 0 | — |
| repair-alternatives | 3 | qa-pilot-dev-09, qa-train-02, qa-train-28 |
| relabel-multihop | 0 | — (no multihop labels in this slice) |
| reject-replace | 0 | — |

**Global Q3 note (factoids):** every single-atom factoid has a same-paragraph `p:`/`t:` mirror (sentence atom vs containing paragraph). Following Pass 1 precedent these ancestor/descendant spans are NOT genuinely different evidence, so Q3=NONE FOUND for all of them unless a different-passage alternative is listed. All node ids resolved (no missing ids). All hard negatives have `reviewed=true` and none entails any answer.

---

## Per-Draft Audit — factoids

### 1. qa-pilot-dev-01 (factoid) — **approve**
Q: "Which planet is described as the first from the Sun and the smallest in the Solar System?" A: Mercury. Set0: {t:mercury_planet:00:000:00} ("Mercury is the first planet from the Sun and the smallest in the Solar System." — verbatim corpus match).
Q1: N/A single atom. Q2: supplies the answer proposition directly. Q3: NONE FOUND (only ancestor p:mercury_planet:00:000). Not tautological (answer entity not named in Q). Neg (Mercury Records) is a clean confusable. **approve.**

### 2. qa-pilot-dev-02 (factoid) — **approve**
Q asks birth name of Queen lead vocalist/pianist; A: Farrokh Bulsara. Set0: {t:freddie_mercury:00:000:00} (verbatim match, supplies birth name + Queen role).
Q1: N/A. Q2: supplies answer + identifying description. Q3: NONE FOUND — p:freddie_mercury:01:000 ("Mercury was born Farrokh Bulsara in Stone Town...") gives the birth name but does NOT link Mercury to Queen, so {p:01:000} alone is not sufficient; no genuine alternative. Neg (Mercury planet) clean. **approve.**

### 3. qa-pilot-dev-04 (factoid) — **approve**
Q: Greater Sunda island, capital on NW coast, most populous; A: Java. Set0: {t:java:00:000:02} (verbatim; "world's most populous island... 159.2 million"). Q2: supplies answer + disambiguator. Q3: NONE FOUND (only ancestor p:java:00:000). Neg (Borneo third-largest) clean same-group distractor. **approve.**

### 4. qa-pilot-dev-06 (factoid) — **approve**
Q: GDR construction-commencement date; A: 13 August 1961. Set0: {t:berlin_wall:00:000:01} (verbatim). Q3: NONE FOUND (only ancestor p:berlin_wall:00:000). Neg (neighbor sentence on death strip) non-answering. **approve.**

### 5. qa-pilot-dev-08 (factoid) — **approve**
Q: most solitary great ape, mother-offspring bonds; A: Orangutans. Set0: {t:orangutan:00:000:08} (verbatim). Q3: NONE FOUND (only ancestor p:orangutan:00:000). Neg (gorilla troops) is the contrast entity, clean. **approve.**

### 6. qa-pilot-dev-10 (factoid) — **approve**
Q: dominant wavelength for yellow+red mix percept; A: between roughly 585 and 620 nanometres. Set0: {t:orange_colour:00:000:01} (verbatim). Q3: NONE FOUND. Neg (Orange telecom brand) clean entity-confusion. **approve.**

### 7. qa-train-01 (factoid) — **approve**
Q: company owning Audible, Goodreads, Twitch, Zappos; A: Amazon. Set0: {p:amazon_company:12:000} (verbatim; lists all four). Q3: NONE FOUND — corpus-wide check: only 12:000 nodes list Goodreads+Twitch together; 23 other 'audible' passages are partial. Neg (rainforest basin shares) clean. **approve.**

### 8. qa-train-04 (factoid) — **approve**
Q: Beatles 1968 label; A: Apple Records. Set0: {t:apple_records:00:000:00} (verbatim). Q3: NONE FOUND. Neg (Apple Inc wearables) clean. **approve.**

### 9. qa-train-06 (factoid) — **approve**
Q: 52% of 2024 world apple production; A: China. Set0: {p:apple:14:000} (verbatim). Q3: NONE FOUND. Two negatives (Malus genus, Malus sections) clean. **approve.**

### 10. qa-train-07 (factoid) — **approve**
Q: length of Columbia River (largest tributary Snake); A: 1,243 mi. Set0: {t:columbia_river:00:000:03} (verbatim; single sentence carries both length and tributary). Q3: NONE FOUND. Neg (Colombia biodiversity) clean. **approve.**

### 11. qa-train-10 (factoid) — **approve**
Q: UNESCO site, interior delta not draining to sea; A: Okavango Delta. Set0: {t:okavango_delta:00:000:01} (verbatim). Q3: NONE FOUND. Neg (Ganges-Brahmaputra/Lake Baikal delta passage) is a near-miss distractor, non-answering. **approve.**

### 12. qa-train-11 (factoid) — **approve**
Q: Delta variant first detection where/when; A: India on 5 October 2020. Set0: {t:sars_cov_2_delta_variant:00:000:01} (verbatim). Q3: NONE FOUND. Neg (Delta Air Lines SkyMiles) clean. **approve.**

### 13. qa-train-13 (factoid) — **approve**
Q: Sun's disk in total solar eclipse; A: fully obscured by the Moon. Set0: {t:solar_eclipse:00:000:02} (verbatim). Q3: NONE FOUND. Neg (Mitsubishi Eclipse car) clean. **approve.**

### 14. qa-train-16 (factoid) — **approve**
Q: White Tower builder 1078; A: William the Conqueror. Set0: {t:tower_of_london:00:000:03} (verbatim). Q3: NONE FOUND. Neg (City of London HQs) clean. **approve.**

### 15. qa-train-17 (factoid) — **approve**
Q: 1896 busiest-point bridge crossings/hour; A: 8,000 pedestrians and 900 vehicles. Set0: {p:london_bridge:05:002} (verbatim). Note: Q says "the bridge" without naming London Bridge, but the 1896-busiest description resolves uniquely via the atom; answer needs only the figures. Not a defect (no guessing about what is asked). Q3: NONE FOUND (only sentence-child mirror t:london_bridge:05:002:00). **approve.**

### 16. qa-train-19 (factoid) — **approve**
Q: MOLA height of Olympus Mons; A: 21.287 km. Set0: {t:olympus_mons:00:000:01} (verbatim). Q3: NONE FOUND. Neg (Mars geological activity) clean. **approve.**
### 17. qa-train-22 (factoid) — **approve**
Q: river+city of Aswan High Dam 1960–1970; A: the Nile at Aswan. Set0: {t:aswan_high_dam:00:000:00} (verbatim). Q3: NONE FOUND. Neg (Nile lifeline passage) non-answering. **approve.**

### 18. qa-train-23 (factoid) — **approve**
Q: Sphinx reign; A: king Khafre. Set0: {p:giza_pyramid_complex:06:000} (verbatim). Q3: NONE FOUND (only sentence-child mirror). Neg (Egyptian kingdoms periods) clean. **approve.**

### 19. qa-train-25 (factoid) — **approve**
Q: whom Paris fatally wounded; A: Achilles. Set0: {t:paris_mythology:00:000:02} (verbatim). Q3: NONE FOUND. Neg (Paris population 1640–1780) clean. **approve.**

### 20. qa-train-28 (factoid) — **repair-alternatives**
Q: height of K2; A: 8611 metres. Set0: {t:k2:00:000:00} (verbatim; sufficient, minimal).
Q3: GENUINE ALTERNATIVE FOUND — {t:k2:03:000:00}: "K2's height given on maps and encyclopaedias is 8611 metres." Different passage (section 03 vs 00), different node id, independently determines the answer. (Caution: use the sentence atom, NOT the parent p:k2:03:000, whose continuation cites a conflicting 8609.02 m expedition measurement.) Record {t:k2:03:000:00} as additional sufficient set, then re-verify/re-approve. Neg (Everest neighbors) clean. **repair-alternatives.**

### 21. qa-train-29 (factoid) — **approve**
Q: yearly Kilimanjaro trekkers; A: roughly 50,000. Set0: {p:mount_kilimanjaro:18:000} (verbatim). Q3: NONE FOUND (only sentence-child mirror; park-revenue/tourist node 17:000 gives 2011–12 hiker counts, a different statistic, not the answer). Neg (K2 deadliest) clean. **approve.**

### 22. qa-train-31 (factoid) — **approve**
Q: language emphasizing readability + significant indentation; A: Python. Set0: {t:python_programming_language:00:000:00} (verbatim). Q3: NONE FOUND. Neg (Monty Python troupe) clean entity-confusion. **approve.**

### 23. qa-train-34 (factoid) — **approve**
Q: capital/largest city of Italy; A: Rome. Set0: {t:rome:00:000:00} (verbatim). Q3: NONE FOUND (only ancestor p:rome:00:000; no other passage states it). **approve.**

### 24. qa-train-35 (factoid) — **approve**
Q: Octavian's age and year taking name Augustus; A: In 27 BC and at the age of 36. Set0: {p:ancient_rome:08:000} (verbatim; single paragraph carries both). Q3: NONE FOUND. Two Rome-location negatives clean. **approve.**

### 25. qa-train-37 (factoid) — **approve**
Q: sixth planet, second largest; A: Saturn. Set0: {t:saturn:00:000:00} (verbatim). Q3: NONE FOUND. Neg (Saturn Corporation CEOs) clean. **approve.**

### 26. qa-train-40 (factoid) — **approve**
Q: what kind of programs are most OS shells; A: command-line interface (CLI) programs. Set0: {t:shell_computing:00:000:02} (verbatim). Q3: NONE FOUND. Neg (seashell mantle) clean. **approve.**

### 27. qa-train-41 (factoid) — **approve**
Q: Shell per-share price for Pennzoil-Quaker State 2002; A: US$22 per share. Set0: {p:shell_plc:03:000} (verbatim). Q3: NONE FOUND. Neg (OS shell definition) clean. **approve.**

### 28. qa-train-43 (factoid) — **approve**
Q: current type reversing direction; A: Alternating current (AC). Set0: {t:alternating_current:00:000:00} (verbatim). Q3: NONE FOUND. Neg (Edison/Ford friendship) clean. **approve.**

### 29. qa-train-46 (factoid) — **approve**
Q: Venus orbital period; A: 224.7 days. Set0: {p:venus:10:000} (verbatim). Q3: NONE FOUND. Neg (Venus flytrap leaves) clean. **approve.**

### 30. qa-train-47 (factoid) — **approve**
Q: year flytrap designated NC state carnivorous plant; A: 2005. Set0: {p:venus_flytrap:19:000} (verbatim). Q3: NONE FOUND. Neg (Caesar/Venus ancestor) clean. **approve.**

### 31. qa-train-49 (factoid) — **approve**
Q: two living Loxodonta species; A: bush + forest elephant. Set0: {t:african_elephant:00:000:00} (verbatim). Q3: NONE FOUND. Neg (elephant distribution/habitat) non-answering. **approve.**

### 32. qa-train-50 (factoid) — **approve**
Q: Hitchcock storyboarding detail + viewfinder; A: compound quote. Set0: {p:alfred_hitchcock:23:001} (verbatim; single paragraph carries both facts). Q3: NONE FOUND. Neg (Cornwall Ranch home) clean sibling-paragraph. **approve.**

### 33. qa-train-51 (factoid) — **approve**
Q: three main Amsterdam canals; A: Prinsengracht, Herengracht, Keizersgracht. Set0: {p:amsterdam:09:000} (verbatim). Q3: NONE FOUND. Neg (Port of Amsterdam cargo) clean. **approve.**

### 34. qa-train-52 (factoid) — **approve**
Q: Black Death bacterium + spread; A: Yersinia pestis, flea bites. Set0: {t:black_death:00:000:02} (verbatim). Q3: NONE FOUND. Neg (plague symptoms) non-answering. **approve.**

### 35. qa-train-53 (factoid) — **approve**
Q: Ethereum and Bitcoin block times; A: 12 seconds / 10 minutes. Set0: {p:blockchain:04:000} — verified full corpus text: "Since 2022, the block time for Ethereum is set to exactly 12 seconds, while for bitcoin it is on average 10 minutes." Direct entailment. Q3: NONE FOUND. Neg (permissioned blockchains) clean. **approve.**

### 36. qa-train-54 (factoid) — **approve**
Q: Grand Canyon length/width/depth; A: 277 mi / 18 mi / 6093 ft. Set0: {t:grand_canyon:00:000:01} (verbatim). Q3: NONE FOUND. Neg (canyon species counts) clean. **approve.**

### 37. qa-train-55 (factoid) — **approve**
Q: coral-preying starfish + 2000 outbreak loss; A: crown-of-thorns... 66% loss. Set0: {p:great_barrier_reef:13:000} (verbatim incl. RRC study detail). Q3: NONE FOUND. Neg (ocean acidification) clean. **approve.**

### 38. qa-train-56 (factoid) — **approve**
Q: five Himalayan countries; A: Nepal, India, China, Bhutan, Pakistan. Set0: {t:himalayas:00:000:03} (verbatim). Q3: NONE FOUND. Neg (Sanskrit etymology) clean. **approve.**

### 39. qa-train-57 (factoid) — **approve**
Q: Linux kernel first release when/by whom; A: 17 September 1991 by Linus Torvalds. Set0: {t:linux:00:000:00} (verbatim). Q3: NONE FOUND. Neg (Linux graphics tools) clean. **approve.**

### 40. qa-train-58 (factoid) — **approve**
Q: octopus small-gap ability; A: radically deform its shape. Set0: {t:octopus:00:000:03} (verbatim). Q3: NONE FOUND. Neg (ink sac) clean. **approve.**

### 41. qa-train-59 (factoid) — **approve**
Q: Penicillin G first produced from what; A: a penicillium fungus that occurs in nature. Set0: {p:penicillin:04:000} (verbatim). Q3: NONE FOUND. Neg (beta-lactam ring chemistry) clean. **approve.**

### 42. qa-train-60 (factoid) — **approve**
Q: Tokyo 2007 Michelin stars + vs competitor; A: 191 stars, ~twice Paris. Set0: {p:tokyo:42:000} (verbatim incl. competitor comparison). Q3: NONE FOUND. Neg (Tokyo rail hub) clean. **approve.**

---
## Per-Draft Audit — unanswerable (absence claims verified corpus-wide)

### 43. qa-pilot-dev-07 (unanswerable) — **approve**
Q: "How many visitors toured the Berlin Wall Memorial in 2023?" `absent_reason`: berlin-group articles lack visitor/2023 attendance figures.
Verification: "Berlin Wall Memorial" occurs in exactly 2 corpus nodes (p:berlin:00:000 lead context; t:berlin:00:000:23 landmark list) — neither gives any count. Co-occurrence search for Berlin-Wall + visitor/tourist nodes: only p:berlin:22:000 (2014 city hotel stays/guests, lists memorial among visited places with NO per-site count) and tour-visit procedural passages (visa/DM25 rules, Hasselhoff concert 500k, Kennedy audience 450k — all different events). No node states a 2023 memorial visitor count. The 2014 city-wide hotel figure does not answer the question. Neg (Berlin capital) clean. `absent_reason` specific and true. **approve.**

### 44. qa-train-15 (unanswerable) — **approve**
Q: "How many people travelled to observe the 2024 total solar eclipse in North America?" `absent_reason`: no eclipse-group article states observer/attendance figures for any specific eclipse.
Verification: corpus-wide — no solar-eclipse node mentions 2024 at all (only PROBA-3 2024 launch and Eclipse-software 2024 moribund note); no eclipse node pairs observer/crowd/tourist/attend/million-people figures with any specific eclipse (matches are generic: umbraphiles, path-of-totality definitions, Concorde 74-min stretch, 1919 Eddington). "April 8"/"8 April" absent. Absence holds beyond the eclipse group. Neg (umbraphile passage) non-answering. **approve.**

### 45. qa-train-30 (unanswerable) — **approve**
Q: "What was the summit success rate for the Machame route on Kilimanjaro in 2024?" `absent_reason`: only cross-route 70-80% average, route durations, and a Lemosho-route study stated.
Verification: confirmed — t:mount_kilimanjaro:18:000:00/01 (70-80% all-routes average), 17:000:07 (Machame duration 6-7 days, no rate), 19:000:06 (Marangu lowest rate, no figure), 26:000:03/06 (AMS-sickness study on Lemosho/Machame attempters — altitude sickness, NOT summit success; minor imprecision in `absent_reason`'s "Lemosho-route study" gloss, immaterial since no 2024 Machame success rate exists anywhere). p:mount_kilimanjaro:17:000 (2011–12 park tourist counts) is a different statistic. Absence holds. Neg (Everest 1956-60 ascents) clean. **approve** (suggest fixing the gloss to "AMS study" at repair time, not a decision-changer).

### 46. qa-train-39 (unanswerable) — **approve**
Q: "On what exact date did NASA's Dragonfly rotorcraft launch toward Titan?" `absent_reason`: only scheduled launch month July 2028 + 2034 arrival stated.
Verification: "dragonfly" (case-insensitive) occurs only in p:saturn:21:000 / t:saturn:21:000:00 ("scheduled for launch in July 2028... arrive at Titan in 2034") plus an unrelated insect node (green darner dragonfly). No exact date anywhere; the question's presupposition (already launched) is false in-corpus. Absence holds. Neg (Pioneer 11 flyby) clean. **approve.**

### 47. qa-train-45 (unanswerable) — **approve**
Q: "How many Cybercabs had been delivered to third-party operators by the end of 2025?" `absent_reason`: only investigating-possibility-of-selling status, no delivery counts/dates.
Verification: Cybercab nodes state concept unveiling (t:tesla_inc:05:001:07), announced plans (06:000:02), "taken steps to investigate the possibility of selling... to third-party operators" (11:000:00), 4680-cell usage (31:000:05). Delivery-figure nodes (78:000:xx, 10:000:01/04) cover fleet totals/Cybertruck, never Cybercab third-party deliveries. No Cybercab delivery count exists. Absence holds. Neg (EV battery skateboard) clean. **approve.**

---

## Per-Draft Audit — ambiguous (genuineness of ambiguity)

### 48. qa-pilot-dev-09 (ambiguous) — **repair-alternatives**
Q: "How is the social grouping of the great ape described?" Readings: gorilla (set0: troops/silverback) vs chimpanzee (set1: 200+ groups + male hierarchy). Both atoms verbatim corpus matches; each reading has its own sufficient set and distinct answer. The bare kind term "the great ape" with no species identifier is genuinely underdetermined between two confusable same-group entities — a real lexical/reference ambiguity, not vague wording (the question is crisp; two corpus entities fit it).
Q1/Q2 set0: single atom, supplies gorilla answer. Q1/Q2 set1: remove :06 → {:07} loses the 200-member fact (Q1=no); remove :07 → {:06} loses hierarchy (Q1=no); both necessary for the recorded combined answer — minimal.
Q3: GENUINE ALTERNATIVES FOUND — {p:gorilla:08:000}: "Gorillas live in groups called troops. Troops tend to be made of one adult male or silverback, with a harem of multiple adult females and their offspring..." (different passage, section 08 vs lead, independently determines the gorilla reading); and {p:chimpanzee:10:000}: "Chimpanzees live in communities... Communities can reach over 200 members... males, who are the more dominant sex..." (different passage, section 10 vs lead, determines the chimpanzee reading). Record both as additional sufficient sets, then re-verify/re-approve. Neg (gorilla fur neighbor sentence) clean. **repair-alternatives.**

### 49. qa-train-02 (ambiguous) — **repair-alternatives**
Q: "What does the term Amazon refer to?" Readings: company (set0, Bezos node) vs rainforest (set1). Both verbatim; distinct sets/answers; classic genuine proper-name ambiguity.
Q3: GENUINE ALTERNATIVE FOUND for set0 — {p:amazon_company:00:000}: "Amazon.com, Inc. (doing business as Amazon) is an American multinational technology conglomerate engaged in e-commerce, cloud computing... Founded in 1994 by Jeff Bezos..." Different article/passage from the Bezos node, independently determines reading 0 ("Amazon the company founded by Jeff Bezos" / e-commerce+cloud company). (t:amazon_company:00:000:01 is its sentence child — descendant span, not distinct; do not record.) No alternative for set1 (only ancestor p:amazon_rainforest:00:000). Record {p:amazon_company:00:000} as additional set for reading 0, then re-verify/re-approve. Neg (Amazons queen Hippolyte) clean entity-confusion. **repair-alternatives.**

### 50. qa-train-08 (ambiguous) — **approve**
Q: "What is Columbia?" Readings: university (set0) vs river (set1). Both atoms verbatim; distinct sets/answers; genuine proper-name ambiguity (same string denotes a university and a river in-corpus). Q3: NONE FOUND — only ancestor-paragraph mirrors (p:columbia_university:00:000, p:columbia_river:00:000); other Columbia passages state different facts (discharge figures, flow rank) that do not determine either reading answer. Neg (Columbia Memorial Space Center) clean third-sense distractor. **approve.**

### 51. qa-train-20 (ambiguous) — **approve**
Q: "What is Mars?" Readings: planet (set0) vs chocolate bar (set1). Both verbatim; genuine ambiguity. (Corpus third sense, Mars god, is correctly used as the hard negative rather than a third reading — >=2 readings required, exhaustiveness not required.) Q3: NONE FOUND — "fourth planet from the Sun" occurs only in m:00:000/p-t pair; "caramel and nougat" only in mars_bar:00:000 pair. Neg clean. **approve.**

### 52. qa-train-26 (ambiguous) — **approve**
Q: "Who or what was Paris?" Readings: mythological prince (set0: t:paris_mythology:00:000:01, verbatim) vs city (set1: p:paris:08:000 governance passage, verbatim). Distinct sets/answers; genuine name ambiguity (person vs city). Set1 atom determines the city reading ("governed directly by representatives of the king, emperor, or president" → recorded answer). Q3: NONE FOUND — prince alternatives are ancestor/partial only (p:paris_mythology:00:000 ancestor; t:04:000:00 "child of Priam" lacks prince-of-Troy proposition); city alternatives state different facts (Napoleon prefect, Commune) not the recorded answer. Neg (Eiffel tower names) clean. **approve.**

### 53. qa-train-38 (ambiguous) — **approve**
Q: "What is Saturn?" Readings: planet (set0, single atom) vs Roman god (set1, two atoms). Genuine ambiguity. Set1 minimality: remove :00 → {:01} "He was described as a god of time..." — anaphoric "He" with no resolvable referent, cannot determine Saturn (Q1=no); remove :01 → {:00} "Saturn was a god in ancient Roman religion" — determines godhood but not the recorded domain list (time/generation/abundance/wealth/agriculture) (Q1=no). Both atoms do distinct work (fixes referent / supplies property). Minimal.
Q3: NONE FOUND — only ancestor p:saturn_mythology:00:000 (contains both sentences); other god passages are partial (e.g., t:01:000:08 "god of time" alone). Neg (Saturn Corp no-haggle) clean. **approve.**

---

## Tautology / leak screen (factoids)

Automated answer-words-in-question screen flagged 14 drafts; manual review: all hits are the question's identifying frame restating corpus wording (e.g., "Which starfish preys on coral polyps" sharing "starfish/preys/coral"; "How many Michelin stars did Tokyo receive" sharing "stars/Tokyo") — in no case does the question name the distinctive answer entity or figure. No tautologies. No hard negative entails any answer (nearest misses — qa-train-17's sibling bridge context, qa-train-35's Rome-location negatives, qa-train-30's Everest ascents — all verified non-answering).

## Action Items for Repair Phase

1. **repair-alternatives (3 drafts):** qa-pilot-dev-09 (add {p:gorilla:08:000} to reading 0, {p:chimpanzee:10:000} to reading 1); qa-train-02 (add {p:amazon_company:00:000} to reading 0); qa-train-28 (add {t:k2:03:000:00} — sentence atom only, not the paragraph with the conflicting 8609.02 m figure).
2. **Minor gloss fix (non-blocking):** qa-train-30 `absent_reason` calls the AMS study a "Lemosho-route study" — it covers Lemosho-or-Machame attempters and measures altitude sickness, not success rate. Correct at next touch.
3. **Re-verify and re-approve** each repaired draft with new content hashes; approvals of the other 50 stand.

End of Pass 2 audit.
