"""Evaluation of aixl.relay_check on relays written by real models (data/relays, preregistered in PREREG.md, code frozen in FREEZE.json).   python -m benchmarks.relay_llm_eval"""
import collections
import hashlib
import json
import os
import sys

import aixl
from aixl.invariants import RELAY_FAMILIES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "relays")


def load():
    src = {}
    for n in "AB":
        for line in open(os.path.join(D, f"sources_{n}.jsonl"), encoding="utf-8"):
            r = json.loads(line); src[r["id"]] = r["source"]
    rows, bad = [], 0
    for n in "AB":
        for line in open(os.path.join(D, f"out_{n}.jsonl"), encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                bad += 1; continue
            if r.get("id") in src:
                rows.append({**r, "source": src[r["id"]], "author": "opus" if n == "A" else "sonnet"})
    return rows, bad


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
        print("NOTE: code differs from the frozen state -> this is NOT the preregistered run:", probs)
    rows, bad = load()
    print(f"{len(rows)} sources with relays ({bad} unparsable lines)")
    kinds = ("faithful_light", "faithful_heavy", "corrupted")
    flag = {k: [0, 0] for k in kinds}
    by_type = collections.defaultdict(lambda: [0, 0]); fam_faithful = collections.Counter(); missed = []
    for r in rows:
        for k in kinds:
            t = r.get(k)
            if not t:
                continue
            res = aixl.relay_check(r["source"], t)
            hit = not res["ok"]
            flag[k][0] += hit; flag[k][1] += 1
            if k == "corrupted":
                by_type[r.get("corruption_type")][0] += hit; by_type[r.get("corruption_type")][1] += 1
                if not hit:
                    missed.append((r.get("corruption_type"), r["source"], t, r.get("what_changed")))
            elif hit:
                for v in res["violations"]:
                    fam_faithful[(k, v["family"])] += 1
    pct = lambda a, b: f"{a}/{b} = {a / max(b, 1):.1%}"           # noqa: E731
    c, l, h = flag["corrupted"], flag["faithful_light"], flag["faithful_heavy"]
    print(f"corrupted flagged       {pct(*c)}")
    print(f"faithful_light flagged  {pct(*l)}")
    print(f"faithful_heavy flagged  {pct(*h)}")
    print("\nper corruption type (detected / total):")
    for k, (a, b) in sorted(by_type.items(), key=lambda kv: -kv[1][0] / max(kv[1][1], 1)):
        print(f"  {k:18} {a:>2}/{b:<2} {a / max(b, 1):5.0%}")
    print("\nfamilies firing on FAITHFUL relays:", dict(fam_faithful.most_common()))
    hyp = {
        "H1 corrupted >= 70 %": c[0] / max(c[1], 1) >= 0.70,
        "H2 faithful_light <= 5 %": l[0] / max(l[1], 1) <= 0.05,
        "H3 faithful_heavy <= 25 %": h[0] / max(h[1], 1) <= 0.25,
        "H4 antonym_verb, role_swap, pronoun_reference each >= 50 %": all(by_type[t][0] / max(by_type[t][1], 1) >= 0.5 for t in ("antonym_verb", "role_swap", "pronoun_reference")),
    }
    print("\npreregistered hypotheses:")
    for k, ok in hyp.items():
        print(f"  {'MET    ' if ok else 'NOT MET'}  {k}")
    print(f"\nmissed corruptions ({len(missed)}):")
    for t, s, r, w in missed:
        print(f"  [{t}] {s[:90]!r}\n      -> {r[:90]!r}\n      ({w})")


if __name__ == "__main__":
    sys.exit(main())
