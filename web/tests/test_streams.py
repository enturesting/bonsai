"""web/streams.py — Auto backend selection (mock vs real loop.eval_stream)."""
from __future__ import annotations

from web import streams
from web.mock_stream import mock_eval_stream


def test_explicit_flag_forces_mock(monkeypatch):
    monkeypatch.setenv("WEB_MOCK_STREAM", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")  # flag still wins
    assert streams.use_mock() is True
    assert streams.resolve_eval_stream() is mock_eval_stream


def test_no_api_key_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("WEB_MOCK_STREAM", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert streams.use_mock() is True
    assert streams.resolve_eval_stream() is mock_eval_stream


def test_key_present_and_loop_importable_uses_real_eval_stream(monkeypatch):
    monkeypatch.delenv("WEB_MOCK_STREAM", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-key")
    from loop import eval_stream

    assert streams.use_mock() is False
    assert streams.resolve_eval_stream() is eval_stream
