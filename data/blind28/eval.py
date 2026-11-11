"""blind28 one-shot evaluation (see PREREG.md). Refuses to run if frozen code, model hashes or author files changed, and refuses a second run once RESULT_run1.txt exists.
usage: python3 -I eval.py"""
import collections
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODEL_DIR = os.environ.get("AIXL_QWEN_DIR", os.path.expanduser("~/Claude/aixl-models/qwen2.5-7b-instruct-q4_k_m"))
sys.path.insert(0, ROOT)
from aixl.hybrid_protocol import decide  # noqa: E402
from aixl.semantic import compare_texts  # noqa: E402

for f, h in json.load(open(os.path.join(HERE, "CODE_FREEZE.json"))).items():
    assert hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest() == h, f"{f} changed after the freeze: blind28 is void"
mf = json.load(open(os.path.join(HERE, "MODEL_FREEZE.json")))          # written before the Qwen judge ran
assert hashlib.sha256(open(os.path.join(MODEL_DIR, "SHA256.txt"), "rb").read()).hexdigest() == mf["SHA256.txt"], "the model files changed: blind28 is void"
man = json.load(open(os.path.join(HERE, "MANIFEST.json")))
for n, h in man.items():
    assert hashlib.sha256(open(os.path.join(HERE, "authors", n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind28 was already run once (RESULT_run1.txt exists): the set is SPENT")

rows = [json.loads(line) for n in man for line in open(os.path.join(HERE, "authors", n), encoding="utf-8") if line.strip()]
key = json.load(open(os.path.join(HERE, "judge_key.json")))
inv = {v: k for k, v in key.items()}
J = {}
for m in ("opus", "sonnet", "qwen"):
    J[m] = {}
    for line in open(os.path.join(HERE, "judge", f"{m}.tsv"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2:
            J[m][p[0]] = p[1].strip().upper()
    bad = [q for q in key if J[m].get(q) not in ("SAME", "DIFFERENT", "UNSURE")]
    assert not bad, f"judge {m}: missing/invalid {bad[:5]}"
for r in rows:
    q = inv[r["id"]]
    r["o"], r["s"], r["q"] = J["opus"][q], J["sonnet"][q], J["qwen"][q]
    r["c"] = compare_texts(r["text_a"], r["text_b"]).verdict
    r["h"] = decide(r["text_a"], r["text_b"], {"opus": r["o"], "sonnet": r["s"]})["verdict"]
    r["hs"] = decide(r["text_a"], r["text_b"], {"opus": r["o"], "sonnet": r["s"]}, strict=True)["verdict"]

lab = lambda r: r["expected_equivalence"]  # noqa: E731
ne = [r for r in rows if lab(r) != "EQUIVALENT"]
eq = [r for r in rows if lab(r) == "EQUIVALENT"]
pct = lambda a, b: f"{a}/{b} ({100 * a / max(b, 1):.1f}%)"  # noqa: E731
print(f"SET: {len(rows)} pairs  labels {dict(collections.Counter(map(lab, rows)))}  authors {dict(collections.Counter(r['id'][0] for r in rows))}")
print(f"comparator verdicts {dict(collections.Counter(r['c'] for r in rows))}")
print("judge verdicts: " + "  ".join(f"{m} {dict(collections.Counter(J[m].values()))}" for m in J))
S = lambda r, k: r[k] == "SAME"  # noqa: E731
rules = {
    "R0 comparator alone": lambda r: r["c"] == "EQUIVALENT",
    "R1 comparator AND opus AND sonnet SAME (PRIMARY)": lambda r: r["c"] == "EQUIVALENT" and S(r, "o") and S(r, "s"),
    "R3 comparator AND all three judges SAME": lambda r: r["c"] == "EQUIVALENT" and S(r, "o") and S(r, "s") and S(r, "q"),
    "default hybrid (2 Claude + veto) = SAME": lambda r: r["h"] == "SAME",
    "strict hybrid (2 Claude) = SAME": lambda r: r["hs"] == "SAME",
    "J2 opus AND sonnet SAME": lambda r: S(r, "o") and S(r, "s"),
    "J3 all three judges SAME": lambda r: S(r, "o") and S(r, "s") and S(r, "q"),
    "qwen alone": lambda r: S(r, "q"),
    "opus alone": lambda r: S(r, "o"),
    "sonnet alone": lambda r: S(r, "s"),
}
fa, tp = {}, {}
print()
for name, rule in rules.items():
    fa[name] = {r["id"] for r in ne if rule(r)}
    tp[name] = sum(1 for r in eq if rule(r))
    print(f"{name:50s} false accepts {pct(len(fa[name]), len(ne)):14s} proven-EQUIVALENT {pct(tp[name], len(eq))}")
r1 = "R1 comparator AND opus AND sonnet SAME (PRIMARY)"
within = len(fa[r1]) <= 0.03 * len(ne)
vac = tp[r1] < 10
g1 = "VACUOUS (R1 proves fewer than 10 equivalent pairs)" if vac else ("PASS" if within else "FAIL")
print(f"\n[G1] R1 false accepts <= 3% of {len(ne)} NOT_EQUIVALENT-labelled pairs (<= {int(0.03 * len(ne))}); proven-EQUIVALENT {tp[r1]} (floor 10) -> {g1}   ids {sorted(fa[r1])}")
g1b = len(fa["J3 all three judges SAME"]) <= 0.03 * len(ne)
print(f"[G1b] J3 (all three judges) false accepts {len(fa['J3 all three judges SAME'])} -> {'PASS' if g1b else 'FAIL'}   ids {sorted(fa['J3 all three judges SAME'])}")


def overlap(a, b, label):
    x, y = fa[a], fa[b]
    print(f"[overlap] {label}: {len(x)} and {len(y)}, in common {len(x & y)} (expected if independent {len(x) * len(y) / max(len(ne), 1):.1f})")


overlap("opus alone", "sonnet alone", "opus vs sonnet false SAME")
overlap("qwen alone", "J2 opus AND sonnet SAME", "qwen vs (opus AND sonnet) false SAME")
overlap("R0 comparator alone", "J2 opus AND sonnet SAME", "comparator false accepts vs the two Claude judges")
agree = lambda a, b: sum(1 for r in rows if r[a] == r[b])  # noqa: E731
print(f"[agreement] opus-sonnet {agree('o', 's')}/{len(rows)}  qwen-opus {agree('q', 'o')}/{len(rows)}  qwen-sonnet {agree('q', 's')}/{len(rows)}")
print("\n[construct] n | comparator EQ on equivalents (proven/of) | comparator false accepts | R1 false | J2 false | qwen false | J3 false")
for fam in sorted({r["family"] for r in rows}):
    rs = [r for r in rows if r["family"] == fam]
    nn = [r for r in rs if lab(r) != "EQUIVALENT"]
    ee = [r for r in rs if lab(r) == "EQUIVALENT"]
    ok = sum(1 for r in ee if r["c"] == "EQUIVALENT")
    bad = sum(1 for r in nn if r["c"] == "EQUIVALENT")
    cnt = lambda name, nn=nn: sum(1 for r in nn if r["id"] in fa[name])  # noqa: E731
    print(f"  {fam:30s} {len(rs)} | {ok}/{len(ee)} | {bad} | {cnt(r1)} | {cnt('J2 opus AND sonnet SAME')} | {cnt('qwen alone')} | {cnt('J3 all three judges SAME')}")
print("\ncomparator false accepts (NOT_EQUIVALENT-labelled, comparator EQUIVALENT):")
for r in ne:
    if r["c"] == "EQUIVALENT":
        print(f"  {r['id']} [{lab(r)}] {r['text_a']} || {r['text_b']} | author: {r['what_differs']}")
print("\nJ3 false accepts:")
for r in ne:
    if r["id"] in fa["J3 all three judges SAME"]:
        print(f"  {r['id']} [{lab(r)}] {r['text_a']} || {r['text_b']} | author: {r['what_differs']}")
print(f"\nCLAIM: {'none allowed (VACUOUS)' if vac else ('narrow claim allowed' if within else 'NOT ALLOWED')}")
