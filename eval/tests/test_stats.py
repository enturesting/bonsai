from eval.stats import wilson, sign_test


def test_wilson_brackets_point_estimate():
    lo, hi = wilson(27, 31)
    assert 0.0 <= lo <= hi <= 1.0
    assert lo < 27 / 31 < hi


def test_wilson_edges():
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(0, 20)
    assert lo == 0.0 and hi < 1.0
    lo2, hi2 = wilson(20, 20)
    assert hi2 > 0.99 and lo2 > 0.0  # Wilson upper → 1.0 (float ~0.9999…)


def test_sign_test_direction():
    before = [False, False, True, True, False]
    after = [True, True, True, True, False]  # 2 helped, 0 hurt
    r = sign_test(before, after)
    assert r["helped"] == 2 and r["hurt"] == 0 and r["n"] == 2
    assert 0.0 <= r["p"] <= 1.0


def test_sign_test_no_flip_returns_none():
    assert sign_test([True, False, True], [True, False, True]) is None
