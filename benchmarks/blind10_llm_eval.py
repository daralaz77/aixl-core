"""E-BLIND10 LLM route: AIXL lines written by an LLM encoder (card 0.3) for data/blind10/texts.json, decoded with the SAME codec,
classified with the SAME mapping as sil5x100_eval.predict but on graphs. usage: python -m benchmarks.blind10_llm_eval ANS1 [ANS2...] [--show N]
Parse failures: pair judged NOT_EQUIVALENT (conservative); AMBIGUOUS single judged by detect_ambiguity_graph on text+graph."""
import json, os, re, sys, collections
from aixl.serialization import aixl_codec
from aixl.core.comparator import compare_graphs
from aixl.core.contradiction import detect_contradiction_graphs
from aixl.core.ambiguity import detect_ambiguity_graph
from benchmarks.sil5x100_eval import LABELS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    paths = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[i-1] == "--show"]
    ans = {}
    for p in paths:
        for l in open(p, encoding="utf-8"):
            m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
            if m: ans[m.group(1)] = m.group(2).strip("`")
    texts = json.load(open(os.path.join(ROOT, "data/blind10/texts.json"), encoding="utf-8"))
    gold = {}
    for src in ("opus", "haiku"):
        for l in open(os.path.join(ROOT, f"data/blind10/{src}.jsonl"), encoding="utf-8"):
            r = json.loads(l); gold[r["id"]] = r
    g, perr, missing = {}, 0, 0
    for t in texts:
        if t["tid"] not in ans: missing += 1; continue          # not evaluated
        try: g[t["tid"]] = aixl_codec.decode(ans[t["tid"]])
        except Exception: g[t["tid"]] = None; perr += 1
    by = collections.defaultdict(dict)
    for t in texts: by[t["id"]][t["side"]] = t
    rows = []
    for pid, sides in by.items():
        r = gold[pid]
        if any(s["tid"] not in g and s["tid"] not in ans for s in sides.values()): continue
        gs = {k: g.get(s["tid"]) for k, s in sides.items()}
        if r["label"] == "AMBIGUOUS":
            ga = gs["a"]
            pred = "AMBIGUOUS" if ga and detect_ambiguity_graph(r["a"], ga).ambiguous else "UNAMBIGUOUS"
        elif not gs["a"] or not gs["b"]:
            pred = "NOT_EQUIVALENT"
        elif detect_contradiction_graphs(gs["a"], gs["b"]).contradiction: pred = "CONTRADICTORY"
        else:
            c = compare_graphs(gs["a"], gs["b"])
            kinds = {d.kind for d in c.differences}
            if c.equivalent: pred = "EQUIVALENT"
            elif len(kinds) == 1 and kinds <= {"added", "removed"} and all(d.field != "NEGATION" for d in c.differences): pred = "PARTIALLY_EQUIVALENT"
            else: pred = "NOT_EQUIVALENT"
        rows.append({**r, "pred": pred, "src": pid.split("-")[0]})
    for scope in ("all", "O", "H"):
        sel = [r for r in rows if scope == "all" or r["src"] == scope]
        conf = collections.defaultdict(collections.Counter)
        for r in sel: conf[r["label"]][r["pred"]] += 1
        tot = 0; print(f"== {scope}")
        for lab in LABELS:
            n = sum(conf[lab].values()); ok = conf[lab][lab]; tot += ok
            print(f"{lab:22s} {ok:3d}/{n}  " + ", ".join(f"{k}={v}" for k, v in conf[lab].most_common() if k != lab))
        print(f"overall {tot}/{len(sel)} = {100*tot/max(1,len(sel)):.1f}%   (parse failures {perr}, texts without answer {missing})")
    fe = [r for r in rows if "b" in r and r["label"] != "EQUIVALENT" and r["pred"] == "EQUIVALENT"]
    print("false-EQUIVALENT:", len(fe))
    for r in [r for r in rows if r["pred"] != r["label"]][:show]:
        print(f'[{r["label"]}->{r["pred"]}] {r["a"]} || {r.get("b","")}')

main()
