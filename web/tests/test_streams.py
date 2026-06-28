"""web/streams.py — Auto backend selection (mock vs real loop.eval_stream)."""
from __future__ import annotations

from types import SimpleNamespace

import config
from web import streams
from web.mock_stream import mock_eval_stream


def _settings(backend):
    return lambda: SimpleNamespace(loop_backend=backend)


def test_explicit_flag_forces_mock(monkeypatch):
    monkeypatch.setenv("WEB_MOCK_STREAM", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")  # flag still wins
    assert streams.use_mock() is True
    assert streams.resolve_eval_stream() is mock_eval_stream


def test_anthropic_backend_no_key_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("WEB_MOCK_STREAM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(config, "get_settings", _settings("anthropic"))
    assert streams.use_mock() is True
    assert streams.resolve_eval_stream() is mock_eval_stream


def test_gemini_backend_needs_no_anthropic_key_uses_real_loop(monkeypatch):
    # The Gemini/Vertex backend runs the real loop with no Anthropic key (ADC + credit).
    monkeypatch.delenv("WEB_MOCK_STREAM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(config, "get_settings", _settings("gemini"))
    from loop import eval_stream

    assert streams.use_mock() is False
    assert streams.resolve_eval_stream() is eval_stream


def test_anthropic_key_present_uses_real_eval_stream(monkeypatch):
    monkeypatch.delenv("WEB_MOCK_STREAM", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")
    monkeypatch.setattr(config, "get_settings", _settings("anthropic"))
    from loop import eval_stream

    assert streams.use_mock() is False
    assert streams.resolve_eval_stream() is eval_stream
