"""Measure a fine-tuned, locally-served (Ollama) AIXL translator against blind5 — the one blind set
deliberately kept out of distill/corpus.jsonl, so this is an honest held-out measurement, directly
comparable to the zero-shot qwen2.5:1.5b-instruct baseline measured on 2026-10-01 (F1 0.06) and to the
cloud LLM route (93.5-96.5%, measured the same way via benchmarks/llm_translator_eval.py).

Uses the SHORT system prompt the model was fine-tuned on (distill/train_colab.ipynb) — no card_0.3.md
at inference time; that's the whole point of distillation.

usage: python distill/eval_distilled.py <ollama-model-name> [--limit N]
Then: python -m benchmarks.llm_translator_eval <model-name> distill/answers_<model>.txt --set5
"""
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYSTEM_PROMPT = (
    "You are an AIXL 0.3 encoder. Given an instruction in Spanish, English or Portuguese, output "
    "its AIXL encoding as exactly one line starting with V:AIXL-0.3. Output only that line, nothing else."
)


def extract_aixl_line(text):
    for line in text.strip().splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def call_ollama(model, text, timeout=60, temperature=0.0):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read()).get("message", {}).get("content", "")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    model = sys.argv[1]
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    temperature = 0.0
    if "--temp" in sys.argv:
        temperature = float(sys.argv[sys.argv.index("--temp") + 1])

    with open(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), encoding="utf-8") as f:
        texts = json.load(f)
    if limit:
        texts = texts[:limit]

    out_path = os.path.join(ROOT, "distill", f"answers_{model.replace(':', '_')}.txt")
    t0 = time.time()
    ok = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for i, t in enumerate(texts):
            try:
                raw = call_ollama(model, t["text"], temperature=temperature)
                line = extract_aixl_line(raw)
            except Exception as e:                       # noqa: BLE001
                raw, line = f"ERROR: {e}", None
            ok += line is not None
            out.write(f"{t['tid']} :: {line or 'PARSE_FAILURE'}\n")
            print(f"[{i+1}/{len(texts)}] {t['tid']} parsed={line is not None}", flush=True)

    elapsed = time.time() - t0
    print(f"\n{elapsed:.1f}s for {len(texts)} texts, parsed {ok}/{len(texts)}")
    print(f"answers written to: {out_path}")
    print(f"next: python -m benchmarks.llm_translator_eval {model} {out_path} --set5")


if __name__ == "__main__":
    main()
