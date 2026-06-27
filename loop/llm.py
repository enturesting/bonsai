"""The single Anthropic seam for /loop.

Every Opus/Haiku call in the engine goes through one of the helpers here, so the
exact request shape lives in exactly one place:

  * Opus 4.8 (grower / judge / skeptic):  thinking={"type":"adaptive"} +
    output_config={"effort":"high"}  — never budget_tokens.
  * Haiku 4.5 (cheap checker):            plain — no thinking, no effort
    (both error on Haiku 4.5).

Structured output uses ``client.messages.parse(..., output_format=Model)`` →
``.parsed_output`` (the current SDK's validated path). Streaming uses
``client.messages.stream(...).text_stream``.

NOTE (integration): the locally-installed `anthropic` may predate `messages.parse`
/ adaptive thinking / effort. These helpers target the frozen CONTRACTS shapes;
real calls need a current SDK (`pip install -U anthropic`). Tests never hit the
network — they patch `get_client`.
"""
from __future__ import annotations

HAIKU = "claude-haiku-4-5"  # cheap checker — plain, no effort/adaptive
OPUS = "claude-opus-4-8"     # grower / judge / skeptic — adaptive + effort=high

_client = None


def get_client():
    """Lazy singleton Anthropic client (built on first real use, not import)."""
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def haiku_parse(*, system, user, schema, max_tokens=400):
    """Plain Haiku structured call → validated `schema` instance."""
    resp = get_client().messages.parse(
        model=HAIKU,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return resp.parsed_output


def opus_parse(*, system, user, schema, max_tokens=1500):
    """Opus structured call (adaptive thinking + high effort) → `schema` instance."""
    resp = get_client().messages.parse(
        model=OPUS,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return resp.parsed_output


def opus_stream_text(*, system, user, max_tokens=2000):
    """Opus streaming (adaptive + high effort) yielding text-delta tokens."""
    with get_client().messages.stream(
        model=OPUS,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for text in stream.text_stream:
            yield text
