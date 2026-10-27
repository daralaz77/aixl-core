"""relay_check on FRESH model-written role swaps. Preregistered: data/relays_roles/PREREG.md.   python -m benchmarks.roles_fresh_eval"""
import collections
import hashlib
import json
import os
import sys

import aixl
from aixl.invariants import RELAY_FAMILIES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "relays_roles")


def freeze_problems():
    f = json.load(open(os.path.join(D, "FREEZE.json")))
    out = []
    for path, h in f.items():
        if path == "RELAY_FAMILIES":
            if sorted(RELAY_FAMILIES) != h:
                out.append("RELAY_FAMILIES changed")
        elif hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest() != h:
            out.append(f"{path} changed since the freeze")
    return out


def main():
    probs = freeze_problems()
    if probs:
        print("NOTE: code differs from the frozen state -> NOT the preregistered run:", probs)
    rows, bad = [], 0
    for n, who in (("A", "opus"), ("B", "sonnet")):
        for line in open(os.path.join(D, f"out_{n}.jsonl"), encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                bad += 1; continue
            if r.get("source"):
                rows.append({**r, "author": who})
    print(f"{len(rows)} sources ({bad} unparsable lines)")
    pct = lambda a, b: f"{a}/{b} = {a / max(b, 1):.1%}"      # noqa: E731
    flag = {k: [0, 0] for k in ("faithful_light", "faithful_heavy", "role_swap", "control")}
    styles = collections.defaultdict(lambda: [0, 0]); ctrl = collections.defaultdict(lambda: [0, 0]); missed = []; fam_light = collections.Counter()
    lang = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        for k in flag:
            t = r.get(k)
            if not t:
                continue
            res = aixl.relay_check(r["source"], t); hit = not res["ok"]
            flag[k][0] += hit; flag[k][1] += 1
            if k == "role_swap":
                styles[r.get("role_swap_style")][0] += hit; styles[r.get("role_swap_style")][1] += 1
                lang[r.get("lang")][0] += hit; lang[r.get("lang")][1] += 1
                if not hit:
                    missed.append((r.get("role_swap_style"), r["source"], t, r.get("role_swap_what_changed")))
            if k == "control":
                ctrl[r.get("control_type")][0] += hit; ctrl[r.get("control_type")][1] += 1
            if k == "faithful_light" and hit:
                for v in res["violations"]:
                    fam_light[v["family"]] += 1
    for k, (a, b) in flag.items():
        print(f"{k:15} flagged {pct(a, b)}")
    print("\nrole_swap by style:", {k: pct(*v) for k, v in styles.items()})
    print("role_swap by language:", {k: pct(*v) for k, v in lang.items()})
    print("control by type:", {k: pct(*v) for k, v in ctrl.items()})
    print("families on faithful_light:", dict(fam_light.most_common()))
    rs, fl, ct = flag["role_swap"], flag["faithful_light"], flag["control"]
    hyp = {"R1 role_swap >= 50 %": rs[0] / max(rs[1], 1) >= 0.5, "R2 faithful_light <= 10 %": fl[0] / max(fl[1], 1) <= 0.10,
           "R3 control >= 70 %": ct[0] / max(ct[1], 1) >= 0.70,
           "R4 every style >= 30 %": bool(styles) and all(v[0] / max(v[1], 1) >= 0.30 for v in styles.values())}
    print("\npreregistered hypotheses:")
    for k, ok in hyp.items():
        print(f"  {'MET    ' if ok else 'NOT MET'}  {k}")
    print(f"\nmissed role swaps ({len(missed)}):")
    for st, s, t, w in missed:
        print(f"  [{st}] {s[:100]!r}\n      -> {t[:100]!r}\n      ({w})")


if __name__ == "__main__":
    sys.exit(main())
