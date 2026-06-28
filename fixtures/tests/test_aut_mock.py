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
    out = run_agent(_by_id("secq-clean-encryption-01"))
    assert isinstance(out, AUTOutput)


def test_mock_is_deterministic():
    from fixtures.aut import run_agent
    fx = _by_id("secq-single-source-overcite-01")
    a, b = run_agent(fx), run_agent(fx)
    assert a.model_dump() == b.model_dump()


def test_output_fields_map_from_fixture():
    from fixtures.aut import run_agent
    fx = _by_id("secq-clean-subprocessors-01")
    out = run_agent(fx)
    assert out.input == fx["question"]
    assert out.claim == fx["mock"]["claim"]
    assert out.output == fx["mock"]["output"]


def test_sources_are_the_cited_sources_with_text():
    from fixtures.aut import run_agent
    fx = _by_id("secq-stale-wrong-citation-01")   # candidates S1,S2 ; cites only S1
    out = run_agent(fx)
    assert [s.id for s in out.sources] == ["S1"]
    assert out.sources[0].text                 # text populated for verbatim matching
    assert "S2" not in {s.id for s in out.sources}


def test_clean_numeric_is_supported_by_cited_source():
    from fixtures.aut import run_agent
    # AES-256 / TLS 1.2 in the claim are both present verbatim in the cited policy.
    out = run_agent(_by_id("secq-clean-encryption-01"))
    assert _numbers(out.claim) <= _numbers(out.sources_text)


def test_numeric_mismatch_number_absent_from_cited_source():
    from fixtures.aut import run_agent
    # the claim says "16 characters"; the cited policy states a 12-character minimum,
    # so the load-bearing figure is NOT present -> the numeric-cites-source check fails.
    out = run_agent(_by_id("secq-unsupported-numeric-02"))
    assert not (_numbers(out.claim) <= _numbers(out.sources_text))


def test_fabricated_quote_has_no_verbatim_support():
    from fixtures.aut import run_agent
    # the claimed "zero-data-retention guarantee" appears nowhere in the cited source
    # (which only commits to deleting data within 30 days of termination).
    out = run_agent(_by_id("secq-fabricated-quote-01"))
    assert "zero-data-retention" not in out.sources_text.lower()
    assert "zero data retention" not in out.sources_text.lower()


def test_run_all_covers_every_fixture():
    from fixtures.aut import run_all
    outs = run_all()
    assert len(outs) == len(load_fixture_questions())
    assert all(isinstance(o, AUTOutput) for o in outs)
