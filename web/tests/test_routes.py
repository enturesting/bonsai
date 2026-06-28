"""Route-level tests for /web. The loop is mocked (WEB_MOCK_STREAM=1)."""
from __future__ import annotations

from web.tests.conftest import FAKE_QUESTIONS


def test_dashboard_lists_each_claim_with_an_idle_pill(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    for q in FAKE_QUESTIONS:
        # Pill DOM id MUST be the claim_id value (== eval_stream data.check_id).
        assert f'id="pill-{q["id"]}"' in body
    # Every claim starts idle ("not checked") — the harness hasn't verified it yet.
    assert body.count("pill--idle") >= len(FAKE_QUESTIONS)
    # The claim text (the unit of evaluation) is shown.
    assert "3.2 billion" in body


def test_dashboard_score_panel_shows_counts_and_wilson_ci(client):
    body = client.get("/").text
    # honest baseline: 0 green of N, with a CI — never a bare %.
    assert f"/ {len(FAKE_QUESTIONS)} green" in body
    assert "95% CI [" in body


def test_run_mints_pill_skeleton_keyed_by_fixture_id(client):
    r = client.post("/run")
    assert r.status_code == 200
    body = r.text
    # claim_id == fixture id, so pills carry the same value eval_stream emits.
    for q in FAKE_QUESTIONS:
        assert f'id="pill-{q["id"]}"' in body
    assert body.count("pill--idle") == len(FAKE_QUESTIONS)
    # Each claim exposes an Improve trigger to /fragment/improve-container/{id}.
    for q in FAKE_QUESTIONS:
        assert f'/fragment/improve-container/{q["id"]}' in body


def test_dashboard_claims_credit_gemini_with_citations(client):
    # Feature 2: surface the AUT — every claim is "Answered by Verity · Gemini 3.5"
    # (span.badge--gemini) and shows the [S#] citations it grounded on.
    body = client.get("/").text
    assert body.count("badge--gemini") >= len(FAKE_QUESTIONS)
    assert body.count("Gemini 3.5") >= len(FAKE_QUESTIONS)
    # the numeric claim cites S1 — the handle must render as a chip.
    assert "[S1]" in body


def test_run_claims_credit_gemini_with_citations(client):
    body = client.post("/run").text
    assert body.count("badge--gemini") == len(FAKE_QUESTIONS)
    assert "Gemini 3.5" in body
    # citations come from the AUTOutput.sources the AUT actually cited.
    assert "[S1]" in body
