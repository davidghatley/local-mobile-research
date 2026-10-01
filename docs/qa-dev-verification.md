# QA Semantic Verification — Dev Drafts (qa-dev-11 through qa-dev-60)

**Reviewer:** opencode/nemotron-3-ultra-free (independent verifier)
**Corpus revision:** pilot-297-r1 (HEAD 3e82aa2)
**Date:** 2026-10-01
**Scope:** 50 newly authored dev drafts, all decision=pending. No pre-existing drafts audited.

---

## Batch 1: qa-dev-11 through qa-dev-20

### qa-dev-11 (multihop, claimed genuine) — **relabel-multihop**

**Question:** "The colour that derives its name from a fruit shares its name with a crop whose 2024 world production of 67 million tonnes was led by which country?"
**Answer:** "Brazil"
**Sufficient set 0:** {p:orange_colour:01:000, t:orange_fruit:23:000:00}

**Corpus text verification:**
- p:orange_colour:01:000: "The colour orange derives its name from the orange fruit. Lifeboats in Arklow Harbour, Ireland. Orange is chosen for lifeboats and lifesaving jackets because of its high visibility. A young Buddhist monk in Laos. A Hindu Sadhu (pious man), in Rajasthan, wearing orange as a sacred colour. Emperor Naruhito, then Crown Prince, wears an orange sokutai. Saffron is both a spice and a widely used dye in Asia, especially in India." — MATCHES draft
- t:orange_fruit:23:000:00: "In 2024, world production of oranges was 67 million tonnes, led by Brazil with 23% of the total, followed by China, Mexico, and Egypt (table)." — MATCHES draft

**Q1/Q2 per atom:**
- p:orange_colour:01:000: Q1=yes (t:orange_fruit:23:000:00 alone answers "Brazil"); Q2=setup (the question already states "The colour that derives its name from a fruit" — this atom merely confirms orange ← orange fruit, which the question premise supplies)
- t:orange_fruit:23:000:00: Q1=no (without it, no 2024 production leader); Q2=supplies the final property (2024 production led by Brazil)

**Multi-hop genuineness:** NO. The question already identifies the colour by its fruit-derived name. Atom 1 is setup the question gives verbatim. Only atom 2 is necessary. Single-atom answerable from t:orange_fruit:23:000:00.

**Hard negative:** t:orange_county_california:17:000:00 ("Tourism remains a vital aspect of Orange County's economy.") — clean, no answer string, no overlap.

**Decision:** relabel-multihop — drop is_multi_hop=true and hop chain; this is a factoid (single-atom answerable).

---

### qa-dev-12 (ambiguous) — **approve**

**Question:** "Which cybersecurity company did Orange acquire in 2019?"
**Readings:** 
- Reading 0: "UK cybersecurity provider SecureData" (set0: {p:orange_group:27:000})
- Reading 1: "SecureLink, a Netherlands-based cybersecurity company" (set1: {p:orange_group:28:000})

**Corpus text verification:**
- p:orange_group:27:000: "In February 2019 Orange acquired UK cybersecurity provider SecureData for an undisclosed sum, merging it with Orange Cyberdefense Division." — MATCHES
- p:orange_group:28:000: "Orange acquired SecureLink, a Netherlands-based cybersecurity company, in 2019 for €515 million." — MATCHES

**Q1/Q2 per set:**
- Set 0 (single atom): Q1=N/A; Q2=supplies the answer (SecureData) + disambiguator (UK, Feb 2019)
- Set 1 (single atom): Q1=N/A; Q2=supplies the answer (SecureLink) + disambiguator (Netherlands, €515M)

**Genuine ambiguity:** YES. Two distinct 2019 acquisitions of different cybersecurity companies by Orange in the same article. The bare question "Which cybersecurity company did Orange acquire in 2019?" is genuinely underdetermined — both readings have distinct sufficient sets and distinct answers. Not vague wording; two corpus entities fit.

**Q3 Alternatives:** NONE FOUND — only ancestor paragraphs (p:orange_group:27:000 is the paragraph atom; no other passage states the SecureData acquisition; same for SecureLink).

**Hard negative:** p:orange_group:06:000 (shareholders) — clean, non-answering.

**Decision:** approve.

---

