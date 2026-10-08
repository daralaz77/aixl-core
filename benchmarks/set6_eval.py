"""Confirm codec/translator fixes on a single-file blind set (set 6+: 100 pairs, one pairs_S<n>.jsonl,
texts_set<n>.json). usage: python -m benchmarks.set6_eval rule [--set7] | python -m benchmarks.set6_eval
<encoder> <answers.txt>... [--set7]. Parse failures count as NOT_EQUIVALENT (same convention as
llm_translator_eval / xv_eval). Default set is 6; pass --set7 (or edit SET_NO) for later ones."""
import json
import os
import sys
from datetime import date

from aixl.core.comparator import compare_graphs
from aixl.serialization import aixl_codec
from aixl.translators.natural_to_semantic import to_graph
from benchmarks.llm_translator_eval import CRIT, ROOT, read
from benchmarks.metrics import prf

REFERENCE_TODAY = date(2026, 9, 27)  # pinned: the date these blind sets were authored/encoded against


def evaluate(mode, paths=(), set_no=6):
    texts = json.load(open(os.path.join(ROOT, "data", "llm_translator", f"texts_set{set_no}.json"), encoding="utf-8"))
    ans = {} if mode == "rule" else read(paths)
    graphs, perr, perr_ids = {}, 0, []
    for t in texts:
        try:
            graphs[t["tid"]] = to_graph(t["text"], today=REFERENCE_TODAY) if mode == "rule" else aixl_codec.decode(ans[t["tid"]])
        except Exception:                                # noqa: BLE001
            graphs[t["tid"]] = None; perr += 1; perr_ids.append(t["tid"])
    by = {}
    for t in texts: by.setdefault(t["pair"], {})[t["side"]] = t["tid"]
    gold = {}
    for l in open(os.path.join(ROOT, "data", f"blind{set_no}", f"pairs_S{set_no}.jsonl"), encoding="utf-8"):
        r = json.loads(l); gold[r["id"]] = r
    rows = []
    for pid, s in by.items():
        ga, gb = graphs[s["a"]], graphs[s["b"]]
        c = compare_graphs(ga, gb, today=REFERENCE_TODAY) if ga and gb else None
        rows.append({**gold[pid], "pred": bool(c and c.equivalent), "level": c.drift_level if c else "UNKNOWN"})
    tp = sum(r["label"] == "EQUIVALENT" and r["pred"] for r in rows); fn = sum(r["label"] == "EQUIVALENT" and not r["pred"] for r in rows)
    fp = sum(r["label"] == "NOT_EQUIVALENT" and r["pred"] for r in rows); tn = sum(r["label"] == "NOT_EQUIVALENT" and not r["pred"] for r in rows)
    crit = [r for r in rows if r["label"] == "NOT_EQUIVALENT" and r["category"] in CRIT]
    det = [r for r in crit if not r["pred"] and r["level"] in ("MAJOR_DRIFT", "CRITICAL_DRIFT")]
    summ = {"n": len(rows), **prf(tp, fp, fn, tn), "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "critical": f"{len(det)}/{len(crit)}", "parse_failures": perr, "parse_failure_ids": perr_ids}
    return summ, rows


if __name__ == "__main__":
    args = sys.argv[1:]
    set_no = 6
    for a in list(args):
        if a.startswith("--set") and a[5:].isdigit():
            set_no = int(a[5:]); args.remove(a)
    mode = args[0]
    s, rows = evaluate("rule" if mode == "rule" else "enc", args[1:], set_no)
    print(mode, json.dumps(s, ensure_ascii=False))
    if os.environ.get("XV") == "--errors":
        for r in rows:
            if (r["label"] == "EQUIVALENT") != r["pred"]:
                print(r["id"], r["label"], r["a"], "||", r["b"])
