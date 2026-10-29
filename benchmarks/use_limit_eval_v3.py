"""USE_LIMIT v3 on the NEW fresh set (data/use_limits_v3/PREREG.md). Run ONCE after FREEZE.json; nothing is tuned after reading.
python -m benchmarks.use_limit_eval_v3 [--out data/use_limits_v3/RESULT.txt]"""
import collections
import glob
import json
import os
import sys

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_V1, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "use_limits_v3")
KINDS = ("faithful_light", "faithful_heavy", "limit_drop", "control")


def load():
    rows, bad = [], 0
    for path in sorted(glob.glob(os.path.join(D, "out_*.jsonl"))):
        who = os.path.basename(path)[4]
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
                assert all(r.get(k) for k in ("source", "limit_drop", "style", "lang"))
                r["_a"] = who
                rows.append(r)
            except Exception:                                         # noqa: BLE001
                bad += 1
    return rows, bad


def fams(src, rel, families):
    return {v[0] for v in check(src, rel, families)}


def pct(k, n):
    return f"{k}/{n} = {100 * k / max(n, 1):.1f} %"


def old_sets_false_alarms():
    hits = n = 0
    for f in glob.glob(os.path.join(ROOT, "data", "**", "*.jsonl"), recursive=True):
        if "use_limits" in f or "names_lower" in f:
            continue
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:                                         # noqa: BLE001
                continue
            a, b = r.get("a") or r.get("text_a"), r.get("b") or r.get("text_b")
            lab = r.get("expected_equivalence") or r.get("label")
            if not a or not b or str(lab).upper() not in ("EQUIVALENT", "SAME"):
                continue
            try:
                v = check(a, b, {"USE_LIMIT"})
            except Exception:                                         # noqa: BLE001
                continue
            n += 1
            hits += bool(v)
    return hits, n


def main(out=None):
    rows, bad = load()
    L = []
    P = L.append
    n = len(rows)
    P(f"records {n} (malformed lines: {bad}); authors: {dict(collections.Counter(r['_a'] for r in rows))}")
    flag = {k: {"new": 0, "old": 0, "uonly": 0} for k in KINDS}
    st = collections.defaultdict(lambda: [0, 0]); lg = collections.defaultdict(lambda: [0, 0]); au = collections.defaultdict(lambda: [0, 0])
    missed, heavy_u, rec_n, rec_u = [], [], 0, 0
    rec_hits = []
    for r in rows:
        for k in KINDS:
            if not r.get(k):
                continue
            new, old = fams(r["source"], r[k], RELAY_FAMILIES), fams(r["source"], r[k], RELAY_FAMILIES_V1)
            flag[k]["new"] += bool(new); flag[k]["old"] += bool(old); flag[k]["uonly"] += new == {"USE_LIMIT"}
            if k == "limit_drop":
                for d, key in ((st, r["style"]), (lg, r["lang"]), (au, r["_a"])):
                    d[key][1] += 1; d[key][0] += bool(new)
                if not new:
                    missed.append((r["style"], r["lang"], r.get("marker"), r["source"]))
            if k == "faithful_heavy" and new == {"USE_LIMIT"}:
                heavy_u.append((r.get("marker"), r[k]))
        if r.get("recipient_source") and r.get("recipient_relay"):
            rec_n += 1
            f = fams(r["recipient_source"], r["recipient_relay"], {"USE_LIMIT"})
            rec_u += bool(f)
            if f:
                rec_hits.append((r["recipient_source"], r["recipient_relay"]))
    P(f"limit_drop flagged NEW {pct(flag['limit_drop']['new'], n)}   (families without USE_LIMIT: {pct(flag['limit_drop']['old'], n)})")
    P("  per style : " + "; ".join(f"{s} {pct(*v)}" for s, v in sorted(st.items())))
    P("  per lang  : " + "; ".join(f"{s} {pct(*v)}" for s, v in sorted(lg.items())))
    P("  per author: " + "; ".join(f"{s} {pct(*v)}" for s, v in sorted(au.items())))
    P(f"faithful_light flagged NEW {pct(flag['faithful_light']['new'], n)} (OLD {pct(flag['faithful_light']['old'], n)}); by USE_LIMIT alone {pct(flag['faithful_light']['uonly'], n)}")
    P(f"faithful_heavy flagged NEW {pct(flag['faithful_heavy']['new'], n)} (OLD {pct(flag['faithful_heavy']['old'], n)}); by USE_LIMIT alone {pct(flag['faithful_heavy']['uonly'], n)}")
    P(f"control corruption flagged NEW {pct(flag['control']['new'], n)} (OLD {pct(flag['control']['old'], n)})")
    P(f"recipient decoy flagged by USE_LIMIT {pct(rec_u, rec_n)}")
    hits, tot = old_sets_false_alarms()
    P(f"equivalent pairs of the older sets with a USE_LIMIT alarm: {hits} of {tot}")
    v1 = flag["limit_drop"]["new"] / n >= 0.80 and all(v[0] / max(v[1], 1) >= 0.70 for v in st.values()) and lg["pt"][0] / max(lg["pt"][1], 1) >= 0.75
    v2 = flag["faithful_light"]["new"] / n <= 0.10 and flag["faithful_light"]["uonly"] / n <= 0.03
    v3 = flag["faithful_heavy"]["uonly"] / n <= 0.10
    v4 = rec_u / max(rec_n, 1) <= 0.03
    v5 = flag["control"]["new"] / n >= 0.70
    v6 = hits == 0
    P(f"\nV1 {'PASS' if v1 else 'FAIL'}  V2 {'PASS' if v2 else 'FAIL'}  V3 {'PASS' if v3 else 'FAIL'}  V4 {'PASS' if v4 else 'FAIL'}  V5 {'PASS' if v5 else 'FAIL'}  V6 {'PASS' if v6 else 'FAIL'}")
    P(f"\nfaithful_heavy USE_LIMIT-only alarms ({len(heavy_u)}):")
    for m in heavy_u:
        P("  " + " | ".join(str(x)[:110] for x in m))
    P(f"\nrecipient decoy alarms ({len(rec_hits)}):")
    for m in rec_hits:
        P("  " + " => ".join(x[:90] for x in m))
    P(f"\nmissed limit_drop ({len(missed)}):")
    for m in missed:
        P("  " + " | ".join(str(x) for x in m))
    txt = "\n".join(L)
    print(txt)
    if out:
        open(out, "w", encoding="utf-8").write(txt + "\n")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None)
