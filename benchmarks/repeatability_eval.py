"""ADR-017 repeatability of the full-text arbiter: the SAME 82 pairs (10 boundary pairs where a judge erred/disagreed before + 72 stable
background pairs), SAME rules, 5 independent passes per model (fresh agent each, line order shuffled per pass).
Reports per model: pairs with unanimous verdict over 5 passes, flip rate, per-pass accuracy spread, unstable pairs; and the 2-of-2
consensus per pass (SAME only if both models say SAME in that pass) with its own stability.  usage: python -m benchmarks.repeatability_eval DIR"""
import json
import os
import sys


def load(d, model):
    runs = []
    for i in range(1, 6):
        v = {}
        p = os.path.join(d, f"rep_out_{model}_{i}.tsv")
        if os.path.exists(p):
            for l in open(p, encoding="utf-8"):
                f = l.rstrip("\n").split("\t")
                if len(f) >= 2: v[f[0]] = f[1].strip().upper()
        runs.append(v)
    return runs

def main():
    d = sys.argv[1]
    sel = json.load(open("data/blind10/rep_set.json"))
    R = {m: load(d, m) for m in ("sonnet", "haiku")}
    exp = lambda r: "SAME" if r["label"] == "EQUIVALENT" else "DIFFERENT"
    print(f"pairs {len(sel)}  (boundary {sum(1 for r in sel if r['s']!=exp(r) or r['h']!=exp(r) or r['s']!=r['h'])})")
    cons = [dict() for _ in range(5)]
    for m, runs in R.items():
        unstable = []; acc = []
        for i, v in enumerate(runs):
            acc.append(sum(v.get(r["key"]) == exp(r) for r in sel))
        for r in sel:
            vs = [v.get(r["key"], "MISSING") for v in runs]
            if len(set(vs)) > 1: unstable.append((r["key"], r["label"], vs, r["a"][:45], r["b"][:45]))
        print(f"{m:7s} passes {len(runs)} | correct per pass {acc} | pairs with a flip: {len(unstable)}/{len(sel)} = {100*len(unstable)/len(sel):.1f}%")
        for u in unstable[:10]: print("     ", u)
    for i in range(5):
        for r in sel:
            s, h = R["sonnet"][i].get(r["key"]), R["haiku"][i].get(r["key"])
            cons[i][r["key"]] = "SAME" if s == h == "SAME" else "NOT_SAME"
    uns = [r for r in sel if len({cons[i][r["key"]] for i in range(5)}) > 1]
    acc = [sum((cons[i][r["key"]] == "SAME") == (r["label"] == "EQUIVALENT") for r in sel) for i in range(5)]
    print(f"consensus 2-of-2 | correct per pass {acc} | pairs with a flip: {len(uns)}/{len(sel)} = {100*len(uns)/len(sel):.1f}%")
    wrong_all = [r for r in sel if all((cons[i][r["key"]] == "SAME") != (r["label"] == "EQUIVALENT") for i in range(5))]
    print(f"consensus wrong in ALL 5 passes: {len(wrong_all)}", [(r['key'], r['label']) for r in wrong_all])
    fs = [sum(cons[i][r["key"]] == "SAME" and r["label"] != "EQUIVALENT" for r in sel) for i in range(5)]
    print("consensus false-SAME per pass:", fs)
main()
