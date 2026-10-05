"""Does the normal form raise agreement between independent extractions of the same text, without collapsing different texts?
  python benchmarks/atoms_norm_eval.py [--stages lemma,alias,rewrite] [--tables path]   (dev = blind1v3,2,3 ; held-out = blind4)"""
import sys, os, json, itertools, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atoms_sources import *
from aixl.atoms import fidelity
from aixl.atoms.normalize import Normalizer, load_tables

PAIRS = [("ann-S", "ann-O"), ("llm-sonnet", "llm-opus"), ("ann-S", "llm-opus"), ("ann-O", "llm-sonnet"), ("ann-S", "llm-sonnet"), ("ann-O", "llm-opus")]


def measure(norm, sets):
    sc = []
    for s in sets:
        src = sources(s)
        N = {k: ({i: norm(g) for i, g in v.items()} if norm else v) for k, v in src.items()}
        for a, b in PAIRS:
            if a in N and b in N:
                sc += [fidelity.score(N[a][i], N[b][i]) for i in N[a] if i in N[b]]
    a = fidelity.aggregate(sc)
    return dict(n=len(sc), exact=round(a["exact_graph"], 3), f1=round(a["overall"]["f1"], 3), core=round(a["core"]["f1"], 3), identity=round(a["identity"]["f1"], 3), relation=round(a["relation"]["f1"], 3))


def collisions(norm, sets):
    """different texts whose graphs got the same fingerprint (false equivalence); counted within each source."""
    seen = collections.defaultdict(dict); bad = []
    for s in sets:
        for name, G in sources(s).items():
            for i, g in G.items():
                h = (norm(g) if norm else g).fingerprint(include_unrepresented=False)
                key = (name, h)
                if key in seen and seen[key] != (s, i): bad.append((name, seen[key], (s, i)))
                seen.setdefault(key, (s, i))
    return bad


if __name__ == "__main__":
    stages = tuple(sys.argv[sys.argv.index("--stages") + 1].split(",")) if "--stages" in sys.argv else ("lemma", "alias", "rewrite")
    tables = load_tables(sys.argv[sys.argv.index("--tables") + 1]) if "--tables" in sys.argv else None
    norm = Normalizer(tables, stages)
    print("normal form version", norm.version, "stages", stages)
    for label, sets in (("DEV  (blind1v3,2,3)", DEV), ("HELD-OUT (blind4)", HELD)):
        print(f"{label}: raw  ", measure(None, sets)); print(f"{label}: norm ", measure(norm, sets))
    allsets = DEV + HELD
    print("false equivalences (different texts, same fingerprint): raw", len(collisions(None, allsets)), " norm", len(collisions(norm, allsets)))
