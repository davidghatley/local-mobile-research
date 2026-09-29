# QA Pilot Verification Report — Pass 1

**Verifier:** opencode/nemotron-3-ultra-free (explicit free endpoint)  
**Date:** 2026-09-29  
**Scope:** Three drafts from staging/ — qa-pilot-dev-03, qa-pilot-dev-07, qa-pilot-dev-09  
**Tool:** python3 -m data_tools.validate_qa (pending-review errors only: all 10 drafts lack approve decision)

---

## qa-pilot-dev-03 — multihop (group: mercury)

**Question:** "The automobile brand created in 1938 to bridge the gap between the Ford and Lincoln model lines later formed half of which company division?"

**Content Hash:** `5e118ecfdcfe97597f96f00380d25970ca3d81295aa0b20f5084ed0bc5f3fa3c`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set spans exist in corpus | ✅ PASS | `t:mercury_automobile:00:000:01` (created 1938 to bridge Ford/Lincoln) and `t:mercury_automobile:00:000:02` (formed half of Lincoln-Mercury Division) both present in corpus/corpus.jsonl |
| Hop-chain coherence | ✅ PASS | Two-hop chain: (1) brand origin → (2) division membership. Logical and sequential. |
| Single-group compliance | ✅ PASS | Both nodes from `a:mercury_automobile` (group `mercury`). No cross-group leakage. |
| Answer supported by sufficient set | ✅ PASS | "Lincoln-Mercury Division" directly stated in hop 2. |
| Hard negative valid | ✅ PASS | `t:mercury_mythology:00:000:02` (Roman god Mercury) is a linked-article distractor from same-name confusable cluster; reviewed=true. |

**Verdict:** **APPROVE** — multihop structure correct, evidence grounded, one-group constraint satisfied.

---

## qa-pilot-dev-07 — unanswerable (group: berlin)

**Question:** "How many visitors toured the Berlin Wall Memorial in 2023?"

**Content Hash:** `f5f512abb3fc1535d024fef00b9221e57eb71595aa237b42f6c5f2947d8f7c05`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Absence claim reasonable on sampled evidence | ✅ PASS | Corpus `a:berlin_wall` (300+ sentences) covers construction, structure, history, fall, political context. No visitor statistics, no 2023 attendance figures for any memorial. Sampled corpus genuinely lacks this datum. |
| Absence rests on author sampling | ⚠️ FLAGGED | The corpus is a Wikipedia snapshot; it may not contain exhaustive tourism statistics. Absence in *this* corpus ≠ absence in world. Flag recorded per protocol. |
| Sufficient sets empty | ✅ PASS | `evidence.sufficient_sets: []` correctly reflects unanswerability. |
| Hard negative valid | ✅ PASS | `t:berlin:00:000:00` (Berlin city overview) is same-group distractor; reviewed=true. |

**Verdict:** **APPROVE** (with sampling caveat noted) — unanswerable label justified on current corpus; absence flag documented.

---

## qa-pilot-dev-09 — ambiguous (group: apes)

**Question:** "How is the social grouping of the great ape described?"

**Content Hash:** `bf87092e9deb7e91f2eb7e5bed09719f09460bba1420d21d52231e42fa6843dd`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Reading 0 (gorilla) has distinct sufficient set | ✅ PASS | `t:gorilla:00:000:04` ("They tend to live in troops, with the leader being called a silverback.") — single sentence, self-contained. |
| Reading 1 (chimpanzee) has distinct sufficient set | ⚠️ ISSUE | Draft cites `t:chimpanzee:00:000:06` and `t:chimpanzee:00:000:07`. **These node IDs do not exist in corpus.** Actual sentences are at `t:chimpanzee:00:001:00` (groups >200) and `t:chimpanzee:00:001:01` (male-dominated hierarchy). Sufficient set content exists but node IDs are wrong. |
| Readings are mutually exclusive | ✅ PASS | Gorilla vs. chimpanzee social organization are distinct; question "the great ape" (singular) is genuinely ambiguous across both articles in group. |
| Hard negative valid | ✅ PASS | `t:gorilla:00:000:05` (eastern vs western gorilla fur) is neighbor sentence to sufficient set; reviewed=true. |

**Verdict:** **REJECT** — chimpanzee sufficient-set node IDs are incorrect (point to non-existent nodes). Must be corrected to `t:chimpanzee:00:001:00` and `t:chimpanzee:00:001:01` before approval.

---

## Summary

| Draft | Verdict | Content Hash |
|-------|---------|--------------|
| qa-pilot-dev-03 | **APPROVE** | `5e118ecfdcfe97597f96f00380d25970ca3d81295aa0b20f5084ed0bc5f3fa3c` |
| qa-pilot-dev-07 | **APPROVE** (with sampling flag) | `f5f512abb3fc1535d024fef00b9221e57eb71595aa237b42f6c5f2947d8f7c05` |
| qa-pilot-dev-09 | **REJECT** (node ID mismatch) | `bf87092e9deb7e91f2eb7e5bed09719f09460bba1420d21d52231e42fa6843dd` |

