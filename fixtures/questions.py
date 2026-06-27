"""
fixtures/questions.py — load the DEV working-pool fixture questions.

These are the *development* fixtures (`fixtures/questions/*.json`) that /loop and
/web develop against. They are deliberately kept SEPARATE from the frozen gold set
(which lives under /eval/gold and is owned by the /eval terminal). Nothing here may
read or import the gold set.

Each fixture is a question + candidate sources, plus a deterministic `mock` script
the offline AUT replays (see fixtures/aut.py) and, for designed failures, an
`expected`/`why` diagnosis used to seed the initial failure pool.
"""
from __future__ import annotations

import json
from pathlib import Path

# The five citation-grounding failure classes this harness catches — named to match
# the gold set's `category_relevant`. Every failure fixture is tagged with exactly one
# of these; "clean" fixtures must pass.
FAILURE_CATEGORIES = (
    "unsupported-numeric",     # a number/stat in the claim has no verbatim supporting quote in the cited source
    "fabricated-quote",        # an attributed claim is not byte-recoverable from the cited source
    "stale-wrong-citation",    # a real source is cited, but it is the wrong one and does not support the claim
    "vague-not-checkable",     # the cited source supports only a hedged/narrower version of a stronger claim
    "single-source-overcite",  # one source is cited to carry many distinct claims it does not all support
)

QUESTIONS_DIR = Path(__file__).resolve().parent / "questions"


def load_fixture_questions() -> "list[dict]":
    """Load every DEV fixture from fixtures/questions/*.json, sorted by filename.

    Returns plain dicts (not Pydantic) — the fixture file format is a superset of the
    AUT input (it also carries the offline `mock` script and failure diagnosis).
    Source ids default to "S{n}" by position when a fixture omits them.
    """
    out: "list[dict]" = []
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            fixture = json.load(fh)
        fixture.setdefault("id", path.stem)
        _assign_source_ids(fixture)
        out.append(fixture)
    return out


def _assign_source_ids(fixture: dict) -> None:
    """Fill in missing Source ids as S1, S2, … by position (in place)."""
    for n, src in enumerate(fixture.get("sources", []), start=1):
        if not src.get("id"):
            src["id"] = f"S{n}"
