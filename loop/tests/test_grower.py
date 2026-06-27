"""TDD for loop.grower — check-minting + is_general gate + grow cycle.

The /store seam (nearest_failures, known_good_sample, upsert_check) is built in a
parallel terminal; grower references `store.X` at call-time and tests inject async
fakes with monkeypatch(raising=False), so /loop tests never depend on /store's
build progress.
"""
from __future__ import annotations

import store as store_pkg

from store.models import AUTOutput, Check, Failure, Source, Verdict

from loop import OPUS
from loop import grower
from loop.grower import grow, is_general, mint_check, mint_check_from_miss


def a_check(id="numeric-cites-source"):
    return Check(id=id, property="Every numeric claim has a verbatim supporting quote.",
                 rationale="r", positive_example="p",
                 negative_example="Revenue was 4.2B with no quote.", overfit_risk="o")


def a_failure(id="f1", claim="Revenue was 4.2B"):
    return Failure(id=id, input="What was revenue?", claim=claim,
                   expected="cite a verbatim figure", actual="Revenue was 4.2B", why="no supporting quote")


def passer(claim="Margins held"):
    return AUTOutput(input="q", claim=claim, output="ans", sources=[Source(text=claim + " per the filing")])


def faily(claim="EPS was 3.10"):
    return AUTOutput(input="q", claim=claim, output="ans", sources=[])  # no sources → numeric claim unsupported


# ── mint_check ───────────────────────────────────────────────────────────────
def test_mint_check_calls_opus_with_check_schema_and_failure_body(patch_llm, fake_client):
    minted = a_check(id="minted")
    client = patch_llm(fake_client(parsed=[minted]))
    res = mint_check(a_failure())
    assert res is minted
    kw = client.messages.parse_calls[0]
    assert kw["model"] == OPUS
    assert kw["thinking"] == {"type": "adaptive"} and kw["output_config"] == {"effort": "high"}
    assert kw["output_format"] is Check
    body = kw["messages"][0]["content"]
    assert "no supporting quote" in body and "Revenue was 4.2B" in body


# ── mint_check_from_miss ─────────────────────────────────────────────────────
def test_mint_check_from_miss_builds_failure_from_output(monkeypatch):
    captured = {}

    def _capture(f):
        captured["f"] = f
        return a_check("from-miss")

    monkeypatch.setattr(grower, "mint_check", _capture)
    out = AUTOutput(input="What was net income?", claim="Net income was 9.9B",
                    output="Net income was 9.9B", sources=[])
    res = mint_check_from_miss(out, "number with no verbatim quote")
    assert res.id == "from-miss"
    f = captured["f"]
    assert isinstance(f, Failure)
    assert f.input == out.input and f.claim == out.claim and f.actual == out.output
    assert f.why == "number with no verbatim quote"
    assert f.id  # a stable, non-empty slug


# ── is_general gate ──────────────────────────────────────────────────────────
def _discriminating_run_check(check, claim, output):
    # pass when the output cites the claim, fail otherwise (numeric/unsupported)
    return Verdict(passed=bool(output.sources), confidence=1.0, reason="")


def test_is_general_true_when_all_good_pass_and_two_plus_fail(monkeypatch):
    monkeypatch.setattr(grower, "run_check", _discriminating_run_check)
    known_good = [passer("a"), passer("b")]
    cluster = [faily("x"), faily("y"), faily("z")]
    assert is_general(a_check(), known_good, cluster) is True


def test_is_general_false_when_a_known_good_fails(monkeypatch):
    monkeypatch.setattr(grower, "run_check", _discriminating_run_check)
    known_good = [passer("a"), faily("regressed")]  # one good item wrongly fails
    cluster = [faily("x"), faily("y")]
    assert is_general(a_check(), known_good, cluster) is False


def test_is_general_false_when_fewer_than_two_failures_caught(monkeypatch):
    monkeypatch.setattr(grower, "run_check", _discriminating_run_check)
    known_good = [passer("a")]
    cluster = [faily("x"), passer("not actually a failure")]  # only 1 caught
    assert is_general(a_check(), known_good, cluster) is False


# ── grow cycle ───────────────────────────────────────────────────────────────
def _install_store(monkeypatch, *, cluster, known_good, upserts):
    async def _nearest(seed, db, **kw):
        return cluster

    async def _known(db, k=8):
        return known_good

    async def _upsert(c, db):
        upserts.append(c)
        return c.id

    monkeypatch.setattr(store_pkg, "nearest_failures", _nearest, raising=False)
    monkeypatch.setattr(store_pkg, "known_good_sample", _known, raising=False)
    monkeypatch.setattr(store_pkg, "upsert_check", _upsert, raising=False)


async def test_grow_mints_and_upserts_when_general(monkeypatch):
    minted = a_check("grown")
    upserts = []
    _install_store(monkeypatch, cluster=[a_failure("f1"), a_failure("f2")], known_good=[passer()], upserts=upserts)
    monkeypatch.setattr(grower, "mint_check", lambda f: minted)
    monkeypatch.setattr(grower, "is_general", lambda c, kg, cf: True)
    res = await grow(a_check(), db=object())
    assert res is minted
    assert upserts == [minted]  # persisted to the rubric store


async def test_grow_returns_none_and_does_not_upsert_when_overfit(monkeypatch):
    upserts = []
    _install_store(monkeypatch, cluster=[a_failure("f1"), a_failure("f2")], known_good=[passer()], upserts=upserts)
    monkeypatch.setattr(grower, "mint_check", lambda f: a_check("grown"))
    monkeypatch.setattr(grower, "is_general", lambda c, kg, cf: False)
    res = await grow(a_check(), db=object())
    assert res is None
    assert upserts == []


async def test_grow_returns_none_on_empty_cluster(monkeypatch):
    upserts = []
    _install_store(monkeypatch, cluster=[], known_good=[passer()], upserts=upserts)
    monkeypatch.setattr(grower, "mint_check", lambda f: (_ for _ in ()).throw(AssertionError("no mint on empty")))
    res = await grow(a_check(), db=object())
    assert res is None
