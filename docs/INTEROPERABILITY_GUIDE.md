# Interoperability guide

Golden rule (§57): system A understands AIXL, system B understands AIXL — `A ↔ AIXL ↔ B`, never `A ↔ B`. The core is provider-agnostic: it needs no AI API and imports no vendor SDK.

## Deciding whether two agents mean the same (read this first, 2026-10-03)
Transporting an AIXL line is solved (below). **Deciding that two open-text instructions mean the same is not something an AIXL line can prove**: on other authors' text the line drops whatever has no slot, so different instructions can encode identically ([EVIDENCE.md](EVIDENCE.md)). The measured recommendation:
1. Keep the instructions' original texts. Hash them or the canonical key for exact duplicates (`semantic_fingerprint`, free).
2. For candidate pairs, ask a strict full-text arbiter, 2-of-2 (two independent LLMs, "same" only if both say SAME); ≈ $0.28 per 1 000 pairs, 359/360 true paraphrases recovered with 0/480 false "same" on near-misses (blind12).
3. Store each verdict (pair hash + models + prompt id) and reuse it; do not re-derive (the 2-of-2 flips on 1.2 % of pairs between runs).
4. Use a cheap lexical filter, not AIXL's key, to cut candidate pairs (recall 60 % vs 15.8 % at 1.3 % vs 0.28 % of all pairs).
5. Keep AIXL for what it measured well: controlled-vocabulary exact comparison, input hygiene, and as the interchange/negotiation format between MCP/A2A agents.

## Adapters (`aixl/adapters/protocol_adapter.py`) — outside the core
| Adapter | Status |
|---|---|
| `AixlAdapter`, `JsonAdapter` | real (graph ⇄ AIXL line / JSON) |
| `MCPAdapter` + `aixl/mcp_server.py` | **real**, official `mcp` SDK, stdio; validated against the SDK's own models, real subprocess + client round-trip, and 3 vendors' real clients (Claude Desktop, ChatGPT/Codex, Antigravity CLI) |
| `A2AAdapter` + `aixl/agents/a2a_server.py` | **real**, official `a2a-sdk`, JSON-RPC over HTTP, real subprocess + client round-trip |
| `RESTAdapter`, `OpenAPIAdapter`, `GraphQLAdapter` | **not implemented** (raise `NotImplementedError`); §48's OpenAI/Gemini-style agent and workflow-engine adapters do not exist either |

Install the optional pieces with `pip install .[mcp]` and/or `.[a2a]`. Run: `python -m aixl.mcp_server` · `python -m aixl.agents.a2a_server 8766`. Tools and skills: [API_REFERENCE.md](API_REFERENCE.md).

## Two agents, one meaning (the central demo)
1. Agent A encodes its instruction: `aixl.to_aixl("Elimina el reporte #4.")` and sends the line over any transport.
2. Agent B decodes (`aixl.from_aixl(line)`) or encodes its *own* reading of the same task, then `aixl.compare_aixl(line_a, line_b)`.
3. `equivalent` → same *captured* meaning (controlled vocabulary: operational meaning; open text: see the section above); otherwise the typed `differences` (with severity) say exactly what moved, and `warnings` say what could not be verified.
Use `semantic_fingerprint()` when you only need a stable key for "same meaning".

## When two agents disagree: negotiation (implemented)
`negotiate(sender_text, receiver_text)` (or `negotiate_aixl` on two lines) runs a bounded, severity-ordered exchange `REQUEST → CLARIFY → ANSWER → ACCEPT | REJECT`
(≤ 3 rounds by default). The sender is authoritative; the receiver adopts the sender's value one disputed dimension at a time. Measured on 21 real cross-vendor disagreements: 19/21 converge,
the other 2 end in an honest REJECT, not a guess. **Irreversible actions (`DELETE`, `SEND`) are never auto-resolved**: REJECT, or over A2A the Task pauses (`INPUT_REQUIRED`) for a human.
`aixl_negotiate_autonomous` does the exchange between two real OS processes over MCP stdio with no human relay.

## Capability handshake and feature negotiation (§53–§54): design only
There is no `AIXL-CAPABILITIES` message. What exists instead: the A2A *agent card* advertises skills; the parser accepts `V:AIXL-0.2` and `V:AIXL-0.3` and **rejects every other version**
(`VERSION_MISMATCH`) rather than guessing. A 0.2 reader receiving a 0.3-only construct (`K:QTY=`, `K:FORBID_`, `K:SCOPE=` …) gets no automatic `UNSUPPORTED_CAPABILITY` — check versions out of band
until a handshake is built. A proposal belongs in a MINOR release ([VERSIONING_POLICY.md](VERSIONING_POLICY.md)).

## Practical cautions
* Different encoders (rule-based vs LLM) disagree on ≈ 21 % of the same texts' encodings (cross-vendor consistency 79 % after shared vocabulary); that is why `negotiate` exists.
* Always pass the same `today=` on both sides when relative times appear, or compare before encoding to AIXL.
* Treat `warnings` as part of the answer. A verdict with `NO_ACTION_RECOGNIZED` or `UNRECOGNIZED_TERMS` is weaker than it looks.
