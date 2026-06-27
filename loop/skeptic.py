"""Skeptic — Opus adversarial pass that tries to REFUTE a green verdict.

A pass is the dangerous direction: a wrongly-green claim is an undetected failure.
The skeptic only fires on a PASS (a fail has nothing to refute) and re-checks it
adversarially with Opus, defaulting to refuted when the supporting quote is not
genuinely verbatim and sufficient.
"""
from __future__ import annotations

from store.models import AUTOutput, Verdict

from .llm import OPUS, opus_parse

SKEPTIC_SYS = (
    "You are an adversarial skeptic. A prior checker PASSED this claim. Your job is "
    "to REFUTE that pass: find any way the claim is not genuinely supported by a "
    "verbatim quote in the cited sources. Default to refuted (passed=false) unless "
    "the support is unambiguous and byte-recoverable. Return your verdict."
)


def skeptic(output: AUTOutput, verdict: Verdict) -> Verdict:
    if not verdict.passed:
        return verdict  # only passes need challenging
    user = (
        f"PRIOR VERDICT (passed): {verdict.reason}\n"
        f"CLAIM: {output.claim}\nANSWER: {output.output}\n"
        f"SOURCES:\n{output.sources_text}"
    )
    return opus_parse(system=SKEPTIC_SYS, user=user, schema=Verdict)
