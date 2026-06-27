"""TDD for loop.engine — Wilson CI, run_checker, rewrite_rule_stream, eval_stream.

eval_stream is the single generator /web iterates. Lifecycle (CONTRACTS §2):
pill(yellow) → chunk×N → pill(green|red) → score → done (+ optional error).
The fixtures/store seams are resolved inside engine._context, patched per-test.
"""
from __future__ import annotations

import asyncio
import pathlib

import pytest

from store.models import AUTOutput, Check, Source, Verdict

from loop import OPUS
from loop import engine
from loop.engine import eval_stream, rewrite_rule_stream, run_checker


def out(claim, sources_text=""):
    sources = [Source(text=sources_text)] if sources_text else []
    return AUTOutput(input="q", claim=claim, output="ans " + claim, sources=sources)


def a_check(prop="ORIGINAL property"):
    return Check(id="numeric-cites-source", property=prop, rationale="r",
                 positive_example="p", negative_example="n", overfit_risk="o")


async def collect(agen):
    return [x async for x in agen]


# ── Wilson CI (closed form, no statsmodels) ──────────────────────────────────
def test_wilson_full_interval_for_zero_samples():
    assert engine._wilson(0, 0) == (0.0, 1.0)


def test_wilson_matches_known_value_27_of_31():
    lo, hi = engine._wilson(27, 31)
    assert abs(lo - 0.71) < 0.01 and abs(hi - 0.95) < 0.01


def test_wilson_bounds_stay_within_unit_interval():
    for k, n in [(0, 5), (5, 5), (1, 40), (39, 40)]:
        lo, hi = engine._wilson(k, n)
        assert 0.0 <= lo <= hi <= 1.0


# ── run_checker ──────────────────────────────────────────────────────────────
async def test_run_checker_applies_rewritten_rule_then_rechecks(monkeypatch):
    seen = {}

    async def ctx(cid):
        return out("Revenue 4.2B"), a_check("ORIGINAL property"), []

    def rc(check, claim, output):
        seen["property"] = check.property
        return Verdict(passed=True, confidence=1.0, reason="")

    monkeypatch.setattr(engine, "_context", ctx)
    monkeypatch.setattr(engine, "run_check", rc)
    res = await run_checker("c1", "Numbers must cite a verbatim source row.")
    assert res is True
    assert seen["property"] == "Numbers must cite a verbatim source row."  # rule applied


async def test_run_checker_keeps_original_property_when_rule_blank(monkeypatch):
    seen = {}

    async def ctx(cid):
        return out("x"), a_check("ORIGINAL property"), []

    monkeypatch.setattr(engine, "_context", ctx)
    monkeypatch.setattr(engine, "run_check",
                        lambda check, claim, output: seen.update(property=check.property) or Verdict(passed=False, confidence=1.0, reason=""))
    res = await run_checker("c1", "   ")
    assert res is False and seen["property"] == "ORIGINAL property"


# ── rewrite_rule_stream ──────────────────────────────────────────────────────
async def test_rewrite_rule_stream_yields_opus_tokens_with_adaptive_effort(patch_llm, fake_client, monkeypatch):
    client = patch_llm(fake_client(tokens=["Numeric ", "claims ", "must cite."]))

    async def ctx(cid):
        return out("Revenue 4.2B"), a_check(), []

    monkeypatch.setattr(engine, "_context", ctx)
    tokens = await collect(rewrite_rule_stream("c1"))
    assert tokens == ["Numeric ", "claims ", "must cite."]
    kw = client.messages.stream_calls[0]
    assert kw["model"] == OPUS
    assert kw["thinking"] == {"type": "adaptive"} and kw["output_config"] == {"effort": "high"}


# ── eval_stream lifecycle ────────────────────────────────────────────────────
def _install_eval_stream(monkeypatch, *, passed, pool_green=3, n=4, tokens=("IF ", "numeric")):
    # the target claim drives the pill; "ok" claims pass run_check
    target = out("ok target" if passed else "bad target")
    pool = [out("ok %d" % i) for i in range(pool_green)] + [out("bad %d" % i) for i in range(n - pool_green)]

    async def ctx(cid):
        return target, a_check("ORIGINAL"), pool

    async def rtoks(output, check):
        for t in tokens:
            yield t

    monkeypatch.setattr(engine, "_context", ctx)
    monkeypatch.setattr(engine, "_rewrite_tokens", rtoks)
    # pill verdict (target) and before/after counts (pool) both flow through run_check
    monkeypatch.setattr(engine, "run_check",
                        lambda check, claim, output: Verdict(passed=("ok" in claim), confidence=1.0, reason=""))
    return pool


