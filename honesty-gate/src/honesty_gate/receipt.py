"""honesty_gate.receipt — improvement as direction + Wilson interval, never a bare percent.

Doctrine (ported from the reference implementation's verification-side stats):
at small n (≈15-40 held-out items) a bare percentage overclaims. Every
formatter in this module therefore emits DIRECTION (improved / unchanged /
regressed) plus counts and a 95% Wilson score interval. There is deliberately
NO API that renders the score as a lone percentage — the only percent signs
this module ever prints are the interval bounds.

Stdlib-only by default; `sign_test` uses scipy when present and falls back to
an exact pure-python binomial tail otherwise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple


def wilson(passes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
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


def sign_test(before: Sequence[bool], after: Sequence[bool]) -> Optional[Dict[str, float]]:
    """Paired before/after verdicts on the SAME held-out items. Counts
    red->green (helped) vs green->red (hurt), drops ties, one-sided binomial
    p-value (H1: helped > hurt). Returns None if nothing flipped (no signal)."""
    if len(before) != len(after):
        raise ValueError("before/after must be the same length (paired on the same items)")
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


@dataclass(frozen=True)
class Receipt:
    """A before/after result against a held-out reference set.

    Renders (via `str()` / `format_receipt`) as direction + counts + 95% CI,
    e.g. "improved — 6 → 11 / 15 · 95% CI [48.0%, 89.1%] · 5 helped, 0 hurt".
    A held-out score AGREES with the reference — it never proves honesty, and
    a regression prints "regressed", never dressed up as a gain.
    """

    before: int                              # items green before
    after: int                               # items green after
    n: int                                   # held-out items
    ci: Tuple[float, float]                  # 95% Wilson interval on after/n
    sign: Optional[Dict[str, float]] = None  # {"helped","hurt","n","p"} or None

    @property
    def direction(self) -> str:
        if self.after > self.before:
            return "improved"
        if self.after < self.before:
            return "regressed"
        return "unchanged"

    def __str__(self) -> str:
        return format_receipt(self)


def receipt(before: Sequence[bool], after: Sequence[bool]) -> Receipt:
    """Build a Receipt from paired per-item verdicts (same held-out items,
    same order). Includes the sign test; raises ValueError on length mismatch."""
    b = [bool(x) for x in before]
    a = [bool(x) for x in after]
    sign = sign_test(b, a)  # validates pairing before anything else
    n = len(a)
    return Receipt(before=sum(b), after=sum(a), n=n, ci=wilson(sum(a), n), sign=sign)


def receipt_from_counts(before: int, after: int, n: int) -> Receipt:
    """Build a Receipt when only counts survive (no per-item pairing, so no
    sign test). Still direction + interval — never a bare percent."""
    return Receipt(before=before, after=after, n=n, ci=wilson(after, n), sign=None)


def format_receipt(r: Receipt) -> str:
    """THE formatter — always direction + counts + 95% Wilson CI. There is no
    variant that emits the percentage alone."""
    lo, hi = r.ci
    line = f"{r.direction} — {r.before} → {r.after} / {r.n} · 95% CI [{lo:.1%}, {hi:.1%}]"
    if r.sign is not None:
        line += f" · {r.sign['helped']} helped, {r.sign['hurt']} hurt"
    return line
