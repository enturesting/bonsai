"""web/lineage.py — make the Atlas $vectorSearch clustering VISIBLE.

For a grown check this assembles the lineage the grower walked to mint it:

    seed failure  →  the N nearest failures Atlas $vectorSearch returned
                  →  the minted general check + its is_general verdict

One interface, two backends (the web.streams Auto policy, reused):
  * real path — pulls the cluster from ``store.nearest_failures`` and the minted
    check from ``loop.grow`` (the frozen seams; /web never touches Mongo/Voyage
    /Anthropic directly — those imports are lazy, inside the functions).
  * mock path — rebuilds a faithful lineage from the offline fixture pool so the
    money-shot demos with no live Atlas. Forced in tests via WEB_MOCK_STREAM=1,
    exactly like the scripted mock_eval_stream.

Both return the SAME dict shape so ``_lineage.html`` renders either blind:

    {
      "claim_id": str,
      "seed":    {"id", "claim", "why"},
      "cluster": [{"rank", "id", "why", "similarity"|None}, ...],  # similarity order
      "k":       int,                                              # cluster size
      "minted":  {"id", "property"},
      "verdict": {"is_general", "passed_known_good", "caught_siblings", "n_known_good"},
      "source":  "atlas" | "mock",
    }
"""
from __future__ import annotations

import fixtures
from web.streams import use_mock

# How many nearest failures to surface (the real grow() default is wider).
N_NEAREST = 8

# The general INVARIANT minted per failure class — phrased over roles/types, not
# the literal strings of any one failure (mirrors loop.grower's MINT contract).
_PROPERTY_BY_CATEGORY = {
    "unsupported-numeric": "Every numeric claim must cite a source whose text contains that figure (within rounding).",
    "fabricated-quote": "Every quoted span must appear verbatim in the text of a cited source.",
    "stale-wrong-citation": "Each citation must point to a source whose text actually supports the claim.",
    "single-source-overcite": "A source may be cited only for the claims its text genuinely supports.",
    "vague-not-checkable": "A claim must be specific enough to verify against a cited source span.",
}
_DEFAULT_PROPERTY = "Each claim must be backed by a verbatim span in a cited source."


def _resolve(claim_id: str, questions: list) -> dict:
    return next(
        (q for q in questions if q.get("id") == claim_id),
        questions[0] if questions else {},
    )


def _why(q: dict) -> str:
    return q.get("why") or q.get("category") or "uncategorised failure"


def _seed_id(fixture_id: str) -> str:
    # Matches fixtures.seed_failures' id scheme so the lineage names real Atlas docs.
    return f"seed-{fixture_id}"


def _property_for(q: dict) -> str:
    return _PROPERTY_BY_CATEGORY.get(q.get("category", ""), _DEFAULT_PROPERTY)


def _minted_id(q: dict) -> str:
    return f"minted-{q.get('category') or 'general'}"


def _order_by_similarity(seed_q: dict, failures: list) -> list:
    """Deterministic stand-in for $vectorSearch ranking: the seed's own failure is
    nearest, then same-class siblings, then the rest — each with a descending
    synthetic cosine score so the demo reads like a real similarity list."""
    cat = seed_q.get("category")
    seed_fid = seed_q.get("id")

    def tier(f: dict) -> int:
        if f.get("id") == seed_fid:
            return 0
        if f.get("category") == cat:
            return 1
        return 2

    ordered = sorted(failures, key=lambda f: (tier(f), f.get("id", "")))
    out = []
    sim = 0.98
    for f in ordered:
        out.append((f, round(sim, 2)))
        sim = max(0.50, sim - 0.07)
    return out


def _verdict(*, caught_siblings: int, n_known_good: int, passed_known_good: bool) -> dict:
    """The is_general gate, made legible: passes ALL held-back known-good AND
    catches ≥2 sibling failures (loop.grower.is_general's exact rule)."""
    return {
        "is_general": passed_known_good and caught_siblings >= 2,
        "passed_known_good": passed_known_good,
        "caught_siblings": caught_siblings,
        "n_known_good": n_known_good,
    }


