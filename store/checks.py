"""store.checks — the rubric read/write path + the one-shot seed() bootstrap.

The rubric is `list[Check]`; get_checks/upsert_check are its async accessors
(`_id` == Check.id). seed() is a synchronous bootstrap that plants the demo's
first check (`numeric-cites-source`) plus a starter failure pool and a held-back
known-good set, so grow()/is_general() have something to chew on from t=0. It is
idempotent (everything upserts by stable id) and safe to re-run.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from store.client import (
    checks_collection,
    failures_collection,
    from_doc,
    known_good_collection,
    to_doc,
)
from store.failures import save_failure
from store.models import AUTOutput, Check, Failure

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_checks(db: "AsyncIOMotorDatabase") -> list[Check]:
    """Return the full rubric as Check objects (`_id` → id)."""
    docs = await checks_collection(db).find().to_list(length=None)
    return [Check(**from_doc(d)) for d in docs]


async def upsert_check(c: Check, db: "AsyncIOMotorDatabase") -> str:
    """Insert or replace a Check by id; return the id."""
    await checks_collection(db).replace_one({"_id": c.id}, to_doc(c), upsert=True)
    return c.id


# ── Seed content (the demo's first check + starters) ─────────────────────────
SEED_CHECK = Check(
    id="numeric-cites-source",
    property=(
        "Every numeric value stated in the claim must appear verbatim in the text "
        "of at least one cited source."
    ),
    rationale=(
        "An uncited number is fabricated authority — the most common and most "
        "damaging failure mode in cited answers."
    ),
    positive_example=(
        "Claim 'Revenue was $4.2B [S2]' where the text of source S2 contains '4.2B', "
        "or a claim that states no specific number at all."
    ),
    negative_example=(
        "Claim 'Revenue was $4.2B [S2]' where no cited source's text contains 4.2B."
    ),
    overfit_risk=(
        "May over-fire on derived or rounded figures (e.g. a percentage computed "
        "from cited numbers) since it tests for the literal, not numeric equivalence."
    ),
)

SEED_FAILURES = [
    Failure(
        id="seed-revenue-uncited",
        input="What was Acme's 2023 revenue?",
        claim="Acme's 2023 revenue was $4.2B [S2].",
        expected="A revenue figure that appears in the cited source's text.",
        actual="$4.2B cited to S2, whose text never mentions 4.2B.",
        why="numeric claim with no supporting source text",
    ),
    Failure(
        id="seed-date-uncited",
        input="When did Acme go public?",
        claim="Acme went public in 2014 [S1].",
        expected="A date that appears in the cited source's text.",
        actual="2014 cited to S1, whose text gives no IPO date.",
        why="numeric (date) claim with no supporting source text",
    ),
]

SEED_KNOWN_GOOD = [
    AUTOutput(
        input="What was Acme's 2023 revenue?",
        claim="Acme's 2023 revenue was $4.2B [S2].",
        output="According to the annual report, Acme's 2023 revenue was $4.2B [S2].",
        sources=[{"id": "S2", "title": "Acme 2023 10-K", "text": "Total revenue for 2023 was $4.2B."}],
    ),
    AUTOutput(
        input="How did Acme describe its 2023 performance?",
        claim="Acme called 2023 a record year [S3].",
        output="Acme described 2023 as a record year for the company [S3].",
        sources=[{"id": "S3", "title": "Press release", "text": "2023 was a record year for Acme."}],
    ),
]


async def _seed(db: "AsyncIOMotorDatabase") -> None:
    await upsert_check(SEED_CHECK, db)
    for f in SEED_FAILURES:
        await save_failure(f, db)
    for i, kg in enumerate(SEED_KNOWN_GOOD):
        doc = kg.model_dump()
        doc["_id"] = f"seed-known-good-{i}"  # stable id keeps re-seeds idempotent
        await known_good_collection(db).replace_one({"_id": doc["_id"]}, doc, upsert=True)


def seed(db: "AsyncIOMotorDatabase") -> None:
    """Idempotently plant the seed Check + starter failures + known-good set.

    Synchronous bootstrap helper: call from a sync context (CLI / startup script),
    not from inside a running event loop.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        raise RuntimeError("seed() must be called from a sync context, not a running event loop.")
    asyncio.run(_seed(db))
