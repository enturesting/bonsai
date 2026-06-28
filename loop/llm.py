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

from config import get_settings

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


def _backend() -> str:
    """Engine LLM provider: 'gemini' (Vertex, free via credit) or 'anthropic'."""
    return get_settings().loop_backend


# ── Gemini / Vertex backend (default) ───────────────────────────────────────

_gemini = None


def _gemini_client():
    """Lazy singleton google-genai Vertex client — one transport, reused across calls
    (a fresh client per call can close the shared httpx transport on GC)."""
    global _gemini
    if _gemini is None:
        from google import genai  # google-genai unified SDK (lazy import)

        cfg = get_settings()
        _gemini = genai.Client(
            vertexai=True,
            project=cfg.google_cloud_project,
            location=cfg.google_cloud_location,
        )
    return _gemini


def _gemini_parse(*, system, user, schema, max_tokens):
    """Gemini structured call (Vertex JSON mode) → validated `schema` instance."""
    from google.genai import types

    cfg = get_settings()
    resp = _gemini_client().models.generate_content(
        model=cfg.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=max_tokens,
            # Gemini 3.x thinking shares the output budget; disable it so the small
            # structured verdict/check always fits and returns fast.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    parsed = resp.parsed
    if parsed is None:  # fall back to manual validation if .parsed is unset
        parsed = schema.model_validate_json(resp.text)
    return parsed


def _gemini_stream_text(*, system, user, max_tokens):
    """Gemini streaming (Vertex) yielding text-delta tokens for the rule rewrite."""
    from google.genai import types

    cfg = get_settings()
    for chunk in _gemini_client().models.generate_content_stream(
        model=cfg.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            # No thinking → tokens stream immediately (no pre-stream pause on stage).
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    ):
        if chunk.text:
            yield chunk.text


# ── Public helpers (route on the configured backend) ────────────────────────

def haiku_parse(*, system, user, schema, max_tokens=400):
    """Cheap structured check → validated `schema` instance (Gemini or plain Haiku)."""
    if _backend() == "gemini":
        return _gemini_parse(system=system, user=user, schema=schema, max_tokens=max_tokens)
    resp = get_client().messages.parse(
        model=HAIKU,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return resp.parsed_output


def opus_parse(*, system, user, schema, max_tokens=1500):
    """Strong structured call → `schema` instance (Gemini, or Opus adaptive+effort)."""
    if _backend() == "gemini":
        return _gemini_parse(system=system, user=user, schema=schema, max_tokens=max_tokens)
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
    """Streaming text-delta tokens for the rule rewrite (Gemini, or Opus)."""
    if _backend() == "gemini":
        yield from _gemini_stream_text(system=system, user=user, max_tokens=max_tokens)
        return
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
