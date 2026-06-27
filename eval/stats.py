"""
eval/stats.py — small-N honesty statistics. VERIFICATION-ONLY.

Wilson score CI + paired sign test. At n≈15–40 never quote a bare % — report
direction + a confidence interval. Closed-form Wilson (no statsmodels dep);
scipy.stats.binomtest for the sign test (scipy is in requirements), with a
pure-python fallback.
"""
from __future__ import annotations

import math


def wilson(passes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion (correct at small n / near 0|1)."""
    if n <= 0:
        return (0.0, 1.0)
    p = passes / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (center - margin) / denom
    hi = (center + margin) / denom
    return (max(0.0, lo), min(1.0, hi))


def sign_test(before: list[bool], after: list[bool]) -> dict | None:
    """
    Paired before/after on the SAME gold items. Counts red->green (helped) vs
    green->red (hurt), drops ties, one-sided binomial p-value (H1: helped > hurt).
    Returns None if nothing flipped (no signal).
    """
    if len(before) != len(after):
        raise ValueError("before/after must be the same length (paired on gold items)")
    helped = sum(1 for b, a in zip(before, after) if a and not b)
    hurt = sum(1 for b, a in zip(before, after) if b and not a)
    n = helped + hurt
    if n == 0:
        return None
    try:
        from scipy.stats import binomtest
        p = float(binomtest(helped, n, 0.5, alternative="greater").pvalue)
    except Exception:
        from math import comb
        p = sum(comb(n, k) for k in range(helped, n + 1)) / float(2 ** n)
    return {"helped": helped, "hurt": hurt, "n": n, "p": p}
