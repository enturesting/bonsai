"""POST /teach — the owner-intake path: a plain-English standard becomes a check.

The binding guardrails under test: the gate verdict shown is ALWAYS the real
is_general outcome (never faked); the keyless/mock box records the requirement
as UNVERIFIED instead of pretending to gate it; every response triggers the
rubric + value-strip refresh.
"""
from __future__ import annotations

from store.models import Check

from web import routes as web_routes


def _check(id="std-price", prop="Quoted prices must appear in the current price book."):
    return Check(id=id, property=prop, rationale="r", positive_example="p",
                 negative_example="n", overfit_risk="o")


def test_teach_keyless_records_unverified_requirement(client):
    r = client.post("/teach", data={"standard": "Never invent a price."})
    body = r.text
    assert "unverified" in body and "generality gate" in body
    assert "ADMITTED" not in body                    # no fake gate verdict, ever
    assert r.headers.get("hx-trigger") == "grow"     # rubric + value strip refresh
    # the ◆ requirement row is now in the rubric panel
    rubric = client.get("/rubric").text
    assert "Never invent a price." in rubric
    assert "unverified" in rubric


def test_teach_form_keyless_hint_sets_expectations_before_submit(client):
    """Q3: on a keyless box the pre-submit hint must say the demo only RECORDS
    the rule — never imply the gate runs here — and point (prose only; the real
    screening path isn't built yet) at where a rule becomes real."""
    import html

    body = html.unescape(client.get("/").text)
    assert "demo records your rule but can’t test it" in body
    assert "a live box runs the gate" in body
    assert "outputs you screen" in body  # the screen-an-output path, prose only
    # the keyed-box hint must not double up on the keyless form
    assert "sharp enough to police a family" not in body


def test_teach_form_keyed_box_keeps_gate_hint_no_keyless_warning(client, monkeypatch):
    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    body = client.get("/").text
    assert "sharp enough to police a family" in body
    assert "demo records your rule but can" not in body


def test_teach_unverified_card_says_wont_catch_anything_yet(client):
    """The flying-dogs guard: a keyless recorded rule must say it won't catch
    anything yet, so nobody screens a contradicting output expecting a CAUGHT."""
    import html

    body = html.unescape(client.post("/teach", data={"standard": "Dogs can never fly."}).text)
    assert "won’t catch anything yet" in body
    assert "screened output" in body  # where a rule becomes real — prose, no link
    assert "generality gate" in body
    assert "ADMITTED" not in body


def test_teach_empty_standard_is_a_noop(client):
    assert client.post("/teach", data={"standard": "   "}).text == ""


def test_teach_live_path_shows_real_gate_verdict_admitted(client, monkeypatch):
    async def fake_live(standard):
        return {"check": _check(), "gated": True, "caught": 3, "n_known_good": 5}

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "_teach_live", fake_live)
    body = client.post("/teach", data={"standard": "Never invent a price."}).text
    assert "ADMITTED" in body
    assert "caught 3 sibling" in body and "5 known-good" in body
    assert "current price book" in body


def test_teach_live_path_shows_rejection_honestly(client, monkeypatch):
    async def fake_live(standard):
        return {"check": _check(), "gated": False, "caught": 1, "n_known_good": 5}

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "_teach_live", fake_live)
    import html

    body = html.unescape(client.post("/teach", data={"standard": "Never invent a price."}).text)
    assert "REJECTED" in body and "needs ≥2" in body
    assert "ADMITTED" not in body


def test_teach_live_seam_failure_degrades_to_unverified(client, monkeypatch):
    async def boom(standard):
        raise RuntimeError("MONGODB_URI is empty")

    monkeypatch.setattr(web_routes, "use_mock", lambda: False)
    monkeypatch.setattr(web_routes, "_teach_live", boom)
    body = client.post("/teach", data={"standard": "Never invent a price."}).text
    assert "unverified" in body and "MONGODB_URI is empty" in body
    assert "ADMITTED" not in body


def test_dashboard_offers_add_a_requirement(client):
    body = client.get("/").text
    assert "Add a requirement" in body
    assert 'hx-post="/teach"' in body


def test_teach_form_lives_outside_the_grow_swapped_rubric(client):
    """The /teach response fires the `grow` trigger that outerHTML-swaps #rubric —
    if the verdict-card target sat inside #rubric it would be wiped ~4ms after
    rendering (reproduced in a real browser). Pin the hoist: the form + result
    slot live in their own panel, and the /rubric fragment carries neither."""
    rubric_fragment = client.get("/rubric").text
    assert "teach-result" not in rubric_fragment
    assert 'hx-post="/teach"' not in rubric_fragment
    dashboard = client.get("/").text
    assert "teach-result" in dashboard and "teach-panel" in dashboard


async def test_teach_live_gate_math_and_persist_guard(monkeypatch):
    """Execute the REAL _teach_live with patched store/loop seams (the same way
    test_grower exercises grow): the gate rule — passes ALL known-good AND
    catches ≥2 siblings — is what decides persistence, and a rejection persists
    NOTHING. This is the honesty-critical body every route test patches away."""
    import store as store_pkg
    import loop as loop_pkg
    import loop.grower as grower
    from store.models import AUTOutput, Failure, Source, Verdict

    check = _check()
    upserts = []

    async def known(db, k=8):
        return [AUTOutput(input="q", claim="good", output="a",
                          sources=[Source(text="good, per the filing")])]

    async def nearest(seed, db, **kw):
        return [Failure(id=f"f{i}", input="i", claim=f"bad {i}", expected="e",
                        actual="a", why="w") for i in range(2)]

    async def upsert(c, db):
        upserts.append(c)
        return c.id

    monkeypatch.setattr(store_pkg, "get_db", lambda: object())
    monkeypatch.setattr(loop_pkg, "mint_check_from_standard", lambda text: check)
    monkeypatch.setattr(store_pkg, "known_good_sample", known, raising=False)
    monkeypatch.setattr(store_pkg, "nearest_failures", nearest, raising=False)
    monkeypatch.setattr(store_pkg, "upsert_check", upsert, raising=False)
    # discriminating verdicts: known-good (has sources) passes, failures caught
    monkeypatch.setattr(grower, "run_check",
                        lambda c, claim, o: Verdict(passed=bool(o.sources), confidence=1.0, reason=""))

    res = await web_routes._teach_live("Never invent a price.")
    assert res["gated"] is True and res["caught"] == 2 and res["n_known_good"] == 1
    assert upserts == [check]                    # ADMITTED → persisted

    upserts.clear()
    monkeypatch.setattr(grower, "run_check",     # overfit: wrongly fails known-good
                        lambda c, claim, o: Verdict(passed=False, confidence=1.0, reason=""))
    res = await web_routes._teach_live("Never invent a price.")
    assert res["gated"] is False
    assert upserts == []                         # REJECTED → nothing persisted


def test_reteaching_the_same_standard_does_not_double_count(client):
    client.post("/teach", data={"standard": "Never invent a price."})
    client.post("/teach", data={"standard": "  never invent a  price. "})
    from web.state import RUBRIC

    assert len(RUBRIC.requirements()) == 1       # latest wins; value strip can't inflate
