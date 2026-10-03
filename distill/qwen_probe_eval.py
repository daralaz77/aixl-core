"""Local scorer for the free-teacher feasibility probe (see distill/colab/qwen_gen.py). Same seeds, same deterministic checks
for Haiku (from distill/paraphrase_cache.jsonl) and for the open model's raw generations:
  parse     : valid JSON with >= 3 variants
  facts     : numbers/#ids and modifier cues equal to the seed (aixl.core.irreversible_guard.cue_signature)
  rules     : rule-based translator + comparator call seed and variant EQUIVALENT (proxy, ~80 % accurate for both generators)
  all3-facts: all three variants pass `facts` (the unit that would become a training group)
usage: python distill/qwen_probe_eval.py seeds.json gens.txt   (gens.txt = the GEN lines copied from Colab)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.core.comparator import compare_graphs  # noqa: E402
from aixl.core.irreversible_guard import cue_signature  # noqa: E402
from aixl.translators.natural_to_semantic import to_graph  # noqa: E402


def parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        d = json.loads(m.group(0))
        vs = [v["text"].strip() for v in d["variants"] if v.get("text", "").strip()]
        return vs if len(vs) >= 3 else None
    except Exception:  # noqa: BLE001
        return None


def checks(seed, variants):
    out = []
    for v in variants[:3]:
        facts = cue_signature(seed) == cue_signature(v)
        try:
            rules = bool(compare_graphs(to_graph(seed), to_graph(v)).equivalent)
        except Exception:  # noqa: BLE001
            rules = False
        out.append((facts, rules))
    return out


def summarize(name, rows):
    n = len(rows)
    ok = [r for r in rows if r["variants"]]
    allc = [c for r in ok for c in r["checks"]]
    all3 = sum(all(f for f, _ in r["checks"]) for r in ok)
    print(f"{name:14} seeds={n} parse={len(ok)/n:.2f} variants={len(allc)} facts={sum(f for f,_ in allc)/max(1,len(allc)):.2f} "
          f"rules={sum(r for _,r in allc)/max(1,len(allc)):.2f} all3-facts={all3/n:.2f}")


def main():
    seeds_file, gens_file = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else "open-model"
    data = json.load(open(seeds_file, encoding="utf-8"))  # [{"seed":..., "haiku":[3 variants]}]
    raw = {}
    for line in open(gens_file, encoding="utf-8"):
        if line.startswith("GEN\t"):
            _, i, js = line.rstrip("\n").split("\t", 2)
            raw[int(i)] = json.loads(js)
    h_rows, q_rows = [], []
    for i, d in enumerate(data):
        vs = parse(raw.get(i, ""))
        q_rows.append({"seed": d["seed"], "variants": vs, "checks": checks(d["seed"], vs) if vs else []})
        h_rows.append({"seed": d["seed"], "variants": d["haiku"], "checks": checks(d["seed"], d["haiku"])})
    print("=== same seeds, same deterministic checks ===")
    summarize("haiku", h_rows)
    summarize(label, q_rows)
    print(f"--- {label} variants failing `facts` (first 10) ---")
    k = 0
    for r in q_rows:
        for v, (f, _) in zip(r["variants"] or [], r["checks"]):
            if not f and k < 10:
                k += 1
                print(" SEED:", r["seed"][:100], "\n   VAR:", v[:100])


if __name__ == "__main__":
    main()
