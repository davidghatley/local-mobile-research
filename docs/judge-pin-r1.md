# Judge Pin — Round 1 (`google/flan-t5-large`)

Date: 2026-10-04. Role: orchestrator/custodian.

This document discharges **accepted risk #4** (`docs/STATUS.md`) and the
"HARD PRECONDITION BEFORE FIRST USE" clause in `docs/scoring-protocol.md` §2,
which requires the custodian to replace the floating model id with a resolved
revision commit SHA and the weight-file sha256 before any judge metric exists.

`docs/scoring-protocol.md` is **not edited by this run.** The protocol's own
rule 5.1 forbids scoring-rule modification, and this repository's precedent
(`experiments/R1_CONTRACT_ERRATUM.md`) is that a correction to a preregistered
document lives in a dated companion document that names the sentence it
supersedes. The sentence superseded is quoted verbatim below.

---

## 1. The superseded sentence

`docs/scoring-protocol.md` §2, verbatim as frozen at commit `75884b5`:

> - **Judge model digest: NOT YET PINNED — HARD PRECONDITION BEFORE FIRST USE.**
>   `google/flan-t5-large` is a *floating* identifier: the hub can move that tag.

**Superseded reading:** the digest is now pinned, to the values in §2 below. The
model id, prompt, temperature, decoding settings and output schema are
**unchanged**; only the missing digest is supplied. No scoring rule moved.

## 2. The pin

Source: `GET https://huggingface.co/api/models/google/flan-t5-large?blobs=true`,
observed 2026-10-04.

| Field | Value |
|---|---|
| Provider | huggingface.co Hub |
| Model id | `google/flan-t5-large` |
| **Revision (immutable commit SHA)** | `0613663d0d48ea86ba8cb3d7a44f0f65dc596a2a` |
| Last modified | `2023-07-17T12:49:05.000Z` |
| Gated | `false` |
| Private | `false` |
| License | `apache-2.0` |
| Params (card) | 783.2 M, `T5ForConditionalGeneration` |

### Weight files at that revision

| File | Bytes | Digest |
|---|---|---|
| `model.safetensors` | 3,132,668,804 | sha256 `a9dd06ce490f139af36e9eb77dd3758b4fd07a08a73d5a1abe5ff2591e2d388e` |
| `tokenizer.json` | 2,424,064 | git blob `fc669fbad1a6a82119ca3e1fa75db33ee22ca47d` |
| `config.json` | 662 | git blob `52d6c53a0bc88c7d1fe251e9643ce8aaf1c13e2e` |
| `generation_config.json` | 147 | git blob `d52815623b46b7db1c4b957b5a83a8ad30b0146a` |
| `special_tokens_map.json` | 2,201 | git blob `2c19eb6e3b583f52d34b903b5978d3d30b6b7682` |

`safetensors`, not `pytorch_model.bin`, is the canonical artifact: the `.bin`
sha256 is `93249e5f2b058ccddd0f4f5ef82aad80e262133eb103f1b42dc2da4b9bc97b36`
(3,132,781,861 B) and is recorded only so a re-download can prove it fetched the
same revision rather than a sibling file.

### The pin, as a single string

```
google/flan-t5-large@0613663d0d48ea86ba8cb3d7a44f0f65dc596a2a
  weights  sha256:a9dd06ce490f139af36e9eb77dd3758b4fd07a08a73d5a1abe5ff2591e2d388e
  file     model.safetensors (3132668804 B)
```

## 3. Unchanged preregistered judge settings

Reproduced here for the run manifest. **None of these were edited.**

- temperature `0.0`, `do_sample=false`
- greedy, `max_new_tokens=64`, `num_beams=1`, `early_stopping=true`
- no sampling, no top-k / top-p, no system-prompt variation
- the model's own tokenizer, input truncated to 2048 tokens
  (question + gold + prediction + evidence citation block)
- the verbatim prompt and the verbatim JSON Schema in
  `docs/scoring-protocol.md` §2
- non-conforming output is scored **judge-absent for that item**, never retried
  with a different prompt or model
- unavailability rule unchanged: report the deterministic metric as primary and
  judge metrics as ABSENT with an explicit note. Never substitute another model,
  another temperature, or an edited prompt.

## 4. What this does and does not unblock

**Unblocks:** secondary judge-based generated-answer metrics become
*available*, at a pinned revision, for comparison / multi-hop / free-form items
where exact matching does not apply.

**Does not unblock, and this matters more:** nothing on the primary path.
`experiments/comparability/CONTRACT.md` §3 states that no primary metric depends
on the judge, and its tie-break chain is fully deterministic. The Phase 1B
generator-floor probe is scored with `eval/answer_scoring.normalize_answer` and
`exact_match`. Accepted risk #4 was scoped "BLOCKING-FOR-ROUND-1" for *judge
metrics only*, and the primary tournament was never gated on it.

Consequently the gate is discharged, but **judge-based metrics remain OPTIONAL
and are used only where they add information the deterministic metrics cannot.**
They are never allowed to decide a comparison, and they are never compared
across architectures at different revisions.

## 5. Honest caveat on what a 783 M seq2seq judge is worth

Recorded now, before any judge output exists, so it cannot be revised downward
later: `google/flan-t5-large` is a small instruction-tuned T5. It is
*deterministic and pinned*, which is what the protocol needs. It is not a strong
judge, and a `CORRECT`/`INCORRECT` verdict from it on a composed multi-hop
statement should be read as a weak signal with a real error rate in both
directions. The protocol's rule 5.1 means we cannot improve the prompt to fix
that. So: if judge metrics and deterministic metrics disagree, the
deterministic metric is primary and the disagreement is reported, not resolved
by re-prompting.
