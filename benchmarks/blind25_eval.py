"""blind25 (80 pairs, semantic comparator alone) one-shot evaluation. See data/blind25/PREREG.md for the gates, written before the pairs existed.
Refuses to run if the frozen code/rules or the pair files changed, and refuses a second run once RESULT_run1.txt exists.
usage: python -m benchmarks.blind25_eval [--show]"""
import collections
import hashlib
import json
import os
import sys

from aixl.semantic import compare_texts

ROOT = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(ROOT, "data", "blind25")


def pct(a, b):
    return f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"


if __name__ == "__main__":
    for f, h in json.load(open(os.path.join(D, "CODE_FREEZE.json"))).items():
        assert hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind25 is void"
    man = json.load(open(os.path.join(D, "MANIFEST.json")))
    for n, h in man.items():
        if n.endswith(".jsonl"):
            assert hashlib.sha256(open(os.path.join(D, n), "rb").read()).hexdigest() == h, f"{n} changed"
    if os.path.exists(os.path.join(D, "RESULT_run1.txt")):
        sys.exit("blind25 was already run once (RESULT_run1.txt exists): the set is SPENT")

    rows = [json.loads(l) for n in man if n.endswith(".jsonl") for l in open(os.path.join(D, n), encoding="utf-8") if l.strip()]
    lab = lambda r: r["expected_equivalence"]
    verdict = {r["id"]: compare_texts(r["text_a"], r["text_b"]) for r in rows}
    V = lambda r: verdict[r["id"]].verdict
    non_eq = [r for r in rows if lab(r) != "EQUIVALENT"]
    eq = [r for r in rows if lab(r) == "EQUIVALENT"]
    print(f"SET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}  verdicts {dict(collections.Counter(V(r) for r in rows))}")

    fe = [r for r in non_eq if V(r) == "EQUIVALENT"]
    called_ne = [r for r in rows if V(r) == "NOT_EQUIVALENT"]
    ok_ne = [r for r in called_ne if lab(r) == "NOT_EQUIVALENT"]
    g1 = len(fe) <= 0.03 * len(non_eq)
    g2 = len(ok_ne) >= 0.90 * max(len(called_ne), 1)
    print(f"\n[G1] false-EQUIVALENT: {pct(len(fe), len(non_eq))} (gate <= 3%) -> {'PASS' if g1 else 'FAIL'}   ids: {[r['id'] for r in fe]}")
    print(f"[G2] NOT_EQUIVALENT precision: {pct(len(ok_ne), len(called_ne))} (gate >= 90%) -> {'PASS' if g2 else 'FAIL'}")
    wrong_ne = [r for r in called_ne if lab(r) != "NOT_EQUIVALENT"]
    print("     wrong NOT_EQUIVALENT ids:", [(r["id"], lab(r)) for r in wrong_ne])
    print(f"[G3] proven-EQUIVALENT recall: {pct(sum(V(r) == 'EQUIVALENT' for r in eq), len(eq))}   "
          f"NOT_EQUIVALENT recall: {pct(sum(V(r) == 'NOT_EQUIVALENT' for r in rows if lab(r) == 'NOT_EQUIVALENT'), sum(lab(r) == 'NOT_EQUIVALENT' for r in rows))}   "
          f"INCONCLUSIVE: {pct(sum(V(r) == 'INCONCLUSIVE' for r in rows), len(rows))}")
    print("\n[G4] per family: false-EQUIVALENT | wrong NOT_EQUIVALENT | proven-EQUIVALENT of EQUIVALENT-labelled | n")
    for fam in sorted({r["family"] for r in rows}):
        rs = [r for r in rows if r["family"] == fam]
        a = sum(1 for r in rs if lab(r) != "EQUIVALENT" and V(r) == "EQUIVALENT")
        b = sum(1 for r in rs if V(r) == "NOT_EQUIVALENT" and lab(r) != "NOT_EQUIVALENT")
        c = sum(1 for r in rs if lab(r) == "EQUIVALENT" and V(r) == "EQUIVALENT")
        print(f"  {fam:36s} {a} | {b} | {c}/{sum(lab(r) == 'EQUIVALENT' for r in rs)} | {len(rs)}")
    sus = sum(1 for r in non_eq if V(r) == "INCONCLUSIVE" and verdict[r["id"]].suspected)
    print(f"\n[extra] non-EQUIVALENT-labelled pairs that are INCONCLUSIVE but carry a suspected difference: {sus}")
    print(f"\nCLAIM 'does not fail silently on new families (G1)': {'ALLOWED (worded narrowly, with INCONCLUSIVE rate and NOT_EQUIVALENT recall)' if g1 else 'NOT ALLOWED'}")
    print(f"CLAIM 'NOT_EQUIVALENT is reliable on other authors text (G1 and G2)': {'ALLOWED' if g1 and g2 else 'NOT ALLOWED'}")
    if "--show" in sys.argv:
        for r in rows:
            wrong = (V(r) == "EQUIVALENT" and lab(r) != "EQUIVALENT") or (V(r) == "NOT_EQUIVALENT" and lab(r) != "NOT_EQUIVALENT")
            if wrong:
                print(f"\n{r['id']} [{lab(r)} vs {V(r)}] {r['text_a']} || {r['text_b']}\n   {[(d.path, d.original, d.new) for d in verdict[r['id']].diffs]}")
