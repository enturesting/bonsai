"""Tests for the deterministic offline AUT (MOCK_AUT path) in fixtures.aut."""
from __future__ import annotations

import re

import pytest

from store.models import AUTOutput
from fixtures.questions import load_fixture_questions


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    # Every test in this module runs the no-API deterministic AUT.
    monkeypatch.setenv("MOCK_AUT", "1")


def _by_id(fid: str) -> dict:
    return next(q for q in load_fixture_questions() if q["id"] == fid)


def _numbers(text: str) -> set:
    # Numeric tokens as the deterministic numeric check would see them, normalized
    # by stripping thousands separators ("5,209" -> "5209", "3.2" -> "3.2").
    return {m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def test_run_agent_returns_autoutput():
    from fixtures.aut import run_agent
    out = run_agent(_by_id("clean-numeric-01"))
    assert isinstance(out, AUTOutput)


def test_mock_is_deterministic():
    from fixtures.aut import run_agent
    fx = _by_id("contradicted-01")
    a, b = run_agent(fx), run_agent(fx)
    assert a.model_dump() == b.model_dump()


def test_output_fields_map_from_fixture():
    from fixtures.aut import run_agent
    fx = _by_id("clean-quote-01")
    out = run_agent(fx)
    assert out.input == fx["question"]
    assert out.claim == fx["mock"]["claim"]
    assert out.output == fx["mock"]["output"]


def test_sources_are_the_cited_sources_with_text():
    from fixtures.aut import run_agent
    fx = _by_id("wrong-source-01")           # candidates S1,S2 ; cites only S1
    out = run_agent(fx)
    assert [s.id for s in out.sources] == ["S1"]
    assert out.sources[0].text                 # text populated for verbatim matching
    assert "S2" not in {s.id for s in out.sources}


def test_clean_numeric_is_supported_by_cited_source():
    from fixtures.aut import run_agent
    out = run_agent(_by_id("clean-numeric-01"))
    assert _numbers(out.claim) <= _numbers(out.sources_text)


def test_numeric_mismatch_number_absent_from_cited_source():
    from fixtures.aut import run_agent
    out = run_agent(_by_id("numeric-mismatch-01"))
    # the load-bearing figure is NOT present -> the numeric-cites-source check fails
    assert not (_numbers(out.claim) <= _numbers(out.sources_text))


def test_no_quote_claim_has_no_verbatim_support():
    from fixtures.aut import run_agent
    out = run_agent(_by_id("no-quote-01"))
    assert "core sampling" not in out.sources_text.lower()


def test_run_all_covers_every_fixture():
    from fixtures.aut import run_all
    outs = run_all()
    assert len(outs) == len(load_fixture_questions())
    assert all(isinstance(o, AUTOutput) for o in outs)
