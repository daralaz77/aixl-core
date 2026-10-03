"""Colab side of the free-teacher feasibility probe: generates 3 paraphrase variants per seed with an open model using the SAME
system prompt as distill/gen_paraphrase_groups.py (Haiku). Prints one line per seed: GEN<TAB>index<TAB>json-string(raw output).
Scoring happens locally (distill/qwen_probe_eval.py) with the project's own code, identically for Haiku and the open model.
usage (Colab): python qwen_gen.py <hf_model_id> <seeds.json>
"""
import json
import sys
import time

GEN_SYSTEM = (
    "You rewrite short software/data instructions. Given one instruction (Spanish, English or Portuguese), produce "
    "exactly 3 variants that keep the EXACT same meaning, as a JSON object and nothing else: "
    '{"seed_lang":"es|en|pt","variants":[{"lang":"..","text":".."},{"lang":"..","text":".."},{"lang":"..","text":".."}]}. '
    "Variant 1 and 2: faithful translations into each of the OTHER two languages. Variant 3: a natural rewording in the "
    "SAME language as the seed (different wording/word order, same meaning). Hard rules: keep every number, quantity, "
    "date/time expression, #reference id, proper name and file/format name unchanged; keep every negation, condition "
    "(if/when/unless), priority and recipient; do not add, drop or soften anything; keep the imperative register; "
    "one sentence each; no explanations.")


def main():
    model_id, seeds = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = "left"
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="cuda")
    print(f"loaded {model_id} in {time.time()-t0:.0f}s", flush=True)
    prompts = [tok.apply_chat_template([{"role": "system", "content": GEN_SYSTEM}, {"role": "user", "content": s}],
                                       add_generation_prompt=True, tokenize=False) for s in seeds]
    t0 = time.time()
    for s in range(0, len(prompts), 16):
        enc = tok(prompts[s:s + 16], return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=400, do_sample=True, temperature=0.3, top_p=0.95, pad_token_id=tok.pad_token_id)
        for j, x in enumerate(g):
            print("GEN\t%d\t%s" % (s + j, json.dumps(tok.decode(x[enc["input_ids"].shape[1]:], skip_special_tokens=True), ensure_ascii=False)), flush=True)
    print(f"DONE {len(prompts)} seeds in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