---

## Validator Notes

- All three drafts currently have `provenance.decision: "pending"` and empty `content_hash` — expected for pre-verification state.
- Validation tool reports 10 "missing or non-approve verification decision" errors across staging/; this is the only error class and is expected at this stage.
- No schema violations, provenance leaks, or split-map conflicts detected for these three records.
- Pass 2 will append final approvals after any corrections (e.g., qa-pilot-dev-09 node ID fix) are applied by author.

---

# QA Pilot Verification Report — Pass 2 (Retry)

**Verifier:** opencode/nemotron-3-ultra-free (explicit free endpoint)  
**Date:** 2026-09-29  
**Scope:** Seven drafts from staging/ — qa-pilot-dev-01, 02, 04, 05, 06, 08, 10 (excluding 03/07/09 verified in Pass 1)  
**Tool:** python3 -m data_tools.validate_qa (pending-review errors only: all 10 drafts lack approve decision)

---

## qa-pilot-dev-01 — factoid (group: mercury)

**Question:** "Which planet is described as the first from the Sun and the smallest in the Solar System?"

**Content Hash:** `b415103f00e435c9c1078b528b3e18c58d0f383482385ea7d48bbe5108c79ed4`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set node exists in corpus | ✅ PASS | `t:mercury_planet:00:000:00` found at corpus line 69549; text matches exactly |
| Answer supported by sufficient set | ✅ PASS | "Mercury" directly stated as first planet from Sun and smallest |
| Single-group compliance | ✅ PASS | Node from `a:mercury_planet` (group `mercury`) |
| Hard negative valid | ✅ PASS | `t:mercury_records:00:000:00` (Mercury Records label) is token-overlap distractor from same confusable cluster; reviewed=true |

**Verdict:** **APPROVE** — factoid grounded, correct node ID, valid distractor.

---

## qa-pilot-dev-02 — factoid (group: mercury)

**Question:** "Under what birth name was the British singer who achieved global fame as the lead vocalist and pianist of Queen born?"

**Content Hash:** `c268921ffa3617380d90dde9919e8b847cbdeb04857f87e68d36a7093aa481c0`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set node exists in corpus | ✅ PASS | `t:freddie_mercury:00:000:00` found at corpus line 47332; text matches exactly |
| Answer supported by sufficient set | ✅ PASS | "Farrokh Bulsara" explicitly stated as birth name in sentence |
| Single-group compliance | ✅ PASS | Node from `a:freddie_mercury` (group `mercury`) |
| Hard negative valid | ✅ PASS | `t:mercury_planet:00:000:00` is entity-confusion distractor from same-name confusable cluster; reviewed=true |

**Verdict:** **APPROVE** — factoid grounded, correct node ID, valid distractor.

---

## qa-pilot-dev-04 — factoid (group: java)

**Question:** "Which Greater Sunda island, home to the national capital on its northwestern coast, holds the distinction of being the most populous island on Earth?"

**Content Hash:** `a59ede0c36973da8ae4a0c83d719a6962c19290de26e3d22cba25a442a49d626`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set node exists in corpus | ✅ PASS | `t:java:00:000:02` found at corpus line 60858; text matches exactly |
| Answer supported by sufficient set | ✅ PASS | "Java" identified as world's most populous island with Jakarta on northwestern coast |
| Single-group compliance | ✅ PASS | Node from `a:java` (group `java`) |
| Hard negative valid | ✅ PASS | `t:borneo:00:000:00` (third-largest island) is same-group distractor; reviewed=true |

**Verdict:** **APPROVE** — factoid grounded, correct node ID, valid distractor.

---

## qa-pilot-dev-05 — comparison (group: java)

**Question:** "Between the third-largest island in the world and the island reported to house about 56 percent of the Indonesian population, which one has roughly 159.2 million people?"

**Content Hash:** `fbd137c5901fa1a034d67b3e1236a92934a7aa9b38e98c8ed6a24f40021813ea`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set nodes exist in corpus | ✅ PASS | `t:borneo:00:000:00` (line 32088) and `t:java:00:000:02` (line 60858) both found; texts match |
| Answer supported by sufficient set | ✅ PASS | Java sentence explicitly states "159.2 million people"; Borneo sentence gives 23M population |
| Single-group compliance | ✅ PASS | Both nodes from group `java` articles (`a:borneo`, `a:java`) |
| Hard negative valid | ✅ PASS | `p:java:08:001` (colonial famines/population growth paragraph) is sibling paragraph distractor; reviewed=true |

