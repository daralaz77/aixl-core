"""aixl.logic on a FRESH set (data/logic_v1/PREREG.md). Run ONCE after FREEZE.json; nothing is tuned after reading.   python -m benchmarks.logic_eval [--out data/logic_v1/RESULT.txt]"""
import collections
import glob
import json
import os
import sys

from aixl.api.service import compare_verified
from aixl.invariants import relay_check
from aixl.logic import logic_compare

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "logic_v1")


def pct(k, n):
    return f"{k}/{n} = {100 * k / max(n, 1):.1f} %"


def old_pairs():
    fe = fd = n = 0
    for f in glob.glob(os.path.join(ROOT, "data", "**", "*.jsonl"), recursive=True):
        if any(x in f for x in ("use_limits", "names_lower", "recipients", "logic_v1")):
            continue
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:                                         # noqa: BLE001
                continue
            a, b = r.get("a") or r.get("text_a"), r.get("b") or r.get("text_b")
            lab = str(r.get("expected_equivalence") or r.get("label")).upper()
            if not a or not b or lab not in ("EQUIVALENT", "SAME", "NOT_EQUIVALENT", "DIFF", "DIFFERENT"):
                continue
            eq = lab in ("EQUIVALENT", "SAME")
            v = logic_compare(a, b)["verdict"]
            n += 1
            fe += (not eq) and v == "EQUIVALENT_LOGIC"
            fd += eq and v == "DIFFERENT_LOGIC"
    return fe, fd, n


def main(out=None):
    rows, bad = [], 0
    for path in sorted(glob.glob(os.path.join(D, "out_*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
                assert all(r.get(k) for k in ("a", "b", "label", "subtype", "lang"))
                r["_a"] = os.path.basename(path)[4]
                rows.append(r)
            except Exception:                                         # noqa: BLE001
                bad += 1
    L = []
    P = L.append
    P(f"records {len(rows)} (malformed {bad}); authors {dict(collections.Counter(r['_a'] for r in rows))}; labels {dict(collections.Counter(r['label'] for r in rows))}")
    res = collections.defaultdict(collections.Counter)
    reasons = collections.Counter()
    wrong = []
    base = collections.Counter()
    for r in rows:
        eq = r["label"].upper() == "EQUIVALENT"
        res_out = logic_compare(r["a"], r["b"])
        v = res_out["verdict"]
        for key in (("all",), ("sub", r["subtype"]), ("lang", r["lang"]), ("label", r["label"].upper())):
            c = res[key]
            c["n"] += 1
            c["decided"] += v != "ABSTAIN"
            c["right"] += (v == "EQUIVALENT_LOGIC" and eq) or (v == "DIFFERENT_LOGIC" and not eq)
            c["false_eq"] += v == "EQUIVALENT_LOGIC" and not eq
            c["false_diff"] += v == "DIFFERENT_LOGIC" and eq
        if v == "ABSTAIN":
            reasons[res_out["reason"][:70]] += 1
        elif not ((v == "EQUIVALENT_LOGIC" and eq) or (v == "DIFFERENT_LOGIC" and not eq)):
            wrong.append((r["label"], r["subtype"], r["lang"], v, r["a"], r["b"]))
        cv = compare_verified(r["a"], r["b"])
        rc = relay_check(r["a"], r["b"])
        base[("cv_proves_eq", eq)] += bool(cv.get("equivalent") and cv.get("verified"))
        base[("cv_inconclusive", eq)] += cv.get("verdict") == "INCONCLUSIVE"
        base[("relay_flags", eq)] += not rc["ok"]
        base[("n", eq)] += 1
    a = res[("all",)]
    P(f"coverage (verdict, not ABSTAIN): {pct(a['decided'], a['n'])}; accuracy among decided: {pct(a['right'], a['decided'])}")
    P(f"label EQUIVALENT: decided {pct(res[('label', 'EQUIVALENT')]['decided'], res[('label', 'EQUIVALENT')]['n'])}; false DIFFERENT_LOGIC {res[('label', 'EQUIVALENT')]['false_diff']}")
    P(f"label DIFFERENT : decided {pct(res[('label', 'DIFFERENT')]['decided'], res[('label', 'DIFFERENT')]['n'])}; false EQUIVALENT_LOGIC {res[('label', 'DIFFERENT')]['false_eq']}")
    P("\nper subtype (decided / right / wrong):")
    for k in sorted(k for k in res if k[0] == "sub"):
        c = res[k]
        P(f"  {k[1]:<24}n {c['n']:>3}  decided {c['decided']:>3}  right {c['right']:>3}  false_eq {c['false_eq']}  false_diff {c['false_diff']}")
    P("per language: " + "; ".join(f"{k[1]} decided {pct(res[k]['decided'], res[k]['n'])}" for k in sorted(k for k in res if k[0] == "lang")))
    P("\nbaselines on the same pairs:")
    P(f"  compare_verified proves EQUIVALENT: on EQUIVALENT pairs {base[('cv_proves_eq', True)]}/{base[('n', True)]}; on DIFFERENT pairs (false proofs) {base[('cv_proves_eq', False)]}/{base[('n', False)]}")
    P(f"  relay_check flags: DIFFERENT pairs {base[('relay_flags', False)]}/{base[('n', False)]}; EQUIVALENT pairs (false alarms) {base[('relay_flags', True)]}/{base[('n', True)]}")
    fe, fd, n_old = old_pairs()
    P(f"older labelled pairs: false EQUIVALENT_LOGIC {fe}, false DIFFERENT_LOGIC {fd}, of {n_old}")
    l1 = a["false_eq"] == 0
    l2 = res[("label", "EQUIVALENT")]["false_diff"] <= 3
    l3 = a["decided"] / max(a["n"], 1) >= 0.50
    l4 = a["right"] / max(a["decided"], 1) >= 0.95
    l5 = fe == 0 and fd == 0
    P("\n" + "  ".join(f"L{i + 1} {'PASS' if v else 'FAIL'}" for i, v in enumerate([l1, l2, l3, l4, l5])))
    P("\nabstention reasons:")
    for k, v in reasons.most_common():
        P(f"  {v:>3}  {k}")
    P(f"\nwrong verdicts ({len(wrong)}):")
    for w in wrong:
        P("  " + " | ".join(str(x)[:110] for x in w))
    txt = "\n".join(L)
    print(txt)
    if out:
        open(out, "w", encoding="utf-8").write(txt + "\n")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None)
