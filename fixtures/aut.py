"""
fixtures/aut.py — the agent-under-test (AUT) seam.

`run_agent` is the ONLY Gemini call site (it delegates to the private
fixtures.gemini_client.gemini_answer). With MOCK_AUT set it instead replays a
deterministic, no-API answer scripted in the fixture so /loop and /web can develop
offline. Either way it returns an AUTOutput whose `sources` are the *cited* sources
with full `text`, so deterministic checks can match verbatim quotes.

`seed_failures` runs the AUT over the DEV pool and seeds the initial failure
collection in Atlas. /fixtures owns the ground truth of which fixtures are designed
failures (it authored them), so it builds Failure docs from that annotation rather
than importing /loop's checkers. The only /store touch here is store.save_failure,
imported lazily so this package stays importable before /store is built.
"""
from __future__ import annotations

import os

from config import get_settings
from store.models import AUTOutput, Source
from fixtures.questions import load_fixture_questions


def _mock_enabled() -> bool:
    """True when the deterministic offline AUT should be used.

    An explicit MOCK_AUT env var wins (so tests can toggle it without busting the
    cached Settings); otherwise fall back to the configured default.
    """
    raw = os.environ.get("MOCK_AUT")
    if raw is not None:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return get_settings().mock_aut


def _candidate_sources(fixture: dict) -> "list[Source]":
    return [Source(**s) for s in fixture.get("sources", [])]


def _mock_agent(fixture: dict) -> AUTOutput:
    """Replay the fixture's scripted answer — fully deterministic, no API call."""
    mock = fixture["mock"]
    by_id = {s["id"]: s for s in fixture.get("sources", [])}
    cited = [Source(**by_id[cid]) for cid in mock["cite_ids"] if cid in by_id]
    return AUTOutput(
        input=fixture["question"],
        claim=mock["claim"],
        output=mock["output"],
        sources=cited,
    )


def run_agent(fixture: dict) -> AUTOutput:
    """Answer one fixture with the Gemini 3.5 AUT (or the MOCK_AUT replay)."""
    if _mock_enabled():
        return _mock_agent(fixture)
    from fixtures.gemini_client import gemini_answer  # private real-path seam
    return gemini_answer(fixture["question"], _candidate_sources(fixture))


def run_all() -> "list[AUTOutput]":
    """Run the AUT over the entire DEV fixture pool."""
    return [run_agent(fx) for fx in load_fixture_questions()]
