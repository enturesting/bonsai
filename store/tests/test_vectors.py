"""TDD for store.vectors — failvec index def + $vectorSearch retrieval."""
from __future__ import annotations

import pytest

import store.vectors as vectors
from store.models import EMBED_DIM, Failure


def test_index_definition_is_1024_cosine_on_embedding():
    name, definition = vectors.index_definition()
    assert name == "failvec"
    field = definition["fields"][0]
    assert field["type"] == "vector"
    assert field["path"] == "embedding"
    assert field["numDimensions"] == EMBED_DIM == 1024
    assert field["similarity"] == "cosine"


# ── fakes: real $vectorSearch only exists on Atlas, so unit-test the wiring ──
class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs if length is None else self._docs[:length]


class FakeColl:
    name = "failures"

    def __init__(self, docs):
        self._docs = docs
        self.pipeline = None

    def aggregate(self, pipeline):
        self.pipeline = pipeline
        return FakeCursor(self._docs)


class FakeDB:
    def __init__(self, docs):
        self.coll = FakeColl(docs)

    def __getitem__(self, _name):
        return self.coll


@pytest.fixture
def fake_query(monkeypatch):
    vec = [0.5] * EMBED_DIM
    monkeypatch.setattr(vectors, "embed_query", lambda text: vec)
    return vec


async def test_nearest_failures_builds_vectorsearch_pipeline(fake_query):
    db = FakeDB(docs=[])
    await vectors.nearest_failures("a blind spot", db, limit=5, num_candidates=50)
    stage = db.coll.pipeline[0]["$vectorSearch"]
    assert stage["index"] == "failvec"
    assert stage["path"] == "embedding"
    assert stage["queryVector"] == fake_query
    assert stage["limit"] == 5
    assert stage["numCandidates"] == 50


async def test_nearest_failures_returns_failures_with_id_mapped(fake_query):
    docs = [
        {
            "_id": "fail-1",
            "input": "Q?",
            "claim": "Revenue was 4.2B.",
            "expected": "cite a source",
            "actual": "no source",
            "why": "uncited number",
            "embedding": [0.1] * EMBED_DIM,
        }
    ]
    db = FakeDB(docs=docs)
    out = await vectors.nearest_failures("seed", db)
    assert len(out) == 1
    assert isinstance(out[0], Failure)
    assert out[0].id == "fail-1"
    assert out[0].claim == "Revenue was 4.2B."


async def test_nearest_failures_defaults(fake_query):
    db = FakeDB(docs=[])
    await vectors.nearest_failures("seed", db)
    stage = db.coll.pipeline[0]["$vectorSearch"]
    assert stage["limit"] == 12
    assert stage["numCandidates"] == 200
