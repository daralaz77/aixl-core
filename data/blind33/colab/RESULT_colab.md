# Cross-family judges on Google Colab (2026-11-18; spent sets, evidence only)
Runtime: Colab T4 GPU, 4-bit (bitsandbytes), greedy decoding, the arbiter rules as system prompt plus a one-word format override (SAME / DIFFERENT / UNSURE), 630 synthetic pairs (270 blind33 + 360 adversarial; ids as in `data/blind33/hybrid*/key.json`). Models: Qwen2.5-7B-Instruct (Alibaba), Falcon3-7B-Instruct (TII). Phi-3.5-mini was queued but its download stalled and was interrupted.

| judge | SAME on 255 equivalents | false SAME on 375 not-equivalent | invalid |
|---|---|---|---|
| Sonnet | 255 | 4 | 0 |
| Haiku | 249 | 45 | 0 |
| Qwen2.5-7B (4-bit) | 245 | 110 | 0 |
| Falcon3-7B (4-bit) | 163 | 68 | 163 |

| unanimity | SAME on equivalents | false SAME |
|---|---|---|
| Sonnet + Haiku (current 2-of-2) | 249 | 3 |
| Sonnet + Haiku + Qwen | 239 | 3 |
| Sonnet + Qwen (two families) | 245 | 4 |
| all four | 154 | 3 |

Reading: a 7B model in 4 bits is a far weaker judge than the Claude pair (29 % false SAME for Qwen alone), so adding it to the vote costs equivalents and removes no false SAME. The 3 false SAME of the Claude pair are accepted by all four judges, from two other families too: they are not a Claude-specific blind spot (they are the pairs whose label is arguable: the kind of mark after an answer word). Falcon often did not answer in the requested format (163 invalid; max_new_tokens=5). A real cross-family check needs a stronger open model (a 32B-class model in 4 bits needs a 24 GB GPU) and the reasoned-answer format.
Limits: spent sets, 4-bit 7B models, one prompt, one run.


## Second run: 24-32B judges on a Colab L4 (24 GB), reasoned answer (one sentence, then a final VERDICT line), same 630 pairs
Models (pre-quantised 4-bit): Qwen2.5-32B-Instruct (Alibaba), Mistral-Small-24B-Instruct-2501 (Mistral). Run time: 32B 1057 s, 24B 644 s for 630 pairs. Script: colab_run_32b_L4.txt (kept as .txt so the linter ignores its notebook-only lines).

| judge | SAME on 255 equivalents | false SAME on 375 not-equivalent | invalid |
|---|---|---|---|
| Sonnet | 255 | 4 | 0 |
| Haiku | 249 | 45 | 0 |
| Qwen2.5-7B | 245 | 110 | 0 |
| Qwen2.5-32B | 246 | 37 | 11 |
| Mistral-Small-24B | 154 | 19 | 3 |

| unanimity | SAME on equivalents | false SAME |
|---|---|---|
| Sonnet + Haiku (current) | 249 | 3 |
| Sonnet + Qwen-32B | 246 | 3 |
| Sonnet + Mistral-24B | 154 | 3 |
| Sonnet + Qwen-32B + Mistral-24B | 152 | 3 |
| Haiku + Qwen-32B | 241 | 17 |

Reading: (1) The three false SAME of the Claude pair are also accepted by the 32B and the 24B judges, i.e. by three model families: they are not a Claude blind spot, they are the pairs whose label is arguable (the kind of mark after an answer word is not meaning). (2) Claude pair, 3 families and every combination that includes Sonnet agree on 372 of 375 not-equivalent pairs: no judge-family-specific miss was found on these 630 pairs. (3) A single open judge is clearly weaker (10 % false SAME for the 32B alone, 29 % for the 7B) and Mistral is very strict (154 of 255 equivalents): they work as an independent second opinion, not as the decider. (4) Adding a third family never removed a false SAME and costs equivalents.
Limits: spent sets, 4-bit models, one prompt, one run; authors of the pairs are Claude models, so a pair style that only other families find hard would not appear here.
