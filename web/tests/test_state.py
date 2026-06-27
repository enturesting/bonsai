"""web/state.py — the in-memory rubric whose branches the bonsai tree draws.

/web owns only this DISPLAY history (grow/prune), never minting logic: it records
a branch when it observes an improve's score event from eval_stream.
"""
from __future__ import annotations

from web.state import SEED_CHECK_ID, Rubric

_COORDS = ("x1", "y1", "x2", "y2", "leaf_cx", "leaf_cy")


def test_seed_branch_present_by_default():
    bs = Rubric().branches()
    assert len(bs) == 1
    assert bs[0]["status"] == "seed"
    assert bs[0]["claim_id"] == SEED_CHECK_ID


def test_record_growth_sprouts_a_new_green_branch():
    r = Rubric()
    r.record_growth("clean-numeric-01", True)
    bs = r.branches()
    assert len(bs) == 2
    grown = bs[-1]
    assert grown["claim_id"] == "clean-numeric-01"
    assert grown["status"] == "green"
    assert grown["new"] is True


def test_failed_growth_is_amber():
    r = Rubric()
    r.record_growth("numeric-mismatch-01", False)
    assert r.branches()[-1]["status"] == "amber"


def test_reimproving_same_claim_does_not_double_sprout():
    r = Rubric()
    r.record_growth("c1", True)
    r.record_growth("c1", False)  # latest wins
    grown = [b for b in r.branches() if b["claim_id"] == "c1"]
    assert len(grown) == 1
    assert grown[0]["status"] == "amber"


def test_only_the_latest_branch_is_marked_new():
    r = Rubric()
    r.record_growth("c1", True)
    r.record_growth("c2", True)
    news = [b for b in r.branches() if b.get("new")]
    assert len(news) == 1
    assert news[0]["claim_id"] == "c2"


def test_branches_carry_drawable_coordinates_alternating_sides():
    r = Rubric()
    r.record_growth("c1", True)
    r.record_growth("c2", True)
    bs = r.branches()
    for b in bs:
        for k in _COORDS:
            assert isinstance(b[k], (int, float))
    # grown branches lean off the trunk centre (x=120), alternating sides.
    assert bs[1]["x2"] != 120 and bs[2]["x2"] != 120
    assert (bs[1]["x2"] - 120) * (bs[2]["x2"] - 120) < 0


def test_reset_returns_to_seed_only():
    r = Rubric()
    r.record_growth("c1", True)
    r.reset()
    assert len(r.branches()) == 1
