"""Qwen2.5-7B-Instruct Q4_K_M as a third judge through a LOCAL llama-server (127.0.0.1 only): same prompt, temperature 0, seed 28 and grammar as PREREG.md,
model loaded once. Writes results incrementally so a killed run keeps its progress; resumes where it stopped.
usage: python3 run_qwen_server.py <batch.jsonl> <out.tsv> [--limit N] [--port 8089]"""
import json
import os
import sys
import urllib.request

RULES = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "aixl", "resources", "arbiter_rules_v1.txt"), encoding="utf-8").read().strip()
GRAMMAR = r'''root ::= id "\t" verdict "\t" reason
id ::= "Q" [0-9] [0-9] [0-9]
verdict ::= "SAME" | "DIFFERENT" | "UNSURE"
reason ::= [A-Za-z ,.'-]+'''
batch, out = sys.argv[1], sys.argv[2]
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8089
rows = [json.loads(line) for line in open(batch, encoding="utf-8") if line.strip()][:limit]
done = set()
if os.path.exists(out):
    done = {line.split("\t")[0] for line in open(out, encoding="utf-8") if line.strip()}
with open(out, "a", encoding="utf-8") as f:
    for r in rows:
        if r["id"] in done:
            continue
        user = json.dumps({"id": r["id"], "a": r["a"], "b": r["b"]}, ensure_ascii=False)
        prompt = f"<|im_start|>system\n{RULES}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"
        body = json.dumps({"prompt": prompt, "n_predict": 40, "temperature": 0, "seed": 28, "grammar": GRAMMAR, "cache_prompt": True}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=body, headers={"Content-Type": "application/json"})
        text = json.loads(urllib.request.urlopen(req, timeout=300).read())["content"].strip()
        parts = text.split("\t")
        v = parts[1].strip().upper() if len(parts) >= 2 else ""
        verdict = v if v in ("SAME", "DIFFERENT", "UNSURE") else "UNSURE"
        f.write(f"{r['id']}\t{verdict}\t{parts[2].strip() if len(parts) >= 3 else 'unparsed'}\n")
        f.flush()
        print(r["id"], verdict, flush=True)
print("done")
