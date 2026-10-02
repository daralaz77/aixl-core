"""Honest held-out measurement of an MLX (LoRA-adapted) AIXL translator on blind5 -- same texts, same codec, same
comparator and same F1 as every other route in this project (benchmarks/llm_translator_eval.py). No Colab, no GGUF.

usage: python distill/mlx_eval.py <model> <adapter_dir|-> <tag> [--limit N]
Writes distill/answers_mlx_<tag>.txt and prints the F1 summary + per-category error breakdown.
"""
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mlx_lm import generate, load  # noqa: E402

from benchmarks.llm_translator_eval import run  # noqa: E402


def first_aixl(text):
    for line in text.strip().splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def main():
    model_id, adapter, tag = sys.argv[1], sys.argv[2], sys.argv[3]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    model, tok = load(model_id, adapter_path=None if adapter == "-" else adapter)

    texts = json.load(open(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), encoding="utf-8"))
    if limit:
        texts = texts[:limit]
    out_path = os.path.join(ROOT, "distill", f"answers_mlx_{tag}.txt")
    t0, ok = time.time(), 0
    with open(out_path, "w", encoding="utf-8") as out:
        for i, t in enumerate(texts):
            prompt = tok.apply_chat_template([{"role": "user", "content": t["text"]}], add_generation_prompt=True, tokenize=False)
            raw = generate(model, tok, prompt=prompt, max_tokens=120, verbose=False)
            line = first_aixl(raw)
            ok += line is not None
            out.write(f"{t['tid']} :: {line or 'PARSE_FAILURE'}\n")
            out.flush()
            if (i + 1) % 25 == 0:
                print(f"[{i+1}/{len(texts)}] {time.time()-t0:.0f}s parsed={ok}", flush=True)
    print(f"\n{time.time()-t0:.0f}s, emitted AIXL line for {ok}/{len(texts)}")
    if limit:
        print("(--limit set: skipping F1 since blind5 pairs are incomplete)")
        return
    summ, rows = run([out_path], fallback=False, set_no=5)
    print(tag, json.dumps(summ, ensure_ascii=False))
    wrong = [r for r in rows if (r["label"] == "EQUIVALENT") != r["pred"]]
    from collections import Counter
    print("errors by (label, category):", Counter((r["label"], r.get("category")) for r in wrong).most_common(12))


if __name__ == "__main__":
    main()
