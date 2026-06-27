"""store — Bonsai's data layer: the only seam to MongoDB Atlas + Voyage.

Public surface (CONTRACTS §3 /store, FROZEN). Other terminals import from here,
e.g. `from store import save_failure, get_db`. Models stay authoritative in
`store.models` — this package never forks them.
"""
from store.checks import get_checks, seed, upsert_check
from store.client import get_db
from store.embed import embed, embed_one, embed_query
from store.failures import known_good_sample, save_failure
from store.models import EMBED_DIM, AUTOutput, Check, Failure, Source, Verdict
from store.vectors import ensure_index, nearest_failures

__all__ = [
    # connection
    "get_db",
    # embeddings
    "embed",
    "embed_one",
    "embed_query",
    # index + retrieval
    "ensure_index",
    "nearest_failures",
    # failures + known-good
    "save_failure",
    "known_good_sample",
    # rubric + bootstrap
    "get_checks",
    "upsert_check",
    "seed",
    # models (re-exported for convenience; authoritative in store.models)
    "Failure",
    "Check",
    "Verdict",
    "AUTOutput",
    "Source",
    "EMBED_DIM",
]