async def test_eval_stream_emits_full_lifecycle_in_order(monkeypatch):
    _install_eval_stream(monkeypatch, passed=True)
    events = await collect(eval_stream("claim-1"))
    names = [e["event"] for e in events]
    assert names == ["pill", "chunk", "chunk", "pill", "score", "done"]

    first_pill, c1, c2, last_pill, score, done = events
    assert first_pill["data"] == {"color": "yellow", "check_id": "claim-1", "label": "CHECKING…"}
    assert c1["data"] == {"token": "IF "} and c2["data"] == {"token": "numeric"}
    assert last_pill["data"]["color"] == "green" and last_pill["data"]["label"] == "GREEN"
    assert last_pill["data"]["check_id"] == "claim-1"
    assert done["data"] == {}


async def test_eval_stream_resolves_context_exactly_once(monkeypatch):
    # The pill (passed) and the before/after counts must derive from ONE AUT
    # generation, or with a non-deterministic AUT the green pill can disagree with
    # the after-count it's meant to back. One resolution also avoids 3x(N+1) Gemini
    # calls blocking the SSE event loop.
    from loop import llm

    calls = {"n": 0}
    target, pool = out("ok target"), [out("ok a"), out("bad b")]

    async def ctx(cid):
        calls["n"] += 1
        return target, a_check("ORIGINAL"), pool

    monkeypatch.setattr(engine, "_context", ctx)
    monkeypatch.setattr(engine, "run_check",
                        lambda check, claim, output: Verdict(passed=("ok" in claim), confidence=1.0, reason=""))
    monkeypatch.setattr(llm, "opus_stream_text", lambda **kw: iter(["IF ", "numeric"]))

    events = await collect(eval_stream("c1"))
    assert calls["n"] == 1, f"_context resolved {calls['n']}x (must be 1)"
    # pill verdict and the after-count come from the same resolved generation
    last_pill = [e for e in events if e["event"] == "pill"][-1]
    score = next(e for e in events if e["event"] == "score")["data"]
    assert last_pill["data"]["color"] == "green" and score["passed"] is True


async def test_eval_stream_score_shape_counts_and_wilson(monkeypatch):
    _install_eval_stream(monkeypatch, passed=True, pool_green=3, n=4)
    events = await collect(eval_stream("claim-1"))
    score = next(e for e in events if e["event"] == "score")["data"]
    assert set(score) == {"passed", "before", "after", "n", "ci"}
    assert score["passed"] is True
    assert score["n"] == 4 and score["before"] == 3 and score["after"] == 3
    lo, hi = score["ci"]
    assert (lo, hi) == engine._wilson(3, 4)
    assert isinstance(lo, float) and isinstance(hi, float)


async def test_eval_stream_pill_is_red_when_recheck_fails(monkeypatch):
    _install_eval_stream(monkeypatch, passed=False)
    events = await collect(eval_stream("c1"))
    last_pill = [e for e in events if e["event"] == "pill"][-1]
    assert last_pill["data"]["color"] == "red" and last_pill["data"]["label"] == "RED"
    score = next(e for e in events if e["event"] == "score")["data"]
    assert score["passed"] is False


async def test_eval_stream_emits_error_then_done_on_failure(monkeypatch):
    async def boom(cid):
        raise RuntimeError("store down")

    monkeypatch.setattr(engine, "_context", boom)
    events = await collect(eval_stream("c1"))
    assert events[-2]["event"] == "error" and "store down" in events[-2]["data"]["message"]
    assert events[-1]["event"] == "done"


async def test_eval_stream_propagates_client_cancellation(monkeypatch):
    pool = [out("ok")]

    async def ctx(cid):
        return pool[0], a_check(), pool

    async def cancel_stream(output, check):
        raise asyncio.CancelledError
        yield  # pragma: no cover  (makes this an async generator)

    monkeypatch.setattr(engine, "_context", ctx)
    monkeypatch.setattr(engine, "run_check",
                        lambda *a: Verdict(passed=True, confidence=1.0, reason=""))
    monkeypatch.setattr(engine, "_rewrite_tokens", cancel_stream)
    with pytest.raises(asyncio.CancelledError):
        async for _ in eval_stream("c1"):
            pass


# ── honesty rail: /loop must never import /eval or read gold ─────────────────
def test_loop_never_references_eval_gold():
    import re

    loop_dir = pathlib.Path(__file__).resolve().parent.parent
    # the eval PACKAGE (\beval\b excludes eval_stream/evaluate), plus gold artifacts
    forbidden = (
        r"\b(?:from|import)\s+eval\b",   # importing the /eval package
        r"eval/gold",                    # reading the gold dir
        r"\bload_gold\b",
        r"\bscore_rubric\b",
    )
    offenders = []
    for py in loop_dir.glob("*.py"):
        text = py.read_text()
        for pat in forbidden:
            if re.search(pat, text):
                offenders.append(f"{py.name}: /{pat}/")
    assert offenders == [], f"gold/eval leak in /loop: {offenders}"
