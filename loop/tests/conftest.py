"""Shared fixtures for the /loop suite.

The /loop engine is the ONLY terminal that talks to Anthropic. Tests never make a
real API call: `patch_llm` swaps `loop.llm.get_client()` for a `FakeClient` that
records every `messages.parse(...)` / `messages.stream(...)` kwarg, so we can both
assert the exact request shape (Opus adaptive+effort, Haiku plain) and feed back
canned `parsed_output` Verdicts/Checks. The store + fixtures seams (built in other
terminals) are monkeypatched per-test against the frozen CONTRACTS interface.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


class FakeStream:
    """Mimics `client.messages.stream(...)` context manager + `.text_stream`."""

    def __init__(self, tokens):
        self._tokens = list(tokens)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield from self._tokens

    def get_final_message(self):  # parity with the real helper; unused by most tests
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="".join(self._tokens))])


class FakeMessages:
    def __init__(self, parsed=None, tokens=()):
        self.parse_calls = []
        self.stream_calls = []
        self._parsed = list(parsed or [])
        self._tokens = tokens

    def parse(self, **kwargs):
        self.parse_calls.append(kwargs)
        if not self._parsed:
            raise AssertionError("FakeClient.messages.parse called with no queued outputs")
        return SimpleNamespace(parsed_output=self._parsed.pop(0))

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)
        return FakeStream(self._tokens)


class FakeClient:
    def __init__(self, parsed=None, tokens=()):
        self.messages = FakeMessages(parsed=parsed, tokens=tokens)


@pytest.fixture
def fake_client():
    """Factory: fake_client(parsed=[Verdict(...)], tokens=["a","b"])."""
    def _make(parsed=None, tokens=()):
        return FakeClient(parsed=parsed, tokens=tokens)
    return _make


@pytest.fixture(autouse=True)
def _no_network_mint(request, monkeypatch):
    """eval_stream's red path now drives the REAL grow seam (_grow_from_miss →
    Atlas + Voyage + the model). A local .env can carry live keys, so unit tests
    must never reach it: default the seam to an inert empty report. A test that
    exercises the seam itself opts out by requesting `real_grow_seam`."""
    from loop import engine

    engine._LAST_GROW.clear()  # per-claim grow-report cache must not leak between tests
    if "real_grow_seam" in request.fixturenames:
        yield
        return
    from loop.grower import GrowReport

    async def _inert(output, check):
        return GrowReport()

    monkeypatch.setattr(engine, "_grow_from_miss", _inert)
    yield


@pytest.fixture
def real_grow_seam():
    """Opt out of the autouse _no_network_mint guard (test patches its own seams)."""
    return None


@pytest.fixture
def patch_llm(monkeypatch):
    """Install a FakeClient as the singleton Anthropic client for loop.llm."""
    def _install(client):
        from loop import llm
        # Force the Anthropic path so the FakeClient + request-shape assertions apply
        # (default backend is gemini; tests pin anthropic to exercise get_client).
        monkeypatch.setattr(llm, "_backend", lambda: "anthropic")
        monkeypatch.setattr(llm, "get_client", lambda: client)
        return client
    return _install
