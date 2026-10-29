"""USE_LIMIT family on FRESH model-written relays (data/use_limits/PREREG.md). Run ONCE after FREEZE.json; nothing is tuned after reading.
python -m benchmarks.use_limit_eval [--out data/use_limits/RESULT.txt]"""
import collections
import json
import os
import sys

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_V1, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "use_limits")


def load():
    rows, bad = [], 0
    for f in ("out_A.jsonl", "out_B.jsonl"):
        for line in open(os.path.join(D, f), encoding="utf-8"):
            try:
                r = json.loads(line)
                assert all(r.get(k) for k in ("source", "faithful_light", "faithful_heavy", "limit_drop", "control", "style"))
                r["_a"] = f[4]
                rows.append(r)
            except Exception:                                         # noqa: BLE001
                bad += 1
    return rows, bad


def fams(src, rel, families):
    return {v[0] for v in check(src, rel, families)}


def pct(k, n):
    return f"{k}/{n} = {100 * k / max(n, 1):.1f} %"


def main(out=None):
    rows, bad = load()
    L = []
    P = L.append
    P(f"records {len(rows)} (malformed lines: {bad})")
    kinds = ("faithful_light", "faithful_heavy", "limit_drop", "control")
    flag = {k: {"new": 0, "old": 0, "uonly": 0} for k in kinds}
    by_style = collections.defaultdict(lambda: [0, 0])
    by_lang = collections.defaultdict(lambda: [0, 0])
    missed, fired_light = [], collections.Counter()
    for r in rows:
        for k in kinds:
            new, old = fams(r["source"], r[k], RELAY_FAMILIES), fams(r["source"], r[k], RELAY_FAMILIES_V1)
            flag[k]["new"] += bool(new); flag[k]["old"] += bool(old); flag[k]["uonly"] += new == {"USE_LIMIT"}
            if k == "limit_drop":
                by_style[r["style"]][1] += 1; by_style[r["style"]][0] += bool(new)
                by_lang[r["lang"]][1] += 1; by_lang[r["lang"]][0] += bool(new)
                if not new:
                    missed.append((r["style"], r["lang"], r.get("marker"), r["source"]))
            if k == "faithful_light":
                fired_light.update(new)
    n = len(rows)
    P(f"limit_drop flagged  NEW {pct(flag['limit_drop']['new'], n)}   (baseline OLD families {pct(flag['limit_drop']['old'], n)})")
    P("  per style (NEW): " + "; ".join(f"{s} {pct(*v)}" for s, v in sorted(by_style.items())))
    P("  per lang  (NEW): " + "; ".join(f"{s} {pct(*v)}" for s, v in sorted(by_lang.items())))
    P(f"faithful_light flagged NEW {pct(flag['faithful_light']['new'], n)} (OLD {pct(flag['faithful_light']['old'], n)}); by USE_LIMIT alone {pct(flag['faithful_light']['uonly'], n)}")
    P(f"faithful_heavy flagged NEW {pct(flag['faithful_heavy']['new'], n)} (OLD {pct(flag['faithful_heavy']['old'], n)}); by USE_LIMIT alone {pct(flag['faithful_heavy']['uonly'], n)}")
    P(f"control corruption flagged NEW {pct(flag['control']['new'], n)} (OLD {pct(flag['control']['old'], n)})")
    P("families fired on faithful_light: " + ", ".join(f"{k}:{v}" for k, v in fired_light.most_common()))
    u1 = flag["limit_drop"]["new"] / n >= 0.70 and all(v[0] / max(v[1], 1) >= 0.50 for v in by_style.values())
    u2 = flag["faithful_light"]["new"] / n <= 0.10
    u3 = flag["control"]["new"] / n >= 0.70
    u4 = flag["faithful_light"]["uonly"] / n <= 0.03 and flag["faithful_heavy"]["uonly"] / n <= 0.10
    P(f"\nU1 {'PASS' if u1 else 'FAIL'}  U2 {'PASS' if u2 else 'FAIL'}  U3 {'PASS' if u3 else 'FAIL'}  U4 {'PASS' if u4 else 'FAIL'}")
    P(f"\nmissed limit_drop ({len(missed)}):")
    for m in missed:
        P("  " + " | ".join(str(x) for x in m))
    txt = "\n".join(L)
    print(txt)
    if out:
        open(out, "w", encoding="utf-8").write(txt + "\n")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None)
