"""ADR-016 step 1 gate metrics: for pair sets, how often a NON-equivalent pair is judged EQUIVALENT (false-EQUIVALENT, the
dangerous error) and how often a truly EQUIVALENT pair is judged EQUIVALENT / INCONCLUSIVE / NOT_EQUIVALENT.
usage: python -m benchmarks.inconclusive_eval [--off]   (--off disables INCONCLUSIVE = the 0.4 behaviour, for A/B)"""
import json, sys, glob, collections
from aixl import compare
from aixl.core.ontology import load_config

def sets():
    out = {}
    for src in ("opus", "haiku"):
        out["blind10-" + src] = [json.loads(l) for l in open(f"data/blind10/{src}.jsonl")]
    out["own-5x100"] = [json.loads(l) for lab in ("EQUIVALENT", "NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "CONTRADICTORY")
                        for l in open(f"data/sil5x100/{lab}.jsonl")]
    pairs = []
    for f in glob.glob("data/blind*/pairs_*.jsonl"):
        for l in open(f):
            r = json.loads(l)
            if "a" in r and "b" in r and r.get("label") in ("EQUIVALENT", "NOT_EQUIVALENT"): pairs.append(r)
    out["blind1-9"] = pairs
    return out

def main():
    cfg = dict(load_config()); cfg["inconclusive"] = "--off" not in sys.argv
    for name, rows in sets().items():
        eq = collections.Counter(); ne = collections.Counter()
        for r in rows:
            if "b" not in r: continue
            v = compare(r["a"], r["b"], cfg).verdict
            (eq if r["label"] == "EQUIVALENT" else ne)[v] += 1
        ne_n, eq_n = sum(ne.values()), sum(eq.values())
        print(f"{name:14s} false-EQUIVALENT {ne['EQUIVALENT']:3d}/{ne_n} = {100*ne['EQUIVALENT']/max(1,ne_n):5.1f}%   "
              f"| true EQUIV -> EQ {eq['EQUIVALENT']}/{eq_n} = {100*eq['EQUIVALENT']/max(1,eq_n):5.1f}%, INCONCL {eq['INCONCLUSIVE']}, NOT {eq['NOT_EQUIVALENT']}")
main()
