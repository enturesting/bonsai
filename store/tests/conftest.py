"""Shared test fixtures for the /store suite.

Unit tests run keyless and Atlas-less: a mongomock-motor database stands in for
Atlas, and the Voyage client is stubbed (see `stub_voyage`). The single real
integration test is gated behind the `RUN_ATLAS_IT=1` env flag.
"""
from __future__ import annotations

import os

import pytest

from config import get_settings


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    """Give every test a clean, fully-populated (but fake) settings object.

    config.get_settings() is lru_cached, so we clear it and feed dummy creds via
    the environment. Real values are never needed for the mocked unit tests.
    """
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("ATLAS_DB", "bonsai_test")
    monkeypatch.setenv("ATLAS_COLLECTION", "failures")
    monkeypatch.setenv("ATLAS_VECTOR_INDEX", "failvec")
    monkeypatch.setenv("VOYAGE_API_KEY", "stub-key")
    monkeypatch.setenv("VOYAGE_MODEL", "voyage-3")
    monkeypatch.setenv("VOYAGE_DIM", "1024")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_db():
    """A fresh mongomock-motor database (async, Atlas-shaped, no $vectorSearch)."""
    from mongomock_motor import AsyncMongoMockClient

    client = AsyncMongoMockClient()
    return client["bonsai_test"]


def atlas_it():
    """Skip marker for the one real-Atlas integration test."""
    return pytest.mark.skipif(
        os.getenv("RUN_ATLAS_IT") != "1",
        reason="set RUN_ATLAS_IT=1 (and real MONGODB_URI/VOYAGE_API_KEY) to run Atlas integration test",
    )
