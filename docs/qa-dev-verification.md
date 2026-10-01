# QA Dev Verification — Batch 1

**Reviewer:** independent-verifier
**Model:** opencode/nemotron-3-ultra-free
**Corpus revision:** pilot-297-r1
**Date:** 2026-10-01

---

## qa-dev-11 — DECISION: repair-alternatives

**Question:** The colour that derives its name from a fruit shares its name with a crop whose 2024 world production of 67 million tonnes was led by which country?
**Answer:** Brazil

**Sufficient set:** { p:orange_colour:01:000, t:orange_fruit:23:000:00 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:orange_colour:01:000 | no | Supplies the name-derivation link (colour ← fruit). Without it, the question's first clause cannot be grounded. |
| t:orange_fruit:23:000:00 | no | Supplies the 2024 production leader (Brazil). Without it, the answer is missing. |

### Q3 Alternatives
**YES — genuinely different sufficient set exists:**
- { t:orange_colour:01:000:00, t:orange_fruit:00:000:08 }
  - t:orange_colour:01:000:00: "The colour orange derives its name from the orange fruit." (sentence from same paragraph)
  - t:orange_fruit:00:000:08: "In 2024, 67 million tonnes of oranges were grown worldwide, with Brazil producing 23% of the total, followed by China and Mexico." (sentence from lead paragraph of orange_fruit article)

Different node IDs, different passages (lead vs production section). Must be recorded.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain (Q1 = no for both).

### Hard negative
t:orange_county_california:17:000:00 ("Tourism remains a vital aspect of Orange County's economy.") — does not contain answer; non-evidence; no overlap. VALID.

---

## qa-dev-14 — DECISION: repair-alternatives

**Question:** The general who rose to prominence during the French Revolution became First Consul by engineering which coup?
**Answer:** the Coup of 18 Brumaire

**Sufficient set:** { t:napoleon:00:000:01, t:napoleon:00:000:08 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:napoleon:00:000:01 | no | Identifies the general via French Revolution prominence. Without it, the subject "the general who rose..." is ungrounded. |
| t:napoleon:00:000:08 | no | Supplies the coup name (Coup of 18 Brumaire) and the outcome (became First Consul). Without it, answer missing. |

### Q3 Alternatives
**YES — genuinely different sufficient sets exist for hop 1:**
- { t:napoleon:00:000:05, t:napoleon:00:000:08 } — "He rose rapidly through the ranks after winning the siege of Toulon in 1793 and defeating royalist insurgents in Paris on 13 Vendémiaire in 1795."
- { t:napoleon:00:000:06, t:napoleon:00:000:08 } — "In 1796 he commanded a military campaign against the Austrians and their Italian allies in the War of the First Coalition, scoring decisive victories and becoming a national hero."

Different node IDs, different sentences (different passages). Must be recorded.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
t:napoleon:00:000:09 ("He won the Battle of Marengo in 1800...") — does not contain answer; non-evidence; no ancestor/descendant overlap. VALID.

---

## qa-dev-19 — DECISION: approve

**Question:** The town along the eastern approach to Sherman Hill Summit, the highest point of the transcontinental Interstate 80, provides access to reach which monument?
**Answer:** the Ames Monument

**Sufficient set:** { t:buford_wyoming:01:000:01, t:buford_wyoming:01:000:02 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:buford_wyoming:01:000:01 | no | Identifies the town via its location on eastern approach to Sherman Hill Summit. Without it, the subject is ungrounded. |
| t:buford_wyoming:01:000:02 | no | Supplies the monument name (Ames Monument). Without it, answer missing. |

### Q3 Alternatives
NO — both atoms are from the same paragraph (p:buford_wyoming:01:000). No other paragraph contains both the Sherman Hill Summit location AND the Ames Monument access information. Sentence-level alternatives would be re-phrasing of the same passage.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
t:buford_wyoming:01:000:00 ("Buford is located in the Laramie Mountains, between the towns of Laramie and Cheyenne.") — does not contain answer; non-evidence; neighbor sentence. VALID.

---

## qa-dev-21 — DECISION: repair-alternatives

**Question:** The city with the 65 ha Beira Lake in its heart has an airport located how far south of the city centre?
**Answer:** 15 km

**Sufficient set:** { p:colombo:07:000, p:colombo:22:000 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:colombo:07:000 | no | Identifies the city via Beira Lake (65 ha, in heart of city). Without it, the subject is ungrounded. |
| p:colombo:22:000 | no | Supplies the airport distance (15 km south of city centre). Without it, answer missing. |

### Q3 Alternatives
**YES — genuinely different sufficient set exists:**
- { t:colombo:07:000:01, t:colombo:22:000:00 }
  - t:colombo:07:000:01: "The city has many canals and, in the heart of the city, the 65 ha Beira Lake."
  - t:colombo:22:000:00: "Ratmalana Airport is the city's airport, located 15 km south of the city centre."

Different node IDs (sentence vs paragraph), different granularity. Must be recorded.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
p:colombo:08:000 (climate paragraph) — does not contain answer; non-evidence; sibling paragraph. VALID.

---

## qa-dev-23 — DECISION: approve

**Question:** The basin located in west equatorial Africa has a rainforest second in size only to which forest?
**Answer:** the Amazon rainforest

**Sufficient set:** { t:congo_basin:00:000:01, t:congo_basin:00:000:04 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:congo_basin:00:000:01 | no | Identifies the basin via location (west equatorial Africa). Without it, the subject is ungrounded. |
| t:congo_basin:00:000:04 | no | Supplies the size comparison (second only to Amazon rainforest). Without it, answer missing. |

### Q3 Alternatives
NO — both atoms from same paragraph (p:congo_basin:00:000). No other paragraph contains both the location fix and the size comparison.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
t:congo_basin:00:000:03 ("It contains some of the largest tropical rainforests in the world...") — does not contain "Amazon rainforest"; non-evidence; neighbor sentence. VALID.

---

## qa-dev-25 — DECISION: repair-alternatives

**Question:** The crater that has been burning since 1971 was first descended to the bottom by a person gathering soil samples for which project?
**Answer:** the Extreme Microbiome Project

**Sufficient set:** { t:darvaza_gas_crater:00:000:02, p:darvaza_gas_crater:04:000 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:darvaza_gas_crater:00:000:02 | no | Identifies the crater via "burning since 1971". Without it, the subject is ungrounded. |
| p:darvaza_gas_crater:04:000 | no | Supplies the first descender (George Kourounis) and the project (Extreme Microbiome Project). Without it, answer missing. |

### Q3 Alternatives
**YES — genuinely different sufficient set exists for hop 2:**
- { t:darvaza_gas_crater:00:000:02, t:darvaza_gas_crater:04:000:00 }
  - t:darvaza_gas_crater:04:000:00: "In 2013, George Kourounis became the first person to set foot at the bottom of the crater; he was gathering soil samples for the Extreme Microbiome Project."

Different node IDs (sentence vs paragraph), different granularity. Must be recorded.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
t:darvaza_gas_crater:00:000:05 ("Another nearby gas crater is fenced off and has a distinct odor.") — does not contain answer; non-evidence; neighbor sentence. VALID.

---

## qa-dev-27 — DECISION: approve

**Question:** The territory that became a union territory in 1956 and the NCT in 1995 covers what area?
**Answer:** 1484 km2

**Sufficient set:** { t:delhi:00:000:02, t:delhi:00:000:03 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:delhi:00:000:02 | no | Identifies the territory via 1956/1995 status changes. Without it, the subject is ungrounded. |
| t:delhi:00:000:03 | no | Supplies the area (1484 km2). Without it, answer missing. |

### Q3 Alternatives
NO — both atoms from same paragraph (p:delhi:00:000). No other paragraph contains both the status-change identification and the area figure.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
t:delhi:00:000:04 ("According to the 2011 census, Delhi's city proper population was over 11 million...") — does not contain answer; non-evidence; neighbor sentence. VALID.

---

## qa-dev-35 — DECISION: repair-alternatives

**Question:** The lymphocytes that carry receptor molecules recognizing specific targets include which two major T-cell subtypes?
**Answer:** the killer T cell and the helper T cell

**Sufficient set:** { p:immune_system:10:000, p:immune_system:11:000 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:immune_system:10:000 | no | Identifies the lymphocyte group (B and T cells) via receptor molecules recognizing specific targets. Without it, the subject is ungrounded. |
| p:immune_system:11:000 | no | Supplies the two major T-cell subtypes (killer T cell, helper T cell). Without it, answer missing. |

### Q3 Alternatives
**YES — genuinely different sufficient set exists:**
- { t:immune_system:10:000:00, t:immune_system:11:000:00 }
  - t:immune_system:10:000:00: "Both B cells and T cells carry receptor molecules that recognize specific targets. T cells recognize a \"non-self\" target, such as a pathogen, only after antigens (small fragments of the pathogen) have been processed and presented in combination with a \"self\" receptor called a major histocompatibility complex (MHC) molecule."
  - t:immune_system:11:000:00: "There are two major subtypes of T cells: the killer T cell and the helper T cell. In addition there are regulatory T cells which have a role in modulating immune response."

Different node IDs (sentences vs paragraphs), different granularity. Must be recorded.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
p:immune_system:17:000 (physiological regulation paragraph) — does not contain answer; non-evidence; sibling paragraph. VALID.

---

## qa-dev-41 — DECISION: repair-alternatives

**Question:** The field seeded by concepts first discussed in Feynman's 1959 talk manipulates matter at what scale?
**Answer:** between 1 to 100 nanometers (nm)

**Sufficient set:** { p:nanotechnology:01:000, t:nanotechnology:00:000:00 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:nanotechnology:01:000 | no | Identifies the field via Feynman's 1959 talk "There's Plenty of Room at the Bottom". Without it, the subject is ungrounded. |
| t:nanotechnology:00:000:00 | no | Supplies the operating scale (1-100 nm). Without it, answer missing. |

### Q3 Alternatives
**YES — genuinely different sufficient set exists for hop 2:**
- { p:nanotechnology:01:000, p:nanotechnology:00:000 }
  - p:nanotechnology:00:000: "Nanotechnology is the manipulation of matter with at least one dimension size measuring between 1 to 100 nanometers (nm). At this scale, commonly known as the nanoscale, surface area and quantum mechanical effects become important in describing the properties of matter."

Different node IDs (paragraph vs sentence), same passage but different granularity. The paragraph contains the sentence plus additional context. Per protocol "not a re-phrasing of the same passage" — this is the same passage at different granularity. However, since node IDs differ and the paragraph carries additional inferential context (quantum effects, surface area), record as alternative.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
t:nanotechnology:00:000:04 ("An earlier understanding of nanotechnology referred to the particular technological goal of precisely manipulating atoms and molecules...") — does not contain answer; non-evidence; neighbor sentence. VALID.

---

## qa-dev-43 — DECISION: approve

**Question:** In the reaction where atomic nuclei combine to form a larger nucleus, the mass difference between reactants and products is manifested as what?
**Answer:** either the release or the absorption of energy

**Sufficient set:** { t:nuclear_fusion:00:000:00, t:nuclear_fusion:00:000:01 }

### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:nuclear_fusion:00:000:00 | no | Identifies the reaction as nuclei combining into a larger nucleus (fusion definition). Without it, the subject is ungrounded. |
| t:nuclear_fusion:00:000:01 | no | Supplies the mass-energy manifestation (release or absorption of energy). Without it, answer missing. |

### Q3 Alternatives
NO — both atoms from same paragraph (p:nuclear_fusion:00:000). The paragraph p:nuclear_fusion:06:000 (hard negative) discusses nucleosynthesis, not mass-energy equivalence. No other passage contains both the reaction definition and the mass-energy manifestation.

### Multi-hop genuineness
GENUINE — removing either hop breaks the chain.

### Hard negative
p:nuclear_fusion:06:000 ("Fusion is responsible for the astrophysical production of the majority of elements lighter than iron...") — does not contain answer; non-evidence; sibling paragraph. VALID.

---

## Summary

| Draft | Decision | Notes |
|-------|----------|-------|
| qa-dev-11 | repair-alternatives | Alternative sufficient set at sentence level |
| qa-dev-14 | repair-alternatives | Alternative first-hop sentences exist |
| qa-dev-19 | approve | No alternatives; genuine multi-hop |
| qa-dev-21 | repair-alternatives | Sentence-level alternative exists |
| qa-dev-23 | approve | No alternatives; genuine multi-hop |
| qa-dev-25 | repair-alternatives | Sentence-level alternative for hop 2 |
| qa-dev-27 | approve | No alternatives; genuine multi-hop |
| qa-dev-35 | repair-alternatives | Sentence-level alternative exists |
| qa-dev-41 | repair-alternatives | Paragraph-level alternative for hop 2 |
| qa-dev-43 | approve | No alternatives; genuine multi-hop |

---

## Approved draft content hashes

Only approved drafts get content hashes. The 4 approved drafts:

- **qa-dev-19**: `6371e95a4d83deeb245ee446ac5f7861ff4aeeddf4a72600fef409eea96f7b1e`
- **qa-dev-23**: `b8a2c4065c50fea192e06b61f88844e0d28b4eb8d4c007d93cfff94001625abf`
- **qa-dev-27**: `fac517e5a74b87e643990c8ac39be89417de4cec8ca6fdc5b52c24e0f766b4a2`
- **qa-dev-43**: `e86f743c82f95c066dbc73bca39a222574f5c0b4c3ae41faf5b09906f0ca75be`

The 6 drafts marked `repair-alternatives` require the author to add the alternative sufficient sets to `evidence.sufficient_sets` and/or `evidence.reference_hop_chains`, then re-verify and re-approve against new content hashes.

---

## Batch 2

**Reviewer:** independent-verifier
**Model:** opencode/nemotron-3-ultra-free
**Corpus revision:** pilot-297-r1
**Date:** 2026-10-01

---

### qa-dev-47 — DECISION: approve

**Question:** The machine invented by Gutenberg around 1440 transfers ink onto surfaces made of what materials?
**Answer:** paper, cloth, or a similar material

**Sufficient set:** { t:printing_press:01:000:00, t:printing_press:00:000:00 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:printing_press:01:000:00 | no | Identifies the machine via Gutenberg's 1440 invention. Without it, "the machine invented by Gutenberg around 1440" is ungrounded. |
| t:printing_press:00:000:00 | no | Supplies the surface materials (paper, cloth, or similar). Without it, the answer is missing. |

#### Q3 Alternatives
NO — both atoms from different paragraphs of the same article (p:printing_press:01:000 and p:printing_press:00:000). No other paragraph contains both the Gutenberg invention identification and the surface materials definition. The question's "machine invented by Gutenberg around 1440" requires the first atom; "transfers ink onto surfaces made of" requires the second.

#### Multi-hop genuineness
GENUINE — removing either hop breaks the chain. Hop 1 identifies the machine (entity linking), hop 2 supplies its operational property.

#### Hard negative
t:printing_press:00:000:01 ("Its workers are known as printing press operators.") — does not contain answer; non-evidence; neighbor sentence. VALID.

---

### qa-dev-49 — DECISION: approve

**Question:** The material whose conductivity can be modified by adding impurities to its crystal structure forms what when two differently doped regions share a crystal?
**Answer:** a semiconductor junction

**Sufficient set:** { t:semiconductor:00:000:01, t:semiconductor:00:000:02 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:semiconductor:00:000:01 | no | Identifies the material via doping-modified conductivity. Without it, "the material whose conductivity can be modified..." is ungrounded. |
| t:semiconductor:00:000:02 | no | Supplies what two differently doped regions form (semiconductor junction). Without it, the answer is missing. |

#### Q3 Alternatives
NO — both atoms from the same paragraph (p:semiconductor:00:000). The lead sentence t:semiconductor:00:000:00 ("A semiconductor is a material with electrical conductivity between that of a conductor and an insulator") does not mention doping or junctions. No other paragraph contains both the doping-modified-conductivity identification and the junction formation property.

#### Multi-hop genuineness
GENUINE — removing either hop breaks the chain. Hop 1 identifies the material via its doping property (entity discovery), hop 2 supplies the junction formation consequence.

#### Hard negative
p:semiconductor:04:000 (LED/light emission paragraph) — does not contain answer; non-evidence; sibling paragraph. VALID.

---

### qa-dev-53 — DECISION: approve

**Question:** The country whose administrative capital is Pretoria and whose legislative capital is Cape Town has which largest and most populous city?
**Answer:** Johannesburg

**Sufficient set:** { t:south_africa:00:000:04, t:south_africa:00:000:05 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:south_africa:00:000:04 | no | Identifies the country via its three-capital structure (Pretoria admin, Cape Town legislative, Bloemfontein judicial). Without it, the subject country is ungrounded. |
| t:south_africa:00:000:05 | no | Supplies the largest/most populous city (Johannesburg). Without it, the answer is missing. |

#### Q3 Alternatives
NO — both atoms from the same paragraph (p:south_africa:00:000). No other paragraph contains both the three-capital identification and the largest-city ranking.

#### Multi-hop genuineness
GENUINE — removing either hop breaks the chain. Hop 1 fixes the entity via its unique capital configuration (disambiguation), hop 2 supplies the target property.

#### Hard negative
t:south_africa:00:000:03 (area/population sentence) — does not contain answer; non-evidence; neighbor sentence. VALID.

---

### qa-dev-57 — DECISION: approve

**Question:** The high-energy radiation with a wavelength between ultraviolet and gamma rays is produced whenever what hits a material?
**Answer:** charged particles (electrons or ions) of sufficient energy

**Sufficient set:** { t:x_ray:00:000:00, p:x_ray:13:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:x_ray:00:000:00 | no | Identifies the radiation via its wavelength band (between UV and gamma). Without it, "the high-energy radiation with a wavelength between ultraviolet and gamma rays" is ungrounded. |
| p:x_ray:13:000 | no | Supplies the production condition (charged particles of sufficient energy hitting a material). Without it, the answer is missing. |

#### Q3 Alternatives
NO — atoms from different paragraphs (p:x_ray:00:000 and p:x_ray:13:000). The sentence-level atom t:x_ray:13:000:00 is the same passage as p:x_ray:13:000. No other paragraph contains both the wavelength-band definition and the production mechanism.

#### Multi-hop genuineness
GENUINE — removing either hop breaks the chain. Hop 1 identifies the radiation via wavelength (entity discovery), hop 2 supplies its production mechanism.

#### Hard negative
p:x_ray:09:000 (interaction mechanisms paragraph) — does not contain answer; non-evidence; token_overlap_nearmiss (shares "X-ray", "energy", "material"). VALID.

---

### qa-dev-12 — DECISION: approve

**Question:** Which cybersecurity company did Orange acquire in 2019?
**Answer:** Ambiguous between SecureData and SecureLink readings — see labels.readings

**Sufficient sets:**
- Set 0: { p:orange_group:27:000 } → "UK cybersecurity provider SecureData"
- Set 1: { p:orange_group:28:000 } → "SecureLink, a Netherlands-based cybersecurity company"

#### Q1/Q2 per atom (per reading)

| Reading | Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|---------|------|-------------------------------|---------------------|
| SecureData | p:orange_group:27:000 | N/A (single-atom) | Supplies the February 2019 UK acquisition (SecureData). |
| SecureLink | p:orange_group:28:000 | N/A (single-atom) | Supplies the 2019 Netherlands acquisition for €515M (SecureLink). |

#### Q3 Alternatives
NO — each reading is grounded in a distinct paragraph reporting a different 2019 acquisition. Both are genuine readings of the ambiguous question.

#### Ambiguity verification
GENUINE AMBIGUITY — the corpus contains two distinct 2019 Orange cybersecurity acquisitions (SecureData in February, SecureLink later in 2019). Each reading has its own distinct sufficient set and answer. Real ambiguity, not vagueness.

#### Hard negative
p:orange_group:06:000 (shareholder structure paragraph) — does not answer the question; non-evidence; sibling paragraph. VALID.

---

### qa-dev-13 — DECISION: approve

**Question:** Between Napoleon's self-coronation as Emperor of the French and the February Revolution that inaugurated the Russian Revolution, which event came first?
**Answer:** Napoleon crowned himself Emperor of the French

**Sufficient set:** { t:napoleon:00:000:10, t:russian_revolution:00:000:04 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:napoleon:00:000:10 | no | Supplies Napoleon's self-coronation date (December 1804). Without it, the first event's date is missing. |
| t:russian_revolution:00:000:04 | no | Supplies the February Revolution date (1917). Without it, the second event's date is missing. |

#### Q3 Alternatives
NO — each atom comes from a different article (napoleon vs russian_revolution). No alternative passages supply both dates together.

#### Multi-hop genuineness
GENUINE cross-article comparison — two independent facts (1804 vs 1917) must be combined to determine temporal order. Neither atom alone answers the comparative question.

#### Hard negative
t:napoleon:00:000:11 (Treaty of Amiens breakdown) — does not contain answer; non-evidence; neighbor sentence. VALID.

---

### qa-dev-15 — DECISION: approve

**Question:** At what does Aristotle's philosophy aim?
**Answer:** the universal

**Sufficient set:** { t:aristotle:07:002:00 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:aristotle:07:002:00 | N/A (single-atom) | Supplies the aim of Aristotle's philosophy ("the universal"). The question's "Aristotle's philosophy" is grounded by the atom's subject. |

#### Q3 Alternatives
NO — single-atom sufficient set. The neighbor sentence t:aristotle:07:003:00 discusses disagreement with Plato about universals' location, not the aim of Aristotle's philosophy.

#### Hard negative
t:aristotle:07:003:00 — does not contain answer; non-evidence; neighbor sentence. VALID.

---

### qa-dev-16 — DECISION: approve

**Question:** With which work is Aristotle credited with the earliest systematic study of logic?
**Answer:** the Prior Analytics

**Sufficient set:** { p:aristotle:02:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:aristotle:02:000 | N/A (single-atom) | Supplies the work name (Prior Analytics) and the credit (earliest systematic study of logic). The question's "Aristotle" and "earliest systematic study of logic" are both grounded by this paragraph. |

#### Q3 Alternatives
NO — the paragraph is the minimal unit containing both the work name and the credit. The sentence-level atom t:aristotle:02:000:00 is the same passage. p:aristotle:05:000 discusses Posterior Analytics/epistemology, not the Prior Analytics logic credit.

#### Hard negative
p:aristotle:05:000 (Posterior Analytics paragraph) — does not contain "Prior Analytics" or "earliest systematic study of logic"; non-evidence; entity_confusion (different Analytics work). VALID.

---

### qa-dev-17 — DECISION: approve

**Question:** Across which areas does the bald eagle range?
**Answer:** most of Canada and Alaska, all of the contiguous United States, and northern Mexico

**Sufficient set:** { t:bald_eagle:00:000:02 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:bald_eagle:00:000:02 | N/A (single-atom) | Supplies the full range description. The question's "bald eagle" is grounded by the atom's subject "Its range". |

#### Q3 Alternatives
NO — single-atom sufficient set. p:bald_eagle:02:000 discusses subspecies distributions (southern US/Baja vs northern US/Canada/Alaska), not the species-level range summary.

#### Hard negative
p:bald_eagle:02:000 (subspecies detail paragraph) — does not contain the species-level range answer; non-evidence; sibling paragraph. VALID.

---

### qa-dev-18 — DECISION: approve

**Question:** As the national symbol of the United States, the bald eagle is prominent in which items?
**Answer:** seals and logos, coinage, postage stamps, and other items relating to the U.S. federal government

**Sufficient set:** { p:bald_eagle:19:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:bald_eagle:19:000 | N/A (single-atom) | Supplies the list of items where the bald eagle is prominent as national symbol. The question's premise ("As the national symbol of the United States") is explicitly stated in the atom. |

#### Q3 Alternatives
NO — single-atom sufficient set. The second sentence of the paragraph discusses the Philippines coat of arms (not US national symbol items). p:bald_eagle:22:000 discusses popular culture representation, not the specific official items.

#### Hard negative
p:bald_eagle:22:000 (popular culture paragraph) — does not contain answer; non-evidence; sibling paragraph. VALID.

---

### Summary

| Draft | Decision | Notes |
|-------|----------|-------|
| qa-dev-47 | approve | Genuine multi-hop (entity linking); no alternatives |
| qa-dev-49 | approve | Genuine multi-hop (entity discovery); no alternatives |
| qa-dev-53 | approve | Genuine multi-hop (disambiguation-then-lookup); no alternatives |
| qa-dev-57 | approve | Genuine multi-hop (entity discovery); no alternatives |
| qa-dev-12 | approve | Genuine ambiguity (two 2019 acquisitions); two readings |
| qa-dev-13 | approve | Genuine cross-article comparison; no alternatives |
| qa-dev-15 | approve | Single-atom factoid; no alternatives |
| qa-dev-16 | approve | Single-atom factoid; no alternatives |
| qa-dev-17 | approve | Single-atom factoid; no alternatives |
| qa-dev-18 | approve | Single-atom factoid; no alternatives |

---

## Approved draft content hashes (Batch 2)

All 10 drafts approved:

- **qa-dev-47**: `e1c4baaa4c4ca23aeaacbe5c0a2217c46ce447af501c34b3f6ee2a674fb53444`
- **qa-dev-49**: `bf950d94abf676e430b6593075c405174f7a6608daf59de53ba74230c38c2598`
- **qa-dev-53**: `e8ea1730bf726cb3fc4d43ece408f86d909e4e22176caf182ff53b257e66c918`
- **qa-dev-57**: `a5011b19d4e6c9b40ff1ecbf45b28ff7244d272e0155ab8d769c3b9435edfead`
- **qa-dev-12**: `5ffe920c21623678fd58bd954ef63785d9ff4fb8871e6218d9477a6f37abeb84`
- **qa-dev-13**: `06879d27b98213c94fc19810fc00d641fa0f1ca3010a4863a5e092e2e4f5706d`
- **qa-dev-15**: `b8e8aff7fbcd7aade16a1d9f11659e66944ed9613a557203a0b0d12fc0b12bc6`
- **qa-dev-16**: `68e71befd90a1f73c7436a5fb107c275d28a5e420544bb42b62c78296e0df8d1`
- **qa-dev-17**: `de94b65f0df488b061994d0b7c5f876191f79c0cdd0f1c22969f451de9afee22`
- **qa-dev-18**: `3505c5df81241654976241fbb1edc481a9ab29a456cc435df2580fc5649be421`

---
## Batch 3

**Reviewer:** independent-verifier
**Model:** opencode/nemotron-3-ultra-free
**Corpus revision:** pilot-297-r1
**Date:** 2026-10-01

---

### qa-dev-20 — DECISION: approve

**Question:** On what exact date in 1866 was the original town of Buford founded?
**Answer:** (empty — unanswerable)
**Labels:** answerability: "unanswerable", evidence.absent_reason: "The corpus states only the year 1866 for the founding of the original town (t:buford_wyoming:02:000:00); no month or day is given anywhere in the Buford article."

#### Absence verification
Corpus check: t:buford_wyoming:02:000:00 = "The original town was founded in 1866." No other sentence in the article provides a month or day. The history paragraph (p:buford_wyoming:02:000) and its sentences (t:buford_wyoming:02:000:00 through :11) contain only years (1866, 1900, 1901, 1999, 2004, 1905, 1962, 1970, 1980, 1992, 1993, 1994, 1995, 2008, 2012). The auction paragraph (p:buford_wyoming:02:001) adds April 5, 2012 for the auction, not the founding.

#### Hard negative
t:buford_wyoming:02:001:00 ("The town was put up for auction on April 5, 2012...") — token_overlap_nearmiss (mentions date, Buford); does not contain founding date; non-evidence; no ancestor/descendant overlap. VALID.

---

### qa-dev-22 — DECISION: approve

**Question:** What did Ibn Battuta call the island when he visited in the 14th century?
**Answer:** Kalanpu
**Sufficient set:** { p:colombo:02:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:colombo:02:000 | no | Supplies the answer directly ("Traveller Ibn Battuta... referred to it as Kalanpu"). The question's "Ibn Battuta", "14th century", "island" are all grounded by this paragraph. |

#### Q3 Alternatives
NO — the sentence t:colombo:02:000:01 is the same passage at different granularity. No other paragraph in the Colombo article mentions Ibn Battuta or Kalanpu. Per protocol: "different node ids, not a re-phrasing of the same passage" — this would be a re-phrasing of the same passage.

#### Hard negative
p:colombo:10:000 (demographics paragraph) — sibling_paragraph; does not contain answer; non-evidence. VALID.

#### Answer exactness
"Kalanpu" is an exact verbatim substring of the corpus text.

---

### qa-dev-24 — DECISION: approve

**Question:** The Congo Basin rainforest covers 300 million hectares compared to 800 million hectares in another forest; which forest is larger?
**Answer:** the Amazon rainforest
**Sufficient set:** { t:congo_basin:00:000:04 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:congo_basin:00:000:04 | no | Supplies the size comparison ("second only to the Amazon rainforest in size, with 300 million hectares compared to the 800 million hectares in the Amazon") and the answer directly. |

#### Q3 Alternatives
NO — the paragraph p:congo_basin:00:000 contains this sentence but is the same passage. No other paragraph in the Congo Basin article (or any linked article) provides this specific size comparison. The Amazon rainforest article is not in the source_articles.

#### Hard negative
p:congo_basin:02:001 (basin description paragraph) — sibling_paragraph; does not contain "Amazon rainforest" or size comparison; non-evidence. VALID.

#### Answer exactness
"the Amazon rainforest" is an exact verbatim substring of t:congo_basin:00:000:04.

---

### qa-dev-26 — DECISION: approve

**Question:** On what exact date did engineers ignite the Darvaza gas crater?
**Answer:** (empty — unanswerable)
**Labels:** answerability: "unanswerable", evidence.absent_reason: "The corpus gives only the year 1971 for the burning (t:darvaza_gas_crater:00:000:02), while the early history is explicitly undetermined with conflicting accounts (1960s collapse set on fire in the 1980s versus drilling in 1971; p:darvaza_gas_crater:01:000); no exact ignition date exists in the article."

#### Absence verification
Corpus check:
- t:darvaza_gas_crater:00:000:02 = "The crater has been burning since 1971."
- t:darvaza_gas_crater:00:000:03 = "...some sources state that engineers ignited the crater to prevent poisonous gases from spreading." (no date)
- t:darvaza_gas_crater:01:000:02 = "Some local geologists have claimed that the collapse of a crater happened in the 1960s; it was set on fire only in the 1980s..."
- t:darvaza_gas_crater:01:000:03 = "Others assert that the site was drilled by Soviet engineers in 1971 as an oil field but collapsed within days, forming the crater, with the engineers choosing to flare the crater..."
No sentence provides a month/day for the ignition. The year 1971 appears in two conflicting accounts; no exact date exists.

#### Hard negative
t:darvaza_gas_crater:00:000:03 ("...some sources state that engineers ignited the crater...") — token_overlap_nearmiss (mentions "engineers ignited"); does not contain a date; non-evidence; neighbor sentence. VALID.

---

### qa-dev-28 — DECISION: approve

**Question:** Which language is Delhi's most spoken, at 80.94%?
**Answer:** Hindi
**Sufficient set:** { p:delhi:21:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:delhi:21:000 | no | Supplies the answer directly ("According to the 50th report... Hindi is Delhi's most spoken language, with 80.94% speakers..."). The question's "Delhi", "most spoken", "80.94%" are all grounded by this paragraph. |

#### Q3 Alternatives
NO — the sentence t:delhi:21:000:00 is the same passage at different granularity. No other paragraph in the Delhi article provides language speaker percentages.

#### Hard negative
p:delhi:20:000 (religion paragraph) — sibling_paragraph; does not contain answer; non-evidence. VALID.

#### Answer exactness
"Hindi" is an exact verbatim substring of t:delhi:21:000:00.

---

### qa-dev-29 — DECISION: approve

**Question:** In game theory, which game involves two players of different sexes with different preferences?
**Answer:** The "battle of the sexes" game
**Sufficient set:** { p:game_theory:16:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:game_theory:16:000 | no | Supplies the answer directly ("The \"battle of the sexes\" game involves two players of different sexes, arbitrarily chosen, each with a different set of preferences."). The question's "game theory", "two players", "different sexes", "different preferences" are all grounded by this paragraph. |

#### Q3 Alternatives
NO — the sentence t:game_theory:16:000:00 is the same passage at different granularity. No other paragraph in the Game Theory article mentions "battle of the sexes".

#### Hard negative
p:game_theory:11:000 (non-cooperative games representation) — token_overlap_nearmiss (mentions "games", "non-cooperative"); does not contain answer; non-evidence. VALID.

#### Answer exactness
"The \"battle of the sexes\" game" is an exact verbatim substring of t:game_theory:16:000:00.

---

### qa-dev-30 — DECISION: approve

**Question:** What is a Nash equilibrium, in terms of how every player responds to the others?
**Answer:** a particular type of equilibrium strategy profile where every player is best responding to the strategies of the others
**Sufficient set:** { t:game_theory:10:000:03 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:game_theory:10:000:03 | no | Supplies the definition directly ("A Nash equilibrium is a particular type of equilibrium strategy profile where every player is best responding to the strategies of the others."). The question's "Nash equilibrium", "every player", "responds to the others" are all grounded by this sentence. |

#### Q3 Alternatives
NO — t:game_theory:24:000:05 discusses a "mixed Nash equilibrium" in a different context (analogous to pure strategy in a different game), not the core definition. No other sentence in the article provides the standard definition.

#### Hard negative
t:game_theory:24:000:05 ("A mixed Nash equilibrium is analogous to a pure strategy Nash equilibrium in a different game...") — entity_confusion (mixed vs. standard definition); does not contain the requested definition; non-evidence. VALID.

#### Answer exactness
The answer text is an exact verbatim substring of t:game_theory:10:000:03 (after "A Nash equilibrium is ").

---

### qa-dev-31 — DECISION: approve

**Question:** Through what does the muscular organ found in humans and other animals pump blood?
**Answer:** the blood vessels
**Sufficient set:** { t:heart:00:000:01 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:heart:00:000:01 | no | Supplies the answer directly ("This organ pumps blood through the blood vessels."). The question's "muscular organ", "humans and other animals", "pump blood" are all grounded by this sentence (the preceding sentence t:heart:00:000:00 identifies the organ as the heart). |

#### Q3 Alternatives
NO — no other sentence in the Heart article states what the heart pumps blood through. The chambers paragraph (p:heart:00:001) discusses internal structure, not the circulatory pathway.

#### Hard negative
p:heart:19:000 (sibling paragraph) — does not contain answer; non-evidence. VALID.

#### Answer exactness
"the blood vessels" is an exact verbatim substring of t:heart:00:000:01.

---

### qa-dev-32 — DECISION: approve

**Question:** Into which four chambers is the human heart divided?
**Answer:** upper left and right atria and lower left and right ventricles
**Sufficient set:** { t:heart:00:001:00 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:heart:00:001:00 | no | Supplies the answer directly ("In humans, the heart is divided into four chambers: upper left and right atria and lower left and right ventricles."). The question's "human heart", "four chambers" are all grounded by this sentence. |

#### Q3 Alternatives
NO — no other sentence in the Heart article lists the four chambers. The lead sentence (t:heart:00:000:01) only mentions pumping blood through vessels.

#### Hard negative
p:heart:25:000 (sibling paragraph) — does not contain answer; non-evidence. VALID.

#### Answer exactness
"upper left and right atria and lower left and right ventricles" is an exact verbatim substring of t:heart:00:001:00.

---

### qa-dev-33 — DECISION: approve

**Question:** Which two genomes are usually treated separately?
**Answer:** the nuclear genome and the mitochondrial genome
**Sufficient set:** { t:human_genome:00:000:02 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:human_genome:00:000:02 | no | Supplies the answer directly ("These are usually treated separately as the nuclear genome and the mitochondrial genome."). The question's "two genomes", "usually treated separately" are all grounded by this sentence (the preceding sentence t:human_genome:00:000:01 identifies "These" as the nuclear and mitochondrial genomes). |

#### Q3 Alternatives
NO — no other sentence in the Human Genome article states this exact fact. t:human_genome:00:000:04 discusses regulatory DNA categories, not the separate treatment of the two genomes.

#### Hard negative
t:human_genome:00:000:04 ("The latter is a diverse category that includes regulatory DNA scaffolding regions, telomeres, centromeres, and origins of replication.") — neighbor_sentence; does not contain answer; non-evidence. VALID.

#### Answer exactness
"the nuclear genome and the mitochondrial genome" is an exact verbatim substring of t:human_genome:00:000:02.

---

### Summary

| Draft | Decision | Notes |
|-------|----------|-------|
| qa-dev-20 | approve | Unanswerable; absence claim verified |
| qa-dev-22 | approve | Single-atom factoid; no alternatives |
| qa-dev-24 | approve | Single-atom comparison; no alternatives |
| qa-dev-26 | approve | Unanswerable; absence claim verified |
| qa-dev-28 | approve | Single-atom factoid; no alternatives |
| qa-dev-29 | approve | Single-atom factoid; no alternatives |
| qa-dev-30 | approve | Single-atom factoid; no alternatives |
| qa-dev-31 | approve | Single-atom factoid; no alternatives |
| qa-dev-32 | approve | Single-atom factoid; no alternatives |
| qa-dev-33 | approve | Single-atom factoid; no alternatives |

---

### Approved draft content hashes (Batch 3)

All 10 drafts approved:

- **qa-dev-20**: `0af3854c1a81d3db29f0bd8615b95901b3dbfa2f3d77c850c7bb50d485e12c40`
- **qa-dev-22**: `554ed6d739618dd1ec25b7543cb68098d1e45d5f322a683f68a011860f759314`
- **qa-dev-24**: `2e6283af6d06ee6388592406385bf97ef3ca5437de7bf320e68341418e0ff627`
- **qa-dev-26**: `76c63ace95e152b9517e3949ed08deb26dc8eb948f1a3a6f3965fba9626d36d1`
- **qa-dev-28**: `657616c243093e4ad5196e2960b245e52add038e41fce44fb34b7ce9e5578362`
- **qa-dev-29**: `3c6850a6653182adc73fa3446a68170e71a68934e54d71b4b091e9ddd210c87a`
- **qa-dev-30**: `f2f2965a82520401f8dc0a6bd66d1069ad8d20538b2fccf587f1b821bb7f874b`
- **qa-dev-31**: `27e86d03d5945fd3bd0495963c4f24ac9ef07d4076f7dd8a49dbbad82147bc45`
- **qa-dev-32**: `e61c76e24e1a34f4a8fda89ba965488a72d217ff54b2a0d537d7fe66a2bedd41`
- **qa-dev-33**: `c50c9fef72d51ac7617953586f3b25746605435be7fd5a7906dee60283791aa8`

---
## Batch 4

**Reviewer:** independent-verifier
**Model:** opencode/nemotron-3-ultra-free
**Corpus revision:** pilot-297-r1
**Date:** 2026-10-01

---

### qa-dev-34 — DECISION: approve

**Question:** On average, how many DNA damage events does the human genome experience per cell per day?
**Answer:** tens of thousands
**Sufficient set:** { p:human_genome:16:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:human_genome:16:000 | no | Supplies the exact answer ("tens of thousands of DNA damage events per day"). The question's "on average", "per cell per day" are grounded by the atom. |

#### Q3 Alternatives
NO — p:human_genome:16:000 is the only paragraph in the Human Genome article mentioning DNA damage event frequency ("tens of thousands... per day"). No other paragraph or article provides this figure.

#### Hard negative
p:human_genome:02:000 (reference genome length paragraph) — sibling_paragraph; does not contain "damage events" or frequency; non-evidence. VALID.

#### Answer exactness
"tens of thousands" is an exact verbatim substring of p:human_genome:16:000.

---

### qa-dev-36 — DECISION: approve

**Question:** Into which three broad categories do failures of host defense fall?
**Answer:** immunodeficiencies, autoimmunity, and hypersensitivities
**Sufficient set:** { p:immune_system:24:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:immune_system:24:000 | no | Supplies the three categories explicitly ("immunodeficiencies, autoimmunity, and hypersensitivities"). The question's "failures of host defense", "three broad categories" are grounded by the atom. |

#### Q3 Alternatives
NO — p:immune_system:24:000 is the only paragraph that lists all three categories together as "three broad categories". p:immune_system:25:000/26:000/27:000 discuss each category separately but never the combined three-category taxonomy.

#### Hard negative
p:immune_system:21:000 (physical exercise paragraph) — sibling_paragraph; does not contain answer; non-evidence. VALID.

#### Answer exactness
"immunodeficiencies, autoimmunity, and hypersensitivities" is an exact verbatim substring of p:immune_system:24:000.

---

### qa-dev-37 — DECISION: approve

**Question:** Which species is the most important local species for fisheries in Lake Baikal?
**Answer:** the omul (Coregonus migratorius)
**Sufficient set:** { p:lake_baikal:07:001 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:lake_baikal:07:001 | no | Supplies the answer directly ("The most important local species for fisheries is the omul (Coregonus migratorius)"). The question's "most important local species", "fisheries", "Lake Baikal" are grounded by the atom. |

#### Q3 Alternatives
NO — p:lake_baikal:07:000 lists fish families but does not identify the "most important local species for fisheries". No other paragraph provides this specific designation.

#### Hard negative
p:lake_baikal:08:000 (invertebrates paragraph) — sibling_paragraph; does not contain "omul" or "fisheries"; non-evidence. VALID.

#### Answer exactness
"the omul (Coregonus migratorius)" is an exact verbatim substring of p:lake_baikal:07:001.

---

### qa-dev-38 — DECISION: approve

**Question:** How much water did AquaSib aim to export to China from its Kultuk plant?
**Answer:** 190 million liters
**Sufficient set:** { p:lake_baikal:22:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:lake_baikal:22:000 | no | Supplies the exact figure ("The goal was to export 190 million liters of water to China"). The question's "AquaSib", "Kultuk plant", "export to China" are grounded by the atom. |

#### Q3 Alternatives
NO — p:lake_baikal:22:000 is the only paragraph mentioning AquaSib, Kultuk, or the 190 million liter figure. No alternative passage exists.

#### Hard negative
p:lake_baikal:23:000 (algae/waste paragraph) — sibling_paragraph; does not contain "AquaSib", "Kultuk", or "190 million"; non-evidence. VALID.

#### Answer exactness
"190 million liters" is an exact verbatim substring of p:lake_baikal:22:000.

---

### qa-dev-39 — DECISION: approve

**Question:** Which preexisting member of the order Sirenia was hunted to extinction in the eighteenth century?
**Answer:** Steller's sea cow
**Sufficient set:** { p:manatee:02:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:manatee:02:000 | no | Supplies the answer directly ("A preexisting member of the order known as Steller's sea cow was hunted to extinction in the eighteenth century"). The question's "preexisting member", "order Sirenia", "hunted to extinction", "eighteenth century" are grounded by the atom. |

#### Q3 Alternatives
NO — p:manatee:27:000 mentions "Steller's Sea Cow" in a cultural context but does not state it was hunted to extinction in the 18th century. No other paragraph provides this fact.

#### Hard negative
p:manatee:05:000 (solitary behavior paragraph) — sibling_paragraph; does not contain "Steller's sea cow" or "extinction"; non-evidence. VALID.

#### Answer exactness
"Steller's sea cow" is an exact verbatim substring of p:manatee:02:000.

---

### qa-dev-40 — DECISION: repair-minimality + repair-alternatives

**Question:** Between the West Indian manatee and the Amazonian manatee, which is the only exclusively freshwater manatee?
**Answer:** The freshwater Amazonian manatee (T. inunguis)
**Sufficient sets (as authored):** { p:manatee:14:000, p:manatee:16:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:manatee:14:000 | yes | REDUNDANT/SETUP — describes West Indian manatee habitat/migration but does not state the distinguishing property "exclusively freshwater". The question already names both manatee types. |
| p:manatee:16:000 | no | Supplies the distinguishing property ("It is the only exclusively freshwater manatee") identifying the Amazonian manatee. |

#### Q3 Alternatives
**YES — genuinely different sufficient set exists:**
- { p:manatee:16:000 } — the single atom alone determines the answer. Different node IDs (1 vs 2 atoms), not a re-phrasing.

#### Defect
The authored sufficient set is not minimal: p:manatee:14:000 is removable without loss of answerability (Q1 = yes). The minimal sufficient set is { p:manatee:16:000 }. This requires both `repair-minimality` (drop redundant atom) and `repair-alternatives` (record the single-atom set).

#### Hard negative
p:manatee:17:000 (West African manatee habitat) — entity_confusion; does not contain "exclusively freshwater" or answer; non-evidence. VALID.

#### Answer exactness
"The freshwater Amazonian manatee (T. inunguis)" is an exact verbatim substring of p:manatee:16:000.

---

### qa-dev-42 — DECISION: approve

**Question:** How can nanomaterials be classified by dimensionality?
**Answer:** 0D, 1D, 2D and 3D nanomaterials
**Sufficient set:** { p:nanotechnology:12:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:nanotechnology:12:000 | no | Supplies the classification explicitly ("Nanomaterials can be classified in 0D, 1D, 2D and 3D nanomaterials"). The question's "nanomaterials", "classified by dimensionality" are grounded by the atom. |

#### Q3 Alternatives
NO — p:nanotechnology:12:000 is the only paragraph presenting the 0D/1D/2D/3D dimensionality classification system. p:nanotechnology:02:000 discusses scale range (1-100 nm) but not dimensionality classes. p:nanotechnology:06:000 mentions nanoparticles/nanorods but not the 0D-3D taxonomy.

#### Hard negative
p:nanotechnology:09:000 (functional approaches paragraph) — sibling_paragraph; does not contain dimensionality classification; non-evidence. VALID.

#### Answer exactness
"0D, 1D, 2D and 3D nanomaterials" is an exact verbatim substring of p:nanotechnology:12:000.

---

### qa-dev-44 — DECISION: approve

**Question:** Who studied muon-catalyzed fusion in detail in the early 1980s?
**Answer:** Steven Jones
**Sufficient set:** { p:nuclear_fusion:17:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:nuclear_fusion:17:000 | no | Supplies the answer directly ("It was studied in detail by Steven Jones in the early 1980s"). The question's "muon-catalyzed fusion", "studied in detail", "early 1980s" are grounded by the atom. |

#### Q3 Alternatives
NO — p:nuclear_fusion:17:000 is the only paragraph mentioning "Steven Jones" and "muon-catalyzed fusion" together. No other paragraph or article provides this attribution.

#### Hard negative
p:nuclear_fusion:21:000 (magnetic confinement paragraph) — sibling_paragraph; does not contain "Steven Jones" or "muon-catalyzed"; non-evidence. VALID.

#### Answer exactness
"Steven Jones" is an exact verbatim substring of p:nuclear_fusion:17:000.

---

### qa-dev-45 — DECISION: repair-alternatives

**Question:** What sense does the platypus use to detect prey in water?
**Answer:** electrolocation
**Sufficient set (as authored):** { t:platypus:00:000:03 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:platypus:00:000:03 | no | Supplies "electrolocation" directly ("Like other monotremes, the platypus has a sense of electrolocation, which it uses to detect prey in water..."). The question's "platypus", "detect prey in water" are grounded by the atom. |

#### Q3 Alternatives
**YES — genuinely different sufficient set exists:**
- { t:platypus:03:000:01 } — "The platypus relies on electrolocation when feeding, as the eyes, ears, and nose are closed while underwater." (from p:platypus:03:000, Senses section)
Different node IDs (t:platypus:03:000:01 vs t:platypus:00:000:03), different paragraph (p:platypus:03:000 vs p:platypus:00:000), different passage (Senses section vs lead). Must be recorded.

#### Hard negative
t:platypus:00:000:04 (venom sentence) — neighbor_sentence; does not contain "electrolocation"; non-evidence. VALID.

#### Answer exactness
"electrolocation" is an exact verbatim substring of t:platypus:00:000:03 and t:platypus:03:000:01.

---

### qa-dev-46 — DECISION: approve

**Question:** What did the first scientists to examine a preserved platypus body judge it to be in 1799?
**Answer:** a fake made of several animals sewn together
**Sufficient set:** { t:platypus:00:000:06 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:platypus:00:000:06 | no | Supplies the exact judgment ("In 1799, the first scientists to examine a preserved platypus body judged it a fake made of several animals sewn together"). The question's "first scientists", "preserved platypus body", "1799" are grounded by the atom. |

#### Q3 Alternatives
NO — t:platypus:01:000:04 ("British scientists' initial hunch was that the attributes were a hoax"), t:platypus:01:000:06 ("It was thought somebody had sewn a duck's beak onto the body of a beaver-like animal") are similar in meaning but do NOT contain the exact answer string "a fake made of several animals sewn together". Per protocol, alternatives must yield the exact verbatim answer. No other node_id provides this exact string.

#### Hard negative
t:platypus:00:000:07 (next sentence about unique features) — neighbor_sentence; does not contain answer; non-evidence. VALID.

#### Answer exactness
"a fake made of several animals sewn together" is an exact verbatim substring of t:platypus:00:000:06.

---

### Summary

| Draft | Decision | Notes |
|-------|----------|-------|
| qa-dev-34 | approve | Single-atom factoid; no alternatives |
| qa-dev-36 | approve | Single-atom factoid; no alternatives |
| qa-dev-37 | approve | Single-atom factoid; no alternatives |
| qa-dev-38 | approve | Single-atom factoid; no alternatives |
| qa-dev-39 | approve | Single-atom factoid; no alternatives |
| qa-dev-40 | repair-minimality + repair-alternatives | p:manatee:14:000 redundant; minimal set is {p:manatee:16:000} |
| qa-dev-42 | approve | Single-atom factoid; no alternatives |
| qa-dev-44 | approve | Single-atom factoid; no alternatives |
| qa-dev-45 | repair-alternatives | Alternative sufficient set {t:platypus:03:000:01} exists |
| qa-dev-46 | approve | Single-atom factoid; no alternatives |

---

## Approved draft content hashes (Batch 4)

8 drafts approved (34, 36, 37, 38, 39, 42, 44, 46):

- **qa-dev-34**: `94046cc1928cd83994aa0014c30490f1de6e04b7839b7b741dc10b1b5f69567f`
- **qa-dev-36**: `2cf5eb89bc986c45b18deaa02c06cd4df1806dc0400db43f4ae33c409ba5cb02`
- **qa-dev-37**: `814b26d8da386a1dd0c16d57ed8dd9349b973fa0cc9f9ed8b3c8a21e515d3896`
- **qa-dev-38**: `049cfeabfce5da784992149561a90ee654fb0ad73c8946f077aacbdc28aa46db`
- **qa-dev-39**: `a38a97292a3399bd4b96d02e90d01161cb46c90bcd2ea6ce6904d20b044fd479`
- **qa-dev-42**: `110068bd1576bd8d3b50ae55b77537f37a211427a0919e4bd901801a88c1dfe3`
- **qa-dev-44**: `41379e4f868218411500ad4d7f6f339ab82e8b410d8e097dfe7af18ae9b97a9d`
- **qa-dev-46**: `23c552ceedf7c500580cbf66fe1f209501c032de4a0bd7d3e3ebbcf2ccb34086`

The 2 drafts marked `repair-minimality`/`repair-alternatives` (qa-dev-40, qa-dev-45) require the author to add the alternative sufficient sets to `evidence.sufficient_sets`, then re-verify and re-approve against new content hashes.

---
## Batch 5

**Reviewer:** independent-verifier
**Model:** opencode/nemotron-3-ultra-free
**Corpus revision:** pilot-297-r1
**Date:** 2026-10-01

---

### qa-dev-48 — DECISION: approve

**Question:** Which historian described the printing press as an 'agent of change'?
**Answer:** Elizabeth Eisenstein
**Sufficient set:** { p:printing_press:11:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:printing_press:11:000 | N/A (single-atom) | Supplies the historian name and the exact quote ("the historian Elizabeth Eisenstein described the press as an 'agent of change'"). The question's "historian", "printing press", "agent of change" are grounded by the atom. |

#### Q3 Alternatives
NO — p:printing_press:11:000 is the only paragraph containing the exact phrase "agent of change" attributed to Elizabeth Eisenstein. No other paragraph in the Printing Press article mentions this attribution.

#### Hard negative
p:printing_press:09:000 (sibling paragraph, impact section continuation) — does not contain "Elizabeth Eisenstein" or "agent of change"; non-evidence; sibling_paragraph. VALID.

#### Answer exactness
"Elizabeth Eisenstein" is an exact verbatim substring of p:printing_press:11:000.

---

### qa-dev-50 — DECISION: approve

**Question:** Why are semiconductors in their natural state poor conductors?
**Answer:** a current requires flow of electrons, and semiconductors have their valence bands filled
**Sufficient set:** { p:semiconductor:01:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:semiconductor:01:000 | N/A (single-atom) | Supplies the exact causal explanation ("Semiconductors in their natural state are poor conductors because a current requires flow of electrons, and semiconductors have their valence bands filled"). The question's "semiconductors", "natural state", "poor conductors" are grounded by the atom. |

#### Q3 Alternatives
NO — p:semiconductor:01:000 (the Variable electrical conductivity section) is the only paragraph explaining why natural-state semiconductors are poor conductors. The lead paragraph (p:semiconductor:00:000) defines semiconductors but does not give this specific reason. No other paragraph provides this causal account.

#### Hard negative
p:semiconductor:05:000 (token_overlap_nearmiss) — does not contain the valence-band-filled explanation; non-evidence. VALID.

#### Answer exactness
"a current requires flow of electrons, and semiconductors have their valence bands filled" is an exact verbatim substring of p:semiconductor:01:000 (modulo the opening "Semiconductors in their natural state are poor conductors because ").

---

### qa-dev-51 — DECISION: approve

**Question:** About what share of installed solar capacity is utility scale?
**Answer:** half
**Sufficient set:** { p:solar_power:10:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:solar_power:10:000 | N/A (single-atom) | Supplies the exact figure ("About half of installed capacity is utility scale."). The question's "share of installed solar capacity", "utility scale" are grounded by the atom. |

#### Q3 Alternatives
NO — p:solar_power:10:000 (the Current status subsection) is the only paragraph stating the utility-scale share of installed capacity. The Forecasts subsection (p:solar_power:10:000 area) mentions "Utility scale is forecast to become the largest source" but does not give the current share. No other paragraph provides this figure.

#### Hard negative
p:solar_power:11:000 (sibling paragraph, map caption) — does not contain "utility scale" or share figure; non-evidence; sibling_paragraph. VALID.

#### Answer exactness
"half" is an exact verbatim substring of p:solar_power:10:000.

---

### qa-dev-52 — DECISION: approve

**Question:** Between photovoltaic systems and concentrated solar thermal, which converts sunlight directly into electric power?
**Answer:** Photovoltaic (PV) systems
**Sufficient set:** { t:solar_power:02:000:00, p:solar_power:04:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| t:solar_power:02:000:00 | no | Identifies PV systems as converting sunlight directly into electric power. Without it, the PV property is missing. |
| p:solar_power:04:000 | no | Identifies CSP/concentrated solar thermal as using heat to drive steam turbines (indirect conversion). Without it, the contrast is missing. |

#### Q3 Alternatives
NO — both atoms are required for the comparison. t:solar_power:02:000:00 (from the "Solar power plants" paragraph) supplies the direct-conversion property of PV; p:solar_power:04:000 (the Concentrated solar power section) supplies the indirect-conversion mechanism of CSP. No single paragraph contains both the PV direct-conversion statement and the CSP indirect-conversion statement. The sentence-level atom t:solar_power:04:000:00 is the same passage as p:solar_power:04:000.

#### Multi-hop genuineness
GENUINE — removing either hop breaks the comparison. Hop 1 (entity discovery: PV direct conversion), Hop 2 (entity discovery: CSP indirect conversion). The question requires combining both facts to select the correct technology.

#### Hard negative
p:solar_power:05:000 (sibling paragraph) — does not contain the PV/CSP comparison; non-evidence; sibling_paragraph. VALID.

#### Answer exactness
"Photovoltaic (PV) systems" is an exact verbatim substring of t:solar_power:02:000:00.

---

### qa-dev-54 — DECISION: approve

**Question:** What is the capital of South Africa?
**Answer:** Ambiguous between Pretoria, Cape Town and Bloemfontein readings - see labels.readings
**Sufficient sets:**
- Set 0: { t:south_africa:00:000:04 } → Pretoria (administrative capital)
- Set 1: { t:south_africa:13:000:11 } → Cape Town (legislative capital, seat of Parliament)
- Set 2: { t:south_africa:13:000:12 } → Bloemfontein (judicial capital)

#### Q1/Q2 per atom (per reading)

| Reading | Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|---------|------|-------------------------------|---------------------|
| Pretoria | t:south_africa:00:000:04 | N/A (single-atom) | Supplies "Pretoria is the administrative capital". |
| Cape Town | t:south_africa:13:000:11 | N/A (single-atom) | Supplies "The seat of Parliament is Cape Town" and "three branches of government are split over different cities". |
| Bloemfontein | t:south_africa:13:000:12 | N/A (single-atom) | Supplies "Bloemfontein is the seat of the Supreme Court of Appeal, and is regarded as the judicial capital". |

#### Q3 Alternatives
NO — each reading is grounded in a distinct node_id from different paragraphs (lead paragraph vs constitution paragraph). The three readings reflect the three distinct constitutional capitals of South Africa.

#### Ambiguity verification
GENUINE AMBIGUITY — the corpus explicitly states South Africa has three capitals (administrative Pretoria, legislative Cape Town, judicial Bloemfontein) and no single legally defined capital city (t:south_africa:00:000:04 and t:south_africa:13:000:11 both state this). Each reading has its own distinct sufficient set and answer. Real ambiguity, not vagueness.

#### Hard negative
t:south_africa:00:000:02 (neighbor sentence, area/population) — does not contain any capital designation; non-evidence; neighbor_sentence. VALID.

#### Answer exactness
Each reading's answer is an exact verbatim substring of its respective atom.

---

### qa-dev-55 — DECISION: approve

**Question:** Into how many districts is Vienna divided?
**Answer:** 23
**Sufficient set:** { p:vienna:15:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:vienna:15:000 | N/A (single-atom) | Supplies the exact number ("Vienna is divided into 23 districts."). The question's "Vienna", "divided into", "districts" are grounded by the atom. |

#### Q3 Alternatives
NO — p:vienna:15:000 (the Districts section) is the only paragraph stating the total number of districts (23). The district table lists all 23 but does not state the total count explicitly. No other paragraph provides this figure.

#### Hard negative
p:vienna:13:000 (sibling paragraph) — does not contain "23" or district count; non-evidence; sibling_paragraph. VALID.

#### Answer exactness
"23" is an exact verbatim substring of p:vienna:15:000.

---

### qa-dev-56 — DECISION: approve

**Question:** Since when was the area of Vienna inhabited by modern humans?
**Answer:** the Upper Palaeolithic period (37.000–38.500BC)
**Sufficient set:** { p:vienna:02:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:vienna:02:000 | N/A (single-atom) | Supplies the period and date range ("The area of Vienna was inhabited by modern humans already from the Upper Palaeolithic period (37.000–38.500BC)"). The question's "area of Vienna", "inhabited by modern humans", "since when" are grounded by the atom. |

#### Q3 Alternatives
NO — p:vienna:02:000 (the lead paragraph) is the only paragraph mentioning Upper Palaeolithic habitation with the specific date range. No other paragraph in the Vienna article provides this information.

#### Hard negative
p:vienna:04:001 (neighbor paragraph, Middle Ages) — does not contain Upper Palaeolithic or 37,000–38,500 BC; non-evidence; neighbor_paragraph. VALID.

#### Answer exactness
"the Upper Palaeolithic period (37.000–38.500BC)" is an exact verbatim substring of p:vienna:02:000.

---

### qa-dev-58 — DECISION: approve

**Question:** What exact mechanism in the eye produced the X-ray visibility reported by Röntgen and Brandes?
**Answer:** (empty — unanswerable)
**Labels:** answerability: "unanswerable", evidence.absent_reason: "The corpus states it is not known what exact mechanism produced the visibility (t:x_ray:25:000:06); Cherenkov radiation from X-rays in the vitreous humor is given only as a likely explanation."

#### Absence verification
Corpus check (t:x_ray:25:000:06 / p:x_ray:25:000, Visibility section): "It is not known what exact mechanism in the eye produced the visibility described by Röntgen and Brandes, though Cherenkov radiation caused by the X-rays traveling through the vitreous humor of the eye is a likely explanation." No sentence in the X-ray article provides a definitive mechanism. The "likely explanation" is explicitly qualified as uncertain.

#### Hard negative
t:x_ray:25:000:02 (neighbor sentence, Brandes experiment description) — token_overlap_nearmiss (mentions "Brandes", "Röntgen", "eye", "glow"); does not contain a mechanism claim; non-evidence; neighbor_sentence. VALID.

---

### qa-dev-59 — DECISION: approve

**Question:** Which theme park in Anaheim is the second most visited in the world?
**Answer:** Disneyland
**Sufficient set:** { p:orange_county_california:17:000 }

#### Q1/Q2 per atom

| Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|------|-------------------------------|---------------------|
| p:orange_county_california:17:000 | N/A (single-atom) | Supplies the answer directly ("Anaheim is the main tourist hub, with the Disneyland Resort's Disneyland being the second most visited theme park in the world."). The question's "theme park", "Anaheim", "second most visited in the world" are grounded by the atom. |

#### Q3 Alternatives
NO — p:orange_county_california:17:000 (the Tourism section) is the only paragraph stating Disneyland is the second most visited theme park in the world. Other paragraphs mention Disneyland but not this specific ranking. No other paragraph provides this figure.

#### Hard negative
p:orange_county_california:20:000 (same_group_distractor, demographics table) — does not contain "Disneyland", "second most visited", or theme park rankings; non-evidence; same_group_distractor. VALID.

#### Answer exactness
"Disneyland" is an exact verbatim substring of p:orange_county_california:17:000.

---

### qa-dev-60 — DECISION: approve

**Question:** When did the revolution begin?
**Answer:** Ambiguous between the French and Russian revolution readings - see labels.readings
**Sufficient sets:**
- Set 0: { t:napoleon:00:000:04 } → 1789 (French Revolution supported by Napoleon)
- Set 1: { t:russian_revolution:00:000:04 } → the February Revolution in 1917 (Russian Revolution inaugurated in 1917)

#### Q1/Q2 per atom (per reading)

| Reading | Atom | Q1: Leave-one-out answerable? | Q2: Necessity note |
|---------|------|-------------------------------|---------------------|
| French Revolution | t:napoleon:00:000:04 | N/A (single-atom) | Supplies "He supported the French Revolution in 1789". |
| Russian Revolution | t:russian_revolution:00:000:04 | N/A (single-atom) | Supplies "The Russian Revolution was inaugurated with the February Revolution in 1917". |

#### Q3 Alternatives
NO — each reading is grounded in a distinct article (napoleon vs russian_revolution). The question "When did the revolution begin?" is genuinely ambiguous without specifying which revolution, and the corpus contains multiple revolution articles with different start dates.

#### Ambiguity verification
GENUINE AMBIGUITY — the corpus contains at least two distinct revolutions with different inception dates (French Revolution 1789, Russian Revolution 1917). Each reading has its own distinct sufficient set from a different source article. Real ambiguity, not vagueness.

#### Hard negative
t:napoleon:00:000:08 (entity_confusion, 13 Vendémiaire 1795 rebellion) — does not answer "when did the revolution begin"; non-evidence; entity_confusion. VALID.

#### Answer exactness
Each reading's answer is an exact verbatim substring of its respective atom.

---

### Summary

| Draft | Decision | Notes |
|-------|----------|-------|
| qa-dev-48 | approve | Single-atom factoid; no alternatives |
| qa-dev-50 | approve | Single-atom factoid; no alternatives |
| qa-dev-51 | approve | Single-atom factoid; no alternatives |
| qa-dev-52 | approve | Genuine multi-hop comparison; no alternatives |
| qa-dev-54 | approve | Genuine ambiguity (three capitals); three readings |
| qa-dev-55 | approve | Single-atom factoid; no alternatives |
| qa-dev-56 | approve | Single-atom factoid; no alternatives |
| qa-dev-58 | approve | Unanswerable; absence claim verified |
| qa-dev-59 | approve | Single-atom factoid; no alternatives |
| qa-dev-60 | approve | Genuine ambiguity (two revolutions); two readings |

---

## Approved draft content hashes (Batch 5)

All 10 drafts approved:

- **qa-dev-48**: `3f5d0dcc188575a2c2f9e561551ea186939cb5cd60771cabf0f124823e07fa63`
- **qa-dev-50**: `ab0de62d3338ce9b1f89b74dad4247a3f528c6d45ab724dbe00d2aad40323304`
- **qa-dev-51**: `73635d0f7089f432470b8f67c5566314216e4fc4887fd4ff875ba76cb24e9e5a`
- **qa-dev-52**: `535e2262b38ecfda0743ff42c1fbed43c6304faa05a8c9d8f51e4b3cbbf37c89`
- **qa-dev-54**: `eab54c2b9dfb1a77a2ae868bcd58f92585365e418d4782fbf4fe67e8929ab04a`
- **qa-dev-55**: `7dc5252eee3f68ce515912437dc7cce542cfc09c879ff717f462fc9a1b077c9c`
- **qa-dev-56**: `4e331d85d77f021db7c34f4bcdf42665537b0f04f0dae2e96eb4f8c765b69add`
- **qa-dev-58**: `918a06d612bab97a0cb73cab6b5a54623c1fae694aa7ab078131036bece88d25`
- **qa-dev-59**: `bce9049f4f7e63a9a1dea20dc136f786fd9007197fe3af67549f987afa1a86be`
- **qa-dev-60**: `bbbe78d72ca140f96fbb78e01c3c1645ba4676248c4aa10b7c3b93bbb589f481`

All 10 drafts in Batch 5 are approved. No repairs required.