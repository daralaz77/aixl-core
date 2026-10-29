"""USE_LIMIT v5 (a strong audience verb is the marker by itself) on a NEW fresh set (data/use_limits_v5/PREREG.md). Run ONCE after FREEZE.json; nothing is tuned after reading.
Baseline = the v4 code saved before the change (data/use_limits_v5/baseline_invariants_v4.py.txt).   python -m benchmarks.use_limit_eval_v5 [--out data/use_limits_v5/RESULT.txt]"""
import collections
import glob
import importlib.machinery
import importlib.util
import json
import os
import sys

from aixl.invariants import RELAY_FAMILIES, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "use_limits_v5")


def _load_v4():
    path = os.path.join(D, "baseline_invariants_v4.py.txt")
    loader = importlib.machinery.SourceFileLoader("invariants_v4_baseline", path)
    spec = importlib.util.spec_from_loader("invariants_v4_baseline", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def pct(k, n):
    return f"{k}/{n} = {100 * k / max(n, 1):.1f} %"


def main(out=None):
    v4 = _load_v4()
    rows, bad = [], 0
    for path in sorted(glob.glob(os.path.join(D, "out_*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
                assert all(r.get(k) for k in ("source", "faithful_light", "limit_drop", "kind", "lang"))
                r["_a"] = os.path.basename(path)[4]
                rows.append(r)
            except Exception:                                         # noqa: BLE001
                bad += 1
    L = []
    P = L.append
    P(f"records {len(rows)} (malformed {bad}); authors {dict(collections.Counter(r['_a'] for r in rows))}; kinds {dict(collections.Counter(r['kind'] for r in rows))}")

    def fl(mod, fams, src, rel):
        return {v[0] for v in mod.check(src, rel, fams)}
    res = collections.defaultdict(lambda: collections.Counter())
    miss, decoy_fa = [], []
    for r in rows:
        k = r["kind"]
        for arm, mod, fams in (("v5", __import__("aixl.invariants", fromlist=["x"]), RELAY_FAMILIES), ("v4", v4, v4.RELAY_FAMILIES)):
            drop = fl(mod, fams, r["source"], r["limit_drop"])
            light = fl(mod, fams, r["source"], r["faithful_light"])
            res[(k, arm)]["n"] += 1
            res[(k, arm)]["drop_flag"] += bool(drop)
            res[(k, arm)]["drop_u"] += "USE_LIMIT" in drop
            res[(k, arm)]["light_flag"] += bool(light)
            res[(k, arm)]["light_uonly"] += light == {"USE_LIMIT"}
            if arm == "v5":
                if k == "open_audience" and not drop:
                    miss.append((r["lang"], r.get("complement"), r["source"]))
                if k == "decoy" and "USE_LIMIT" in drop:
                    decoy_fa.append((r["lang"], r.get("complement"), r["source"]))
    for k in ("open_audience", "decoy"):
        for arm in ("v5", "v4"):
            c = res[(k, arm)]
            P(f"{k:<14}{arm}: drop flagged {pct(c['drop_flag'], c['n'])}; by USE_LIMIT {pct(c['drop_u'], c['n'])}; faithful_light flagged {pct(c['light_flag'], c['n'])}, by USE_LIMIT alone {pct(c['light_uonly'], c['n'])}")
    oa, dc = res[("open_audience", "v5")], res[("decoy", "v5")]
    by = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["kind"] == "open_audience":
            by[r["lang"]][1] += 1
            by[r["lang"]][0] += bool(fl(__import__("aixl.invariants", fromlist=["x"]), RELAY_FAMILIES, r["source"], r["limit_drop"]))
    P("open_audience per lang (v5): " + "; ".join(f"{k} {pct(*v)}" for k, v in sorted(by.items())))
    from benchmarks.use_limit_eval_v3 import old_sets_false_alarms
    hits, tot = old_sets_false_alarms()
    P(f"equivalent pairs of the older sets with a USE_LIMIT alarm: {hits} of {tot}")
    # W5: regression on the spent v3 set (recipient decoy + faithful_light by USE_LIMIT alone)
    rec_n = rec_u = fl_u = fl_n = 0
    for path in glob.glob(os.path.join(ROOT, "data", "use_limits_v3", "out_*.jsonl")):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if r.get("recipient_source") and r.get("recipient_relay"):
                rec_n += 1; rec_u += bool(check(r["recipient_source"], r["recipient_relay"], {"USE_LIMIT"}))
            fl_n += 1; fl_u += {v[0] for v in check(r["source"], r["faithful_light"], RELAY_FAMILIES)} == {"USE_LIMIT"}
    P(f"spent v3 set: recipient decoy flagged by USE_LIMIT {pct(rec_u, rec_n)}; faithful_light by USE_LIMIT alone {pct(fl_u, fl_n)}")
    w1 = oa["drop_flag"] / max(oa["n"], 1) >= 0.75
    w2 = dc["drop_u"] / max(dc["n"], 1) <= 0.10
    w3 = (oa["light_uonly"] + dc["light_uonly"]) / max(oa["n"] + dc["n"], 1) <= 0.03
    w4 = hits == 0
    w5 = rec_u / max(rec_n, 1) <= 0.03 and fl_u / max(fl_n, 1) <= 0.03
    P(f"\nW1 {'PASS' if w1 else 'FAIL'}  W2 {'PASS' if w2 else 'FAIL'}  W3 {'PASS' if w3 else 'FAIL'}  W4 {'PASS' if w4 else 'FAIL'}  W5 {'PASS' if w5 else 'FAIL'}")
    P(f"\ndecoy false alarms by USE_LIMIT ({len(decoy_fa)}):")
    for m in decoy_fa:
        P("  " + " | ".join(str(x)[:120] for x in m))
    P(f"\nmissed open_audience drops ({len(miss)}):")
    for m in miss:
        P("  " + " | ".join(str(x)[:120] for x in m))
    txt = "\n".join(L)
    print(txt)
    if out:
        open(out, "w", encoding="utf-8").write(txt + "\n")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None)
