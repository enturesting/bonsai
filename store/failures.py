"""store.failures — persist caught failures + sample held-back known-good outputs.

save_failure() is the write path for the failure pool that grow() clusters over:
it embeds the failure (document side) if no vector is present yet, then upserts
by id so re-catching the same failure stays a single doc. known_good_sample()
returns the held-back passers is_general() uses to reject overfit checks.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from store.client import (
    drop_id,
    failures_collection,
    known_good_collection,
    to_doc,
)
from store.embed import embed_one
from store.models import AUTOutput, Failure

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase


def _failure_text(f: Failure) -> str:
    """The text we embed for a failure (document side).

    Joins the semantic core of the failure — the triggering question, the
    unsupported claim, and the one-line diagnosis — so the failvec neighborhood
    clusters by *kind* of mistake, which is what grow() searches over.
    """
    return "\n".join([f.input, f.claim, f.why])


async def save_failure(f: Failure, db: "AsyncIOMotorDatabase") -> str:
    """Embed the failure if it has no vector yet, upsert by id, return the id."""
    if not f.embedding:
        f.embedding = embed_one(_failure_text(f))
    doc = to_doc(f)  # _id == f.id
    await failures_collection(db).replace_one({"_id": f.id}, doc, upsert=True)
    return f.id


async def known_good_sample(db: "AsyncIOMotorDatabase", k: int = 8) -> list[AUTOutput]:
    """Return up to k held-back known-good AUTOutputs (for is_general gating)."""
    docs = await known_good_collection(db).find().to_list(length=k)
    return [AUTOutput(**drop_id(d)) for d in docs[:k]]
