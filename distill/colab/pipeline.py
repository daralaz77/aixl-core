"""Self-verifying train -> merge -> export pipeline for the self-hosted AIXL translator (runs in ONE command on Colab).

Why this exists: the previous Colab/Unsloth path trained fine (correct in-session output) but the exported GGUF was
garbage, and nothing in the pipeline could say WHERE it broke. Every stage here is measured with the project's real
F1 on the held-out blind5 set, so a regression is localized to exactly one stage:

  S1 train LoRA (bf16 base, no 4-bit, no Unsloth -> adapter and merge target are the SAME weights)
  S2 F1 with adapter attached                      (what the student really learned)
  S3 merge_and_unload -> save -> RELOAD from disk -> F1  (must equal S2; if not, the merge/save is the bug)
  S4 (optional) HF -> GGUF f16 -> Q4_K_M with llama.cpp's own converter, sample-checked against S3 outputs

usage (Colab):  !python pipeline.py --model Qwen/Qwen2.5-3B-Instruct --epochs 3 --tag base3b [--export]
"""
import argparse
import gc
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def log(*a):
    print(*a, flush=True)


def load_rows(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        if line.strip():
            m = json.loads(line)["messages"]
            rows.append((m[0]["content"], m[1]["content"]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--train", default="mlx_data/train.jsonl")
    ap.add_argument("--valid", default="mlx_data/valid.jsonl")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--skip-merge-check", action="store_true")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    from peft import LoraConfig, get_peft_model

    out_dir = os.path.join(ROOT, f"out_{args.tag}")
    os.makedirs(out_dir, exist_ok=True)
    results = {"tag": args.tag, "model": args.model, "epochs": args.epochs, "lr": args.lr, "rank": args.rank}

    tok = AutoTokenizer.from_pretrained(args.model)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    stop_ids = [i for i in {im_end, tok.eos_token_id} if i is not None]

    def prompt_ids(text):
        return tok.apply_chat_template([{"role": "user", "content": text}], add_generation_prompt=True, tokenize=True)

    def as_ids(x):
        return x["input_ids"] if hasattr(x, "keys") else list(x)

    train_rows = load_rows(os.path.join(ROOT, args.train))
    valid_rows = load_rows(os.path.join(ROOT, args.valid))
    log(f"train rows {len(train_rows)}  valid rows {len(valid_rows)}")

    class DS(torch.utils.data.Dataset):
        def __init__(self, rows):
            self.items = []
            for text, aixl in rows:
                p = as_ids(prompt_ids(text))
                c = tok(aixl, add_special_tokens=False)["input_ids"] + [im_end]
                ids = (p + c)[:256]
                labels = ([-100] * len(p) + c)[:256]
                self.items.append((ids, labels))

        def __len__(self):
            return len(self.items)

        def __getitem__(self, i):
            return self.items[i]

    def collate(batch):
        n = max(len(x[0]) for x in batch)
        ids = torch.full((len(batch), n), tok.pad_token_id, dtype=torch.long)
        lab = torch.full((len(batch), n), -100, dtype=torch.long)
        att = torch.zeros((len(batch), n), dtype=torch.long)
        for i, (a, b) in enumerate(batch):
            ids[i, : len(a)] = torch.tensor(a)
            lab[i, : len(b)] = torch.tensor(b)
            att[i, : len(a)] = 1
        return {"input_ids": ids, "labels": lab, "attention_mask": att}

    def load_model(path):
        try:
            return AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, device_map="cuda")
        except TypeError:
            return AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16, device_map="cuda")

    # ---------------------------------------------------------------- eval helpers
    from benchmarks.llm_translator_eval import run as run_f1

    blind5 = json.load(open(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), encoding="utf-8"))

    @torch.no_grad()
    def generate_all(model, texts, bs=64):
        model.eval()
        outs = []
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        res = {}
        for s in range(0, len(order), bs):
            idx = order[s : s + bs]
            enc = tok([tok.apply_chat_template([{"role": "user", "content": texts[i]}], add_generation_prompt=True, tokenize=False) for i in idx],
                      return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
            gen = model.generate(**enc, max_new_tokens=110, do_sample=False, eos_token_id=stop_ids, pad_token_id=tok.pad_token_id)
            for j, i in enumerate(idx):
                res[i] = tok.decode(gen[j][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        return [res[i] for i in range(len(texts))]

    def first_line(raw):
        for line in raw.splitlines():
            line = line.strip().strip("`").strip()
            if line.startswith("V:AIXL"):
                return line
        return None

    def f1_blind5(model, label):
        t0 = time.time()
        raws = generate_all(model, [t["text"] for t in blind5])
        lines = [first_line(r) for r in raws]
        path = os.path.join(out_dir, f"answers_{label}.txt")
        with open(path, "w", encoding="utf-8") as f:
            for t, l in zip(blind5, lines):
                f.write(f"{t['tid']} :: {l or 'PARSE_FAILURE'}\n")
        summ, rows = run_f1([path], fallback=False, set_no=5)
        wrong = [r for r in rows if (r["label"] == "EQUIVALENT") != r["pred"]]
        from collections import Counter
        eq = summ["equivalence"]
        log(f"[{label}] F1={eq.get('f1')} P={eq.get('precision')} R={eq.get('recall')} parse_fail={summ['parse_failures']} "
            f"critical_drift={summ['critical_drift']['rate']}  ({time.time()-t0:.0f}s)")
        log(f"[{label}] errors by (label,category):", Counter((r["label"], r.get("category")) for r in wrong).most_common(10))
        return summ, lines

    def exact_valid(model, label):
        raws = generate_all(model, [t for t, _ in valid_rows])
        em = sum(first_line(r) == a for r, (_, a) in zip(raws, valid_rows)) / len(valid_rows)
        log(f"[{label}] valid exact-match vs teacher label: {em:.3f}")
        return em

    # ---------------------------------------------------------------- S1 train
    log("=== S1: training LoRA on bf16 base ===")
    model = load_model(args.model)
    cfg = LoraConfig(r=args.rank, lora_alpha=args.rank, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, cfg)
    model.print_trainable_parameters()
    import inspect
    total_steps = int(len(train_rows) / args.bs * args.epochs) + 1
    wanted = dict(output_dir=os.path.join(out_dir, "ckpt"), per_device_train_batch_size=args.bs,
                  num_train_epochs=args.epochs, learning_rate=args.lr, lr_scheduler_type="cosine",
                  warmup_steps=max(1, int(0.03 * total_steps)), bf16=True, logging_steps=25, save_strategy="no",
                  report_to="none", seed=0, remove_unused_columns=False)
    accepted = set(inspect.signature(TrainingArguments.__init__).parameters)
    dropped = [k for k in wanted if k not in accepted]
    if dropped:
        log("TrainingArguments: dropping unsupported args for this transformers version:", dropped)
    targs = TrainingArguments(**{k: v for k, v in wanted.items() if k in accepted})
    t0 = time.time()
    trainer = Trainer(model=model, args=targs, train_dataset=DS(train_rows), data_collator=collate)
    tr = trainer.train()
    results["train_loss"] = tr.training_loss
    results["train_seconds"] = time.time() - t0
    log(f"train done: loss {tr.training_loss:.4f} in {time.time()-t0:.0f}s")

    # ---------------------------------------------------------------- S2 adapter F1
    log("=== S2: F1 with adapter attached ===")
    model.config.use_cache = True
    results["valid_em_adapter"] = exact_valid(model, "adapter")
    s2, lines_adapter = f1_blind5(model, "adapter")
    results["adapter"] = s2["equivalence"]
    model.save_pretrained(os.path.join(out_dir, "lora_adapter"))

    # ---------------------------------------------------------------- S3 merge + reload from disk
    log("=== S3: merge, save, RELOAD from disk, re-measure ===")
    merged_dir = os.path.join(out_dir, "merged")
    merged = model.merge_and_unload()
    merged.save_pretrained(merged_dir)
    tok.save_pretrained(merged_dir)
    del merged, model, trainer
    gc.collect()
    torch.cuda.empty_cache()
    if not args.skip_merge_check:
        m2 = load_model(merged_dir)
        results["valid_em_merged"] = exact_valid(m2, "merged")
        s3, lines_merged = f1_blind5(m2, "merged")
        results["merged"] = s3["equivalence"]
        same = sum(a == b for a, b in zip(lines_adapter, lines_merged)) / len(lines_adapter)
        results["adapter_vs_merged_identical_outputs"] = same
        log(f"adapter-vs-merged identical outputs: {same:.3f}  (should be ~1.0; much lower => merge/save bug)")
        del m2
        gc.collect()
        torch.cuda.empty_cache()

    # ---------------------------------------------------------------- S4 export
    if args.export:
        log("=== S4: HF -> GGUF (llama.cpp converter) ===")
        sh = lambda c: subprocess.run(c, shell=True, check=True)  # noqa: E731
        if not os.path.isdir("/content/llama.cpp"):
            sh("git clone --depth 1 https://github.com/ggml-org/llama.cpp /content/llama.cpp")
        sh("pip install -q gguf sentencepiece")
        f16 = os.path.join(out_dir, "model-f16.gguf")
        sh(f"python /content/llama.cpp/convert_hf_to_gguf.py {merged_dir} --outfile {f16} --outtype f16")
        if not os.path.exists("/content/llama.cpp/build/bin/llama-quantize"):
            sh("cd /content/llama.cpp && cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DGGML_NATIVE=ON > /dev/null "
               "&& cmake --build build -j --target llama-quantize llama-completion")
        q4 = os.path.join(out_dir, f"aixl-{args.tag}-Q4_K_M.gguf")
        sh(f"/content/llama.cpp/build/bin/llama-quantize {f16} {q4} Q4_K_M")
        sha = hashlib.sha256(open(q4, "rb").read()).hexdigest()
        results["gguf"] = {"path": q4, "sha256": sha, "bytes": os.path.getsize(q4)}
        log(f"GGUF {q4}  sha256={sha}")
        ok = 0
        sample = blind5[:12]
        for t in sample:
            p = tok.apply_chat_template([{"role": "user", "content": t["text"]}], add_generation_prompt=True, tokenize=False)
            r = subprocess.run(["/content/llama.cpp/build/bin/llama-completion", "-m", q4, "-p", p, "-n", "90", "--temp", "0",
                                "--no-display-prompt"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
            got = first_line(r.stdout.replace("<|im_end|>", "\n"))
            want = lines_adapter[blind5.index(t)]
            ok += got == want
            log(f"  gguf-vs-adapter {'OK ' if got == want else 'DIFF'} | {t['text'][:60]} | {got}")
        results["gguf_sample_match"] = f"{ok}/{len(sample)}"
        log(f"GGUF sample agreement with the verified adapter outputs: {ok}/{len(sample)}")

    json.dump(results, open(os.path.join(out_dir, "results.json"), "w"), indent=1)
    log("=== RESULT ===")
    log(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
