"""usage: score.py <root> -> json per-pair hybrid verdicts using the stored judge TSVs"""
import json
import os
import sys

root = sys.argv[1]; sys.path.insert(0, root)
import aixl  # noqa: E402,I001
assert aixl.__file__.startswith(root)
from aixl.semantic import hybrid  # noqa: E402,I001

H = os.path.dirname(os.path.abspath(__file__)) + "/"
key = json.load(open(H + "key.json"))
tab = {}
for name, f in (("sonnet", "judge_sonnet.tsv"), ("haiku", "judge_haiku.tsv")):
    d = {}
    for line in open(H + f, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2: d[p[0]] = p[1].strip().upper()
    tab[name] = d
by_text = {}
out = {}
for jid, r in key.items():
    judges = {n: (lambda a, b, n=n, jid=jid: tab[n].get(jid, "")) for n in tab}
    d = hybrid.decide(r["a"], r["b"], judges)
    ds = hybrid.decide(r["a"], r["b"], judges, require_semantic_equivalent=True)
    out[jid] = {"label": r["label"], "verdict": d.verdict, "strict": ds.verdict, "sem": d.semantic.verdict, "judges": {n: tab[n].get(jid, "") for n in tab}}
json.dump(out, sys.stdout)
