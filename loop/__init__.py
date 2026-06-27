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

__all__ = [
    "HAIKU",
    "OPUS",
    "CONF_FLOOR",
    "deterministic",
    "haiku_check",
    "opus_check",
    "run_check",
]
