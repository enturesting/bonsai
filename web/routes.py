"""/web routes — htmx/SSE UI over the eval harness.

This layer owns NO checking/minting logic. It imports only the frozen seams:
`loop.eval_stream` (via web.streams), `fixtures.run_agent`,
`fixtures.load_fixture_questions`, and `eval.scoring.headline`. It never touches
Mongo / Voyage / Anthropic / Gemini directly.
"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse

import fixtures
from eval.scoring import headline
from web.lineage import resolve_cluster_lineage
from web.sse import sse_events
from web.state import RUBRIC
from web.streams import resolve_eval_stream
from web.templating import templates

router = APIRouter()


def _claim_from_fixture(q: dict) -> dict:
    """Skeleton claim dict from a fixture's offline `mock` (no AUT call)."""
    mock = q.get("mock") or {}
    return {
        "id": q["id"],
        "question": q.get("question", ""),
        "claim": mock.get("claim", ""),
        "category": q.get("category", ""),
        # the source handles the Gemini AUT cited (offline: the fixture's mock script).
        "citations": list(mock.get("cite_ids", [])),
    }


def _claim_from_output(q: dict, output) -> dict:
    """Claim dict from a real AUTOutput produced by fixtures.run_agent."""
    return {
        "id": q["id"],
        "question": q.get("question", ""),
        "claim": output.claim,
        "category": q.get("category", ""),
        # the source handles the Gemini AUT actually grounded this answer on.
        "citations": [s.id for s in output.sources],
    }


def _baseline_score(n: int) -> dict:
    """Honest starting line: every claim starts RED (0 green of n). Counts + CI."""
    return headline([False] * n, [False] * n)


_GOLD_RESULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "gold_result.json"
)


def _load_gold_result() -> dict | None:
    """The PRECOMPUTED gold-gap number (seed vs grown rubric scored against the frozen
    gold set) — display only. /web reads the result file, never the gold items."""
    try:
        with open(_GOLD_RESULT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    questions = fixtures.load_fixture_questions()
    claims = [_claim_from_fixture(q) for q in questions]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "claims": claims,
            "score": _baseline_score(len(claims)),
            "branches": RUBRIC.branches(),
            "gold_result": _load_gold_result(),
        },
    )


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request) -> HTMLResponse:
    """The intro/about page — the no-PowerPoint opening + plain-language explainer."""
    return templates.TemplateResponse("about.html", {"request": request})


@router.post("/reset")
async def reset(request: Request) -> RedirectResponse:
    """Clear the in-memory rubric/tree so the demo starts fresh.

    Display state only — there's NO database to wipe (the tree's growth history lives
    in the process-wide RUBRIC). Redirects back to a clean dashboard.
    """
    RUBRIC.reset()
    return RedirectResponse(url="/", status_code=303)


@router.post("/run", response_class=HTMLResponse)
async def run(request: Request) -> HTMLResponse:
    """Run the AUT over each fixture → claim_ids + RED pill skeleton.

    claim_id == fixture id, so the pills the dashboard mints match the
    data.check_id values eval_stream will later emit.
    """
    questions = fixtures.load_fixture_questions()
    claims = []
    for q in questions:
        try:
            claims.append(_claim_from_output(q, fixtures.run_agent(q)))
        except Exception:  # noqa: BLE001
            # one malformed/blocked live AUT answer must not 500 the whole board —
            # fall back to this tile's offline claim so the board stays complete.
            claims.append(_claim_from_fixture(q))
    return templates.TemplateResponse(
        "_claims.html", {"request": request, "claims": claims}
    )


@router.get("/fragment/improve-container/{claim_id}", response_class=HTMLResponse)
async def improve_container(request: Request, claim_id: str) -> HTMLResponse:
    """The htmx swap target that opens an SSE connection for this claim."""
    return templates.TemplateResponse(
        "_improve.html", {"request": request, "claim_id": claim_id}
    )


def _growth_observer(claim_id: str):
    """Record a rubric branch when the improve's score event passes by.

    This is display history only — /web never mints/prunes; it just watches
    eval_stream's output and remembers that this claim's check evolved.
    """

    def observe(d: dict) -> None:
        if d.get("event") == "score":
            RUBRIC.record_growth(claim_id, bool(d["data"].get("passed")))

    return observe


@router.get("/stream/improve/{claim_id}")
async def stream_improve(claim_id: str) -> EventSourceResponse:
    """Drive eval_stream (real or mock) and emit the §2 events as SSE.

    The pill DOM id the events carry == claim_id, matching the dashboard's pills.
    """
    stream_fn = resolve_eval_stream()
    return EventSourceResponse(
        sse_events(claim_id, stream_fn, observer=_growth_observer(claim_id)),
        ping=20,
        headers={"X-Accel-Buffering": "no"},
    )


@router.get("/tree", response_class=HTMLResponse)
async def tree(request: Request) -> HTMLResponse:
    """The bonsai viz: a branch per minted/evolved check (grow history)."""
    return templates.TemplateResponse(
        "_treesvg.html", {"request": request, "branches": RUBRIC.branches()}
    )


@router.get("/tree/{claim_id}", response_class=HTMLResponse)
async def tree_lineage(request: Request, claim_id: str) -> HTMLResponse:
    """The Atlas money-shot: how this check was minted from a failure cluster.

    Renders seed failure → the nearest failures $vectorSearch returned → the
    minted general check + is_general verdict. The data comes from the frozen
    seams (store.nearest_failures / loop.grow) or, offline, the scripted mock —
    /web owns no clustering/minting itself.
    """
    lineage = await resolve_cluster_lineage()(claim_id)
    return templates.TemplateResponse(
        "_lineage.html", {"request": request, "lineage": lineage}
    )
