"""
/fixtures — the agent-under-test (Gemini 3.5 AUT) and the DEV fixture questions.

Public surface (CONTRACTS §3, frozen):
    run_agent(fixture)          -> AUTOutput
    load_fixture_questions()    -> list[dict]
    run_all()                   -> list[AUTOutput]
    seed_failures(db)           -> list[Failure]   (async)

`gemini_answer` stays PRIVATE to fixtures.gemini_client and is NOT exported here.
This package is the ONLY non-Anthropic (Gemini) seam in Bonsai.
"""
from __future__ import annotations

from fixtures.aut import run_agent, run_all, seed_failures
from fixtures.questions import FAILURE_CATEGORIES, load_fixture_questions

__all__ = [
    "FAILURE_CATEGORIES",
    "load_fixture_questions",
    "run_agent",
    "run_all",
    "seed_failures",
]
