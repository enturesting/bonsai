"""TDD for store.checks — get_checks / upsert_check + seed() bootstrap."""
from __future__ import annotations

import asyncio

import pytest

import store.checks as checks_mod
from store.checks import get_checks, upsert_check
from store.client import failures_collection, known_good_collection
from store.models import EMBED_DIM, Check


def _check(id="numeric-cites-source"):
    return Check(
        id=id,
        property="Every numeric value in the claim appears in a cited source's text.",
        rationale="Uncited numbers are fabricated authority.",
        positive_example="'Revenue was 4.2B [S2]' where S2 text contains '4.2B'.",
        negative_example="'Revenue was 4.2B [S2]' where no source text contains 4.2B.",
        overfit_risk="May over-fire on derived/rounded figures.",
    )


async def test_upsert_check_roundtrips_with_id(mock_db):
    cid = await upsert_check(_check(), mock_db)
    assert cid == "numeric-cites-source"
    out = await get_checks(mock_db)
    assert len(out) == 1
    assert isinstance(out[0], Check)
    assert out[0].id == "numeric-cites-source"
    assert out[0].property.startswith("Every numeric value")


async def test_upsert_check_is_idempotent(mock_db):
    await upsert_check(_check(), mock_db)
    await upsert_check(_check(), mock_db)
    assert await checks_mod.checks_collection(mock_db).count_documents({}) == 1


async def test_get_checks_empty(mock_db):
    assert await get_checks(mock_db) == []


# ── seed() is the sync bootstrap; stub Voyage so starters embed offline ──
@pytest.fixture(autouse=True)
def _stub_embed(monkeypatch):
    import store.failures as failures_mod

    monkeypatch.setattr(failures_mod, "embed_one", lambda text: [0.1] * EMBED_DIM)


def test_seed_creates_seed_check_and_starters(mock_db):
    checks_mod.seed(mock_db)

    async def _read():
        checks = await get_checks(mock_db)
        n_fail = await failures_collection(mock_db).count_documents({})
        n_good = await known_good_collection(mock_db).count_documents({})
        return checks, n_fail, n_good

    checks, n_fail, n_good = asyncio.run(_read())
    assert any(c.id == "numeric-cites-source" for c in checks)
    assert n_fail >= 1  # starter failure pool to cluster over
    assert n_good >= 1  # held-back known-good for is_general


def test_seed_is_idempotent(mock_db):
    checks_mod.seed(mock_db)
    checks_mod.seed(mock_db)

    async def _counts():
        seed_checks = [c for c in await get_checks(mock_db) if c.id == "numeric-cites-source"]
        return len(seed_checks), await failures_collection(mock_db).count_documents({})

    n_seed_check, n_fail_after = asyncio.run(_counts())
    assert n_seed_check == 1  # not duplicated

    checks_mod.seed(mock_db)
    n_fail_after_third = asyncio.run(failures_collection(mock_db).count_documents({}))
    assert n_fail_after == n_fail_after_third  # failure pool stable across re-seeds
