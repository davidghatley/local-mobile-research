# QA Shadow-Dev Re-approval Ledger (independent re-approval pass)

Re-approver: `round0-shadow-dev-reapprover` / `opencode/space-bunny-free`
(VERIFIED zero-cost endpoint; recorded substitution for the failed
`gemma-4-31b-it:free` provider error. No nested spawning. No paid fallback.)

Corpus revision read: `pilot-297-r1` — `corpus/corpus.jsonl`, 297 articles, 113,951 nodes.
Protocol: `docs/qa-semantic-audit-protocol.md`. Phase 2 batch ledgers: `BATCH-A` (01-30),
`BATCH-B` (31-59, which recorded NO `audit_decision` on any file — all 29 treated as
unaudited), `BATCH-C` (61-90).

This reviewer did not author the items and did not perform the Phase 2 audit. All 89 items
were re-read against the actual corpus, not against the batch ledgers.

## Outcome

- Approved: **89 / 89**. 88 as-is, 1 after an in-place repair.
- Repaired and re-approved: **1** (`qa-shadow-dev-36`).
- Rejected: **0**. Files deleted: **0**.
- Validator errors before this pass: **89** (all `missing or non-approve verification decision`).
- Validator errors after this pass: **0** (`drafts: 209, approved: 209, errors: 0`).
- Test suite: `python3 -m unittest discover -s tests` -> **343 tests, 1 failure** — identical
  before and after this pass (verified by re-running against a pristine copy of `staging/`).
  The failure is `test_full_mode_runs_the_freeze_gated_stages`, which asserts the literal
  string `[6/9]` while the uncommitted working-tree change to `scripts/verify_round0`
  (`STAGE_IDS` 9 -> 10 stages) makes the entrypoint print `[6/10]`. Not caused by this pass;
  `scripts/` and `tests/` are outside this reviewer's write scope.

## Programmatic checks run over all 89 items

| check | result |
|---|---|
| every evidence `node_id` resolves in the corpus | 89/89 pass |
| atom text == corpus node text, code-point exact | 89/89 pass, 0 mismatches |
| atom text == corpus node text, UTF-8 **byte** exact | 89/89 pass, 0 mismatches |
| exotic space/format chars injected into atom text | none (NBSPs present are inherited verbatim from the corpus) |
| every hard-negative `node_id` resolves | 89/89 pass |
| hard negative contains the answer phrase verbatim | 0 of 178 negatives |
| hard negative textually repeats >80% of an evidence atom | 0 |
| question text or answer duplicated vs the 60 train / 50 dev items | 0 (the only `answer_text` collisions are the empty strings of the 5 unanswerable items) |
| conjunctive question split into alternative singletons `[[A],[B]]` | 0 (all 31 multi-atom sets across 25 items are single conjunctive sets) |

`13` items carry more than one singleton set. All 13 were checked individually and every
second set was confirmed to be an INDEPENDENT route to the same answer, not a split hop:
6 are `ambiguous` items where one set backs each reading (27, 28, 57, 58, 87, 88) and 7 are
factoid items where a second genuinely different passage was recorded (73, 75, 76, 78, 80,
81, 83).

## The one repair

**`qa-shadow-dev-36`** — hard negative that contained the answer. `hard_negatives[1]` was
`p:gda_sk:05:000`, whose full corpus text reads "it describes how in 997, Saint Adalbert of
Prague baptised the inhabitants of **urbs Gyddannyzc**". The question asks under what name the
settlement was recorded after St. Adalbert's death in 997 and the gold answer is
`urbs Gyddanyzc`, so the negative answered the question — the recurring defect class named in
the brief. It also revealed a latent problem: the two spellings differ, so a lexical
answer-string check would never have caught it; only reading the paragraph did.

Repair: `p:gda_sk:05:000` -> `p:gda_sk:03:000` (same article, same `token_overlap_nearmiss`
type, `reviewed: true`). The replacement discusses Kashubian names for the city (Gduńsk,
"The Royal Polish City of Gdańsk", "Our Capital City Gduńsk") and contains neither the 997
record nor any `Gyddany` spelling — a strong lexical near-miss that does not answer.
Question, answer, evidence and sufficient_sets were not touched; `negative.reviewer` set to
this reviewer because this reviewer is the one attesting non-answering status.

## Per-item ledger

`batch` = the Phase 2 batch that claimed the item; `prior audit_decision` = what that batch
actually left in the file.

