"""Worst-case input budgets (OSTIF guide ch.4/5; CodeQL py/polynomial-redos alerts, 2026-11-05).

Before the fixes `to_semantic('9' * 2000)` took 19 s (cubic: 4000 digits = 150 s) and `compare_texts('9' * 16384)` raised ValueError after 3 s.
The service caps its input at AIXL_MAX_INPUT_CHARS = 16384, so these budgets are checked at sizes where the old code was already unusable
and the new code is far inside the limit (time limits are generous to survive a slow CI machine)."""
import time

import pytest

import aixl
from aixl.semantic import compare_texts

BUDGET_S = 6.0


def _timed(fn):
    t0 = time.time()
    out = fn()
    return out, time.time() - t0


@pytest.mark.parametrize("unit,count", [("9", 3000), ("9,", 1500), ("9.", 1500), ("a9", 1500), ("+", 3000), ("-", 3000), ("  ", 1500), ("\t", 3000)])
def test_adversarial_runs_stay_inside_the_budget(unit, count):
    text = unit * count
    for fn in (lambda: aixl.to_semantic(text), lambda: compare_texts(text, "Send the report."), lambda: aixl.relay_check("Send the report.", text)):
        _, dt = _timed(fn)
        assert dt < BUDGET_S, f"{unit!r} x {count}: {dt:.1f}s"


def test_a_digit_run_longer_than_any_integer_does_not_crash():
    assert compare_texts("9" * 16384, "Send the report.").verdict in ("EQUIVALENT", "NOT_EQUIVALENT", "INCONCLUSIVE")
    assert compare_texts("9" * 5000, "9" * 5000).verdict == "EQUIVALENT"
