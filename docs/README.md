# AIXL documentation (master prompt §50) — state 2026-10-03

AIXL is an **experimental** semantic layer: it turns an instruction (ES/EN/PT) into a canonical meaning graph, serializes it as a
compact `ATOM:VALUE` line, and compares two meanings (equivalence, diff, drift, ambiguity, contradiction). It is a research
MVP, **not a standard**, and nothing in it executes an action. Status of every claim is in [BENCHMARK_SPEC.md](BENCHMARK_SPEC.md)
and [../LIMITATIONS.md](../LIMITATIONS.md).

> **Read [EVIDENCE.md](EVIDENCE.md) first.** It is the single source of truth for what has been measured (on other authors' text), what to use for what, and what is not shown. Older accuracy figures (99.4 %, 95 %+) come from sets that share the translator's vocabulary or its author; they are kept as history in [HISTORY.md](HISTORY.md).

## Read this first, by audience
| You are | Start with | Then |
|---|---|---|
| Non-technical / evaluating | [EVIDENCE.md](EVIDENCE.md), then this page, "What it does today" | [SECURITY_MODEL.md](SECURITY_MODEL.md) §"What it does not do" |
| Developer using the library | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | [API_REFERENCE.md](API_REFERENCE.md), [CLI_REFERENCE.md](CLI_REFERENCE.md) |
| Agent builder (MCP / A2A) | [INTEROPERABILITY_GUIDE.md](INTEROPERABILITY_GUIDE.md) | [API_REFERENCE.md](API_REFERENCE.md) §MCP/A2A |
| Protocol implementer / researcher | [PROTOCOL.md](PROTOCOL.md), [SEMANTIC_MODEL.md](SEMANTIC_MODEL.md) | [BENCHMARK_SPEC.md](BENCHMARK_SPEC.md) |
| Security reviewer / enterprise architect | [SECURITY_MODEL.md](SECURITY_MODEL.md) | [VERSIONING_POLICY.md](VERSIONING_POLICY.md) |
| Extending the vocabulary | [EXTENSION_GUIDE.md](EXTENSION_GUIDE.md) | [VERSIONING_POLICY.md](VERSIONING_POLICY.md) |

## What it does today (measured; 2026-10-03 supersedes the 2026-10-02 figures below where they disagree)
* **Open-domain text from other authors:** the rule-based and LLM-encoded AIXL routes wrongly call 40–59 % of non-equivalent pairs equivalent; the repaired, safe version (opt-in `inconclusive`) proves only 0–32 % of true paraphrases; a strict full-text arbiter (two independent LLMs, "same" only if both agree) recovers 99.7–100 % with 0 false "same" on 480 hard near-misses. See [EVIDENCE.md](EVIDENCE.md).
* **What remains uniquely AIXL (measured or engineering-verified):** exact, free, offline comparison in a controlled vocabulary; deterministic input hygiene; MCP/A2A servers confirmed with three vendors' clients; a bounded negotiation protocol.

### Figures from 2026-10-02 (same-author benchmark; kept for context)
* Meaning-level comparison of two instructions, across ES/EN/PT: 5-class benchmark (EQUIVALENT / NOT_EQUIVALENT /
  PARTIALLY_EQUIVALENT / AMBIGUOUS / CONTRADICTORY ×100) **497/500 = 99.4 %** — but that benchmark is written by the same
  author as the code; on fresh blind sets the rule-based translator generalises at **≈ 76–88 %** (BENCHMARK_SPEC.md).
* Adversarial suite (§39): every attack in 450 combinatorial cases and 57 hand-written hard cases is flagged; 54/57 hard cases are
  flagged *critical* (3 declared limitations); 0/31 false alarms on benign restatements.
* Real MCP server and real A2A agent (official SDKs), a bounded negotiation protocol, a stable semantic fingerprint.

## What it does NOT do (deliberately)
No execution, no enforcement/firewall, no REST service (the §32 `POST /encode …` API is **not** implemented — see API_REFERENCE.md),
no capability handshake or extension registry (§52–§54 are design-only), no context-poisoning defence, and it is not validated
with any real organisation.

## Where the master prompt and the code differ (conformance matrix)
See [PROTOCOL.md §Conformance](PROTOCOL.md#conformance-with-the-master-prompt). Short version: the atom letters, the intent names,
and the relative-time handling differ from the prompt's examples, and are documented rather than hidden.

## Decisions and changes
[adr/README.md](adr/README.md) lists the architecture decision records (§82); [SEMANTIC_CHANGELOG.md](SEMANTIC_CHANGELOG.md) lists semantic changes with compatibility and migration (§83).
