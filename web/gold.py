"""web/gold.py — the gold receipt + the owner's answer-key write path.

/web MAY touch gold: the honesty rail (CONTRACTS §3 /eval) forbids the LOOP — the
self-improving part — from ever seeing the answer key. Verification-side surfaces
(/eval itself, and this display layer) read it at scoring time, and the OWNER may
extend it from here: their labels, not just their rules. The rail bars the whole
eval/gold/ directory from /loop, not a filename list, so owner-added items are
held out exactly like the frozen ones.

Provenance stays explicit: frozen items (authored offline, frozen:true) are never
edited or overwritten here; owner adds land as g-owner-*.json with frozen:false +
provenance:"owner-added". Writes use copy-verify — the item is written, read back
off disk and compared; a mismatch removes the file and raises, so success is never
reported for a partial write.

The live recompute sits behind an explicit "Verify now" button, never page load:
it rescores every held-out gold item under the seed rubric AND the current stored
rubric (15 items × checks, one model call each), so it's slow and user-triggered
by design. The precomputed eval/gold_result.json stays the receipt of record —
and it stays tied to the frozen set it was computed on.
"""
from __future__ import annotations

import asyncio
import json
import os
import re

from fixtures.questions import FAILURE_CATEGORIES
from store.models import Check

# The canonical seed the "before" baseline is scored with (web.state.SEED_CHECK_ID
# is the same id; redeclared here so gold.py has no display-state import).
SEED_CHECK_ID = "numeric-cites-source"

_GOLD_RESULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "gold_result.json"
)

# The one directory owner adds may land in. Module attribute (read at call time)
# so tests can redirect every read AND write to a sandbox dir with one patch.
GOLD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval", "gold"
)

OWNER_ID_PREFIX = "g-owner-"  # owner-added ids can never collide with (or pose as) frozen g-* names
ALLOWED_VERDICTS = ("pass", "fail")
ALLOWED_CLAIM_TYPES = ("numeric", "quote", "judgment")  # the frozen items' claim_type vocabulary
_MAX_FIELD_CHARS = 2000
# One path-safe shape for ids: lowercase slug, no separators, no dots — rejected,
# never repaired, so "../x" is an error rather than a silent rewrite.
_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")


