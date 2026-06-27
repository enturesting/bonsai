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

import hashlib
import re

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


def is_general(check: Check, known_good: list[AUTOutput], cluster_failures: list[AUTOutput]) -> bool:
    """Verify generality, don't trust self-report: passes ALL known-good AND
    catches ≥2 cluster failures."""
    pos = sum(1 for g in known_good if run_check(check, g.claim, g).passed)
    neg = sum(1 for f in cluster_failures if not run_check(check, f.claim, f).passed)
    return pos == len(known_good) and neg >= 2


def _seed_text(worst_check: Check) -> str:
    """Text to retrieve the blind-spot cluster — the motivating failure works best."""
    return worst_check.negative_example or worst_check.property


def _failure_to_output(f: Failure) -> AUTOutput:
    """An AUTOutput view of a stored failure for re-checking (no sources → a numeric
    claim is deterministically unsupported, which is the point)."""
    return AUTOutput(input=f.input, claim=f.claim, output=f.actual, sources=[])


async def grow(worst_check: Check, db) -> Check | None:
    """Cluster the blindest failures → mint one general check → gate it. Returns the
    new check (persisted to the rubric store) or None if it's overfit noise."""
    cluster = await store.nearest_failures(_seed_text(worst_check), db)
    if not cluster:
        return None
    new_check = mint_check(cluster[0])  # representative; mint generalizes the class
    known_good = await store.known_good_sample(db)
    cluster_outputs = [_failure_to_output(f) for f in cluster]
    if is_general(new_check, known_good, cluster_outputs):
        await store.upsert_check(new_check, db)
        return new_check
    return None
