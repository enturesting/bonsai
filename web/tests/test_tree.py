"""GET /tree and the sprout-on-improve flow."""
from __future__ import annotations


def test_tree_renders_seed_branch(client):
    body = client.get("/tree").text
    assert "<svg" in body and 'class="trunk"' in body
    assert 'data-claim="numeric-cites-source"' in body


def test_improve_sprouts_a_branch_on_the_tree(client):
    # Driving the stream records growth via sse_events' observer on the score event.
    client.get("/stream/improve/clean-numeric-01")
    body = client.get("/tree").text
    assert 'data-claim="clean-numeric-01"' in body
    # newest branch is flagged for the sprout animation.
    assert "branch--new" in body


def test_failed_improve_sprouts_an_amber_branch(client):
    client.get("/stream/improve/numeric-mismatch-01")
    body = client.get("/tree").text
    assert 'data-claim="numeric-mismatch-01"' in body
    assert "branch--amber" in body


def test_dashboard_includes_the_tree_with_grow_trigger(client):
    body = client.get("/").text
    assert 'id="tree"' in body
    # htmx refreshes the tree when main.js fires `grow` on sse close.
    assert 'hx-trigger="grow from:body"' in body
