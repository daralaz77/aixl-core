"""Risk control for the SAME claim on STORED judgments (no model is called): blind17 and blind18, 115 pairs of other authors.
Expectations written BEFORE running: C1 the exact bound covers (tests/test_risk.py, simulation); C2 calibrating on one set and testing on the other, the realised false-SAME rate among the accepted claims is <= the certified alpha in
BOTH directions; C3 at alpha = 15 % the policy accepts >= 80 % of the truly SAME pairs of the held-out set. Small samples: an indicative check of a statistical guarantee, not a proof for your traffic.   python -m benchmarks.conformal_eval"""
from aixl.risk import certify
from benchmarks.layered_eval import SETS, load
from benchmarks.risk_coverage import tier

ORDER = ["U", "split"]                                          # unanimous judges first; the rule is fixed here, before any error is counted


def tiers_of(set_name):
    labels, texts, judges = load(set_name)
    out = []
    for i, (a, b) in texts.items():
        lab = labels.get(i)
        if lab is None:
            continue
        t = tier(a, b, [j.get(i, "") for j in judges.values()])
        out.append(("U" if t in ("J+", "J") else t, lab == "DIFF"))        # relay_check does not make a unanimous SAME safer (E-RISK-COVERAGE), so J+ and J are one tier
    return out


def counts(rows):
    c = {}
    for t, err in rows:
        k, n = c.get(t, (0, 0))
        c[t] = (k + err, n + 1)
    return c


def main():
    data = {s: tiers_of(s) for s in SETS}
    allrows = [r for rows in data.values() for r in rows]
    print(f"pairs {len(allrows)}; tiers (errors, n): {counts(allrows)}\n")
    print("certified alpha on ALL pairs (delta = 0.1):")
    for alpha in (0.05, 0.08, 0.10, 0.12, 0.15, 0.20):
        r = certify(counts(allrows), ORDER, alpha, 0.1)
        print(f"  alpha {alpha:.2f}: accepted {r['accepted_tiers']}  errors {r['errors']}/{r['n']}  upper bound {r['upper_bound']}")
    print("\nsplit check (calibrate on one set, test on the other):")
    ok = []
    for cal, test in (("blind17", "blind18"), ("blind18", "blind17")):
        for alpha in (0.10, 0.15, 0.20):
            r = certify(counts(data[cal]), ORDER, alpha, 0.1)
            acc = [(t, e) for t, e in data[test] if t in r["accepted_tiers"]]
            true_same = sum(1 for _t, e in data[test] if not e)
            tp = sum(1 for _t, e in acc if not e)
            fa = sum(1 for _t, e in acc if e)
            rate = fa / len(acc) if acc else 0.0
            ok.append((alpha, not acc or rate <= alpha))
            print(f"  calibrate {cal} -> test {test} alpha {alpha:.2f}: accepted tiers {r['accepted_tiers']} (bound {r['upper_bound']}); on the test set accepted {len(acc)}, false SAME {fa} = {100 * rate:.1f} %; "
                  f"true SAME accepted {tp}/{true_same} = {100 * tp / max(true_same, 1):.0f} %")
    print("\nC2 (realised rate <= alpha in every direction and alpha):", "PASS" if all(v for _a, v in ok) else "FAIL")


if __name__ == "__main__":
    main()
