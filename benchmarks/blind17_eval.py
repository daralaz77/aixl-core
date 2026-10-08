"""blind17 (short) one-shot evaluation: semantic alone | arbiter 2-of-2 alone | HYBRID (see data/blind17/PREREG.md).
Refuses to run if the frozen code/rules changed or the pair files changed. Judge verdicts come from stored TSVs (data/blind17/judge_<name>.tsv),
produced by two independent agents that saw only rules_v1.txt and (id, a, b).
usage: python -m benchmarks.blind17_eval [--show]"""
import collections
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(ROOT, "data", "blind17")
for f, h in json.load(open(os.path.join(D, "CODE_FREEZE.json"))).items():
    assert hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind17 is void"
man = json.load(open(os.path.join(D, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(D, n), "rb").read()).hexdigest() == h, f"{n} changed"
from aixl import arbiter
from aixl.semantic import compare_texts, hybrid_decide

rows = [json.loads(l) for f in man if f.startswith("author") for l in open(os.path.join(D, f), encoding="utf-8")]
ids = [r["id"] for r in rows]
judges_raw = {}
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

def pct(a, b): return f"{a}/{b} ({100*a/max(b,1):.1f}%)"
print(f"\nSET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}")
fe = [r for r in non_eq if sem[r["id"]].verdict == "EQUIVALENT"]
print("\n[S1] SEMANTIC alone")
print("  false-equivalent:", pct(len(fe), len(non_eq)), "ids:", [r["id"] for r in fe])
for fam in ("gender_pronoun", "explicit_vs_bare_order"):
    fr = [r for r in rows if r.get("family") == fam and lab(r) != "EQUIVALENT"]
    print(f"  family {fam}: false-equivalent {sum(sem[r['id']].verdict=='EQUIVALENT' for r in fr)}/{len(fr)}")
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
    if "--show" in sys.argv:
        for r in rows:
            h = hyb[r["id"]]
            if (lab(r) != "EQUIVALENT" and h.verdict == "SAME") or (lab(r) == "EQUIVALENT" and h.verdict in ("REVIEW", "DIFFERENT")) or (lab(r) != "EQUIVALENT" and sem[r["id"]].verdict == "EQUIVALENT"):
                print(f"   {r['id']} {r.get('family','')[:14]:14} lab={lab(r)[:5]} sem={sem[r['id']].verdict[:6]} arb={arb[r['id']][:5]} hyb={h.verdict} | {r['text_a']} | {r['text_b']}")