| id | batch | prior audit_decision | verdict | what I verified | repair |
|---|---|---|---|---|---|
| `qa-shadow-dev-01` | A | approve | **approve** | Single atom p:cambridge:00:000 states both the Cambridgeshire county town and the River Cam, so the singleton set is sufficient and minimal; both negatives read in full name no river for Cambridge, England. | — |
| `qa-shadow-dev-02` | A | approve | **approve** | p:cambridge_massachusetts:00:000 states the Middlesex County city is across the Charles River from Boston and was named for the University of Cambridge; negatives are an industrial-history and a rent-control paragraph, neither of which names the namesake university. | — |
| `qa-shadow-dev-03` | A | approve | **approve** | p:harvard_university:00:000 gives the 1636 founding and the Cambridge, Massachusetts Ivy-League description the question supplies; negatives cover 20th-century admissions history and the Cambridge mathematics Tripos, neither stating 1636. | — |
| `qa-shadow-dev-04` | A | approve | **approve** | p:solar_corona:00:000 opens by identifying the corona as the outermost atmospheric layer, which is the whole answer; negatives describe coronal structure and Corona Australis stars and do not answer the layer question. | — |
| `qa-shadow-dev-05` | A | approve | **approve** | p:corona_beer:00:000 states Corona is produced by Grupo Modelo in Mexico; negatives are the Sinebrychoff ingredient paragraph and the Corona Australis constellation lead, neither of which names the producer. | — |
| `qa-shadow-dev-06` | A | approve | **approve** | p:corona_australis:00:000 gives the Latin gloss 'southern crown' directly; negatives cover constellation boundaries and beer ingredients, neither of which glosses the name. | — |
| `qa-shadow-dev-07` | A | approve | **approve** | p:jaguar:00:000 gives Panthera onca with the Americas-native description; negatives are the animal's body-size paragraph and the Jaguar Cars lead, neither giving a scientific name. | — |
| `qa-shadow-dev-08` | A | approve | **approve** | p:jaguar_cars:00:000 states the brand is owned by Tata Motors; negatives are the Daimler-factory history and the Atari Jaguar lead, neither naming an owner. | — |
| `qa-shadow-dev-09` | A | approve | **approve** | p:jaguar_supercomputer:00:000 states Jaguar was built at Oak Ridge National Laboratory; negatives are the XT3/XT4 upgrade history and the Swallow Sidecar origin, neither naming a national laboratory. | — |
| `qa-shadow-dev-10` | A | approve | **approve** | p:lincolnshire:02:001 states Wolds Top as the highest point; negatives are the county's border geography and the Lincoln Motor Company lead, neither naming a high point. | — |
| `qa-shadow-dev-11` | A | approve | **approve** | p:mount_vernon:00:000 places the estate on the Potomac; negatives are the mansion construction history and the 1759 marriage/estate-management paragraph, neither naming a river for Mount Vernon. | — |
| `qa-shadow-dev-12` | A | approve | **approve** | p:washington_d_c:00:000 gives the 2020 census figure 689,545; negatives are the 1814 burning of Washington and the Kennewick Man paragraph, neither stating a census population. | — |
| `qa-shadow-dev-13` | A | approve | **approve** | p:university_of_washington:00:000 gives the 1861 founding with the U-Dub and Seattle descriptors; negatives are the campus-relocation paragraph and the Twenty-third Amendment history, neither stating a founding year. | — |
| `qa-shadow-dev-14` | A | approve | **approve** | p:oymyakon:00:000 states the coldest-permanently-inhabited distinction outright; negatives are the two-valley climate paragraph and the WWII airfield paragraph, neither repeating the distinction. | — |
| `qa-shadow-dev-15` | A | approve | **approve** | p:mary_celeste:00:000 gives the December 4, 1872 discovery date; negatives give Briggs's birth date and the 1868/October 1872 ownership dates, so the December 4, 1872 string appears in no negative. | — |
| `qa-shadow-dev-16` | A | approve | **approve** | p:saola:00:000 gives Pseudoryx nghetinhensis with the Annamite Range bovid descriptor; negatives cover range/elevation and Robichaud's measurements, neither naming the species. | — |
| `qa-shadow-dev-17` | A | approve | **approve** | p:dead_sea:00:000 states the Jordan River as the main tributary; negatives are the historical-names list and the Sedom Lagoon evaporites paragraph, neither naming a tributary. | — |
| `qa-shadow-dev-18` | A | approve | **approve** | Comparison with is_multi_hop=true is sound: p:harvard_university:08:000 (209 acre main campus) and :09:000 (358 acre Allston campus) are both required, neither alone compares, and 358 > 209 yields Allston; negatives give no acreage. | — |
| `qa-shadow-dev-19` | A | approve | **approve** | Comparison with is_multi_hop=true is sound: p:university_of_cambridge:00:000 (1209) and p:harvard_university:00:000 (1636) are both required to compare, and the negatives state no founding year for either. | — |
| `qa-shadow-dev-20` | A | approve | **approve** | Genuine two-hop: p:cambridge_massachusetts:00:000 fixes the Middlesex County city named for an English university but gives no year, while p:university_of_cambridge:00:000 supplies 1209 without the city link; negatives cover Cambridge, England wartime history and Massachusetts bridge-building, neither giving 1209. | — |
| `qa-shadow-dev-21` | A | approve | **approve** | Genuine two-hop: p:washington_state:01:000 fixes the Columbia-to-Washington renaming and names George Washington, p:george_washington:01:000 supplies the February 22, 1732 birth date; negatives give no birth date and no Columbia renaming. | — |
| `qa-shadow-dev-22` | A | approve | **approve** | Genuine two-hop: p:emancipation_proclamation:00:000 identifies the January 1, 1863 issuer as Lincoln, p:abraham_lincoln:01:000 supplies the 1637 emigration to Massachusetts; negatives mention Lincoln but state neither the proclamation nor the 1637 emigration. | — |
| `qa-shadow-dev-23` | A | approve | **approve** | Genuine two-hop: p:american_civil_war:02:000 fixes Lincoln as the 1860 winner whose victory triggered secession, p:lincoln_motor_company:01:000 supplies the Leland naming; negatives are slavery-cause history and Model L/K production, neither naming a namesake company. | — |
| `qa-shadow-dev-24` | A | repaired | **approve** | The Phase 2 relabel is correct: p:coronavirus:02:001 alone both identifies June Almeida (working with Tyrrell, the group later named coronaviruses) and states St Thomas' Hospital, while the dropped p:coronavirus:01:000 names the coiners but no hospital, so the singleton is sufficient, minimal and correctly a factoid. | — |
| `qa-shadow-dev-25` | A | approve | **approve** | Genuine two-hop: p:atari_jaguar:00:000 gives the November 1993 North American release with no tagline, p:atari_jaguar:03:000 gives the 'Do the math!' American-market tagline with no release date; negatives are the peripherals paragraph and the Atari 7800 sentence. | — |
| `qa-shadow-dev-26` | A | approve | **approve** | Genuine two-hop: p:cambridge_massachusetts:00:000 fixes Washington via the July 2, 1775 Cambridge Common command, p:george_washington:00:000 supplies the 1789 to 1797 term; negatives give no presidential term. | — |
| `qa-shadow-dev-27` | A | approve | **approve** | Ambiguity is genuine, not vagueness: 'Corona' resolves to the beer brand (p:corona_beer:01:000, officially introduced 1925) or the constellation name (p:corona_australis:01:000, entered by the IAU in 1922), two distinct concrete answers each with corpus support; negatives cover neither year. | — |
| `qa-shadow-dev-28` | A | approve | **approve** | Ambiguity is genuine: two corpus cities are named Cambridge, giving 145,700 (p:cambridge:00:000, City of Cambridge 2021) and 118,403 (p:cambridge_massachusetts:00:000, 2020 US census); each atom states its own city's figure and neither states the other's. | — |
| `qa-shadow-dev-29` | A | approve | **approve** | Corpus-wide absence verified: the Atari Jaguar article's only price statements are a redacted relative price (p:atari_jaguar:00:000), an unquantified 'low price point' (:02:000/:17:000), a redacted 1995 price drop (:04:000), 'selling at a loss', competitor figures and 2001 UK resale; no node states a November 1993 launch price. | — |
| `qa-shadow-dev-30` | A | approve | **approve** | Corpus-wide absence verified: the only 2022 Rano Raraku wildfire statement is t:moai:15:000:12 'an unknown number of moai ... were damaged'; no node in the corpus gives a damaged count. | — |
| `qa-shadow-dev-31` | B | NONE (unaudited by Phase 2) | **approve** | p:australia:03:000 names the Duyfken as the 1606 first documented European landing; negatives cover colonial settlement and federation, naming no ship. | — |
| `qa-shadow-dev-32` | B | NONE (unaudited by Phase 2) | **approve** | p:buenos_aires:03:000 gives the 1806 first British invasion and the repelled 1807 second; negatives are the 1516 Solis sentence and 19th-century municipal politics, neither giving 1806. | — |
| `qa-shadow-dev-33` | B | NONE (unaudited by Phase 2) | **approve** | p:cactus:00:000 gives about 127 genera for Cactaceae; negatives give species counts and morphology and no genus total, so the 127 figure appears in no negative. | — |
| `qa-shadow-dev-34` | B | NONE (unaudited by Phase 2) | **approve** | p:cheese:04:000 states Anglo-Saxons named the Thames village Ceswican, meaning 'Cheese farm', around 1000; negatives are Roman cheesemaking and cheesemaking origins, neither naming Ceswican. | — |
| `qa-shadow-dev-35` | B | NONE (unaudited by Phase 2) | **approve** | p:fifa_world_cup:02:001 states Lucien Laurent scored the first goal in World Cup history; negatives cover Uruguay's hosting and the 1950 tournament, naming no scorer. | — |
| `qa-shadow-dev-36` | B | NONE (unaudited by Phase 2) | **approve** | p:gda_sk:02:000 states the post-997 recorded name urbs Gyddanyzc; negative p:gda_sk:05:000 was replaced because it states urbs Gyddannyzc for the same 997 episode and so answered the question, and the replacement p:gda_sk:03:000 gives only Kashubian names. | hard_negatives[1] replaced p:gda_sk:05:000 -> p:gda_sk:03:000. The old node stated 'urbs Gyddannyzc' as the name recorded for the 997 Adalbert episode and therefore answered the question (a hard negative containing the answer); the new same-article, same-type node lists Kashubian names (Gduńsk, 'The Royal Polish City of Gdańsk') and contains neither the 997 record nor any Gyddanyzc spelling, so it is a genuine non-answering near-miss. Evidence, answer and question unchanged. |
| `qa-shadow-dev-37` | B | NONE (unaudited by Phase 2) | **approve** | p:great_zimbabwe:00:000 states it is the largest stone structure in precolonial Southern Africa; negative p:great_zimbabwe:03:000 says only 'some of the oldest and largest structures located in Southern Africa', a hedged near-miss that does not state the recorded distinction. | — |
| `qa-shadow-dev-38` | B | NONE (unaudited by Phase 2) | **approve** | p:hiv_aids:04:000 defines AIDS at a CD4+ count below 200 cells per microlitre; negatives cover clinical latency, elite controllers and the three infection stages, none giving a threshold. | — |
| `qa-shadow-dev-39` | B | NONE (unaudited by Phase 2) | **approve** | p:kyiv:03:000 derives the 1982 celebration from the traditional 482 CE founding; negatives are the foundation legends and the 968-1240 period, neither mentioning the anniversary. | — |
| `qa-shadow-dev-40` | B | NONE (unaudited by Phase 2) | **approve** | p:ludwig_van_beethoven:03:000 gives the November 1792 permanent move to Vienna; negative p:ludwig_van_beethoven:02:000 mentions 'move to Vienna in 1792' without the month, so it cannot yield the gold 'November 1792'. | — |
| `qa-shadow-dev-41` | B | NONE (unaudited by Phase 2) | **approve** | p:neutron_star:01:000 states the greater-than-8-solar-mass threshold for neutron-star potential; negatives give the remnant mass figure and the collapse limits, not the 8-solar-mass threshold (the competing 'between 10 or possibly more' in p:neutron_star:00:000 is a distractor, not the answer). | — |
| `qa-shadow-dev-42` | B | NONE (unaudited by Phase 2) | **approve** | p:operating_system:06:000 states a hypervisor runs a virtual machine; negatives are the embedded and real-time operating-system paragraphs, neither mentioning a hypervisor. | — |
| `qa-shadow-dev-43` | B | NONE (unaudited by Phase 2) | **approve** | p:silk_road:01:000 names Ferdinand von Richthofen as popularizing the term in 1877; negatives cover the network overview and the northern route, naming no popularizer. | — |
| `qa-shadow-dev-44` | B | NONE (unaudited by Phase 2) | **approve** | p:superconductivity:01:000 states superconductivity was discovered in solid mercury on April 8, 1911; negatives are the BCS-theory history and the magnet applications, neither naming a 1911 discovery material. | — |
| `qa-shadow-dev-45` | B | NONE (unaudited by Phase 2) | **approve** | Comparison with is_multi_hop=true is sound: p:acid:02:000 (Arrhenius, 1884, hydrogen cations) and p:acid:03:000 (Brønsted-Lowry, 1923, proton transfer) are both required to order the two concepts; negatives cover the 1923 Lewis concept and acid dissociation, which do not order Arrhenius against Brønsted. | — |
| `qa-shadow-dev-46` | B | NONE (unaudited by Phase 2) | **approve** | Comparison with is_multi_hop=true is sound: p:gda_sk:00:000 (486,492 at the Motława mouth) and p:zurich:00:000 (440,935, largest city in Switzerland) are both required and 486,492 > 440,935 gives Gdańsk; negatives give no population for either city. | — |
| `qa-shadow-dev-47` | B | NONE (unaudited by Phase 2) | **approve** | is_multi_hop=false is correct because the single atom p:hummingbird:02:000 carries both compared facts (bee hummingbird about 2 g, giant hummingbird largest at about twice the next largest), so one atom determines the comparison; negatives are the feet paragraph and the general description. | — |
| `qa-shadow-dev-48` | B | NONE (unaudited by Phase 2) | **approve** | Comparison with is_multi_hop=true is sound: p:superconductivity:01:000 (Onnes, solid mercury, 1911) and :05:000 (Josephson, supercurrent through an insulating layer, 1962) are both required and 1911 precedes 1962; negatives are the London equations and 2D materials, naming neither. | — |
| `qa-shadow-dev-49` | B | NONE (unaudited by Phase 2) | **approve** | The Phase 2 relabel is minimality-correct because p:jaguar_cars:00:000 alone names Jaguar as owned by Tata Motors, so a two-atom set would fail leave-one-out; noted for the orchestrator that this atom does not carry the Lyons/Walmsley descriptor and that the item is now a low-difficulty twin of qa-shadow-dev-08. | — |
| `qa-shadow-dev-50` | B | NONE (unaudited by Phase 2) | **approve** | Genuine two-hop: p:coronavirus:01:000 supplies the coiners and the Latin root corona, p:corona_australis:00:000 supplies the Southern Celestial Hemisphere constellation sharing that root; the beer and solar-corona negatives are different entities sharing the 'corona' token. | — |
| `qa-shadow-dev-51` | B | NONE (unaudited by Phase 2) | **approve** | Genuine two-hop: p:emancipation_proclamation:00:000 identifies Proclamation 95 as Lincoln's January 1, 1863 act, p:lincoln_motor_company:01:000 supplies both the Leland naming and the August 1917 founding; negatives give no founding month. | — |
| `qa-shadow-dev-52` | B | NONE (unaudited by Phase 2) | **approve** | Genuine two-hop: p:mount_vernon:07:000 fixes the 1752 remainder heir as the half-brother George already living at Mount Vernon, p:george_washington:04:000 supplies the January 6, 1759 marriage to Martha Dandridge Custis; negatives are D.C. population and Mount Vernon interiors. | — |
| `qa-shadow-dev-53` | B | NONE (unaudited by Phase 2) | **approve** | The Phase 2 relabel is correct: p:harvard_university:08:000 alone states the 209 acre main campus centered on Harvard Yard, and negative p:harvard_university:09:000 supplies the Allston 358-acre campus, a competing figure that does not answer a question about the main campus. | — |
| `qa-shadow-dev-54` | B | NONE (unaudited by Phase 2) | **approve** | Genuine two-hop: p:university_of_cambridge:00:000 supplies the 1209 founding by scholars leaving Oxford, p:cambridge_massachusetts:00:000 supplies the Middlesex County city named in its honour; negatives are an Oxford incident sentence and a Charles River basin sentence. | — |
| `qa-shadow-dev-55` | B | NONE (unaudited by Phase 2) | **approve** | Genuine two-hop: p:fifa_world_cup:02:000 identifies Uruguay as the two-time world champion named host, p:fifa_world_cup:02:001 supplies the final opponent Argentina; negatives cover tournament expansion and pre-FIFA history. | — |
| `qa-shadow-dev-56` | B | NONE (unaudited by Phase 2) | **approve** | Genuine two-hop: p:university_of_washington:04:000 supplies the March 2016 Capitol Hill-to-Husky-Station light rail premise, p:university_of_washington:00:000 supplies the main campus in the University District; each atom lacks the other's fact. | — |
| `qa-shadow-dev-57` | B | NONE (unaudited by Phase 2) | **approve** | Ambiguity is genuine: 'Jaguar' resolves to the animal described by Linnaeus in 1758 (p:jaguar:02:000) or the motor business founded as Swallow Sidecar Company in 1922 (p:jaguar_cars:01:000), two concrete corpus-grounded answers; negatives give neither year. | — |
| `qa-shadow-dev-58` | B | NONE (unaudited by Phase 2) | **approve** | Ambiguity is genuine: 'Washington' resolves to the federal city named on September 9, 1791 (p:washington_d_c:02:001) or Washington Territory named in 1853 (p:washington_state:01:000); negatives name no Washington and no naming year. | — |
| `qa-shadow-dev-59` | B | NONE (unaudited by Phase 2) | **approve** | Corpus-wide absence verified: no Plitvice node states an admission price; the only 'entrance' mentions are daily and hourly visitor caps (p:plitvice_lakes_national_park:18:001), and no currency figure appears anywhere in the article. | — |
| `qa-shadow-dev-61` | C | repair-minimality | **approve** | Genuine two-hop in one conjunctive set: p:virtual_reality:05:000 gives the 1978 Aspen Movie Map at MIT and no city, p:cambridge_massachusetts:00:000 gives MIT's 168-acre campus in Cambridge and no Aspen tour; negatives are VR precursors and Harvard admissions history. | — |
| `qa-shadow-dev-62` | C | repair-minimality + repair-alternatives | **approve** | Two genuinely different sufficient sets, both conjunctive: p:virtual_reality:04:000 fixes the 1968 HMD creator as Harvard Professor Ivan Sutherland, and 1636 is then reachable either via p:cambridge_massachusetts:00:000 or via p:harvard_university:00:000; the negatives are the Cambridge founding paragraph and the Aspen/MIT paragraph. | — |
| `qa-shadow-dev-63` | C | repair-minimality | **approve** | Genuine two-hop: p:washington_state:00:000 identifies the Pacific Northwest state named for the first president and its most populous city Seattle, p:university_of_washington:00:000 supplies the public research university founded 1861; negatives omit the founding year. | — |
| `qa-shadow-dev-64` | C | relabel-multihop | **approve** | The Phase 2 relabel is correct: p:george_washington:00:000 alone contains both the referent (namesakes include the national capital and the State of Washington) and the 1789 to 1797 term, so the singleton is sufficient and minimal. | — |
| `qa-shadow-dev-65` | C | repair-minimality + repair-alternatives | **approve** | Two genuinely different conjunctive sufficient sets: p:lincoln_motor_company:01:000 fixes Lincoln as Leland's first-ever presidential vote, and 1860 comes from either p:abraham_lincoln:00:000 or p:american_civil_war:02:000; negatives give no election year. | — |
| `qa-shadow-dev-66` | C | repair-minimality + repair-alternatives | **approve** | Two genuinely different conjunctive sufficient sets: p:abraham_lincoln:01:000 fixes the log-cabin-born Kentuckian as Lincoln, and the January 1, 1863 proclamation comes from either p:emancipation_proclamation:00:000 or p:emancipation_proclamation:00:001; negatives are Lincoln's romantic interests and the border states. | — |
| `qa-shadow-dev-67` | C | relabel-multihop | **approve** | The Phase 2 relabel is correct: p:george_washington:00:000 alone carries the first-president identity and 'led Patriot forces to victory in the American Revolutionary War'; negatives are the 1870 district population and the Mount Vernon acreage. | — |
| `qa-shadow-dev-68` | C | approve | **approve** | p:thermodynamics:02:000 states the first thermodynamic textbook was written in 1859 by William Rankine; negatives are the four laws and the zeroth law, naming no author. | — |
| `qa-shadow-dev-69` | C | approve | **approve** | p:virtual_reality:07:000 states Google introduced Street View in 2007; negatives are headset display technology and VRML, giving no Street View year. | — |
| `qa-shadow-dev-70` | C | approve | **approve** | p:corona_beer:01:000 states Anheuser-Busch InBev transferred all US distribution rights to Constellation Brands to satisfy DOJ antitrust concerns; negatives are the solar corona interior and Corona Australis boundaries. | — |
| `qa-shadow-dev-71` | C | approve | **approve** | p:solar_corona:01:000 states Maraldi recognised the eclipse aura as the Sun's in 1724; negatives are the corona definition and the coronavirus naming paragraph, neither naming a year for Maraldi. | — |
| `qa-shadow-dev-72` | C | approve | **approve** | p:corona_australis:01:000 states the four-letter abbreviations were repealed in 1955; negatives are the constellation lead and the Alfecca Meridiana naming paragraph, neither giving 1955. | — |
| `qa-shadow-dev-73` | C | repair-alternatives | **approve** | Both recorded singletons independently state the answer, in different passages: p:jaguar:00:000 'bites directly through the skull of mammalian prey between the ears' and p:jaguar:10:000 'bites mammalian prey directly through the skull between the ears'; negatives are the jaguar etymology and the Daimler factory history. | — |
| `qa-shadow-dev-74` | C | approve | **approve** | p:jaguar_supercomputer:00:000 names Tianhe-1A as the Chinese supercomputer taking the top TOP500 spot in late October 2010; negatives are the Jaguar upgrade history and the jaguar etymology. | — |
| `qa-shadow-dev-75` | C | repair-alternatives | **approve** | Both recorded singletons independently name Cybermorph as the pack-in game, in different passages (p:atari_jaguar:00:000 lead; p:atari_jaguar:17:000 game-library critique); negatives are the Atari 7800 sentence and the Jaguar supercomputer upgrades. | — |
| `qa-shadow-dev-76` | C | repair-alternatives | **approve** | Both recorded singletons independently give Lindum Colonia (p:lincolnshire:01:000 'derived from Lindum Colonia'; p:lincolnshire:00:000 'In the Roman era Lincoln was a major settlement, called Lindum Colonia'); negatives are Lincoln's 1831 move and the Proclamation's covered states. | — |
| `qa-shadow-dev-77` | C | approve | **approve** | p:lincoln_motor_company:32:000 states Lincoln adopted a greyhound as a hood ornament in 1927; negatives are the 1989-1990 sales years and the Ford division overview. | — |
| `qa-shadow-dev-78` | C | repair-alternatives | **approve** | All three recorded singletons independently give April 12, 1861 with the Fort Sumter firing (p:american_civil_war:04:000 'began on April 12, 1861, when Confederate forces opened fire on the Union-held Fort Sumter'; p:american_civil_war:00:000 'the Confederacy bombarded Fort Sumter'; p:abraham_lincoln:15:000 'On April 12, 1861, Confederate forces fired on Union troops at Fort Sumter'); negatives are secession politics and the battles overview. | — |
| `qa-shadow-dev-79` | C | approve | **approve** | p:washington_d_c:03:000 states British forces occupied Washington on August 24, 1814; negatives are the Continental Congress capitals list and the Alexandria decline, neither giving the date. | — |
| `qa-shadow-dev-80` | C | repair-alternatives | **approve** | Both recorded singletons independently give 1781 (p:george_washington:00:000 'decisive victory ... at Yorktown in 1781'; p:george_washington:13:000 the August 19, 1781 march and October 19, 1781 surrender); negatives are Washington's birth and the mansion construction. | — |
| `qa-shadow-dev-81` | C | repair-alternatives | **approve** | Both recorded singletons independently name Tacoma and Bothell (p:university_of_washington:00:000 'satellite campuses in nearby cities of Tacoma and Bothell'; p:university_of_washington:04:000 'additional campuses in Bothell and Tacoma'); negatives are the 1854 Stevens recommendation and the 1909 exposition. | — |
| `qa-shadow-dev-82` | C | approve | **approve** | p:washington_state:00:000 states Mount Rainier is the state's highest elevation at 4,389 m; negatives are the Kennewick Man paragraph and the Tacoma smelters, giving no elevation. | — |
| `qa-shadow-dev-83` | C | repair-alternatives | **approve** | Both recorded singletons independently name the Dnieper (p:kyiv:00:000 'it straddles both banks of the Dnieper River'; p:kyiv:10:000 'today Kyiv is on both sides of the Dnieper'); negatives are the Kyi etymology and the founding-date paragraph. | — |
| `qa-shadow-dev-84` | C | repair-minimality | **approve** | Comparison with is_multi_hop=true is sound: p:virtual_reality:06:000 (Sega VR headset for the Mega Drive, 1991) and :08:000 (Rift first shown at E3, 2012) are both required and 1991 precedes 2012; negatives cover the 2000s VR lull and headset displays. | — |
| `qa-shadow-dev-85` | C | repair-minimality + repair-alternatives | **approve** | Comparison with is_multi_hop=true is sound, with two genuine Harvard-acreage routes: p:harvard_university:08:000 (209 acre main campus) or :00:000 ('a 209 acre in Cambridge'), each paired with p:university_of_washington:00:000 (700 acre main campus), and 700 > 209 gives the University of Washington; negative p:harvard_university:09:000 supplies the Allston 358-acre campus, a competing figure for a different campus. | — |
| `qa-shadow-dev-86` | C | repair-minimality + repair-alternatives | **approve** | Comparison with is_multi_hop=true is sound across three conjunctive sets: the capital district's 1790 Residence Act comes from p:washington_d_c:00:000 or p:washington_d_c:02:000, and the 1889 42nd-state admission from p:washington_state:05:000 or p:washington_state:00:000, in every pairing both atoms are required and 1790 precedes 1889. | — |
| `qa-shadow-dev-87` | C | approve | **approve** | Ambiguity is genuine: 'the capital of Washington' resolves to Olympia's role as the state capital (p:washington_state:00:000) or Washington's role as the federal capital city (p:washington_d_c:00:000), two concrete corpus-grounded answers; negatives are the Cascade climate and the Mount Vernon land purchase. | — |
| `qa-shadow-dev-88` | C | approve | **approve** | Ambiguity is genuine: the earliest use is either Artaud's French 'la réalité virtuelle' in 1938 (t:virtual_reality:01:000:02) or Broderick's English term in 1982 (t:virtual_reality:01:000:05), both stated verbatim in the corpus; negatives are simulation-based VR and the perspective/stereoscope precursors. | — |
| `qa-shadow-dev-89` | C | approve | **approve** | Corpus-wide absence verified: no node pairs the Sensorama with any price; the article's monetary figures attach to Virtuality systems, the Oculus purchase and a Gloveone Kickstarter, and p:virtual_reality:04:000 describes the Sensorama only as a 1962 mechanical device. | — |
| `qa-shadow-dev-90` | C | approve | **approve** | Corpus-wide absence verified: no node states a numerical efficiency computed by Carnot himself; the only numerical Carnot efficiency is p:steam_engine:32:000's 'about 64%' for a modern coal-fired station, and the repaired absent_reason states this accurately. | — |

