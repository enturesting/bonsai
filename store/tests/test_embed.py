"""TDD for store.embed — the Voyage seam (voyage-3, 1024-dim, asymmetric)."""
from __future__ import annotations

import importlib

import pytest

from store.models import EMBED_DIM

# `store/__init__` re-exports the `embed` function, which shadows the `store.embed`
# package attribute. Grab the real module from sys.modules to monkeypatch it.
embed_mod = importlib.import_module("store.embed")


class StubVoyage:
    """Records calls; returns deterministic 1024-dim vectors per input text."""

    def __init__(self):
        self.calls = []

    def embed(self, texts, model, input_type):
        self.calls.append({"texts": list(texts), "model": model, "input_type": input_type})

        class _R:
            embeddings = [[float(len(t))] * EMBED_DIM for t in texts]

        return _R()


@pytest.fixture
def stub(monkeypatch):
    s = StubVoyage()
    monkeypatch.setattr(embed_mod, "_client", s)
    return s


def test_embed_uses_document_input_type_and_passes_all_texts(stub):
    out = embed_mod.embed(["alpha", "beta"])
    assert stub.calls[0]["input_type"] == "document"
    assert stub.calls[0]["model"] == "voyage-3"
    assert stub.calls[0]["texts"] == ["alpha", "beta"]
    assert len(out) == 2
    assert all(len(v) == EMBED_DIM for v in out)


def test_embed_one_returns_single_1024_vector(stub):
    v = embed_mod.embed_one("hello")
    assert isinstance(v, list)
    assert len(v) == EMBED_DIM
    assert stub.calls[0]["input_type"] == "document"


def test_embed_query_uses_query_input_type(stub):
    v = embed_mod.embed_query("a question")
    assert len(v) == EMBED_DIM
    assert stub.calls[0]["input_type"] == "query"
    assert stub.calls[0]["texts"] == ["a question"]


def test_embed_raises_when_key_missing(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "")
    from config import get_settings

    get_settings.cache_clear()
    embed_mod._client = None
    with pytest.raises(RuntimeError, match="VOYAGE_API_KEY"):
        embed_mod.embed(["x"])
