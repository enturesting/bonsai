"""TDD for store.client — the Mongo connection seam."""
from __future__ import annotations

import pytest

import store.client as client
from config import get_settings


@pytest.fixture(autouse=True)
def _reset_singleton():
    client._db = None
    yield
    client._db = None


def test_get_db_returns_db_named_per_config():
    db = client.get_db()
    assert db.name == "bonsai_test"


def test_get_db_is_singleton():
    assert client.get_db() is client.get_db()


def test_get_db_raises_when_uri_empty(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="MONGODB_URI"):
        client.get_db()


def test_collection_helpers_target_expected_names():
    db = client.get_db()
    assert client.failures_collection(db).name == "failures"
    assert client.checks_collection(db).name == "checks"
    assert client.known_good_collection(db).name == "known_good"
