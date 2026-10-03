# Parser (text -> SemanticGraph)
Entry point: `aixl.translators.natural_to_semantic.to_graph(text, today=None)`; the public API uses `aixl/translators/auto.py`, which selects a route via `AIXL_TRANSLATOR_MODE`:

| Mode | Route | Evidence |
|---|---|---|
| `rule_based` (default) | lexicons + regex, no dependencies | ~76-88% on the project's earlier blind sets (same vocabulary family); **24.7–40.0 % on other authors' open text (blind10)** and 40.6 % of non-equivalent pairs judged equivalent (blind11); 99.4% on the 5x100 benchmark (generated, same author) |
| `llm` / `auto` | LLM proposes AIXL, the unmodified codec parses it, Core validates; falls back to rules on any failure | 93.5-96.5% cross-vendor **on sets drawn from the card's own vocabulary**; on other authors' open text 37.0 % (blind10) and 0 % of true paraphrases proven with 0.6 % false when `inconclusive` is on (blind11) — it drops what the card has no slot for |
| `local` | fine-tuned local model via Ollama | F1 0.69, offline only |

The LLM is an interpretation component; the Core (canonicalisation + comparison) is the semantic authority (§42). Input is first passed through `sanitize_input` (invisible characters, compatibility forms, mixed-script homoglyphs) and any finding becomes a warning.
Languages: ES, EN, PT. Not covered: coreference beyond nearest-noun counting, per-action argument binding (LIMITATIONS #3), deep world knowledge.
