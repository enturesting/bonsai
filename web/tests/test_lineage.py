"""Feature 1 — the Atlas $vectorSearch cluster lineage made visible.

GET /tree/{claim_id} renders, for a grown check: the seed failure → the N
nearest failures Atlas returned (similarity order) → the minted general check +
its is_general verdict. Offline it builds from the fixture pool (mock path); the
real path pulls via store.nearest_failures + loop.grow — both MOCKED here, the
same way the rest of the suite mocks loop.eval_stream.
"""
from __future__ import annotations

import asyncio

import pytest

import fixtures
from web.tests.conftest import FAKE_QUESTIONS


def _run(coro):
    # A fresh loop per call — robust to other suites closing the global loop.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── mock builder (offline) ────────────────────────────────────────────


def _patch_pool(monkeypatch, pool):
    monkeypatch.setattr(fixtures, "load_fixture_questions", lambda: [dict(q) for q in pool])


def test_mock_lineage_has_seed_cluster_and_minted(monkeypatch):
    from web.lineage import mock_cluster_lineage

    _patch_pool(monkeypatch, FAKE_QUESTIONS)
    lin = _run(mock_cluster_lineage("numeric-mismatch-01"))

    assert lin["source"] == "mock"
    assert lin["seed"]["id"] == "seed-numeric-mismatch-01"
    assert "3.2 billion" in lin["seed"]["claim"]
    # cluster carries the nearest stored failures with rank + why.
    assert lin["k"] == len(lin["cluster"]) >= 1
    assert lin["cluster"][0]["id"] == "seed-numeric-mismatch-01"
    assert all("rank" in c and "why" in c for c in lin["cluster"])
    # a general property was minted, not a paraphrase of the one failure.
    assert lin["minted"]["property"]
    assert "is_general" in lin["verdict"]


def test_mock_lineage_cluster_is_similarity_ordered(monkeypatch):
    from web.lineage import mock_cluster_lineage

    # three sibling failures of the same class + a clean held-back item.
    pool = [
        {"id": "n1", "category": "unsupported-numeric", "question": "q1",
         "mock": {"claim": "c1"}, "why": "w1"},
        {"id": "n2", "category": "unsupported-numeric", "question": "q2",
         "mock": {"claim": "c2"}, "why": "w2"},
        {"id": "n3", "category": "unsupported-numeric", "question": "q3",
         "mock": {"claim": "c3"}, "why": "w3"},
        {"id": "ok", "category": "clean", "question": "q4", "mock": {"claim": "c4"}},
    ]
    _patch_pool(monkeypatch, pool)
    lin = _run(mock_cluster_lineage("n1"))

    ranks = [c["rank"] for c in lin["cluster"]]
    assert ranks == sorted(ranks) and ranks[0] == 1  # 1..K ascending
    sims = [c["similarity"] for c in lin["cluster"]]
    assert sims == sorted(sims, reverse=True)  # similarity descends with rank
    # clean items are NOT failures and never appear in the cluster.
    assert all("ok" not in c["id"] for c in lin["cluster"])


def test_mock_lineage_is_general_when_two_or_more_siblings(monkeypatch):
    from web.lineage import mock_cluster_lineage

    pool = [
        {"id": "n1", "category": "unsupported-numeric", "mock": {"claim": "c1"}, "why": "w1"},
        {"id": "n2", "category": "unsupported-numeric", "mock": {"claim": "c2"}, "why": "w2"},
        {"id": "ok", "category": "clean", "mock": {"claim": "c3"}},
    ]
    _patch_pool(monkeypatch, pool)
    lin = _run(mock_cluster_lineage("n1"))

    assert lin["verdict"]["caught_siblings"] >= 2
    assert lin["verdict"]["is_general"] is True


def test_mock_lineage_not_general_with_a_single_failure(monkeypatch):
    from web.lineage import mock_cluster_lineage

    _patch_pool(monkeypatch, FAKE_QUESTIONS)  # exactly one failure fixture
    lin = _run(mock_cluster_lineage("numeric-mismatch-01"))

    assert lin["verdict"]["caught_siblings"] == 1
    assert lin["verdict"]["is_general"] is False  # the gate needs ≥2 siblings


# ── route (mock path, via the dashboard client) ───────────────────────


