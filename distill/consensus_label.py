"""Consensus of three INDEPENDENT labelers for NEW seeds (no paid teacher): rule-based translator, distilled student (GGUF),
open model + card (Qwen2.5-14B). Pairwise agreement uses the project's own comparator on the decoded graphs. A text is kept
only if >= 2 labelers agree; the target is the majority label's canonical string (preferring the student's/Qwen's string over
the rules' verbose one). The agreement statistics ARE the experiment's first result: they bound how trustworthy labels on
natural, other-author text can be (docs/EVIDENCE.md warns the card route is weak there).
usage: python distill/consensus_label.py texts.json rules.jsonl student.jsonl qwen_labels.txt [--out distill/corpus_newseeds.jsonl]
"""
import json
import os
import re
import sys
from collections import Counter
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.core.comparator import compare_graphs  # noqa: E402
from aixl.serialization import aixl_codec  # noqa: E402


def first_aixl(raw):
    for line in (raw or "").strip().splitlines():
        line = line.strip().strip("`").strip()
        if line.startswith("V:AIXL"):
            return line
    return None


def graph(line):
    try:
        return aixl_codec.decode(line) if line else None
    except Exception:  # noqa: BLE001
        return None


def main():
    texts = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(ROOT, "distill", "corpus_newseeds.jsonl")
    labelers = {"rules": {}, "student": {}, "qwen": {}}
    for l in open(sys.argv[2], encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            labelers["rules"][d["i"]] = d["aixl"]
    for l in open(sys.argv[3], encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            labelers["student"][d["i"]] = first_aixl(d["raw"])
    for l in open(sys.argv[4], encoding="utf-8"):
        if l.startswith("LAB\t"):
            _, i, js = l.rstrip("\n").split("\t", 2)
            labelers["qwen"][int(i)] = first_aixl(json.loads(js))
    prefer = ["student", "qwen", "rules"]
    st, rows, pair_ok = Counter(), [], Counter()
    for i, text in enumerate(texts):
        gs = {k: graph(v.get(i)) for k, v in labelers.items()}
        valid = {k: g for k, g in gs.items() if g is not None}
        st["texts"] += 1
        st[f"valid_{len(valid)}"] += 1
        agree = {}
        for a, b in combinations(sorted(valid), 2):
            try:
                eq = bool(compare_graphs(valid[a], valid[b]).equivalent)
            except Exception:  # noqa: BLE001
                eq = False
            agree[(a, b)] = eq
            pair_ok[f"{a}~{b}"] += eq
        # the labeler that agrees with the most others (ties broken by `prefer`)
        score = {k: sum(eq for (a, b), eq in agree.items() if k in (a, b)) for k in valid}
        if not score:
            continue
        best = max(score, key=lambda k: (score[k], -prefer.index(k)))
        if score[best] >= 1:
            st["kept"] += 1
            st[f"kept_by_{best}"] += 1
            st["unanimous"] += score[best] == 2
            rows.append({"text": text, "aixl": aixl_codec.encode(valid[best]), "group": "n:" + str(i), "agree": score[best]})
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = max(1, st["texts"])
    print(json.dumps(dict(st)), "\npairwise equivalent rate:", {k: round(v / n, 3) for k, v in pair_ok.items()}, "->", out)


if __name__ == "__main__":
    main()
