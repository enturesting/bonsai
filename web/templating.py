"""Single Jinja2 environment shared by routes AND web/sse.py.

Using one env everywhere means the pill markup the dashboard renders and the pill
markup the SSE adapter streams come from the SAME `_pill.html` partial — they can
never drift, which is what keeps the `outerHTML` swap chain (yellow→green) hitting
the right DOM id.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_partial(name: str, **context: object) -> str:
    """Render a partial template to a stripped string (no Request needed).

    Used by web/sse.py to turn semantic eval_stream dicts into wire HTML.
    """
    return templates.env.get_template(name).render(**context).strip()
