"""blind33 one-shot THREE-WAY paired evaluation (see PREREG.md). usage: python3 -I eval.py  (env AIXL_V071, AIXL_P0005 point at the two baseline trees; NEW is this repository)
Refuses to run if frozen code or author files changed, and refuses a second run once RESULT_run1.txt exists."""
import collections
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREES = {"v071": os.environ["AIXL_V071"], "p0005": os.environ["AIXL_P0005"], "new": os.path.abspath(os.path.join(HERE, "..", ".."))}
frz = json.load(open(os.path.join(HERE, "CODE_FREEZE.json")))
for tag, root in TREES.items():
    for f, h in frz[tag].items():
        assert hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest() == h, f"{tag}:{f} changed after the freeze: blind33 is void"
man = json.load(open(os.path.join(HERE, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(HERE, "authors", n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind33 was already run once (RESULT_run1.txt exists): the set is SPENT")
rows = [json.loads(line) for n in man for line in open(os.path.join(HERE, "authors", n), encoding="utf-8") if line.strip()]
RUN = ("import sys,json\nsys.path.insert(0,sys.argv[1])\nfrom aixl.semantic import compare_texts\n"
       "d=json.load(sys.stdin)\nprint(json.dumps({k:[compare_texts(a,b).verdict,compare_texts(b,a).verdict] for k,(a,b) in d.items()}))\n")
payload = json.dumps({r["id"]: [r["text_a"], r["text_b"]] for r in rows})
V = {t: json.loads(subprocess.run([sys.executable, "-I", "-c", RUN, root], input=payload, capture_output=True, text=True, check=True).stdout) for t, root in TREES.items()}
lab = lambda r: r["expected_equivalence"]  # noqa: E731
acc = lambda t, r: "EQUIVALENT" in V[t][r["id"]]  # noqa: E731
proven = lambda t, r: V[t][r["id"]] == ["EQUIVALENT", "EQUIVALENT"]  # noqa: E731
ne = [r for r in rows if lab(r) != "EQUIVALENT"]
eq = [r for r in rows if lab(r) == "EQUIVALENT"]
print(f"SET {len(rows)} pairs: {len(eq)} EQUIVALENT-labelled, {len(ne)} NOT_EQUIVALENT-labelled; languages {dict(collections.Counter(r['language'] for r in rows))}")


def table(title, sub):
    n_, e_ = [r for r in sub if lab(r) != "EQUIVALENT"], [r for r in sub if lab(r) == "EQUIVALENT"]
    print(f"\n== {title}: {len(e_)} EQ / {len(n_)} NE")
    for t in TREES:
        print(f"  {t:6s} false accepts {sum(acc(t, r) for r in n_):3d}/{len(n_)}   proven {sum(proven(t, r) for r in e_):3d}/{len(e_)}")


table("ALL", rows)
for lg in ("en", "es", "pt"):
    table(f"language {lg}", [r for r in rows if r["language"] == lg])
for fam in sorted({r["family"] for r in rows}):
    table(f"family {fam}", [r for r in rows if r["family"] == fam])
fa = {t: {r["id"] for r in ne if acc(t, r)} for t in TREES}
pr = {t: {r["id"] for r in eq if proven(t, r)} for t in TREES}
new_fa = fa["new"] - fa["p0005"] - fa["v071"]
print(f"\n[R-safety]  NEW false accepts not already in P0005/V071: {len(new_fa)} {sorted(new_fa)} -> {'HOLDS' if not new_fa else 'DOES NOT HOLD'}")
print(f"[R-binding] NEW {len(fa['new'])} <= P0005 {len(fa['p0005'])} -> {'HOLDS' if len(fa['new']) <= len(fa['p0005']) else 'DOES NOT HOLD'}")
gain, lost = pr["new"] - pr["p0005"], pr["p0005"] - pr["new"]
print(f"[R-recall]  NEW proven {len(pr['new'])} - P0005 {len(pr['p0005'])} = {len(pr['new']) - len(pr['p0005'])} (needs >= +3) -> {'HOLDS' if len(pr['new']) - len(pr['p0005']) >= 3 else 'DOES NOT HOLD'}")
print(f"[R-loss]    NEW loses {len(lost)} (allowed <= 2) -> {'HOLDS' if len(lost) <= 2 else 'DOES NOT HOLD'}")
print(f"[V071 -> NEW] proven {len(pr['v071'])} -> {len(pr['new'])}; false accepts {len(fa['v071'])} -> {len(fa['new'])}")
ids = {r["id"]: r for r in rows}
for title, s_ in (("NEW false accepts", fa["new"]), ("P0005 false accepts", fa["p0005"]), ("V071 false accepts", fa["v071"])):
    print(f"\n{title}:")
    for i in sorted(s_):
        r = ids[i]; print(f"  {i} {r['language']} {r['family']} | {r['text_a']} || {r['text_b']} | author: {r['what_differs']}")
print("\nnewly proven by NEW (vs P0005):")
for i in sorted(gain): print(f"  {i} {ids[i]['language']} | {ids[i]['text_a']} || {ids[i]['text_b']}")
print("\nlost by NEW (vs P0005):")
for i in sorted(lost): print(f"  {i} {ids[i]['language']} | {ids[i]['text_a']} || {ids[i]['text_b']} | NEW said {V['new'][i]}")
print("\nunproven by NEW (EQ-labelled):")
for r in eq:
    if not proven("new", r): print(f"  {r['id']} {r['language']} {r['family']} | {r['text_a']} || {r['text_b']} | {V['new'][r['id']]}")
