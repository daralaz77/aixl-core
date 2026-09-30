"""E-XV: cross-vendor evaluation on set 5 (pairs authored by Gemini [A5] and ChatGPT [B5]).
usage: python -m benchmarks.xv_eval rule | python -m benchmarks.xv_eval <encoder> <answers.txt>...
Reports overall and per author family. Parse failures count as NOT_EQUIVALENT."""
import json, os, sys
from aixl.serialization import aixl_codec
from aixl.core.comparator import compare_graphs
from aixl.translators.natural_to_semantic import to_graph
from benchmarks.llm_translator_eval import read, ROOT, CRIT
from benchmarks.metrics import prf


def evaluate(mode, paths=()):
    texts = json.load(open(os.path.join(ROOT, "data", "llm_translator", "texts_blind5.json"), encoding="utf-8"))
    ans = {} if mode == "rule" else read(paths)
    graphs, perr = {}, 0
    for t in texts:
        try:
            graphs[t["tid"]] = to_graph(t["text"]) if mode == "rule" else aixl_codec.decode(ans[t["tid"]])
        except Exception:                                # noqa: BLE001
            graphs[t["tid"]] = None; perr += 1
    by = {}
    for t in texts: by.setdefault(t["pair"], {})[t["side"]] = t["tid"]
    gold = {}
    for f in ("pairs_A5", "pairs_B5"):
        for l in open(os.path.join(ROOT, "data", "blind5", f + ".jsonl"), encoding="utf-8"):
            r = json.loads(l); gold[r["id"]] = r
    rows = []
    for pid, s in by.items():
        ga, gb = graphs[s["a"]], graphs[s["b"]]
        c = compare_graphs(ga, gb) if ga and gb else None
        rows.append({**gold[pid], "pred": bool(c and c.equivalent), "level": c.drift_level if c else "UNKNOWN"})
    def summ(rs):
        tp = sum(r["label"] == "EQUIVALENT" and r["pred"] for r in rs); fn = sum(r["label"] == "EQUIVALENT" and not r["pred"] for r in rs)
        fp = sum(r["label"] == "NOT_EQUIVALENT" and r["pred"] for r in rs); tn = sum(r["label"] == "NOT_EQUIVALENT" and not r["pred"] for r in rs)
        crit = [r for r in rs if r["label"] == "NOT_EQUIVALENT" and r["category"] in CRIT]
        det = [r for r in crit if not r["pred"] and r["level"] in ("MAJOR_DRIFT", "CRITICAL_DRIFT")]
        return {"n": len(rs), **prf(tp, fp, fn, tn), "tp": tp, "fn": fn, "fp": fp, "tn": tn, "critical": f"{len(det)}/{len(crit)}"}
    return {"parse_failures": perr, "all": summ(rows), "gemini": summ([r for r in rows if r["id"].startswith("GEM")]),
            "chatgpt": summ([r for r in rows if r["id"].startswith("GPT")])}, rows


if __name__ == "__main__":
    mode = sys.argv[1]; s, rows = evaluate("rule" if mode == "rule" else "enc", sys.argv[2:])
    print(mode, json.dumps(s, ensure_ascii=False))
    if "--errors" in os.environ.get("XV", ""):
        for r in rows:
            if (r["label"] == "EQUIVALENT") != r["pred"]: print(r["id"], r["label"], r["a"], "||", r["b"])
