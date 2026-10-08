"""blind11 — the pre-registered one-shot evaluation (ADR-017 PRE-REGISTRATION). Arms exactly as registered:
 A rules 0.4 (inconclusive off) | B rules (inconclusive on) | C AIXL LLM route (card 0.6, per encoder; completeness+markers, inconclusive on)
 D arbiter (Sonnet, Haiku, 2-of-2) | E D + obfuscation veto | F D + C must prove EQUIVALENT.   AMBIGUOUS: rules detect_ambiguity only.
usage: python -m benchmarks.blind11_eval DIR"""
import collections
import glob
import json
import os
import re
import sys

from aixl import compare, detect_ambiguity
from aixl.core.comparator import compare_graphs
from aixl.core.completeness import annotate
from aixl.core.normalizer import sanitize_input
from aixl.core.ontology import load_config
from aixl.serialization import aixl_codec

CLS = ("EQUIVALENT", "NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "CONTRADICTORY")

def read_tsv(d, pattern):
    v = {}
    for p in glob.glob(os.path.join(d, pattern)):
        for l in open(p, encoding="utf-8"):
            f = l.rstrip("\n").split("\t")
            if len(f) >= 2: v[f[0]] = f[1].strip().upper()
    return v

def read_enc(d, model):
    a = {}
    for p in glob.glob(os.path.join(d, f"b11_enc_{model}_*.txt")):
        for l in open(p, encoding="utf-8"):
            m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
            if m: a[m.group(1)] = m.group(2).strip("`")
    return a

def main():
    d = sys.argv[1]
    rows = {r["id"]: r for r in map(json.loads, open("data/blind10/blind11.jsonl", encoding="utf-8")) if r.strip()} if False else {}
    for l in open("data/blind10/blind11.jsonl", encoding="utf-8"):
        if l.strip(): r = json.loads(l); rows[r["id"]] = r
    gold = json.load(open("data/blind10/b11_gold.json"))
    T = json.load(open("data/blind10/b11_texts.json")); txt = {t["tid"]: t["text"] for t in T}
    by = {}
    for t in T: by.setdefault(t["id"], {})[t["side"]] = t["tid"]
    off = dict(load_config()); off["inconclusive"] = False
    on = dict(load_config()); on["inconclusive"] = True
    said = collections.defaultdict(dict)                      # arm -> pid -> True if judged SAME/EQUIVALENT
    for g in gold:
        r = rows[g["pid"]]
        said["A rules 0.4"][g["pid"]] = compare(r["a"], r["b"], off).verdict == "EQUIVALENT"
        said["B rules +inconclusive"][g["pid"]] = compare(r["a"], r["b"], on).verdict == "EQUIVALENT"
    for m in ("sonnet", "haiku"):
        enc = read_enc(d, m); bad = 0
        for g in gold:
            ids = by[g["pid"]]; gs = []
            try:
                for k in ("a", "b"):
                    gr = aixl_codec.decode(enc[ids[k]]); annotate(gr, txt[ids[k]]); gs.append(gr)
                ok = compare_graphs(gs[0], gs[1], on).verdict == "EQUIVALENT"
            except Exception:
                ok = False; bad += 1
            said[f"C AIXL LLM-route ({m} enc)"][g["pid"]] = ok
        print(f"[C {m}] parse/missing failures: {bad}/{len(gold)}")
    sv, hv = read_tsv(d, "b11_arb_out_sonnet_*.tsv"), read_tsv(d, "b11_arb_out_haiku_*.tsv")
    for g in gold:
        s, h = sv.get(g["jid"]), hv.get(g["jid"]); pid = g["pid"]; r = rows[pid]
        obf = bool(sanitize_input(r["a"])[1] or sanitize_input(r["b"])[1])
        said["D arbiter Sonnet"][pid] = s == "SAME"
        said["D arbiter Haiku"][pid] = h == "SAME"
        cons = s == h == "SAME"
        said["D arbiter 2-of-2"][pid] = cons
        said["E arbiter Sonnet + obf. veto"][pid] = s == "SAME" and not obf
        said["E arbiter Haiku + obf. veto"][pid] = h == "SAME" and not obf
        said["E arbiter 2-of-2 + obf. veto"][pid] = cons and not obf
        for m in ("sonnet", "haiku"):
            said[f"F 2-of-2 + C({m})"][pid] = cons and said[f"C AIXL LLM-route ({m} enc)"][pid]
    lab = {g["pid"]: g["label"] for g in gold}
    print(f"\n{'arm':36s} {'EQUIV proven':>14s} {'false-EQUIV (180)':>20s}   NOT / PARTIAL / CONTRA")
    for arm, v in said.items():
        eq = sum(v[p] for p in v if lab[p] == "EQUIVALENT")
        fe = {c: sum(v[p] for p in v if lab[p] == c) for c in CLS[1:]}
        tot = sum(fe.values())
        print(f"{arm:36s} {eq:3d}/60={100*eq/60:5.1f}% {tot:3d}/180={100*tot/180:5.1f}%      {fe['NOT_EQUIVALENT']:2d} / {fe['PARTIALLY_EQUIVALENT']:2d} / {fe['CONTRADICTORY']:2d}")
    amb = [r for r in rows.values() if r["label"] == "AMBIGUOUS"]
    non = [rows[g["pid"]] for g in gold if g["label"] == "EQUIVALENT"]
    d1 = sum(detect_ambiguity(r["a"]).ambiguous for r in amb); d2 = sum(detect_ambiguity(r["a"]).ambiguous for r in non)
    print(f"\nAMBIGUOUS (rules detect_ambiguity): detected {d1}/{len(amb)} = {100*d1/len(amb):.1f}% | flagged on {d2}/{len(non)} non-ambiguous a-sides = {100*d2/len(non):.1f}%")


if __name__ == "__main__":
    main()
