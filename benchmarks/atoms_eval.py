"""Evaluate the atom extractor against a gold set: per-dimension fidelity, exact-graph rate, failures listed."""
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl.atoms.schema import AtomGraph
from aixl.atoms import fidelity
from aixl.atoms.extract import extract
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atoms_show import brief
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "atoms")

def run(gold_file="gold_dev.jsonl", cases_file="cases_dev.json", verbose=False, extractor=extract):
    texts = {c["id"]: c for c in json.load(open(os.path.join(D, cases_file), encoding="utf-8"))}
    scores, fails, errs = {}, [], []
    for l in open(os.path.join(D, gold_file), encoding="utf-8"):
        r = json.loads(l); c = texts[r["id"]]
        gold = AtomGraph.from_dict(dict(atoms=r["atoms"], relations=r["relations"], text=c["text"], lang=c["lang"]))
        try:
            got = extractor(c["text"])
        except Exception as e:
            errs.append((r["id"], repr(e))); got = AtomGraph(text=c["text"])
        s = fidelity.score(gold, got); scores[r["id"]] = s
        if not s["exact"]: fails.append((r["id"], c["text"], gold, got, s))
    return texts, scores, fails, errs

if __name__ == "__main__":
    verbose = "-v" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    gold = args[0] if args else "gold_dev.jsonl"; cases = args[1] if len(args) > 1 else "cases_dev.json"
    texts, scores, fails, errs = run(gold, cases)
    agg = fidelity.aggregate(list(scores.values()))
    print({k: (v if not isinstance(v, dict) else v["f1"]) for k, v in agg.items()}); print("cases", len(scores), "exact", len(scores) - len(fails), "errors", len(errs))
    for i, e in errs[:10]: print("ERR", i, e)
    if verbose:
        for i, t, g, got, s in fails:
            print(i, t); print("   G", brief(g)); print("   X", brief(got))
