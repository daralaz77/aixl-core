"""Risk-coverage of a SAME claim, on stored judgments (no model is called): which observable evidence tier makes a "SAME" safe, and how much of the truly-SAME set it covers.
Sets: blind17 (Sonnet, Haiku, Haiku-b) and blind18 (Sonnet, Haiku), labels from the authors' files (115 pairs).  python -m benchmarks.risk_coverage
Tiers (all computable at run time): P = deterministic proof (compare_verified verified) | J+ = every judge SAME and relay_check ok | J = every judge SAME but relay_check flagged
| split = judges disagree | N = every judge says different.  Reported: n, truly SAME, truly DIFF, false-SAME rate with a Wilson 95 % interval."""
import math

from aixl.api.service import compare_verified
from aixl.invariants import relay_check
from benchmarks.layered_eval import SETS, load


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def tier(a, b, votes):
    v = compare_verified(a, b)
    if v.get("equivalent") and v.get("verified"):
        return "P"
    vs = set(votes)
    if vs == {"SAME"}:
        return "J+" if relay_check(a, b)["ok"] else "J"
    if vs <= {"DIFFERENT", "DIFF"}:
        return "N"
    return "split"


def main():
    rows = {}
    for s in SETS:
        labels, texts, judges = load(s)
        for i, (a, b) in texts.items():
            lab = labels.get(i)
            if lab is None:
                continue
            t = tier(a, b, [j.get(i, "") for j in judges.values()])
            r = rows.setdefault(t, {"n": 0, "same": 0, "diff": 0})
            r["n"] += 1
            r["same" if lab == "SAME" else "diff"] += 1
    tot_same = sum(r["same"] for r in rows.values())
    print(f"{'tier':<6}{'n':>4}{'SAME':>6}{'DIFF':>6}   false-SAME if we claim SAME   (Wilson 95 %)")
    cum_same = cum_false = 0
    for t in ("P", "J+", "J", "split", "N"):
        r = rows.get(t, {"n": 0, "same": 0, "diff": 0})
        lo, hi = wilson(r["diff"], r["n"])
        print(f"{t:<6}{r['n']:>4}{r['same']:>6}{r['diff']:>6}   {r['diff']}/{r['n']} = {100 * r['diff'] / max(r['n'], 1):5.1f} %   ({100 * lo:.1f}-{100 * hi:.1f} %)")
    print("\ncumulative claim-SAME policy (add tiers in this order):")
    for t in ("P", "J+", "J", "split"):
        r = rows.get(t, {"n": 0, "same": 0, "diff": 0})
        cum_same += r["same"]; cum_false += r["diff"]
        n = cum_same + cum_false
        lo, hi = wilson(cum_false, n)
        print(f"  up to {t:<5}: covers {cum_same}/{tot_same} true SAME ({100 * cum_same / max(tot_same, 1):.0f} %), false SAME {cum_false}/{n} = {100 * cum_false / max(n, 1):.1f} % ({100 * lo:.1f}-{100 * hi:.1f} %)")


if __name__ == "__main__":
    main()
