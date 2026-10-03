"""Labels texts with the distilled student (a GGUF served by llama-server, optional GBNF grammar) -- one of the three independent
labelers of distill/consensus_label.py. usage: python distill/label_with_gguf.py <model.gguf> <texts.json> <out.jsonl> [--grammar distill/aixl.gbnf]
Resumable: lines already in out.jsonl are skipped."""
import json
import os
import subprocess
import sys
import time
import urllib.request

PORT = 8091
PROMPT = ("<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
          "<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n")


def main():
    gguf, texts_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    grammar = open(sys.argv[sys.argv.index("--grammar") + 1], encoding="utf-8").read() if "--grammar" in sys.argv else None
    texts = json.load(open(texts_path, encoding="utf-8"))
    done = set()
    if os.path.exists(out_path):
        done = {json.loads(l)["i"] for l in open(out_path, encoding="utf-8") if l.strip()}
    srv = subprocess.Popen(["llama-server", "-m", gguf, "--port", str(PORT), "-ngl", "99", "-c", "2048", "--parallel", "1"],
                           stdout=subprocess.DEVNULL, stderr=open("/tmp/llama_label.log", "w"))
    try:
        for _ in range(180):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        t0 = time.time()
        with open(out_path, "a", encoding="utf-8") as out:
            for i, t in enumerate(texts):
                if i in done:
                    continue
                payload = {"prompt": PROMPT.format(text=t), "n_predict": 110, "temperature": 0, "stop": ["<|im_end|>"], "cache_prompt": True}
                if grammar:
                    payload["grammar"] = grammar
                req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    raw = json.loads(r.read()).get("content", "")
                out.write(json.dumps({"i": i, "raw": raw}, ensure_ascii=False) + "\n")
                out.flush()
                if (i + 1) % 100 == 0:
                    print(f"[{i+1}/{len(texts)}] {time.time()-t0:.0f}s", flush=True)
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
