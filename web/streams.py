"""web/streams.py — pick the eval_stream implementation (Auto policy).

One interface, two backends:
  * real `loop.eval_stream` when the loop is importable AND an ANTHROPIC_API_KEY is
    present (deploy / wired demo), unless explicitly overridden.
  * the offline scripted `web.mock_stream.mock_eval_stream` otherwise — demo
    insurance, and what the unit tests force via WEB_MOCK_STREAM=1.

Resolution is dynamic (reads env each call) so tests and the running process can
flip backends without reimporting.
"""
from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: str) -> bool:
    return value.strip().lower() in _TRUTHY


def use_mock() -> bool:
    if _truthy(os.getenv("WEB_MOCK_STREAM", "")):
        return True
    if not os.getenv("ANTHROPIC_API_KEY"):
        return True  # no key → real loop can't reach Anthropic; fall back to mock.
    try:
        import loop

        return not hasattr(loop, "eval_stream")
    except Exception:
        return True


def resolve_eval_stream():
    """Return the eval_stream callable to drive: (claim_id) -> async iterator[dict]."""
    if use_mock():
        from web.mock_stream import mock_eval_stream

        return mock_eval_stream
    from loop import eval_stream

    return eval_stream
