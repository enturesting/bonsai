"""Shared fixtures for the /web suite.

Unit tests run keyless and offline: WEB_MOCK_STREAM forces the scripted mock
eval_stream (so no /loop → Anthropic call), MOCK_AUT gives a deterministic AUT,
and fixtures.load_fixture_questions is monkeypatched to a tiny deterministic pool.
The harness never reaches Mongo/Voyage/Anthropic/Gemini in these tests.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Two fixtures: one failing (numeric mismatch), one clean. Mirrors the real
# fixture dict shape (id, category, question, sources, mock{claim,output,cite_ids}).
FAKE_QUESTIONS = [
    {
        "id": "numeric-mismatch-01",
        "category": "unsupported-numeric",
        "question": "Approximately how many base pairs are in the human genome?",
        "sources": [
            {
                "id": "S1",
                "title": "Human Genome — Size",
                "url": "https://example.org/genome",
                "text": "The human genome consists of approximately 3.1 billion base pairs.",
            }
        ],
        "mock": {
            "claim": "The human genome consists of approximately 3.2 billion base pairs.",
            "output": "The human genome consists of approximately 3.2 billion base pairs [S1].",
            "cite_ids": ["S1"],
        },
        "expected": "Approximately 3.1 billion base pairs.",
        "why": "Numeric claim (3.2B) has no matching figure in the cited source (3.1B).",
    },
    {
        "id": "clean-numeric-01",
        "category": "clean",
        "question": "What primarily causes ocean tides?",
        "sources": [
            {
                "id": "S1",
                "title": "Tides",
                "url": "https://example.org/tides",
                "text": "Tides are primarily caused by the gravitational pull of the Moon.",
            }
        ],
        "mock": {
            "claim": "Tides are primarily caused by the gravitational pull of the Moon.",
            "output": "Tides are primarily caused by the gravitational pull of the Moon [S1].",
            "cite_ids": ["S1"],
        },
    },
]


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Clean, fully-populated (but fake) settings; force offline/mock paths."""
    monkeypatch.setenv("MOCK_AUT", "1")
    monkeypatch.setenv("WEB_MOCK_STREAM", "1")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("VOYAGE_API_KEY", "stub-key")
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key")
    from config import get_settings

    get_settings.cache_clear()
    # Reset the process-wide rubric + live-claim registry so neither tree state nor
    # typed claims bleed between tests (both are module-global).
    from web.state import RUBRIC
    from web.live_claims import LIVE

    RUBRIC.reset()
    LIVE.reset()
    yield
    get_settings.cache_clear()
    RUBRIC.reset()
    LIVE.reset()


@pytest.fixture
def fake_questions(monkeypatch):
    """Patch the ONLY fixtures seam /web uses for the working pool."""
    import fixtures

    monkeypatch.setattr(
        fixtures,
        "load_fixture_questions",
        lambda: [dict(q) for q in FAKE_QUESTIONS],
    )
    return FAKE_QUESTIONS


@pytest.fixture
def client(fake_questions):
    import main

    with TestClient(main.app) as c:
        yield c
