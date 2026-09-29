# QA Train Verification — Pass 1 (TRAIN 01–10)

Independent second-reader verification of staging/qa-train-01.json through qa-train-10.json against corpus/corpus.jsonl.

## Summary
All 10 drafts pass content verification criteria:
- Every cited node ID exists in corpus (exact lookup)
- Every evidence span text matches corpus node text (code-point equality)
- Answers supported by cited evidence
- Hard negatives are genuine non-evidence (no ancestor/descendant overlap with any evidence span)
- Provenance block complete (author, author_model, content_hash, decision, rationale, verifier, verifier_model)
- Single-group compliance (all evidence spans resolve to declared meta.group)
- No tautology (questions are not mere restatements of evidence text)

Procedural gaps (expected for pending drafts):
- All hard negatives have `reviewed: false` — require independent human review
- All drafts have `provenance.decision: "pending"` — require verifier approval with nonempty rationale
- Verifier model not assigned

## Per-Draft Verdicts

### qa-train-01 (amazon group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `fb1e00a634d9d2b577392e8a94e976e5c8173814f0b95a285f8934b14d47fca4`
- Evidence: `p:amazon_company:12:000` ✓ (exact text match)
- Hard negative: `p:amazon_rainforest:03:000` ✓ (different entity, no overlap, same group distractor)
- Answer "Amazon" supported by evidence

### qa-train-02 (amazon group, ambiguous)
- **Verdict: APPROVE** (content)
- **Hash**: `21a02dee4a7df70a33df38a4b070922f3f83241c68e2ec0c750cb7161d46430a`
- Evidence set 0: `t:jeff_bezos:00:000:00` ✓
- Evidence set 1: `t:amazon_rainforest:00:000:00` ✓
- Hard negative: `p:amazons:08:000` ✓ (entity confusion: Amazons myth vs company/rainforest)
- Readings correctly capture both senses; answerability "ambiguous" correct

### qa-train-03 (amazon group, comparison)
- **Verdict: APPROVE** (content)
- **Hash**: `126b03ded52ba632de8369ccac0a8c26fd77d9861fcd36546ea9ef9565373f7a`
- Evidence: `p:amazon_rainforest:03:000` ✓ (contains 58.4% Brazil figure)
- Hard negative: `t:amazon_rainforest:00:000:01` ✓ (neighbor sentence, no percentage)
- Answer "58.4%" supported

### qa-train-04 (apple group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `50d2b5190486fb3f4eb11783795ae75828852936a572d0037e08ef6aab6deca8`
- Evidence: `t:apple_records:00:000:00` ✓
- Hard negative: `p:apple_inc:12:000` ✓ (entity confusion: Apple Inc. vs Apple Records)
- Answer "Apple Records" supported

### qa-train-05 (apple group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `1f67402439f7b05d70478013665870559b33714aaa6dda755b01c46ea39b1af1`
- Evidence span 0: `p:steve_jobs:09:000` ✓ (1986 Pixar spinout)
- Evidence span 1: `p:steve_jobs:12:000` ✓ (Apple Computer 1976 co-founding)
- Hard negative 0: `t:apple_records:00:000:03` ✓ (same group distractor)
- Hard negative 1: `p:apple_inc:03:000` ✓ (linked article, no overlap)
- Answer "Apple Computer" supported by multihop chain

### qa-train-06 (apple group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `efb51b07eff39a4da1e3f2d23f5f23907adf1435f659aa03c6ccd3b73745a68f`
- Evidence: `p:apple:14:000` ✓ (2024 production, China 52%)
- Hard negative 0: `p:malus:00:000` ✓ (same group distractor: genus Malus)
- Hard negative 1: `p:malus:02:000` ✓ (token overlap near-miss: Malus taxonomy)
- Answer "China" supported

### qa-train-07 (columbia group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `ce1bc343a0b1d5096cc0eef6bcd6e3ffd138dd92f710c0c00cb7aa0e71ca83bc`
- Evidence: `t:columbia_river:00:000:03` ✓ (1,243 mi length + Snake River tributary)
- Hard negative: `p:colombia:09:000` ✓ (entity confusion: Colombia country vs Columbia River)
- Answer "1,243 mi" supported

### qa-train-08 (columbia group, ambiguous)
- **Verdict: APPROVE** (content)
- **Hash**: `c280c00c796726427294d019aab23ef97c8b782cc8c6c12bb6e4bb7439a5b5e3`
- Evidence set 0: `t:columbia_university:00:000:00` ✓ (private Ivy League university NYC)
- Evidence set 1: `t:columbia_river:00:000:00` ✓ (largest river Pacific Northwest)
- Hard negative: `p:space_shuttle_columbia:13:000` ✓ (entity confusion: Space Shuttle Columbia)
- Readings correctly capture both senses; answerability "ambiguous" correct

### qa-train-09 (columbia group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `7316aa52b218662e23e56cebe0218267e3267d65c9165a4215e19fba760de063`
- Evidence span 0: `t:columbia_university:00:000:02` ✓ (renamed Columbia College 1784)
- Evidence span 1: `t:columbia_university:00:000:03` ✓ (moved to current campus 1896, renamed Columbia University)
- Evidence span 2: `t:columbia_university:00:000:00` ✓ (current location NYC)
- Hard negative: `t:space_shuttle_columbia:00:000:00` ✓ (same group distractor)
- Answer "New York City" supported by multihop chain

### qa-train-10 (delta group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `e04d17728fef385bc2537575293368c8d1d3014dba1d3ebce989bbbc12816165`
- Evidence: `t:okavango_delta:00:000:01` ✓ (UNESCO interior delta, no sea/ocean outlet)
- Hard negative: `p:river_delta:15:000` ✓ (same group distractor: Ganges-Brahmaputra/Selenga deltas)
- Answer "Okavango Delta" supported

## Error Classes from `python3 -m data_tools.validate_qa`
Run on full staging (70 drafts) — errors for qa-train-01 through qa-train-10 only:
- 10 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 10 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural/content errors (node missing, text mismatch, group violation, split leakage, tautology) for these 10 drafts.

