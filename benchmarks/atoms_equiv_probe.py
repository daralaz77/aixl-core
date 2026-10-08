"""Behavioural equivalence probe for aixl.atoms between two code trees (e.g. a pre-registration freeze commit vs HEAD).
   git worktree add /tmp/frozen <commit>
   (cd /tmp && PYTHONPATH=/tmp/frozen python <repo>/benchmarks/atoms_equiv_probe.py /tmp/frozen.json)
   (cd /tmp && PYTHONPATH=<repo>      python <repo>/benchmarks/atoms_equiv_probe.py /tmp/head.json)   # then compare the two JSON files
Hashes, per item: the prompts built from the stored batches (both registry conditions), the rule extractor + normal form on every text found under
data/atoms, and every stored model response parsed + normalised. Inputs always come from THIS repo's data/; only the code under test differs."""
import glob
import hashlib
import json
import os
import sys

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "atoms")


def _h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def probe():
    import aixl.atoms.llm_extract as LX
    from aixl.atoms.extract import extract
    out = {"code_tree": os.path.dirname(os.path.dirname(LX.__file__)), "prompts": {}, "extract": {}, "resp": {}}
    for b in sorted(os.path.basename(p)[:-5] for p in glob.glob(f"{DATA}/batches/blind5_b*.json")):
        items = json.load(open(f"{DATA}/batches/{b}.json", encoding="utf-8"))
        for learned in (False, True):
            out["prompts"][f"{b}|learned={learned}"] = _h(LX.build_prompt(items, learned=learned))
    texts = {}
    for f in sorted(glob.glob(f"{DATA}/batches/*.json")) + sorted(glob.glob(f"{DATA}/*_cases.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for c in d if isinstance(d, list) else []:
            if isinstance(c, dict) and "text" in c:
                texts[os.path.basename(f) + ":" + c["id"]] = c["text"]
    for k, t in sorted(texts.items()):
        try:
            g = extract(t)
            n = LX.normalize_graph(g)
            out["extract"][k] = _h(json.dumps([g.fingerprint(include_unrepresented=False), n.fingerprint(include_unrepresented=False), g.to_dict()], sort_keys=True, default=str))
        except Exception as e:
            out["extract"][k] = "ERR " + type(e).__name__
    for f in sorted(glob.glob(f"{DATA}/llm/resp_*.txt")):
        r = LX.parse_response(open(f, encoding="utf-8").read(), [], None)
        out["resp"][os.path.basename(f)] = _h(json.dumps(sorted((i, g.fingerprint(include_unrepresented=False), LX.normalize_graph(g).fingerprint(include_unrepresented=False))
                                                              for i, g in r.graphs.items()), default=str) + json.dumps(sorted(r.errors)[:50], default=str))
    return out


def compare(a, b):
    return {k: (sum(a[k][x] == b[k].get(x) for x in a[k]), len(a[k])) for k in ("prompts", "extract", "resp")}


if __name__ == "__main__":
    res = probe()
    json.dump(res, open(sys.argv[1], "w"), indent=0, sort_keys=True)
    print(res["code_tree"], {k: len(res[k]) for k in ("prompts", "extract", "resp")})
    if len(sys.argv) > 2:
        print("identical (same/total):", compare(json.load(open(sys.argv[2])), res))
