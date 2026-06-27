"""Tests for seed_failures — the initial failure-pool seeder (fixtures.aut)."""
from __future__ import annotations

import pytest

import store
from store.models import Failure
from fixtures.aut import seed_failures
from fixtures.questions import load_fixture_questions


@pytest.fixture
def captured_saves(monkeypatch):
    monkeypatch.setenv("MOCK_AUT", "1")
    calls = []

    async def fake_save_failure(f, db):
        calls.append((f, db))
        return f.id

    # seed_failures does `from store import save_failure` at call time.
    monkeypatch.setattr(store, "save_failure", fake_save_failure, raising=False)
    return calls


@pytest.mark.asyncio
async def test_seeds_only_designed_failures(captured_saves):
    sentinel_db = object()
    saved = await seed_failures(sentinel_db)

    n_failures = sum(1 for q in load_fixture_questions() if q["category"] != "clean")
    assert len(saved) == n_failures
    assert all(isinstance(f, Failure) for f in saved)
    # nothing clean leaked into the pool
    assert all(not f.id.endswith(("clean-numeric-01", "clean-quote-01", "clean-multi-01"))
               for f in saved)


@pytest.mark.asyncio
async def test_each_failure_is_persisted_via_store(captured_saves):
    sentinel_db = object()
    saved = await seed_failures(sentinel_db)

    assert len(captured_saves) == len(saved)
    assert all(db is sentinel_db for _, db in captured_saves)


@pytest.mark.asyncio
async def test_seeded_failures_carry_diagnosis_and_no_embedding(captured_saves):
    saved = await seed_failures(object())
    for f in saved:
        assert f.id.startswith("seed-")
        assert f.why and f.expected
        assert f.claim and f.actual
        assert f.embedding == []        # store.save_failure embeds on write, not here
