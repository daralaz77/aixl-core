"""UNION (closed audience list + plural head) on a NEW fresh set (data/use_limits_v10/PREREG.md). Run ONCE after FREEZE.json; nothing is tuned after reading.
python -m benchmarks.use_limit_union_eval [--out data/use_limits_v10/RESULT.txt]"""
import collections
import glob
import json
import os
import sys

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_OPEN, RELAY_FAMILIES_PLURAL, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "use_limits_v10")
AUD = {"USE_LIMIT", "USE_LIMIT_PLURAL"}
ARMS = (("default", RELAY_FAMILIES, {"USE_LIMIT"}), ("union", RELAY_FAMILIES_PLURAL, AUD), ("open", RELAY_FAMILIES_OPEN, {"USE_LIMIT", "USE_LIMIT_OPEN"}))


def pct(k, n):
    return f"{k}/{n} = {100 * k / max(n, 1):.1f} %"


def old_pairs_alarms():
    hits = n = 0
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
                v = {x[0] for x in check(a, b, RELAY_FAMILIES_PLURAL)}
            except Exception:                                         # noqa: BLE001
                continue
            n += 1
            hits += bool(v & AUD)
    return hits, n


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
            for key in ((r["kind"], arm), (r["subkind"], arm), (r["lang"] + ":" + r["kind"], arm)):
                c = res[key]
                c["n"] += 1
                c["drop"] += bool(drop)
                c["own"] += bool(drop & own)
                c["light_own_alone"] += bool(light) and light <= own
            if arm == "union":
                if r["kind"] == "open_audience" and not (drop & AUD):
                    miss.append((r["subkind"], r["lang"], r.get("complement"), r["source"]))
                if r["kind"] == "decoy" and (drop & AUD):
                    fa.append((r["subkind"], r["lang"], r.get("complement"), r["source"]))
    for k in ("open_audience", "decoy"):
        for arm, _f, _o in ARMS:
            c = res[(k, arm)]
            P(f"{k:<14}{arm:<8} flagged by the audience families {pct(c['own'], c['n'])}; any family {pct(c['drop'], c['n'])}; faithful_light by them alone {pct(c['light_own_alone'], c['n'])}")
    P("\nper subkind (union / default / open):")
    for sk in ("plural_group", "singular_group", "other", "plural_event"):
        u, d, o = res[(sk, "union")], res[(sk, "default")], res[(sk, "open")]
        P(f"  {sk:<15}union {pct(u['own'], u['n'])}; default {pct(d['own'], d['n'])}; open {pct(o['own'], o['n'])}")
    P("per language (open_audience, union): " + "; ".join(f"{lg} {pct(res[(lg + ':open_audience', 'union')]['own'], res[(lg + ':open_audience', 'union')]['n'])}" for lg in ("es", "en", "pt")))
    hits, n_old = old_pairs_alarms()
    rec_n = rec_u = 0
    for path in glob.glob(os.path.join(ROOT, "data", "use_limits_v3", "out_*.jsonl")):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if r.get("recipient_source") and r.get("recipient_relay"):
                rec_n += 1
                rec_u += bool(check(r["recipient_source"], r["recipient_relay"], AUD))
    P(f"equivalent pairs of the older sets with an audience alarm: {hits} of {n_old}; spent v3 set: recipient decoy {pct(rec_u, rec_n)}")
    oa, ot = res[("open_audience", "union")], res[("other", "union")]
    en = res[("en:open_audience", "union")]
    lt = (oa["light_own_alone"] + res[("decoy", "union")]["light_own_alone"]) / max(oa["n"] + res[("decoy", "union")]["n"], 1)
    y = [oa["own"] / max(oa["n"], 1) >= 0.75, ot["own"] / max(ot["n"], 1) <= 0.10, en["own"] / max(en["n"], 1) >= 0.60, lt <= 0.03, hits == 0, rec_u / max(rec_n, 1) <= 0.03]
    P("\n" + "  ".join(f"Y{i + 1} {'PASS' if v else 'FAIL'}" for i, v in enumerate(y)))
    P(f"\ndecoy false alarms by the union ({len(fa)}):")
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
