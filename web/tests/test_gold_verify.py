"""The honesty-receipt live recompute: POST /gold/verify + web.gold.

The rail nuance under test: /web may READ gold (verification-side display); only
/loop is forbidden. The recompute is explicit (button), never on page load, and a
failed or unavailable recompute must fall back to the stored receipt VISIBLY —
never masquerade as fresh numbers.
"""
from __future__ import annotations

import store as store_pkg

from store.models import Check

from web import gold as web_gold
from web import routes as web_routes


def seed_check(id="numeric-cites-source"):
    return Check(id=id, property="Every numeric claim has a verbatim supporting quote.",
                 rationale="r", positive_example="p", negative_example="n", overfit_risk="o")


# ── route: mock/keyless box ──────────────────────────────────────────────────
def test_dashboard_mock_mode_shows_stored_receipt_without_verify(client):
    body = client.get("/").text
    assert "Honesty receipt" in body
    assert "precomputed, fixed" in body
    assert "Verify now" not in body           # no live seams → no live promise
    assert "recomputed live" not in body


def test_gold_verify_mock_mode_returns_stored_receipt(client):
    body = client.post("/gold/verify").text
    assert "Honesty receipt" in body
    assert "precomputed, fixed" in body
    assert "recomputed live" not in body and "Verify now" not in body


# ── route: live path ─────────────────────────────────────────────────────────
def _live_result():
    return {"before": 9, "after": 14, "n": 15, "ci": [0.702, 0.988],
            "sign_test": {"helped": 5, "hurt": 0, "n": 5, "p": 0.03125},
            "checks_before": 1, "checks_after": 6, "live": True}


def test_gold_verify_live_recompute_labels_result_live(client, monkeypatch):
    async def fake_recompute():
        return _live_result()

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "recompute_gold_result", fake_recompute)
    body = client.post("/gold/verify").text
    assert "recomputed live just now" in body
    assert "9" in body and "14" in body
    assert "Verify now" in body               # can rescore again


def test_gold_verify_regression_is_reported_not_dressed_as_gain(client, monkeypatch):
    """A live rescore that REGRESSED must say so — the receipt exists to expose
    exactly this, so it must never render '-2 more cases caught … gain is real'."""
    async def fake_recompute():
        return {"before": 9, "after": 7, "n": 15, "ci": [0.24, 0.71],
                "sign_test": {"helped": 1, "hurt": 3, "n": 4, "p": 0.3125},
                "checks_before": 1, "checks_after": 6, "live": True}

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "recompute_gold_result", fake_recompute)
    body = client.post("/gold/verify").text
    assert "regressed" in body and "2 fewer held-out cases" in body
    assert "gain is real" not in body
    assert "score-after down" in body            # painted as a drop, not green
    assert "1 helped, 3 hurt" in body


def test_gold_verify_failure_falls_back_visibly(client, monkeypatch):
    async def boom():
        raise RuntimeError("rubric store is empty")

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "recompute_gold_result", boom)
    body = client.post("/gold/verify").text
    assert "live rescore failed" in body and "rubric store is empty" in body
    assert "precomputed, fixed" in body       # the stored receipt, honestly labeled
    assert "recomputed live" not in body


def test_dashboard_live_mode_offers_verify_button(client, monkeypatch):
    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    body = client.get("/").text
    assert "Verify now" in body


# ── web.gold.recompute_gold_result ───────────────────────────────────────────
async def test_recompute_scores_seed_vs_current_rubric(monkeypatch):
    import eval.scoring as scoring

    rubric = [seed_check(), seed_check("minted-fabricated-quote")]
    gold = [{"id": f"g{i}"} for i in range(3)]

    async def fake_checks(db):
        return rubric

    def fake_score(checks, items):
        # seed rubric alone misses; the grown rubric agrees on every item
        return [len(checks) > 1 for _ in items]

    monkeypatch.setattr(store_pkg, "get_db", lambda: object())
    monkeypatch.setattr(store_pkg, "get_checks", fake_checks, raising=False)
    monkeypatch.setattr(scoring, "load_gold", lambda: gold)
    monkeypatch.setattr(scoring, "score_rubric", fake_score)

    res = await web_gold.recompute_gold_result()
    assert res["before"] == 0 and res["after"] == 3 and res["n"] == 3
    assert res["checks_before"] == 1 and res["checks_after"] == 2
    assert res["live"] is True
    lo, hi = res["ci"]
    assert 0.0 <= lo <= hi <= 1.0


async def test_recompute_raises_on_empty_rubric(monkeypatch):
    async def no_checks(db):
        return []

    monkeypatch.setattr(store_pkg, "get_db", lambda: object())
    monkeypatch.setattr(store_pkg, "get_checks", no_checks, raising=False)
    try:
        await web_gold.recompute_gold_result()
    except RuntimeError as exc:
        assert "rubric store is empty" in str(exc)
    else:
        raise AssertionError("expected RuntimeError on empty rubric")