def load_gold_result() -> dict | None:
    """The PRECOMPUTED gold-gap receipt (seed vs grown rubric scored against the
    frozen gold set) — display only. Reads the result file, never the gold items."""
    try:
        with open(_GOLD_RESULT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return None


def gold_provenance() -> dict:
    """The on-disk gold set split by provenance (read-only): items with frozen:true
    are the offline-authored frozen set; everything else is owner-added (or at
    least NOT frozen — an unflagged stray must never be displayed as frozen)."""
    from eval.scoring import load_gold

    items = load_gold(GOLD_DIR)
    frozen = [it for it in items if it.get("frozen") is True]
    owner = [it for it in items if it.get("frozen") is not True]
    return {"frozen": frozen, "owner": owner}


def list_owner_items() -> list[dict]:
    """Just the owner-added gold items, sorted by filename (load_gold's order)."""
    return gold_provenance()["owner"]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")


def _safe_gold_id(gold_id: str | None, claim: str) -> str:
    """A path-safe id, ALWAYS carrying the owner prefix. An explicitly supplied id
    is validated and rejected on failure — never repaired — so path traversal
    ("../x") is an error, not a guess. A derived id is slugged from the claim."""
    if gold_id:
        if not _ID_RE.fullmatch(gold_id):
            raise ValueError(
                "unsafe id — use lowercase letters, digits and hyphens only "
                "(no slashes, dots or spaces)"
            )
        base = gold_id
    else:
        base = _slug(claim)
        if not base:
            raise ValueError("could not derive an id from the claim — supply one")
    return base if base.startswith(OWNER_ID_PREFIX) else OWNER_ID_PREFIX + base


def _owner_item_path(gold_id: str) -> str:
    """Absolute path for an owner item, provably confined to eval/gold/."""
    path = os.path.abspath(os.path.join(GOLD_DIR, gold_id + ".json"))
    if os.path.dirname(path) != os.path.abspath(GOLD_DIR):  # belt-and-braces after _ID_RE
        raise ValueError("gold write would escape eval/gold/ — refused")
    return path


def _read_back_item(path: str) -> dict:
    """The copy-verify read. A separate seam on purpose: tests patch THIS to prove
    a failed verify is reported honestly and leaves nothing behind."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_gold_item(*, question: str, claim: str, supporting_quote: str = "",
                  category: str = "clean", claim_type: str = "judgment",
                  expected_verdict: str = "pass", gold_id: str | None = None) -> dict:
    """Write ONE owner-labeled gold example into eval/gold/ with copy-verify.

    Mirrors the frozen items' schema exactly (gold_id/question/reference_answer/
    must_support/must_not_assert/expected_verdict/frozen), stored with
    frozen:false + provenance:"owner-added" — an owner label is never dressed up
    as part of the frozen set. Existing files (frozen above all) are never
    overwritten. Success means: written, read back off disk, and the parsed
    content matched; anything less removes the file and raises.
    """
    question = (question or "").strip()
    claim = (claim or "").strip()
    supporting_quote = (supporting_quote or "").strip()
    if not question or not claim:
        raise ValueError("both a question and the answer to label are required")
    for name, value in (("question", question), ("claim", claim),
                        ("supporting quote", supporting_quote)):
        if len(value) > _MAX_FIELD_CHARS:
            raise ValueError(f"{name} is too long (max {_MAX_FIELD_CHARS} characters)")
    if expected_verdict not in ALLOWED_VERDICTS:
        raise ValueError("the label must be 'pass' or 'fail'")
    if claim_type not in ALLOWED_CLAIM_TYPES:
        raise ValueError(f"claim_type must be one of {', '.join(ALLOWED_CLAIM_TYPES)}")
    if category != "clean" and category not in FAILURE_CATEGORIES:
        raise ValueError(f"unknown category: {category!r}")
    gid = _safe_gold_id(gold_id, claim)
    path = _owner_item_path(gid)
    if os.path.exists(path):
        raise ValueError(f"an item with id {gid} already exists — items are never overwritten")
    item = {
        "gold_id": gid,
        "question": question,
        "reference_answer": claim,
        "must_support": [
            {
                "claim": claim,
                "claim_type": claim_type,
                "supporting_quote": supporting_quote,
                "source_url": "S1",
                "category_relevant": category,
            }
        ],
        # frozen convention: a fail-labeled item's claim is exactly what the
        # agent must never assert; pass items here carry no counter-claims.
        "must_not_assert": [claim] if expected_verdict == "fail" else [],
        "expected_verdict": expected_verdict,
        "frozen": False,
        "provenance": "owner-added",  # explicit in storage, not just in the UI
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(item, f, indent=2, ensure_ascii=False)
        f.write("\n")
    try:
        stored = _read_back_item(path)
    except Exception as exc:  # noqa: BLE001 — unreadable == unverified == not added
        os.remove(path)
        raise RuntimeError(f"copy-verify failed — the item could not be read back ({exc}); "
                           "the file was removed") from exc
    if stored != item:
        os.remove(path)
        raise RuntimeError("copy-verify failed — what came back off disk does not match "
                           "what was written; the file was removed")
    return item


async def _score_rubric_async(rubric: "list[Check]", gold: list[dict]) -> list[bool]:
    """Per-item green/red, each gold item scored on its own thread (run_check is a
    blocking model call; per-item fan-out turns 15 sequential passes into one)."""
    from eval.scoring import score_rubric

    rows = await asyncio.gather(
        *(asyncio.to_thread(score_rubric, rubric, [item]) for item in gold)
    )
    return [r[0] for r in rows]


async def recompute_gold_result() -> dict:
    """Rescore the held-out gold set LIVE: seed rubric (before) vs the rubric as
    it now stands in the store (after). Returns the same shape as gold_result.json
    plus live=True, so _gold.html renders either blind.

    load_gold() takes every item in eval/gold/ — owner-added ones included — so
    the result also carries n_frozen/n_owner: the receipt copy must say which set
    it was computed on, or a grown denominator would silently pose as the frozen 15.
    """
    import store
    from config import get_settings
    from eval.scoring import headline, load_gold

    db = store.get_db()
    checks = await store.get_checks(db)
    if not checks:
        raise RuntimeError("rubric store is empty — no checks to score against gold")
    seed = [c for c in checks if c.id == SEED_CHECK_ID] or checks[:1]
    gold = load_gold()
    if not gold:
        raise RuntimeError("no gold items found under eval/gold/")
    before, after = await asyncio.gather(
        _score_rubric_async(seed, gold),
        _score_rubric_async(checks, gold),
    )
    cfg = get_settings()
    n_frozen = sum(1 for it in gold if it.get("frozen") is True)
    return headline(before, after) | {
        "checks_before": len(seed),
        "checks_after": len(checks),
        "backend": cfg.loop_backend,
        "model": cfg.gemini_model if cfg.loop_backend == "gemini" else cfg.grower_model,
        "live": True,
        # provenance of the scored set — the displayed receipt claims depend on it
        "n_frozen": n_frozen,
        "n_owner": len(gold) - n_frozen,
    }
