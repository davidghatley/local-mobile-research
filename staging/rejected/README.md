# Rejected QA items (quarantine)

Items here were authored, independently reviewed, and then **rejected** on
semantic grounds. They are retained, not deleted, so the rejection is auditable
and so the same defect is not re-authored.

They are NOT part of any split. They are not counted in `train`, `dev`,
`shadow_dev`, or `private_test`, they are not in `corpus/questions.json`, and
`data_tools.validate_qa` does not scan this directory (it reads only the
top level of `staging/`).

| item | rejected because | ledger |
|---|---|---|
| `qa-shadow-dev-84` | comparison question pre-stated both years being compared (1991 / 2012), so `p:virtual_reality:06:000` alone answers it; the single conjunctive set therefore fails leave-one-out and the corpus offers no independent second route | `docs/qa-shadow-dev-84-86-repair-ledger.md` |
| `qa-shadow-dev-86` | comparison question pre-stated both years (1790 / 1889) and the answer text was the question's own side-A descriptor; all three recorded sets were cross-products of granularity variants, not independent routes | `docs/qa-shadow-dev-84-86-repair-ledger.md` |
| `qa-dev-24` | comparison question pre-stated both compared magnitudes (300M vs 800M hectares), so the answer follows from the question text alone; the single atom t:congo_basin:00:000:04 is the sole route and no independent alternatives exist | `docs/qa-prestated-premise-sweep.md` |

Honest consequence: the dev set is **59 usable items** (was 60), and the shadow-dev set is **87 usable items** (was 89).
