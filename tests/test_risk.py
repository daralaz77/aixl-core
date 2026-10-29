import random

import pytest

from aixl.risk import certify, clopper_pearson_upper


def test_known_values():
    assert clopper_pearson_upper(0, 29, 0.05) == pytest.approx(1 - 0.05 ** (1 / 29), abs=1e-6)       # closed form for zero errors
    assert clopper_pearson_upper(0, 0, 0.1) == 1.0 and clopper_pearson_upper(5, 5, 0.1) == 1.0


def test_bound_is_self_consistent():
    """the bound p satisfies P(X <= k | p) = delta (that is what a one-sided Clopper-Pearson bound is)."""
    from aixl.risk import _binom_cdf
    for k, n, d in ((2, 54, 0.10), (1, 18, 0.05), (7, 120, 0.2)):
        assert _binom_cdf(k, n, clopper_pearson_upper(k, n, d)) == pytest.approx(d, abs=1e-6)


def test_bound_is_monotone():
    assert clopper_pearson_upper(1, 30, 0.1) < clopper_pearson_upper(2, 30, 0.1) < clopper_pearson_upper(3, 30, 0.1)
    assert clopper_pearson_upper(2, 100, 0.1) < clopper_pearson_upper(2, 30, 0.1)


def test_coverage_in_simulation():
    """The bound must exceed the true error rate in at least 1 - delta of the calibration draws (it is conservative: usually more)."""
    rng = random.Random(7)
    delta, n, p, trials = 0.10, 40, 0.07, 600
    covered = sum(clopper_pearson_upper(sum(rng.random() < p for _ in range(n)), n, delta) >= p for _ in range(trials))
    assert covered / trials >= 1 - delta


def test_certify_walks_in_order_and_stops():
    counts = {"U": (2, 54), "split": (9, 11)}
    r = certify(counts, ["U", "split"], alpha=0.12, delta=0.1)
    assert r["accepted_tiers"] == ["U"] and r["errors"] == 2 and r["n"] == 54 and r["upper_bound"] < 0.12
    assert certify(counts, ["U", "split"], alpha=0.05, delta=0.1)["accepted_tiers"] == []              # 2 errors in 54 cannot certify 5 %
    assert "no tier" in certify(counts, ["U", "split"], alpha=0.05)["guarantee"]


def test_fixed_sequence_stops_at_the_first_failure():
    """a small first tier with one error has a wide bound and stops the walk even if a bigger later prefix would pass: the order is fixed before looking at errors."""
    assert certify({"J+": (1, 18), "J": (1, 36)}, ["J+", "J"], alpha=0.15, delta=0.1)["accepted_tiers"] == []


def test_a_bad_tier_never_rides_in_on_good_ones():
    counts = {"A": (0, 200), "B": (50, 100)}
    assert certify(counts, ["A", "B"], alpha=0.05)["accepted_tiers"] == ["A"]
