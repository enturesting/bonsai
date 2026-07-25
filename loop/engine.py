"""Engine — the SSE generator /web iterates, plus its support functions.

`eval_stream(claim_id)` is the single async generator the UI consumes. It drives
the rule-rewrite stream and the re-check, and emits the §2 lifecycle of semantic
dicts: pill(yellow) → chunk×N → pill(green|red) → score → done (+ optional error).

The "score" carries the honest numbers — green counts over the WORKING pool plus a
Wilson CI — never a bare %. Wilson is the closed form (no statsmodels, no /eval
import: the honesty rail forbids /loop touching /eval or gold).

`_context(claim_id)` is the resolution seam to /fixtures (the AUT) and /store (the
rubric), built in parallel terminals; it's the one place tests patch to drive the
generator offline.
"""
from __future__ import annotations

import asyncio
import math

import fixtures
import store

from store.models import AUTOutput, Check

from . import llm
from .checker import run_check
from .grower import GrowReport, grow_report

REWRITE_SYS = (
    "You are improving an eval rubric check so it reliably catches a class of "
    "unsupported claims. Rewrite the check's property as ONE precise, testable "
    "sentence phrased over ROLES/TYPES (not the literal strings of this example). "
    "Output only the rewritten property sentence — no preamble."
)


# ── Wilson 95% binomial CI (closed form; correct at small n / near 0,1) ──────
def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = max(0.0, (centre - margin) / d)  # clamp float noise at the 0/1 edges
    hi = min(1.0, (centre + margin) / d)
    return (lo, hi)


# ── resolution seam (patched in tests; real path uses /fixtures + /store) ────
def _pick_check(checks: list[Check]) -> Check:
    for c in checks:
        if c.id == "numeric-cites-source":
            return c
    if checks:
        return checks[0]
    return Check(
        id="numeric-cites-source",
        property="Every numeric claim has a verbatim supporting quote in a cited source.",
        rationale="numbers without support mislead",
        positive_example="Revenue rose, per the filing.",
        negative_example="Revenue was 4.2B (no quote).",
        overfit_risk="might over-match formatted dates",
    )


async def _context(claim_id: str) -> tuple[AUTOutput, Check, list[AUTOutput]]:
    """Resolve (this claim's AUT output, the relevant check, the working pool).

    The claim_id maps to a working-pool fixture id (the unit /web runs the AUT on).
    Working pool ONLY — never the gold set.
    """
    questions = fixtures.load_fixture_questions()
    # Run the AUT over the whole working pool CONCURRENTLY — each run_agent is a
    # blocking model call, so gather-over-threads turns ~9 sequential calls into one
    # wall-clock pass. The clicked claim's output is its own pool entry (resolved
    # once and reused), keeping the pill and the after-count on one generation.
    pool = (
        list(await asyncio.gather(*(asyncio.to_thread(fixtures.run_agent, q) for q in questions)))
        if questions else []
    )
    idx = next((i for i, q in enumerate(questions) if q.get("id") == claim_id), 0)
    output = pool[idx] if pool else fixtures.run_agent(questions[0] if questions else {})
    db = store.get_db()
    check = _pick_check(await store.get_checks(db))
    return output, check, pool


def _apply_rule(check: Check, rule_text: str) -> Check:
    rule = (rule_text or "").strip()
    return check.model_copy(update={"property": rule}) if rule else check


def _green_count(check: Check, pool: list[AUTOutput]) -> int:
    return sum(1 for o in pool if run_check(check, o.claim, o).passed)


async def _green_count_async(check: Check, pool: list[AUTOutput]) -> int:
    """Concurrent green-count: each run_check is a blocking model call, so run them
    together (one wall-clock pass) instead of N sequential calls."""
    verdicts = await asyncio.gather(*(asyncio.to_thread(run_check, check, o.claim, o) for o in pool))
    return sum(1 for v in verdicts if v.passed)


async def _green_count_rubric_async(rubric: list[Check], pool: list[AUTOutput]) -> int:
    """Green-count under a MULTI-check rubric: an item is green only when EVERY
    check passes it (eval.scoring's rubric semantics — additive checks can only
    tighten). All (item × check) verdicts run concurrently on threads."""
    grid = await asyncio.gather(
        *(asyncio.to_thread(run_check, c, o.claim, o) for o in pool for c in rubric)
    )
    k = len(rubric)
    return sum(1 for i in range(len(pool)) if all(v.passed for v in grid[i * k : (i + 1) * k]))


# The most recent grow report per claim. The /tree lineage route reuses the
# click's actual mint story instead of re-running grow (which would mint and
# possibly persist a SECOND check per improve). Process-wide display cache,
# mirroring /web's RUBRIC pattern; keys are the finite fixture pool ids.
_LAST_GROW: dict[str, GrowReport] = {}


def last_grow_report(claim_id: str) -> GrowReport | None:
    """The GrowReport eval_stream produced for this claim's most recent improve."""
    return _LAST_GROW.get(claim_id)


def reset_grow_reports() -> None:
    """Clear the per-claim grow-report cache (demo reset)."""
    _LAST_GROW.clear()


