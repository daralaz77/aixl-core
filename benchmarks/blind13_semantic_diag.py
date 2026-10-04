"""DIAGNOSTIC ONLY: the 0.3-R semantic track on blind13 after blind13 was spent and seen. Not independent evidence (see data/blind13/PREREG.md)."""
import json, os, sys, collections
from aixl.semantic import compare_texts
from benchmarks.golden_r_eval import outcome
D = os.path.join(os.path.dirname(__file__), "..", "data", "blind13")
rows = [json.loads(l) for f in ("authorS_sonnet.jsonl", "authorO_opus.jsonl") for l in open(os.path.join(D, f), encoding="utf-8")]
c, cat = collections.Counter(), collections.defaultdict(collections.Counter)
for r in rows:
    v = compare_texts(r["text_a"], r["text_b"]); got = v.verdict
    o = outcome(r["expected_equivalence"], got); c[o] += 1; cat[r["category"]][o] += 1
    if r["expected_equivalence"] == "EQUIVALENT" and got == "EQUIVALENT": c["_proven"] += 1
    if r["expected_equivalence"] == "UNDECIDABLE" and got == "INCONCLUSIVE": c["_und"] += 1
    if "--show" in sys.argv and o in ("FALSE_EQUIVALENT", "FALSE_REJECT", "over_decided"):
        print(f'  {o:16} {r["id"]} exp={r["expected_equivalence"][:6]:6} got={got[:6]:6} {r["text_a"]!r} | {r["text_b"]!r}  {v.unresolved[:1]}')
n_eq = sum(r["expected_equivalence"] == "EQUIVALENT" for r in rows); n_bad = len(rows) - n_eq
print(f'false_equivalent {c["FALSE_EQUIVALENT"]}/{n_bad} ({100*c["FALSE_EQUIVALENT"]/n_bad:.1f}%)  proven {c["_proven"]}/{n_eq}  undecidable_flagged {c["_und"]}/18  '
      f'false_reject {c["FALSE_REJECT"]}  inconclusive {c["inconclusive"]}  over_decided {c["over_decided"]}')