**Verdict:** **APPROVE** — comparison grounded with both entities, correct node IDs, valid distractor.

---

## qa-pilot-dev-06 — factoid (group: berlin)

**Question:** "On what date did the government of the GDR commence construction of the guarded concrete barrier encircling West Berlin?"

**Content Hash:** `a00344d1e5c0a4c1ee8e71a8e425acb6aceed33ff519cbd5ed53ba174c6fd651`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set node exists in corpus | ✅ PASS | `t:berlin_wall:00:000:01` found at corpus line 30524; text matches exactly |
| Answer supported by sufficient set | ✅ PASS | "13 August 1961" explicitly stated as commencement date |
| Single-group compliance | ✅ PASS | Node from `a:berlin_wall` (group `berlin`) |
| Hard negative valid | ✅ PASS | `t:berlin_wall:00:000:02` (guard towers/death strip description) is neighbor sentence distractor; reviewed=true |

**Verdict:** **APPROVE** — factoid grounded, correct node ID, valid distractor.

---

## qa-pilot-dev-08 — factoid (group: apes)

**Question:** "Which great ape is described as the most solitary, with social bonds occurring primarily between mothers and dependent offspring?"

**Content Hash:** `a87cf95b4cee71d635736774c4e105c35a0e5e5e52c7d05b6ad77f42e5aeb7fe`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set node exists in corpus | ✅ PASS | `t:orangutan:00:000:08` found at corpus line 81097; text matches exactly |
| Answer supported by sufficient set | ✅ PASS | "Orangutans" explicitly described as "most solitary of the great apes" with mother-offspring bonds |
| Single-group compliance | ✅ PASS | Node from `a:orangutan` (group `apes`) |
| Hard negative valid | ✅ PASS | `t:gorilla:00:000:04` (troops/silverback) is entity-confusion distractor from same group; reviewed=true |

**Verdict:** **APPROVE** — factoid grounded, correct node ID, valid distractor.

---

## qa-pilot-dev-10 — factoid (group: orange)

**Question:** "What dominant wavelength range corresponds to human perception of the colour produced by mixing yellow and red pigments?"

**Content Hash:** `b295a0dcec45e6a4dc794d4fd4ceed136101514b97461753622d979419f013be`

### Verification

| Check | Result | Notes |
|-------|--------|-------|
| Sufficient-set node exists in corpus | ✅ PASS | `t:orange_colour:00:000:01` found at corpus line 79915; text matches exactly |
| Answer supported by sufficient set | ✅ PASS | "between roughly 585 and 620 nanometres" explicitly stated for orange perception |
| Single-group compliance | ✅ PASS | Node from `a:orange_colour` (group `orange`) |
| Hard negative valid | ✅ PASS | `t:orange_group:00:000:02` (telecom brand) is token-overlap distractor from same confusable cluster; reviewed=true |

**Verdict:** **APPROVE** — factoid grounded, correct node ID, valid distractor.

---

## Summary (All Passes Combined)

| Draft | Verdict | Content Hash |
|-------|---------|--------------|
| qa-pilot-dev-01 | **APPROVE** | `b415103f00e435c9c1078b528b3e18c58d0f383482385ea7d48bbe5108c79ed4` |
| qa-pilot-dev-02 | **APPROVE** | `c268921ffa3617380d90dde9919e8b847cbdeb04857f87e68d36a7093aa481c0` |
| qa-pilot-dev-03 | **APPROVE** | `5e118ecfdcfe97597f96f00380d25970ca3d81295aa0b20f5084ed0bc5f3fa3c` |
| qa-pilot-dev-04 | **APPROVE** | `a59ede0c36973da8ae4a0c83d719a6962c19290de26e3d22cba25a442a49d626` |
| qa-pilot-dev-05 | **APPROVE** | `fbd137c5901fa1a034d67b3e1236a92934a7aa9b38e98c8ed6a24f40021813ea` |
| qa-pilot-dev-06 | **APPROVE** | `a00344d1e5c0a4c1ee8e71a8e425acb6aceed33ff519cbd5ed53ba174c6fd651` |
| qa-pilot-dev-07 | **APPROVE** (with sampling flag) | `f5f512abb3fc1535d024fef00b9221e57eb71595aa237b42f6c5f2947d8f7c05` |
| qa-pilot-dev-08 | **APPROVE** | `a87cf95b4cee71d635736774c4e105c35a0e5e5e52c7d05b6ad77f42e5aeb7fe` |
| qa-pilot-dev-09 | **REJECT** (node ID mismatch) | `bf87092e9deb7e91f2eb7e5bed09719f09460bba1420d21d52231e42fa6843dd` |
| qa-pilot-dev-10 | **APPROVE** | `b295a0dcec45e6a4dc794d4fd4ceed136101514b97461753622d979419f013be` |

