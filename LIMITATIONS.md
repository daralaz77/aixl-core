# AIXL 0.3 — Known limitations (measured or observed, not hypothetical)

> **Status 2026-10-03 — read [docs/EVIDENCE.md](docs/EVIDENCE.md) first.** The newest and most important limitations are the sections *E-BLIND10* (and round 2) at the END of this file and ADR-017: on other authors' open-domain text the closed vocabulary drops what it has no slot for, so ~40–59 % of non-equivalent pairs were judged equivalent; AIXL-side repairs make that visible (`R:`, completeness, INCONCLUSIVE) but prove only 0–32 % of true paraphrases; a full-text LLM arbiter is the measured baseline. Accuracy figures earlier in this file come from sets drawn from the translator's own vocabulary.

1. **The rule-based translator plateaus around 76–80 % accuracy on unseen phrasing** (precision 92–95 %, recall 57–63 %): rules learned from blind sets 1–2 did not transfer to set 3 (see BENCHMARK.md). Every fresh set exposes a new long tail of verbs, idioms and syntactic forms. The core (graph/comparator/drift) is not the bottleneck; the translator is.
2. **Fixed vocabulary**: 25 actions, ~20 nouns, ES/EN/PT only. Out-of-vocabulary language is silently ignored (it will not raise an error), so a text with only unknown words yields an empty graph and can look "equivalent" to another empty graph. **Update 2026-10-02:** still true that unknown words are ignored, but no longer *silently*: out-of-lexicon object nouns raise an `UNRECOGNIZED_TERMS` warning (`ComparisonResult.warnings`, `graph.meta["unrecognized"]`), and a text with no recognised action raises a BLOCKING `NO_ACTION_RECOGNIZED` warning so "equivalent" there reads as "cannot verify". The verdict itself is unchanged (an unknown-noun swap is still judged PARTIAL, not NOT_EQUIVALENT).
3. **Action-argument binding** (CLOSED in part 2026-10-02, option "K:BIND, compare only if both sides declare"): for texts with 2+ actions the rule-based translator binds name references, entities and data to the action whose text segment contains them, serialized as `K:BIND=ACTION>ARG` and compared as the canonical dimension `bindings`. "Delete users and analyze reports" vs "Delete reports and analyze users" is now detected (CRITICAL when a destructive action's target changes). Measured: 0 verdict changes on 1400 labelled pairs (blind1-9 + dev200), set6 accuracy unchanged (86 %), sil5x100/sil_security/negotiation/interop outputs identical. **Still open:** (a) bindings are positional-heuristic and are deliberately NOT produced for passive clauses or step-order cues ("before/after/then/first"), where arguments are fronted — there they are UNKNOWN and the swap is not detected; (b) output formats, time, location and constraints are not bound (binding them made 19/1400 paraphrase pairs falsely NOT_EQUIVALENT before being removed); (c) anaphoric dependencies ("envíalo") stay graph edges only; (d) an encoder that does not emit BIND (an LLM with the frozen card, sha256 8b2b03bf…) is UNKNOWN on this dimension, so the swap goes undetected for that route until the card is updated and the LLM routes re-measured; (e) compare treats subset bindings as compatible, so a fingerprint can differ for two texts that compare EQUIVALENT (stricter, safe direction).
4. **Relative time**: day/month/year granularity ("ayer", "el mes pasado", "este año") now resolves against a reference clock (see "Date/time/duration fixes" below) — FIXED 2026-09-27, was previously unresolved. **Week granularity still is not**: "la semana pasada" ≠ any literal date, on purpose (AIXL has no week-range literal to resolve it to without inventing one).
5. **Aggregates and superlatives** ("el mayor número de ventas") are only partly modelled; "top N"/"N mejores" become LIMIT.
6. **Conditions**: only count thresholds, existence/containment and confidence thresholds are structured; any other condition stays a weak literal string and is compared by exact text.
7. **Negation scope**: "never delete X without validating" collapses to FORBID DELETE (the "without validating" part is lost). Conditional prohibitions ("if H<.8, don't delete") keep the condition and the prohibition as independent fields.
8. **Ambiguity detector is heuristic**: "el reporte" without an id is flagged for destructive/sending actions only; pronoun resolution counts nouns before the pronoun, not real coreference.
9. **Contradiction detector** needs an explicit opposition on the same object; it does not detect implicit contradictions or contradictions inside one text.
10. **No real tokenizer for Claude/Gemini**: token counts use OpenAI's cl100k (proxy). AIXL is LONGER than the natural sentence in characters and tokens (see BENCHMARK.md); it is not a compression scheme.
11. **Labels come from single annotators** (model authors) without adjudication; some blind labels are arguable (e.g. "ejecuta el análisis" = "analiza"). One specific case was checked against the corpus rather than assumed: "urgent" vs "high priority" is labelled NOT_EQUIVALENT by 23 independent blind pairs across 6 rounds and EQUIVALENT by exactly 1 (set6 S6-033); the system follows the 23, and S6-033 is left as an open single-annotator disagreement.
12. The 200-case DEV dataset and the six demos are DEMO material written by the code's author. Only the blind sets are experimental evidence, and none of this is real-world validation.

## E-XV findings (cross-vendor)
* Card ↔ codec gap: 26 of 1600 LLM answers (Sonnet 8, Gemini 16, ChatGPT 2, Haiku 0) failed to parse, mostly `O:` with two values or `H:> .90`. Fixed after E-XV (see next section) and re-measured on a fresh set (E-CODEC, set 6): 0/200 parse failures on both routes (was 26/1600 pre-fix), Sonnet 94.0 % accuracy.
* The 96 % result holds across vendors (93.5–96.5 %) on templated pairs written by non-Anthropic models, but those pairs are easier/more homogeneous than real traffic. Still no REAL VALIDATION.

## Codec fixes after E-XV (2026-09-27, aixl/ sha256 e134183d14f5b47361a8 → 99ccdcd9f79d734b44e3)
Three tolerance fixes to the AIXL parser, each found from a real LLM-encoder failure in E-XV, none changing the wire format the encoder is told to produce (the card is unchanged, sha256 8b2b03bf4989a64c9591):
1. `O:` (output format) is now a list atom, like `A`/`D`/`E`/etc. Before, `O:MARKDOWN,TABLE` (two formats for one request) raised `ERROR:INVALID_AIXL "O takes one value"`. Canonical form and comparison are now a set, same as the other list atoms (order-insensitive).
2. The parser tolerates a stray space right after a comparator operator and before its number/decimal point (`H:> .90`, `F:COUNT>= 100`) — a formatting habit some LLMs have. Fixed in `_collapse_comparator_space` (`aixl/legacy02/core/parser.py`), applied only outside quoted literals.
3. A LIST atom (e.g. `E:`) repeated on the same line (`E:COMPANY ... E:ANOMALY`) is now merged (union of values) instead of raising `ERROR:INVALID_AIXL "duplicate atom E"`. A repeated SCALAR atom (`V:`, `H:`, `I:`...) still raises — two different values for a single-value atom is a real conflict, not a formatting slip.
Regression tests: `tests/test_regression.py::test_bug020/021/022`. Confirmed on set 5 (all four encoders' stored answers, re-evaluated with the fixed code): parse failures 26 → 0. Measured fresh in experiment E-CODEC (`BENCHMARK/PREREG_0.3.md`) on set 6, unseen by any of this.

## Date/time/duration fixes after E-CODEC (2026-09-27, aixl/ sha256 99ccdcd9f79d734b44e3 → 25613d30c4fd57ba65c8)
All in `aixl/translators/natural_to_semantic.py` (LANGUAGE layer only, no codec/wire-format change), closing the 6 misses E-CODEC left on set 6 (plus one worse bug found while investigating one of them):
1. **Reference clock**: `to_graph(text, today=...)` resolves TODAY/YESTERDAY/TOMORROW to an ISO day, THIS_MONTH/LAST_MONTH/NEXT_MONTH to `YYYY-MM`, THIS_YEAR/LAST_YEAR/NEXT_YEAR to a year (default `today`: the real system date; tests pin a fixed one). Verified against the corpus first (blind3 A3-024, set6 S6-009/S6-061 — three independent authors across different rounds, not a single guess) before implementing. THIS_WEEK/LAST_WEEK/NEXT_WEEK still unresolved on purpose (see limitation 4 above).
2. **Date ranges**: DD/MM/YYYY slash dates, and "el N al M de MES de AÑO" (the 0.2 analyzer used to keep only the second day), both now produce the same two ISO dates.
3. **Clock time**: `antes de`/`before`/`después de`/`after` + a 12h or 24h time now produces a `BEFORE=`/`AFTER=` constraint. Before this fix the time of day was silently dropped (out of vocabulary) — worse than a miss, it made two genuinely DIFFERENT deadlines ("before 3pm" vs "before 5pm") compare as a **false EQUIVALENT**. Found while investigating S6-076, not in the original miss list.
4. **Age/duration**: "older than N year(s)" / "más de N año(s) de antigüedad" (also month/day) → `K:AGE>N:UNIT`; "newer than" / "menos de...antigüedad" → `<`.
Regression tests: `tests/test_regression.py::test_bug023` through `test_bug027` (107/107 total). Measured on set 7, which then EXPOSED a bigger bug (round 2, below).

## E-DATE round 2 and 3 (2026-09-27, aixl/ sha256 25613d30c4fd57ba65c8 → d4a740dca1aed42ecd5e, card sha256 8b2b03bf4989a64c9591 → 1cf27968c1cbbdd934de — first card edit since the LLM-translator experiments began)
Round 2, found by set 7: the reference clock above lived ONLY in the translator, so an LLM-encoded `T:TODAY` could never match a literal date — Sonnet's accuracy on set 7 was 80.0 %, far below the 94–96.5 % on other fresh sets. Fixed by moving the resolution into `SemanticGraph.canonical()` / `compare_graphs(..., today=...)` (`aixl/core/ontology.resolve_relative_time_token`), so it covers TIME nodes from EITHER route. Also added duration-unit conversion (1 YEAR = 12 MONTHS) since an LLM independently reused the card's own `COUNT>N:UNIT` pattern for age with mismatched units. Set 7 (already seen): 80→88 %.
Round 3, found by set 8: the frozen card never taught the LLM about AGE=/TIME_AT=/the clock-BEFORE extension, so it sometimes DROPPED an age/deadline clause entirely instead of quoting or structuring it — a genuine **false EQUIVALENT** on set 8 (Sonnet accuracy 85.0 %, 7 false positives). Fixed by updating `data/llm_translator/card_0.3.md` to teach `K:AGE>N:UNIT`, `K:TIME_AT=`, clock times in `K:BEFORE=`/`K:AFTER=`, and that "ticket número 77" / "issue number 58" (no `#`) is still `Y:#77`/`Y:#58` — the last one also fixed in the rule-based translator itself (`aixl/translators/natural_to_semantic.py`), a real gap found independently on 4 pairs in one set. Set 8 (already seen): Sonnet 85→96 %, rule-based 79→83 %.
Regression tests: `test_bug029`–`test_bug031` (111/111 total). **Final, trustworthy number** (fresh set 9, code+card frozen at this point, single run): Sonnet **95.0 %** accuracy / 0 parse failures / 39-of-39 critical drift; rule-based **88.0 %** (still short of S1). Full trace and table: `BENCHMARK/PREREG_0.3.md` (E-DATE).

## Remaining known gaps after E-DATE (not chased further — documented, not fixed)
* Weekday-relative dates ("before Thursday") are not resolved — no corpus evidence gathered yet on how blind authors treat this.
* The LLM route still falls back to a raw quoted literal for a clause it can't structure (e.g. "for 2:30pm" vs "para las 14:30", two different literal strings in two languages) — only structured atoms are compared, by design; this is inherent to an LLM improvising outside the card's taught vocabulary, not a bug with a clean fix.
* Number-word vs digit normalization ("tres meses" vs "3 meses") only happens automatically in the rule-based translator's preprocessing; an LLM that falls back to a quoted literal does not get this normalization.
* A handful of set 7/8/9 misses are unrelated to date/time/duration/reference (recipient/department/target-person differences, "fail" vs "pass" validation outcome, "notify" vs "replace" action) — pre-existing rule-based-translator vocabulary gaps, out of this round's scope.

## E-INTEROP finding (2026-09-29): cross-vendor ENCODING consistency is 53 %, not 93-96 %
All prior cross-vendor numbers (E-XV, E-DATE) measured JUDGE accuracy — whether the comparator classifies a pre-written, pre-labelled pair correctly, using one encoder at a time. This experiment measured something the project had never tested: two independent vendors (Sonnet, Gemini), given the identical text and identical card, encoding it separately — do their two AIXL outputs compare as equivalent TO EACH OTHER? Answer: only 53/100. That is the real interoperability number, and it is much lower than the judge-accuracy figures because it is a different, harder question.
Bug found and fixed along the way: an out-of-vocabulary action value (`A:ANALYSIS` instead of `A:ANALYZE`) crashed the whole comparison (`derive_intent`'s bare dict lookup); fixed to degrade to UNKNOWN instead (`test_bug032`, code sha256 3803e88e628ae5d161d5).
The dominant remaining cause (18 of 47 disagreements, 38 %) is a genuine, unresolved PROTOCOL DESIGN QUESTION, not a bug: for a verb not literally on the card's action list, Sonnet defaults to `I:UNKNOWN`; Gemini guesses the nearest known action. Both are internally consistent readings of the same card. Left unresolved and reported to the user rather than decided unilaterally, since fixing it means picking a strictness policy for the whole protocol (see `BENCHMARK/PREREG_0.3.md`, E-INTEROP results, for the full breakdown and 29 additional within-vocabulary verb-choice disagreements).

## E-INTEROP resolution (2026-09-29): shared vocabulary took cross-vendor consistency 53 % → 79 %
The user chose to close the 53 % finding by expanding the card + code together (option 3: a shared, deterministic vocabulary is the only "way to reach agreement" two parties who never talk live can use). Three rounds, each measured on the SAME 100 texts before trusting the next change (round 1→2: +16 points from a much bigger VERB TABLE and a tie-break rule; round 2→3: +10 points fixing 2 regressions THAT round's own tie-break rule introduced — "generate a report" had started wrongly triggering the summary override, and "flag" wasn't yet a recognized synonym). Final: **79 % cross-vendor consistency, 0 parse failures** (code sha256 3d02fce9cea07a3ccf6e, card sha256 d0e597aa867347bc03d6).
Not chased further (diminishing returns: +16, then +10, then presumably less): the remaining 21 disagreements are mostly DATA-extraction granularity (should "100 records" also produce a separate `D:RECORDS` entity, or is `K:QTY=100:RECORDS` enough? the card never says), plus a handful of genuine unlisted-verb guesses. Getting past this would need either a 4th+ round of narrower fixes, or a live clarification exchange between agents — AIXL 0.3 has the error codes for that (E002 unknown token, E007 ambiguous) but no actual negotiation mechanism; that is future work, not built here.

## E-NEGOTIATE (2026-09-30): built the live negotiation protocol, honest scope of what was actually tested
`aixl/negotiation.py` gives two disagreeing agents a bounded, severity-ordered clarification exchange instead of silently guessing. Measured on real data: 21/21 genuine E-INTEROP disagreements converge (avg 1.14 rounds), and a real 2-model live demo (two independent Sonnet subagents, spec-only) produced a correct 3-turn exchange — after a real spec bug (multi-value candidates colliding on comma) was caught by that same demo and fixed.
What this is NOT: proof that the "resolved" reading is semantically true. The mechanism trusts the sender for the disputed dimension by design (convergence is close to guaranteed given enough rounds) — its value is the STRUCTURE (bounded, prioritized, honestly reportable), not oracle-grade arbitration between two equally-plausible readings when neither side actually holds the ground truth. Wired into the CLI/API 2026-09-30 (`aixl.negotiate`/`aixl.negotiate_aixl`, `cli.py negotiate`/`negotiate-aixl`) — that step itself caught a second real bug (CLARIFY's candidates/question had receiver and sender swapped in the displayed wording; the resolved value was always correct regardless; fixed). Still not done: a live, autonomous, multi-round exchange with no human relaying each turn between two running agents; testing it with more than one real disagreement case live (the deterministic 21/21 measurement covers breadth, the live demo covers depth on one case only).

## E-MCP (2026-09-30): built the first REAL protocol adapter (MCP), honest scope of what was actually tested
`aixl/adapters/protocol_adapter.py`'s `MCPAdapter` used to raise `NotImplementedError` like every other named adapter. Now it encodes/decodes an AIXL message as a real MCP tool-call envelope and validates it against the OFFICIAL `mcp` SDK's own pydantic models — not a hand-rolled guess of the wire shape. `aixl/mcp_server.py` is an actual running MCP server (stdio transport) exposing `aixl_translate`/`aixl_compare`/`aixl_negotiate`. Real validation: `tests/test_mcp_integration.py` spawns the server as a genuine subprocess and drives it with the SDK's own client over real stdio JSON-RPC (4/4 pass) — not an in-process mock.
What this is NOT (as first built): proof that AIXL interoperates with an unrelated, independently-built MCP client or agent — until this point, the only client that had ever talked to this server was this project's own test suite.
**Closed the same day**: registered the server in Claude Desktop's own `claude_desktop_config.json` (a real config edit, backed up first, dry-run-verified before restarting). The user restarted the app and called `aixl_compare` from an ordinary chat conversation — a genuine third-party client, never authored or driven by this project. The result matched byte-for-byte what this project's own reproduction got moments later (`BENCHMARK/results_mcp_desktop_client_FIRST_RUN.md`).
**Then `aixl_negotiate` too**, same session: the user called it on the "Close/Delete ticket #77" case; the transcript matched this project's own reproduction exactly (`BENCHMARK/results_mcp_desktop_negotiate_FIRST_RUN.md`).
**Then `aixl_translate`**, same session: the user ran "Analiza las ventas del primer trimestre de 2026." — output matched exactly (`BENCHMARK/results_mcp_desktop_translate_FIRST_RUN.md`). All 3 exposed tools are now confirmed with this real third-party client.
**Then a SECOND, independent vendor's client**: OpenAI's ChatGPT/Codex desktop app, registered via its own `~/.codex/config.toml` (`[mcp_servers.aixl-core]` — a completely separate codebase from Claude Desktop's config format). User restarted Codex and called `aixl_compare` from an ordinary conversation there; result matched exactly (`BENCHMARK/results_mcp_second_client_codex_FIRST_RUN.md`). Two independent vendors' clients now both interoperate correctly with the same real server — a materially stronger claim than one vendor's client, and the actual point of building AIXL vendor-neutral.
**Then a THIRD vendor**: Gemini Desktop's UI has no path anywhere to add a custom MCP server (Settings sections and the compose-bar tools menu were checked exhaustively, both directly and by asking the user to look). Fell back to `gemini-cli`, which has a real `gemini mcp add` command — but its personal Google OAuth login is server-side discontinued ("migrate to the Antigravity suite of products"), an external Google decision, not a bug here. Followed that pointer: installed Google's newer Antigravity CLI (`agy`), registered the server, and the user ran a real prompt in an `agy` chat session — its own agent found and called `aixl-core/aixl_compare` (behind a genuine tool-approval gate the user answered), and the result matched this project's reproduction exactly (`BENCHMARK/results_mcp_third_client_antigravity_FIRST_RUN.md`). Two credentials (an API key, a one-time OAuth code) were pasted into chat by mistake during this process and were never used or entered anywhere by this project — the user completed both the browser login and the CLI's first-run onboarding themselves.
Three independent vendors (Anthropic, OpenAI, Google) now confirmed. **`aixl_negotiate` confirmed on Antigravity too**, same session: the "Close/Delete ticket #77" case, run by the user through Antigravity's own agent, returned a transcript matching this project's reproduction exactly.
**`aixl_translate` confirmed on Antigravity too**, same session: "Analiza las ventas del primer trimestre de 2026." matched this project's reproduction exactly. All 3 tools are now confirmed on Antigravity CLI — the same coverage as Claude Desktop.
**Then `aixl_negotiate` AND `aixl_translate` confirmed on Codex too**, same day: tried to drive ChatGPT/Codex myself via computer-use (allowed, since it's not this project's own host app — unlike Claude Desktop) but its window sat on a macOS Space that couldn't be reached without disrupting the user's own full-screen Space, so the user ran both prompts themselves in the same Codex conversation as the earlier `aixl_compare` test. Both matched this project's own reproductions exactly (`BENCHMARK/results_mcp_second_client_codex_FIRST_RUN.md`).
**All 3 tools (`aixl_compare`, `aixl_negotiate`, `aixl_translate`) are now confirmed on all 3 independent vendor clients** (Anthropic, OpenAI, Google) — a real, broad cross-vendor result, not one lucky case. Still n=1 per tool per client (one call each); not yet demonstrated: two SEPARATE, independently-running AIXL instances negotiating over MCP end-to-end (the negotiation tool is exposed and callable by real third-party clients now, but E-NEGOTIATE's own live-demo depth — two agents negotiating WITH EACH OTHER — has not been re-run through a real MCP transport instead of two human-relayed subagents); production-scale/repeated usage. REST/OpenAPI/GraphQL remain unimplemented (A2A was built next, same day — see E-A2A below); MCP was chosen first because it's the protocol Claude Code (this project's own host) actually uses, not because the others are less valuable.

**A real design gap this same third-party test surfaced — found, then fixed** (2026-09-30): the Desktop-side model correctly noted that `negotiate()`'s ANSWER turn is not a fresh confirmation from a live sender — it reads the sender's OWN already-computed canonical value (`aixl/negotiation.py:181`), derived once at the very start from the same text that produced the disagreement. Confirmed the risk was real with `aixl_negotiate("Quita el ticket #77.", "Elimina el ticket #77.")`: an out-of-vocabulary sender verb left `actions` empty, and the exchange reported ACCEPT/converged while silently discarding the receiver's plausibly-correct `DELETE` reading.
Fixed by rejecting instead — but ONLY for `actions`, not every dimension: a first, broader attempt (reject on ANY empty sender value) broke a real, correct existing case (`test_negotiate_prioritizes_critical_severity_first`: a sender that genuinely states no prohibition has a correctly-empty `negation` value, and adopting it is the right resolution, not a translator failure) — caught immediately by the test suite, not shipped. `actions` is the one dimension where empty is unconditionally a failure signal (every real instruction has a main verb); every other dimension can be legitimately, correctly empty. Re-verified: the ambiguous case now REJECTs, the original "Close/Delete" case still ACCEPTs, and the real 21/21 E-INTEROP convergence measurement is unaffected (none of those 21 cases hit an empty-actions sender). Regression tests: `test_negotiate_rejects_rather_than_silently_discard_a_correct_reading_when_sender_cant_resolve_actions`, `test_negotiate_still_adopts_a_legitimately_empty_dimension_other_than_actions`.
Residual, honest limitation: this only catches the "empty/unresolved" case. A sender whose vocabulary DOES cover a wrong verb (a genuine translator misreading, not an empty one) still gets trusted as authoritative — this fix narrows one specific failure mode, it does not make the sender's re-derived value into ground truth in general.

## E-AUTONOMOUS (2026-09-30): a REAL 2-process negotiation with no human relay — built, honest scope
Every prior negotiation test still had either both canonical forms known to one caller (`negotiate()`), or a human copying a prompt between two chat windows (all 3 E-MCP third-party tests). Built `aixl/agents/sender_agent.py` (a real, standalone MCP server — its own OS process) and `aixl/autonomous_negotiation.py`'s `negotiate_autonomous()` (spawns it as a genuine subprocess, drives the same tested turn logic from `aixl/negotiation.py`, `negotiate()` itself untouched). The sender's `answer()` is recomputed fresh from its stored source on EVERY call, not cached at setup — closing the "is the ANSWER live?" critique the Claude Desktop third-party test raised earlier the same day.
Re-measured the real 21 E-INTEROP disagreements through two genuinely separate OS processes: 21/21 converge, avg 1.143 rounds — identical to the single-process number, now over real subprocess-to-subprocess MCP stdio JSON-RPC.
What this is NOT: for the 21 replayed cases, the sender answers from an already-fixed AIXL line (`--aixl` replay mode) — real process/transport separation, but not fresh natural-language re-interpretation on each question (that liveness is only shown on the smaller `--text`-mode cases, e.g. "Close/Delete ticket #77", "Quita el ticket #77"). The sender remains trusted as authoritative for the disputed dimension, same design principle as `negotiate()` — this closes the "no autonomous exchange" gap, not "is the sender's answer provably true." Only one sender + one receiver have been shown negotiating this way, not two full peer AIXL Semantic Core instances with neither side privileged.

**Wired into the real MCP server the same day**: `aixl_negotiate_autonomous` added to `aixl/mcp_server.py` — a real MCP client calling this ONE tool makes the server spawn a genuinely separate sender-agent subprocess (a THIRD process, distinct from both the calling client and the server) and negotiate with it over real MCP stdio, no human relay anywhere in the chain. `negotiate_autonomous_async()` was exported from `aixl/autonomous_negotiation.py` so the server's own async tool handler can `await` it directly (the sync `negotiate_autonomous()` still exists for scripts). Verified with the SDK's own client and a new subprocess-based integration test, 147/147 total.
Still open: this has only been called from this project's own SDK-client test — no real DEPLOYED client (Claude Desktop/Codex/Antigravity) has invoked `aixl_negotiate_autonomous` itself yet, even though those clients already have this same server registered and would see the new tool on their next restart.

**A real bug the real Claude Desktop test found that this project's own reproductions could not** (2026-09-30): both a real Claude Desktop call and this Code session's own connection failed twice with a generic "Error executing tool", no detail — while every local reproduction attempt (direct spawn, an empty env, the exact restricted env from Claude Desktop's config, even the same `disclaimer --pgroup` wrapper Claude.app uses internally) succeeded. Root-caused from the `mcp` SDK's own source: its default env-inheritance for a spawned stdio process (`DEFAULT_INHERITED_ENV_VARS`) does NOT include `PYTHONPATH` — across two layers of MCP process spawning (host app → this server → the nested sender-agent), that silently drops the one variable the nested process needs. Fixed by building the nested child's `env`/`cwd` explicitly instead of relying on inheritance; also hardened the tool to return a real traceback instead of an opaque error on any future failure.
Honestly: **this fix has not been confirmed against the actual failure** — the failure itself was never reproduced locally, so this is the best evidence-grounded hypothesis available (real SDK source, not a guess), not a proven root cause. Needs a real retest from Claude Desktop to confirm.

## E-MCP-DESTRUCTIVE (2026-09-30): negotiation used to trust the sender even on irreversible actions — found by the same real Claude Desktop retest, fixed
The retest above CONFIRMED the env/cwd fix (a real Claude Desktop call converged correctly on "Close ticket #77." vs "Delete ticket #77." → UPDATE). But the same test then raised, unprompted, a real concern: closing a ticket is reversible, deleting it is not — yet the negotiation ACCEPTed after one round of blindly trusting the sender, with no signal that DELETE (the losing candidate) is irreversible, even though `aixl_compare` on the identical pair already reports CRITICAL_DRIFT/"destructive action involved". Verified systematic with 3 real pairs (Close/Delete, Archive/Delete, Send/Delete).
First fix (reuse comparator's `destructive_actions`: DELETE/EXECUTE/SEND/DISABLE/UPDATE) broke 8 existing tests — UPDATE is on that list and is extremely common, including in the project's own long-standing reference case. Caught by the full suite, not shipped. Narrowed to a smaller, separate `irreversible_actions` config list (DELETE only): `destructive_actions` stays exactly as it was, used only for comparator's own severity display; the new list gates ONLY whether `negotiate()`/`negotiate_autonomous_async()` may auto-resolve an `actions` disagreement or must REJECT and ask a human.
**Re-measured the real 21 E-INTEROP disagreements**: now 20/21 converge (was 21/21) — a real correction, not a regression: the case that now REJECTs (`t061`) is one where Gemini genuinely misread "excluir" (EXCLUDE) as DELETE; the old number had silently trusted the correct sender with no way to distinguish that from a case where the sender itself got it wrong.
What this is NOT (as first shipped): `irreversible_actions` was scoped to DELETE alone. It also doesn't cover ANTONYM_ACTIONS-style contradictions (e.g. ENABLE vs DISABLE) on a non-DELETE pair — untested, not addressed here.

**Widened the same day, at the user's request, to EXECUTE and SEND** — re-measured the real 21 E-INTEROP disagreements (now 18/21, was 20/21) and examined each new REJECT individually rather than just counting: SEND's addition is backed by a genuine bug (`t092`: Gemini over-extracted SEND from a temporal clause, "before sending it", when only CHECK was actually commanded). EXECUTE's addition is more debatable — its one affected case (`t077`, "schedule the call") isn't genuinely irreversible under either reading; EXECUTE as a translator vocabulary LABEL doesn't always mean "runs something you can't undo" in the real world. Reported honestly rather than silently reverting EXECUTE or declaring the widening fully validated.

**Wider evidence search then confirmed the split, and EXECUTE was removed** — scanned a completely independent, larger real corpus (the 200-pair E-XV cross-vendor dataset, `data/xv/answers5/`, not just the 21-case E-INTEROP set) for every real cross-vendor disagreement involving EXECUTE or SEND (full breakdown: `BENCHMARK/results_irreversible_actions_evidence_search.md`). Found 9 more real EXECUTE-involving disagreements, 7-8 of which are the SAME vocabulary quirk as `t077`: a sentence literally says "execute/run the analysis," and one vendor mistags the introductory verb as the action instead of recognizing `ANALYZE` — completely benign either way. Combined: 8 of 10 real EXECUTE instances across two datasets are noise, not danger — removed. SEND found 2 more real, distinct supporting cases in the same search — kept, now backed by 3 independent real instances total (2 datasets).
**Final state**: `irreversible_actions` = `["DELETE", "SEND"]`. Re-measured the real 21 E-INTEROP disagreements one last time: **19/21 converge** — exactly the 2 cases with real evidence (`t061` DELETE, `t092` SEND) REJECT; the EXECUTE false positive (`t077`) resolves normally again. What this is STILL not: EXECUTE and SEND's evidence base remains small (a handful of real cases each, across 2 datasets totaling ~421 texts) — a larger corpus could still surface counter-evidence; `irreversible_actions` doesn't cover ANTONYM_ACTIONS-style contradictions on a non-DELETE/SEND pair.

## E-A2A (2026-09-30): built a SECOND real protocol adapter (A2A, over HTTP instead of stdio), honest scope
`aixl/adapters/protocol_adapter.py`'s `A2AAdapter` used to raise `NotImplementedError` like every other still-unbuilt adapter. Now it encodes/decodes an AIXL message as a real A2A `Message` (Google's official `a2a-sdk`, protobuf-typed) and validates it against the SDK's OWN `Message` protobuf descriptor via `google.protobuf.json_format.ParseDict` — not a hand-rolled guess of the wire shape, same standard as `MCPAdapter`. `aixl/agents/a2a_server.py` is an actual running A2A agent (real HTTP server via `starlette`+`uvicorn`) exposing one skill, `aixl_compare`, discoverable at the spec's real `.well-known/agent-card.json` endpoint. Real validation: `tests/test_a2a_integration.py` spawns the agent as a genuine subprocess bound to a real socket and drives it with the SDK's own `ClientFactory`/`Client` over a real JSON-RPC/HTTP round-trip (3/3 pass) — not an in-process mock, same standard as `test_mcp_integration.py`.

What this is NOT: proof that AIXL interoperates with an unrelated, independently-built A2A client or agent — the only client that has ever talked to this agent, so far, is this project's own test suite (unlike MCP's 3-independent-vendor confirmation). Also not exercised: A2A's task-lifecycle features (streaming, push notifications, multi-turn `input-required` flows, task cancellation) — this experiment deliberately scoped to the "immediate response" workflow (one synchronous reply Message, never a long-running Task), which is what `aixl_compare` genuinely needs; `cancel()` on the executor honestly raises `UnsupportedOperationError` rather than pretending to support a lifecycle this agent doesn't have. Only one skill is exposed (`aixl_compare`), not `aixl_translate`/`aixl_negotiate`. REST/OpenAPI/GraphQL remain unimplemented.

A genuinely different architectural shape from MCP was found by reading the SDK before writing any code, not assumed: A2A's `Message`/`Task`/`Part`/`AgentExecutor`/`TaskStore` model is built for long-running, stateful, potentially multi-turn agent interactions — a materially heavier and more general design than MCP's simple synchronous tool call. This is real, useful evidence about what "protocol-agnostic" actually costs in practice: the two adapters built so far (MCP, A2A) are not interchangeable in complexity, even though both now genuinely work.

## E-A2A-NEGOTIATE (2026-09-30): negotiation as a native multi-turn A2A Task, honest scope
Reviewed E-A2A's own honest finding (A2A's Task model is heavier than MCP's simple call) at the user's request and found it was an opportunity, not just a cost: AIXL's negotiation protocol is genuinely multi-turn, and A2A's `TASK_STATE_INPUT_REQUIRED` + TaskStore do natively what E-AUTONOMOUS had to build a whole separate mechanism for over MCP. `aixl_negotiate` as an A2A skill now pauses and asks a human when, and only when, a disagreement involves an irreversible action (`aixl/resources/config.json`'s `irreversible_actions`) — making real a claim (`negotiate()`'s REJECT message: "requires human confirmation") that previously had no actual mechanism behind it.

Two real bugs were found by actually running the round-trip, not by reading the code and assuming it correct — both fixed, both now regression-tested: (1) the human's answer was applied only to the receiver's belief, leaving the sender's own canonical value unchanged, so the exact same disagreement kept reappearing after resume; (2) the irreversible-action check was placed before the empty-sender-value check — the SAME ordering mistake made and fixed earlier the same day in the `negotiate()`/`negotiate_autonomous_async()` merge (AUDIT.md finding #4) — causing an out-of-vocabulary sender case to pause and ask a human to choose "DELETE" vs "NOT_SPECIFIED" instead of correctly rejecting outright.

What this is NOT: proof that A2A's task model is "lighter" now — it isn't; this experiment uses that same weight deliberately, for the one capability that actually needs it, rather than avoiding it. Not yet exercised: a negotiation needing TWO separate human-confirmation rounds in one task (untested, though the loop structure should support it); `cancel()` on a negotiation task mid-flight (still `UnsupportedOperationError`); any independent third-party A2A client driving this multi-turn flow (still only this project's own test client, same honest gap as E-A2A itself).

## E-BLIND10 (2026-10-02): first benchmark written by OTHER models (Opus + Haiku, no repo access) — the "same author" bias, measured
150 natural, untemplated cases each (30 per class, ES/EN/PT, open domains), `data/blind10/`, evaluated with the unchanged `predict()` of the 5x100 benchmark (`python -m benchmarks.blind10_eval FILE`). Nothing was tuned before running.
**Result: Opus-authored 60/150 = 40.0 %; Haiku-authored 37/150 = 24.7 %** (own 5x100: 99.4 %). Per class (Opus/Haiku): EQUIVALENT 19/13, NOT_EQUIVALENT 14/8, PARTIAL 13/11, AMBIGUOUS 9/1, CONTRADICTORY 5/4 (of 30).
**Verdict on the hypothesis for the rule-based pipeline**: the 99.4 % did NOT generalize. The translator is a closed-vocabulary system; on open-domain text it fails mainly by treating different sentences as EQUIVALENT (Opus 42, Haiku 46 false-EQUIVALENT among non-equivalent pairs: "CFO"→"CEO", "daily"→"weekly", "read-only"→"full access", "$500"→"$1000" were all judged equal).
**Safety signal**: the UNRECOGNIZED_TERMS warning (§66) accompanied 34/42 (Opus) and 21/46 (Haiku) of those false-EQUIVALENTs, so about half to four-fifths are flagged but a large share (8 and 25) are silent.
Not claimed: that the architecture (Core + AIXL) is wrong — only that the rule-based parser's coverage is the bottleneck, consistent with the earlier distill finding (data-limited). Not fixed here; fixing per-item would overfit the new set. Candidate next step: use the LLM-translator route (which scored 95 %+ on E-XV) on this same set for a like-for-like comparison.

### E-BLIND10 round 2 — LLM route (Sonnet, card 0.3 frozen, 6 fresh agents, texts only, 0 parse failures)
`python -m benchmarks.blind10_llm_eval data/blind10/ans_sonnet_*.txt` (same class mapping, on decoded graphs). **111/300 = 37.0 %** (Opus-authored 43.3 %, Haiku-authored 30.7 %) vs rule-based 40.0 % / 24.7 %. Per class (of 60): EQUIVALENT 55, NOT_EQUIVALENT 17, PARTIAL 14, AMBIGUOUS 9, CONTRADICTORY 16. **106 false-EQUIVALENT**.
**Diagnosis from the encodings (not a guess)**: the LLM encodes faithfully what the card has slots for and silently DROPS what it doesn't: "15 %"→"25 %", "daily"→"weekly", "before 5 pm"→"before 3 pm", "CFO"→"CEO" (kept as `Y:@CFO`/`Y:@CEO`, not compared) all collapse to identical AIXL. So the 95 %+ of E-XV was an artifact of benchmark sets drawn from the card's own vocabulary; both routes (rules and LLM) share the same bottleneck: **AIXL 0.3's slot vocabulary is too narrow for open-domain instructions, and loss is silent**.
**Consequence for the hypothesis**: not refuted, but the evidence now says representational coverage — not parser quality — is the limit. A fix would be architectural (open slots: quantity with unit and comparator, frequency, time-of-day, recipient role, generic qualifier kept as compared text; plus an explicit "unencodable residue" field that makes drop non-silent), not another lexicon. Not implemented; should be designed against this set AND a fresh unseen one to avoid overfitting.

## E-ARENA-SCOPE (2026-10-10): the core comparator calls some meaning-changing edits EQUIVALENT — measured by the adversarial arena
`python -m lab.arena.arena scope` (fixed seed, 844 mutants, own-author seeds): `aixl.compare(...).equivalent` is True on **24** of them (2.8%). The unique patterns, so that nobody relies on them:
1. **An appended clause outside the lexicon**: "Envía el informe a Ana" vs "... a Ana and notify the whole team" (the extra clause is ignored).
2. **A dropped trailing clause**: "Compare the two documents and list the differences" vs "Compare the two documents".
3. **A modifier antonym outside the lexicon**: `temporal` → `permanente`, `old` → `new`, `duplicados` → `únicos`; and an unknown token (`duplicatres`) is ignored.
This is the same closed-vocabulary ceiling already documented above (open-text equivalence is only reliable in a controlled vocabulary). **What protects a message is not this verdict**: on the same 844 mutants the integrity envelope gave 0 false MATCH (it abstains with UNVERIFIED when either side is incomplete) and the gate shipped 0 lossy AIXL. Use `envelope.verify` / `gate.is_complete`, never `aixl.compare` equivalence alone, for open text.

### Update 2026-10-13 (consejo-5x audit): what changed after E-ARENA-SCOPE
- **The MCP `aixl_compare` and the A2A `aixl_compare` skill returned the raw core verdict** (`equivalent: true`, `similarity: 1.0`) for the 24-of-844 patterns above, with no warning, to three vendors' clients. They now return `aixl.compare_verified`: EQUIVALENT only when both texts are completely accounted for (same rule as the envelope) and they do not differ in disjunction; otherwise INCONCLUSIVE with `raw_verdict`, `reason` and the unaccounted words. On other authors' labelled pairs the false-EQUIVALENT rate went 19.7 % / 35.4 % -> 0 % (blind13 / blind14, n = 71 / 65 non-equivalent). **Price:** recall of true open-text paraphrases 22–25 % -> 0–2 % (dev set 100 % -> 76 %): for "are these two open texts the same?" use the 2-of-2 arbiter, not this.
- **A new meaning flip no layer saw: AND <-> OR** ("a Ana **y** a Luis" -> "a Ana **o** a Luis"). `y/o` are function words, so the core comparator said EQUIVALENT *and the integrity envelope said MATCH*. Fixed with a connective witness (`aixl.core.connectives.or_count`): the envelope stores it, `compare_verified` checks it, the arena has an attacker (`conj_swap`). Without the guard the arena finds 8 false MATCH in 415 mutants; with it, 0. Deliberately over-cautious: PT article `o` counts, so `o relatório` vs `relatório` also withholds the claim.
- **Availability:** `to_graph` was O(n^2) and no server bounded its input (62 KB took 5 s; 80–120 KB of repeated years/numbers took > 8 s). Inputs over 16,384 characters are now refused (`AIXL_MAX_INPUT_CHARS`; gate -> NATURAL, envelope -> UNVERIFIED, `compare_verified` -> UNVERIFIED) and four quadratic scans were removed (worst measured just under the limit: 0.21 s). One superlinear pattern remains (a long run of repeated full sentences: 124 KB ~ 2.5 s), bounded by the limit.
- **What the published layers cannot decide (arena, 2026-10-13, 13 META families, 1,676 mutants):** only 15 % of the mutants had both texts completely accounted for. Conditionals (`if/si/when/unless`), modality (`must/may/debes/puedes`), comparators and quantifiers with open nouns (`at least N`, `more than N`, `all the`), negation scope inside a conjunct and sequence order all push a text outside the closed vocabulary, so the envelope answers UNVERIFIED and `compare_verified` INCONCLUSIVE: **no wrong claim was made (0 defects), but no detection was demonstrated either**. "Obligation vs permission" ("You must delete X" vs "You may delete X") is not verifiable by AIXL at all today. Extending the vocabulary to model these as markers is the way to turn abstention into detection; until then use the 2-of-2 arbiter.

## E-LOGIC-VOCAB (2026-10-13) — comparators and conditionals are modelled; completeness is still bounded by nouns

- The translator now emits `CMP=GT|GE|LT|LE|EQ:<n>` (bound strictness bound to its number, spelling-canonical: `.9` = `0.90`) and `COND=IF|UNLESS|ONLY_IF|WHEN`
  (affirmations such as `si, muestrame` and `verify if` are excluded). `data/arena/logic_pairs.jsonl` (75 labelled pairs) +
  `benchmarks/logic_pairs_eval.py` + `tests/test_comparators_conditionals.py`: 0 DIFF pairs declared same; envelope false MATCH on comparator
  pairs 9/30 -> 0; conditional SAME 6/6 EQUIVALENT.
- What did NOT move: the arena's decided share is 17% (was 15%). Mutants such as `Borra los respaldos si ...` -> `a menos que ...` are now
  correctly NOT_EQUIVALENT, but `complete` stays False because the closed vocabulary does not account for the object nouns
  (`respaldos`, `registros`, `backups`). The ceiling on "decided" is the noun lexicon, not the operators. Widening it is a separate,
  measured step (each new term must pass the blind sets), not something this change claims.

### Update 2026-10-13: noun lexicon extension (aixl/resources/nouns_v1.json, 36 concepts x ES/EN/PT)
- Selected by frequency of unaccounted tokens on dev200 + golden_r + blind10-12 + arena seeds; blind13/14 held out for evaluation.
- Effect: objects such as backups/files/orders/tickets now reach the graph (before: silently dropped, so `Delete the backups` == `Delete the files`).
  Arena decided share 17% -> 23%; arena core false-EQUIVALENT 33% -> 25%; `compare_verified` false-EQUIVALENT stays 0 on all four corpora;
  logic pairs still 0 defects.
- Cost: core recall on other authors' SAME pairs drops 1-2 points (blind13 22->20%, blind14 25->22%) — synonyms across the new nouns
  (e.g. `issue` vs `ticket` are merged, `report` vs `summary` are not) now matter. Not a safety loss (core was already not trusted for EQUIVALENT).
- Still open: 77% abstain. The open vocabulary of real instructions is a long tail (hundreds of domain nouns); this is a sampled batch, not closure.
- Deliberately excluded: alert/notification (light-verb objects) and invoice/factura (benchmark + docs exemplar of an out-of-lexicon noun).

### Update 2026-10-13: arena over OTHER authors' seeds (`python -m lab.arena.arena scope --other`)
- 177 seeds written by Opus/Sonnet/Haiku sub-agents (`data/arena/other_author_seeds.jsonl`) that never saw the arena or the lexicons -> 6569 mutants.
- First run found 16 false EQUIVALENT in the semantic engine (`aixl.semantic.compare_texts`, behind the hybrid protocol/MCP): root cause `al menos`
  parsed as the exception word `menos` (swallowed the quantity), plus `must not` == `may not` and a negation lost under `que ninguno`. Fixed
  (root cause + fail-closed flags AMBIGUOUS_MAY_NOT / AMBIGUOUS_EMBEDDED_NEGATION / UNREPRESENTABLE_EXCEPTION); now 0.
- The published `compare_verified` and the envelope were already 0. DECIDED share on these seeds is **0.2% (15 of 6569)**: on realistic, longer
  instructions the closed vocabulary abstains almost always (own-author seeds: 23%). This is the real coverage number to quote, not the 23%.

### Update 2026-10-13: how far a hand-extended lexicon can go (`benchmarks/lexicon_coverage_curve.py`)
Ceiling analysis, selection corpus 4160 texts / 2399 distinct unaccounted words, evaluated on the held-out other-author seeds: knowing the top
50 words -> 2% of seeds fully accounted, 200 -> 3%, 800 -> 10%, ALL 2399 -> 22%. The long tail is the problem: a 36-noun block moved the
own-author arena share but cannot move realistic text. Decision: no more hand blocks of nouns; the decided share on realistic instructions
needs a different mechanism (an arbiter that checks the *residue* only, or open-vocabulary verification), not a bigger table.

## E-OPEN-VOCAB (2026-10-13): proving unknown words "the same" on both sides does NOT work safely — negative result, not shipped
Rule (aixl/core/open_vocab.py): core graphs equivalent + no unreflected marker + identical ordered sequence of unaccounted tokens
(+ rule 4: every differing token is accounted content, never an operator/function word). Measured by `benchmarks/open_vocab_eval.py`:
- v1 (rules 1-3): rescued 231 of 3957 meaning-changing mutants as EQUIVALENT (`Never if ...` vs `if ...`: marker reflection is per class, not per
  occurrence, so an existing negation "reflects" an added one) and 5 labelled DIFF pairs of other authors. Unsafe.
- v2 (+ rule 4): 0 false on own-author mutants, 2 of 3957 on other-author mutants (`Monday` -> `Tuesday`: weekday names are accounted but the core
  does not compare them) and 1 labelled DIFF pair; recall gained: 2 of ~40 SAME pairs. Fails the zero-false-EQUIVALENT requirement for a ~5% gain.
- Root cause is the base, not the rule: the core comparator is permissive on exactly the words it "knows" (weekday names, ordering words,
  per-class marker reflection), so any scheme of "core equal + residue equal" inherits those blind spots.
- Decision: `compare_verified` stays as is. Next real levers: harden the core where it is permissive (per-occurrence marker reflection,
  weekday/ordinal comparison), each with its own arena family; or an arbiter over the residue only.

### Update 2026-10-13: core hardened where it was permissive (surface operators -> constraints)
`DISJ=<n>` (or/ou/o/u; PT article `o` and `or more` excluded), `DOW=<days>` (ES/EN/PT canonical), `NEGN=<n>` (>= 2 negations, negative concord
aware) are emitted by the translator, so the CORE comparator sees them. Core-EQUIVALENT on meaning-changing mutants (known limit, not a defect):
own seeds 122 -> 82, other-author seeds 1244 -> 321. SAME recall of core unchanged on every corpus; published layers still 0 defects; suite green.
Remaining core-permissive families: lex_swap (`duplicados`->`únicos`), compose, drop_tail, modal_flip, num_change, add_constraint.

### Update 2026-10-13: lex_swap — contrast modifiers modelled (aixl/core/modifiers.py, `MOD=` constraint)
Of the core-EQUIVALENT lex_swap mutants, two real classes: (1) a known contrast word swapped for its opposite (`old`->`new`, `temporal`->`permanente`,
`activos`->`inactivos`): now 26 contrast concepts ES/EN/PT emitted as `MOD=<codes>` and counted as accounted words only when the graph carries them;
(2) a changed word that is UNKNOWN (typos / gibberish: `duplicatres`, `csome`): nothing to model — the published layers abstain because the word is
unaccounted; the core alone cannot see it (documented limit).
Deliberately not in the table (already modelled; a second path broke convergence tests): older/newer than, recent, public/private, urgent, open/closed.
Core-EQUIVALENT on meaning-changing mutants: own seeds 82 -> 25, other-author 321 -> 279; arena decided share 23% -> 30% (own seeds), published layers 0
defects, SAME recall of the core unchanged on every corpus (after adding repeated/redundant to DUP: one paraphrase pair had split).

### Update 2026-10-13: compose residue — three real silent drops found and fixed
Reading the core-EQUIVALENT `compose` mutants (not just counting them) found three genuine gaps, not arena artefacts:
- the DAY of a month was dropped (`March 3rd` == `March 4th`, `after August 1st` == `after August 2nd`): now `DAYM=MAR-03`, unless a full ISO date
  already carries it;
- a hyphenated duration was dropped (`45-minute sync` == `54-minute sync`): `45-minute` is normalised to `45 minute`;
- `older`/`newer` without `than` (`keep the older record`): comparative modifiers OLD/NEW, while `older than N` stays the AGE constraint.
Still open and documented: an appended clause whose verb folds into an existing action (`copy the team on the email` + `and notify the whole team`
stays SEND), and unknown-word typos (the core cannot see them; the published layers abstain). Core-EQUIVALENT on mutants (other authors) 279 -> 259.

### Update 2026-10-13: modal_flip — modality strength modelled (`MODAL=SHOULD|MAY|SHOULD_NOT|MAY_NOT`)
`must`/`may`/`should` were function words: no layer compared them, so `You must delete` == `You may delete` in the core. Now only the WEAKER
readings are emitted (`must`/`debes`/`deve` and the bare imperative are the same thing, `must not` is the negation already modelled):
SHOULD (should, ought to, deberías, deveria ...), MAY (may, can, puedes, pode, allowed to ...), with `_NOT` when negated (`cannot`, `no puedes`).
Excluded on purpose: `May` the month (neighbour words) and polite questions (`Can you send it?`, `¿Puedes enviarlo?` == the imperative).
Core-EQUIVALENT on meaning-changing mutants: own seeds 25 -> 15, other authors 259 -> 227; recall of SAME unchanged; published layers 0 defects.
Residual: `may not` is genuinely ambiguous (not permitted / not necessarily) and is carried as MAY_NOT, distinct from `must not`.

### Update 2026-10-13: drop_tail — a dropped trailing clause is now visible (`CLAUSES=<n>`)
A coordinated clause led by a verb OUTSIDE the lexicon (`and list the differences`, `y destaca las quejas`, `and attach their ...`) vanished without
trace. Pattern, not lexicon: conjunction (and/y/e/also) + word + determiner/possessive/pronoun counts as a clause; clauses whose verb already became an
ACTION are not double counted; `then/luego/depois` sequencing stays with the ORDER constraints; noun coordination (`logs and backups`) has no
determiner and is not counted. Core-EQUIVALENT on mutants: own seeds 15 -> 10, other authors 227 -> 205; published layers 0 defects.
Cost, measured: 1 of ~110 labelled SAME pairs of other authors splits in the core (blind14 12 -> 11) — surface differences such as `y reporta los` vs
`e informa de los` (a preposition, not a determiner, follows) are asymmetric. DIFF false-EQUIVALENT of the core: blind13 14 -> 13, blind14 21 -> 20.
Residual: a clause whose verb is followed by a preposition (`comparte con`, `compartilhe com`) is not detected; counting prepositions would turn
noun coordination into false clauses.

### Update 2026-10-13: neg_suffix / neg_prefix / neg_scope — a second negation no longer hides behind an existing one
The graph carries negation as a boolean, so a text that already negated (`process it without asking...`) swallowed any added `Do not`, `no lo hagas`,
`não aponte`. `without`/`sin`/`sem` now count as negators in `NEGN=<n>`, and `but/pero/mas/porém` (+ an optional adverb such as `primero`/`first`)
open a counted clause like `and` does. Core-EQUIVALENT on mutants: other authors 205 -> 141, own seeds unchanged (10); SAME recall of the core and
published layers unchanged (0 defects).
Residual: a negation inside an unknown-verb scope change that keeps the token counts equal (`no` moved from one clause to another) stays invisible.

### Update 2026-10-13: loop pass 1 — clock times, windows, weekday relations, ONLY, CANCEL, modal counts (`benchmarks/loop_pass.py`)
Residue of the arena (other authors) read pair by pair, fixed in the translator: `16h`/`16h30`/`às 14 horas`/`5 de la tarde`/`noon` now give TIME_AT (and
`at 5 pm` no longer ALSO emits QTY=5, which split it from `17:00`); `entre 14h e 16h` -> TIME_BETWEEN; `antes del viernes`/`before Friday` ->
DOWREL=BEFORE:FRI; `only/solo/apenas/somente` counted (ONLY=n, `only if/after/before` excluded); CANCEL joins the action table; a second `may` is
`MAY:2`. Core-EQUIVALENT on mutants: own seeds 10 -> 2, other authors 141 -> 40; published layers 0.
Net labelled DIFF pairs the core calls EQUIVALENT: 39 -> 38 (2 fixed: `Pausa`/`Cancela la campaña`, `Cancele`/`Adie a reunião`; 1 exposed:
`Si llueve, cancela el evento y avisa…` vs `Cancela el evento y, si llueve, avisa…` — the condition's SCOPE over one action is not modelled; the new
CANCEL action made the two graphs otherwise equal. compare_verified abstains on it).

### Update 2026-10-13: loop pass 2 — read on blind15-18 (other authors, never tuned on)
Core-EQUIVALENT on labelled DIFF pairs of blind13-18: 86 -> 70 (b13 14->11, b14 19->14, b15 17->15, b16 18->14, b18 5->3, b17 13 unchanged);
core SAME recall 53 -> 50 (3 paraphrases split; published layers unaffected: 0 false-EQUIVALENT on all 318 DIFF pairs, verified recall unchanged).
Added: `SEQ=` order of action/entity concepts, only on sequencing cues (`then/luego/depois/despues`, sentence-initial `primero`; ordinals such as
`primer trimestre` excluded — they cost two true paraphrases in the first attempt, the unrestricted version lost 8 of 58 dev paraphrases and was
discarded); `MEAS=<n>:<UNIT>` and `PER=<UNIT>` (mg/ml/g/kg/l/ha/alqueire/km/mile/°C/currencies); `MOD=BUSINESS|SENDER|RECIPIENT|ACTUAL`;
`FREQ=ALWAYS`; `NEGW=<n>` only when the graph lost the negation (unknown verb; `until` and comparator negations excluded); `ONLY=<n>@<concepts before>`.
Tried and removed: APPROVE as an action (`has approved` inside a subordinate clause became a second action and split `only after` from `until`).
Not modelled (honest list, from the same read): swapped recipients/roles (`al comprador ... al vendedor`), pronoun reference (`dale a él`/`a ella`),
added destinatario/payment-method/warning phrases after a complete instruction (`y a su contador`, `con tarjeta corporativa`), approve vs review.
Residual confirmed by test, not claimed fixed: the position of `only`/`solo` and step reorder are only visible when the sentence's objects are in the
lexicon (`Solo el notario puede firmar el acta` vs `El notario puede firmar solo el acta`; `back up the database, then run the migration` reversed).
Loop pass 2b: the Spanish `o` was counted as a disjunction only when the language detector said `es`, but `Envía el informe a Ana o a Luis` is detected
as `en`; now every `o` counts unless the text is detected as Portuguese (article). Core-EQUIVALENT on own-seed mutants: 0 (was 2).

## E-LAYERED-ARBITER (2026-10-14): the arbiter behind the deterministic layers — what it adds and what it does not
`aixl.arbiter.layered_decide(a, b, judges, memo)`: `compare_verified` EQUIVALENT (proof, no judge) -> SAME; everything else goes to the existing
2-of-2 full-text arbiter (SAME only if every judge says SAME). Measured offline on the stored judgments of blind17 + blind18 (115 pairs;
`benchmarks/layered_eval.py`, no model called): arbiter alone 52/54 SAME proven, 58/61 DIFF found, 2 false SAME (both disputed labels:
a double negation `No es cierto que no debas` = `Debes`, and `X después de Y` reordered); layered: identical numbers, 2 UNSURE (invalid judge
output). On open-domain text the deterministic proof fires on 0 of 115 pairs, so layering saves no judge call there and adds no correctness —
consistent with EVIDENCE.md. What it does add is a deterministic answer (no judge, no cost) wherever the vocabulary is controlled, and an audit
trail (`deterministic` hint + judge verdicts + stored decision).
First design rejected by measurement: treating a deterministic NOT_EQUIVALENT as FINAL (or as a veto) dropped proven SAME from 52/54 to 13/54, because
on 411 labelled pairs of blind13-18 a NOT_EQUIVALENT on a text that is not fully accounted for is right only 50 % (205 DIFF / 206 SAME); when both
texts are fully accounted for it was 6 of 8. So NOT_EQUIVALENT is "not proven equal", never "proven different". `compare_verified` now adds
`difference_reliable` (true only when both texts are accounted for) and the MCP tool description says so.
Consequence for the 0.2 % coverage figure: it is the share the DETERMINISTIC layers can decide; with the arbiter in the loop every pair gets an
answer at ~$0.28 per 1 000 pairs (EVIDENCE.md), with the arbiter's own measured error (1.2 % flip, 2-of-2).

## E-RELAY (2026-10-22): what AIXL CAN do for agent-to-agent hand-offs — preservation of critical slots (`aixl.relay_check`, MCP `aixl_relay_check`)
Context: the proprietary language could not be spoken between AIs (LLM encode/decode routes: 0 % proven on open text), and equivalence of free paraphrases
needs the arbiter. What survives, and what is measurable without any vocabulary: **did a critical slot change on the hop?** Negation, numbers, dates,
weekdays, clock times, modality (`must`/`may`), `and`/`or`, conditions, `only`, comparators, extra clauses, named entities — closed-class words, digits and
capitalised tokens, extracted deterministically in ES/EN/PT as language-independent codes (`aixl/invariants.py`).
- **Regime where it works (near-verbatim relays: copy, truncation, a flipped word, an injected clause).** `benchmarks/invariants_relay_eval.py`, other
  authors' seeds (never seen by the code), families chosen on the project's OWN seeds by a stated rule (benign false-alarm rate <= 0.5 %, >= 1 detection):
  **91.8 % of 2 622 meaning-changing corruptions flagged, 0.1 % of 1 141 benign edits flagged** (case, whitespace, newline, politeness prefix, contraction,
  markdown, quotes). By attack: negation / condition / quantifier / modality / name swaps 95–100 %, number change 93 %, dropped tail 86 %, added constraint 85 %.
  **Blind spot by design: antonym of a verb 0/18** (`send` -> `cancel`) and any change that touches only vocabulary.
- **Regime where it does NOT work (adversarial paraphrase pairs).** On blind13-18 (author-written SAME paraphrases vs near-miss DIFFERENT), most families fire as
  often on SAME as on DIFFERENT (lift ~1: `NEGATION` 41 SAME vs 17 DIFF — paraphrases legitimately restructure negation: `sin casco` / `casco obligatorio`);
  the only families with lift >= 2 on dev (`CLAUSES`, `DISJUNCTION`) detected 8–11 % of DIFF at 3–10 % false alarm. So `relay_check` must not be used to
  decide whether two differently-worded texts are equivalent. That is the arbiter's job.
- Bugs this harness found in the translator (fixed): quotes / markdown around a whole instruction lost `COND=IF` and the negation (`^` anchor); a Portuguese
  article `o` was counted as the Spanish disjunction when a Spanish politeness prefix confused the language detector; a sentence-initial word after leading
  whitespace was taken for a named entity.
- `ok: true` is never an equivalence claim. Unanalysable input (over the size cap) returns `ok: false`.

### E-RELAY-LLM (2026-10-22): `relay_check` on relays written by real models — preregistered, run once (data/relays/PREREG.md, FREEZE.json, RESULT_preregistered_run.txt)
120 sources, two model authors (Opus, Sonnet) acting as an intermediate agent, no access to the repository; per source a near-verbatim faithful relay, a strongly reworded
faithful relay and ONE subtle corruption (5 of each of 12 types). Code frozen by hash before the outputs were read.
| Preregistered hypothesis | Result | Verdict |
|---|---|---|
| H1 corrupted relays flagged >= 70 % | **91/120 = 75.8 %** | MET |
| H2 near-verbatim faithful relays flagged <= 5 % | 10/120 = 8.3 % | **NOT MET** |
| H3 strongly reworded faithful relays flagged <= 25 % | **109/120 = 90.8 %** | **NOT MET** |
| H4 antonym_verb, role_swap, pronoun_reference each >= 50 % | 50 %, **20 %**, 90 % | **NOT MET** (role_swap) |
Per type: conjunction 100 %, omission / date / number / negation / pronoun 90 %, condition / entity / modality 80 %, scope 50 %, antonym_verb 50 %, role_swap 20 %.
**What this means.** The detector catches most realistic corruptions, but when an intermediate agent REWORDS the instruction (the usual way agents hand work over) it
flags 9 of 10 faithful relays: moving a negation, swapping `approve`/`be approved by`, adding `them` are legitimate and move the slots. So `relay_check` is a
**copy / tamper / near-verbatim** detector, NOT a quality gate for paraphrasing agents; for those the arbiter is the tool and `relay_check` is only evidence for it.
Missed: scope widening without a closed-class word (`support team` -> `company`), a swapped role noun with no capitalised name (`Rodrigo` / `el contador`), a noun-level
antonym (`declining` -> `accepting`, `back up` -> `restore` outside the verb table), one-digit-word changes (`fourteen` -> `fifteen`: number WORDS are not compared unless in the table).
**Post-hoc (NOT part of the preregistered run, set already spent):** two genuine translator bugs behind near-verbatim false alarms were fixed — a sentence-initial
Portuguese `O` counted as a disjunction, and `ao e-mail` read as the verb `e-mail` (action SEND). Near-verbatim false alarm 8.3 % -> 7.5 %; nothing else moved
(RESULT_postfix.txt). The residual light false alarms are surface variation (`isn't available` / `unavailable`, `check` / `check them`, `aponte` / `indique`).

## E-HYBRID-RELAY (2026-10-22): `relay_check` as evidence for the 2-of-2 arbiter — preregistered, run once; REJECTED
Same 120 sources / 360 relays written by Opus and Sonnet (E-RELAY-LLM); judges Sonnet and Haiku read only `rules_v1` + (id, a, b), 4 blocks of 90, labels never shown
(`data/relays/PREREG_HYBRID.md`, `judge_key.json`, `JUDGE_*.tsv`, `RESULT_hybrid.txt`; no judgment was lost or invalid: 720 valid lines, 1 UNSURE).
| Arm | corrupted accepted as SAME | proven SAME, near-verbatim | proven SAME, reworded |
|---|---|---|---|
| A  2-of-2 arbiter alone | **1/120 = 0.8 %** | **120/120** | **117/120** |
| B  + veto on hard-fact slots (number, date, weekday, clock, name, bound, unit) | 1/120 | 120/120 | 99/120 (-15 %) |
| C  + veto on any slot | 0/120 | 111/120 | 11/120 (-91 %) |
Hypotheses: H5 (arbiter alone has >= 5 % false SAME so there is something to fix) **NOT MET** (0.8 %); H6 (veto cuts false SAME by >= 30 %) **NOT MET** (1 -> 1);
H7 (veto keeps >= 97 % of proven SAME) **NOT MET** (219/237 = 92 %); H8 (full veto loses > 10 % on reworded relays) **MET**.
**Decision: the hybrid is not offered.** The arbiter alone is already strong on realistic relays — 237/240 faithful relays proven (98.8 %), 119/120 corruptions caught (the one
accepted, `Não altere` -> `Evite alterar`, softens a prohibition and is arguably a judgement call). The veto can only remove SAMEs; here it removed 18 correct ones and added
nothing. `relay_check` therefore stays what it is — a free, offline copy / tamper detector for near-verbatim relays — and the arbiter is the tool for reworded ones.
Limits: 120 sources, two relay authors and two judge families from one vendor; the 95 % interval of a 1/120 false-SAME rate is roughly 0.02-4.6 %.

## Improvement round 2026-10-26 (method: find with evidence, smallest change, verify, record)
**Found (confirmed by running it):**
1. **A false EQUIVALENT from the published `compare_verified`.** `Envie o relatório dos clientes` vs `Envie o relatório aos dois clientes` -> EQUIVALENT, verified, envelope MATCH.
   Cause: `dos` is the number 2 in Spanish and `de + os` ("of the") in Portuguese; the translator read it as 2 in both (QTY=2 on each side).
   Fix: `dos` is never "accounted" (`aixl/core/completeness.py`), so any text containing it is INCOMPLETE and no layer claims equivalence over it. `unaccounted` now lists the
   words completeness refuses. Cost, accepted: Spanish `dos clientes` vs English `two customers` is withheld (INCONCLUSIVE). The first attempt (counting `dos` in the OR
   witness) was rejected: `dos clientes` vs `dos dois clientes` still came out EQUIVALENT.
2. **Number words beyond ten were invisible** to the core (`fourteen`/`fifteen`, `catorce`/`quince`, `quatorze`/`quinze` all compared EQUIVALENT) and `relay_check` compared
   `fourteen` with `14` as different. One shared table and parser (`aixl/core/numberwords.py`: ES/EN/PT, compounds `treinta y cinco`, `dois mil`, `one hundred and five`;
   `one`/`uno`/`um` only before a unit); the translator's table is extended from it.
3. **Clock times in another notation were a "change"** (`6 pm` vs `18:00`, `6 de la tarde`, `15h30`): normalised to one token. A different time (`6 pm` -> `8 pm`) is still flagged.
4. **Spanish `la` counted as a pronoun** (`de la tarde`): removed; `él/ella/le/les/his/her/...` still count.
5. **Portuguese article `o` counted as a disjunction** after a politeness prefix: more Portuguese-only cues (number words, `quando`, `mais`, `qualquer`, ...).
**Measured after** (arena mutants, other authors' seeds; families chosen on own seeds as before): corruptions flagged 94.7 % -> 94.5 %, benign edits flagged 0.1 % -> **0.0 %** (0 of 1 141).
Core and `compare_verified` on labelled pairs (dev, arena paraphrases, blind13/14): false EQUIVALENT 0 on every corpus; verified recall unchanged (44, 1, 1, 0). Suite 1292 -> 1320 tests.
On the model-written relays (a SPENT set: regression check only, not evidence): corrupted flagged 91 -> 93 of 120 (the two number-word cases), near-verbatim faithful 10 (unchanged),
reworded faithful 109 -> 108.
**Not done / still open:** swapped roles without names (2 of 10), widened scope without a marker word, noun-level antonyms, `isn't available` vs `unavailable`. No real traffic yet.

### Improvement round 2026-10-26 (b): swapped roles
Evidence: on the 120 model-written relays only 2 of 10 swapped-role corruptions were flagged. Three patterns explained the misses: the actor moves (`Send Priya X` -> `Have Priya send X`,
`avísale a Jorge` -> `pídele a Jorge que te avise`), the addressee becomes `you`/`te` (`assign it to the team` -> `assign it to you`), and two roles trade places.
Added: `DELEGATION` (cues `have/ask/tell/request/instruct`, `pide/pídele/dile/pede/peça/diga`), second-person pronouns in `PRONOUN` and in the `NAME_ORDER` sequence,
and the accented `él` (the article `el` had been counted as a pronoun instead).
**Tried and removed — a negative result:** `ROLE_PAIRS` (the pairs preposition + head word, to catch two role nouns trading places). It added no swapped-role detection and
raised near-verbatim false alarms on model-written faithful relays from 10/120 to 25/120 (19 firings). Mechanical benign edits (1 141) had missed it entirely: **the arena's benign edits
are too gentle to be the only false-alarm test.**
Measured after the removal: arena corruptions 94.5 %, benign 0.0 % (unchanged). On the model-written relays (a SPENT set, and the swapped-role patterns were read from it, so this is NOT
evidence of generalisation): corrupted flagged 93 -> 100 of 120, swapped roles 2 -> 8 of 10, near-verbatim faithful 10 of 120 (unchanged), reworded 108 -> 107.
`DELEGATION` is in the default set by principle, not by the arena selection rule (it never fires on the arena's mutants). **A fresh set of model-written role swaps is needed before any claim.**

## E-ROLES (2026-10-26): swapped roles on FRESH model-written relays — preregistered, run once (data/relays_roles/PREREG.md, FREEZE.json, RESULT.txt)
Two new authors (Opus, Sonnet) wrote 90 instructions of their own (ES/EN/PT, half naming people, half only roles/teams) and, for each, a near-verbatim relay, a reworded relay, one swapped-role
corruption (four styles) and one control corruption. They never saw the code or the previous data; the code was frozen by hash before their outputs were read.
| Hypothesis | Result | Verdict |
|---|---|---|
| R1 swapped roles flagged >= 50 % | **65/90 = 72.2 %** | MET |
| R2 near-verbatim faithful flagged <= 10 % | 11/90 = 12.2 % | **NOT MET** |
| R3 control corruptions (negation/number/date/condition) flagged >= 70 % | 77/90 = 85.6 % (condition only 11/23) | MET |
| R4 every swap style flagged >= 30 % | actor_flip 63 %, addressee_to_you 95 %, delegation 100 %, **two_roles_swap 29 % (6/21)** | **NOT MET** |
Same data, code BEFORE the role changes (post-hoc comparison): swapped roles 37/90 -> 65/90 (addressee 3/22 -> 21/22, delegation 12/23 -> 23/23); near-verbatim faithful 10 -> 11; control 78 -> 77.
So the change does what it was designed to do on data its author had not read, at the price of one more false alarm in 90.
**What remains unsolved:** two roles trading places with no marker word (`Finance approves and Purchasing pays` -> `Purchasing approves and Finance pays`), 6 of 21; `actor_flip` between two
role nouns (`The night shift hands the log to the morning shift` reversed) is only caught when a name is involved. Both need who-does-what binding (subject-verb pairing), which the
closed vocabulary does not give for unknown verbs; the earlier shortcut (`ROLE_PAIRS`) was a measured failure. Language: es 77 %, en 73 %, pt 67 %. Sample: 90 sources, two authors.

### E-ROLES follow-up (2026-10-26): the 11 false alarms on near-verbatim faithful relays, one by one
Read from data/relays_roles (so that set is now SPENT for false-alarm claims; the gains below are not independent evidence):
- **Confirmed translator bugs, fixed:** `hand over the 6 laptops` was read as "more than 6" (phrasal verbs `hand/turn/pass/take/carry/look/roll/go over`); `siempre que` was not a
  condition and `siempre y cuando` was one only by accident (it contains `cuando`; now both are IF, and `once` / `as soon as` / `en cuanto` / `assim que` are WHEN, `provided that` /
  `as long as` / `desde que` are IF); `by Friday noon` lost its weekday relation when written `by noon on Friday`.
- **Confirmed design fixes:** the Portuguese article `o` was a disjunction in a relay that lost the word revealing the language (`deve` -> `tem que`): the language is now decided once for
  the PAIR; two delegation cues (`solicita` / `pede`) are one fact: the total is compared.
- **Tried and reverted:** flag `ACTION` only when both sides have a known verb (it removed 2 false alarms, `encaminhar` / `enviar`, but cost 6 of 18 antonym corruptions in the arena): in a
  safety detector a missed corruption weighs more than a false alarm.
- **Left as real changes:** `should` -> `needs to` (a stronger modality) and `para confirmar` -> `y confirma` (a purpose clause became a coordinated one).
Result: near-verbatim faithful relays flagged 11/90 -> 5/90 on the fresh roles set, 10/120 unchanged on the earlier set, arena 94.5 % / 0.0 % unchanged, swapped roles 65/90 unchanged.

### E-ROLES follow-up (2026-10-26): conditions — `relay_check` now compares WHAT the condition says
The 12 condition corruptions that slipped through all kept the connective and changed the content (`critico` -> `menor`, `renovado` -> `cancelado`, `internacional` -> `refrigerado`,
`regression tests` -> `smoke tests`, `estavel` -> `instavel`). The graph already held the clause text; `relay_check` only compared the connective (`COND=IF`). New family `CONDITION_TEXT`
(clause text without its introducing connective, without articles; skipped when one side has no clause text, because a dropped condition is `CONDITION`'s job).
Measured: condition corruptions flagged 11/23 -> **22/23**, all control corruptions 77/90 -> **88/90**; swapped roles 65/90 and near-verbatim faithful 5/90 unchanged on the fresh set; arena
corruptions 94.5 % -> 94.6 %, benign 0.0 % (the family passes the arena's selection rule by itself); earlier model-written set: corrupted 100/120 unchanged, near-verbatim faithful 10 -> 13 of 120.
**Cost, accepted:** a word-level check cannot tell a synonym from an antonym: `requests` -> `asks for`, `politely` -> `nicely`, `unavailable` -> `isn't available`, `cair` -> `entrar` inside a
condition are flagged with `estavel` -> `instavel`. A missed `critico` -> `menor` weighs more than that alarm. Evidence status: the 12 misses were read to design this, so the 88/90 is not
independent; the arena result and the earlier set are.

## E-USE-LIMIT (2026-10-29): a family for use-limit markers (`Confidential.`, `under NDA`, `Embargoed`, `for management eyes`, `Draft`) — preregistered, run once; v2 post-hoc
**Why.** A 12-pair probe (same author as the code: indicative, spent) showed `relay_check` missed 7 of 12 relays that dropped a PURE use-limit marker, because those markers carry no negation,
`only`, number, date or modal. `ok: true` then read "no critical slot changed" while a confidentiality notice had vanished (`compare_verified` was never wrong: it did not claim equivalence).
Motivation from the literature: a 2026 preprint on boundary-metadata collapse (facts survive hand-offs, the markers limiting their use do not; unreviewed, two models).
**What.** `aixl.invariants.use_limits` / family `USE_LIMIT`: four COARSE concepts (CONFIDENTIALITY, LEGAL_HOLD, AUDIENCE, DOC_STATUS), ES/EN/PT, presence only, so `confidential` -> `internal-use
document` is not a change but dropping, adding or swapping the concept is. `RELAY_FAMILIES_V1` keeps the previous set for baselines.
**Evaluation** (data/use_limits/PREREG.md, FREEZE.json, RESULT_v1_frozen.txt): two models (Opus, Sonnet) wrote 80 fresh instructions without seeing code (ES/EN/PT; confidentiality, legal_status,
audience, doc_status), each with a faithful-light, a faithful-heavy, a marker-dropped and a one-corruption control relay.
Frozen v1 result (all four preregistered hypotheses PASSED): dropped marker flagged **82.5 %** (baseline with the old families 22.5 %); per style confidentiality 100 %, doc_status 85 %,
legal_status 85 %, audience 60 %; faithful-light flagged 7.5 % (same as before, 0 by USE_LIMIT alone); faithful-heavy flagged 90 % overall (not a gate), 8.8 % by USE_LIMIT alone (threshold 10 %);
control corruptions 97.5 %. By language: es 92 %, en 85 %, pt 71 %.
**A false-alarm class the fresh set did not show, found on OLD sets:** v1 raised USE_LIMIT on 2 truly-equivalent blind10 pairs (`para a diretoria` ≈ `to the board`): `for`/`para` + an audience word is
usually an ADDRESSEE, not a limit. v2 (post-hoc, justified by independent data, NOT evidence): bare `for`/`para` + audience only counts as a sentence-opening LABEL (`For management.`) or as
`for X eyes`; false alarms on equivalent pairs of the older sets 2 -> **0 of 1 280**. Cost, measured on the fresh set post-hoc (RESULT_v2_posthoc.txt): marker-dropped flagged 82.5 -> 75.0 %,
audience 60 -> 30 %, pt 61 %. Accepted: a missed audience marker is better than a normal recipient read as a change.
**Still missed (14 of 80 in v1; read after the freeze, NOT tuned):** audience written with a verb (`written for`, `addressed to`, `dirigido al`, `escrito para`, `voltado aos`, `direcionado à`) and
Portuguese legal/status phrasings (`sujeita a parecer jurídico`, `em litígio`, `em fase de aprovação`, `minuta`). The fresh set is now spent; the next lexicon extension needs a NEW set.
Presence only: it does not say WHICH audience (`for management` -> `for the board` is the same concept).

## E-RISK-COVERAGE (2026-10-29): which evidence makes a SAME claim safe — `benchmarks/risk_coverage.py`, `aixl.confidence.claim_tier`
Stored judgments only (no model called): blind17 + blind18, 115 pairs of other authors, 54 truly SAME. Claiming SAME, by tier: deterministic proof **P: 0 of 115 pairs** (open domain, consistent with
EVIDENCE.md); every judge SAME and `relay_check` ok (J+): 1 false in 18 (5.6 %, 1.0-25.8 %); every judge SAME but `relay_check` flagged (J): 1 in 36 (2.8 %, 0.5-14.2 %); judges disagree: 9 in 11
(81.8 %); all say different: 50 of 50 truly different. Cumulative "claim SAME when judges are unanimous": covers 52/54 true SAME (96 %) at 2/54 false (3.7 %, 1.0-12.5 %).
**Finding kept on purpose:** `relay_check` ok does NOT make a unanimous SAME safer (the same conclusion as E-HYBRID-RELAY: on paraphrase it is the wrong signal); the useful signal is the judges' agreement.
`aixl.confidence.claim_tier` returns the tier with its MEASURED rate, interval and scope; these are small samples and not a calibrated probability.

## E-TERM-CONFIDENCE (2026-10-29): per-term trust from data — evaluated, NOT implemented (negative result)
Idea: certify each term by measured disagreement instead of a hand list. Existing measurement (`benchmarks/lexicon_coverage_curve.py`, 4 440 selection texts, 2 600 distinct unaccounted words,
177 other-author seeds): even if ALL 2 600 words were known, only 25 % of seeds would have nothing left unaccounted (2 % today; top 400 words -> 7 %; top 1 600 -> 18 %). A per-term table cannot lift
coverage materially, and `difference_reliable` already captures the pair-level reliability (NOT_EQUIVALENT right 50 % when a text is not accounted, 6 of 8 when both are). A term table built from ~400
labelled pairs would also overfit. Conclusion: the arbiter stays the route for open vocabulary.

## E-HANDOFF (2026-10-29): receiving-side contract — `aixl.handoff.handoff_check`, MCP tool `aixl_handoff_check`
`relay_check` asks whether a relay lost something the SOURCE had; this asks whether the instruction we received carries the fields we need at all (required kinds DATE, NUMBER, NAME, CONDITION,
USE_LIMIT) and answers `ready` or `input-required` (ask the sender, do not guess). Closed-class detection, open vocabulary; unknown kinds are an error, never "satisfied". Checked on 10 hand-written
ES/EN/PT instructions (same author: indicative): 9 of 10 had every expected kind detected; missed `next quarter` as a date. Known limits: NAME needs a capitalised token not at the start of a sentence (a
lower-case name is not seen); DATE does not understand `soon`/`pronto` or relative periods. It says nothing about whether the instruction is correct. Not wired into the A2A agent (design only).

### E-USE-LIMIT v3 (2026-10-29): extended lexicon on a NEW, larger fresh set — preregistered (data/use_limits_v3/PREREG.md), run once; 4 of 6 hypotheses passed
The v1 set was spent, so the lexicon extension (audience constructions with a verb, Portuguese legal/status phrasings, hyphenated forms, more group nouns) was tested on 150 records from THREE
authors (Opus, Sonnet, Haiku; es 45, en 45, pt 60) that never saw the code, with a recipient decoy per record. Frozen code: FREEZE.json; result: RESULT.txt.
* **V1 PASS** — dropped marker flagged **91.3 %** (137/150; families without USE_LIMIT: 20.0 %). Per style: doc_status 100 %, confidentiality 94.9 %, legal_status 86.8 %, audience 83.3 %
  (v1 frozen set: 60 %, v2: 30 %). Per language: en 95.6 %, es 95.6 %, **pt 85.0 %**. Per author 86 / 96 / 92 %.
* **V4 PASS** — the recipient decoy (`send it for/to/para the board`) is flagged by USE_LIMIT in **0 of 150**; **V5 PASS** — control corruptions 96.7 %; **V6 PASS** — 0 of 1 280 equivalent pairs of the older sets.
* **V2 FAIL** — faithful near-verbatim relays flagged 13.3 % (threshold 10 %). Of those, only 1.3 pts come from USE_LIMIT (2/150); the old families alone already flag 12.0 % on this set (other authors,
  more varied edits). The threshold was written for the whole detector and this set exceeds it without the new family; reported, not repaired.
* **V3 FAIL** — strongly reworded (heavy) faithful relays flagged by USE_LIMIT alone: **23.3 %** (threshold 10 %; v1 set 8.8 %). Reading the 35: the heavy relay expresses the limit as a DESCRIPTION
  (`still awaiting confirmation`, `lodged with the court away from public view`, `cuyo contrato es objeto de una disputa`, `mantida em total discrição`) so the concept is present in the source
  as a marker word and in the relay only as prose, or the reverse. Presence-only detection cannot see a concept written outside the lexicon: this is the closed-vocabulary limit again, not a bug with a
  clean fix. It matters only where heavy rewording is the regime, and `relay_check` is documented as NOT a gate there (heavy relays are flagged 70.7 % without this family, 94.0 % with it).
* **Still missed (13 of 150, read after the freeze, NOT tuned):** open audience nouns (`investors`, `inversionistas`, `professores`, `gestores de RH`, `alta gestão` — `gestão/gestión` was not in the
  list), Portuguese legal phrasings (`objeto de inquérito`, `em disputa judicial`, `em processo de arbitragem`, `objeto de ação civil pública`, `em investigação`), and the single words `secreto`, `proprietary`.
  Lesson: the audience noun list can never be closed (any group can be an audience). A possible next step needs NEW data and a risk check: treat a STRONG audience verb (`written for`, `dirigido a`,
  `aimed at`) as the marker by itself, whatever noun follows — it risks `prepared for the meeting`.

## E-HANDOFF-NAMES (2026-10-29): why the hand-off contract does not see lower-case names — verified, two fixes measured and REJECTED
**Cause (confirmed in code and by a probe):** `invariants.extract` recognises NAME only as a capitalised token that is not at the start of a sentence, an `@handle`, a `#id`, an e-mail or a URL.
`envía el informe a ana` yields no NAME while `... a Ana` does; a lowercase `ana` is indistinguishable from `casa` without extra information. Names at the start of a sentence are skipped too.
**Two candidate fixes, each evaluated on an independent set written by a model without the code** (acceptance bars fixed before reading the data):
1. Names set (data/names_lower: 60 lowercase first names + 60 lowercase common-noun recipients, es/en/pt; bars: false positives on nouns <= 5 %, recall >= 50 %): a 240-name list detects **18 %**
   (11/60; 0 false positives; the set deliberately includes rare names), the word after `a/to/para` detects 72 % but flags **46 %** of the common nouns (`finanzas`, `marketing`, `contabilidad`): rejected.
2. Recipient presence (data/recipients: 160 instructions, 80 with a recipient and 80 without, with date / quantity / place / infinitive decoys; bars: detected >= 80 %, false "present" <= 15 %): `NAME` alone
   detects **19 %** (0 of 50 lowercase lines, 4 % false); the recipient-position detector detects **84 %** (41/50 lowercase) but claims a recipient in **45 %** of the lines that have none (`a la carpeta`,
   `a 15 dólares`, `to the shared folder`, `para el jueves`) and misses recipients without a preposition (`notify support`, `send john`): rejected, because a contract that says `ready` when a field is missing fails open.
**Decision:** neither is wired into `handoff_check`; `aixl/core/lowername.py` stays only so the two evaluations can be re-run. The honest design is to have the sender DECLARE the recipient as a structured field
instead of inferring it from free text. The contract documentation and the MCP tool description now say that a lower-case name is not seen.
* **Bug found by the unit tests after the freeze (v4, post-hoc, NOT evidence):** the Spanish contraction `a + el` = `al` was missing (`dirigida al equipo`, `dirigido al comité ejecutivo`). Fixed; re-scoring the same set: dropped
  marker 91.3 -> 92.0 %, audience 83.3 -> 86.1 %, es 95.6 -> 97.8 %; recipient decoy 0/150, older sets 0/1 280, heavy-relay alarms 23.3 -> 22.7 % (V2 and V3 still FAIL). Frozen result kept in RESULT_v3_frozen.txt.

## E-USE-LIMIT v5 (2026-10-29): a STRONG audience verb as the marker by itself — preregistered (data/use_limits_v5/PREREG.md), run once; **W2 FAILED**, then three post-hoc fixes (NOT evidence)
Candidate v5: after `written for / aimed at / addressed to / dirigido a / escrito para / voltado a / ...` ANY group counts as the audience, except an event, deadline, number, gerund/infinitive or technical target
(`prepared for the meeting`). 180 fresh records from three authors (Opus, Sonnet, Haiku): 90 `open_audience` (unusual groups: interns, patients, tenants, investors...) and 90 `decoy` (same verbs, complement NOT an audience).
Frozen result (RESULT_v5_frozen.txt; the v4 code scored on the same data is the baseline):
* **W1 PASS** — open-audience drops flagged **96.7 %** (v4: 16.7 %; en 92.6, es 100, pt 97.2). **W3 PASS** (faithful-light flagged by USE_LIMIT alone 0.6 %), **W4 PASS** (0 of 1 280), **W5 PASS** (spent v3 set).
* **W2 FAIL** — the decoy drops flagged by USE_LIMIT: **43.3 %** (threshold 10 %; v4: 5.6 %). The risk named when the round was planned was real: of the 39 alarms, 36 were the new behaviour (an event/period noun my closed list did
  not know: `feria`, `fase`, `campaña`, `seminário`, `quarterly business review`, `product launch event`...) and 3 came from the old lexicon (`auditoria interna`, `revisão jurídica`, `reservado`).
**Post-hoc work after reading the failures** (the data is now SPENT: three tuning passes on it, so the numbers below are NOT evidence and need a fresh set):
* v6: English puts the noun-phrase HEAD last, so both ends of the complement are checked against the event / time / technical lists; a gerund is only a purpose when it starts or heads the complement; more event, period, phase and
  campaign nouns in en/es/pt (found missing: `migracao` was in the Spanish list only — an implementation slip). Decoy alarms 43.3 -> 21.1 %.
* v7: a verb at the start of the complement (`aimed at reducing churn`, `orientado a reducir las devoluciones`) is a purpose; `reservado para X` is the audience verb, no longer a CONFIDENTIALITY notice (`reservado` alone still is);
  more technical targets and experiments. Two slips found by the unit tests: the `-ar/-er/-ir` infinitive rule hit the English word `summer`, and the Portuguese contraction `destinado às` (a + as) was missing. Re-scored on the same data:
  open-audience **96.7 %**, decoy alarms **3.3 %** (v4 baseline 5.6 %), 0 of 1 280 older equivalent pairs; spent v3 set: recipient decoy 1/150, faithful-light by USE_LIMIT alone 2.0 %.
**Caveat that matters:** this is a closed-list arms race (events/periods/targets are about as open as audiences) tuned on 180 records; the number to believe is the frozen one (W2 failed). A final validation needs a new set.

## E-USE-LIMIT v8 (2026-10-29): VALIDATION of the strong-audience-verb mode on a NEW set — preregistered, code frozen by hash BEFORE the data (data/use_limits_v8/PREREG.md, FREEZE.json), run once; **W2 FAILED again**
180 fresh records, three authors (Opus, Sonnet, Haiku), 90 open audiences from domains unlike the office ones (health, agriculture, education, public sector, NGOs, sport, culture, transport) and 90 decoys chosen widely
(ceremonies, festivals, harvests, elections, anniversaries, funerals, strikes, compound noun phrases, purposes that start with a verb, technical targets). Code = commit c6c4dc3 (reproduce with `git checkout c6c4dc3`); result: RESULT.txt.
* **W1 PASS** — unusual audiences flagged **91.1 %** (en 100, es 92.6, **pt 83.3**; v4: 13.3 %). **W3, W4, W5 PASS** (faithful-light by USE_LIMIT alone 0 %, 0 of 1 280, spent v3 set 0.7 % / 2.0 %).
* **W2 FAIL** — decoys flagged by USE_LIMIT **36.7 %** (33/90), threshold 10 %; the v4 code scored 0.0 % on the same decoys. The 33 false alarms are occasions and events my lists did not contain (`ceremonia de graduación`, `cosecha de aguacate`,
  `harvest festival`, `anniversary gala`, `festa junina`, `greve dos caminhoneiros`, `funeral`, `marathon weekend`) plus technical targets (`customer orders schema`, `galpão`, `bodega central`).
* **The post-hoc v6/v7 numbers did not generalise:** on the set they were tuned on the decoy alarms were 3.3 %, on fresh data 36.7 % — a measured overfit of 33 points. Events, occasions and purposes are about as open as audiences, so
  no closed exclusion list works; that is the finding.
* **8 audiences still missed** (read after the run, NOT tuned), three different causes: verbs outside the list (`adaptada a`, `concebido para`, `focada em`, `feita para`); a technical word that is also a group
  (`servidores do cartório` = civil servants, read as `servidores` = servers); and the head-noun check reading `turno` inside `enfermeras de turno nocturno` as an event. All three are closed-list fragility.
**Decision (product, not statistics):** the strong-audience-verb mode is NOT part of the default. `USE_LIMIT` keeps the closed audience list (same behaviour as the frozen v3 numbers plus the `al` / `às` contractions and
`reservado para X`); the open mode is the opt-in family `USE_LIMIT_OPEN` (`RELAY_FAMILIES_OPEN`, `relay_check(source, relay, open_audience=True)`, `aixl.invariants.open_audience`) for callers who prefer sensitivity over alerts:
on fresh data it catches 91 % of unusual audiences and flags 37 % of decoys. `python -m benchmarks.use_limit_modes use_limits_v8` prints both modes side by side. Not wired into the MCP tool (default only).
**What a better answer needs:** not a longer list but a different signal — e.g. whether the complement is a group of PEOPLE (a noun class needing a vocabulary) or a judge that decides audience vs occasion on the flagged pairs only.

## E-USE-LIMIT v9 (2026-10-29): USE_LIMIT_PLURAL — a structural audience signal on a NEW set, preregistered, code and data frozen by hash, run once; **X1 and X2 FAILED, the structure is informative**
Signal: a strong audience verb whose complement has a PLURAL head (English last word of the noun phrase, Spanish/Portuguese first). 180 fresh records, three authors (Opus, Sonnet, Haiku), with the known weak spots included on purpose per author:
10 singular-group audiences (`la junta directiva`, `the film crew`) and 10 plural-event decoys (`las pruebas de carga`, `the nightly builds`). Result: data/use_limits_v9/RESULT.txt.
* **X1 FAIL** — audiences flagged by the plural family **57.8 %** (threshold 75 %): plural groups **85.0 %** (51/60), singular groups **3.3 %** (1/30, the predicted hole). By language es 66.7, **en 37.0**, pt 66.7.
* **X2 FAIL** — decoys flagged by the plural family **30.0 %** (27/90, threshold 10 %), but the split is the finding: ordinary decoys (events, purposes, deadlines, technical targets) **3.3 %** (2/60) versus **plural events 83.3 %** (25/30, the other predicted hole).
  For comparison the open mode (strong verb + any group, E-USE-LIMIT v8) flags 35.0 % of the ordinary decoys on this set and the default closed list 1.7 %.
* **X3 PASS** (faithful-light by the family alone 0 %), **X4 PASS** (0 of 1 280 older equivalent pairs), **X5 PASS** (spent v3 set: recipient decoy 0.7 %).
**What it says.** A morphological signal generalises where the event lists did not (ordinary decoys 3.3 % vs 35 % for the open mode), at the cost of two blind spots that are structural, not lexical: a PLURAL event reads as an audience, a SINGULAR group does not.
**English recall is low for a reason found after the run (NOT tuned):** the head-last rule is wrong when the noun phrase has a post-modifier (`the tenants of the Maple Street building` -> head read as `building`; `school groups visiting the museum` -> `museum`), and the
verb `directed at` is not in the list. Spanish and Portuguese put the head first, so they do not suffer from it.
**The two signals are complementary (post-hoc, on the set already read — NOT evidence):** the default closed list already catches 73.3 % of the singular groups (collective nouns are a small closed class: `junta`, `comité`, `equipo`, `board`, `crew`,
`conselho`, `diretoria`, `comissão`, `time`) and 5.0 % of plural groups; the plural family catches 85 % of plural groups. Union default + plural: audiences **83.3 %** (plural groups 88.3, singular 73.3), ordinary decoys **5.0 %**, plural events still **83.3 %**.
**Decision:** `USE_LIMIT_PLURAL` stays opt-in (`RELAY_FAMILIES_PLURAL`, `aixl.invariants.plural_audience`); no mode of the audience family meets the 10 % decoy bar because of plural events. A fix would need a different signal for those
(whether the head is an EVENT-like noun) — the same closed-class problem again — or a judge restricted to the pairs this family flags. Not implemented.
