"""TDD for store.failures — save_failure (embed-if-empty, upsert) + known_good_sample."""
from __future__ import annotations

import pytest

import store.failures as failures_mod
from store.client import failures_collection, known_good_collection
from store.models import EMBED_DIM, AUTOutput, Failure


def _failure(id="f1", embedding=None):
    return Failure(
        id=id,
        input="What was 2023 revenue?",
        claim="Revenue was 4.2B.",
        expected="A figure backed by a cited source row.",
        actual="4.2B with no source.",
        why="numeric claim with no supporting source",
        embedding=embedding or [],
    )


@pytest.fixture
def stub_embed(monkeypatch):
    calls = []

    def fake_embed_one(text):
        calls.append(text)
        return [0.25] * EMBED_DIM

    monkeypatch.setattr(failures_mod, "embed_one", fake_embed_one)
    return calls


async def test_save_failure_embeds_when_empty_and_persists_with_mongo_id(mock_db, stub_embed):
    fid = await failures_mod.save_failure(_failure(), mock_db)
    assert fid == "f1"
    assert len(stub_embed) == 1  # embedded exactly once

    doc = await failures_collection(mock_db).find_one({"_id": "f1"})
    assert doc is not None
    assert doc["_id"] == "f1"
    assert "id" not in doc  # not duplicated alongside _id
    assert len(doc["embedding"]) == EMBED_DIM


async def test_save_failure_does_not_reembed_when_embedding_present(mock_db, stub_embed):
    await failures_mod.save_failure(_failure(embedding=[0.9] * EMBED_DIM), mock_db)
    assert stub_embed == []  # never called
    doc = await failures_collection(mock_db).find_one({"_id": "f1"})
    assert doc["embedding"][0] == 0.9


async def test_save_failure_is_idempotent_upsert(mock_db, stub_embed):
    await failures_mod.save_failure(_failure(), mock_db)
    await failures_mod.save_failure(_failure(), mock_db)  # same id again
    assert await failures_collection(mock_db).count_documents({"_id": "f1"}) == 1


async def test_known_good_sample_returns_autoutputs_capped_at_k(mock_db):
    for i in range(5):
        await known_good_collection(mock_db).insert_one(
            {"input": f"q{i}", "claim": f"c{i}", "output": f"o{i}", "sources": []}
        )
    sample = await failures_mod.known_good_sample(mock_db, k=3)
    assert len(sample) == 3
    assert all(isinstance(s, AUTOutput) for s in sample)


async def test_known_good_sample_empty_when_none(mock_db):
    assert await failures_mod.known_good_sample(mock_db) == []
