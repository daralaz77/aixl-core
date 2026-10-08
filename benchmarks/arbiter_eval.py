"""ADR-017 arbiter experiment: a judge that sees the FULL texts of both sides, two independent models (Sonnet, Haiku), on 240 blind10 pairs
(60 each of EQUIVALENT / NOT_EQUIVALENT / PARTIALLY_EQUIVALENT / CONTRADICTORY). Reports:
  - each judge alone, 2-of-2 consensus (SAME only if both say SAME),
  - PIPELINE = per-side completeness (card 0.6 encodings) + marker check + consensus SAME  ->  EQUIVALENT proven.
usage: python -m benchmarks.arbiter_eval DIR"""
import collections
import glob
import json
import os
import re
import sys

from aixl.core.completeness import annotate, marker_conflicts
from aixl.serialization import aixl_codec

LABELS = ("EQUIVALENT", "NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "CONTRADICTORY")

def load_verdicts(d, model):
    v = {}
    for p in glob.glob(os.path.join(d, f"arb_out_{model}_*.tsv")):
        for l in open(p, encoding="utf-8"):
            f = l.rstrip("\n").split("\t")
            if len(f) >= 2: v[f[0]] = f[1].strip().upper()
    return v

def main():
    d = sys.argv[1]
    gold = json.load(open("data/blind10/arb_gold.json"))
    T = json.load(open("data/blind10/texts.json")); txt = {t["tid"]: t["text"] for t in T}
    by = {}
    for t in T: by.setdefault(t["id"], {})[t["side"]] = t["tid"]
    ans = {}
    for p in glob.glob("data/blind10/ans06_sonnet_*.txt"):
        for l in open(p):
            m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
            if m: ans[m.group(1)] = m.group(2)
    J = {m: load_verdicts(d, m) for m in ("sonnet", "haiku")}
    def gate(pid):
        cs = []
        for k in ("a", "b"):
            tid = by[pid][k]; cs.append(annotate(aixl_codec.decode(ans[tid]), txt[tid]).meta["completeness"])
        opp, oth = marker_conflicts(set(cs[0]["markers"]), set(cs[1]["markers"]))
        return cs[0]["complete"] and cs[1]["complete"] and not opp and not oth
    res = collections.defaultdict(collections.Counter)
    for g in gold:
        j, lab = g["jid"], g["label"]
        s, h = J["sonnet"].get(j, "MISSING"), J["haiku"].get(j, "MISSING")
        cons = "SAME" if s == h == "SAME" else ("DIFFERENT" if "DIFFERENT" in (s, h) else "UNSURE")
        gt = gate(g["pid"])
        for name, v in (("sonnet alone", s), ("haiku alone", h), ("consensus 2-of-2", cons),
                        ("PIPELINE gate+consensus", "SAME" if gt and cons == "SAME" else ("BLOCKED" if not gt else cons))):
            res[name][(lab, v)] += 1
    for name, c in res.items():
        eq = c[("EQUIVALENT", "SAME")]
        fe = sum(c[(l, "SAME")] for l in LABELS[1:])
        per = {l: c[(l, "SAME")] for l in LABELS[1:]}
        print(f"{name:26s} EQUIVALENT proven {eq:2d}/60 = {100*eq/60:4.1f}% | false-EQUIVALENT {fe:2d}/180 = {100*fe/180:4.1f}%  {per}")
main()
