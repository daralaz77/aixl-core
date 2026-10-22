"""Hybrid (relay_check as evidence for the 2-of-2 arbiter) on relays written by real models. Preregistered: data/relays/PREREG_HYBRID.md.   python -m benchmarks.hybrid_relay_eval
Inputs: data/relays/judge_key.json (id -> label/kind) and judge_sonnet_*.tsv / judge_haiku_*.tsv (verbatim judge outputs)."""
import collections
import csv
import glob
import json
import os
import sys

from aixl.arbiter import consensus
from aixl.invariants import check

# Decided by principle in PREREG_HYBRID.md before any judge output existed: facts a faithful rewording cannot legitimately change.
HARD_FACT_FAMILIES = frozenset({"NUMBER", "DATE", "WEEKDAY", "CLOCK", "NAME", "COMPARATOR", "QUANTITY", "UNIT", "DAY_OF_MONTH"})
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "relays")


def votes(model):
    v = {}
    for f in sorted(glob.glob(os.path.join(D, f"judge_{model}_*.tsv"))):
        for row in csv.reader(open(f, encoding="utf-8"), delimiter="\t"):
            if len(row) >= 2:
                v[row[0].strip()] = row[1].strip().upper()
    return v


def main():
    key = json.load(open(os.path.join(D, "judge_key.json"), encoding="utf-8"))
    s, h = votes("sonnet"), votes("haiku")
    print(f"pairs {len(key)}; judgments: sonnet {len(s)}, haiku {len(h)}")
    arms = {"A arbiter alone": lambda it, c, hard, anyv: c, "B hybrid-hard": lambda it, c, hard, anyv: "ESCALATE" if c == "SAME" and hard else c,
            "C hybrid-all": lambda it, c, hard, anyv: "ESCALATE" if c == "SAME" and anyv else c}
    tab = {a: collections.Counter() for a in arms}; n = collections.Counter()
    miss_a = []
    for it in key:
        c = consensus({"sonnet": s.get(it["id"], ""), "haiku": h.get(it["id"], "")})["verdict"]
        viol = check(it["a"], it["b"])
        fams = {x[0] for x in viol}
        hard, anyv = bool(fams & HARD_FACT_FAMILIES), bool(viol)
        n[it["kind"]] += 1
        for a, fn in arms.items():
            tab[a][(it["kind"], fn(it, c, hard, anyv))] += 1
        if it["kind"] == "corrupted" and c == "SAME":
            miss_a.append((it["a"], it["b"], sorted(fams)))
    for a in arms:
        t = tab[a]
        cs = t[("corrupted", "SAME")]; ls = t[("faithful_light", "SAME")]; hs = t[("faithful_heavy", "SAME")]
        print(f"{a:16} corrupted accepted as SAME {cs:>3}/{n['corrupted']} ({cs / max(n['corrupted'], 1):.1%}) | proven SAME: light {ls}/{n['faithful_light']}, heavy {hs}/{n['faithful_heavy']}"
              f" | corrupted -> DIFFERENT {t[('corrupted', 'DIFFERENT')]}, ESCALATE {t[('corrupted', 'ESCALATE')]}, UNSURE {t[('corrupted', 'UNSURE')]}")
    A, B, C = (tab[k] for k in arms)
    fa = A[("corrupted", "SAME")]; fb = B[("corrupted", "SAME")]
    keepA = A[("faithful_light", "SAME")] + A[("faithful_heavy", "SAME")]; keepB = B[("faithful_light", "SAME")] + B[("faithful_heavy", "SAME")]
    heavyA, heavyC = A[("faithful_heavy", "SAME")], C[("faithful_heavy", "SAME")]
    print("\npreregistered hypotheses:")
    print(f"  {'MET    ' if fa / max(n['corrupted'], 1) >= 0.05 else 'NOT MET'}  H5 arbiter-alone false SAME >= 5 %  ({fa}/{n['corrupted']})")
    print(f"  {'MET    ' if (fa > 0 and (fa - fb) / fa >= 0.30) or (fa > 0 and fb == 0) else 'NOT MET'}  H6 hybrid-hard cuts false SAME by >= 30 % relative  ({fa} -> {fb})")
    print(f"  {'MET    ' if keepA and keepB / keepA >= 0.97 else 'NOT MET'}  H7 hybrid-hard keeps >= 97 % of proven SAME on faithful  ({keepB}/{keepA})")
    print(f"  {'MET    ' if heavyA and (heavyA - heavyC) / heavyA > 0.10 else 'NOT MET'}  H8 hybrid-all loses > 10 % of proven SAME on faithful_heavy  ({heavyA} -> {heavyC})")
    print(f"\ncorrupted relays the arbiter accepted ({len(miss_a)}):")
    for a, b, f in miss_a:
        print(f"  {a[:80]!r}\n    -> {b[:80]!r}   invariants fired: {f}")


if __name__ == "__main__":
    sys.exit(main())