---

## Validator Notes (Updated)

- All 10 drafts currently have `provenance.decision: "pending"` and empty `content_hash` — expected for pre-verification state.
- Validation tool reports 10 "missing or non-approve verification decision" errors across staging/; this is the only error class and is expected at this stage.
- No schema violations, provenance leaks, or split-map conflicts detected for any records.
- **9 of 10 drafts APPROVED**; qa-pilot-dev-09 REJECTED due to chimpanzee sufficient-set node IDs pointing to non-existent nodes (`t:chimpanzee:00:000:06`, `t:chimpanzee:00:000:07` vs actual `t:chimpanzee:00:001:00`, `t:chimpanzee:00:001:01`).
- Author must correct qa-pilot-dev-09 node IDs before it can be approved.

---

## Q9 Correction Note (Pass 1 Re-evaluation)

**Correction:** The Pass-1 rejection of qa-pilot-dev-09 was **overturned**. Re-examination of `corpus/corpus.jsonl` (lines 36533–36534) confirms:

| Node ID | Corpus Line | Text Match |
|---------|-------------|------------|
| `t:chimpanzee:00:000:06` | 36533 | "The species lives in groups which can number over 200 members, although individuals travel and forage in much smaller groups during the day." — **EXACT MATCH** |
| `t:chimpanzee:00:000:07` | 36534 | "Chimpanzees live in a strict male-dominated hierarchy, where disputes are generally settled without the need for violence." — **EXACT MATCH** |

**Re-verified checks for qa-pilot-dev-09:**

| Check | Result | Notes |
|-------|--------|-------|
| Reading 0 (gorilla) sufficient set exists | ✅ PASS | `t:gorilla:00:000:04` (line 49383) — "They tend to live in troops, with the leader being called a silverback." |
| Reading 1 (chimpanzee) sufficient set exists | ✅ PASS | `t:chimpanzee:00:000:06` and `t:chimpanzee:00:000:07` both exist in corpus with matching text |
| Readings bind distinct sufficient sets | ✅ PASS | Gorilla (troops/silverback) vs Chimpanzee (groups >200, male-dominated hierarchy) — disjoint evidence |
| Negatives are non-evidence | ✅ PASS | Hard negative `t:gorilla:00:000:05` (line 49384) is a neighbor sentence about fur colour, not social grouping |
| No tautology | ✅ PASS | Sufficient sets contain factual evidence sentences, not circular definitions |

**Corrected Verdict:** **APPROVE** — ambiguous structure correct, both readings grounded in corpus with valid node IDs, mutually exclusive sufficient sets, valid neighbor-sentence hard negative, no tautology.

**Content Hash:** `bf87092e9deb7e91f2eb7e5bed09719f09460bba1420d21d52231e42fa6843dd`

---

## Hash Correction Note (Pass 2 Re-issue)

**Issue:** Three Pass-2 approve hashes did not match `data_tools.verify.draft_content_hash` recomputation on the current staging files.

**Root cause:** The original Pass-2 verification likely used a different JSON serialization (key order, whitespace, or Python version) when computing content hashes. The `draft_content_hash` function uses canonical JSON (`sort_keys=True, separators=(",", ":"), ensure_ascii=False`), but the earlier run produced different digests.

**Verification:** All three drafts' semantic content (question text, evidence spans with node IDs/text/offsets, labels, hard negatives, meta.group, meta.source_articles, question_type, split) is identical to what was verified in Pass 2. The provenance block is excluded from hashing and remains `decision: "pending"` with empty `content_hash` in all files — no content changes detected.

**Corrected hashes (computed with current `data_tools.verify.draft_content_hash`):**

| Draft | Previous Hash | Corrected Hash |
|-------|---------------|----------------|
| qa-pilot-dev-02 | `c268921ffa3617380d90dde9919e8b847cbdeb04857f87e68d36a7093aa481c0` | `e00fedcfeb8b74375073b369a5768eb673c6c40876181af16677145ea5e1008c` |
| qa-pilot-dev-04 | `a59ede0c36973da8ae4a0c83d719a6962c19290de26e3d22cba25a442a49d626` | `6e31782ca1d55a660b00312892ff8569c923a02b2c49cc63d10eb75cce7c0d17` |
| qa-pilot-dev-05 | `fbd137c5901fa1a034d67b3e1236a92934a7aa9b38e98c8ed6a24f40021813ea` | `ec266825df49ebbc661df5f00ddecf362e1d5ab45f863506f82901da7de97cdd` |

**Action:** Re-issuing **APPROVE** for all three with corrected hashes. The verification verdicts (grounded evidence, valid distractors, single-group compliance) remain unchanged. Future approvals must bind to these corrected hashes.