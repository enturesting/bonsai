"""GET /stream/improve/{claim_id} and the improve-container fragment.

End-to-end through the real routes with the mock eval_stream (WEB_MOCK_STREAM=1).
This is the red→yellow→green flip the demo hangs on.
"""
from __future__ import annotations


def test_fragment_returns_sse_connect_container(client):
    r = client.get("/fragment/improve-container/numeric-mismatch-01")
    assert r.status_code == 200
    body = r.text
    assert 'hx-ext="sse"' in body
    assert 'sse-connect="/stream/improve/numeric-mismatch-01"' in body
    assert 'sse-close="done"' in body
    # A pill target carrying the claim_id, plus the rule-stream sink.
    assert 'id="pill-numeric-mismatch-01"' in body
    assert 'sse-swap="pill"' in body
    assert 'id="rule-stream"' in body
    assert 'sse-swap="chunk"' in body
    assert 'sse-swap="score"' in body


def test_stream_is_event_stream_with_no_buffering(client):
    r = client.get("/stream/improve/numeric-mismatch-01")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    # nginx/proxy must not buffer SSE.
    assert r.headers.get("x-accel-buffering") == "no"


def test_stream_emits_the_section2_lifecycle(client):
    body = client.get("/stream/improve/numeric-mismatch-01").text
    assert "event: pill" in body
    assert "event: chunk" in body
    assert "event: score" in body
    assert "event: done" in body
    # Pill DOM id == claim_id, and the first pill is the yellow CHECKING state.
    assert "id=\"pill-numeric-mismatch-01\"" in body
    assert "CHECKING" in body


def test_stream_clean_claim_flips_to_green(client):
    body = client.get("/stream/improve/clean-numeric-01").text
    assert "pill--green" in body
    assert ">GREEN<" in body


def test_stream_failure_claim_resolves_red(client):
    body = client.get("/stream/improve/numeric-mismatch-01").text
    # final pill is red; the score event reports passed:false
    assert "pill--red" in body
    assert '"passed": false' in body
