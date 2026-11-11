"""blind30 one-shot PAIRED evaluation (see PREREG.md): OLD comparator (v0.7.0) vs NEW comparator (frozen working tree) on the same fresh pairs, plus two blind Claude judges.
Reports overall, for the two TARGETED constructs and for the EIGHT OTHER constructs. Refuses to run if frozen code or author files changed, and refuses a second run once
RESULT_run1.txt exists.  usage: python3 -I eval.py"""
import collections
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.abspath(os.path.join(HERE, "..", ".."))
OLD = os.environ.get("AIXL_OLD_CODE", os.path.join(HERE, "oldcode"))   # `git archive v0.7.0 aixl` extracted here
TARGET = {"word_order_voice", "quantifier_all_each_any"}
frz = json.load(open(os.path.join(HERE, "CODE_FREEZE.json")))
for tag, root in (("new", NEW), ("old", OLD)):
    for f, h in frz[tag].items():
        assert hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest() == h, f"{tag}:{f} changed after the freeze: blind30 is void"
man = json.load(open(os.path.join(HERE, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(HERE, "authors", n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind30 was already run once (RESULT_run1.txt exists): the set is SPENT")

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
    r["target"] = r["family"] in TARGET
lab = lambda r: r["expected_equivalence"]  # noqa: E731
pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"  # noqa: E731
S = lambda r, k: r[k] == "SAME"  # noqa: E731
print(f"SET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}  authors {dict(collections.Counter(r['id'][0] for r in rows))}  targeted {sum(r['target'] for r in rows)}")
print(f"OLD verdicts {dict(collections.Counter(r['old'] for r in rows))}")
print(f"NEW verdicts {dict(collections.Counter(r['new'] for r in rows))}")
print("judge verdicts: " + "  ".join(f"{m} {dict(collections.Counter(J[m].values()))}" for m in J))


def block(title, sub):
    ne = [r for r in sub if lab(r) != "EQUIVALENT"]
    eq = [r for r in sub if lab(r) == "EQUIVALENT"]
    rules = {"OLD comparator alone": lambda r: r["old"] == "EQUIVALENT", "NEW comparator alone": lambda r: r["new"] == "EQUIVALENT",
             "R1-new: NEW AND opus AND sonnet SAME": lambda r: r["new"] == "EQUIVALENT" and S(r, "o") and S(r, "s"),
             "both judges SAME": lambda r: S(r, "o") and S(r, "s")}
    fa, tp = {}, {}
    print(f"\n=== {title}: {len(sub)} pairs, {len(eq)} EQUIVALENT-labelled, {len(ne)} non-EQUIVALENT-labelled")
    for name, rule in rules.items():
        fa[name] = {r["id"] for r in ne if rule(r)}
        tp[name] = {r["id"] for r in eq if rule(r)}
        print(f"  {name:40s} false accepts {pct(len(fa[name]), len(ne)):14s} proven-EQUIVALENT {pct(len(tp[name]), len(eq))}")
    po, pn = tp["OLD comparator alone"], tp["NEW comparator alone"]
    fo, fn = fa["OLD comparator alone"], fa["NEW comparator alone"]
    print(f"  [paired] newly proven {len(pn - po)}, lost {len(po - pn)}, net {len(pn) - len(po)}; new false accepts {len(fn - fo)} {sorted(fn - fo)}; false accepts removed {len(fo - fn)} {sorted(fo - fn)}")
    return po, pn, fo, fn, fa, tp, ne


allr = block("ALL", rows)
tgt = block("TARGETED constructs (word_order_voice + quantifier_all_each_any)", [r for r in rows if r["target"]])
oth = block("EIGHT OTHER constructs", [r for r in rows if not r["target"]])
net_t = len(tgt[1]) - len(tgt[0])
new_fa_all = allr[3] - allr[2]
lost_o = len(oth[0] - oth[1])
rec = net_t >= 5 and not new_fa_all
noh = not (oth[3] - oth[2]) and lost_o <= 1
saf = not new_fa_all
print(f"\n[R-recall] targeted net {net_t} (needs >= 5) and 0 new false accepts overall ({len(new_fa_all)}) -> {'HOLDS' if rec else 'DOES NOT HOLD'}")
print(f"[R-noharm] other constructs: new false accepts {len(oth[3] - oth[2])}, lost proven {lost_o} (needs 0 and <= 1) -> {'HOLDS' if noh else 'DOES NOT HOLD'}")
print(f"[R-safety] NEW adds no false accept anywhere -> {'HOLDS' if saf else 'DOES NOT HOLD'}")
nne = len(allr[6])
print(f"[G1 NEW] false accepts {len(allr[3])} of {nne} (3% = {0.03 * nne:.1f}) -> {'PASS' if len(allr[3]) <= 0.03 * nne else 'FAIL'}; R1-new false {len(allr[4]['R1-new: NEW AND opus AND sonnet SAME'])}, proven {len(allr[5]['R1-new: NEW AND opus AND sonnet SAME'])} (floor 10)")
ids = {r["id"]: r for r in rows}
print("\nNEW false accepts:")
for i in sorted(allr[3]):
    r = ids[i]
    print(f"  {i} [{lab(r)}] {r['family']} | {r['text_a']} || {r['text_b']} | author: {r['what_differs']} | OLD said {r['old']}")
print("\nnewly proven by NEW:")
for i in sorted(allr[1] - allr[0]):
    r = ids[i]
    print(f"  {i} {r['family']} | {r['text_a']} || {r['text_b']}")
print("\nlost by NEW:")
for i in sorted(allr[0] - allr[1]):
    r = ids[i]
    print(f"  {i} {r['family']} | {r['text_a']} || {r['text_b']} | NEW said {r['new']}")
print("\n[construct] EQUIVALENT proven OLD -> NEW | false accepts OLD -> NEW")
for fam in sorted({r["family"] for r in rows}):
    ee = [r for r in rows if r["family"] == fam and lab(r) == "EQUIVALENT"]
    nn = [r for r in rows if r["family"] == fam and lab(r) != "EQUIVALENT"]
    print(f"  {fam:30s} {sum(1 for r in ee if r['old'] == 'EQUIVALENT')}/{len(ee)} -> {sum(1 for r in ee if r['new'] == 'EQUIVALENT')}/{len(ee)} | {sum(1 for r in nn if r['old'] == 'EQUIVALENT')} -> {sum(1 for r in nn if r['new'] == 'EQUIVALENT')}")
