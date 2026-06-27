"""store.embed — the only seam to Voyage (voyage-3, 1024-dim, cosine).

Asymmetric by design: stored failures embed with input_type="document", live
query seeds embed with input_type="query". Both are 1024-dim for voyage-3, so
the failvec index is unaffected by which side called.

The client is a lazily-built module singleton so tests can swap `_client` for a
stub without touching the network or needing a real key.
"""
from __future__ import annotations

from config import get_settings

_client = None  # voyageai.Client singleton; tests monkeypatch this


def _voyage():
    global _client
    if _client is None:
        cfg = get_settings()
        if not cfg.voyage_api_key:
            raise RuntimeError(
                "VOYAGE_API_KEY is empty; set it in the environment before embedding."
            )
        import voyageai

        _client = voyageai.Client(api_key=cfg.voyage_api_key)
    return _client


def embed(texts: list[str]) -> list[list[float]]:
    """Embed stored documents (caught failures). input_type='document', 1024-dim."""
    cfg = get_settings()
    return _voyage().embed(texts, model=cfg.voyage_model, input_type="document").embeddings


def embed_one(text: str) -> list[float]:
    """Convenience: embed a single document and return its 1024-dim vector."""
    return embed([text])[0]


def embed_query(text: str) -> list[float]:
    """Embed a retrieval query (asymmetric). input_type='query', 1024-dim."""
    cfg = get_settings()
    return _voyage().embed([text], model=cfg.voyage_model, input_type="query").embeddings[0]