async def _grow_from_miss(output: AUTOutput, check: Check) -> GrowReport:
    """The REAL grow path for a confirmed miss: cluster the failure store around
    this claim → mint one general check → is_general gate → persist if gated.

    Any seam failure (Atlas/Voyage unreachable, model error) degrades to a report
    with `error` set: the improve stream must never die because minting couldn't
    reach the failure store, and the miss must be reported, not hidden.
    """
    try:
        db = store.get_db()
        # Cluster around the claim that just slipped through (grow seeds off
        # negative_example) so the minted check generalizes THIS failure's class.
        seed = check.model_copy(update={"negative_example": output.claim or check.negative_example})
        return await grow_report(seed, db)
    except Exception as exc:  # noqa: BLE001 — degrade honestly, never kill the stream
        return GrowReport(error=str(exc))


# ── frozen public surface ────────────────────────────────────────────────────
async def _rewrite_tokens(output: AUTOutput, check: Check):
    """Stream the Opus rule-rewrite over an ALREADY-resolved (output, check), so
    eval_stream can drive the rewrite without re-resolving the AUT context."""
    user = (
        f"CURRENT CHECK PROPERTY:\n{check.property}\n\n"
        f"A claim that slipped through:\nCLAIM: {output.claim}\n"
        f"SOURCES:\n{output.sources_text}\n\n"
        "Rewrite the property so this class of unsupported claim is caught."
    )
    for token in llm.opus_stream_text(system=REWRITE_SYS, user=user):
        yield token
        await asyncio.sleep(0)  # yield control to the event loop between tokens


async def rewrite_rule_stream(claim_id: str):
    """Stream the Opus rule-rewrite token-by-token (adaptive thinking + effort)."""
    output, check, _ = await _context(claim_id)
    async for token in _rewrite_tokens(output, check):
        yield token


async def run_checker(claim_id: str, rule_text: str) -> bool:
    """Re-run the checker on this claim with the rewritten rule applied."""
    output, check, _ = await _context(claim_id)
    return run_check(_apply_rule(check, rule_text), output.claim, output).passed


def _pill(check_id: str, color: str, label: str) -> dict:
    return {"event": "pill", "data": {"color": color, "check_id": check_id, "label": label}}


async def eval_stream(claim_id: str):
    """The single generator /web iterates. Emits the §2 lifecycle of semantic dicts.

    Resolves the AUT context ONCE and reuses (output, check, pool) for the before
    count, the rule rewrite, the re-check, and the after count — so the green/red
    pill and the score's after-count derive from the same generation (coherent
    honesty numbers) and one click costs one pool pass, not three.

    A RED re-check (confirmed failure) also drives the REAL grow path —
    cluster→mint→is_general→persist via _grow_from_miss — and the after-count is
    taken over the rubric WITH the minted check, so the score reflects the rubric
    as it now actually stands. The mint story rides the score event's additive
    `mint` field (None when the click cleared a false positive: nothing to mint).
    """
    try:
        output, check, pool = await _context(claim_id)

        yield _pill(claim_id, "yellow", "CHECKING…")
        await asyncio.sleep(0)  # flush the yellow pill immediately

        n = len(pool)
        before = await _green_count_async(check, pool)

        rule_text = ""
        async for token in _rewrite_tokens(output, check):
            rule_text += token
            yield {"event": "chunk", "data": {"token": token}}

        new_check = _apply_rule(check, rule_text)
        passed = (await asyncio.to_thread(run_check, new_check, output.claim, output)).passed
        # The pill judges the ANSWER (supported or caught) — never the harness.
        yield _pill(claim_id, "green" if passed else "red", "SUPPORTED" if passed else "CAUGHT")

        # Confirmed failure → the real grow path (cluster→mint→gate→persist).
        # A GREEN re-check cleared a false positive: no failure to generalize.
        if not passed:
            report = await _grow_from_miss(output, new_check)
            _LAST_GROW[claim_id] = report  # the lineage route shows THIS mint
        else:
            report = GrowReport()
        rubric = [new_check] + ([report.minted] if report.minted else [])
        after = await _green_count_rubric_async(rubric, pool)
        lo, hi = _wilson(after, n)
        yield {
            "event": "score",
            "data": {
                "passed": passed,
                "before": before,
                "after": after,
                "n": n,
                "ci": [lo, hi],
                # additive field (CONTRACTS §2, 2026-07-02): the mint story for a
                # confirmed failure; None when there was nothing to mint from.
                "mint": report.as_event_data() if not passed else None,
            },
        }
        yield {"event": "done", "data": {}}
    except asyncio.CancelledError:
        raise  # client disconnected mid-stream; let sse-starlette close cleanly
    except Exception as exc:  # noqa: BLE001 — surface any failure to the UI, then close
        # Flip the pill to a visible failed state (never leave it stuck yellow),
        # then surface the message and terminate the stream.
        yield _pill(claim_id, "red", "ERROR")
        yield {"event": "error", "data": {"message": str(exc)}}
        yield {"event": "done", "data": {}}
