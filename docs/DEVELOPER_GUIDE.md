# Developer guide

## Before you build on it (2026-10-03)
AIXL's rule/LLM routes are exact only inside a controlled vocabulary and are not safe on open text; the measured way to decide "same meaning" for open text is a full-text arbiter ([EVIDENCE.md](EVIDENCE.md)). Do not present `compare().equivalent` as proof of equal intent unless the texts are in the vocabulary, and consider `config["inconclusive"] = True`.

## Setup
```bash
cd ~/.claude/skills/aixl-core            # Python ≥ 3.11; the core has zero runtime dependencies
python3 -m venv .venv && .venv/bin/pip install pytest tiktoken
.venv/bin/pip install mcp "a2a-sdk[http-server]" uvicorn   # optional: MCP / A2A tests and servers
.venv/bin/python -m pytest -q                              # 479 tests; A2A tests skip cleanly without the SDK
```
Always run through the venv (`python3 -m unittest` finds nothing and a bare `python3` lacks pytest). CI (`.github/workflows/tests.yml`) runs Python 3.11 and 3.12.

## Layout
`aixl/core` semantics (graph, canonical form, comparator, drift, ambiguity, contradiction, fingerprint, lexicon_gaps, normalizer) ·
`aixl/translators` text→graph · `aixl/serialization` AIXL/JSON codecs · `aixl/api/service.py` public API · `aixl/adapters` + `aixl/agents` + `aixl/mcp_server.py` transport ·
`aixl/legacy02` vendored, measured AIXL 0.2 analyzer/parser/encoder · `data/config.json` weights/severities · `benchmarks/` and `data/` evidence · `tests/`.
Rule for any new feature (§59): is it semantic, syntactic, transport, adaptation, or domain-specific? Provider-specific ⇒ never in `core`; domain-specific ⇒ extension.

## Typical tasks
* **Compare two instructions:** `aixl.compare(a, b)`; to reproduce results across days pass `today=` to the functions that accept it.
* **Add vocabulary:** [EXTENSION_GUIDE.md](EXTENSION_GUIDE.md).
* **Fix a translator bug:** write the failing case in `tests/test_regression.py` (`test_bugNNN`) first, fix, run the whole suite **and** the blind/benchmark ratchets.
* **Change a severity or weight:** edit `data/config.json` (not code); document it in ARCHITECTURE.md if it is an assumption.

## Quality gates (a change is not done until all pass)
1. `pytest -q` green. 2. Ratchets: `tests/test_sil5x100.py`, `tests/test_sil_security.py` (floors = measured values; raise on improvement, never lower silently).
3. Blind sets 1–4 numbers unchanged unless you intend a change: `python -m benchmarks.blind_eval --round N`. 4. Docs: `tests/test_docs.py` checks every `aixl-example` line and every CLI command named in these docs.

## Benchmark hygiene (what keeps the numbers honest)
Fresh blind sets are evaluated **once** before any tuning; after you read a set's failures it is contaminated and must be labelled so. blind10, blind11 and blind12 are spent: any new claim needs a new set written by someone who has not seen the repository, with the gates fixed in an ADR first. The dev-200 set and the generated
5×100 / security sets are written by the code's author — regression instruments, not evidence of generalisation. Details: [BENCHMARK_SPEC.md](BENCHMARK_SPEC.md).