## Systemic observations (no repair made — recorded for the orchestrator)

1. **Batch B left no `audit_decision` at all.** `docs/qa-shadow-dev-audit-ledger-BATCH-B.md`
   reports verdicts for 31-59 and claims all 29 "now carry provenance audit fields
   `{auditor, auditor_model}`", but no one of those 29 files has an `audit_decision` field.
   They were unaudited in the record, so this pass audited all 29 from the corpus. Five of
   them (45, 46, 48, 49, 53) do carry the repairs Batch B's table claims — the merged
   conjunctive sets on 45, 46 and 48 are present and correct, and 49 and 53 carry the
   multihop -> factoid relabels — so Batch B's repairs landed; only its recorded outcome did not.
2. **`qa-shadow-dev-49` is now a low-difficulty twin of `qa-shadow-dev-08`.** Both have the
   answer `Tata Motors` and the same single evidence atom `p:jaguar_cars:00:000`. Batch B
   relabelled 49 multihop -> factoid on the ground that `p:jaguar_cars:00:000` alone
   determines the answer, which makes the retained atom minimal and correct — but that
   same atom never names William Lyons or William Walmsley, the descriptor 49's question
   uses to identify its subject. The relabel is minimality-correct and the item is sound, so
   it is approved; the question's premise is simply no longer grounded by its evidence and
   the item no longer discriminates from 08. Flagged, not repaired: restoring the two-atom
   set would fail leave-one-out, and reclassifying is Phase 2 / orchestrator scope.
3. **`qa-shadow-dev-37` carries a near-miss negative.** `p:great_zimbabwe:03:000` says the
   ruins are "some of the oldest and largest structures located in Southern Africa" against
   the gold "the largest stone structure in precolonial Southern Africa". It is hedged and
   does not state the recorded distinction, so it is an acceptable `sibling_paragraph`
   negative; it is the closest thing in the 89 to the recurring leak defect.
4. **`qa-shadow-dev-40` and `qa-shadow-dev-41` carry partial-credit negatives.**
   `p:ludwig_van_beethoven:02:000` gives "move to Vienna in 1792" without the month against
   gold `November 1792`, and `p:neutron_star:00:000` gives a competing "between 10 or
   possibly more" initial mass against gold `greater than 8`. Neither states the gold
   string, so neither answers; both are recorded as near-misses deliberately.
5. **Ambiguous items encode the ambiguity in `answer_text`.** Items 27, 28, 57, 58, 87, 88
   put a prose disjunction in `labels.answer_text` and the concrete answers in
   `labels.readings`. That is the existing convention across the split and was left alone,
   but any scoring code that compares `answer_text` to model output will score all six
   wrong. Worth an orchestrator decision before the split is used.
