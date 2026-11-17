"""blind32 one-shot PAIRED evaluation (see PREREG.md): OLD comparator (main 04e9574) vs NEW comparator (frozen tree) on the same fresh bounds pairs. No judges.
Refuses to run if frozen code or author files changed, and refuses a second run once RESULT_run1.txt exists.  usage: python3 -I eval.py"""
import collections
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.abspath(os.path.join(HERE, "..", ".."))
OLD = os.environ.get("AIXL_OLD_CODE", os.path.join(HERE, "oldcode"))
frz = json.load(open(os.path.join(HERE, "CODE_FREEZE.json")))
for tag, root in (("new", NEW), ("old", OLD)):
    for f, h in frz[tag].items():
        assert hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest() == h, f"{tag}:{f} changed after the freeze: blind32 is void"
man = json.load(open(os.path.join(HERE, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(HERE, "authors", n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind32 was already run once (RESULT_run1.txt exists): the set is SPENT")

rows = [json.loads(line) for n in man for line in open(os.path.join(HERE, "authors", n), encoding="utf-8") if line.strip()]
RUN = ("import sys,json\nsys.path.insert(0,sys.argv[1])\nfrom aixl.semantic import compare_texts\n"
       "d=json.load(sys.stdin)\nprint(json.dumps({k:compare_texts(a,b).verdict for k,(a,b) in d.items()}))\n")


def verdicts(root):
    payload = json.dumps({r["id"]: [r["text_a"], r["text_b"]] for r in rows})
    out = subprocess.run([sys.executable, "-I", "-c", RUN, root], input=payload, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def verdicts_swapped(root):
    payload = json.dumps({r["id"]: [r["text_b"], r["text_a"]] for r in rows})
    out = subprocess.run([sys.executable, "-I", "-c", RUN, root], input=payload, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


old, new, old2, new2 = verdicts(OLD), verdicts(NEW), verdicts_swapped(OLD), verdicts_swapped(NEW)
for r in rows:
    r["old"] = "EQUIVALENT" if "EQUIVALENT" in (old[r["id"]], old2[r["id"]]) else old[r["id"]]      # either direction accepting counts as an accept (conservative for safety)
    r["new"] = "EQUIVALENT" if "EQUIVALENT" in (new[r["id"]], new2[r["id"]]) else new[r["id"]]
    r["nfw"] = "no fewer than" in (r["text_a"] + " " + r["text_b"]).lower()
lab = lambda r: r["expected_equivalence"]  # noqa: E731
pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"  # noqa: E731
print(f"SET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}  languages {dict(collections.Counter(r['language'] for r in rows))}  authors {dict(collections.Counter(r['id'][0] for r in rows))}  with 'no fewer than': {sum(r['nfw'] for r in rows)}")
print(f"OLD verdicts {dict(collections.Counter(r['old'] for r in rows))}")
print(f"NEW verdicts {dict(collections.Counter(r['new'] for r in rows))}")


def block(title, sub):
    ne = [r for r in sub if lab(r) != "EQUIVALENT"]
    eq = [r for r in sub if lab(r) == "EQUIVALENT"]
    fo, fn = {r["id"] for r in ne if r["old"] == "EQUIVALENT"}, {r["id"] for r in ne if r["new"] == "EQUIVALENT"}
    po, pn = {r["id"] for r in eq if r["old"] == "EQUIVALENT"}, {r["id"] for r in eq if r["new"] == "EQUIVALENT"}
    print(f"\n=== {title}: {len(sub)} pairs, {len(eq)} EQUIVALENT-labelled, {len(ne)} non-EQUIVALENT-labelled")
    print(f"  OLD false accepts {pct(len(fo), len(ne)):14s} proven-EQUIVALENT {pct(len(po), len(eq))}")
    print(f"  NEW false accepts {pct(len(fn), len(ne)):14s} proven-EQUIVALENT {pct(len(pn), len(eq))}")
    print(f"  [paired] newly proven {len(pn - po)}, lost {len(po - pn)}, net {len(pn) - len(po)}; new false accepts {len(fn - fo)} {sorted(fn - fo)}; false accepts removed {len(fo - fn)} {sorted(fo - fn)}")
    return po, pn, fo, fn, ne


allr = block("ALL", rows)
for lg in ("en", "es", "pt"):
    block(f"language {lg}", [r for r in rows if r["language"] == lg])
block("pairs containing 'no fewer than'", [r for r in rows if r["nfw"]])
net = len(allr[1]) - len(allr[0])
new_fa = allr[3] - allr[2]
print(f"\n[R-recall] net {net} (needs >= 2) and 0 new false accepts ({len(new_fa)}) -> {'HOLDS' if net >= 2 and not new_fa else 'DOES NOT HOLD'}")
print(f"[R-safety] NEW adds no false accept -> {'HOLDS' if not new_fa else 'DOES NOT HOLD'}")
nne = len(allr[4])
print(f"[G1 NEW] false accepts {len(allr[3])} of {nne} (3% = {0.03 * nne:.1f}, bound 1) -> {'PASS' if len(allr[3]) <= max(1, 0.03 * nne) else 'FAIL'}")
ids = {r["id"]: r for r in rows}
print("\nNEW false accepts:")
for i in sorted(allr[3]):
    r = ids[i]
    print(f"  {i} [{lab(r)}] {r['language']} | {r['text_a']} || {r['text_b']} | author: {r['what_differs']} | OLD said {r['old']}")
print("\nnewly proven by NEW:")
for i in sorted(allr[1] - allr[0]):
    r = ids[i]
    print(f"  {i} {r['language']} | {r['text_a']} || {r['text_b']}")
print("\nlost by NEW:")
for i in sorted(allr[0] - allr[1]):
    r = ids[i]
    print(f"  {i} {r['language']} | {r['text_a']} || {r['text_b']} | NEW said {r['new']}")
