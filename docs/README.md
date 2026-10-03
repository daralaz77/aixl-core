# AIXL 0.3 documentation (master prompt §50)

AIXL is an **experimental** semantic layer: it turns an instruction (ES/EN/PT) into a canonical meaning graph, serializes it as a
compact `ATOM:VALUE` line, and compares two meanings (equivalence, diff, drift, ambiguity, contradiction). It is a research
MVP, **not a standard**, and nothing in it executes an action. Status of every claim is in [BENCHMARK_SPEC.md](BENCHMARK_SPEC.md)
and [../LIMITATIONS.md](../LIMITATIONS.md).

## Read this first, by audience
| You are | Start with | Then |
|---|---|---|
| Non-technical / evaluating | this page, "What it does today" | [SECURITY_MODEL.md](SECURITY_MODEL.md) §"What it does not do" |
| Developer using the library | [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | [API_REFERENCE.md](API_REFERENCE.md), [CLI_REFERENCE.md](CLI_REFERENCE.md) |
| Agent builder (MCP / A2A) | [INTEROPERABILITY_GUIDE.md](INTEROPERABILITY_GUIDE.md) | [API_REFERENCE.md](API_REFERENCE.md) §MCP/A2A |
| Protocol implementer / researcher | [PROTOCOL.md](PROTOCOL.md), [SEMANTIC_MODEL.md](SEMANTIC_MODEL.md) | [BENCHMARK_SPEC.md](BENCHMARK_SPEC.md) |
| Security reviewer / enterprise architect | [SECURITY_MODEL.md](SECURITY_MODEL.md) | [VERSIONING_POLICY.md](VERSIONING_POLICY.md) |
| Extending the vocabulary | [EXTENSION_GUIDE.md](EXTENSION_GUIDE.md) | [VERSIONING_POLICY.md](VERSIONING_POLICY.md) |

## What it does today (measured, 2026-10-02)
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
