"""E-LLM: LLM encoder (card 0.3) -> AIXL -> SAME codec + comparator. usage: python -m benchmarks.llm_translator_eval <model> <chunk1.txt> <chunk2.txt> [--fallback]
Parse failures count as errors (pair judged NOT_EQUIVALENT); with --fallback the rule-based translator is used for texts whose AIXL does not parse."""
import json
import os
import re
import sys

from aixl.core.comparator import compare_graphs
from aixl.serialization import aixl_codec
from aixl.translators.natural_to_semantic import to_graph
from benchmarks.metrics import prf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRIT = {"NEGATION", "QUANTITY", "TIME", "CONSTRAINT", "CONDITION", "REFERENCE"}


def read(paths):
    d = {}
    for p in paths:
        for l in open(p, encoding="utf-8"):
            m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
            if m: d[m.group(1)] = m.group(2).strip("`")
    return d


def run(paths, fallback=False, set_no=3):
    texts = json.load(open(os.path.join(ROOT, "data", "llm_translator", f"texts_blind{set_no}.json"), encoding="utf-8"))
    ans = read(paths)
    graphs, parse_err = {}, []
    for t in texts:
        g = None
        try: g = aixl_codec.decode(ans[t["tid"]])
        except Exception:                                # noqa: BLE001
            parse_err.append(t["tid"])
            if fallback: g = to_graph(t["text"])
        graphs[t["tid"]] = g
    by_pair = {}
    for t in texts:
        by_pair.setdefault(t["pair"], {})[t["side"]] = t["tid"]
    gold = {}
    for f in (f"pairs_A{set_no}", f"pairs_B{set_no}"):
        for l in open(os.path.join(ROOT, "data", f"blind{set_no}", f + ".jsonl"), encoding="utf-8"):
            r = json.loads(l); gold[r["id"]] = r
    rows = []
    for pid, sides in by_pair.items():
        ga, gb = graphs[sides["a"]], graphs[sides["b"]]
        pred = compare_graphs(ga, gb).equivalent if ga and gb else False
        lvl = compare_graphs(ga, gb).drift_level if ga and gb else "UNKNOWN"
        rows.append({**gold[pid], "pred": pred, "level": lvl})
    tp = sum(1 for r in rows if r["label"] == "EQUIVALENT" and r["pred"]); fn = sum(1 for r in rows if r["label"] == "EQUIVALENT" and not r["pred"])
    fp = sum(1 for r in rows if r["label"] == "NOT_EQUIVALENT" and r["pred"]); tn = sum(1 for r in rows if r["label"] == "NOT_EQUIVALENT" and not r["pred"])
    crit = [r for r in rows if r["label"] == "NOT_EQUIVALENT" and r["category"] in CRIT]
    det = [r for r in crit if not r["pred"] and r["level"] in ("MAJOR_DRIFT", "CRITICAL_DRIFT")]
    return {"equivalence": prf(tp, fp, fn, tn), "critical_drift": {"n": len(crit), "detected": len(det), "rate": round(len(det) / len(crit), 4)},
            "texts": len(texts), "answers": len(ans), "parse_failures": len(parse_err), "fallback": fallback}, rows


if __name__ == "__main__":
    fb = "--fallback" in sys.argv
    set_no = 5 if "--set5" in sys.argv else (4 if "--set4" in sys.argv else 3)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    model, paths = args[0], args[1:]
    summ, rows = run(paths, fb, set_no)
    print(model, json.dumps(summ, ensure_ascii=False))
