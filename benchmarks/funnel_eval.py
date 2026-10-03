"""blind12 funnel test, exactly as pre-registered in ADR-017. Stage 1 (deterministic): K1 canonical equality (rules route, inconclusive off),
K2 semantic_fingerprint equality, K3 lexical Jaccard baseline (>=0.1/0.2/0.3), K4 all pairs.  Stage 2: arbiter 2-of-2 on 360 equivalent + 480 near-miss pairs.
usage: python -m benchmarks.funnel_eval stage1 | stage2 DIR"""
import json, re, sys, itertools, collections, glob, os
from aixl import semantic_fingerprint
from aixl.api.service import to_semantic
from aixl.core.comparator import compare_graphs
from aixl.core.ontology import load_config
from aixl.core.normalizer import strip_accents, STOP
from aixl.core.lexicon_gaps import FUNCTION_WORDS
from aixl.core.completeness import SHORT_FUNCTION, _CLOSED

TOK = re.compile(r"\d+(?:[.,]\d+)?|[a-z]+")
STOPALL = STOP | FUNCTION_WORDS | SHORT_FUNCTION | _CLOSED

def load():
    return [json.loads(l) for l in open("data/blind10/blind12.jsonl", encoding="utf-8") if l.strip()]

def pairs_truth(rows):
    by = collections.defaultdict(list)
    for r in rows: by[r["cluster"]].append(r["id"])
    eq = {frozenset(p) for ids in by.values() for p in itertools.combinations(ids, 2)}
    par = {r["id"] for r in rows if r["kind"] == "paraphrase"}
    nm = {frozenset((r["id"], p)) for r in rows if r["kind"] == "near_miss" for p in by[r["of"]]}
    return eq, nm

def cwords(t):
    return {w for w in TOK.findall(strip_accents(t).lower()) if w not in STOPALL}

def stage1():
    rows = load(); ids = [r["id"] for r in rows]; txt = {r["id"]: r["text"] for r in rows}
    eq, nm = pairs_truth(rows)
    allp = [frozenset(p) for p in itertools.combinations(ids, 2)]
    print(f"texts {len(rows)} | all pairs {len(allp)} | equivalent pairs {len(eq)} | near-miss pairs {len(nm)}")
    cfg = dict(load_config()); cfg["inconclusive"] = False
    g = {i: to_semantic(txt[i]) for i in ids}
    fp = {i: semantic_fingerprint(txt[i]) for i in ids}
    cw = {i: cwords(txt[i]) for i in ids}
    def jac(a, b):
        A, B = cw[a], cw[b]; return len(A & B) / len(A | B) if (A | B) else 0.0
    cand = {"K1 canonical equality": set(), "K2 fingerprint equality": set(), "K3 lexical J>=0.1": set(), "K3 lexical J>=0.2": set(), "K3 lexical J>=0.3": set(), "K4 all pairs": set(allp)}
    for p in allp:
        a, b = tuple(p)
        if compare_graphs(g[a], g[b], cfg).verdict == "EQUIVALENT": cand["K1 canonical equality"].add(p)
        if fp[a] == fp[b]: cand["K2 fingerprint equality"].add(p)
        j = jac(a, b)
        for th in (0.1, 0.2, 0.3):
            if j >= th: cand[f"K3 lexical J>={th}"].add(p)
    ctrl_cl = set()
    by = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "paraphrase": by[r["cluster"]].append(r["id"])
    for c, ids4 in by.items():
        if all(not g[i].meta.get("unrecognized") and g[i].by_type("ACTION") for i in ids4): ctrl_cl.add(c)
    cl_of = {r["id"]: r["cluster"] for r in rows}
    eq_ctrl = {p for p in eq if cl_of[next(iter(p))] in ctrl_cl}
    print(f"controlled clusters: {len(ctrl_cl)}/60 ({sum(1 for _ in eq_ctrl)} equivalent pairs)")
    print(f"\n{'generator':26s} {'recall':>8s} {'ctrl':>7s} {'free':>7s} {'nm-leak':>8s} {'cand-rate':>10s} {'precision':>10s} {'candidates':>11s}")
    out = {}
    for k, c in cand.items():
        rec = len(c & eq) / len(eq); rc = len(c & eq_ctrl) / max(1, len(eq_ctrl)); rf = len(c & (eq - eq_ctrl)) / max(1, len(eq - eq_ctrl))
        leak = len(c & nm) / len(nm); rate = len(c) / len(allp); prec = len(c & eq) / max(1, len(c))
        print(f"{k:26s} {100*rec:7.1f}% {100*rc:6.1f}% {100*rf:6.1f}% {100*leak:7.1f}% {100*rate:9.2f}% {100*prec:9.2f}% {len(c):11d}")
        out[k] = {"recall": rec, "candidates": len(c)}
    json.dump({k: sorted(sorted(p) for p in v) for k, v in cand.items() if k != "K4 all pairs"}, open("data/blind10/b12_stage1_candidates.json", "w"))
    return rows, eq, nm, cand

def stage2(d):
    rows = load(); txt = {r["id"]: r for r in rows}
    eq, nm = pairs_truth(rows)
    gold = json.load(open("data/blind10/b12_stage2_gold.json"))
    cands = {k: {frozenset(p) for p in v} for k, v in json.load(open("data/blind10/b12_stage1_candidates.json")).items()}
    def rd(m):
        v = {}
        for p in glob.glob(os.path.join(d, f"b12_arb_out_{m}_*.tsv")):
            for l in open(p, encoding="utf-8"):
                f = l.rstrip("\n").split("\t")
                if len(f) >= 2: v[f[0]] = f[1].strip().upper()
        return v
    s, h = rd("sonnet"), rd("haiku")
    same = {}
    for g in gold:
        p = frozenset(g["pair"]); same[p] = (s.get(g["jid"]) == "SAME", h.get(g["jid"]) == "SAME")
    print(f"\nstage 2: judged {len(same)} pairs (Sonnet {len(s)}, Haiku {len(h)} verdicts)")
    def stats(sel, name):
        e = [p for p in sel if p in eq]; n = [p for p in sel if p in nm]
        row = lambda f: (sum(f(same[p]) for p in e), sum(f(same[p]) for p in n))
        for lab, f in (("Sonnet", lambda x: x[0]), ("Haiku", lambda x: x[1]), ("2-of-2", lambda x: x[0] and x[1])):
            a, b = row(f)
            print(f"  {name:28s} {lab:7s} equivalent SAME {a:3d}/{len(e)} = {100*a/max(1,len(e)):5.1f}% | near-miss SAME {b:3d}/{len(n)} = {100*b/max(1,len(n)):5.1f}%")
    stats(set(same), "arbiter alone (all 840)")
    for k, c in cands.items(): stats(set(same) & c, f"funnel {k}")
main_stage = sys.argv[1] if len(sys.argv) > 1 else "stage1"
if main_stage == "stage1": stage1()
else: stage2(sys.argv[2])
