"""blind18 (short) one-shot evaluation: semantic alone | arbiter 2-of-2 alone | HYBRID (see data/blind18/PREREG.md).
Refuses to run if the frozen code/rules changed or the pair files changed. Judge verdicts come from stored TSVs (data/blind18/judge_<name>.tsv),
produced by two independent agents that saw only rules_v1.txt and (id, a, b).
usage: python -m benchmarks.blind18_eval [--show]"""
import collections
import glob
import hashlib
import json
import os
import sys

from aixl import arbiter
from aixl.semantic import compare_texts, hybrid_decide

judges_raw = {}

def pct(a, b): return f"{a}/{b} ({100*a/max(b,1):.1f}%)"


if __name__ == "__main__":

    ROOT = os.path.join(os.path.dirname(__file__), "..")
    D = os.path.join(ROOT, "data", "blind18")
    for f, h in json.load(open(os.path.join(D, "CODE_FREEZE.json"))).items():
        assert hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind18 is void"
    man = json.load(open(os.path.join(D, "MANIFEST.json")))
    for n, h in man.items():
        assert hashlib.sha256(open(os.path.join(D, n), "rb").read()).hexdigest() == h, f"{n} changed"

    rows = [json.loads(l) for f in man if f.startswith("author") for l in open(os.path.join(D, f), encoding="utf-8")]
    ids = [r["id"] for r in rows]
    VARIANT_B = "--haiku-b" in sys.argv          # the Haiku judge produced two different answer sets; both are evaluated, a gate counts only if it holds under BOTH
    for p in sorted(glob.glob(os.path.join(D, "judge_*.tsv"))):
        name = os.path.basename(p)[6:-4]
        if name == "haiku_b": continue
        if name == "haiku" and VARIANT_B: p = os.path.join(D, "judge_haiku_b.tsv")
        parsed = arbiter.parse_judge_lines(open(p, encoding="utf-8").read(), ids)
        judges_raw[name] = parsed
        print(f"judge {name}: {len(parsed['verdicts'])}/{len(ids)} valid, missing {parsed['missing']}, invalid {parsed['invalid']}")
    J = {n: (lambda a, b, n=n, key={(r['text_a'], r['text_b']): r['id'] for r in rows}: judges_raw[n]["verdicts"].get(key[(a, b)])) for n in judges_raw}

    lab = lambda r: r["expected_equivalence"]
    non_eq = [r for r in rows if lab(r) != "EQUIVALENT"]; eq = [r for r in rows if lab(r) == "EQUIVALENT"]
    sem = {r["id"]: compare_texts(r["text_a"], r["text_b"]) for r in rows}
    hyb = {r["id"]: hybrid_decide(r["text_a"], r["text_b"], J) for r in rows}
    arb = {r["id"]: hyb[r["id"]].arbiter.verdict for r in rows}
    print(f"\nSET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}")
    fe = [r for r in non_eq if sem[r["id"]].verdict == "EQUIVALENT"]
    print("\n[SEMANTIC alone]")
    print("  false-equivalent:", pct(len(fe), len(non_eq)), "ids:", [r["id"] for r in fe])
    ne = [r for r in rows if sem[r["id"]].verdict == "NOT_EQUIVALENT"]; ok = [r for r in ne if lab(r) == "NOT_EQUIVALENT"]
    print("  NOT_EQUIVALENT precision:", pct(len(ok), len(ne)), " recall:", pct(len(ok), sum(lab(r) == "NOT_EQUIVALENT" for r in rows)),
          " proven equivalent:", pct(sum(sem[r['id']].verdict == 'EQUIVALENT' for r in eq), len(eq)))
    if judges_raw:
        print("\n[ARBITER 2-of-2 alone]")
        print("  false-SAME:", pct(sum(arb[r['id']] == 'SAME' for r in non_eq), len(non_eq)), "ids:", [r["id"] for r in non_eq if arb[r["id"]] == "SAME"])
        print("  SAME on equivalent:", pct(sum(arb[r['id']] == 'SAME' for r in eq), len(eq)))
        print("\n[H] HYBRID")
        hs = [r for r in non_eq if hyb[r["id"]].verdict == "SAME"]
        print("  [H1] false-SAME:", pct(len(hs), len(non_eq)), "ids:", [r["id"] for r in hs])
        print("  [H2] SAME on equivalent:", pct(sum(hyb[r['id']].verdict == 'SAME' for r in eq), len(eq)))
        rv = [r for r in rows if hyb[r["id"]].verdict == "REVIEW"]
        print("  REVIEW:", len(rv), "-> truly non-equivalent (veto was right):", sum(lab(r) != "EQUIVALENT" for r in rv), " truly equivalent (FALSE veto):", sum(lab(r) == "EQUIVALENT" for r in rv))
        print("  verdict x label:", dict(collections.Counter((lab(r)[:5], hyb[r["id"]].verdict) for r in rows)))

        # ---- ambiguity-rule accounting (pre-registered claim policy)
        amb_rv = [r for r in rows if hyb[r["id"]].verdict == "REVIEW" and hyb[r["id"]].semantic.verdict == "INCONCLUSIVE"]
        benefit = [r for r in non_eq if arb[r["id"]] == "SAME" and hyb[r["id"]].verdict == "REVIEW"]
        cost = [r for r in eq if arb[r["id"]] == "SAME" and hyb[r["id"]].verdict == "REVIEW"]
        arb_fs = [r for r in non_eq if arb[r["id"]] == "SAME"]; hyb_fs = [r for r in non_eq if hyb[r["id"]].verdict == "SAME"]
        print("\n[RULE] ambiguity veto")
        print("  [R1] hybrid false-SAME", pct(len(hyb_fs), len(non_eq)), "vs arbiter alone", pct(len(arb_fs), len(non_eq)), "-> hybrid <= arbiter:", len(hyb_fs) <= len(arb_fs))
        print("  [R2] hybrid SAME on equivalent:", pct(sum(hyb[r['id']].verdict == 'SAME' for r in eq), len(eq)))
        print("  [R3] REVIEW caused by the ambiguity rule:", len(amb_rv), "-> truly not-equivalent/undecidable:", sum(lab(r) != "EQUIVALENT" for r in amb_rv), pct(sum(lab(r) != "EQUIVALENT" for r in amb_rv), len(amb_rv)))
        print("  BENEFIT (arbiter false-SAME turned into REVIEW by any veto):", len(benefit), [r["id"] for r in benefit])
        print("  COST (true SAME turned into REVIEW):", len(cost), [r["id"] for r in cost])
        r1 = len(hyb_fs) <= 0.05 * len(non_eq) and len(hyb_fs) <= len(arb_fs)
        r2 = sum(hyb[r['id']].verdict == 'SAME' for r in eq) >= 0.85 * len(eq)
        r3 = (not amb_rv) or sum(lab(r) != "EQUIVALENT" for r in amb_rv) >= 0.6 * len(amb_rv)
        print(f"  gates: R1={r1} R2={r2} R3={r3}; benefit>0={len(benefit) >= 1}")
        print("  claim 'hybrid safer than arbiter alone' allowed (pre-registered policy: benefit>0 AND R1 AND R2 AND R3):", len(benefit) >= 1 and r1 and r2 and r3)
        if "--show" in sys.argv:
            for r in rows:
                h = hyb[r["id"]]
                if (lab(r) != "EQUIVALENT" and h.verdict == "SAME") or (lab(r) == "EQUIVALENT" and h.verdict in ("REVIEW", "DIFFERENT")) or (lab(r) != "EQUIVALENT" and sem[r["id"]].verdict == "EQUIVALENT"):
                    print(f"   {r['id']} {r.get('family','')[:14]:14} lab={lab(r)[:5]} sem={sem[r['id']].verdict[:6]} arb={arb[r['id']][:5]} hyb={h.verdict} | {r['text_a']} | {r['text_b']}")
