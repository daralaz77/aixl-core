"""USE_LIMIT_PLURAL on a NEW fresh set (data/use_limits_v9/PREREG.md). Run ONCE after FREEZE.json; nothing is tuned after reading.   python -m benchmarks.use_limit_plural_eval [--out data/use_limits_v9/RESULT.txt]"""
import collections
import glob
import json
import os
import sys

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_OPEN, RELAY_FAMILIES_PLURAL, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "use_limits_v9")
ARMS = (("default", RELAY_FAMILIES, {"USE_LIMIT"}), ("plural", RELAY_FAMILIES_PLURAL, {"USE_LIMIT_PLURAL"}), ("open", RELAY_FAMILIES_OPEN, {"USE_LIMIT_OPEN"}))


def pct(k, n):
    return f"{k}/{n} = {100 * k / max(n, 1):.1f} %"


def main(out=None):
    rows, bad = [], 0
    for path in sorted(glob.glob(os.path.join(D, "out_*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
                assert all(r.get(k) for k in ("source", "faithful_light", "limit_drop", "kind", "subkind", "lang"))
                r["_a"] = os.path.basename(path)[4]
                rows.append(r)
            except Exception:                                         # noqa: BLE001
                bad += 1
    L = []
    P = L.append
    P(f"records {len(rows)} (malformed {bad}); authors {dict(collections.Counter(r['_a'] for r in rows))}; kinds {dict(collections.Counter((r['kind'], r['subkind']) for r in rows))}")
    res = collections.defaultdict(collections.Counter)
    miss, fa = [], []
    for r in rows:
        for arm, fams, own in ARMS:
            drop = {v[0] for v in check(r["source"], r["limit_drop"], fams)}
            light = {v[0] for v in check(r["source"], r["faithful_light"], fams)}
            for key in ((r["kind"], arm), (r["subkind"], arm), (r["lang"] + ":" + r["kind"], arm), (r["_a"] + ":" + r["kind"], arm)):
                c = res[key]
                c["n"] += 1
                c["drop"] += bool(drop)
                c["own"] += bool(drop & own)
                c["light_own_alone"] += bool(light) and light <= own
            if arm == "plural":
                if r["kind"] == "open_audience" and "USE_LIMIT_PLURAL" not in drop:
                    miss.append((r["subkind"], r["lang"], r.get("complement"), r["source"]))
                if r["kind"] == "decoy" and "USE_LIMIT_PLURAL" in drop:
                    fa.append((r["subkind"], r["lang"], r.get("complement"), r["source"]))
    for k in ("open_audience", "decoy"):
        for arm, _f, _o in ARMS:
            c = res[(k, arm)]
            P(f"{k:<14}{arm:<8} drop flagged {pct(c['drop'], c['n'])}; by the audience family {pct(c['own'], c['n'])}; faithful_light by it alone {pct(c['light_own_alone'], c['n'])}")
    P("\nper subkind (plural family: flagged by USE_LIMIT_PLURAL):")
    for sk in ("plural_group", "singular_group", "other", "plural_event"):
        c = res[(sk, "plural")]
        P(f"  {sk:<15}{pct(c['own'], c['n'])}   (open mode {pct(res[(sk, 'open')]['own'], res[(sk, 'open')]['n'])}; default {pct(res[(sk, 'default')]['own'], res[(sk, 'default')]['n'])})")
    P("per language (open_audience, plural family): " + "; ".join(f"{lg} {pct(res[(lg + ':open_audience', 'plural')]['own'], res[(lg + ':open_audience', 'plural')]['n'])}" for lg in ("es", "en", "pt")))
    P("per author  (open_audience, plural family): " + "; ".join(f"{a} {pct(res[(a + ':open_audience', 'plural')]['own'], res[(a + ':open_audience', 'plural')]['n'])}" for a in "ABC"))
    hits = n_old = 0
    for f in glob.glob(os.path.join(ROOT, "data", "**", "*.jsonl"), recursive=True):
        if any(x in f for x in ("use_limits", "names_lower", "recipients")):
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
                v = check(a, b, {"USE_LIMIT_PLURAL"})
            except Exception:                                         # noqa: BLE001
                continue
            n_old += 1
            hits += bool(v)
    rec_n = rec_u = 0
    for path in glob.glob(os.path.join(ROOT, "data", "use_limits_v3", "out_*.jsonl")):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if r.get("recipient_source") and r.get("recipient_relay"):
                rec_n += 1
                rec_u += bool(check(r["recipient_source"], r["recipient_relay"], {"USE_LIMIT_PLURAL"}))
    P(f"equivalent pairs of the older sets with a USE_LIMIT_PLURAL alarm: {hits} of {n_old}; spent v3 set: recipient decoy {pct(rec_u, rec_n)}")
    oa, dc = res[("open_audience", "plural")], res[("decoy", "plural")]
    x1 = oa["own"] / max(oa["n"], 1) >= 0.75
    x2 = dc["own"] / max(dc["n"], 1) <= 0.10
    x3 = (oa["light_own_alone"] + dc["light_own_alone"]) / max(oa["n"] + dc["n"], 1) <= 0.03
    x4 = hits == 0
    x5 = rec_u / max(rec_n, 1) <= 0.03
    P(f"\nX1 {'PASS' if x1 else 'FAIL'}  X2 {'PASS' if x2 else 'FAIL'}  X3 {'PASS' if x3 else 'FAIL'}  X4 {'PASS' if x4 else 'FAIL'}  X5 {'PASS' if x5 else 'FAIL'}")
    P(f"\ndecoy false alarms by USE_LIMIT_PLURAL ({len(fa)}):")
    for m in fa:
        P("  " + " | ".join(str(x)[:115] for x in m))
    P(f"\nmissed audiences ({len(miss)}):")
    for m in miss:
        P("  " + " | ".join(str(x)[:115] for x in m))
    txt = "\n".join(L)
    print(txt)
    if out:
        open(out, "w", encoding="utf-8").write(txt + "\n")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None)
