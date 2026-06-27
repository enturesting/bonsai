"""web/sse.py — maps semantic eval_stream dicts to wire ServerSentEvents.

These are the §2 contract shapes. eval_stream is mocked elsewhere; here we feed
sse.py the exact dicts it must render.
"""
from __future__ import annotations

import json

import pytest

from web import sse


def test_render_pill_uses_check_id_as_dom_id_and_keeps_sse_swap():
    html = sse.render_pill({"color": "green", "check_id": "numeric-mismatch-01", "label": "GREEN"})
    assert 'id="pill-numeric-mismatch-01"' in html
    assert "pill--green" in html
    assert ">GREEN<" in html
    # MUST re-declare sse-swap so the green pill is still a target after the
    # yellow pill's outerHTML swap replaced the original element.
    assert 'sse-swap="pill"' in html
    assert 'hx-swap="outerHTML"' in html


def test_render_chunk_escapes_html():
    html = sse.render_chunk({"token": "<b>3.2 & 5</b>"})
    assert html == "<span>&lt;b&gt;3.2 &amp; 5&lt;/b&gt;</span>"


def test_render_score_is_json_string_of_data():
    data = {"passed": True, "before": 2, "after": 3, "n": 5, "ci": [0.34, 0.9]}
    assert json.loads(sse.render_score(data)) == data


def test_to_sse_maps_event_name_and_renders_data():
    ev = sse.to_sse({"event": "pill", "data": {"color": "red", "check_id": "x", "label": "RED"}})
    assert ev.event == "pill"
    assert 'id="pill-x"' in ev.data


def test_to_sse_done_is_empty():
    ev = sse.to_sse({"event": "done", "data": {}})
    assert ev.event == "done"
    assert ev.data == ""


async def _fake_stream(claim_id):
    yield {"event": "pill", "data": {"color": "yellow", "check_id": claim_id, "label": "CHECKING…"}}
    yield {"event": "chunk", "data": {"token": "Numeric "}}
    yield {"event": "pill", "data": {"color": "green", "check_id": claim_id, "label": "GREEN"}}
    yield {"event": "score", "data": {"passed": True, "before": 1, "after": 2, "n": 3, "ci": [0.1, 0.9]}}
    yield {"event": "done", "data": {}}


async def test_sse_events_maps_full_lifecycle_and_notifies_observer():
    seen = []
    events = [ev async for ev in sse.sse_events("c1", _fake_stream, observer=seen.append)]
    assert [e.event for e in events] == ["pill", "chunk", "pill", "score", "done"]
    # observer sees the raw semantic dicts (used to record rubric growth).
    assert [d["event"] for d in seen] == ["pill", "chunk", "pill", "score", "done"]
    assert events[-1].data == ""  # done closes


async def _boom_stream(claim_id):
    yield {"event": "pill", "data": {"color": "yellow", "check_id": claim_id, "label": "CHECKING…"}}
    raise RuntimeError("loop blew up")


async def test_sse_events_emits_error_event_on_exception():
    events = [ev async for ev in sse.sse_events("c1", _boom_stream)]
    assert events[0].event == "pill"
    assert events[-1].event == "error"
    assert "loop blew up" in events[-1].data
