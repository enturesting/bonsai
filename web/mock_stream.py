"""web/mock_stream.py — offline demo insurance.

A standalone async generator with the SAME interface as `loop.eval_stream`:
`mock_eval_stream(claim_id)` scripts the CONTRACTS §2 lifecycle so the
red→yellow→green pill flip, the streaming rule-rewrite, and the running score all
demo OFFLINE with no Anthropic/Gemini/Mongo. web.streams swaps in the real
loop.eval_stream behind this same shape when a key is present.

The result is faithful, not random: a clean claim is a false-positive the rewrite
corrects (red→green, score +1); a real failure is confirmed (red→red, score flat).
"""
from __future__ import annotations

import asyncio
import os

import fixtures
from eval.scoring import wilson

# Per-category rule rewrites the grower "streams" while re-deriving the check.
_RULES = {
    "unsupported-numeric": "Numeric claims must cite a source whose text contains the same figure, within rounding.",
    "fabricated-quote": "Any quoted span must appear verbatim in the text of a cited source.",
    "stale-wrong-citation": "Each claim must cite a source whose text actually supports it, not a stale or mismatched one.",
    "single-source-overcite": "Do not attach more citations than the number of sources that genuinely support the claim.",
    "vague-not-checkable": "Reject claims too vague to be checked against any cited source span.",
    "clean": "A supported claim is backed by a verbatim span in at least one cited source.",
}
_DEFAULT_RULE = "Each claim must be supported by a verbatim span in a cited source."


def _delay() -> float:
    """Token cadence for the live demo; 0 in tests (set WEB_MOCK_DELAY for a UI)."""
    try:
        return max(0.0, float(os.getenv("WEB_MOCK_DELAY", "0")))
    except ValueError:
        return 0.0


def _questions() -> list:
    return fixtures.load_fixture_questions()


def _resolve(claim_id: str, questions: list) -> dict:
    return next(
        (q for q in questions if q.get("id") == claim_id),
        questions[0] if questions else {},
    )


def _tokens(text: str) -> list:
    # Word-by-word, keeping the trailing space so beforeend reads naturally.
    return [w + " " for w in text.split()]


def _pill(claim_id: str, color: str, label: str) -> dict:
    return {"event": "pill", "data": {"color": color, "check_id": claim_id, "label": label}}


async def mock_eval_stream(claim_id: str):
    delay = _delay()
    try:
        questions = _questions()
        q = _resolve(claim_id, questions)
        category = q.get("category", "")
        passed = category == "clean"

        yield _pill(claim_id, "yellow", "CHECKING…")

        rule = _RULES.get(category, _DEFAULT_RULE)
        for tok in _tokens(rule):
            if delay:
                await asyncio.sleep(delay)
            yield {"event": "chunk", "data": {"token": tok}}

        if delay:
            await asyncio.sleep(delay)
        yield _pill(claim_id, "green" if passed else "red", "GREEN" if passed else "RED")

        # Honest counts: greens among the working pool. A corrected false-positive
        # (clean claim) lifts the count by one; a confirmed failure leaves it flat.
        n = max(1, len(questions))
        green_total = sum(1 for x in questions if x.get("category") == "clean")
        after = green_total
        before = green_total - 1 if passed else green_total
        before = max(0, before)
        lo, hi = wilson(after, n)
        yield {
            "event": "score",
            "data": {"passed": passed, "before": before, "after": after, "n": n, "ci": [lo, hi]},
        }
        yield {"event": "done", "data": {}}
    except Exception as exc:  # mirror eval_stream: error THEN done, so the SSE closes
        yield {"event": "error", "data": {"message": str(exc)}}
        yield {"event": "done", "data": {}}
