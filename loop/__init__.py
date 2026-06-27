"""Bonsai /loop — the eval engine (checker, skeptic, grower, pruner, SSE stream).

The frozen public surface (CONTRACTS §3 /loop). Models come from `store.models`;
there is no `loop/models.py`. /loop never imports /eval and never reads gold.
"""
from __future__ import annotations

from .checker import (
    CONF_FLOOR,
    HAIKU,
    OPUS,
    deterministic,
    haiku_check,
    opus_check,
    run_check,
)
from .engine import eval_stream, rewrite_rule_stream, run_checker
from .grower import grow, is_general, mint_check, mint_check_from_miss
from .pruner import PRUNE_HI, PRUNE_LO, prune
from .skeptic import skeptic

__all__ = [
    "HAIKU",
    "OPUS",
    "CONF_FLOOR",
    "PRUNE_HI",
    "PRUNE_LO",
    "deterministic",
    "haiku_check",
    "opus_check",
    "run_check",
    "skeptic",
    "mint_check",
    "mint_check_from_miss",
    "is_general",
    "grow",
    "prune",
    "rewrite_rule_stream",
    "run_checker",
    "eval_stream",
]
