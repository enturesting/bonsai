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
    assert last_pill["data"]["color"] == "green" and last_pill["data"]["label"] == "SUPPORTED"
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
    assert set(score) == {"passed", "before", "after", "n", "ci", "mint"}
    assert score["passed"] is True
    assert score["n"] == 4 and score["before"] == 3 and score["after"] == 3
    lo, hi = score["ci"]
    assert (lo, hi) == engine._wilson(3, 4)
    assert isinstance(lo, float) and isinstance(hi, float)
    # a cleared false positive has no failure to generalize — nothing to mint
    assert score["mint"] is None


async def test_eval_stream_pill_is_red_when_recheck_fails(monkeypatch):
    _install_eval_stream(monkeypatch, passed=False)
    events = await collect(eval_stream("c1"))
    last_pill = [e for e in events if e["event"] == "pill"][-1]
    assert last_pill["data"]["color"] == "red" and last_pill["data"]["label"] == "CAUGHT"
    score = next(e for e in events if e["event"] == "score")["data"]
    assert score["passed"] is False
    # a confirmed failure carries the mint story (inert report under the conftest
    # guard: grow was attempted by the engine, nothing came back to gate in)
    assert score["mint"] is not None and score["mint"]["gated"] is False


# ── eval_stream × the real grow path (cluster→mint→gate→persist) ─────────────
def _minted_check():
    return Check(id="minted-unsupported-numeric",
                 property="Every numeric claim must cite a source containing that figure.",
                 rationale="r", positive_example="p", negative_example="n", overfit_risk="o")


async def test_eval_stream_red_mints_gated_check_into_after_count(monkeypatch):
    """A confirmed miss mints a new gated check, and the after-count is taken over
    the rubric WITH it — the minted check tightens the score it reports."""
    from loop.grower import GrowReport

    minted = _minted_check()
    pool = [out("ok sneaky"), out("ok plain"), out("bad x")]
    target = out("bad target")

    async def ctx(cid):
        return target, a_check("ORIGINAL"), pool

    async def rtoks(output, check):
        yield "rewritten"

    calls = {}

    async def fake_grow(output, check):
        calls["output"], calls["check"] = output, check
        return GrowReport(minted=minted, candidate=minted, gated=True,
                          cluster_size=3, caught_siblings=2, n_known_good=2)

    def rc(check, claim, output):
        if check.id == minted.id:  # the minted check also catches the sneaky item
            return Verdict(passed=("sneaky" not in claim and "ok" in claim), confidence=1.0, reason="")
        return Verdict(passed=("ok" in claim), confidence=1.0, reason="")

    monkeypatch.setattr(engine, "_context", ctx)
    monkeypatch.setattr(engine, "_rewrite_tokens", rtoks)
    monkeypatch.setattr(engine, "_grow_from_miss", fake_grow)
    monkeypatch.setattr(engine, "run_check", rc)

    events = await collect(eval_stream("c1"))
    score = next(e for e in events if e["event"] == "score")["data"]
    assert score["passed"] is False
    assert score["before"] == 2          # seed check alone: both "ok" items green
    assert score["after"] == 1           # conjunction with minted: sneaky now caught
    mint = score["mint"]
    assert mint["gated"] is True and mint["id"] == minted.id
    assert mint["property"] == minted.property
    assert mint["caught_siblings"] == 2 and mint["n_known_good"] == 2
    # grow was seeded with the clicked output + the rewritten check
    assert calls["output"] is target and calls["check"].property == "rewritten"
    # the report is cached for the lineage route (one mint per click, reused)
    cached = engine.last_grow_report("c1")
    assert cached is not None and cached.minted is minted


async def test_green_recheck_leaves_grow_report_cache_empty(monkeypatch):
    _install_eval_stream(monkeypatch, passed=True)
    await collect(eval_stream("c-green"))
    assert engine.last_grow_report("c-green") is None


async def test_eval_stream_green_recheck_never_calls_grow(monkeypatch):
    called = []

    async def fake_grow(output, check):
        called.append(1)
        from loop.grower import GrowReport
        return GrowReport()

    _install_eval_stream(monkeypatch, passed=True)
    monkeypatch.setattr(engine, "_grow_from_miss", fake_grow)
    events = await collect(eval_stream("c1"))
    assert called == []
    assert next(e for e in events if e["event"] == "score")["data"]["mint"] is None


async def test_eval_stream_mint_seam_error_degrades_honestly(monkeypatch):
    """Atlas down must not kill the stream — the score still lands, the after-count
    falls back to the rewritten check alone, and the error is REPORTED in mint."""
    from loop.grower import GrowReport

    async def fake_grow(output, check):
        return GrowReport(error="MONGODB_URI is empty")

    _install_eval_stream(monkeypatch, passed=False, pool_green=3, n=4)
    monkeypatch.setattr(engine, "_grow_from_miss", fake_grow)
    events = await collect(eval_stream("c1"))
    names = [e["event"] for e in events]
    assert names[-1] == "done" and "error" not in names
    score = next(e for e in events if e["event"] == "score")["data"]
    assert score["after"] == 3           # rewritten check alone
    assert score["mint"]["error"] == "MONGODB_URI is empty"
    assert score["mint"]["gated"] is False


async def test_grow_from_miss_seeds_cluster_with_clicked_claim(real_grow_seam, monkeypatch):
    """_grow_from_miss must cluster around the claim that just slipped through
    (negative_example ← output.claim) and degrade to an error report when the
    store seam is unreachable."""
    from loop import grower

    seen = {}

    async def fake_report(worst_check, db):
        seen["check"] = worst_check
        return grower.GrowReport(gated=False)

    monkeypatch.setattr(engine.store, "get_db", lambda: object())
    monkeypatch.setattr(engine, "grow_report", fake_report)
    rep = await engine._grow_from_miss(out("Revenue was 4.2B"), a_check("P"))
    assert seen["check"].negative_example == "Revenue was 4.2B"
    assert rep.error is None

    def boom():
        raise RuntimeError("MONGODB_URI is empty")

    monkeypatch.setattr(engine.store, "get_db", boom)
    rep = await engine._grow_from_miss(out("x"), a_check("P"))
    assert rep.error is not None and "MONGODB_URI" in rep.error


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
