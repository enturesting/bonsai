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
    # the lineage panel the clickable nodes open into.
    assert 'id="lineage"' in body


def test_grown_nodes_are_clickable_into_the_lineage(client):
    # sprout a branch, then each grown node opens its cluster lineage.
    client.get("/stream/improve/clean-numeric-01")
    body = client.get("/tree").text
    assert 'hx-get="/tree/clean-numeric-01"' in body
    assert 'hx-target="#lineage"' in body


def test_seed_node_is_not_clickable(client):
    # the seed has no minting cluster behind it — only grown checks open a lineage.
    body = client.get("/tree").text
    assert 'hx-get="/tree/numeric-cites-source"' not in body
