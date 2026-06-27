"""TDD for loop.pruner — drop checks outside the 5–95% pass band."""
from __future__ import annotations

from store.models import AUTOutput, Check, Verdict

from loop import grower  # noqa: F401  (ensures package import path is warm)
from loop import pruner
from loop.pruner import PRUNE_HI, PRUNE_LO, prune


def chk(id):
    return Check(id=id, property=f"prop {id}", rationale="r",
                 positive_example="p", negative_example="n", overfit_risk="o")


def item(i):
    return AUTOutput(input="q", claim=f"claim {i}", output="ans", sources=[])


def make_run_check(plan):
    """Replay a per-check pass/fail plan: {check_id: [bool, ...]}."""
    counters = {}

    def _rc(check, claim, output):
        i = counters.get(check.id, 0)
        counters[check.id] = i + 1
        return Verdict(passed=plan[check.id][i], confidence=1.0, reason="")

    return _rc


def test_prune_drops_check_that_always_passes(monkeypatch):
    items = [item(i) for i in range(20)]
    monkeypatch.setattr(pruner, "run_check", make_run_check({"trivial": [True] * 20}))
    assert prune([chk("trivial")], items) == []


def test_prune_drops_check_that_always_fails(monkeypatch):
    items = [item(i) for i in range(20)]
    monkeypatch.setattr(pruner, "run_check", make_run_check({"degenerate": [False] * 20}))
    assert prune([chk("degenerate")], items) == []


def test_prune_keeps_discriminating_check(monkeypatch):
    items = [item(i) for i in range(20)]
    monkeypatch.setattr(pruner, "run_check", make_run_check({"mid": [True] * 10 + [False] * 10}))
    kept = prune([chk("mid")], items)
    assert [c.id for c in kept] == ["mid"]


def test_prune_keeps_rates_exactly_on_the_band_edges(monkeypatch):
    # 19/20 = 0.95 (== PRUNE_HI, not >) and 1/20 = 0.05 (== PRUNE_LO, not <): both kept
    items = [item(i) for i in range(20)]
    plan = {"hi": [True] * 19 + [False], "lo": [True] + [False] * 19}
    monkeypatch.setattr(pruner, "run_check", make_run_check(plan))
    assert PRUNE_HI == 0.95 and PRUNE_LO == 0.05
    kept = prune([chk("hi"), chk("lo")], items)
    assert {c.id for c in kept} == {"hi", "lo"}


def test_prune_filters_a_mixed_rubric_preserving_order(monkeypatch):
    items = [item(i) for i in range(20)]
    plan = {
        "always": [True] * 20,          # drop
        "good": [True] * 12 + [False] * 8,   # keep
        "never": [False] * 20,          # drop
        "ok": [True] * 4 + [False] * 16,     # keep (0.20)
    }
    monkeypatch.setattr(pruner, "run_check", make_run_check(plan))
    rubric = [chk("always"), chk("good"), chk("never"), chk("ok")]
    assert [c.id for c in prune(rubric, items)] == ["good", "ok"]


def test_prune_keeps_everything_when_no_items_to_judge(monkeypatch):
    monkeypatch.setattr(pruner, "run_check", make_run_check({}))  # never called
    rubric = [chk("a"), chk("b")]
    assert prune(rubric, []) == rubric
