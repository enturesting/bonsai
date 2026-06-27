"""
eval/scoring.py — score the rubric against the FROZEN, human-authored gold set.

VERIFICATION ONLY. The honesty gate: /loop must NEVER import this module or read
eval/gold/*.json. Gold is touched exactly once — here, at scoring time — to produce
precision/direction + Wilson CIs. (Enforced by eval/tests/test_honesty_gate.py.)
"""
from __future__ import annotations

import glob
import json
import os
from typing import Callable

from store.models import Check, AUTOutput, Source
from eval.stats import wilson, sign_test

GOLD_DIR = os.path.join(os.path.dirname(__file__), "gold")


def load_gold(gold_dir: str = GOLD_DIR) -> list[dict]:
    """Load every frozen gold item from eval/gold/*.json (read-only, sorted by filename)."""
    items: list[dict] = []
    for path in sorted(glob.glob(os.path.join(gold_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            items.append(json.load(f))
    return items


def _gold_to_output(item: dict) -> AUTOutput:
    """
    Build an AUTOutput from a gold item so the rubric's checks can be applied to it.
    Uses the gold's primary supported claim + its supporting quotes as the cited sources.
    (v1 scorer: one claim per item — the first must_support entry.)
    """
    sources: list[Source] = []
    for i, ms in enumerate(item.get("must_support", []), start=1):
        sources.append(Source(
            id=ms.get("source_url") or f"S{i}",
            title="",
            url=ms.get("source_url", ""),
            text=ms.get("supporting_quote", ""),
        ))
    must = item.get("must_support") or []
    claim = must[0]["claim"] if must else item.get("reference_answer", "")
    return AUTOutput(
        input=item.get("question", ""),
        claim=claim,
        output=item.get("reference_answer", ""),
        sources=sources,
    )


def score_rubric(rubric: list[Check], gold: list[dict],
                 run_check: Callable | None = None) -> list[bool]:
    """
    Per-gold-item green/red: does the harness verdict AGREE with the human label?
      expected_verdict 'pass' -> green when ALL checks pass.
      expected_verdict 'fail' -> green when AT LEAST ONE check fails (harness caught it).
    run_check is injected for testing; defaults to loop.checker.run_check (lazy import so
    /eval imports even before /loop exists, and so importing /eval can't pull in the loop).
    """
    if run_check is None:
        from loop.checker import run_check as run_check  # noqa: lazy — keeps /eval standalone
    results: list[bool] = []
    for item in gold:
        output = _gold_to_output(item)
        verdicts = [run_check(c, output.claim, output) for c in rubric]
        all_pass = all(v.passed for v in verdicts) if verdicts else True
        expected_pass = item.get("expected_verdict", "pass") == "pass"
        results.append(all_pass if expected_pass else (not all_pass))
    return results


def headline(before: list[bool], after: list[bool]) -> dict:
    """
    The honesty numbers for the slide / SSE `score` event. Counts + Wilson CI, never a bare %.
    Returns {"before","after","n","ci":[lo,hi],"sign_test":{...}|None}.
    """
    n = len(after)
    lo, hi = wilson(sum(after), n)
    return {
        "before": sum(before),
        "after": sum(after),
        "n": n,
        "ci": [round(lo, 3), round(hi, 3)],
        "sign_test": sign_test(before, after),
    }
