"""web/mock_stream.py — offline demo insurance: scripts the §2 lifecycle.

Same interface as loop.eval_stream(claim_id): async generator of semantic dicts.
"""
from __future__ import annotations

from web.mock_stream import mock_eval_stream


async def _collect(claim_id):
    return [d async for d in mock_eval_stream(claim_id)]


async def test_scripts_the_section2_lifecycle_in_order(fake_questions):
    events = await _collect("numeric-mismatch-01")
    names = [d["event"] for d in events]
    # yellow pill → chunk(s) → final pill → score → done
    assert names[0] == "pill"
    assert names[-2:] == ["score", "done"]
    assert "chunk" in names
    assert names.count("pill") == 2


async def test_pill_check_id_is_the_claim_id(fake_questions):
    events = await _collect("numeric-mismatch-01")
    pills = [d for d in events if d["event"] == "pill"]
    assert all(p["data"]["check_id"] == "numeric-mismatch-01" for p in pills)
    assert pills[0]["data"]["color"] == "yellow"


async def test_clean_claim_flips_to_green(fake_questions):
    events = await _collect("clean-numeric-01")
    final_pill = [d for d in events if d["event"] == "pill"][-1]
    assert final_pill["data"]["color"] == "green"
    score = [d for d in events if d["event"] == "score"][0]
    assert score["data"]["passed"] is True


async def test_failure_claim_stays_red(fake_questions):
    events = await _collect("numeric-mismatch-01")
    final_pill = [d for d in events if d["event"] == "pill"][-1]
    assert final_pill["data"]["color"] == "red"
    score = [d for d in events if d["event"] == "score"][0]
    assert score["data"]["passed"] is False


async def test_score_shape_counts_and_wilson_ci(fake_questions):
    events = await _collect("clean-numeric-01")
    data = [d for d in events if d["event"] == "score"][0]["data"]
    assert set(data) == {"passed", "before", "after", "n", "ci"}
    lo, hi = data["ci"]
    assert 0.0 <= lo <= hi <= 1.0
    assert isinstance(data["before"], int) and isinstance(data["n"], int)