def test_tree_lineage_route_renders_the_cluster(client):
    r = client.get("/tree/numeric-mismatch-01")
    assert r.status_code == 200
    body = r.text
    # the Atlas money-shot label + the clustered failure id.
    assert "Atlas $vectorSearch" in body
    assert "seed-numeric-mismatch-01" in body
    # the grown-node label names the cluster size K.
    assert "cluster of 1" in body


def test_mock_lineage_narration_is_labeled_a_re_enactment(client):
    """Q1/Q2 honesty: a mock box's lineage is a scripted reconstruction from
    authored fixtures — the narration must say so, never read as a mint
    happening live right now, and never claim a recorded run existed."""
    body = client.get("/tree/numeric-mismatch-01").text
    assert "re-enactment" in body
    assert "a scripted reconstruction from authored fixtures, not a live mint" in body
    # nothing was recorded — the narration must not overclaim provenance.
    assert "recorded" not in body
    # the source badge carries the label too, and never claims live Atlas.
    assert "re-enactment · offline mock" in body
    assert "live Atlas" not in body


# ── real path: /web pulls via store.nearest_failures + loop.grow ──────


def test_lineage_real_path_uses_store_and_loop(client, monkeypatch):
    """With a key present (no mock), /tree/{id} drives the frozen seams —
    store.nearest_failures for the cluster, loop.grow for the minted check."""
    import store
    import loop
    from store.models import Check, Failure

    monkeypatch.setenv("WEB_MOCK_STREAM", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "live-key")

    calls = {"nearest": 0, "grow": 0}

    async def fake_nearest_scored(seed_text, db, *, limit=12, num_candidates=200):
        calls["nearest"] += 1
        return [
            (Failure(id="atlas-fail-1", input="i", claim="c", expected="e",
                     actual="a", why="bad citation 1"), 0.91),
            (Failure(id="atlas-fail-2", input="i", claim="c", expected="e",
                     actual="a", why="bad citation 2"), 0.84),
        ]

    async def fake_grow(worst_check, db):
        calls["grow"] += 1
        return Check(id="minted-general", property="A minted general invariant.",
                     rationale="r", positive_example="p", negative_example="n",
                     overfit_risk="o")

    monkeypatch.setattr(store, "get_db", lambda: object())
    monkeypatch.setattr(store, "nearest_failures_scored", fake_nearest_scored)
    monkeypatch.setattr(loop, "grow", fake_grow)

    body = client.get("/tree/numeric-mismatch-01").text
    assert calls["nearest"] == 1 and calls["grow"] == 1
    assert "atlas-fail-1" in body and "atlas-fail-2" in body
    assert "minted-general" in body
    assert "Atlas $vectorSearch" in body
    # the REAL $vectorSearch cosine score is surfaced (not None) in the live path.
    assert "0.91" in body
    # the real path keeps its real narration — no re-enactment label on a live mint.
    assert "live Atlas" in body
    assert "re-enactment" not in body


def test_lineage_reuses_the_improves_grow_report_instead_of_regrowing(client, monkeypatch):
    """After an Improve minted inside eval_stream, /tree/{id} must show THAT mint —
    re-running grow would mint (and possibly persist) a second check per click."""
    import store
    import loop
    from loop.grower import GrowReport
    from store.models import Check, Failure

    monkeypatch.setenv("WEB_MOCK_STREAM", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "live-key")

    grow_calls = []

    async def fake_nearest_scored(seed_text, db, *, limit=12, num_candidates=200):
        return [(Failure(id="atlas-fail-1", input="i", claim="c", expected="e",
                         actual="a", why="w"), 0.9)]

    async def fake_grow(worst_check, db):
        grow_calls.append(1)
        return None

    cached = Check(id="minted-from-stream", property="The check the click actually minted.",
                   rationale="r", positive_example="p", negative_example="n", overfit_risk="o")
    monkeypatch.setattr(store, "get_db", lambda: object())
    monkeypatch.setattr(store, "nearest_failures_scored", fake_nearest_scored)
    monkeypatch.setattr(loop, "grow", fake_grow)
    monkeypatch.setattr(loop, "last_grow_report",
                        lambda cid: GrowReport(minted=cached, candidate=cached, gated=True,
                                               cluster_size=3, caught_siblings=2, n_known_good=4))

    body = client.get("/tree/numeric-mismatch-01").text
    assert grow_calls == []                      # no second mint
    assert "minted-from-stream" in body
    assert "The check the click actually minted." in body
