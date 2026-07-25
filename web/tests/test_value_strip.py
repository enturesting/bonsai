"""The value strip — three health tiles that answer "is this doing anything?"

Counts must MOVE with the same events that grow the rubric (the tiles refresh
on the `grow` htmx trigger), and the honesty tile mirrors the gold receipt.
"""
from __future__ import annotations


def test_dashboard_shows_value_strip_tiles(client):
    body = client.get("/").text
    assert "value-strip" in body
    assert "in the rubric" in body
    assert "failure families covered" in body
    assert "honesty receipt" in body


def test_value_strip_fragment_counts_rubric_growth(client):
    from web.state import RUBRIC

    before = client.get("/fragment/value-strip").text
    assert "1</span>" in before                     # just the rooted seed standard

    RUBRIC.record_growth("numeric-mismatch-01", False, "unsupported-numeric")
    after = client.get("/fragment/value-strip").text
    assert "2</span>" in after                      # seed + 1 minted family check
    assert "1 of 5" in after


def test_value_strip_refreshes_on_the_grow_event(client):
    body = client.get("/").text
    assert 'hx-get="/fragment/value-strip"' in body
    assert 'hx-trigger="grow from:body"' in body
