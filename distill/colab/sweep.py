"""Packaging-loss sweep: how much F1 do we lose between the trained adapter and a quantized GGUF, and which
merge precision (bf16 vs fp32) x quantization (Q4_K_M / Q6_K / Q8_0 / f16) loses the least?

Everything is measured on the A100 with llama.cpp's OWN server (CUDA build), the exact ChatML prompt used for
training, blind5 F1 from the project's comparator, plus the held-out DEV paraphrase groups -- so only the winner needs
the (slow) browser download to the Mac.

usage (Colab):  !python sweep.py --tag para3b
Stages: A train (pipeline.py, if no adapter yet) -> B fp32 re-merge -> C build llama.cpp (CUDA) -> D convert -> E sweep
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

LLAMA = "/content/llama.cpp"
PORT = 8090
PROMPT = ("<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
          "<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n")


def log(*a):
    print(*a, flush=True)


def sh(cmd):
    log("$", cmd[:200])
    subprocess.run(cmd, shell=True, check=True)


def first_line(raw):
    for line in raw.splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def post(path, payload, timeout=120):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


GRAMMAR = None


def serve_and_eval(gguf, label, blind5, dev_rows):
    from aixl.core.comparator import compare_graphs
    from aixl.serialization import aixl_codec
    from benchmarks.llm_translator_eval import run as run_f1

    srv = subprocess.Popen([f"{LLAMA}/build/bin/llama-server", "-m", gguf, "--port", str(PORT), "-ngl", "99", "-c", "4096",
                            "--parallel", "8"], stdout=subprocess.DEVNULL, stderr=open(f"/content/server_{label}.log", "w"))
    try:
        for _ in range(240):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)

        def gen(text):
            payload = {"prompt": PROMPT.format(text=text), "n_predict": 110, "temperature": 0,
                       "stop": ["<|im_end|>"], "cache_prompt": True}
            if GRAMMAR:
                payload["grammar"] = GRAMMAR
            r = post("/completion", payload)
            return first_line(r.get("content", ""))

        t0 = time.time()
        with cf.ThreadPoolExecutor(8) as ex:
            b5 = list(ex.map(gen, [t["text"] for t in blind5]))
            dv = list(ex.map(gen, [r["text"] for r in dev_rows]))
        path = f"/content/answers_{label}.txt"
        with open(path, "w", encoding="utf-8") as f:
            for t, l in zip(blind5, b5):
                f.write(f"{t['tid']} :: {l or 'PARSE_FAILURE'}\n")
        summ, rows = run_f1([path], fallback=False, set_no=5)
        ok = 0
        for r, l in zip(dev_rows, dv):
            try:
                ok += bool(compare_graphs(aixl_codec.decode(l), aixl_codec.decode(r["aixl"])).equivalent)
            except Exception:  # noqa: BLE001
                pass
        with open(f"/content/dev_answers_{label}.jsonl", "w", encoding="utf-8") as f:
            for r, l in zip(dev_rows, dv):
                f.write(json.dumps({"text": r["text"], "target": r["aixl"], "group": r["group"], "out": l}, ensure_ascii=False) + "\n")
        eq = summ["equivalence"]
        out = {"label": label, "f1": eq["f1"], "precision": eq["precision"], "recall": eq["recall"], "accuracy": eq["accuracy"],
               "parse_fail": summ["parse_failures"], "dev": round(ok / len(dev_rows), 4), "gb": round(os.path.getsize(gguf) / 1e9, 2),
               "secs": round(time.time() - t0)}
        log("RESULT", json.dumps(out))
        return out
    finally:
        srv.terminate()
        time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="para3b")
    ap.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--epochs", default="3")
    ap.add_argument("--quants", default="Q4_K_M,Q6_K,Q8_0,f16")
    ap.add_argument("--grammar", default=None, help="path to a GBNF file; evaluates every GGUF with grammar-constrained decoding")
    args = ap.parse_args()
    global GRAMMAR
    if args.grammar:
        GRAMMAR = open(args.grammar, encoding="utf-8").read()
    out = os.path.join(ROOT, f"out_{args.tag}")
    adapter = os.path.join(out, "lora_adapter")
    merged_bf16 = os.path.join(out, "merged")
    merged_fp32 = os.path.join(out, "merged_fp32")

    # ---- A: train (also leaves the bf16-merged model on disk)
    if not os.path.isdir(adapter):
        log("=== A: training (pipeline.py) ===")
        sh(f"cd {ROOT} && python -u pipeline.py --model {args.model} --epochs {args.epochs} --tag {args.tag} --skip-merge-check")

    # ---- B: fp32 re-merge from the SAME adapter (isolates merge rounding)
    if not os.path.isdir(merged_fp32):
        log("=== B: fp32 merge ===")
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        try:
            base = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32, device_map="cuda")
        except TypeError:
            base = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float32, device_map="cuda")
        m = PeftModel.from_pretrained(base, adapter).merge_and_unload()
        m.save_pretrained(merged_fp32)
        AutoTokenizer.from_pretrained(args.model).save_pretrained(merged_fp32)
        del m, base
        import gc
        gc.collect()
        torch.cuda.empty_cache()

    # ---- C: llama.cpp with CUDA
    if not os.path.exists(f"{LLAMA}/build/bin/llama-server"):
        log("=== C: build llama.cpp (CUDA) ===")
        if subprocess.run("which nvcc", shell=True, capture_output=True).returncode != 0:
            log("nvcc not found -> cannot build CUDA llama.cpp"); sys.exit(2)
        if not os.path.isdir(LLAMA):
            sh(f"git clone --depth 1 https://github.com/ggml-org/llama.cpp {LLAMA}")
        sh(f"cd {LLAMA} && cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=80 -DLLAMA_CURL=OFF > /dev/null && "
           f"cmake --build build -j --target llama-server llama-quantize")
    sh("pip install -q gguf sentencepiece")

    # ---- D: convert both merges to f16 GGUF
    f16 = {}
    for name, d in (("bf16merge", merged_bf16), ("fp32merge", merged_fp32)):
        f16[name] = os.path.join(out, f"{name}-f16.gguf")
        if not os.path.exists(f16[name]):
            sh(f"python {LLAMA}/convert_hf_to_gguf.py {d} --outfile {f16[name]} --outtype f16")

    # ---- E: sweep
    blind5 = json.load(open(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), encoding="utf-8"))
    dev_rows = [json.loads(l) for l in open(os.path.join(ROOT, "mlx_data/dev_groups.jsonl"), encoding="utf-8") if l.strip()]
    results = []
    for name in ("bf16merge", "fp32merge"):
        for q in args.quants.split(","):
            if q == "f16":
                g = f16[name]
            else:
                g = os.path.join(out, f"{name}-{q}.gguf")
                if not os.path.exists(g):
                    sh(f"{LLAMA}/build/bin/llama-quantize {f16[name]} {g} {q}")
            results.append(serve_and_eval(g, f"{name}-{q}" + ("-gbnf" if GRAMMAR else ""), blind5, dev_rows))
            json.dump(results, open(os.path.join(out, "sweep_results_gbnf.json" if GRAMMAR else "sweep_results.json"), "w"), indent=1)
    log("=== SWEEP TABLE ===")
    log(f"{'config':22} {'F1':>6} {'P':>6} {'R':>6} {'acc':>6} {'dev':>6} {'parsefail':>9} {'GB':>5}")
    for r in sorted(results, key=lambda r: -r["f1"]):
        log(f"{r['label']:22} {r['f1']:6.3f} {r['precision']:6.3f} {r['recall']:6.3f} {r['accuracy']:6.3f} {r['dev']:6.3f} {r['parse_fail']:9d} {r['gb']:5.2f}")


if __name__ == "__main__":
    main()
