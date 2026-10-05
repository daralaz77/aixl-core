"""Gold-set tooling for the AIXL 0.4 atom model.
  agreement A B   : inter-annotator agreement between two annotation sets (per-dimension F1 + exact-graph rate)
  show ID...      : print the texts and both annotations side by side for adjudication
"""
import glob, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aixl.atoms.schema import AtomGraph
from aixl.atoms import fidelity

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "atoms")


def load(prefix, cases=None):
    texts = {c["id"]: c for c in json.load(open(os.path.join(D, cases or "cases_dev.json"), encoding="utf-8"))}
    out = {}
    for p in sorted(glob.glob(os.path.join(D, f"{prefix}*.jsonl"))):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                c = texts[r["id"]]
                out[r["id"]] = AtomGraph.from_dict(dict(atoms=r["atoms"], relations=r["relations"], text=c["text"], lang=c["lang"], unrepresented=r.get("unrepresented", [])))
    return out, texts


def agreement(a, b, texts):
    ids = sorted(set(a) & set(b))
    scores = {i: fidelity.score(a[i], b[i]) for i in ids}
    by_cat = {}
    for i in ids:
        by_cat.setdefault(i and texts[i].get("cat", "?"), []).append(scores[i])
    return ids, scores, fidelity.aggregate(list(scores.values()))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "agreement":
        cf = sys.argv[4] if len(sys.argv) > 4 else None
        a, texts = load(sys.argv[2], cf); b, _ = load(sys.argv[3], cf)
        ids, scores, agg = agreement(a, b, texts)
        print(f"{len(ids)} cases"); print(json.dumps(agg, indent=1))
        bad = [i for i in ids if not scores[i]["exact"]]
        print(f"exact-different: {len(bad)}:", " ".join(bad))
