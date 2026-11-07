"""blind26 one-shot evaluation (see PREREG.md). Refuses to run if the frozen code or pair files changed, and refuses a second run once RESULT_run1.txt exists.
usage: python3 -I eval.py"""
import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from aixl.semantic import compare_texts  # noqa: E402

for f, h in json.load(open(os.path.join(HERE, "CODE_FREEZE.json"))).items():
    assert hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind26 is void"
man = json.load(open(os.path.join(HERE, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(HERE, n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind26 was already run once (RESULT_run1.txt exists): the set is SPENT")

rows = [json.loads(l) for n in man for l in open(os.path.join(HERE, n), encoding="utf-8") if l.strip()]
key = json.load(open(os.path.join(HERE, "judge_key.json")))          # Q id -> pair id
inv = {v: k for k, v in key.items()}
J = {}
for m in ("opus", "sonnet"):
    J[m] = {}
    for l in open(os.path.join(HERE, "judge", f"{m}.tsv"), encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 2:
            J[m][p[0]] = p[1].strip().upper()
    bad = [q for q in key if J[m].get(q) not in ("SAME", "DIFFERENT", "UNSURE")]
    assert not bad, f"judge {m}: missing/invalid {bad[:5]}"

S = lambda m, r: J[m][inv[r["id"]]] == "SAME"
lab = lambda r: r["expected_equivalence"]
base = {r["id"]: compare_texts(r["text_a"], r["text_b"]) for r in rows}
strict = {r["id"]: compare_texts(r["text_a"], r["text_b"], strict=True) for r in rows}
non_eq = [r for r in rows if lab(r) != "EQUIVALENT"]
eq = [r for r in rows if lab(r) == "EQUIVALENT"]
pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"

print(f"SET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}  comparator verdicts {dict(collections.Counter(v.verdict for v in base.values()))}")
print("judge verdicts: " + "  ".join(f"{m} {dict(collections.Counter(J[m].values()))}" for m in J))
rules = {
    "R0 comparator alone": lambda r: base[r["id"]].verdict == "EQUIVALENT",
    "R1 comparator AND both judges SAME (PRIMARY)": lambda r: base[r["id"]].verdict == "EQUIVALENT" and S("opus", r) and S("sonnet", r),
    "R2 strict comparator AND both judges SAME": lambda r: strict[r["id"]].verdict == "EQUIVALENT" and S("opus", r) and S("sonnet", r),
    "judge opus alone": lambda r: S("opus", r),
    "judge sonnet alone": lambda r: S("sonnet", r),
    "both judges SAME": lambda r: S("opus", r) and S("sonnet", r),
}
fa_ids = {}
print()
for name, rule in rules.items():
    fa = [r for r in non_eq if rule(r)]
    tp = [r for r in eq if rule(r)]
    fa_ids[name] = {r["id"] for r in fa}
    print(f"{name:48s} false accepts {pct(len(fa), len(non_eq)):14s} proven-EQUIVALENT {pct(len(tp), len(eq))}   ids {[r['id'] for r in fa]}")
g1 = len(fa_ids["R1 comparator AND both judges SAME (PRIMARY)"]) <= 0.03 * len(non_eq)
print(f"\n[G1] R1 false accepts <= 3% of {len(non_eq)} non-EQUIVALENT-labelled pairs (<= {int(0.03 * len(non_eq))}) -> {'PASS' if g1 else 'FAIL'}")
c, j = fa_ids["R0 comparator alone"], fa_ids["both judges SAME"]
exp = len(c) * len(j) / max(len(non_eq), 1)
print(f"[overlap] comparator false accepts {len(c)}, both-judges false SAME {len(j)}, in common {len(c & j)} (expected if independent {exp:.1f})")
po = len(fa_ids["judge opus alone"]) / len(non_eq)
ps = len(fa_ids["judge sonnet alone"]) / len(non_eq)
print(f"[judge correlation] both SAME on non-EQ {len(j)} vs {po * ps * len(non_eq):.1f} expected if independent")
print("\n[family] R0 false | judges-both false | R1 false | n")
for fam in sorted({r["family"] for r in rows}):
    rs = [r for r in non_eq if r["family"] == fam]
    ids = lambda name, rs=rs: sum(1 for r in rs if r["id"] in fa_ids[name])  # noqa: E731
    print(f"  {fam:36s} {ids('R0 comparator alone')} | {ids('both judges SAME')} | {ids('R1 comparator AND both judges SAME (PRIMARY)')} | {sum(1 for r in rows if r['family'] == fam)}")
print("\nR1 false-accept pairs:")
for r in non_eq:
    if r["id"] in fa_ids["R1 comparator AND both judges SAME (PRIMARY)"]:
        print(f"  {r['id']} [{lab(r)}] {r['text_a']} || {r['text_b']} | author: {r['what_differs']}")
print(f"\nCLAIM 'comparator AND two judges does not accept non-equivalent pairs on new families (G1)': {'ALLOWED (narrow wording, with proven-EQUIVALENT recall and the rule-of-three note)' if g1 else 'NOT ALLOWED'}")
