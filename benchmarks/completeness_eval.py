"""ADR-017 step 1 gate metrics on the 120 blind10 EQUIVALENT/NOT_EQUIVALENT pairs (LLM route), with per-side completeness and
NO tolerance parameter. usage: python -m benchmarks.completeness_eval ANS_GLOB [--keys]   (--keys: replace R literals by the experiment-A canonical keys)"""
import collections
import glob
import json
import re
import sys

from aixl.core.comparator import compare_graphs
from aixl.core.completeness import annotate
from aixl.core.ontology import load_config
from aixl.serialization import aixl_codec


def main():
    pattern = sys.argv[1]; use_keys = "--keys" in sys.argv
    cfg = dict(load_config()); cfg["inconclusive"] = True
    T = json.load(open("data/blind10/texts.json")); txt = {t["tid"]: t["text"] for t in T}
    by = {}
    for t in T: by.setdefault(t["id"], {})[t["side"]] = t["tid"]
    ans = {}
    for p in glob.glob(pattern):
        for l in open(p):
            m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
            if m: ans[m.group(1)] = m.group(2)
    gold = json.load(open("data/blind10/rj_gold.json"))
    key = dict(l.rstrip("\n").split("\t", 1) for l in open("data/blind10/rc_out.tsv") if "\t" in l)
    res, comp = collections.Counter(), collections.Counter()
    for i, p in enumerate(gold):
        gs = {}
        for k in ("a", "b"):
            tid = by[p["pid"]][k]; g = aixl_codec.decode(ans[tid]); annotate(g, txt[tid])
            comp[g.meta["completeness"]["complete"]] += 1
            if use_keys:
                for n in g.by_type("RESIDUE"): n.value = ""
                rs = g.by_type("RESIDUE")
                if rs: rs[0].value = key.get(f"p{i:03d}{k}") or ""
            gs[k] = g
        res[(p["label"], compare_graphs(gs["a"], gs["b"], cfg).verdict)] += 1
    print(f"false-EQUIVALENT {res[('NOT_EQUIVALENT','EQUIVALENT')]}/60 | EQUIV proven {res[('EQUIVALENT','EQUIVALENT')]}/60, INCONCLUSIVE {res[('EQUIVALENT','INCONCLUSIVE')]}, NOT {res[('EQUIVALENT','NOT_EQUIVALENT')]} | "
          f"NOT_EQUIV: INCONCLUSIVE {res[('NOT_EQUIVALENT','INCONCLUSIVE')]}, NOT {res[('NOT_EQUIVALENT','NOT_EQUIVALENT')]} | sides complete {comp[True]}/{sum(comp.values())}")
main()
