"""Per-family recall / false alarm of the critical-slot invariants on labelled pairs of other authors.   python -m benchmarks.invariants_eval
Design split (stated before looking at the held-out numbers): families are SELECTED on DEV = blind13-15, then the selection is scored once on HELD-OUT = blind16-18.
A family is selected when its mismatch is at least twice as frequent among DIFF pairs as among SAME pairs on DEV (lift >= 2) and fires on >= 3 DIFF pairs."""
import collections
import glob
import json
import os
import sys

import aixl.invariants as I

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pairs(sets):
    for s in sets:
        for f in sorted(glob.glob(os.path.join(ROOT, "data", s, "author*.jsonl"))):
            for line in open(f, encoding="utf-8"):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                e = r.get("expected_equivalence")
                if e in ("EQUIVALENT", "NOT_EQUIVALENT") and r.get("text_a") and r.get("text_b"):
                    yield s, e == "EQUIVALENT", r["text_a"], r["text_b"]


def stats(sets):
    fam = collections.defaultdict(lambda: [0, 0])      # family -> [fires on SAME, fires on DIFF]
    n_same = n_diff = 0
    rows = []
    for _s, same, a, b in pairs(sets):
        fams = {v[0] for v in I.check(a, b)}
        rows.append((same, fams))
        n_same += same; n_diff += not same
        for f in fams:
            fam[f][0 if same else 1] += 1
    return fam, n_same, n_diff, rows


def main():
    dev = ["blind13", "blind14", "blind15"]; held = ["blind16", "blind17", "blind18"]
    fam, ns, nd, _ = stats(dev)
    print(f"DEV {dev}: {ns} SAME, {nd} DIFF\n  {'family':18} fires SAME  fires DIFF  lift")
    chosen = []
    for f, (s, d) in sorted(fam.items(), key=lambda kv: -kv[1][1]):
        lift = (d / nd) / max(s / ns, 1e-9) if d else 0
        sel = d >= 3 and lift >= 2
        print(f"  {f:18} {s:>9} {d:>11}  {lift:5.1f} {'<- selected' if sel else ''}")
        if sel:
            chosen.append(f)
    print("selected:", chosen)
    for name, sets in (("DEV", dev), ("HELD-OUT", held)):
        _, ns2, nd2, rows = stats(sets)
        det = sum(1 for same, fams in rows if not same and fams & set(chosen))
        fa = sum(1 for same, fams in rows if same and fams & set(chosen))
        print(f"{name:9} selected families: detects {det}/{nd2} = {det / max(nd2, 1):.1%} of DIFF pairs; false alarm {fa}/{ns2} = {fa / max(ns2, 1):.1%} of SAME pairs")


if __name__ == "__main__":
    sys.exit(main())
