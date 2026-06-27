"""/web routes — htmx/SSE UI over the eval harness.

This layer owns NO checking/minting logic. It imports only the frozen seams:
`loop.eval_stream` (via web.streams), `fixtures.run_agent`,
`fixtures.load_fixture_questions`, and `eval.scoring.headline`. It never touches
Mongo / Voyage / Anthropic / Gemini directly.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

import fixtures
from eval.scoring import headline
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
    }


def _claim_from_output(q: dict, output) -> dict:
    """Claim dict from a real AUTOutput produced by fixtures.run_agent."""
    return {
        "id": q["id"],
        "question": q.get("question", ""),
        "claim": output.claim,
        "category": q.get("category", ""),
    }


def _baseline_score(n: int) -> dict:
    """Honest starting line: every claim starts RED (0 green of n). Counts + CI."""
    return headline([False] * n, [False] * n)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    questions = fixtures.load_fixture_questions()
    claims = [_claim_from_fixture(q) for q in questions]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "claims": claims, "score": _baseline_score(len(claims))},
    )


@router.post("/run", response_class=HTMLResponse)
async def run(request: Request) -> HTMLResponse:
    """Run the AUT over each fixture → claim_ids + RED pill skeleton.

    claim_id == fixture id, so the pills the dashboard mints match the
    data.check_id values eval_stream will later emit.
    """
    questions = fixtures.load_fixture_questions()
    claims = []
    for q in questions:
        output = fixtures.run_agent(q)
        claims.append(_claim_from_output(q, output))
    return templates.TemplateResponse(
        "_claims.html", {"request": request, "claims": claims}
    )
