"""web/sse.py — the wire adapter.

`loop.eval_stream(claim_id)` (or the offline mock) yields SEMANTIC dicts shaped
`{"event": <name>, "data": {...}}` with NO HTML. This module renders each into
the §2 wire shape and wraps it in a `ServerSentEvent`. It owns NO checking logic.

Wire rendering (CONTRACTS §2):
  pill  -> <span id="pill-{check_id}" class="pill pill--{color}" ...>{label}</span>  (outerHTML)
  chunk -> <span>{html-escaped token}</span>                                          (beforeend)
  score -> JSON string of the data dict                                               (innerHTML)
  done  -> ""                                                                          (sse-close)
  error -> red HTML span                                                              (sse-error)
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Callable, Optional

from markupsafe import escape
from sse_starlette.sse import ServerSentEvent

from web.templating import render_partial


def render_pill(data: dict) -> str:
    # data["check_id"] holds the claim_id value (legacy key name) — it is the DOM id.
    return render_partial(
        "_pill.html",
        check_id=data["check_id"],
        color=data["color"],
        label=data["label"],
    )


def render_chunk(data: dict) -> str:
    return f"<span>{escape(data['token'])}</span>"


def render_score(data: dict) -> str:
    return json.dumps(data)


def render_done(data: dict) -> str:
    return ""


def render_error(data: dict) -> str:
    msg = escape(data.get("message", "stream error"))
    return f'<span class="pill pill--red stream-error">⚠ {msg}</span>'


_RENDERERS: dict = {
    "pill": render_pill,
    "chunk": render_chunk,
    "score": render_score,
    "done": render_done,
    "error": render_error,
}


def to_sse(d: dict) -> ServerSentEvent:
    """Map one semantic dict to its wire ServerSentEvent."""
    event = d["event"]
    rendered = _RENDERERS[event](d.get("data", {}))
    return ServerSentEvent(event=event, data=rendered)


async def sse_events(
    claim_id: str,
    stream_fn: Callable[[str], AsyncIterator[dict]],
    observer: Optional[Callable[[dict], None]] = None,
) -> AsyncIterator[ServerSentEvent]:
    """Iterate the (mock or real) eval_stream and yield wire ServerSentEvents.

    `observer` (optional) sees each raw semantic dict before rendering — /web uses
    it to record rubric growth on the `score` event without coupling sse.py to state.
    A mid-stream exception is surfaced as a final `error` event (htmx aborts on it).
    """
    try:
        async for d in stream_fn(claim_id):
            if observer is not None:
                observer(d)
            yield to_sse(d)
    except Exception as exc:  # belt-and-suspenders; eval_stream also self-reports
        # Flip the pill red (never a frozen yellow) before surfacing the message.
        yield to_sse({"event": "pill", "data": {"check_id": claim_id, "color": "red", "label": "ERROR"}})
        yield to_sse({"event": "error", "data": {"message": str(exc)}})
        # done is the only terminator (sse-close="done"); without it the browser
        # EventSource auto-reconnects and the run spinner hangs.
        yield to_sse({"event": "done", "data": {}})