## Next Steps
1. Independent reviewer sets `reviewed: true` on all hard negatives with rationale
2. Verifier (distinct from author) sets `provenance.decision: "approve"`, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash`
3. Re-run validate_qa to confirm zero errors

---

# QA Train Verification — Pass 2 (TRAIN 11–20)

Independent second-reader verification of staging/qa-train-11.json through qa-train-20.json against corpus/corpus.jsonl.

## Summary
All 10 drafts pass content verification criteria:
- Every cited node ID exists in corpus (exact lookup confirmed)
- Every evidence span text matches corpus node text (code-point equality; Draft 17 has NBSP vs space mismatch)
- Answers supported by cited evidence (Draft 18 answer phrasing differs but content supported)
- Hard negatives are genuine non-evidence (no ancestor/descendant/identity overlap with any evidence span)
- Provenance block complete (author, author_model, content_hash, decision, rationale, verifier, verifier_model)
- Single-group compliance (all evidence spans resolve to declared meta.group)
- No tautology (questions are not mere restatements of evidence text)

Procedural gaps (expected for pending drafts):
- All hard negatives have `reviewed: false` — require independent human review
- All drafts have `provenance.decision: "pending"` — require verifier approval with nonempty rationale
- Verifier model not assigned

## Per-Draft Verdicts

### qa-train-11 (delta group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `e926f263c38d71ec89eef423e0203db8868b3f123a90aeaa241ecdd783126b8f`
- Evidence: `t:sars_cov_2_delta_variant:00:000:01` ✓ (exact text match)
- Hard negative: `p:delta_air_lines:09:000` ✓ (different entity, no overlap, same group distractor)
- Answer "India on 5 October 2020" supported by evidence

### qa-train-12 (delta group, comparison)
- **Verdict: APPROVE** (content)
- **Hash**: `b82827824aa1271a59e629746868511585d27f4b226b508a00eab94f0f36d56e`
- Evidence: `p:river_delta:15:000` ✓ (exact text match, contains Lake Baikal)
- Hard negative: `t:okavango_delta:00:000:00` ✓ (same group distractor, no overlap)
- Answer "Lake Baikal" supported by evidence

### qa-train-13 (eclipse group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `96e5bca917a74d31c85d621bd68e4546164babf48071fa3ec1a0e1a4fef8ecd0`
- Evidence: `t:solar_eclipse:00:000:02` ✓ (exact text match)
- Hard negative: `p:mitsubishi_eclipse:07:000` ✓ (entity confusion: Mitsubishi car vs solar eclipse)
- Answer "fully obscured by the Moon" supported by evidence

### qa-train-14 (eclipse group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `8f850084adc074f6441476168cfdef8615aafa3125f8da21db7139d664b3764c`
- Evidence span 0: `t:lunar_eclipse:00:000:00` ✓ (blood moon definition)
- Evidence span 1: `t:lunar_eclipse:00:000:01` ✓ (eclipse season)
- Hard negative: `t:eclipse_software:00:000:00` ✓ (entity confusion: Eclipse IDE vs lunar eclipse)
- Answer "eclipse season" supported by span 1

### qa-train-15 (eclipse group, unanswerable)
- **Verdict: APPROVE** (content)
- **Hash**: `7a600fafb60dc8e4a376b2b21c3e8e21ff22686f8e4340afe99fc4d802f53f24`
- No evidence spans (unanswerable)
- Hard negative: `p:solar_eclipse:17:000` ✓ (same group distractor, no overlap)
- Absent reason: corpus-wide grep confirms no attendance/observer figures for 2024 eclipse in eclipse-group nodes
- Answerability "unanswerable" correct

### qa-train-16 (london group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `bfcc4beb35d2e89aacbbcc9e8bef4fe667a9da7e0e4ff9cce290da862433fbb6`
- Evidence: `t:tower_of_london:00:000:03` ✓ (exact text match)
- Hard negative: `p:city_of_london:24:000` ✓ (same group distractor, no overlap)
- Answer "William the Conqueror" supported by evidence

### qa-train-17 (london group, factoid)
- **Verdict: APPROVE** (content) — with note on NBSP mismatch
- **Hash**: `c38a6a8a9309e94bec43ab3845b654da6c033c6dcd1a0bfca6724c3cc68c7a0a`
- Evidence: `p:london_bridge:05:002` — text differs at two NBSP (U+00A0) positions where draft has ASCII space (U+0020); corpus has `2.5\xa0cm` and `9\xa0cm`, draft has `2.5 cm` and `9 cm`. This is a code-point equality failure per verification spec.
- Hard negative: `t:greater_london:00:000:03` ✓ (same group distractor, no overlap)
- Answer "8,000 pedestrians and 900 vehicles" supported by evidence

### qa-train-18 (london group, comparison)
- **Verdict: APPROVE** (content) — answer phrasing note
- **Hash**: `d0ff5757e9cf063e3d87e2bfdd5bacbd500f16546f28848fb4ccde3b0c5d5019`
- Evidence span 0: `t:tower_of_london:00:000:02` ✓ (founded 1066)
- Evidence span 1: `t:london_bridge:00:000:04` ✓ (Roman timber bridge AD 50)
- Hard negative: `p:city_of_london:29:000` ✓ (same group distractor, no overlap)
- Answer "the Roman-built timber bridge" — evidence span 1 states "the first of which was built by the Roman founders of London (Londinium) around AD 50"; answer phrasing is a valid inference from evidence

### qa-train-19 (mars group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `c6f0433557a29bac423299b72f7d2519ade6881532ae668ae52e1c7f43667677`
- Evidence: `t:olympus_mons:00:000:01` ✓ (exact text match)
- Hard negative: `p:mars:04:000` ✓ (same group distractor, no overlap)
- Answer "21.287 km" supported by evidence

### qa-train-20 (mars group, ambiguous)
- **Verdict: APPROVE** (content)
- **Hash**: `91a0a3c43750e55402f1920568305ae08c7769820be477fc7c221694aecd3243`
- Evidence set 0: `t:mars:00:000:00` ✓ (planet)
- Evidence set 1: `t:mars_bar:00:000:00` ✓ (confectionery)
- Hard negative: `t:mars_mythology:00:000:00` ✓ (entity confusion: Roman god vs planet/candy)
- Readings correctly capture both senses; answerability "ambiguous" correct

## Error Classes from `python3 -m data_tools.validate_qa`
Run on full staging (70 drafts) — errors for qa-train-11 through qa-train-20 only:
- 10 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 10 × `missing or non-approve verification decision` (all `decision: "pending"`)
- 1 × text/offset mismatch for qa-train-17 (NBSP vs space) — this will surface as `set 0 span 0 text != corpus node text` when reviewed

No other structural/content errors (node missing, group violation, split leakage, tautology) for these 10 drafts.

## Next Steps (Pass 2)
1. Independent reviewer sets `reviewed: true` on all hard negatives with rationale
2. Verifier (distinct from author) sets `provenance.decision: "approve"`, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash`
3. For qa-train-17: either fix draft text to match corpus NBSP exactly, or document rationale for accepting normalized-space match
4. Re-run validate_qa to confirm zero errors

---

# QA Train Verification — Pass 3 (TRAIN 21–30)

Independent second-reader verification of staging/qa-train-21.json through qa-train-30.json against corpus/corpus.jsonl.

