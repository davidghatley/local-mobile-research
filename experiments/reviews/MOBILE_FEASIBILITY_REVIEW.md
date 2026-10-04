# Mobile Feasibility Review — Round 1 (Independent Verdict)

One page, for the build-next decision. Evidence: Hub API + primary docs read
2026-10-04; desktop numbers restated from the settled brief, not re-measured.
No Android performance number appears below; anything unmeasured is labelled.

## Verdicts

- **KaLM multi-rate cascade: mobile BLOCKED (artifact-layer, confirmed).**
  The pinned R2 checkpoint (`32b242bb…`, 1,572,182,264-byte weights) ships
  zero non-PyTorch artifacts — no ONNX, no GGUF, no ExecuTorch/TFLite
  (verified from the complete Hub file listing). No R2 GGUF exists Hub-wide;
  only V1-only GGUFs. Stock llama.cpp converts neither T5Gemma2 nor
  ModernBERT (verified in `conversion/` sources); ORT quantization produces
  fixed graphs, not rate-switchable ones. The prior team was right: there is
  nothing to export at ANY ratio, so the phone story fails before
  rate-switching matters. Desktop science (the 128x-turnover falsifier) is
  unaffected and remains the family's highest-value experiment.
- **Adapter swapping: storage advantage NEUTRALISED on mobile (confirmed).**
  Every mobile path checked requires `merge_and_unload()` first. Arithmetic
  with Hub-measured sizes: 3 LoRA adapters on the 17m base ship ~68 MB with
  swapping vs ~202 MB merged — and merged exceeds family C's single 70.8 MB
  shared encoder (measured) already at 2 adapters (~135 MB). The prior team
  was right. The surviving claim is only the weak one — one merged small
  rivalling a large model at small-model cost — whose quality premise is
  unmeasured (no adapters trained).

## The crossover in one line

Sharing wins ⟺ Σ(adapters) < (A−1)×|base|; at r=8 LoRA tariffs (0.22–0.59 MB)
versus 64–133 MB bases, sharing wins by ~100× wherever swapping runs — and no
checked mobile runtime runs it for these encoders (llama.cpp LoRA is
generative-path only; ORT LoRA is GenAI-API only; ExecuTorch/MNN/NCNN/TFLite
not surveyed).

## What to build next

1. **C-like shared encoders first** (one encode ≈ 99.8% of cost, 3 readouts =
   10.9 ms measured): the only design with measured quality (0.8767, −1
   paragraph vs B3) at phone-plausible weight (70.8 MB, qint8 onnx shippable
   at ~16–66 MB per Hub sizes).
2. **Adapters only as single-task LoRA-vs-large bets**, judged against C on
   quality-per-byte with MMD floors respected (dev 22.0 pp — most deltas will
   be nulls; report them as nulls).
3. **KaLM as desktop retrieval science**, mobile-independent.

## Open unknowns (deliberately not guessed)

Mobile op coverage for T5Gemma2 in NCNN/MNN/TFLite/ExecuTorch/ORT-Mobile;
llama.cpp LoRA on embedding/rerank endpoints; all adapter quality numbers
(gain, merge parity, int8 parity); KaLM 128x turnover on dev sufficient sets.
