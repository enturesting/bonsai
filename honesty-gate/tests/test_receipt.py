"""honesty_gate.receipt — direction + Wilson interval, never a bare percent.

The load-bearing property: no string this module produces states the score as
a lone percentage — every rendered claim carries direction + counts + 95% CI.
"""
import pytest

from honesty_gate import (
    Receipt,
    format_receipt,
    receipt,
    receipt_from_counts,
    sign_test,
    wilson,
)


def test_wilson_brackets_point_estimate():
    lo, hi = wilson(11, 15)
    assert 0.0 <= lo <= hi <= 1.0
    assert lo < 11 / 15 < hi


def test_wilson_edges():
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(0, 20)
    assert lo == 0.0 and hi < 1.0
    lo2, hi2 = wilson(20, 20)
    assert hi2 > 0.99 and lo2 > 0.0


def test_sign_test_direction_and_no_flip():
    r = sign_test([False, False, True, True, False], [True, True, True, True, False])
    assert r["helped"] == 2 and r["hurt"] == 0 and r["n"] == 2
    assert 0.0 <= r["p"] <= 1.0
    assert sign_test([True, False], [True, False]) is None


def test_sign_test_requires_paired_lists():
    with pytest.raises(ValueError):
        sign_test([True], [True, False])
    with pytest.raises(ValueError):
        receipt([True], [True, False])


def test_receipt_from_paired_verdicts():
    before = [True] * 6 + [False] * 9
    after = [True] * 11 + [False] * 4
    r = receipt(before, after)
    assert (r.before, r.after, r.n) == (6, 11, 15)
    assert r.direction == "improved"
    assert r.sign["helped"] == 5 and r.sign["hurt"] == 0
    assert r.ci == wilson(11, 15)


def test_direction_covers_all_three_branches():
    assert receipt_from_counts(6, 11, 15).direction == "improved"
    assert receipt_from_counts(11, 11, 15).direction == "unchanged"
    assert receipt_from_counts(11, 6, 15).direction == "regressed"


def test_formatter_always_emits_direction_plus_interval_never_a_bare_percent():
    s = format_receipt(receipt([True] * 6 + [False] * 9, [True] * 11 + [False] * 4))
    assert s.startswith("improved — 6 → 11 / 15")
    assert "95% CI [" in s
    assert "5 helped, 0 hurt" in s
    # every % in the output is an interval bound (plus the CI label itself)
    inside_ci = s.split("95% CI [", 1)[1].split("]", 1)[0]
    assert inside_ci.count("%") == 2
    assert s.count("%") == 1 + inside_ci.count("%")


def test_regression_is_reported_as_regression_never_dressed_as_gain():
    s = str(receipt_from_counts(11, 6, 15))
    assert s.startswith("regressed — 11 → 6 / 15")
    assert "95% CI [" in s


def test_unchanged_and_zero_n_still_render_with_interval():
    assert str(receipt_from_counts(4, 4, 9)).startswith("unchanged — 4 → 4 / 9")
    s = str(receipt_from_counts(0, 0, 0))
    assert "95% CI [0.0%, 100.0%]" in s  # n=0: maximally uncertain, honestly so


def test_str_is_the_formatter():
    r = Receipt(before=2, after=3, n=5, ci=wilson(3, 5))
    assert str(r) == format_receipt(r)
