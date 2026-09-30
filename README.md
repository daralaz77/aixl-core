# AIXL 0.3 — Semantic Core & Semantic Equivalence Engine (MVP)

## 1. What AIXL is
AIXL (AI Interoperability eXchange Language) is an **experimental semantic layer**: it represents what an instruction *means* (actions, targets, time, quantities, constraints, conditions, negations, references) in a canonical graph, serializes it in a compact `ATOM:VALUE` syntax, and compares two meanings. It is not a replacement for MCP, A2A, REST or JSON, and no claim of superiority over them is made or supported.

## 2. Problem it tries to address
When an intention moves between models, agents or services, its meaning can change (a negation lost, `100` becoming `1000`, `Q1` becoming `Q2`) without anyone noticing. AIXL 0.3 asks: *can we represent and compare meaning independently of how it was written?* (product hypothesis: organizations chaining several models need to verify that an intent kept its meaning across hops — **not tested with any real organization**).

## 3. What 0.3 is
A small, local, dependency-free Python core (no external AI API needed) with: SemanticObject/Relation/Graph, ontology, normalizer, ES/EN/PT rule-based translator, AIXL codec, comparator, semantic diff, drift, ambiguity and contradiction detectors, CLI, Semantic Lab (CLI + web), benchmarks and 99 tests. See `ARCHITECTURE.md`.

## 4. Architecture (short)
`text → translator → SemanticGraph (canonical) → { AIXL | JSON | comparator → equivalence / diff / drift }`. AIXL is a serialization, the graph is the core. Language, semantics, protocol, encoding, transport and execution are separate layers; nothing here executes an action.

## 5. Install
```bash
cd ~/.claude/skills/aixl-core            # Python ≥ 3.11, no runtime dependencies
python3 -m venv .venv && .venv/bin/pip install pytest tiktoken   # dev only
```

## 6. Examples
```python
import aixl
r = aixl.compare("Analiza las ventas de Q1 2026.", "Examina las ventas del primer trimestre de 2026.")
print(r.equivalent, r.similarity, r.diff)        # True 1.0 []
r = aixl.compare("Elimina el reporte.", "No elimines el reporte.")
print(r.equivalent, r.drift_level, r.critical_changes[0].field)   # False CRITICAL_DRIFT NEGATION
print(aixl.to_aixl("Analiza las ventas del primer trimestre de 2026"))
# V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026
print(aixl.detect_ambiguity("Analiza los datos recientes.").reason)   # VAGUE_TIME
print(aixl.detect_contradiction("Permite eliminar el reporte.", "Prohíbe eliminar el reporte.").alerts[0].type)  # ALLOW_VS_FORBID
```

## 7. CLI
```bash
python cli.py translate "Analiza las ventas de Q1 2026"
python cli.py compare "Analiza las ventas de Q1 2026" "Examina las ventas del primer trimestre de 2026"
python cli.py diff "Analiza las ventas de Q1 2026" "Analiza las ventas de Q2 2026"
python cli.py drift "Analiza las ventas de Q1 2026" "Analiza las ventas de Q2 2026"
python cli.py ambiguity "Analiza los datos recientes."      # also: contradiction, aixl, lab, demo, bench
python cli.py serve 8765                                     # Semantic Lab web app -> http://localhost:8765
```

## 8. Benchmark
See `BENCHMARK.md`. Method: pre-registered; independent blind authors; each fresh set evaluated once before tuning; contaminated numbers labelled.

