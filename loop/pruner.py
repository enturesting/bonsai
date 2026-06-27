"""Pruner — drop checks that no longer discriminate, over the WORKING pool.

A check that passes >95% of items never fires (no signal, dead weight); one that
passes <5% misfires constantly (overfit or broken). The 5–95% band is where checks
separate good outputs from bad. Prune runs over the working failure pool, NEVER the
gold set. See CONTRACTS §3 /loop and build-cheat-sheet §2c.
"""
from __future__ import annotations

from store.models import AUTOutput, Check

from .checker import run_check

PRUNE_HI, PRUNE_LO = 0.95, 0.05


def prune(rubric: list[Check], items: list[AUTOutput]) -> list[Check]:
    if not items:
        return rubric  # no evidence to prune on — keep the rubric intact
    keep = []
    for c in rubric:
        rate = sum(1 for it in items if run_check(c, it.claim, it).passed) / len(items)
        if rate > PRUNE_HI:   # always passes → no discriminating signal
            continue
        if rate < PRUNE_LO:   # always fails → overfit or broken
            continue
        keep.append(c)
    return keep
