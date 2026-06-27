"""Two-stage checker: deterministic → Haiku → Opus escalation.

A Check is a predicate over ``(check, claim, output)`` where ``output`` is an
``AUTOutput``. ``deterministic`` decides cheaply when it can (regex/parse/lookup),
``haiku_check`` is the fast LLM judge, and ``opus_check`` is the rigorous
adjudicator we escalate to ~10–20% of the time. See CONTRACTS §3 /loop and
build-cheat-sheet §2b.
"""
from __future__ import annotations

import re

from store.models import AUTOutput, Check, Verdict

from .llm import HAIKU, OPUS, haiku_parse, opus_parse

CONF_FLOOR = 0.75

_NUM = re.compile(r"\d[\d,]*\.?\d*")


def deterministic(check: Check, claim: str, output: AUTOutput) -> bool | None:
    """Regex/parse/lookup verdict, or None when not decidable without an LLM."""
    if check.id == "numeric-cites-source":
        nums = _NUM.findall(claim)
        if not nums:
            return True  # no numeric assertion → nothing to support
        sources_text = output.sources_text
        return all(n in sources_text for n in nums)
    return None


def haiku_check(check: Check, claim: str, output: AUTOutput) -> Verdict:
    """Fast Haiku judge with a self-reported confidence. Plain call."""
    system = (
        "Apply this check to the claim and rate your confidence (0..1).\n"
        f"CHECK: {check.property}"
    )
    user = f"CLAIM: {claim}\nANSWER: {output.output}\nSOURCES:\n{output.sources_text}"
    return haiku_parse(system=system, user=user, schema=Verdict)


def opus_check(check: Check, claim: str, output: AUTOutput) -> Verdict:
    """Rigorous Opus adjudication (adaptive thinking + high effort)."""
    system = (
        "Adjudicate this check rigorously. Quote the supporting source text if the "
        "claim is supported; explain the gap if not.\n"
        f"CHECK: {check.property}"
    )
    user = f"CLAIM: {claim}\nANSWER: {output.output}\nSOURCES:\n{output.sources_text}"
    return opus_parse(system=system, user=user, schema=Verdict)


def run_check(check: Check, claim: str, output: AUTOutput) -> Verdict:
    """det → Haiku → Opus. Escalate on det/Haiku disagreement, or Haiku unsure
    with no deterministic anchor. Deterministic result wins when present and
    agreeing; otherwise the Haiku verdict stands."""
    d = deterministic(check, claim, output)
    h = haiku_check(check, claim, output)
    hard = (d is None and h.confidence < CONF_FLOOR) or (d is not None and d != h.passed)
    if hard:
        return opus_check(check, claim, output)
    passed = d if d is not None else h.passed
    return Verdict(passed=passed, confidence=h.confidence, reason=h.reason)
