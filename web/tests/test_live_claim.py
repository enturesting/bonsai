"""Tests for the on-stage Live Claim path: web/live_claims.py + the merged mock
pool (mock_eval_stream / mock_cluster_lineage) + the /live-claim route and the
force-mock guards. All offline/keyless via the conftest mock env.
"""
from __future__ import annotations

import asyncio


def _collect(agen):
    """Drain an async generator to a list (no pytest-asyncio needed)."""
    async def run():
        return [e async for e in agen]
    return asyncio.run(run())


def test_live_add_id_scheme_and_pool(fake_questions):
    from web.live_claims import LIVE, pool_with_live

    a = LIVE.add(claim="first", category="clean")
    b = LIVE.add(claim="second", category="unsupported-numeric")
    assert a["id"] == "live-1" and b["id"] == "live-2"
    assert LIVE.ids() == {"live-1", "live-2"}

    pool = pool_with_live()
    # fixtures + live, live appended LAST so questions[0] stays the first fixture.
    assert len(pool) == len(fake_questions) + 2
    assert pool[0]["id"] == fake_questions[0]["id"]
    assert pool[-1]["id"] == "live-2"


def test_live_claim_shaped_like_fixture(fake_questions):
    from web.live_claims import LIVE

    e = LIVE.add(claim="X", source_text="src text", category="fabricated-quote", question="Q?")
    # exactly the keys _claim_from_fixture / _resolve / lineage read off a fixture
    assert e["category"] == "fabricated-quote"
    assert e["question"] == "Q?"
    assert e["mock"]["claim"] == "X"
    assert e["mock"]["cite_ids"] == ["S1"]
    assert e["sources"][0]["text"] == "src text"


def test_live_claim_empty_source_has_no_citations(fake_questions):
    from web.live_claims import LIVE

    e = LIVE.add(claim="X", source_text="", category="clean")
    assert e["mock"]["cite_ids"] == []


def test_mock_stream_resolves_live_id_not_questions0(fake_questions):
    # FAKE_QUESTIONS[0] is unsupported-numeric (would stream RED). A CLEAN live claim
    # streaming GREEN proves the merged pool resolved live-1, not the questions[0]
    # silent fallback.
    from web.live_claims import LIVE
    from web.mock_stream import mock_eval_stream

    LIVE.add(claim="well supported", source_text="well supported", category="clean")
    events = _collect(mock_eval_stream("live-1"))
    score = next(e for e in events if e["event"] == "score")
    assert score["data"]["passed"] is True  # clean → green; the fallback would be RED


def test_clean_live_lineage_short_circuit(fake_questions):
    from web.live_claims import LIVE
    from web.lineage import mock_cluster_lineage

    LIVE.add(claim="well supported", category="clean")
    lin = asyncio.run(mock_cluster_lineage("live-1"))
    assert lin.get("clean") is True
    assert lin["k"] == 0
    assert lin["minted"] is None
    assert lin["cluster"] == []


def test_failure_live_lineage_has_cluster(fake_questions):
    from web.live_claims import LIVE
    from web.lineage import mock_cluster_lineage

    LIVE.add(claim="bad number 42", category="unsupported-numeric")
    lin = asyncio.run(mock_cluster_lineage("live-1"))
    assert not lin.get("clean")
    assert lin["k"] >= 1
    assert lin["minted"] is not None


def test_post_live_claim_empty_is_noop(client):
    from web.live_claims import LIVE

    r = client.post("/live-claim", data={"claim": "   ", "category": "clean"})
    assert r.status_code == 200
    assert r.text.strip() == ""
    assert LIVE.ids() == set()


def test_post_live_claim_renders_tile_only(client, fake_questions):
    from web.live_claims import LIVE

    r = client.post("/live-claim", data={
        "claim": "Our SOC 2 report covers all five trust criteria.",
        "source": "The SOC 2 Type II report covers the Security trust services criterion.",
        "category": "single-source-overcite",
    })
    assert r.status_code == 200
    body = r.text
    assert 'id="claim-live-1"' in body
    assert "Our SOC 2 report covers all five trust criteria." in body
    assert "single-source-overcite" in body
    # JUST the tile — no OOB score swap (it would clobber the running greens main.js
    # rendered after a prior flip; the next improve self-corrects the denominator).
    assert "hx-swap-oob" not in body
    assert "live-1" in LIVE.ids()


def test_blank_question_renders_no_claim_q(client):
    # live tiles carry question="" — the .claim-q line must be omitted, not an empty gap.
    r = client.post("/live-claim", data={"claim": "a claim with no question", "category": "clean"})
    assert 'class="claim-q"' not in r.text


def test_tree_live_id_forces_mock_clean_card(client):
    client.post("/live-claim", data={"claim": "well supported", "category": "clean"})
    r = client.get("/tree/live-1")
    assert r.status_code == 200
    assert "nothing to mint" in r.text.lower()


def test_tree_live_id_never_calls_real_lineage(client, monkeypatch):
    # Key-present regression: a live id must route to mock_cluster_lineage, never
    # resolve_cluster_lineage() (real Voyage+Atlas+loop.grow over typed text). If the
    # guard regressed, the else-branch resolver would fire and blow up here.
    import web.routes as routes

    def _boom():
        raise AssertionError("resolve_cluster_lineage() must not run for a live id")

    monkeypatch.setattr(routes, "resolve_cluster_lineage", _boom)
    client.post("/live-claim", data={"claim": "bad number 42", "category": "unsupported-numeric"})
    r = client.get("/tree/live-1")               # live id → forced mock, no boom
    assert r.status_code == 200
    assert "cluster" in r.text.lower()


def test_dashboard_includes_live_tiles(client):
    client.post("/live-claim", data={"claim": "a typed live claim", "category": "clean"})
    body = client.get("/").text
    assert 'id="claim-live-1"' in body
    assert "a typed live claim" in body


def test_reset_clears_live_claims(client):
    from web.live_claims import LIVE

    client.post("/live-claim", data={"claim": "x", "category": "clean"})
    assert LIVE.ids()
    client.post("/reset")
    assert LIVE.ids() == set()
