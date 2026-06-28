"""Tests for the maturation panel: RUBRIC.checks()/maturity() + the property
ladder (web/mock_stream.rung/rung_diff) + the /rubric route. Display state only;
the gold honesty receipt is untouched (see test_honesty_gate)."""
from __future__ import annotations


def test_version_bumps_on_distinct_failures():
    from web.state import RUBRIC

    RUBRIC.record_growth("c1", False, "unsupported-numeric")
    RUBRIC.record_growth("c2", False, "unsupported-numeric")  # a SECOND distinct failure
    rows = [c for c in RUBRIC.checks() if c["category"] == "unsupported-numeric"]
    assert len(rows) == 1                       # one family row, not two twigs
    r = rows[0]
    assert r["version"] == 2 and r["minted_from"] == 2
    assert r["diff"] is not None and r["diff"]["from"] != r["diff"]["to"]


def test_same_claim_recorded_twice_stays_v1():
    from web.state import RUBRIC

    RUBRIC.record_growth("c1", False, "unsupported-numeric")
    RUBRIC.record_growth("c1", True, "unsupported-numeric")   # same claim re-improved
    rows = RUBRIC.checks()
    assert len(rows) == 1
    assert rows[0]["version"] == 1               # re-click doesn't inflate version
    assert rows[0]["diff"] is None


def test_clean_improve_is_control_not_family():
    from web.state import RUBRIC

    RUBRIC.record_growth("clean-1", True, "clean")
    assert RUBRIC.checks() == []                 # clean is the control, never a family
    assert RUBRIC.maturity()["covered"] == 0
    assert len(RUBRIC.branches()) == 2           # but the tree still sprouts (seed + 1)


def test_maturity_covers_distinct_families():
    from web.state import RUBRIC

    RUBRIC.record_growth("a", False, "unsupported-numeric")
    RUBRIC.record_growth("b", False, "fabricated-quote")
    RUBRIC.record_growth("c", False, "stale-wrong-citation")
    m = RUBRIC.maturity()
    assert m["covered"] == 3 and m["total"] == 5
    filled = {s["category"] for s in m["segments"] if s["filled"]}
    assert filled == {"unsupported-numeric", "fabricated-quote", "stale-wrong-citation"}


def test_rung_clamps_and_diff_none_at_v1():
    from web.mock_stream import rung, rung_diff

    assert rung("unsupported-numeric", 0) == rung("unsupported-numeric", 1)    # clamp low
    assert rung("unsupported-numeric", 99) == rung("unsupported-numeric", 3)   # clamp high
    assert rung_diff("unsupported-numeric", 1) is None
    d = rung_diff("unsupported-numeric", 2)
    assert d and d["from"] != d["to"]


def test_newest_touched_family_flagged_new():
    from web.state import RUBRIC

    RUBRIC.record_growth("a", False, "unsupported-numeric")
    RUBRIC.record_growth("b", False, "fabricated-quote")
    new = [c for c in RUBRIC.checks() if c["new"]]
    assert len(new) == 1 and new[0]["category"] == "fabricated-quote"


def test_rubric_route_renders_meter_and_rows(client):
    from web.state import RUBRIC

    RUBRIC.record_growth("a", False, "unsupported-numeric")
    RUBRIC.record_growth("b", True, "fabricated-quote")
    r = client.get("/rubric")
    assert r.status_code == 200
    body = r.text
    assert "failure families" in body            # meter header
    assert "Rooted standard" in body             # the seed row, always shown
    assert "Invented numbers" in body            # unsupported-numeric label
    assert "Made-up quotes" in body              # fabricated-quote label
    assert 'id="rubric"' in body and 'hx-trigger="grow from:body"' in body


def test_minted_v1_shows_precise_property_not_vague():
    # a minted check is NEVER the deliberately-vague v1 placeholder — even at v1 it
    # shows the precise rung; the vague rung only surfaces as a diff's `from`.
    from web.state import RUBRIC
    from web.mock_stream import rung

    RUBRIC.record_growth("a", False, "fabricated-quote")  # single failure → v1
    row = next(c for c in RUBRIC.checks() if c["category"] == "fabricated-quote")
    assert row["version"] == 1
    assert row["property"] == rung("fabricated-quote", 2)
    assert row["property"] != rung("fabricated-quote", 1)


def test_minted_status_is_active():
    from web.state import RUBRIC

    RUBRIC.record_growth("a", False, "fabricated-quote")
    assert RUBRIC.checks()[0]["status"] == "active"


def test_meter_pulses_only_on_first_coverage():
    from web.state import RUBRIC

    RUBRIC.record_growth("n1", False, "unsupported-numeric")  # first coverage → new
    seg = {s["category"]: s for s in RUBRIC.maturity()["segments"]}
    assert seg["unsupported-numeric"]["new"] is True
    RUBRIC.record_growth("n2", False, "unsupported-numeric")  # v2 bump → NOT new
    seg = {s["category"]: s for s in RUBRIC.maturity()["segments"]}
    assert seg["unsupported-numeric"]["new"] is False
    RUBRIC.record_growth("clean-1", True, "clean")            # clean beat → no segment new
    assert all(s["new"] is False for s in RUBRIC.maturity()["segments"])


def test_dashboard_includes_rubric_panel(client):
    body = client.get("/").text
    assert 'id="rubric"' in body
    assert "of 5 failure families" in body
