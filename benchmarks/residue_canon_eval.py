"""ADR-017 experiments on real residues (blind10, card 0.5). 120 pairs: 60 EQUIVALENT (should be SAME) / 60 NOT_EQUIVALENT (should be DIFFERENT).
A = each side canonicalized independently, then key equality;  B = a judge decides per pair.
usage: python -m benchmarks.residue_canon_eval DIR   (DIR has rj_gold.json, rc_out.tsv, rj_out.tsv)"""
import json, sys, os, collections

def main():
    d = sys.argv[1]
    gold = json.load(open(os.path.join(d, "rj_gold.json"), encoding="utf-8"))
    if os.path.exists(os.path.join(d, "rc_out.tsv")):
        key = dict(l.rstrip("\n").split("\t", 1) for l in open(os.path.join(d, "rc_out.tsv"), encoding="utf-8") if "\t" in l)
        c = collections.Counter()
        for i, p in enumerate(gold):
            ka, kb = key.get(f"p{i:03d}a"), key.get(f"p{i:03d}b")
            c[(p["label"], "same" if ka == kb and ka is not None else "diff")] += 1
        eq, ne = c[("EQUIVALENT", "same")], c[("NOT_EQUIVALENT", "diff")]
        print(f"A (canonical-key equality): EQUIVALENT proven {eq}/60 | NOT_EQUIVALENT kept different {ne}/60 | false-SAME {c[('NOT_EQUIVALENT','same')]}/60")
    if os.path.exists(os.path.join(d, "rj_out.tsv")):
        v = {}
        for l in open(os.path.join(d, "rj_out.tsv"), encoding="utf-8"):
            f = l.rstrip("\n").split("\t")
            if len(f) >= 2: v[f[0]] = f[1].strip().upper()
        c = collections.Counter((p["label"], v.get(f"p{i:03d}", "MISSING")) for i, p in enumerate(gold))
        print(f"B (judge): EQUIVALENT->SAME {c[('EQUIVALENT','SAME')]}/60 (UNSURE {c[('EQUIVALENT','UNSURE')]}, DIFFERENT {c[('EQUIVALENT','DIFFERENT')]}) | "
              f"NOT_EQUIVALENT->DIFFERENT {c[('NOT_EQUIVALENT','DIFFERENT')]}/60 (false-SAME {c[('NOT_EQUIVALENT','SAME')]}, UNSURE {c[('NOT_EQUIVALENT','UNSURE')]})")
main()
