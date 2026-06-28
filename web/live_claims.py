"""web/live_claims.py — the on-stage "type a claim" registry.

A presenter-typed claim is stored as a **fixture-shaped dict** and merged into the
pool that the MOCK path resolves against, so every offline surface — the score
math, `mock_eval_stream`, `_claim_from_fixture`, and `mock_cluster_lineage` —
works UNCHANGED (they already key off `id` / `category` / `mock` / `sources`).

Display/demo state only, process-wide, mirroring `web.state.RUBRIC`. This NEVER
touches `/loop`, gold, Mongo, Voyage, or Anthropic/Gemini — a live claim is
deterministic, presenter-scripted insurance (the honesty rail is about the REAL
path never reading gold; see CONTRACTS §4).
"""
from __future__ import annotations

import fixtures


class LiveClaims:
    """Process-wide list of fixture-shaped live claims, ids `live-1`, `live-2`, …"""

    def __init__(self) -> None:
        self._items: list[dict] = []
        self._n = 0

    def add(self, *, claim: str, source_text: str = "",
            category: str = "unsupported-numeric", question: str = "") -> dict:
        self._n += 1
        entry = {
            "id": f"live-{self._n}",          # deterministic counter — no time/random
            "category": category,             # presenter-selected; drives the mock verdict
            "question": question,
            "sources": [{"id": "S1", "title": "live source", "url": "", "text": source_text}],
            "mock": {"claim": claim, "cite_ids": ["S1"] if source_text else []},
            "why": "live claim entered on stage",  # used by the lineage builder
        }
        self._items.append(entry)
        return entry

    def ids(self) -> "set[str]":
        return {e["id"] for e in self._items}

    def entries(self) -> "list[dict]":
        return list(self._items)

    def reset(self) -> None:
        self._items = []
        self._n = 0


LIVE = LiveClaims()


def pool_with_live() -> "list[dict]":
    """Fixture working pool + any live claims (live appended last, so fixture ids
    keep their positions and `questions[0]` stays the first fixture)."""
    return fixtures.load_fixture_questions() + LIVE.entries()
