"""Risk control for a SAME claim: from a labelled calibration set, choose which evidence tiers may be trusted so that the error rate among the ACCEPTED claims is at most `alpha`, with confidence 1 - `delta`.

Method (fixed-sequence testing, the "learn then test" recipe with exact binomial bounds): tiers are ordered from most to least reliable by a rule fixed BEFORE looking at errors (see `aixl.confidence`). For each prefix of that
order, the accepted set is the union of its tiers; its error count k out of n is turned into a one-sided Clopper-Pearson upper bound; prefixes are tested in order and the first one whose bound exceeds `alpha` stops the walk
(fixed-sequence testing keeps the guarantee without a multiplicity penalty). The certified policy is the longest prefix that passed.
Guarantee (finite sample, no model assumption beyond EXCHANGEABILITY): for a NEW claim drawn from the same distribution as the calibration pairs, P(error | accepted) <= alpha with probability >= 1 - delta over the calibration draw.
What it does NOT give: protection against a distribution shift (other domains, other judges, other vocabularies) — the calibration pairs must look like the traffic. Small sets give loose bounds: certifying alpha = 5 % needs about 60 accepted claims
with no error; 2 errors in 54 only certify about 11 %."""
import math


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), by direct summation in log space (n is small here)."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    total = 0.0
    for i in range(0, k + 1):
        total += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log1p(-p))
    return min(1.0, total)


def clopper_pearson_upper(k: int, n: int, delta: float) -> float:
    """One-sided upper confidence bound on an error probability: the p such that P(X <= k | p) = delta (1.0 when k == n, a rule-of-three style bound when k == 0)."""
    if n <= 0:
        return 1.0
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(80):                                                     # bisection on the monotone map p -> P(X <= k | p)
        mid = (lo + hi) / 2
        if _binom_cdf(k, n, mid) > delta:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def certify(tier_counts: dict, order, alpha: float, delta: float = 0.1) -> dict:
    """`tier_counts`: {tier: (errors, n)}; `order`: tiers from most to least reliable. Returns the certified prefix and the bound of every tested prefix."""
    accepted, k_tot, n_tot, walk = [], 0, 0, []
    for t in order:
        k, n = tier_counts.get(t, (0, 0))
        if n == 0:
            continue
        nk, nn = k_tot + k, n_tot + n
        bound = clopper_pearson_upper(nk, nn, delta)
        walk.append({"prefix": [*accepted, t], "errors": nk, "n": nn, "upper_bound": round(bound, 4), "passes": bound <= alpha})
        if bound > alpha:
            break
        accepted.append(t)
        k_tot, n_tot = nk, nn
    return {"alpha": alpha, "delta": delta, "accepted_tiers": accepted, "errors": k_tot, "n": n_tot, "upper_bound": round(clopper_pearson_upper(k_tot, n_tot, delta), 4) if n_tot else None, "walk": walk,
            "guarantee": "P(error | accepted) <= alpha with probability >= 1 - delta, for claims exchangeable with the calibration set" if accepted else "no tier can be certified at this alpha with this calibration set"}
