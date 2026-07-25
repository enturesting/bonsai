"""/web routes — htmx/SSE UI over the eval harness.

This layer owns NO checking/minting logic. It imports only the frozen seams:
`loop.eval_stream` (via web.streams), `fixtures.run_agent`,
`fixtures.load_fixture_questions`, and `eval.scoring.headline`. It never touches
Mongo / Voyage / Anthropic / Gemini directly.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sse_starlette.sse import EventSourceResponse

import fixtures
from eval.honesty import lint_source, run_honesty_lint
from eval.scoring import headline
from web.gold import add_gold_item, gold_provenance, load_gold_result, recompute_gold_result
from web.lineage import mock_cluster_lineage, resolve_cluster_lineage
from web.live_claims import LIVE, pool_with_live
from web.mock_stream import mock_eval_stream
from web.sse import sse_events
from web.state import RUBRIC
from web.streams import resolve_eval_stream, use_mock
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


def _value_strip_ctx() -> dict:
    """The three health tiles: rubric size (the rooted seed + grown family checks
    + gate-ADMITTED owner requirements — unverified ones only watch), failure-family
    coverage, and the gold receipt headline."""
    admitted = sum(1 for r in RUBRIC.requirements() if r["gated"] is True)
    return {
        "maturity": RUBRIC.maturity(),
        "n_checks": len(RUBRIC.checks()) + 1 + admitted,
        "gold_result": load_gold_result(),
    }


def _goldkey_ctx() -> dict:
    """Answer-key manager context: the on-disk gold set split by provenance.
    The receipt panel (_gold.html) gets the same split, so a stored frozen-set
    receipt can say when owner-added items are NOT part of it."""
    prov = gold_provenance()
    return {"owner_gold": prov["owner"], "n_frozen_gold": len(prov["frozen"])}


@router.post("/gold/add", response_class=HTMLResponse)
async def gold_add(request: Request) -> HTMLResponse:
    """Owner adds ONE labeled gold example — their labels, not just their rules.

    Rail nuance: only /loop is barred from gold; /web writes it on the owner's
    behalf, confined to eval/gold/ with a path-safe id. Copy-verify discipline:
    the ✓ card renders only after web.gold read the item back intact; a refused
    id, bad label or failed verify is reported in the panel — never swallowed,
    never a partial write left behind.
    """
    form = await request.form()
    ctx: dict = {"request": request}
    try:
        ctx["gold_added"] = add_gold_item(
            question=(form.get("question") or ""),
            claim=(form.get("claim") or ""),
            supporting_quote=(form.get("supporting_quote") or ""),
            category=(form.get("category") or "clean").strip(),
            claim_type=(form.get("claim_type") or "judgment").strip(),
            expected_verdict=(form.get("expected_verdict") or "").strip(),
            gold_id=(form.get("gold_id") or "").strip() or None,
        )
    except Exception as exc:  # noqa: BLE001 — a refused/failed add is shown, not swallowed
        ctx["gold_add_error"] = str(exc)
    ctx.update(_goldkey_ctx())  # re-list AFTER the write attempt — what's on disk now
    return templates.TemplateResponse("_goldkey.html", ctx)


# ── "try to cheat it" station ────────────────────────────────────────────────
# Canned cheat-attempt snippets, linted AS TEXT through the SAME eval.honesty
# functions CI runs — never written anywhere. They live in /web on purpose:
# /web may name gold (verification side); /loop source never may.
_CANNED_CHEATS = {
    "import-gold": {
        "label": "import the gold loader",
        "code": "# loop/grower.py — tune the new check against the answer key\n"
                "from eval.scoring import load_gold\n\nGOLD = load_gold()",
    },
    "read-gold-file": {
        "label": "open a gold file directly",
        "code": "# loop/checker.py — skip the import, just read the file\n"
                "import json\n\n"
                'with open("eval/gold/g-clean-breach-notification.json") as f:\n'
                "    answers = json.load(f)",
    },
    "comment-leak": {
        "label": "hide it in a comment",
        "code": "# loop/pruner.py\n"
                "# TODO(dev): peek at eval/gold before pruning, just this once\n"
                "RUBRIC_MIN = 3",
    },
    "innocent": {
        "label": "innocent look-alike (passes)",
        "code": "# loop/engine.py — names that merely CONTAIN 'eval' are fine\n"
                "from loop.engine import eval_stream\n\nhealth = evaluate(eval_stream)",
    },
}


def _cheat_ctx() -> dict:
    """The station's context: the REAL CI lint, run against this box's /loop
    source right now (a keyless static scan — cheap enough for page load, and
    it keeps 'running now' literally true), plus the canned example snippets."""
    return {"honesty_lint": run_honesty_lint(), "canned_cheats": _CANNED_CHEATS}


@router.post("/cheat", response_class=HTMLResponse)
async def cheat(request: Request) -> HTMLResponse:
    """Lint a would-be /loop snippet AS TEXT through the real honesty checker.

    Same eval.honesty functions the CI gate runs, so the verdict is always the
    real lint outcome — never staged. The snippet is never written to disk and
    never executed: a lint, not a sandbox.
    """
    form = await request.form()
    canned = _CANNED_CHEATS.get((form.get("canned") or "").strip())
    snippet = canned["code"] if canned else (form.get("snippet") or "").strip()
    if not snippet:  # empty box, no canned pick → no-op (mirrors /teach)
        return HTMLResponse("")
    return templates.TemplateResponse(
        "_cheat_result.html",
        {"request": request, "snippet": snippet, "hits": lint_source(snippet)},
    )


@router.get("/fragment/value-strip", response_class=HTMLResponse)
async def value_strip(request: Request) -> HTMLResponse:
    """The health tiles, refreshed on the same `grow` event as the rubric panel."""
    return templates.TemplateResponse(
        "_valuestrip.html", {"request": request, **_value_strip_ctx()}
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    # merged pool: the board AND the baseline n must come from the SAME pool the
    # score stream uses (pool_with_live), or they diverge after a refresh.
    questions = pool_with_live()
    claims = [_claim_from_fixture(q) for q in questions]
    # One real mode probe drives both the Verify affordance and the header mode
    # chip — the chip must state the box's TRUE runtime mode, never a hardcoded one.
    mock_mode = use_mock()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "claims": claims,
            "score": _baseline_score(len(claims)),
            "branches": RUBRIC.branches(),
            "checks": RUBRIC.checks(),
            "requirements": RUBRIC.requirements(),
            # the live recompute needs the real seams (rubric store + model);
            # a keyless/mock box keeps the precomputed receipt, honestly labeled.
            "can_verify": not mock_mode,
            "mock_mode": mock_mode,
            **_value_strip_ctx(),  # maturity + n_checks + gold_result (one source)
            **_cheat_ctx(),  # the real honesty-gate lint result + canned snippets
            **_goldkey_ctx(),  # answer-key manager: owner-added vs frozen gold split
        },
    )


async def _teach_live(standard: str) -> dict:
    """Keyed path: real mint from the owner's words + the REAL is_general gate.
    Persists to the rubric store only when the gate admits it."""
    import store
    import loop
    from loop.grower import _failure_to_output, _generality_async

    db = store.get_db()
    check = await asyncio.to_thread(loop.mint_check_from_standard, standard)
    known_good = await store.known_good_sample(db)
    cluster = await store.nearest_failures(check.negative_example or check.property, db)
    pos, neg = await _generality_async(check, known_good, [_failure_to_output(f) for f in cluster])
    gated = pos == len(known_good) and neg >= 2
    if gated:
        await store.upsert_check(check, db)
    return {"check": check, "gated": gated, "caught": neg, "n_known_good": len(known_good)}


@router.post("/teach", response_class=HTMLResponse)
async def teach(request: Request) -> HTMLResponse:
    """Owner intake: a plain-English standard → a check, gate verdict ALWAYS real.

    Keyless/mock boxes record the requirement UNVERIFIED (the generality gate
    needs a live model + failure store) — never a fake ADMITTED. Seam failures
    on a keyed box degrade the same way, with the error surfaced.
    """
    form = await request.form()
    standard = (form.get("standard") or "").strip()
    if not standard:
        return HTMLResponse("")
    ctx: dict = {"request": request, "standard": standard}
    if use_mock():
        RUBRIC.record_requirement(standard, standard, gated=None, source="typed")
        ctx["mode"] = "unverified"
    else:
        try:
            res = await _teach_live(standard)
            RUBRIC.record_requirement(standard, res["check"].property,
                                      gated=res["gated"], source="live")
            ctx.update(mode="live", **res)
        except Exception as exc:  # noqa: BLE001 — record unverified, say why
            RUBRIC.record_requirement(standard, standard, gated=None, source="typed")
            ctx.update(mode="unverified", error=str(exc))
    resp = templates.TemplateResponse("_teach.html", ctx)
    resp.headers["HX-Trigger"] = "grow"  # rubric + value strip refresh on the same event
    return resp


@router.post("/gold/verify", response_class=HTMLResponse)
async def gold_verify(request: Request) -> HTMLResponse:
    """Recompute the frozen-gold receipt LIVE over the current rubric store.

    Explicit and user-triggered by design (15 held-out items × every check, one
    model call each — never on page load). On a mock/keyless box, or if the live
    rescore fails, the stored receipt is returned with the failure surfaced —
    a broken recompute must never masquerade as a fresh one.
    """
    # _gold.html hosts the "try to cheat it" station, so every render of the
    # panel re-runs the real lint (keyless, cheap) — the verdict never goes stale.
    # It also needs the gold provenance split, so a stored frozen-set receipt can
    # say when owner-added items are not part of it.
    ctx: dict = {"request": request, "can_verify": not use_mock(),
                 **_cheat_ctx(), **_goldkey_ctx()}
    if not ctx["can_verify"]:
        ctx["gold_result"] = load_gold_result()
        return templates.TemplateResponse("_gold.html", ctx)
    try:
        ctx["gold_result"] = await recompute_gold_result()
    except Exception as exc:  # noqa: BLE001 — degrade to the stored receipt, visibly
        ctx["gold_result"] = load_gold_result()
        ctx["verify_error"] = str(exc)
    return templates.TemplateResponse("_gold.html", ctx)


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
    try:  # loop-side display cache (per-claim grow reports) resets with the demo
        import loop

        loop.reset_grow_reports()
    except Exception:  # noqa: BLE001 — /web must reset even if /loop can't import
        pass
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
        {"request": request, "checks": RUBRIC.checks(), "maturity": RUBRIC.maturity(),
         "requirements": RUBRIC.requirements()},
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
