"""TDD for loop.skeptic — Opus adversarial refutation of a PASS verdict."""
from __future__ import annotations

from store.models import AUTOutput, Source, Verdict

from loop import OPUS
from loop.skeptic import skeptic


def out(claim="Revenue was 4.2B", sources_text="Revenue was 4.2B in 2023"):
    return AUTOutput(input="q", claim=claim, output="answer",
                     sources=[Source(text=sources_text)])


def test_skeptic_returns_pass_unchanged_when_verdict_already_failed(patch_llm, fake_client):
    client = patch_llm(fake_client(parsed=[]))  # any parse call would raise
    failing = Verdict(passed=False, confidence=0.9, reason="no support")
    res = skeptic(out(), failing)
    assert res is failing  # nothing to refute → no Opus call
    assert client.messages.parse_calls == []


def test_skeptic_challenges_a_pass_with_opus_adaptive_effort(patch_llm, fake_client):
    client = patch_llm(fake_client(parsed=[Verdict(passed=True, confidence=1.0, reason="holds up")]))
    passing = Verdict(passed=True, confidence=0.8, reason="looks supported")
    res = skeptic(out(), passing)
    assert isinstance(res, Verdict)
    kw = client.messages.parse_calls[0]
    assert kw["model"] == OPUS == "claude-opus-4-8"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"] == {"effort": "high"}
    assert kw["output_format"] is Verdict


def test_skeptic_can_flip_a_weak_pass_to_fail(patch_llm, fake_client):
    patch_llm(fake_client(parsed=[Verdict(passed=False, confidence=0.95, reason="quote not verbatim")]))
    passing = Verdict(passed=True, confidence=0.76, reason="seems ok")
    res = skeptic(out(), passing)
    assert res.passed is False and "verbatim" in res.reason
