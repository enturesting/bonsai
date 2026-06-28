"""store.vectors — the failvec Atlas Vector Search index + nearest-failure retrieval.

`ensure_index()` is a synchronous bootstrap helper (pymongo): it creates the
`failvec` vectorSearch index over the failures collection, idempotently.
`nearest_failures()` is the async query path used by /loop's grow(): embed the
seed as a *query* (asymmetric) and run $vectorSearch on failvec.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from config import get_settings
from store.client import failures_collection, from_doc
from store.embed import embed_query
from store.models import EMBED_DIM, Failure

if TYPE_CHECKING:  # pragma: no cover
    from motor.motor_asyncio import AsyncIOMotorDatabase


def index_definition() -> tuple[str, dict]:
    """Return (index_name, definition) for the failvec vectorSearch index.

    Pure + config-driven so it can be asserted without touching Atlas.
    """
    cfg = get_settings()
    definition = {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": EMBED_DIM,  # 1024 (voyage-3)
                "similarity": "cosine",
            }
        ]
    }
    return cfg.atlas_vector_index, definition


def ensure_index() -> None:
    """Idempotently create the failvec vectorSearch index on the failures collection.

    Synchronous bootstrap (pymongo): opens its own connection from MONGODB_URI so
    it never tangles with the async event loop. Safe to call repeatedly — returns
    early if an index of the same name already exists.
    """
    cfg = get_settings()
    if not cfg.mongodb_uri:
        raise RuntimeError("MONGODB_URI is empty; cannot create the failvec index.")

    from pymongo import MongoClient
    from pymongo.operations import SearchIndexModel

    name, definition = index_definition()
    client = MongoClient(cfg.mongodb_uri)
    try:
        coll = client[cfg.atlas_db][cfg.atlas_collection]
        existing = {ix["name"] for ix in coll.list_search_indexes()}
        if name in existing:
            return
        coll.create_search_index(
            SearchIndexModel(definition=definition, name=name, type="vectorSearch")
        )
    finally:
        client.close()


async def nearest_failures(
    seed_text: str,
    db: "AsyncIOMotorDatabase",
    *,
    limit: int = 12,
    num_candidates: int = 200,
) -> list[Failure]:
    """$vectorSearch the failvec index for failures nearest to `seed_text`.

    The seed is embedded with input_type="query" (asymmetric with stored docs).
    """
    cfg = get_settings()
    qv = embed_query(seed_text)
    pipeline = [
        {
            "$vectorSearch": {
                "index": cfg.atlas_vector_index,
                "path": "embedding",
                "queryVector": qv,
                "numCandidates": num_candidates,
                "limit": limit,
            }
        }
    ]
    docs = await failures_collection(db).aggregate(pipeline).to_list(length=limit)
    return [Failure(**from_doc(d)) for d in docs]


async def nearest_failures_scored(
    seed_text: str,
    db: "AsyncIOMotorDatabase",
    *,
    limit: int = 12,
    num_candidates: int = 200,
) -> list[tuple[Failure, float | None]]:
    """Like `nearest_failures`, but also returns each hit's Atlas `$vectorSearch`
    cosine score (0..1) so the lineage view can show REAL similarity, not synthetic.

    Adds `{$meta: "vectorSearchScore"}` to the pipeline — the one extra projection
    that makes the vector clustering legible in the UI.
    """
    cfg = get_settings()
    qv = embed_query(seed_text)
    pipeline = [
        {
            "$vectorSearch": {
                "index": cfg.atlas_vector_index,
                "path": "embedding",
                "queryVector": qv,
                "numCandidates": num_candidates,
                "limit": limit,
            }
        },
        {"$addFields": {"_score": {"$meta": "vectorSearchScore"}}},
    ]
    docs = await failures_collection(db).aggregate(pipeline).to_list(length=limit)
    out: list[tuple[Failure, float | None]] = []
    for d in docs:
        score = d.pop("_score", None)
        out.append((Failure(**from_doc(d)), round(float(score), 2) if score is not None else None))
    return out