## 9. Results (summary; details and caveats in BENCHMARK.md)
* Rule-based translator on FRESH blind sets: accuracy **72 → 80 → 76 → 76 %** (precision 88–95 %, recall 51–63 %). **S1 (≥ 90 %) not met by the rule-based route.**
* Same core fed by an LLM translator following the card (Haiku 4.5 / Sonnet 5), fresh set 4: **96.0 % / 96.5 %** accuracy, critical drift 96.8 %. S1 and S2 met on that set; single pass. Cross-vendor E-XV (set 5, pairs written by Gemini and ChatGPT; encoders Haiku, Sonnet, Gemini, ChatGPT): 96.5 / 96.5 / 95.0 / 93.5 %, rule-based 78.5 %; see BENCHMARK.md §7. Codec fixed after E-XV; confirmed on fresh set 6 (E-CODEC, BENCHMARK.md §8): 0/200 parse failures, Sonnet 94.0 % accuracy. Date/time/duration/reference gaps closed over 3 iteration rounds and confirmed on fresh set 9 (E-DATE, BENCHMARK.md §9): Sonnet 95.0 %, 0 parse failures, 39/39 critical drift; rule-based 88.0 %. Cross-vendor ENCODING consistency E-INTEROP (BENCHMARK.md §10): 53 % baseline -> **79 %** after 3 rounds of shared vocabulary + a tie-break rule. Live negotiation protocol E-NEGOTIATE (BENCHMARK.md §11): 21/21 real remaining disagreements converge via a bounded clarification exchange, verified with a real 2-model live demo, and wired into the CLI/API (`cli.py negotiate` / `negotiate-aixl`).
* Critical-drift detection (negation, quantity, time, constraint, condition, reference): 89.6–97.0 % rule-based, 96.8–100 % LLM route.
* Ambiguity (n = 20, first run) 90 %; contradiction (n = 20, first run) 75 %.
* AIXL is **longer** than the sentence (≈ +130 % characters, ≈ +246 % cl100k tokens); 64 % fewer tokens than canonical JSON.
* Tests: 99 passed. Dev 200-case set: 100 % — DEMO only.

## 10. Limitations
See `LIMITATIONS.md` (fixed vocabulary, flat frame, no clock for relative dates, single-annotator labels, weak conditions/negation scope, Anthropic-only encoders tested).

## 11. Roadmap → AIXL 0.4 (Semantic Interoperability Layer) — only if evidence supports it
1. **Cross-vendor encoder test** (GPT, Gemini, open-source) on a fresh blind set authored by a non-Anthropic model — the largest threat to the current result.
2. Per-action targets in the graph (fix the swap blind spot) and a reference clock for relative dates.
3. Adjudicated labels (≥ 2 annotators, κ) on a 300-pair set incl. hard real agent handoffs.
4. Measure the product hypothesis: log real agent-to-agent handoffs and count meaning changes (does the problem occur? how often?).
5. Only then: ProtocolAdapter implementations (MCP/A2A) and a semantic-firewall prototype (`explain()` is the groundwork).

## Audit (master prompt §41–42)
| Question | Answer, with evidence |
|---|---|
| Does it really represent meaning or only match words? | **Both, by layer.** The core compares structured, typed elements (action, target, period, quantity, negation...) on a canonical form, not strings. But the rule-based translator IS lexicon/pattern matching; where the lexicon does not cover a phrase it silently drops it (recall 51–63 % on fresh paraphrases). With an LLM translator the same core reached 96 %. |
| Synonyms vs real differences? | Minimal pairs (Q1/Q2, 100/1000, do/do-not, >= vs >) are separated (precision 88–100 %); synonyms converge only inside the covered vocabulary. |
| Negation, quantity, date, condition, restriction preserved? | Through serialization: 100 %. Captured from text: rule-based ~60–95 % per category on fresh sets (negation weakest, 60 %), LLM route higher. Conditions beyond count/existence/containment/confidence are weak literals. |
| Ambiguity detected? | 90 % on 20 blind items (heuristic; first run). |
| Differences explainable? | Yes: field, source, target, kind, severity, drift level, human diff. |
| Reproducible? | Rule-based route fully deterministic; blind data and first-run results are frozen (read-only) with checksums. The LLM route depends on stored model outputs. |
| Works without an external API? | Yes (rule-based route); accuracy on unseen phrasing is the price. |
| DEMO vs EVIDENCE vs REAL VALIDATION | DEMO: 6 demos, dev-200, tests. EVIDENCE: blind first runs (sets 1–4), E-LLM on set 4, cross-vendor E-XV on set 5, codec-fix confirmation E-CODEC on set 6, date/time/duration/reference fixes E-DATE on set 9, and cross-vendor ENCODING-consistency E-INTEROP (53%→79%), and the E-NEGOTIATE live negotiation protocol (21/21 real disagreements resolved, one real 2-model live demo). REAL VALIDATION: none. |
