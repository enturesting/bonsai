"""TDD for loop.checker — deterministic → Haiku → Opus escalation."""
from __future__ import annotations

import pytest

from store.models import AUTOutput, Check, Source, Verdict

from loop import checker
from loop.checker import CONF_FLOOR, deterministic, haiku_check, opus_check, run_check


def seed_check(id="numeric-cites-source"):
    return Check(
        id=id,
        property="Every numeric claim has a verbatim supporting quote in a cited source.",
        rationale="numbers without support mislead",
        positive_example="Revenue rose, per S1.",
        negative_example="Revenue was 4.2B (no quote).",
        overfit_risk="might over-match formatted dates",
    )


def out(claim, sources_text=""):
    sources = [Source(text=sources_text)] if sources_text else []
    return AUTOutput(input="q", claim=claim, output="answer", sources=sources)


def v(passed, conf, reason="r"):
    return Verdict(passed=passed, confidence=conf, reason=reason)


# ── deterministic ───────────────────────────────────────────────────────────
def test_deterministic_true_when_number_quoted_verbatim():
    assert deterministic(seed_check(), "Revenue was 4.2 billion",
                         out("x", "Revenue was 4.2 billion in 2023")) is True


def test_deterministic_false_when_number_absent_from_sources():
    assert deterministic(seed_check(), "Revenue was 4.2 billion",
                         out("x", "no figures appear here")) is False


def test_deterministic_true_when_claim_has_no_numbers():
    assert deterministic(seed_check(), "It improved markedly", out("x", "anything")) is True


def test_deterministic_none_for_non_seed_check():
    assert deterministic(seed_check(id="vague-not-checkable"), "x 5", out("x", "")) is None


def test_deterministic_comma_grouped_number_must_match_verbatim():
    assert deterministic(seed_check(), "Sales hit 1,200 units",
                         out("x", "Sales hit 1,200 units last year")) is True
    assert deterministic(seed_check(), "Sales hit 1,200 units",
                         out("x", "Sales hit 1200 units")) is False


# ── run_check escalation logic (LLM stages monkeypatched) ────────────────────
def test_run_check_uses_det_result_when_haiku_agrees_no_opus(monkeypatch):
    monkeypatch.setattr(checker, "deterministic", lambda *a: True)
    monkeypatch.setattr(checker, "haiku_check", lambda *a: v(True, 0.9, "haiku"))
    monkeypatch.setattr(checker, "opus_check", lambda *a: pytest.fail("must not escalate"))
    res = run_check(seed_check(), "c", out("c"))
    assert res.passed is True


def test_run_check_escalates_to_opus_when_det_and_haiku_disagree(monkeypatch):
    monkeypatch.setattr(checker, "deterministic", lambda *a: True)
    monkeypatch.setattr(checker, "haiku_check", lambda *a: v(False, 0.95, "haiku"))
    monkeypatch.setattr(checker, "opus_check", lambda *a: v(True, 1.0, "opus"))
    res = run_check(seed_check(), "c", out("c"))
    assert res.reason == "opus" and res.passed is True


def test_run_check_escalates_when_haiku_unsure_and_no_det_anchor(monkeypatch):
    monkeypatch.setattr(checker, "deterministic", lambda *a: None)
    monkeypatch.setattr(checker, "haiku_check", lambda *a: v(True, CONF_FLOOR - 0.01, "haiku"))
    monkeypatch.setattr(checker, "opus_check", lambda *a: v(False, 1.0, "opus"))
    res = run_check(seed_check(), "c", out("c"))
    assert res.reason == "opus" and res.passed is False


def test_run_check_no_escalate_when_haiku_confident_and_no_det(monkeypatch):
    monkeypatch.setattr(checker, "deterministic", lambda *a: None)
    monkeypatch.setattr(checker, "haiku_check", lambda *a: v(True, CONF_FLOOR, "haiku"))
    monkeypatch.setattr(checker, "opus_check", lambda *a: pytest.fail("must not escalate"))
    res = run_check(seed_check(), "c", out("c"))
    assert res.passed is True and res.confidence == CONF_FLOOR


def test_run_check_falls_back_to_haiku_when_no_det(monkeypatch):
    monkeypatch.setattr(checker, "deterministic", lambda *a: None)
    monkeypatch.setattr(checker, "haiku_check", lambda *a: v(False, 0.8, "haiku"))
    monkeypatch.setattr(checker, "opus_check", lambda *a: pytest.fail("must not escalate"))
    res = run_check(seed_check(), "c", out("c"))
    assert res.passed is False and res.reason == "haiku"


# ── request-shape: Haiku plain, Opus adaptive+effort ─────────────────────────
def test_haiku_check_calls_haiku_plain(patch_llm, fake_client):
    client = patch_llm(fake_client(parsed=[v(True, 0.8, "ok")]))
    res = haiku_check(seed_check(), "claim 5", out("claim 5", "claim 5 here"))
    assert isinstance(res, Verdict) and res.passed is True
    kw = client.messages.parse_calls[0]
    assert kw["model"] == checker.HAIKU == "claude-haiku-4-5"
    assert "thinking" not in kw and "output_config" not in kw
    assert kw["output_format"] is Verdict


def test_opus_check_calls_opus_with_adaptive_and_effort(patch_llm, fake_client):
    client = patch_llm(fake_client(parsed=[v(False, 1.0, "no")]))
    res = opus_check(seed_check(), "claim 5", out("claim 5"))
    assert isinstance(res, Verdict) and res.passed is False
    kw = client.messages.parse_calls[0]
    assert kw["model"] == checker.OPUS == "claude-opus-4-8"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"] == {"effort": "high"}
    assert kw["output_format"] is Verdict