async def mock_cluster_lineage(claim_id: str) -> dict:
    """Rebuild a faithful lineage from the offline fixture pool (+ live claims, no Atlas)."""
    from web.live_claims import pool_with_live

    questions = pool_with_live()
    q = _resolve(claim_id, questions)
    # A clean seed has no failure to cluster — short-circuit to a "nothing to mint"
    # card. The failure filter below is seed-INDEPENDENT, so a clean seed would
    # otherwise get a full sibling cluster + is_general=True, rendering a confident
    # "minted a general check, caught N siblings" panel over a claim the audience
    # just watched flip GREEN — the inverse of the "cleared a false positive" story.
    if q.get("category") == "clean":
        return {
            "claim_id": claim_id,
            "source": "mock",
            "clean": True,
            "seed": {
                "id": _seed_id(q.get("id", claim_id)),
                "claim": (q.get("mock") or {}).get("claim", ""),
                "why": "well-supported",
            },
            "cluster": [],
            "k": 0,
            "minted": None,
            "verdict": {"is_general": False, "passed_known_good": True,
                        "caught_siblings": 0, "n_known_good": None},
        }
    failures = [x for x in questions if x.get("category") != "clean"]
    known_good = [x for x in questions if x.get("category") == "clean"]

    seed = {
        "id": _seed_id(q.get("id", claim_id)),
        "claim": (q.get("mock") or {}).get("claim", ""),
        "why": _why(q),
    }
    cluster = [
        {"rank": rank, "id": _seed_id(f.get("id", "")), "why": _why(f), "similarity": sim}
        for rank, (f, sim) in enumerate(_order_by_similarity(q, failures), start=1)
    ]
    # Offline the minted check IS the class invariant, so it catches every
    # clustered failure and still passes the held-back clean items.
    verdict = _verdict(
        caught_siblings=len(cluster),
        n_known_good=len(known_good),
        passed_known_good=True,
    )
    return {
        "claim_id": claim_id,
        "seed": seed,
        "cluster": cluster,
        "k": len(cluster),
        "minted": {"id": _minted_id(q), "property": _property_for(q)},
        "verdict": verdict,
        "source": "mock",
    }


def _seed_check(q: dict, seed_text: str):
    """A Check to seed loop.grow from — grow() clusters off its negative_example."""
    from store.models import Check

    return Check(
        id=f"seed-{q.get('category') or 'general'}",
        property=_property_for(q),
        rationale="The rubric's blind spot — grow a general check from this cluster.",
        positive_example="A claim with a verbatim supporting quote in a cited source.",
        negative_example=seed_text,
        overfit_risk="Could restate one failure instead of testing the class.",
    )


async def real_cluster_lineage(claim_id: str) -> dict:
    """Pull the lineage from the live seams: store.nearest_failures + loop.grow.

    Imports are lazy so /web stays importable (and within its boundary) when
    Mongo/Anthropic aren't present — web.streams.use_mock routes here only when a
    key is configured.
    """
    import store
    import loop

    db = store.get_db()
    questions = fixtures.load_fixture_questions()
    q = _resolve(claim_id, questions)
    seed_text = (q.get("mock") or {}).get("claim") or q.get("question") or claim_id

    scored = await store.nearest_failures_scored(seed_text, db, limit=N_NEAREST)
    if not scored:
        # Atlas has no stored failures yet (the failures collection is unseeded) —
        # fall back to the offline cluster so clicking a branch is never empty
        # during a live run. Labeled source="mock" (honest about the data).
        return await mock_cluster_lineage(claim_id)
    minted_check = await loop.grow(_seed_check(q, seed_text), db)

    cluster = [
        {"rank": i, "id": f.id, "why": f.why or "failure", "similarity": sim}
        for i, (f, sim) in enumerate(scored, start=1)
    ]
    is_general = minted_check is not None
    minted = {
        "id": minted_check.id if minted_check else _minted_id(q),
        "property": minted_check.property if minted_check else _property_for(q),
    }
    return {
        "claim_id": claim_id,
        "seed": {"id": _seed_id(q.get("id", claim_id)), "claim": seed_text, "why": _why(q)},
        "cluster": cluster,
        "k": len(cluster),
        "minted": minted,
        # grow() already ran the is_general gate; a returned Check means it passed.
        "verdict": {
            "is_general": is_general,
            "passed_known_good": is_general,
            "caught_siblings": len(cluster),
            "n_known_good": None,
        },
        "source": "atlas",
    }


def resolve_cluster_lineage():
    """Return the lineage builder to drive: (claim_id) -> awaitable[dict]."""
    if use_mock():
        return mock_cluster_lineage
    return real_cluster_lineage
