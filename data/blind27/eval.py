"""blind27 one-shot evaluation (see PREREG.md). Refuses to run if frozen code or the pair file changed, and refuses a second run once RESULT_run1.txt exists.
usage: python3 -I eval.py"""
import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from aixl.hybrid_protocol import decide  # noqa: E402
from aixl.semantic import compare_texts  # noqa: E402

for f, h in json.load(open(os.path.join(HERE, "CODE_FREEZE.json"))).items():
    assert hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind27 is void"
for n, h in json.load(open(os.path.join(HERE, "MANIFEST.json"))).items():
    assert hashlib.sha256(open(os.path.join(HERE, n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind27 was already run once (RESULT_run1.txt exists): the set is SPENT")

pairs = json.load(open(os.path.join(HERE, "pairs.json"), encoding="utf-8"))
key = json.load(open(os.path.join(HERE, "judge_key.json")))
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
for p in pairs:
    p["o"], p["s"] = J["opus"][inv[p["id"]]], J["sonnet"][inv[p["id"]]]
    p["c"] = compare_texts(p["a"], p["b"]).verdict
    p["h"] = decide(p["a"], p["b"], {"opus": p["o"], "sonnet": p["s"]})["verdict"]
    p["hs"] = decide(p["a"], p["b"], {"opus": p["o"], "sonnet": p["s"]}, strict=True)["verdict"]

ne = [p for p in pairs if p["label"] != "EQUIVALENT"]
eq = [p for p in pairs if p["label"] == "EQUIVALENT"]
pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"
print(f"SET: {len(pairs)} pairs  labels {dict(collections.Counter(p['label'] for p in pairs))}  by source {dict(collections.Counter(p['sub'] for p in pairs))}")
print(f"comparator verdicts {dict(collections.Counter(p['c'] for p in pairs))}")
print("judge verdicts: " + "  ".join(f"{m} {dict(collections.Counter(J[m].values()))}" for m in J))
rules = {
    "R0 comparator alone": lambda p: p["c"] == "EQUIVALENT",
    "R1 comparator AND both judges SAME (PRIMARY)": lambda p: p["c"] == "EQUIVALENT" and p["o"] == "SAME" and p["s"] == "SAME",
    "strict hybrid = SAME": lambda p: p["hs"] == "SAME",
    "default hybrid = SAME": lambda p: p["h"] == "SAME",
    "both judges SAME": lambda p: p["o"] == "SAME" and p["s"] == "SAME",
    "judge opus alone": lambda p: p["o"] == "SAME",
    "judge sonnet alone": lambda p: p["s"] == "SAME",
}
fa_ids, tp_n = {}, {}
print()
for name, rule in rules.items():
    fa = [p for p in ne if rule(p)]
    tp = [p for p in eq if rule(p)]
    fa_ids[name] = {p["id"] for p in fa}
    tp_n[name] = len(tp)
    print(f"{name:46s} false accepts {pct(len(fa), len(ne)):14s} proven-EQUIVALENT {pct(len(tp), len(eq))}")
r1 = "R1 comparator AND both judges SAME (PRIMARY)"
within = len(fa_ids[r1]) <= 0.03 * len(ne)
vacuous = tp_n[r1] < 10
g1 = "VACUOUS (R1 proves fewer than 10 equivalent pairs)" if vacuous else ("PASS" if within else "FAIL")
print(f"\n[G1] R1 false accepts <= 3% of {len(ne)} NOT_EQUIVALENT pairs (<= {int(0.03 * len(ne))}); proven-EQUIVALENT {tp_n[r1]} (floor 10) -> {g1}   ids {sorted(fa_ids[r1])}")
c, j = fa_ids["R0 comparator alone"], fa_ids["both judges SAME"]
print(f"[overlap] comparator false accepts {len(c)}, both-judges false SAME {len(j)}, in common {len(c & j)} (expected if independent {len(c) * len(j) / max(len(ne), 1):.1f})")
po, ps = len(fa_ids["judge opus alone"]) / len(ne), len(fa_ids["judge sonnet alone"]) / len(ne)
print(f"[judge correlation] both SAME on NOT_EQUIVALENT {len(j)} vs {po * ps * len(ne):.1f} expected if independent")
print("\n[source] n | comparator EQ | judges-both false SAME (non-EQ) | judges-both SAME on EQ | default-hybrid false")
for sub in sorted({p["sub"] for p in pairs}):
    rs = [p for p in pairs if p["sub"] == sub]
    nn = [p for p in rs if p["label"] != "EQUIVALENT"]
    ee = [p for p in rs if p["label"] == "EQUIVALENT"]
    print(f"  {sub:24s} {len(rs)} | {sum(p['c'] == 'EQUIVALENT' for p in rs)} | {sum(p['o'] == 'SAME' and p['s'] == 'SAME' for p in nn)}/{len(nn)} | {sum(p['o'] == 'SAME' and p['s'] == 'SAME' for p in ee)}/{len(ee)} | {sum(p['h'] == 'SAME' for p in nn)}")
print("\nboth-judges false-SAME pairs (NOT_EQUIVALENT-labelled):")
for p in ne:
    if p["id"] in j:
        print(f"  {p['id']} [{p['sub']}] {p['a'][:110]} || {p['b'][:110]}")
print(f"\nCLAIM: {'none allowed (VACUOUS)' if vacuous else ('narrow claim allowed' if within else 'NOT ALLOWED')}")
