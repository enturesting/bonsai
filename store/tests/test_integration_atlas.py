"""Real-Atlas + real-Voyage integration test (gated).

Run explicitly against live infrastructure:

    RUN_ATLAS_IT=1 MONGODB_URI=... VOYAGE_API_KEY=... \
        .venv/bin/python -m pytest store/tests/test_integration_atlas.py -v

Exercises the whole seam end-to-end: real 1024-dim embeddings, ensure_index(),
save_failure() upsert, and $vectorSearch retrieval. $vectorSearch is eventually
consistent, so retrieval is polled briefly before asserting.
"""
from __future__ import annotations

import asyncio

import pytest

from store import (
    EMBED_DIM,
    embed_one,
    embed_query,
    ensure_index,
    get_db,
    nearest_failures,
    save_failure,
)
from store.client import failures_collection
from store.models import Failure
from store.tests.conftest import requires_atlas

pytestmark = [pytest.mark.atlas_it, requires_atlas]

_MARKER = "zzz-bonsai-it-marker"


def test_real_embeddings_are_1024_and_asymmetric():
    d = embed_one("a stored failure document")
    q = embed_query("a retrieval query")
    assert len(d) == EMBED_DIM == 1024
    assert len(q) == EMBED_DIM


def test_ensure_index_is_idempotent():
    ensure_index()
    ensure_index()  # second call must not raise


async def test_save_then_vector_search_roundtrip():
    db = get_db()
    fid = "it-revenue-uncited"
    failure = Failure(
        id=fid,
        input=f"{_MARKER}: What was the reported revenue?",
        claim=f"{_MARKER}: Revenue was $9.9B with no cited source.",
        expected="A figure that appears in a cited source's text.",
        actual="$9.9B with no source row.",
        why="numeric claim with no supporting source text",
    )
    try:
        returned = await save_failure(failure, db)
        assert returned == fid

        found = None
        for _ in range(20):  # poll: $vectorSearch indexing is eventually consistent
            hits = await nearest_failures(failure.claim, db, limit=12)
            found = next((h for h in hits if h.id == fid), None)
            if found is not None:
                break
            await asyncio.sleep(1.0)

        assert found is not None, "saved failure never became searchable via failvec"
        assert found.claim == failure.claim
    finally:
        await failures_collection(db).delete_one({"_id": fid})
