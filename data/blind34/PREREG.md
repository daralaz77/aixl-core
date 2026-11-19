# blind34 - pre-registration (written BEFORE any judge or comparator saw the pairs; I, the person who wrote the comparator, have not read the pairs)

Set: pairs written by two OPEN models run on Google Colab (Qwen2.5-32B-Instruct and Mistral-Small-24B-Instruct-2501, 4-bit, sampling T=0.9), told only the construct families
(negation scope, excepted set, short answers, which time / modal belongs to which action, bound + number, roles / voice, condition scope), three languages (en / es / pt), and asked per call for 5 pairs that are
either subtly different in meaning or genuine paraphrases. The authors are therefore NOT Claude models. The authors' label is the label by construction (the call asked for one kind); it is noisy by nature.

What runs on the SAME pairs, once:
- comparator trees: V071 (6db46d2), P0005 (patch 0005), V080 (aixl-core main 34654f7, release 0.8.0), frozen by sha256 (CODE_FREEZE.json);
- judges: Claude Sonnet and Claude Haiku (blind subagents, arbiter rules v1, one-word verdicts), and three open judges on Colab (Gemma-3-27B, Phi-4 14B, Qwen3-32B no-think, 4-bit, one reasoned sentence then a verdict line).

A pair is a FALSE ACCEPT of a comparator if either direction returns EQUIVALENT on a NOT_EQUIVALENT-labelled pair; PROVEN if both directions return EQUIVALENT on an EQUIVALENT-labelled pair.
A judge FALSE SAME is a SAME on a NOT_EQUIVALENT-labelled pair.

Rules (the only ones with a pass / fail):
- R-safety: V080 adds no false accept that V071 and P0005 did not already have (paired).
- R-no-regress: V080 false accepts <= P0005 false accepts.
Reported, not rules: per-language and per-family tables; the Claude pair (Sonnet + Haiku, unanimous SAME) false SAME and the SAME rate on equivalents, with veto = all and veto = definite; for every false SAME of the Claude pair, which open judges also say SAME (a shared blind spot) and which say DIFFERENT (extra protection); agreement of each judge with the author label; the list of pairs where a majority of the five judges contradicts the author label (probable label noise), reported separately and never silently removed.
Disclosed limits: labels by construction from open 24-32B models are noisy; judges and comparator are tuned on Claude-written pairs; the open judges run in 4 bits with one prompt; one run, no repetition.

## Deviation recorded BEFORE the run (decided before any result was seen)
Only ONE open judge was run: Gemma-3-27B (Google, 4-bit, reasoned verdict, 954 of 954 pairs). Phi-4 and Qwen3-32B were dropped for time (the session budget): their downloads and runs would have taken about 40 more minutes. The five-judge statements above therefore read as three judges: Sonnet, Haiku and Gemma-3-27B. The comparator trees, the rules R-safety / R-no-regress and the reported quantities are unchanged.
