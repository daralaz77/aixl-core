"""Honest local measurement of a GGUF translator on blind5: serves the exact artifact with llama.cpp's llama-server
(Metal), sends the SAME ChatML prompt the model was trained on (Qwen default system, user text only), and scores with
the project's real codec/comparator -- the number that matters for the self-hosted route.

usage: python distill/gguf_eval.py <model.gguf> <tag>
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from benchmarks.llm_translator_eval import run  # noqa: E402

PORT = 8089
PROMPT = ("<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
          "<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n")


def post(path, payload, timeout=120):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def first_aixl(text):
    for line in text.strip().splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def main():
    gguf, tag = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    srv = subprocess.Popen(["llama-server", "-m", gguf, "--port", str(PORT), "-ngl", "99", "-c", "2048", "--parallel", "1"],
                           stdout=subprocess.DEVNULL, stderr=open(f"/tmp/llama_server_{tag}.log", "w"))
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        texts = json.load(open(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), encoding="utf-8"))
        if limit:
            texts = texts[:limit]
        out_path = os.path.join(ROOT, "distill", f"answers_gguf_{tag}.txt")
        t0, ok = time.time(), 0
        with open(out_path, "w", encoding="utf-8") as out:
            for i, t in enumerate(texts):
                r = post("/completion", {"prompt": PROMPT.format(text=t["text"]), "n_predict": 110, "temperature": 0,
                                         "stop": ["<|im_end|>"], "cache_prompt": True})
                line = first_aixl(r.get("content", ""))
                ok += line is not None
                out.write(f"{t['tid']} :: {line or 'PARSE_FAILURE'}\n")
                out.flush()
                if (i + 1) % 50 == 0:
                    print(f"[{i+1}/{len(texts)}] {time.time()-t0:.0f}s parsed={ok}", flush=True)
        print(f"{time.time()-t0:.0f}s, AIXL line for {ok}/{len(texts)}")
        if limit:
            return
        summ, rows = run([out_path], fallback=False, set_no=5)
        print(tag, json.dumps(summ, ensure_ascii=False))
        from collections import Counter
        wrong = [r for r in rows if (r["label"] == "EQUIVALENT") != r["pred"]]
        print("errors by (label, category):", Counter((r["label"], r.get("category")) for r in wrong).most_common(12))
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
