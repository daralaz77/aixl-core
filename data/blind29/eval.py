"""blind29 one-shot PAIRED evaluation (see PREREG.md): OLD comparator (commit 933fb76) vs NEW comparator (frozen working tree) on the same fresh pairs, plus two blind Claude judges.
Refuses to run if frozen code or author files changed, and refuses a second run once RESULT_run1.txt exists.  usage: python3 -I eval.py"""
import collections
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.abspath(os.path.join(HERE, "..", ".."))
OLD = os.environ.get("AIXL_OLD_CODE", os.path.join(HERE, "oldcode"))   # `git archive 933fb76 aixl` extracted here
frz = json.load(open(os.path.join(HERE, "CODE_FREEZE.json")))
for tag, root in (("new", NEW), ("old", OLD)):
    for f, h in frz[tag].items():
        assert hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest() == h, f"{tag}:{f} changed after the freeze: blind29 is void"
man = json.load(open(os.path.join(HERE, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(HERE, "authors", n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind29 was already run once (RESULT_run1.txt exists): the set is SPENT")

rows = [json.loads(line) for n in man for line in open(os.path.join(HERE, "authors", n), encoding="utf-8") if line.strip()]
key = json.load(open(os.path.join(HERE, "judge_key.json")))
inv = {v: k for k, v in key.items()}
J = {}
for m in ("opus", "sonnet"):
    J[m] = {}
    for line in open(os.path.join(HERE, "judge", f"{m}.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2:
            J[m][p[0]] = p[1].strip().upper()
    bad = [q for q in key if J[m].get(q) not in ("SAME", "DIFFERENT", "UNSURE")]
    assert not bad, f"judge {m}: missing/invalid {bad[:5]}"

RUN = ("import sys,json\nsys.path.insert(0,sys.argv[1])\nfrom aixl.semantic import compare_texts\n"
       "d=json.load(sys.stdin)\nprint(json.dumps({k:compare_texts(a,b).verdict for k,(a,b) in d.items()}))\n")


def verdicts(root):
    payload = json.dumps({r["id"]: [r["text_a"], r["text_b"]] for r in rows})
    out = subprocess.run([sys.executable, "-I", "-c", RUN, root], input=payload, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


old, new = verdicts(OLD), verdicts(NEW)
for r in rows:
    q = inv[r["id"]]
    r["o"], r["s"] = J["opus"][q], J["sonnet"][q]
    r["old"], r["new"] = old[r["id"]], new[r["id"]]
lab = lambda r: r["expected_equivalence"]  # noqa: E731
ne = [r for r in rows if lab(r) != "EQUIVALENT"]
eq = [r for r in rows if lab(r) == "EQUIVALENT"]
pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"  # noqa: E731
print(f"SET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}  authors {dict(collections.Counter(r['id'][0] for r in rows))}")
print(f"OLD verdicts {dict(collections.Counter(r['old'] for r in rows))}")
print(f"NEW verdicts {dict(collections.Counter(r['new'] for r in rows))}")
print("judge verdicts: " + "  ".join(f"{m} {dict(collections.Counter(J[m].values()))}" for m in J))
S = lambda r, k: r[k] == "SAME"  # noqa: E731
rules = {
    "OLD comparator alone": lambda r: r["old"] == "EQUIVALENT",
    "NEW comparator alone": lambda r: r["new"] == "EQUIVALENT",
    "R1-new: NEW AND opus AND sonnet SAME": lambda r: r["new"] == "EQUIVALENT" and S(r, "o") and S(r, "s"),
    "R1-old: OLD AND opus AND sonnet SAME": lambda r: r["old"] == "EQUIVALENT" and S(r, "o") and S(r, "s"),
    "both judges SAME": lambda r: S(r, "o") and S(r, "s"),
    "opus alone": lambda r: S(r, "o"),
    "sonnet alone": lambda r: S(r, "s"),
}
fa, tp = {}, {}
print()
for name, rule in rules.items():
    fa[name] = {r["id"] for r in ne if rule(r)}
    tp[name] = {r["id"] for r in eq if rule(r)}
    print(f"{name:42s} false accepts {pct(len(fa[name]), len(ne)):14s} proven-EQUIVALENT {pct(len(tp[name]), len(eq))}")
wrong = lambda k: sum(1 for r in eq if r[k] == "NOT_EQUIVALENT")  # noqa: E731
print(f"wrong NOT_EQUIVALENT on EQUIVALENT-labelled: OLD {wrong('old')}  NEW {wrong('new')}")
fo, fn = fa["OLD comparator alone"], fa["NEW comparator alone"]
po, pn = tp["OLD comparator alone"], tp["NEW comparator alone"]
print(f"\n[paired recall] newly proven by NEW {len(pn - po)}, lost {len(po - pn)}, net {len(pn) - len(po)}")
print(f"[paired safety] new false accepts (NEW only) {len(fn - fo)} {sorted(fn - fo)}, false accepts removed (OLD only) {len(fo - fn)} {sorted(fo - fn)}")
rec = (len(pn) - len(po)) >= 5 and len(fn - fo) == 0
saf = len(fn) < len(fo) and len(fn - fo) == 0
g1 = len(fn) <= 0.03 * len(ne)
print(f"[RULE recall] NEW proves >= 5 more equivalents with 0 new false accepts -> {'HOLDS' if rec else 'DOES NOT HOLD'}")
print(f"[RULE safety] NEW has fewer false accepts than OLD and none new -> {'HOLDS' if saf else 'DOES NOT HOLD'}")
r1n = tp["R1-new: NEW AND opus AND sonnet SAME"]
print(f"[G1 NEW] false accepts {len(fn)} of {len(ne)} (<= {int(0.03 * len(ne))}) -> {'PASS' if g1 else 'FAIL'}; R1-new false {len(fa['R1-new: NEW AND opus AND sonnet SAME'])}, proven {len(r1n)} (floor 10: {'ok' if len(r1n) >= 10 else 'VACUOUS'})")
ids_new = {r["id"]: r for r in rows}
print("\nNEW false accepts:")
for i in sorted(fn):
    r = ids_new[i]
    print(f"  {i} [{lab(r)}] {r['text_a']} || {r['text_b']} | author: {r['what_differs']} | OLD said {r['old']}")
print("\nnewly proven by NEW:")
for i in sorted(pn - po):
    r = ids_new[i]
    print(f"  {i} {r['text_a']} || {r['text_b']}")
print("\nlost by NEW:")
for i in sorted(po - pn):
    r = ids_new[i]
    print(f"  {i} {r['text_a']} || {r['text_b']} | NEW said {r['new']}")
print("\n[construct] eq proven OLD -> NEW | false OLD -> NEW")
for fam in sorted({r["family"] for r in rows}):
    ee = [r for r in eq if r["family"] == fam]
    nn = [r for r in ne if r["family"] == fam]
    print(f"  {fam:30s} {sum(1 for r in ee if r['old'] == 'EQUIVALENT')}/{len(ee)} -> {sum(1 for r in ee if r['new'] == 'EQUIVALENT')}/{len(ee)} | {sum(1 for r in nn if r['old'] == 'EQUIVALENT')} -> {sum(1 for r in nn if r['new'] == 'EQUIVALENT')}")
