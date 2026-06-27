"""store.client — the singleton seam to MongoDB Atlas.

`get_db()` is the only place that opens a connection from `MONGODB_URI`. Every
other /store module takes a `db` argument so it stays test-injectable. Collection
names are centralized here so the failures/checks/known_good layout lives in one
place.

motor is lazy: constructing `AsyncIOMotorClient` does not connect, so this is
safe to call at import time and binds to the running event loop on first await.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from config import get_settings

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

_db = None  # process-wide singleton over MONGODB_URI


def get_db() -> "AsyncIOMotorDatabase":
    """Return the shared async Atlas database handle (singleton over MONGODB_URI)."""
    global _db
    if _db is None:
        cfg = get_settings()
        if not cfg.mongodb_uri:
            raise RuntimeError(
                "MONGODB_URI is empty; set it in the environment before calling get_db()."
            )
        from motor.motor_asyncio import AsyncIOMotorClient

        _db = AsyncIOMotorClient(cfg.mongodb_uri)[cfg.atlas_db]
    return _db


def failures_collection(db) -> "AsyncIOMotorCollection":
    """Caught-failure docs (Mongo `_id` == Failure.id); target of the failvec index."""
    return db[get_settings().atlas_collection]


def checks_collection(db) -> "AsyncIOMotorCollection":
    """The rubric: one doc per Check (`_id` == Check.id)."""
    return db["checks"]


def known_good_collection(db) -> "AsyncIOMotorCollection":
    """Held-back known-good AUTOutputs used by is_general / known_good_sample."""
    return db["known_good"]
