"""Turns the open-model generations (distill/colab/qwen_gen.py output) into training groups, WITHOUT any teacher labelling:
every kept variant inherits the already-validated canonical label of its seed (corpus_merged.jsonl), and a variant is kept only
if it passes the deterministic `facts` check (numbers/#ids/modifier cues equal to the seed, aixl.core.irreversible_guard).
Seeds that belong to the 80 held-out DEV groups of build_mlx_data.py are skipped (no leakage into the dev measurement).

usage: python distill/build_qwen_groups.py <gens_1200.txt> [--out distill/corpus_paraphrase_qwen.jsonl]
"""
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.core.irreversible_guard import cue_signature  # noqa: E402
from aixl.serialization import aixl_codec  # noqa: E402


def parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        d = json.loads(m.group(0))
        vs = [v["text"].strip() for v in d["variants"] if v.get("text", "").strip()]
        return vs if len(vs) >= 3 else None
    except Exception:  # noqa: BLE001
        return None


def dev_seeds(n_dev=80):
    groups = {}
    for line in open(os.path.join(ROOT, "distill", "corpus_paraphrase.jsonl"), encoding="utf-8"):
        if line.strip():
            groups.setdefault(json.loads(line)["group"], 1)
    keys = sorted(groups)
    random.Random(11).shuffle(keys)
    return set(keys[:n_dev])


def main():
    gens = sys.argv[1]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(ROOT, "distill", "corpus_paraphrase_qwen.jsonl")
    seeds = [json.loads(l)["seed"] for l in open(os.path.join(ROOT, "distill", "paraphrase_cache.jsonl"), encoding="utf-8") if l.strip()]
    label = {}
    for line in open(os.path.join(ROOT, "distill", "corpus_merged.jsonl"), encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            label[d["text"]] = d["aixl"]
    raw = {}
    for line in open(gens, encoding="utf-8"):
        if line.startswith("GEN\t"):
            _, i, js = line.rstrip("\n").split("\t", 2)
            raw[int(i)] = json.loads(js)
    dev = dev_seeds()
    blind5 = {t["text"] for t in json.load(open(os.path.join(ROOT, "data", "llm_translator", "texts_blind5.json"), encoding="utf-8"))}
    st = {"seeds": len(seeds), "no_parse": 0, "dev_skipped": 0, "variants": 0, "kept": 0, "dup": 0, "groups": 0, "blind5_excluded": 0}
    rows = []
    for i, seed in enumerate(seeds):
        if seed in dev:
            st["dev_skipped"] += 1
            continue
        vs = parse(raw.get(i, ""))
        if not vs:
            st["no_parse"] += 1
            continue
        try:
            target = aixl_codec.encode(aixl_codec.decode(label[seed]))
        except Exception:  # noqa: BLE001
            continue
        sig, seen, kept = cue_signature(seed), {seed}, []
        for v in vs[:3]:
            st["variants"] += 1
            if v in seen:
                st["dup"] += 1
                continue
            if v in blind5:  # short generic phrases collide with the held-out test; the model must never train on them
                st["blind5_excluded"] += 1
                continue
            if cue_signature(v) == sig:
                kept.append(v)
                seen.add(v)
        if kept:
            st["groups"] += 1
            st["kept"] += len(kept)
            rows.append({"text": seed, "aixl": target, "group": "q:" + seed})
            rows += [{"text": v, "aixl": target, "group": "q:" + seed} for v in kept]
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps(st), "->", out)


if __name__ == "__main__":
    main()
