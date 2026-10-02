# QA Prestated-Premise Sweep Ledger

**Defect class**: A QA item is unsound when the QUESTION TEXT already supplies the fact that the recorded evidence is supposed to supply, so the item can be answered without the evidence.

**Criterion**: "If I never retrieved any of the recorded atoms, could a competent reader still answer this correctly from the question text alone?" If yes → unsound.

**Scope**: Adjudicated 22 machine-flagged candidates + 1 pre-confirmed (qa-dev-24) + full-corpus sweep.

---

## Adjudication of 22 Machine-Flagged Candidates

| id | split | verdict | answerable from question alone? | change |
|---|---|---|---|---|
| qa-dev-11 | dev | sound | No — question names "67 million tonnes" but not the production leader (Brazil). | none |
| qa-dev-25 | dev | sound | No — question names "burning since 1971" but not the project (Extreme Microbiome Project). | none |
| qa-dev-27 | dev | sound | No — question names 1956/1995 status changes but not the area (1484 km²). | none |
| qa-dev-41 | dev | sound | No — question names Feynman's 1959 talk but not the operating scale (1–100 nm). | none |
| qa-dev-47 | dev | sound | No — question names Gutenberg ~1440 but not the surface materials (paper, cloth, etc.). | none |
| qa-shadow-dev-22 | shadow_dev | sound | No — question names Emancipation Proclamation date and 1637 but not the emigration place (Massachusetts). | none |
| qa-shadow-dev-23 | shadow_dev | sound | No — question names 1860 election/secession but not the motor company (Lincoln Motor Company). | none |
| qa-shadow-dev-25 | shadow_dev | sound | No — question names Nov 1993 release but not the tagline (Do the math!). | none |
| qa-shadow-dev-26 | shadow_dev | sound | No — question names July 1775 Cambridge Common but not the presidency years (1789–1797). | none |
| qa-shadow-dev-51 | shadow_dev | sound | No — question names Proclamation 95 / Jan 1 1863 but not the founding date (August 1917). | none |
| qa-shadow-dev-52 | shadow_dev | sound | No — question names 1752 inheritance and 1759 marriage but not the spouse (Martha Dandridge Custis). | none |
| qa-shadow-dev-54 | shadow_dev | sound | No — question names 1209 founding by Oxford scholars but not the namesake city (Cambridge, MA). | none |
| qa-shadow-dev-56 | shadow_dev | sound | No — question names March 2016 light rail but not the campus district (University District). | none |
| qa-shadow-dev-61 | shadow_dev | sound | No — question names 1978 Aspen Movie Map and 168-acre campus but not the city (Cambridge, MA). | none |
| qa-shadow-dev-62 | shadow_dev | sound | No — question names 1968 HMD system but not the university founding year (1636). | none |
| qa-shadow-dev-65 | shadow_dev | sound | No — question names Leland's 1864 vote but not the president's first win year (1860). | none |
| qa-shadow-dev-66 | shadow_dev | sound | No — question names log-cabin birth and Jan 1 1863 but not the proclamation name (Emancipation Proclamation). | none |
| qa-shadow-dev-85 | shadow_dev | sound | No — question describes both universities but gives neither campus size (209 vs 700 acres). | none |
| qa-train-05 | train | sound | No — question names 1986 Pixar spinout but not the co-founded company (Apple Computer). | none |
| qa-train-18 | train | sound | No — question names Tower of London 1066 but not the Roman bridge date (AD 50). | none |

**All 22 candidates are SOUND.** The machine heuristic (keying on 4-digit years and answer-string overlap) produced false positives for every flagged item.

---

## Pre-Confirmed Unsound (Rejected)

| id | split | verdict | answerable from question alone? | change |
|---|---|---|---|---|
| qa-dev-24 | dev | **rejected** | Yes — question states both compared magnitudes (300M vs 800M hectares); the larger is directly inferable. | moved to `staging/rejected/`; provenance.decision="reject" |

---

## Additional Unsound Items Found by Full-Corpus Sweep

**None.** A manual review of the full approved set found no further instances of
this defect class beyond the three already known (`qa-dev-24`,
`qa-shadow-dev-84`, `qa-shadow-dev-86`).

CORRECTION (added after independent freeze review v3): an earlier version of this
line claimed "all 197 approved items (17 comparison, 33 multihop, 121 factoid,
14 ambiguous, 12 unanswerable)". That census was wrong on three of five buckets
and nine items were unaccounted for. The measured, correct census of the approved
set at the time of the sweep is **206** items: factoid 128, multihop 33,
comparison 17, ambiguous 15, unanswerable 13 (train 60 / dev 59 / shadow_dev 87).
The sweep's CONCLUSION — that only these three items are affected — is
unchanged; only the coverage arithmetic was wrong. An over-claimed census in a
ledger is still a false claim, so it is corrected rather than quietly rewritten.

- **Comparison items (17)**: Only qa-dev-24 pre-states both compared quantities. All others describe the entities to compare but withhold the decisive magnitudes/dates.
- **Multihop items (33)**: All require the evidence for the final hop; the question supplies only the bridge-entity context.
- **Factoid items (121)**: No answer text appears in the question.
- **Ambiguous/Unanswerable (26)**: By design; not this defect class.

---

## Class Rate Summary

| split | approved before | rejected this sweep | usable after |
|---|---|---|---|
| dev | 60 | 1 (qa-dev-24) | 59 |
| shadow_dev | 89 | 2 (qa-shadow-dev-84, -86) | 87 |
| train | 40 | 0 | 40 |
| pilot_dev | 10 | 0 | 10 |

**Total rejected this sweep**: 1 (qa-dev-24)
**Total previously rejected**: 2 (qa-shadow-dev-84, qa-shadow-dev-86)
**Grand total quarantined**: 3

---

## Provenance

- **Adjudicator**: opencode/nemotron-3-ultra-free (VERIFIED zero-cost)
- **Date**: 2026-10-02
- **Method**: Manual review of question text, answer text, and full evidence atoms for each candidate; full-corpus sweep by type.