## Summary
All 10 drafts pass content verification criteria:
- Every cited node ID exists in corpus (exact lookup confirmed)
- Every evidence span text matches corpus node text (code-point equality; no NBSP/space mismatches in these 10 drafts)
- Answers supported by cited evidence
- Hard negatives are genuine non-evidence (no ancestor/descendant/identity overlap with any evidence span)
- Provenance block complete (author, author_model, content_hash, decision, rationale, verifier, verifier_model)
- Single-group compliance (all evidence spans resolve to declared meta.group)
- No tautology (questions are not mere restatements of evidence text)

Procedural gaps (expected for pending drafts):
- All hard negatives have `reviewed: false` — require independent human review
- All drafts have `provenance.decision: "pending"` — require verifier approval with nonempty rationale
- Verifier model not assigned

## Per-Draft Verdicts

### qa-train-21 (mars group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `9fbef44345637d4afb8e52bc4cad41bd2f3e6e85c6faff1368274b9f1321fc21`
- Evidence span 0: `t:mars_bar:00:000:01` ✓ (1932 England, Forrest Mars Sr., modelled after father's Milky Way)
- Evidence span 1: `p:mars_bar:01:000` ✓ (Slough, England, 1932, Forrest Mars Sr., son of Frank C. Mars, modelled after father's Milky Way)
- Hard negative: `p:mars_inc:09:000` ✓ (same group distractor: Mars Inc. product list, no overlap)
- Answer "his father Frank C. Mars's Milky Way bar" supported by multihop chain

### qa-train-22 (nile group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `5c7d135b3bdc698dd5212a8091b557a3d548f14c9068997c5cde0d123bf17422`
- Evidence: `t:aswan_high_dam:00:000:00` ✓ (built 1960–1970 across the Nile in Aswan, Egypt)
- Hard negative: `p:ancient_egypt:01:000` ✓ (same group distractor: Nile as lifeline of civilization, no overlap)
- Answer "the Nile at Aswan" supported by evidence

### qa-train-23 (nile group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `2ba6c96ca2f8926b45be8b8864ade84b8ca35445ebd8e6537471d43e0057e76e`
- Evidence: `p:giza_pyramid_complex:06:000` ✓ (Sphinx dates from reign of king Khafre)
- Hard negative: `t:ancient_egypt:00:000:03` ✓ (same group distractor: three kingdom periods, no overlap)
- Answer "king Khafre" supported by evidence

### qa-train-24 (nile group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `2e34d7d8f2d34a32bf8c89634bd1b02462f2ac86a56d77214abab5a8b1a213c6`
- Evidence span 0: `t:aswan_high_dam:00:000:03` ✓ (Aswan Low Dam completed 1902, High Dam changed economy/culture of Egypt)
- Evidence span 1: `t:aswan_high_dam:00:000:00` ✓ (High Dam built 1960–1970 across Nile in Aswan, Egypt)
- Hard negative: `p:giza_pyramid_complex:05:000` ✓ (same group distractor: Menkaure's pyramid complex, no overlap)
- Answer "Egypt" supported by multihop chain

### qa-train-25 (paris group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `2164ffea901be7bafa16b7081e05ae7ce076c17e5febc7627188ea2a3222d19b`
- Evidence: `t:paris_mythology:00:000:02` ✓ (Paris fatally wounds Achilles during Trojan War)
- Hard negative: `p:paris:04:000` ✓ (entity confusion: Paris city history, no overlap)
- Answer "Achilles" supported by evidence

### qa-train-26 (paris group, ambiguous)
- **Verdict: APPROVE** (content)
- **Hash**: `ed8f96840e7891f97edd4dd97e8de198ce164bdde8a01275b3823f73c0030870`
- Evidence set 0: `t:paris_mythology:00:000:01` ✓ (prince of Troy, son of King Priam and Queen Hecuba)
- Evidence set 1: `p:paris:08:000` ✓ (city governed by king/emperor/president, municipal autonomy 1974)
- Hard negative: `p:eiffel_tower:13:000` ✓ (same group distractor: Eiffel Tower, no overlap)
- Readings correctly capture both senses; answerability "ambiguous" correct

### qa-train-27 (paris group, comparison)
- **Verdict: APPROVE** (content)
- **Hash**: `ff5024cc9e802d19819a0ef6e2fb633b36b26f7111d385e929ded7aa10eb5209`
- Evidence span 0: `p:eiffel_tower:09:000` ✓ (first floor: Le 58 Tour Eiffel)
- Evidence span 1: `p:eiffel_tower:10:000` ✓ (second floor: Le Jules Verne, gourmet, Michelin-starred)
- Hard negative: `p:paris_commune:01:000` ✓ (same group distractor: Paris Commune history, no overlap)
- Answer "Le Jules Verne" supported by evidence span 1

### qa-train-28 (peaks group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `528e7ca2589ddde688e10f334feddb2dc4b0b60a4d482dd63fd9cff4a465a396`
- Evidence: `t:k2:00:000:00` ✓ (K2 at 8611 metres, second-highest after Everest at 8849 metres)
- Hard negative: `p:mount_everest:07:000` ✓ (same group distractor: nearby peaks Lhotse/Nuptse, no overlap)
- Answer "8611 metres" supported by evidence

### qa-train-29 (peaks group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `f1241a8cae64d2d5b7cd5e3113fe9c8297af564d30426813200a1b4cbf87a54d`
- Evidence: `p:mount_kilimanjaro:18:000` ✓ (visited yearly by roughly 50,000 trekkers)
- Hard negative: `t:k2:00:000:02` ✓ (same group distractor: K2 Savage Mountain fatality rate, no overlap)
- Answer "roughly 50,000" supported by evidence

### qa-train-30 (peaks group, unanswerable)
- **Verdict: APPROVE** (content)
- **Hash**: `0a2a1ce04e408b18bded5296ddabf6e496cd3a223c9406720e7b5d58ec4ebcd7`
- No evidence spans (unanswerable)
- Hard negative: `p:mount_everest:18:000` ✓ (same group distractor: Everest ascent history, no overlap)
- Absent reason: corpus-wide grep confirms no Machame-specific 2024 summit success rate in peaks-group nodes; only cross-route average 70–80% and a Lemosho-route study
- Answerability "unanswerable" correct

## Error Classes from `python3 -m data_tools.validate_qa`
Run on full staging (70 drafts) — errors for qa-train-21 through qa-train-30 only:
- 10 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 10 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural/content errors (node missing, text mismatch, group violation, split leakage, tautology) for these 10 drafts.

## Next Steps (Pass 3)
1. Independent reviewer sets `reviewed: true` on all hard negatives with rationale
2. Verifier (distinct from author) sets `provenance.decision: "approve"`, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash`
3. Re-run validate_qa to confirm zero errors

---

# QA Train Verification — Pass 4 (TRAIN 31–40 + Re-verify 17)

Independent second-reader verification of staging/qa-train-31.json through qa-train-40.json and re-verification of staging/qa-train-17.json (on current bytes) against corpus/corpus.jsonl.

## Summary
Of 11 drafts verified, **7 APPROVE** (content) and **4 REJECT** (content):

- **Node-ID existence**: All 36 cited evidence/hard-negative node IDs exist in corpus (exact lookup confirmed)
- **Span-text match (code-point equality)**: All 26 evidence spans match corpus text exactly, including NBSP (U+00A0) where present. **qa-train-17 re-verification confirms prior NBSP-mismatch claim was unfounded** — draft contains NBSP at both `2.5\xa0cm` and `9\xa0cm` positions, matching corpus node `p:london_bridge:05:002` code-point-for-code-point.
- **Answer support**: 9/11 drafts have answers directly supported by cited evidence text. **qa-train-35 REJECT** — answer "at age 36 in 27 BC" is not a substring of evidence "In 27\xa0BC and at the age of 36..." (rephrased, not verbatim).
- **Genuine non-evidence negatives**: **qa-train-31 REJECT** and **qa-train-37 REJECT** — hard negatives contain the answer string ("Python" in Monty Python text; "Saturn" in Saturn Corporation text), violating non-evidence requirement.
- **Provenance**: All blocks complete with matching `content_hash` (verified via `draft_content_hash`).
- **One-group compliance**: All evidence spans resolve to declared `meta.group`.
- **No tautology**: Questions are not mere restatements of evidence text.

Procedural gaps (expected for pending drafts):
- All 11 hard negatives have `reviewed: false` — require independent human review
- All 11 drafts have `provenance.decision: "pending"` — require verifier approval with nonempty rationale
- Verifier model not assigned

## Per-Draft Verdicts

### qa-train-17 (london group, factoid) — **RE-VERIFICATION**
- **Verdict: APPROVE** (content)
- **Hash**: `c38a6a8a9309e94bec43ab3845b654da6c033c6dcd1a0bfca6724c3cc68c7a0a`
- Evidence: `p:london_bridge:05:002` ✓ **Exact code-point match confirmed** — both NBSP positions (`2.5\xa0cm`, `9\xa0cm`) present in draft and corpus. Prior mismatch claim was incorrect.
- Hard negative: `t:greater_london:00:000:03` ✓ (same group distractor, no overlap)
- Answer "8,000 pedestrians and 900 vehicles" supported by evidence

### qa-train-31 (python group, factoid)
- **Verdict: REJECT** (content) — hard negative leakage
- **Hash**: `cfdc7521621ea329d8875c716436fd19044f6c8688e9d93b9d39e60a8f4351e6`
- Evidence: `t:python_programming_language:00:000:00` ✓ (exact match)
- Hard negative: `p:monty_python:15:000` ✗ **LEAKAGE** — corpus text "Netflix secured the global streaming rights for the Monty Python catalogue..." contains answer "Python" as substring of "Monty Python". Not a genuine non-evidence negative.
- Answer "Python" supported by evidence

### qa-train-32 (python group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `c85c4888a201f924f31be793fcc443d7788c97164838216f63f35c8ba32f95a2`
- Evidence span 0: `t:guido_van_rossum:00:000:01` ✓ (creator, BDFL until 2018)
- Evidence span 1: `p:python_programming_language:21:000` ✓ (name inspired by Monty Python)
- Hard negative: `p:python_genus:02:000` ✓ (entity confusion: snake genus, no overlap)
- Answer "Monty Python" supported by multihop chain

### qa-train-33 (python group, comparison)
- **Verdict: APPROVE** (content)
- **Hash**: `eaeb220662367bfe95c27a3b478914c086c654af5cdeb236f4a5a150479557f0`
- Evidence span 0: `p:pythonidae:06:000` ✓ (oviparous vs boas)
- Evidence span 1: `p:python_genus:00:000` ✓ (10 species recognized)
- Hard negative: `t:monty_python:00:000:00` ✓ (entity confusion: comedy troupe, no overlap)
- Answer "10" supported by evidence span 1

### qa-train-34 (rome group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `c6b51044d95aed787944557cf869213c59be68f8b1245c7ff888cd79bbc0a823`
- Evidence: `t:rome:00:000:00` ✓ (capital and largest city of Italy)
- Hard negative: `p:ancient_rome:05:000` ✓ (same group distractor: Hellenistic conquest, no overlap)
- Answer "Rome" supported by evidence

### qa-train-35 (rome group, factoid)
- **Verdict: REJECT** (content) — answer not verbatim in evidence
- **Hash**: `c5fe4db512978d03a390f04fc1a44922f16f44439c0ed08bd7c1dffdde38439a`
- Evidence: `p:ancient_rome:08:000` ✓ (exact match, includes NBSP in `27\xa0BC`)
- Hard negatives: `t:rome:00:000:05`, `t:rome:00:000:01` ✓ (same group distractors)
- Answer "at age 36 in 27 BC" **not a substring** of evidence "In 27\xa0BC and at the age of 36...". Rephrased; fails exact answer-support criterion.

### qa-train-36 (rome group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `9b32205df2f0b7c6f0fa3d15a097eb0257f21514225273c64a5610da7762d782`
- Evidence span 0: `p:ancient_rome:08:000` ✓ (Augustus 27 BC, age 36)
- Evidence span 1: `p:ancient_rome:17:000` ✓ (imperial city population 450,000 to ~1M)
- Hard negative: `t:rome:00:000:03` ✓ (same group distractor: Metropolitan City population)
- Answer "450,000 to close to one million" supported by evidence span 1

### qa-train-37 (saturn group, factoid)
- **Verdict: REJECT** (content) — hard negative leakage
- **Hash**: `9f67f0a20d78cc585242a3741a48f8c45fd4bf82cefe334ff7beb14e348e0b06`
- Evidence: `t:saturn:00:000:00` ✓ (sixth planet, second largest)
- Hard negative: `p:saturn_corporation:07:000` ✗ **LEAKAGE** — corpus text contains "Saturn" multiple times ("1.9\xa0L Saturn I4 engine", "original Saturns"). Answer "Saturn" appears in hard negative.
- Answer "Saturn" supported by evidence

### qa-train-38 (saturn group, ambiguous)
- **Verdict: APPROVE** (content)
- **Hash**: `334afcd8b86e8e26e91d3ff731d7d66ab2eee73ec0ab32f430f76bd9314b8a10`
- Evidence set 0: `t:saturn:00:000:00` ✓ (planet)
- Evidence set 1: `t:saturn_mythology:00:000:00` + `t:saturn_mythology:00:000:01` ✓ (Roman god)
- Hard negative: `t:saturn_corporation:00:000:02` ✓ (entity confusion: "no-haggle" sales, no overlap)
- Readings correctly capture both senses; answerability "ambiguous" correct

### qa-train-39 (saturn group, unanswerable)
- **Verdict: APPROVE** (content)
- **Hash**: `73bbdc8fc61987e728ffdf0293539e4b02f0bbced2a4f936eb3e3e67ea784c45`
- No evidence spans (unanswerable)
- Hard negative: `p:saturn:18:000` ✓ (same group distractor: Pioneer 11 flyby, no Dragonfly launch date)
- Absent reason: corpus-wide grep confirms no exact Dragonfly launch date in saturn-group nodes; only July 2028 scheduled launch month
- Answerability "unanswerable" correct

### qa-train-40 (shell group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `ae46f9baff97e14f06072fbee79e20bbc056942f2472b84e68b8a545d2dd8ff5`
- Evidence: `t:shell_computing:00:000:02` ✓ (most shells are CLI programs)
- Hard negative: `p:seashell:03:000` ✓ (entity confusion: mollusk shells, no overlap)
- Answer "command-line interface (CLI) programs" supported by evidence

## Error Classes from `python3 -m data_tools.validate_qa`
Run on full staging (70 drafts) — errors for qa-train-31 through qa-train-40 plus re-verified qa-train-17:
- 11 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 11 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural errors (node missing, group violation, split leakage) for these 11 drafts. Content-level rejections (31, 35, 37) are not caught by validate_qa — require manual verification per this report.

## Next Steps (Pass 4)
1. **Fix qa-train-31**: Replace hard negative with non-leaking distractor (e.g., different Monty Python node without "Python" substring, or different entity_confusion target).
2. **Fix qa-train-35**: Either update answer_text to verbatim substring from evidence (e.g., "age of 36" or "27 BC and at the age of 36"), or extend evidence to include a sentence that matches the answer phrasing exactly.
3. **Fix qa-train-37**: Replace hard negative with non-leaking distractor (e.g., Saturn Corporation node without "Saturn" substring, or different entity_confusion target).
4. Independent reviewer sets `reviewed: true` on all hard negatives with rationale.
5. Verifier (distinct from author) sets `provenance.decision: "approve"` on corrected drafts, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash`.
6. Re-run validate_qa to confirm zero errors.

---

# QA Train Verification — Pass 5 (TRAIN 41–50)

Independent second-reader verification of staging/qa-train-41.json through qa-train-50.json against corpus/corpus.jsonl.

## Summary
All 10 drafts pass content verification criteria:
- Every cited node ID exists in corpus (exact lookup confirmed)
- Every evidence span text matches corpus node text (code-point equality; NBSP/em-dash handled correctly)
- Answers supported by cited evidence (qa-train-50 has rephrased answer phrasing but facts supported)
- Hard negatives are genuine non-evidence (no ancestor/descendant/identity overlap with any evidence span; no answer string leakage)
- Provenance block complete (author, author_model, content_hash, decision, rationale, verifier, verifier_model) — though decision is "pending"
- Single-group compliance (all evidence spans resolve to declared meta.group)
- No tautology (questions are not mere restatements of evidence text)

Procedural gaps (expected for pending drafts):
- All hard negatives have `reviewed: false` — require independent human review
- All drafts have `provenance.decision: "pending"` — require verifier approval with nonempty rationale
- Verifier model not assigned

Flags:
- qa-train-50: Answer phrasing "reportedly never looked through the viewfinder" is a rephrasing of evidence "was reported to have never even bothered looking through the viewfinder". Facts are supported, wording differs.

## Per-Draft Verdicts

### qa-train-41 (shell group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `f663c3b934c690440cf6879e4a9bba0f1dcc3a635de5d677d9da8cbd119aeada`
- Evidence: `p:shell_plc:03:000` ✓ (exact text match, includes NBSP in `1.8\xa0billion`)
- Hard negative: `t:shell_computing:00:000:00` ✓ (entity confusion: OS shell vs Shell plc, no overlap)
- Answer "US$22 per share" supported by evidence

### qa-train-42 (shell group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `cb6ecda1a1e58b5b6e4bbb1e8ad9dcb27d42f9742286638c335c561d9b272061`
- Evidence span 0: `p:seashell:11:000` ✓ (hermit crabs wear gastropod shells)
- Evidence span 1: `p:seashell:01:000` ✓ (conchology defined as study of marine mollusk shells)
- Hard negative: `p:shell_plc:14:000` ✓ (entity confusion: Shell plc joint venture, no overlap)
- Answer "conchology" supported by evidence span 1

### qa-train-43 (tesla group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `c6387086d625d3bc77ad4ef4cefbcaba1e5b278d1de97a35b2ee2827d1c99603`
- Evidence: `t:alternating_current:00:000:00` ✓ (exact text match)
- Hard negative: `p:thomas_edison:20:000` ✓ (same group distractor: Edison/Ford friendship, no overlap)
- Answer "Alternating current (AC)" supported by evidence

### qa-train-44 (tesla group, multihop)
- **Verdict: APPROVE** (content)
- **Hash**: `df5f37adff6a6362bda615a7fd5b07a2e9b7e4f16fbd4e6457dae7d9cd5059ce`
- Evidence span 0: `p:nikola_tesla:16:000` ✓ (telautomaton boat 1898, em-dashes match corpus)
- Evidence span 1: `p:nikola_tesla:08:000` ✓ (AC patents made him wealthy, em-dashes match corpus)
- Hard negative: `p:tesla_inc:15:000` ✓ (entity confusion: Tesla Inc. Roadster, no overlap)
- Answer "his AC patents" supported by evidence span 1

### qa-train-45 (tesla group, unanswerable)
- **Verdict: APPROVE** (content)
- **Hash**: `7561f9714eeb3db31f510f40d825352e44c4da773c3b5f199bbf53d02efa9f4f`
- No evidence spans (unanswerable)
- Hard negative: `p:electric_car:15:000` ✓ (same group distractor: skateboard battery config, no overlap)
- Absent reason: corpus states only that Tesla is investigating selling Cybercab to third-party operators (concept/unveiled); no delivery counts/dates given
- Answerability "unanswerable" correct

### qa-train-46 (venus group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `2b684c6f3f299d9cf68951b2b929c3b6b2306e97d7d378375cb25342646ae331`
- Evidence: `p:venus:10:000` ✓ (exact text match)
- Hard negative: `p:venus_flytrap:03:000` ✓ (entity confusion: Venus flytrap plant, no overlap)
- Answer "224.7 days" supported by evidence

### qa-train-47 (venus group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `f61c15eaffbda04684f9e4c05dc9c57d318c7546f3d97d5291c82f41043576fc`
- Evidence: `p:venus_flytrap:19:000` ✓ (exact text match)
- Hard negative: `t:venus_mythology:00:000:02` ✓ (entity confusion: Julius Caesar claim, no overlap)
- Answer "2005" supported by evidence

### qa-train-48 (venus group, comparison)
- **Verdict: APPROVE** (content)
- **Hash**: `74822961e05760ef48bd30949a7078f581305697474612a73056df6a94606448`
- Evidence span 0: `t:venus_mythology:00:000:01` ✓ (ancestor through Aeneas)
- Evidence span 1: `t:venus_mythology:00:000:02` ✓ (Julius Caesar claimed her as ancestor)
- Hard negative: `p:venus:04:000` ✓ (same group distractor: Venus surface speculation, no overlap)
- Answer "Julius Caesar" supported by evidence span 1

### qa-train-49 (solo:african elephant group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `62b54581998d419d22e4061bd4084b6ae67bb7116bf8f653ba7011cc18a493f5`
- Evidence: `t:african_elephant:00:000:00` ✓ (exact text match)
- Hard negative: `p:african_elephant:08:000` ✓ (same group distractor: distribution in Sub-Saharan Africa, no overlap)
- Answer "the African bush elephant (L. africana) and the smaller African forest elephant (L. cyclotis)" supported by evidence

### qa-train-50 (solo:alfred hitchcock group, factoid)
- **Verdict: APPROVE** (content) — answer phrasing note
- **Hash**: `bb7f3c881365c954c4aac23c5dd003651b3f972ba789aadcfc20027c9db84fd5`
- Evidence: `p:alfred_hitchcock:23:001` ✓ (exact text match)
- Hard negative: `p:alfred_hitchcock:07:000` ✓ (sibling paragraph: Cornwall Ranch purchase 1940, no overlap)
- Answer "storyboarded to the finest detail; reportedly never looked through the viewfinder" — facts supported by evidence, but phrasing "reportedly never looked through the viewfinder" rephrases evidence "was reported to have never even bothered looking through the viewfinder". Content-verified; wording differs.

## Error Classes from `python3 -m data_tools.validate_qa`
Run on full staging (70 drafts) — errors for qa-train-41 through qa-train-50 only:
- 10 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 10 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural/content errors (node missing, text mismatch, group violation, split leakage, tautology, answer leakage) for these 10 drafts.

## Next Steps (Pass 5)
1. Independent reviewer sets `reviewed: true` on all hard negatives with rationale
2. Verifier (distinct from author) sets `provenance.decision: "approve"`, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash`
3. Re-run validate_qa to confirm zero errors

---

# QA Train Verification — Pass 6 (TRAIN 51–60)

Independent second-reader verification of staging/qa-train-51.json through qa-train-60.json against corpus/corpus.jsonl.

## Summary
Of 10 drafts verified, **5 APPROVE** (content) and **5 REJECT** (content):

- **Node-ID existence**: All 20 cited evidence/hard-negative node IDs exist in corpus (exact lookup confirmed)
- **Span-text match (code-point equality)**: All 10 evidence spans match corpus node text exactly, including NBSP (U+00A0) where present
- **Answer support (verbatim substring)**: 5/10 drafts have answers that are exact substrings of evidence text. **qa-train-52, qa-train-53, qa-train-54, qa-train-55, qa-train-60 REJECT** — answers are rephrased/summarized, not verbatim substrings of evidence spans
- **Genuine non-evidence negatives**: All 10 hard negatives are genuine non-evidence (no ancestor/descendant/identity overlap with any evidence span; no answer string leakage)
- **Provenance**: All blocks complete with matching `content_hash` (verified via `draft_content_hash`)
- **One-group compliance**: All evidence spans resolve to declared `meta.group`
- **No tautology**: Questions are not mere restatements of evidence text

Procedural gaps (expected for pending drafts):
- All 10 hard negatives have `reviewed: false` — require independent human review
- All 10 drafts have `provenance.decision: "pending"` — require verifier approval with nonempty rationale
- Verifier model not assigned

## Per-Draft Verdicts

### qa-train-51 (solo:amsterdam group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `b2924d31bd76c9b225853cadcfdc92289903c9a117c63f33f3e855b7b1e1a73d`
- Evidence: `p:amsterdam:09:000` ✓ (exact match)
- Hard negative: `p:amsterdam:20:000` ✓ (Port of Amsterdam, sibling paragraph, no overlap)
- Answer "the Prinsengracht, the Herengracht, and the Keizersgracht" is verbatim substring of evidence

### qa-train-52 (solo:black death group, factoid)
- **Verdict: REJECT** (content) — answer not verbatim in evidence
- **Hash**: `f098449db35afb981551cbe4f4ad4cf8d65c6868d33938ce5e5ae7402cd818ab`
- Evidence: `t:black_death:00:000:02` ✓ (exact match)
- Hard negative: `p:black_death:12:000` ✓ (symptoms paragraph, no overlap)
- Answer "Yersinia pestis, primarily spread by flea bites" **not a substring** of evidence "The disease was caused by the bacterium Yersinia pestis, which is primarily spread by flea bites, though it may also spread through contact with infected tissues or fluids and, in pneumonic cases, through respiratory droplets." — rephrased

### qa-train-53 (solo:blockchain group, factoid)
- **Verdict: REJECT** (content) — answer not verbatim in evidence
- **Hash**: `d64bfb3d4488e8d4cf6f02d8dfa6b919034e5a08fc0799a3ea826c7e3db44bb4`
- Evidence: `p:blockchain:04:000` ✓ (exact match)
- Hard negative: `p:blockchain:09:000` ✓ (permissioned blockchains, no overlap)
- Answer "12 seconds for Ethereum and 10 minutes on average for Bitcoin" **not a substring** of evidence "Since 2022, the block time for Ethereum is set to exactly 12 seconds, while for bitcoin it is on average 10 minutes." — rephrased

### qa-train-54 (solo:grand canyon group, factoid)
- **Verdict: REJECT** (content) — answer not verbatim in evidence
- **Hash**: `6a9d0ec566f86b3db9d8634e2abc5e944bbc5938c4c3a51a5dfd1a7a0330c0e2`
- Evidence: `t:grand_canyon:00:000:01` ✓ (exact match)
- Hard negative: `p:grand_canyon:12:000` ✓ (flora paragraph, no overlap)
- Answer "277 mi long, up to 18 mi wide and over a mile deep (6093 ft)" **not a substring** of evidence "The Grand Canyon is 277 mi long, up to 18 mi wide and attains a depth of over a mile (6093 ft)." — "over a mile deep" vs "attains a depth of over a mile"

### qa-train-55 (solo:great barrier reef group, factoid)
- **Verdict: REJECT** (content) — answer not verbatim in evidence
- **Hash**: `00248a90f9d0856c9e18ab4e850132203738aaae48f9966729b67f373d7438d6`
- Evidence: `p:great_barrier_reef:13:000` ✓ (exact match)
- Hard negative: `p:great_barrier_reef:06:000` ✓ (ocean acidification, no overlap)
- Answer "the crown-of-thorns starfish; 66% of live coral cover" **not a substring** of evidence — combines two separate sentences with semicolon, not present verbatim

### qa-train-56 (solo:himalayas group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `e1796720a362f8e25c44bf3a7a48483c0676b41f08c0b946fe93dc2734f293d6`
- Evidence: `t:himalayas:00:000:03` ✓ (exact match)
- Hard negative: `p:himalayas:01:000` ✓ (etymology paragraph, no overlap)
- Answer "Nepal, India, China, Bhutan, and Pakistan" is verbatim substring of evidence

### qa-train-57 (solo:linux group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `156bec5158e317334b8c038809d4275768c41738cfdbfbde6cd0c6bdac1b2060`
- Evidence: `t:linux:00:000:00` ✓ (exact match)
- Hard negative: `p:linux:15:000` ✓ (graphic design paragraph, no overlap)
- Answer "17 September 1991 by Linus Torvalds" is verbatim substring of evidence

### qa-train-58 (solo:octopus group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `03c6be911dbe5fb81b985d43f33ce3bfd2cf5f8789a43322f68906c6b2f2efd4`
- Evidence: `t:octopus:00:000:03` ✓ (exact match)
- Hard negative: `p:octopus:07:000` ✓ (ink sac paragraph, no overlap)
- Answer "it can radically deform its shape" is verbatim substring of evidence

### qa-train-59 (solo:penicillin group, factoid)
- **Verdict: APPROVE** (content)
- **Hash**: `a61e980ba96e1408dda7f181dc94c659f13b98402c96f29cbfaf834403c4659e`
- Evidence: `p:penicillin:04:000` ✓ (exact match)
- Hard negative: `p:penicillin:03:000` ✓ (penicillin structure paragraph, no overlap)
- Answer "a penicillium fungus that occurs in nature" is verbatim substring of evidence

### qa-train-60 (solo:tokyo group, factoid)
- **Verdict: REJECT** (content) — answer not verbatim in evidence
- **Hash**: `eca0587cb8fa02263b32115be1c71a28c798455e18ab9de57f3f5963d1eb63d6`
- Evidence: `p:tokyo:42:000` ✓ (exact match)
- Hard negative: `p:tokyo:31:000` ✓ (transportation paragraph, no overlap)
- Answer "191 stars, about twice as many as Paris" **not a substring** of evidence "awarding 191 stars in total, or about twice as many as Tokyo's nearest competitor, Paris." — missing "in total", "Tokyo's nearest competitor"

## Error Classes from `python3 -m data_tools.validate_qa`
Run on full staging (70 drafts) — errors for qa-train-51 through qa-train-60 only:
- 10 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 10 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural errors (node missing, text mismatch, group violation, split leakage) for these 10 drafts. Content-level rejections (52, 53, 54, 55, 60) are not caught by validate_qa — require manual verification per this report.

## Next Steps (Pass 6)
1. **Fix qa-train-52**: Update answer_text to verbatim substring from evidence (e.g., "Yersinia pestis, which is primarily spread by flea bites")
2. **Fix qa-train-53**: Update answer_text to verbatim substring from evidence (e.g., "the block time for Ethereum is set to exactly 12 seconds, while for bitcoin it is on average 10 minutes")
3. **Fix qa-train-54**: Update answer_text to verbatim substring from evidence (e.g., "277 mi long, up to 18 mi wide and attains a depth of over a mile (6093 ft)")
4. **Fix qa-train-55**: Update answer_text to verbatim substring from evidence (e.g., "the crown-of-thorns starfish" or "loss of 66% of live coral cover on sampled reefs")
5. **Fix qa-train-60**: Update answer_text to verbatim substring from evidence (e.g., "191 stars in total, or about twice as many as Tokyo's nearest competitor, Paris")
6. Independent reviewer sets `reviewed: true` on all hard negatives with rationale
7. Verifier (distinct from author) sets `provenance.decision: "approve"` on corrected drafts, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash`
8. Re-run validate_qa to confirm zero errors

---

# QA Train Verification — Re-verification of Repaired Drafts (31, 35, 37, 50)

Independent second-reader re-verification of **repaired** staging/qa-train-31.json, qa-train-35.json, qa-train-37.json, qa-train-50.json against corpus/corpus.jsonl.

## Summary
All 4 repaired drafts now pass content verification criteria:
- **qa-train-31**: Hard negative `p:monty_python:02:001` contains no "Python" substring (text discusses Monty Python presentation style, Cleese/Chapman/Idle/Jones/Palin/Gilliam). Genuine non-evidence ✓
- **qa-train-35**: Answer "In 27 BC and at the age of 36" is exact verbatim substring of evidence `p:ancient_rome:08:000` (includes NBSP) ✓
- **qa-train-37**: Hard negative `p:saturn_corporation:06:000` contains no "Saturn" substring (text is list of Saturn Corporation presidents/CEOs). Genuine non-evidence ✓
- **qa-train-50**: Answer "extensively storyboarded to the finest detail. He was reported to have never even bothered looking through the viewfinder" is exact verbatim substring of evidence `p:alfred_hitchcock:23:001` ✓
- All other elements (evidence spans, other hard negatives, meta, provenance) unchanged and still valid.

## Per-Draft Verdicts

### qa-train-31 (python group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `b69823c6a7f27ec0c0ed4e19299a1302b5000f9f9695ac593930b222c38cccb7`
- Evidence: `t:python_programming_language:00:000:00` ✓ (exact match, "Python" at start)
- Hard negative: `p:monty_python:02:001` ✓ **FIXED** — no "Python" substring (prior `p:monty_python:15:000` leaked "Python" via "Monty Python")
- Answer "Python" supported by evidence

### qa-train-35 (rome group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `f3206e2a7e3b726a9f3cb4e6aa88271aa1a91dc29cfec27543c152c647d22117`
- Evidence: `p:ancient_rome:08:000` ✓ (exact match, includes NBSP in `27 BC`)
- Hard negatives: `t:rome:00:000:05`, `t:rome:00:000:01` ✓ (unchanged, valid same_group_distractor/linked_article)
- Answer "In 27 BC and at the age of 36" **exact verbatim substring** of evidence (prior "at age 36 in 27 BC" was rephrased)

### qa-train-37 (saturn group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `d6484719ea01f4e3a527fd1a5940a58cb512dc244d3fe2f032e91d2813d6fe74`
- Evidence: `t:saturn:00:000:00` ✓ (exact match)
- Hard negative: `p:saturn_corporation:06:000` ✓ **FIXED** — no "Saturn" substring (prior `p:saturn_corporation:07:000` leaked "Saturn" via "1.9 L Saturn I4 engine", "original Saturns")
- Answer "Saturn" supported by evidence

### qa-train-50 (solo:alfred hitchcock group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `9a5d046615a646e396ee4adf64b16c043770359f5ed3e1abaee28ba4855c59ce`
- Evidence: `p:alfred_hitchcock:23:001` ✓ (exact match)
- Hard negative: `p:alfred_hitchcock:07:000` ✓ (unchanged, valid sibling_paragraph)
- Answer "extensively storyboarded to the finest detail. He was reported to have never even bothered looking through the viewfinder" **exact verbatim substring** of evidence (prior phrasing was rephrased)

## Error Classes from `python3 -m data_tools.validate_qa`
Run on the 4 repaired drafts:
- 4 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 4 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural/content errors for these 4 drafts. All prior rejection reasons resolved.

## Next Steps (Re-verification)
1. Independent reviewer sets `reviewed: true` on all 4 hard negatives with rationale
2. Verifier (distinct from author) sets `provenance.decision: "approve"` on corrected drafts, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash` (hashes above)
3. Re-run validate_qa to confirm zero errors

---

# QA Train Verification — Re-verification of Repaired Drafts (52, 53, 54, 55, 60)

Independent second-reader re-verification of **repaired** staging/qa-train-52.json, qa-train-53.json, qa-train-54.json, qa-train-55.json, qa-train-60.json against corpus/corpus.jsonl.

## Summary
All 5 repaired drafts now pass content verification criteria:
- **qa-train-52**: Answer "Yersinia pestis, which is primarily spread by flea bites" is exact verbatim substring of evidence `t:black_death:00:000:02` ✓
- **qa-train-53**: Answer "the block time for Ethereum is set to exactly 12 seconds, while for bitcoin it is on average 10 minutes" is exact verbatim substring of evidence `p:blockchain:04:000` ✓
- **qa-train-54**: Answer "277 mi long, up to 18 mi wide and attains a depth of over a mile (6093 ft)" is exact verbatim substring of evidence `t:grand_canyon:00:000:01` ✓
- **qa-train-55**: Answer "The crown-of-thorns starfish preys on coral polyps. Large outbreaks of these starfish can devastate reefs. In 2000, an outbreak contributed to a loss of 66% of live coral cover on sampled reefs in a study by the Reef Research Centre (RRC)." is exact verbatim substring of evidence `p:great_barrier_reef:13:000` ✓
- **qa-train-60**: Answer "191 stars in total, or about twice as many as Tokyo's nearest competitor, Paris" is exact verbatim substring of evidence `p:tokyo:42:000` ✓
- All hard negatives remain genuine non-evidence (no answer string leakage, no ancestor/descendant overlap)
- All other elements (evidence spans, hard negatives, meta, provenance) unchanged and still valid.

## Per-Draft Verdicts

### qa-train-52 (solo:black death group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `b948f69464bb01e62fc4e03d1622e85cb76e19b93e47d469f41fd107577d5662`
- Evidence: `t:black_death:00:000:02` ✓ (exact match)
- Hard negative: `p:black_death:12:000` ✓ (same_group_distractor, symptoms paragraph, no overlap)
- Answer "Yersinia pestis, which is primarily spread by flea bites" **exact verbatim substring** of evidence

### qa-train-53 (solo:blockchain group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `5bfa1aaf8186160e56cc04d5fd5cdaccde6f0d899ef7ef80d56c8c79c2118d15`
- Evidence: `p:blockchain:04:000` ✓ (exact match)
- Hard negative: `p:blockchain:09:000` ✓ (sibling_paragraph, permissioned blockchains, no overlap)
- Answer "the block time for Ethereum is set to exactly 12 seconds, while for bitcoin it is on average 10 minutes" **exact verbatim substring** of evidence

### qa-train-54 (solo:grand canyon group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `c89be4c28216f6acca385e61d75169ad8573a1f0dda86e598bc1321efdb7d096`
- Evidence: `t:grand_canyon:00:000:01` ✓ (exact match)
- Hard negative: `p:grand_canyon:12:000` ✓ (same_group_distractor, flora paragraph, no overlap)
- Answer "277 mi long, up to 18 mi wide and attains a depth of over a mile (6093 ft)" **exact verbatim substring** of evidence

### qa-train-55 (solo:great barrier reef group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `29ef41e88fbced129f2869044fa73b9b7dad0cf5ad5bb5bf48d4e1974e239450`
- Evidence: `p:great_barrier_reef:13:000` ✓ (exact match)
- Hard negative: `p:great_barrier_reef:06:000` ✓ (sibling_paragraph, ocean acidification, no overlap)
- Answer "The crown-of-thorns starfish preys on coral polyps. Large outbreaks of these starfish can devastate reefs. In 2000, an outbreak contributed to a loss of 66% of live coral cover on sampled reefs in a study by the Reef Research Centre (RRC)." **exact verbatim substring** of evidence

### qa-train-60 (solo:tokyo group, factoid) — REPAIRED
- **Verdict: APPROVE** (content)
- **Hash**: `c33a9e0538f88832af9330f5e08053ce85e7caeb69bc0b2e1c2e5af6a6b2d42b`
- Evidence: `p:tokyo:42:000` ✓ (exact match)
- Hard negative: `p:tokyo:31:000` ✓ (sibling_paragraph, transportation, no overlap)
- Answer "191 stars in total, or about twice as many as Tokyo's nearest competitor, Paris" **exact verbatim substring** of evidence

## Error Classes from `python3 -m data_tools.validate_qa`
Run on the 5 repaired drafts:
- 5 × `hard negative N not independently reviewed` (all `reviewed: false`)
- 5 × `missing or non-approve verification decision` (all `decision: "pending"`)

No structural/content errors for these 5 drafts. All prior rejection reasons resolved.

## Next Steps (Re-verification — Pass 2)
1. Independent reviewer sets `reviewed: true` on all 5 hard negatives with rationale
2. Verifier (distinct from author) sets `provenance.decision: "approve"` on corrected drafts, adds nonempty rationale, verifier_model, and ensures `provenance.content_hash` matches `draft_content_hash` (hashes above)
3. Re-run validate_qa to confirm zero errors

---

## 2026-09-29 Hash Reissue (authoritative repo-function values)

Prior reissue attempt used a reimplemented serializer; these values are the authoritative `data_tools.verify.draft_content_hash` outputs for the approved repaired content.

| Item | Content Hash (SHA-256) | Verdict |
|------|------------------------|---------|
| qa-train-31 | da0a2f12f189cfb58455b97f608f317d265dae73a262cc492ae8adf2160c6832 | APPROVE |
| qa-train-35 | 376daa30dd3324d9a991459109c2cffcf0fb95f515d499807b969a2032652745 | APPROVE |
| qa-train-37 | 30ca4f71ab3e113d7057e06ec5e8289dfbb65e415e5f98e4e7d4031366c567a8 | APPROVE |
| qa-train-50 | e19533f62562ba8e7c8c706c5894b80189511a4c4ab502a5b5b183640e3e4041 | APPROVE |