"""Colab: labels texts with an open model (Qwen2.5-14B-Instruct) using the frozen card as the system prompt, exactly like the
project's live LLM route (aixl/translators/llm_translator.py) but locally and free. One of three INDEPENDENT labelers used by
distill/consensus_label.py (the others: the rule-based translator and the distilled student).
usage (Colab): python qwen_label.py <hf_model_id> <card.md> <texts.json> > labels.txt     (lines: LAB<TAB>index<TAB>json(raw output))
"""
import json
import os
import sys
import time


def main():
    model_id, card_path, texts_path = sys.argv[1], sys.argv[2], sys.argv[3]
    card = open(card_path, encoding="utf-8").read()
    texts = json.load(open(texts_path, encoding="utf-8"))
    system = card + ("\n\nRespond with EXACTLY one line: the AIXL encoding of the text below, "
                     "and nothing else — no explanation, no code fence, no leading/trailing text.")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16, device_map="cuda")
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    t0, bs = time.time(), int(os.environ.get("BS", "5"))
    for s in range(0, len(order), bs):
        idx = order[s:s + bs]
        prompts = [tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": texts[i]}],
                                           add_generation_prompt=True, tokenize=False) for i in idx]
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=110, do_sample=False, pad_token_id=tok.pad_token_id)
        for j, i in enumerate(idx):
            raw = tok.decode(g[j][enc["input_ids"].shape[1]:], skip_special_tokens=True)
            print("LAB\t%d\t%s" % (i, json.dumps(raw, ensure_ascii=False)), flush=True)
        print(f"# {min(s + bs, len(order))}/{len(order)} {time.time()-t0:.0f}s", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
