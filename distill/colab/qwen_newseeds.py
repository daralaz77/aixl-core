"""Colab: asks an open model (Qwen2.5-14B-Instruct, free) to INVENT new, natural instructions -- not paraphrases of existing seeds --
covering the vocabulary the translator must handle (actions, negations, conditions, quantities, dates, formats, recipients,
priorities, ids, irreversible actions) across ES/EN/PT and several registers. Labels come LATER from a consensus of independent
labelers (distill/consensus_label.py); nothing here is labelled.

usage (Colab): python qwen_newseeds.py <hf_model_id> <n_calls> <rng_seed> > newseeds.txt     (one `SEED<TAB>json` line per instruction)
"""
import json
import random
import sys
import time

LANGS = {"es": "Spanish", "en": "English", "pt": "Brazilian Portuguese"}
DOMAINS = ["sales data", "customer records", "support tickets", "HR records", "invoices", "inventory", "marketing campaigns",
           "server logs", "security alerts", "IoT sensor readings", "shipping orders", "finance reports", "social media posts",
           "user accounts", "backups", "code repositories", "meeting notes", "surveys", "calendar events", "audio recordings",
           "video files", "images", "machine-learning models", "dashboards", "email messages", "contracts", "product catalog",
           "payments", "website analytics", "database tables"]
TASKS = ["analyze", "compare", "find or search", "summarize", "generate or create", "calculate", "check or validate", "translate",
         "retrieve or fetch", "delete", "run or execute", "convert or transform", "classify", "extract", "predict or forecast",
         "enable or disable", "archive", "send or notify or share", "include or exclude", "update or close or mark"]
FEATURES = ["a negation (never / do not)", "a condition (if / when / unless something is true)", "a numeric limit (at most N, first N)",
            "a date or time reference (yesterday, last quarter, a specific date, before Friday)", "an output format (JSON, PDF, CSV, table, Markdown)",
            "a named recipient (a person or a team)", "a priority (urgent, high, low)", "a reference id (ticket #123, order #45)",
            "a permission or prohibition (only admins may..., it is forbidden to...)", "an ordering of two steps (first X, then Y)",
            "a confidence or quality threshold", "a language requirement for the result"]
STYLES = ["short imperative", "polite request", "formal business tone", "terse command", "imperative with a concrete detail"]
SYSTEM = ("You write realistic instructions that a person would give to an AI assistant embedded in a company's data/software platform. "
          "Each instruction is ONE sentence (max 30 words), self-contained, concrete, and clearly means one thing. Make the instructions "
          "in a batch clearly different from each other (different verbs, objects, wording). Never explain. Output only a JSON list of strings.")
EXAMPLES = ["Archive the Q3 invoices older than 90 days.", "Envía el resumen semanal al equipo de soporte antes de las 5pm.",
            "Não exclua os registros do cliente #482."]


def make_prompt(rng):
    lang = rng.choice(list(LANGS))
    feats = rng.sample(FEATURES, rng.choice([1, 2, 2, 3]))
    return lang, (f"Write 5 different instructions in {LANGS[lang]} about {rng.choice(DOMAINS)} or {rng.choice(DOMAINS)}. "
                  f"Task types to cover across the batch: {', '.join(rng.sample(TASKS, 3))}. Each instruction should include "
                  f"{' and '.join(feats[:1])}{' (and, in some of them, ' + ' / '.join(feats[1:]) + ')' if len(feats) > 1 else ''}. "
                  f"Style: {rng.choice(STYLES)}. Style examples (different topics, do not copy): {json.dumps(EXAMPLES, ensure_ascii=False)}. "
                  f"Return a JSON list of exactly 5 strings.")


def main():
    model_id, n_calls, rng_seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(rng_seed)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="cuda")
    specs = [make_prompt(rng) for _ in range(n_calls)]
    prompts = [tok.apply_chat_template([{"role": "system", "content": SYSTEM}, {"role": "user", "content": p}],
                                       add_generation_prompt=True, tokenize=False) for _, p in specs]
    t0, kept = time.time(), 0
    for s in range(0, len(prompts), 24):
        enc = tok(prompts[s:s + 24], return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=330, do_sample=True, temperature=0.9, top_p=0.95, pad_token_id=tok.pad_token_id)
        for j, x in enumerate(g):
            raw = tok.decode(x[enc["input_ids"].shape[1]:], skip_special_tokens=True)
            try:
                items = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
            except Exception:  # noqa: BLE001
                continue
            for t in items:
                if isinstance(t, str) and 8 <= len(t) <= 220:
                    kept += 1
                    print("SEED\t%s\t%s" % (specs[s + j][0], json.dumps(t.strip(), ensure_ascii=False)), flush=True)
        print(f"# {min(s + 24, len(prompts))}/{len(prompts)} calls, {kept} instructions, {time.time()-t0:.0f}s", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
