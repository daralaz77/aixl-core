"""blind13 one-shot evaluation (see data/blind13/PREREG.md). usage: python -m benchmarks.blind13_eval [--show]"""
import json, sys, collections, hashlib, os
import aixl
from aixl.core.ontology import load_config
from benchmarks.golden_r_eval import outcome

D = os.path.join(os.path.dirname(__file__), "..", "data", "blind13")
man = json.load(open(os.path.join(D, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(D, n), "rb").read()).hexdigest() == h, f"{n} changed since freezing"
rows = []
for f, a in (("authorS_sonnet.jsonl", "sonnet"), ("authorO_opus.jsonl", "opus")):
    for l in open(os.path.join(D, f), encoding="utf-8"):
        r = json.loads(l); r["author"] = a; rows.append(r)


def run(inconclusive, show):
    cfg = dict(load_config()); cfg["inconclusive"] = inconclusive
    out = {}
    for scope in ("all", "sonnet", "opus"):
        sel = [r for r in rows if scope == "all" or r["author"] == scope]
        c = collections.Counter(); cat = collections.defaultdict(collections.Counter)
        for r in sel:
            got = aixl.compare(r["text_a"], r["text_b"], config=cfg).verdict
            o = outcome(r["expected_equivalence"], got); c[o] += 1; cat[r["category"]][o] += 1
            if r["expected_equivalence"] == "EQUIVALENT" and got == "EQUIVALENT": c["_proven"] += 1
            if r["expected_equivalence"] == "UNDECIDABLE" and got == "INCONCLUSIVE": c["_und_ok"] += 1
            if show and scope == "all" and o in ("FALSE_EQUIVALENT", "FALSE_REJECT"):
                print(f'  {o:16} {r["id"]} {r["category"]:24} exp={r["expected_equivalence"]:14} got={got:14} {r["text_a"]!r} | {r["text_b"]!r}')
        n_eq = sum(r["expected_equivalence"] == "EQUIVALENT" for r in sel); n_bad = len(sel) - n_eq
        out[scope] = dict(n=len(sel), false_equivalent=f"{c['FALSE_EQUIVALENT']}/{n_bad} ({100*c['FALSE_EQUIVALENT']/n_bad:.1f}%)",
                          proven=f"{c['_proven']}/{n_eq} ({100*c['_proven']/n_eq:.1f}%)", undecidable_flagged=f"{c['_und_ok']}/{sum(r['expected_equivalence']=='UNDECIDABLE' for r in sel)}",
                          false_reject=c["FALSE_REJECT"], inconclusive=c["inconclusive"], over_decided=c["over_decided"])
        if scope == "all": out["by_category_false_equiv"] = {k: v["FALSE_EQUIVALENT"] for k, v in sorted(cat.items())}
    return out

for flag in (False, True):
    print(f"=== inconclusive={'ON' if flag else 'OFF'}")
    print(json.dumps(run(flag, "--show" in sys.argv), ensure_ascii=False, indent=1))
