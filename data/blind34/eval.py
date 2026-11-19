"""blind34 one-shot evaluation (see PREREG.md). usage: AIXL_V071=.. AIXL_P0005=.. AIXL_V080=.. python3 -I eval.py   (refuses a second run: RESULT_run1.txt)"""
import collections
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TREES = {"v071": os.environ["AIXL_V071"], "p0005": os.environ["AIXL_P0005"], "v080": os.environ["AIXL_V080"]}
frz = json.load(open(os.path.join(HERE, "CODE_FREEZE.json")))
for tag, root in TREES.items():
    for f, h in frz[tag].items():
        assert hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest() == h, f"{tag}:{f} changed after the freeze: blind34 is void"
for n, h in json.load(open(os.path.join(HERE, "MANIFEST.json"))).items():
    assert hashlib.sha256(open(os.path.join(HERE, n), "rb").read()).hexdigest() == h, f"{n} changed"
if os.path.exists(os.path.join(HERE, "RESULT_run1.txt")):
    sys.exit("blind34 was already run once")
rows = [json.loads(l) for l in open(os.path.join(HERE, "authored.jsonl"), encoding="utf-8") if l.strip()]
byid = {r["id"]: r for r in rows}
RUN = ("import sys,json\nsys.path.insert(0,sys.argv[1])\nfrom aixl.semantic import compare_texts\n"
       "d=json.load(sys.stdin)\nprint(json.dumps({k:[compare_texts(a,b).verdict,compare_texts(b,a).verdict] for k,(a,b) in d.items()}))\n")
payload = json.dumps({r["id"]: [r["a"], r["b"]] for r in rows})
V = {t: json.loads(subprocess.run([sys.executable, "-I", "-c", RUN, root], input=payload, capture_output=True, text=True, check=True).stdout) for t, root in TREES.items()}
def tsv(p):
    return {l.split("\t")[0]: l.split("\t")[1].strip().upper() for l in open(p, encoding="utf-8") if "\t" in l}
ckey = json.load(open(os.path.join(HERE, "claude_key.json")))
J = {}
for name in ("sonnet", "haiku"):
    d = {}
    for c in (1, 2):
        d.update(tsv(os.path.join(HERE, f"judge_{name}_{c}.tsv")))
    J[name] = {ckey[k]: v for k, v in d.items() if k in ckey}
for name, f in (("gemma27", "judge_gemma27.tsv"), ("phi4", "judge_phi4.tsv"), ("qwen3_32", "judge_qwen3_32.tsv")):
    p = os.path.join(HERE, f)
    if os.path.exists(p): J[name] = tsv(p)
lab = lambda r: r["label"]  # noqa: E731
ne = [r for r in rows if lab(r) == "NOT_EQUIVALENT"]; eq = [r for r in rows if lab(r) == "EQUIVALENT"]
acc = lambda t, r: "EQUIVALENT" in V[t][r["id"]]  # noqa: E731
pro = lambda t, r: V[t][r["id"]] == ["EQUIVALENT", "EQUIVALENT"]  # noqa: E731
print(f"SET {len(rows)} pairs: {len(eq)} EQ-labelled, {len(ne)} NE-labelled; languages {dict(collections.Counter(r['lang'] for r in rows))}; authors {dict(collections.Counter(r['author'] for r in rows))}")
def table(title, sub):
    n_, e_ = [r for r in sub if lab(r) == "NOT_EQUIVALENT"], [r for r in sub if lab(r) == "EQUIVALENT"]
    print(f"\n== {title}: {len(e_)} EQ / {len(n_)} NE")
    for t in TREES: print(f"  comparator {t:6s} false accepts {sum(acc(t, r) for r in n_):3d}/{len(n_)}   proven {sum(pro(t, r) for r in e_):3d}/{len(e_)}")
table("ALL", rows)
for lg in ("en", "es", "pt"): table(f"language {lg}", [r for r in rows if r["lang"] == lg])
for fam in sorted({r["family"] for r in rows}): table(f"family {fam}", [r for r in rows if r["family"] == fam])
fa = {t: {r["id"] for r in ne if acc(t, r)} for t in TREES}
new_fa = fa["v080"] - fa["p0005"] - fa["v071"]
print(f"\n[R-safety]     V080 false accepts not already in P0005/V071: {len(new_fa)} {sorted(new_fa)} -> {'HOLDS' if not new_fa else 'DOES NOT HOLD'}")
print(f"[R-no-regress] V080 {len(fa['v080'])} <= P0005 {len(fa['p0005'])} -> {'HOLDS' if len(fa['v080']) <= len(fa['p0005']) else 'DOES NOT HOLD'}")
print("\n== judges (SAME on EQ-labelled / false SAME on NE-labelled / agreement with the author label)")
for n, t in J.items():
    agree = sum((t.get(r["id"]) == "SAME") == (lab(r) == "EQUIVALENT") for r in rows)
    print(f"  {n:9s} SAME {sum(t.get(r['id']) == 'SAME' for r in eq):3d}/{len(eq)}  false SAME {sum(t.get(r['id']) == 'SAME' for r in ne):3d}/{len(ne)}  agrees {agree}/{len(rows)}  invalid {sum(t.get(r['id']) == 'INVALID' for r in rows)}")
sys.path.insert(0, os.environ["AIXL_V080"])
from aixl.semantic import hybrid  # noqa: E402


def claude_same(r): return J["sonnet"].get(r["id"]) == "SAME" and J["haiku"].get(r["id"]) == "SAME"
print("\n== hybrid with the Claude pair as judges (V080 comparator)")
for veto in ("all", "definite"):
    hy = {}
    for r in rows:
        jj = {n: (lambda a, b, n=n, i=r["id"]: J[n].get(i, "")) for n in ("sonnet", "haiku")}
        hy[r["id"]] = hybrid.decide(r["a"], r["b"], jj, veto=veto).verdict
    print(f"  veto={veto:9s} SAME on EQ {sum(hy[r['id']] == 'SAME' for r in eq)}/{len(eq)}   false SAME on NE {sum(hy[r['id']] == 'SAME' for r in ne)}/{len(ne)}   REVIEW on EQ {sum(hy[r['id']] == 'REVIEW' for r in eq)}")
print("\n== shared blind spots: false SAME of the Claude pair, and what the open judges say")
cf = [r for r in ne if claude_same(r)]
for r in cf:
    print(f"  {r['id']} {r['lang']} {r['family']} | {r['a']} || {r['b']} | open judges: " + ", ".join(f"{n}={J[n].get(r['id'], '-')}" for n in J if n not in ('sonnet', 'haiku')) + f" | author: {r['what']}")
open_n = [n for n in J if n not in ("sonnet", "haiku")]
print(f"  total {len(cf)}; open judges that ALSO say SAME: " + ", ".join(f"{n}={sum(J[n].get(r['id']) == 'SAME' for r in cf)}" for n in open_n))
print("\n== probable label noise: a majority of all judges contradicts the author label")
noisy = []
for r in rows:
    votes = [J[n].get(r["id"]) for n in J if J[n].get(r["id"]) in ("SAME", "DIFFERENT")]
    if len(votes) >= 3:
        same = sum(v == "SAME" for v in votes)
        if (same > len(votes) / 2) != (lab(r) == "EQUIVALENT") and abs(same - len(votes) / 2) >= 1: noisy.append(r["id"])
print(f"  {len(noisy)} of {len(rows)} pairs ({collections.Counter(byid[i]['label'] for i in noisy)}); listed in noisy_ids.json, NOT removed from the tables above")
json.dump(noisy, open(os.path.join(HERE, "noisy_ids.json"), "w"))
