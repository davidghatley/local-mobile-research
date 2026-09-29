# Offline Research Architecture Tournament

Experimental research only. The controlling specification is `master_orchestration_prompt.txt`.

## Mandatory worker policy

- All subagents must explicitly select a verified free endpoint. Never inherit a model.
- No GPT-6, Astra, Codex, paid Claude, premium models, or anonymous free-model routers for workers.
- Nested spawning is disabled. Request additional workers from the top-level orchestrator.
- Catalog absence of pricing is not proof that an endpoint is free.
- Record endpoint substitutions and failures. Never fall back to paid endpoints.

## Scientific gates

- Round 0 common substrate must pass independent review and be frozen before architecture implementations begin.
- Keep corpus, candidate interface, generator, prompt, splits, and measurement methods comparable.
- Public bounty questions are development/reference only, never training examples.
- Development workers must not inspect sealed held-out answers or labels.
- Synthetic tests are infrastructure checks, not empirical architecture results.
- Distinguish measured results, estimates, hypotheses, and interpretations.
- Preserve raw traces and exact provenance. A missing artifact blocks freeze.
- Do not claim Android performance from desktop measurements.

## Working conventions

- Keep infrastructure shared and minimal; architecture-specific code belongs under `experiments/` after the gate.
- Use 2-space indentation where appropriate, UTF-8, LF, and final newlines.
- Read dependency/build commands from the substrate documentation once established.
