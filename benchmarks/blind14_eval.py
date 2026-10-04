"""blind14 ONE-SHOT evaluation of the 0.3-R semantic track (see data/blind14/PREREG.md). Refuses to run if the code changed since freezing.
usage: python -m benchmarks.blind14_eval [--show]"""
import json, os, sys, glob, hashlib, collections
D = os.path.join(os.path.dirname(__file__), "..", "data", "blind14")
frozen = json.load(open(os.path.join(D, "CODE_FREEZE.json")))
for f, h in frozen.items():
    assert hashlib.sha256(open(os.path.join(os.path.dirname(__file__), "..", f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind14 is void"
man = json.load(open(os.path.join(D, "MANIFEST.json")))
for n, h in man.items():
    if n.endswith(".jsonl"): assert hashlib.sha256(open(os.path.join(D, n), "rb").read()).hexdigest() == h, f"{n} changed"
from aixl.semantic import compare_texts
from benchmarks.golden_r_eval import outcome
rows = [dict(json.loads(l), file=f) for f in man if f.endswith(".jsonl") for l in open(os.path.join(D, f), encoding="utf-8")]
c, cat, by = collections.Counter(), collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
for r in rows:
    v = compare_texts(r["text_a"], r["text_b"]); got = v.verdict
    o = outcome(r["expected_equivalence"], got)
    for k in (c, cat[r["category"]], by[r["file"]]):
        k[o] += 1
        if r["expected_equivalence"] == "EQUIVALENT" and got == "EQUIVALENT": k["_proven"] += 1
        if r["expected_equivalence"] == "UNDECIDABLE" and got == "INCONCLUSIVE": k["_und"] += 1
    if "--show" in sys.argv and o in ("FALSE_EQUIVALENT", "FALSE_REJECT", "over_decided"):
        print(f'  {o:16} {r["id"]} {r["category"][:12]:12} exp={r["expected_equivalence"][:6]:6} got={got[:6]:6} {r["text_a"]!r} | {r["text_b"]!r}')
def line(c, rows_):
    n_eq = sum(r["expected_equivalence"] == "EQUIVALENT" for r in rows_); n_bad = len(rows_) - n_eq; nu = sum(r["expected_equivalence"] == "UNDECIDABLE" for r in rows_)
    return (f'false_equivalent {c["FALSE_EQUIVALENT"]}/{n_bad} ({100*c["FALSE_EQUIVALENT"]/max(n_bad,1):.1f}%)  proven {c["_proven"]}/{n_eq} ({100*c["_proven"]/max(n_eq,1):.1f}%)  '
            f'undecidable_flagged {c["_und"]}/{nu}  false_reject {c["FALSE_REJECT"]}  inconclusive {c["inconclusive"]}  over_decided {c["over_decided"]}')
print("ALL      ", line(c, rows))
for f in by: print(f"{f[:22]:22}", line(by[f], [r for r in rows if r["file"] == f]))
for k in sorted(cat): print(f"{k:26}", dict((a, b) for a, b in cat[k].items() if not a.startswith("_")))
