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
from web.lineage import mock_cluster_lineage, resolve_cluster_lineage
from web.live_claims import LIVE, pool_with_live
from web.mock_stream import mock_eval_stream
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
    # merged pool: the board AND the baseline n must come from the SAME pool the
    # score stream uses (pool_with_live), or they diverge after a refresh.
    questions = pool_with_live()
    claims = [_claim_from_fixture(q) for q in questions]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "claims": claims,
            "score": _baseline_score(len(claims)),
            "branches": RUBRIC.branches(),
            "checks": RUBRIC.checks(),
            "maturity": RUBRIC.maturity(),
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
    LIVE.reset()
    return RedirectResponse(url="/", status_code=303)


@router.post("/live-claim", response_class=HTMLResponse)
async def live_claim(request: Request) -> HTMLResponse:
    """Add a presenter-typed claim as a fixture-shaped tile (mock path only).

    Renders just the new RED tile. The tile then drives the SAME §2 SSE lifecycle
    as any fixture — the mock is forced for live ids (see /stream/improve and /tree
    below), so it stays deterministic even on a key-present deployment.
    """
    form = await request.form()
    claim = (form.get("claim") or "").strip()
    if not claim:  # empty box → no-op (the form's after-request guard keeps typed text)
        return HTMLResponse("")
    entry = LIVE.add(
        claim=claim,
        source_text=(form.get("source") or "").strip(),
        category=(form.get("category") or "unsupported-numeric").strip(),
        question=(form.get("question") or "").strip(),
    )
    # Render JUST the tile — NO out-of-band score swap. _baseline_score is all-RED
    # (before=0/after=0), and an hx-swap-oob would outerHTML-replace #score-display,
    # clobbering the running greens main.js rendered after a prior flip (the primary
    # path is flip → "now you try" → add). The next improve's score event carries the
    # correct n from pool_with_live() and self-corrects the denominator.
    return templates.TemplateResponse(
        "_claim.html",
        {"request": request, "c": _claim_from_fixture(entry)},
    )


@router.post("/run", response_class=HTMLResponse)
async def run(request: Request) -> HTMLResponse:
    """Run the AUT over each fixture → claim_ids + RED pill skeleton.

    claim_id == fixture id, so the pills the dashboard mints match the
    data.check_id values eval_stream will later emit.
    """
    # build from the MERGED pool so re-running can never wipe live tiles / desync n
    # (this route is currently UI-dead — the Run button was removed — but stays safe).
    questions = pool_with_live()
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


def _category_for(claim_id: str) -> str:
    """The failure category for a claim id (fixture OR live) — powers the maturity
    meter. pool_with_live() is cached/cheap and already the resolver everywhere else."""
    for q in pool_with_live():
        if q.get("id") == claim_id:
            return q.get("category", "")
    return ""


def _growth_observer(claim_id: str):
    """Record a rubric branch when the improve's score event passes by.

    This is display history only — /web never mints/prunes; it just watches
    eval_stream's output and remembers that this claim's check evolved.
    """
    cat = _category_for(claim_id)

    def observe(d: dict) -> None:
        if d.get("event") == "score":
            RUBRIC.record_growth(claim_id, bool(d["data"].get("passed")), cat)

    return observe


@router.get("/stream/improve/{claim_id}")
async def stream_improve(claim_id: str) -> EventSourceResponse:
    """Drive eval_stream (real or mock) and emit the §2 events as SSE.

    The pill DOM id the events carry == claim_id, matching the dashboard's pills.
    """
    # Live (typed-on-stage) claims are presenter-scripted: force the deterministic
    # mock even on a key-present box (the real engine would mis-resolve the live id
    # to questions[0] or run the live AUT over typed text).
    stream_fn = mock_eval_stream if claim_id in LIVE.ids() else resolve_eval_stream()
    return EventSourceResponse(
        sse_events(claim_id, stream_fn, observer=_growth_observer(claim_id)),
        ping=20,
        headers={"X-Accel-Buffering": "no"},
    )


@router.get("/rubric", response_class=HTMLResponse)
async def rubric(request: Request) -> HTMLResponse:
    """The living checklist + maturity meter — refreshed on the same `grow` event
    the tree listens to. Display state only (RUBRIC.checks/maturity)."""
    return templates.TemplateResponse(
        "_rubric.html",
        {"request": request, "checks": RUBRIC.checks(), "maturity": RUBRIC.maturity()},
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
    # main.js auto-fetches this on every flip; for a live id force the mock lineage
    # so a key-present box never runs real Voyage+Atlas+loop.grow over typed text
    # (slow / non-deterministic / can hang). One guard covers the auto-fetch AND a
    # clicked grown leaf (same route).
    lineage_fn = mock_cluster_lineage if claim_id in LIVE.ids() else resolve_cluster_lineage()
    lineage = await lineage_fn(claim_id)
    return templates.TemplateResponse(
        "_lineage.html", {"request": request, "lineage": lineage}
    )