### qa-dev-13 (comparison) — **approve**

**Question:** "Between Napoleon's self-coronation as Emperor of the French and the February Revolution that inaugurated the Russian Revolution, which event came first?"
**Answer:** "Napoleon crowned himself Emperor of the French"
**Sufficient set 0:** {t:napoleon:00:000:10, t:russian_revolution:00:000:04}

**Corpus text verification:**
- t:napoleon:00:000:10: "In December 1804 Napoleon crowned himself Emperor of the French, further consolidating his power." — MATCHES
- t:russian_revolution:00:000:04: "The Russian Revolution was inaugurated with the February Revolution in 1917, in the midst of World War I." — MATCHES

**Q1/Q2 per atom:**
- t:napoleon:00:000:10: Q1=no (without it, no date for Napoleon's coronation); Q2=supplies the first event date (Dec 1804)
- t:russian_revolution:00:000:04: Q1=no (without it, no date for February Revolution); Q2=supplies the second event date (1917)

**Comparison genuineness:** YES. Two distinct events from different articles; neither atom alone enables the temporal comparison. Both necessary.

**Hard negative:** t:napoleon:00:000:11 (Treaty of Amiens breakdown) — clean, non-answering.

**Decision:** approve.

---

### qa-dev-14 (multihop, claimed genuine) — **relabel-multihop**

**Question:** "Napoleon rose to prominence as a general during the French Revolution; by what means did he become First Consul of the Republic?"
**Answer:** "the Coup of 18 Brumaire"
**Sufficient set 0:** {t:napoleon:00:000:01, t:napoleon:00:000:08}

**Corpus text verification:**
- t:napoleon:00:000:01: "He rose to prominence as a general during the French Revolution and led a series of military campaigns across Europe and the Middle East during the French Revolutionary and Napoleonic Wars." — MATCHES
- t:napoleon:00:000:08: "In November 1799 Napoleon engineered the Coup of 18 Brumaire against the French Directory and became First Consul of the Republic." — MATCHES

**Q1/Q2 per atom:**
- t:napoleon:00:000:01: Q1=yes (atom 08 alone answers "Coup of 18 Brumaire"); Q2=setup (the question already states "Napoleon rose to prominence as a general during the French Revolution" — atom 1 restates this premise verbatim)
- t:napoleon:00:000:08: Q1=no (without it, no means of becoming First Consul); Q2=supplies the final property (Coup of 18 Brumaire)

**Multi-hop genuineness:** NO. The question already supplies the first-hop premise. Atom 1 is redundant setup. Only atom 2 is necessary. Single-atom answerable from t:napoleon:00:000:08.

**Hard negative:** t:napoleon:00:000:08 is not a hard negative (it's evidence). Need to check hard_negatives array — the draft shows empty hard_negatives array. Wait, let me check the draft again.

Actually looking at the draft output earlier: qa-dev-14.json hard_negatives: []. The draft has no hard negatives! This is a defect — all drafts should have hard negatives with reviewed=true.

**Decision:** relabel-multihop — drop is_multi_hop=true and hop chain; also needs hard negatives added (but that's a structural repair beyond semantic audit). Primary semantic decision: relabel-multihop.

---

### qa-dev-15 (factoid) — **approve**

**Question:** "Like his teacher Plato, Aristotle's philosophy aims at what?"
**Answer:** "the universal"
**Sufficient set 0:** {t:aristotle:07:002:00}

**Corpus text verification:**
- t:aristotle:07:002:00: "Like his teacher Plato, Aristotle's philosophy aims at the universal." — MATCHES (verbatim)

**Q1/Q2:** Single atom, Q1=N/A; Q2=supplies answer directly (verbatim entailment).

**Q3 Alternatives:** NONE FOUND — only ancestor p:aristotle:07:002 (paragraph span); no different passage gives this answer.

**Hard negative:** Need to check draft — shows empty hard_negatives array. Another missing hard negative.

**Decision:** approve (semantically), but note missing hard negative.

---

### qa-dev-16 (factoid) — **approve**

**Question:** "With which work is Aristotle credited with the earliest systematic study of logic?"
**Answer:** "the Prior Analytics"
**Sufficient set 0:** {p:aristotle:02:000}

**Corpus text verification:**
- p:aristotle:02:000: "With the Prior Analytics, Aristotle is credited with the earliest systematic study of logic, and his conception of it was the dominant form of Western logic until 19th-century advances in mathematical" — MATCHES (prefix)

**Q1/Q2:** Single atom, Q1=N/A; Q2=supplies answer directly.

**Q3 Alternatives:** NONE FOUND — only sentence child t:aristotle:02:000:00 (descendant span); no different passage.

**Hard negative:** Empty array in draft.

**Decision:** approve (semantically), note missing hard negative.

---

### qa-dev-17 (factoid) — **approve**

**Question:** "The bald eagle's range includes most of Canada and Alaska, all of the contiguous United States, and northern Mexico." (This appears to be the answer text, need to check actual question)
**Wait, let me re-read the draft.**

The answer_text is "most of Canada and Alaska, all of the contiguous United States, and northern Mexico". The question text wasn't shown in my summary. Let me check.

Actually, from the draft summary: qa-dev-17 has set0: ['t:bald_eagle:00:000:02'], answer: "most of Canada and Alaska, all of the contiguous United States, and northern Mexico". This is a factoid. The question would be something like "What is the bald eagle's range?" or similar.

**Corpus text verification:**
- t:bald_eagle:00:000:02: "Its range includes most of Canada and Alaska, all of the contiguous United States, and northern Mexico." — MATCHES

**Q1/Q2:** Single atom, Q1=N/A; Q2=supplies answer verbatim.

**Q3 Alternatives:** NONE FOUND — only ancestor p:bald_eagle:00:000.

**Hard negative:** Empty array.

**Decision:** approve (semantically), note missing hard negative.

---

### qa-dev-18 (factoid) — **approve**

**Question:** (Not shown, but answer is about bald eagle symbolism)
**Answer:** "seals and logos, coinage, postage stamps, and other items relating to the U.S. federal government"
**Sufficient set 0:** {p:bald_eagle:19:000}

**Corpus text verification:**
- p:bald_eagle:19:000: "The bald eagle is important in various Native American cultures and, as the national symbol of the United States, is prominent in seals and logos, coinage, postage stamps, and other items relating to" — MATCHES (prefix)

**Q1/Q2:** Single atom, Q1=N/A; Q2=supplies answer.

**Q3 Alternatives:** NONE FOUND — only sentence children.

**Hard negative:** Empty array.

**Decision:** approve (semantically), note missing hard negative.

---

### qa-dev-19 (multihop, claimed genuine) — **relabel-multihop**

**Question:** (Need to check — answer is "the Ames Monument")
**Answer:** "the Ames Monument"
**Sufficient set 0:** {t:buford_wyoming:01:000:01, t:buford_wyoming:01:000:02}

**Corpus text verification:**
- t:buford_wyoming:01:000:01: "The town is along the eastern approach to Sherman Hill Summit, the highest point along all of the transcontinental Interstate 80, Lincoln Highway and the Overland Route." — MATCHES
- t:buford_wyoming:01:000:02: "Buford is also an access to reach the Ames Monument, which marks the highest point along the original routing of the First transcontinental railroad." — MATCHES

**Q1/Q2 per atom:**
- t:buford_wyoming:01:000:01: Q1=yes (atom 02 alone answers "Ames Monument"); Q2=setup (describes Buford's location relative to Sherman Hill Summit — the question likely mentions Buford already)
- t:buford_wyoming:01:000:02: Q1=no (without it, no Ames Monument mention); Q2=supplies the answer (Ames Monument)

**Multi-hop genuineness:** NO. Need to see the actual question text. But atom 02 alone contains "Buford is also an access to reach the Ames Monument". If the question mentions Buford, atom 02 alone answers. Atom 01 is setup/background.

**Hard negative:** Empty array.

**Decision:** relabel-multihop — likely single-atom answerable from atom 02. Need question text to confirm.

---

### qa-dev-20 (unanswerable) — **approve** (pending corpus absence check)

**Sufficient sets:** 0 (unanswerable)
**Hard negatives:** Empty array — defect.

Need to verify absence claim by searching corpus. The question text is missing from my summary. Let me read the actual draft.

---

Let me now read the actual draft files for the remaining details (questions, hard negatives) and continue verification.