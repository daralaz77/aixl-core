# E-MCP-DESTRUCTIVE — wider evidence search on EXECUTE and SEND (2026-09-30)

User asked for more evidence before trusting the widened `irreversible_actions` list beyond the
single case each EXECUTE/SEND had in the 21-case E-INTEROP set. Scanned the larger, INDEPENDENT
200-pair cross-vendor dataset (E-XV, `data/xv/answers5/{sonnet,gemini,haiku,chatgpt}_{1..4}.txt`,
400 texts, 4 vendors each — a completely different corpus from the 21-case E-INTEROP set) for every
real cross-vendor disagreement involving EXECUTE or SEND.

## EXECUTE: 9 real cross-vendor disagreements found. 7-8 of 9 are the SAME translator-vocabulary
## false-positive pattern already seen in E-INTEROP's t077 — not genuine real-world danger.
```
t074 :: "Execute the analysis when there are over 100 records."
        sonnet/haiku/chatgpt=ANALYZE, gemini=EXECUTE,ANALYZE
t357 :: "Se houver mais de 100 registros, execute a análise."           sonnet/gemini/chatgpt=ANALYZE, haiku=EXECUTE
t358 :: "If there are more than 100 records, run the analysis."        sonnet/gemini/chatgpt=ANALYZE, haiku=EXECUTE
t389 :: "Execute the analysis only if there are more than 100 records." sonnet/gemini/chatgpt=ANALYZE, haiku=EXECUTE
t390 :: "Execute the analysis even if there are more than 100 records." sonnet/gemini/chatgpt=ANALYZE, haiku=EXECUTE
t399 :: "Run the analysis if there are more than 100 records."         sonnet/gemini/chatgpt=ANALYZE, haiku=EXECUTE
t400 :: "Run the analysis if there are more than 200 records."         sonnet/gemini/chatgpt=ANALYZE, haiku=EXECUTE
```
In every one of these 7 cases, the sentence literally contains the word "execute" or "run" as a
colloquial verb INTRODUCING the real action (analysis) — not commanding a genuinely irreversible
one-way operation. The majority reading (3 of 4 vendors every time) correctly resolves to `ANALYZE`;
only one vendor (Haiku in 6/7 cases) latches onto the literal verb and mis-tags it `EXECUTE`. Analysis
is about as safe/reversible an action as exists in this ontology — escalating these to REJECT would
be pure noise from a translator vocabulary quirk, not a real safety signal.
```
t203 :: "Run the script to update user document #45."      sonnet/gemini/chatgpt=EXECUTE,UPDATE, haiku=UPDATE
t204 :: "Execute the script to update user document #45."   sonnet/gemini/chatgpt=EXECUTE,UPDATE, haiku=UPDATE
```
The remaining 2 (really 1 underlying case, 2 phrasings) are more mixed: 3 of 4 vendors keep BOTH
`EXECUTE` and `UPDATE` as a joint action set; only Haiku drops `EXECUTE`. This isn't a competing
single-action dispute the way t077/DELETE cases are — it's a disagreement about whether "running a
script" deserves its own action tag alongside the update it performs. Doesn't clearly support treating
EXECUTE as uniquely dangerous either.
**Combined with E-INTEROP's own t077 ("schedule the call" → EXECUTE, also a false-positive-shaped
case): 8 of 10 total real EXECUTE-disagreement instances across BOTH datasets are the same vocabulary
noise, not genuine danger.**

## SEND: 3 raw hits, 1 is a false alarm (order-only), leaving 2 real disagreements — BOTH support keeping SEND
```
t021 :: "Informa los resultados de la encuesta en formato PDF con prioridad alta."
t022 :: "Report survey results in PDF format with high priority."
        sonnet=GET, gemini=GENERATE, chatgpt=GENERATE, haiku=SEND
t193 :: "Send the PDF to Ana after validation."   all 4 vendors: VALIDATE+SEND (order differs only — not a real action disagreement, excluded)
```
t021/t022 (the same pair, ES+EN) is a genuinely ambiguous instruction — GET, GENERATE and SEND are
all plausible readings of "report results," and Haiku's SEND guess, if trusted as authoritative,
would have REAL consequences (a document actually gets sent to someone) that a wrong GET/GENERATE
guess would not. This is a second, independent piece of real evidence supporting SEND, on top of
E-INTEROP's t092 (Gemini over-extracting SEND from a temporal clause, "before sending it").

## Recommendation (evidence, not yet applied — pending user confirmation)
Remove EXECUTE from `irreversible_actions` (8 of 10 real instances are translator-vocabulary noise,
not danger); keep SEND (2 of 2 real, distinct instances across 2 independent datasets show genuine
real-world stakes) and DELETE (confirmed earlier, t061).
