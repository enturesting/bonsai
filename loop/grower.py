"""Grower + check-minting — turn a caught failure into a GENERAL reusable check.

Mint abstracts ONE failure into a property that catches the whole CLASS, then the
``is_general`` gate verifies (rather than trusts) generality: the check must still
pass every held-back known-good item AND catch ≥2 sibling failures. ``grow`` always
mints from the lowest-signal cluster (where the rubric is blindest), one mint per
cycle, gated. See CONTRACTS §3 /loop and build-cheat-sheet §2a.

The /store seam is referenced as ``store.X`` at call-time (it's built in another
terminal); /loop never reaches Mongo/Voyage directly.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass

import store

from store.models import AUTOutput, Check, Failure

from .checker import run_check
from .llm import opus_parse

MINT_SYS = """You convert a single caught failure into ONE general, reusable check.

A check is GENERAL when:
- It tests a PROPERTY/INVARIANT (a type, a role, a relationship), not the literal
  strings in this one failure. "Numeric claims cite a source row" — general.
  "The revenue figure must be 4.2B" — overfit paraphrase, reject.
- It would PASS on unrelated-but-correct outputs (write positive_example to prove it).
- It would FAIL on the motivating failure AND on siblings you can imagine.

Reject your own draft if it merely restates this failure. Generalize one level:
ask "what KIND of mistake is this?" and test that kind.
Output the check. Keep `property` to one testable sentence."""


def mint_check(failure: Failure) -> Check:
    """Opus turns one failure into a general Check (output_format=Check)."""
    user = (
        f"INPUT:\n{failure.input}\n\nCLAIM:\n{failure.claim}\n\n"
        f"EXPECTED:\n{failure.expected}\n\nACTUAL (wrong):\n{failure.actual}\n\n"
        f"WHY WRONG:\n{failure.why}"
    )
    return opus_parse(system=MINT_SYS, user=user, schema=Check, max_tokens=2000)


def _slug(output: AUTOutput, why: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", why.lower()).strip("-")[:32] or "miss"
    h = hashlib.sha1((output.input + output.claim).encode()).hexdigest()[:6]
    return f"{base}-{h}"


def mint_check_from_miss(output: AUTOutput, why: str) -> Check:
    """Build a Failure from a missed (wrongly-green) output, then mint a check."""
    failure = Failure(
        id=_slug(output, why),
        input=output.input,
        claim=output.claim,
        expected="A claim with a verbatim supporting quote in a cited source.",
        actual=output.output,
        why=why,
    )
    return mint_check(failure)


STANDARD_SYS = """You convert a domain owner's plain-English standard into ONE general,
reusable check. The same GENERAL bar as minting from a failure applies: test a
PROPERTY/INVARIANT over roles/types, not the literal strings of the owner's sentence;
write positive_example to prove it passes unrelated-but-correct outputs and
negative_example as a concrete violation. Output the check; keep `property` to one
testable sentence."""


def mint_check_from_standard(text: str) -> Check:
    """An owner's plain-English requirement → a general Check (the owner-intake seam).
    The id is derived from the owner's words (stable, auditable) — never model-chosen."""
    check = opus_parse(system=STANDARD_SYS, user=f"OWNER'S STANDARD:\n{text}", schema=Check, max_tokens=2000)
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "standard"
    return check.model_copy(update={"id": f"std-{slug}"})


def is_general(check: Check, known_good: list[AUTOutput], cluster_failures: list[AUTOutput]) -> bool:
    """Verify generality, don't trust self-report: passes ALL known-good AND
    catches ≥2 cluster failures."""
    pos = sum(1 for g in known_good if run_check(check, g.claim, g).passed)
    neg = sum(1 for f in cluster_failures if not run_check(check, f.claim, f).passed)
    return pos == len(known_good) and neg >= 2


async def _generality_async(
    check: Check, known_good: list[AUTOutput], cluster_failures: list[AUTOutput]
) -> tuple[int, int]:
    """(passed known-good count, caught sibling count) — the is_general inputs,
    with each blocking run_check on its own thread (one wall-clock pass, not
    len(known_good)+len(cluster) sequential model calls)."""
    pos_v, neg_v = await asyncio.gather(
        asyncio.gather(*(asyncio.to_thread(run_check, check, g.claim, g) for g in known_good)),
        asyncio.gather(*(asyncio.to_thread(run_check, check, f.claim, f) for f in cluster_failures)),
    )
    pos = sum(1 for v in pos_v if v.passed)
    neg = sum(1 for v in neg_v if not v.passed)
    return pos, neg


@dataclass
class GrowReport:
    """The full cluster→mint→gate story of one grow attempt, display-friendly.

    `minted` is the check that actually entered the rubric (None unless the gate
    passed); `candidate` is what was minted even when the gate rejected it, so the
    UI can show WHY nothing was added. `error` records a seam failure (Atlas or the
    model unreachable) — surfaced honestly, never silently swallowed.
    """

    minted: Check | None = None
    candidate: Check | None = None
    gated: bool = False
    cluster_size: int = 0
    caught_siblings: int = 0
    n_known_good: int | None = None
    error: str | None = None

    def as_event_data(self) -> dict:
        """The additive `mint` payload for the SSE score event (plain JSON dict)."""
        c = self.candidate
        return {
            "attempted": c is not None or self.error is not None,
            "gated": self.gated,
            "id": c.id if c else None,
            "property": c.property if c else None,
            "cluster_size": self.cluster_size,
            "caught_siblings": self.caught_siblings,
            "n_known_good": self.n_known_good,
            "error": self.error,
            "source": "loop",  # the REAL grow path (the mock mirror says "mock")
        }


async def grow_report(worst_check: Check, db) -> GrowReport:
    """Cluster the blindest failures → mint one general check → gate it, reporting
    every step. Persists the minted check to the rubric store ONLY when the
    is_general gate passes (pos == all known-good AND ≥2 siblings caught)."""
    cluster = await store.nearest_failures(_seed_text(worst_check), db)
    if not cluster:
        return GrowReport()
    candidate = await asyncio.to_thread(mint_check, cluster[0])  # mint generalizes the class
    known_good = await store.known_good_sample(db)
    cluster_outputs = [_failure_to_output(f) for f in cluster]
    pos, neg = await _generality_async(candidate, known_good, cluster_outputs)
    gated = pos == len(known_good) and neg >= 2
    if gated:
        await store.upsert_check(candidate, db)
    return GrowReport(
        minted=candidate if gated else None,
        candidate=candidate,
        gated=gated,
        cluster_size=len(cluster),
        caught_siblings=neg,
        n_known_good=len(known_good),
    )


def _seed_text(worst_check: Check) -> str:
    """Text to retrieve the blind-spot cluster — the motivating failure works best."""
    return worst_check.negative_example or worst_check.property


def _failure_to_output(f: Failure) -> AUTOutput:
    """An AUTOutput view of a stored failure for re-checking (no sources → a numeric
    claim is deterministically unsupported, which is the point)."""
    return AUTOutput(input=f.input, claim=f.claim, output=f.actual, sources=[])


async def grow(worst_check: Check, db) -> Check | None:
    """Cluster the blindest failures → mint one general check → gate it. Returns the
    new check (persisted to the rubric store) or None if it's overfit noise.
    (Frozen public surface — thin wrapper over grow_report so the eval_stream
    wiring and this call can never disagree about what got minted.)"""
    return (await grow_report(worst_check, db)).minted
