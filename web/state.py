"""web/state.py — in-memory rubric grow/prune history for the bonsai viz.

This is DISPLAY state only. /web records a branch when it observes an improve's
`score` event (via web.sse.sse_events' observer hook); it never mints or prunes
checks itself — that lives in /loop. A single process-wide RUBRIC backs the demo.
"""
from __future__ import annotations

from fixtures.questions import FAILURE_CATEGORIES  # the 5 failure families the meter tracks

# The canonical first check (CONTRACTS §0): the seed the tree grows from.
SEED_CHECK_ID = "numeric-cites-source"

# Human labels for the rubric panel — the 5 failure families + the clean control.
CATEGORY_LABELS = {
    "unsupported-numeric":    "Invented numbers",
    "fabricated-quote":       "Made-up quotes",
    "stale-wrong-citation":   "Wrong / stale citation",
    "vague-not-checkable":    "Too vague to check",
    "single-source-overcite": "Over-cited source",
    "clean":                  "Confirmed clean (control)",
}

# SVG geometry (viewBox 0 0 240 200): branches climb the trunk, alternating
# sides and curving upward like a real bonsai. Each branch is drawn as a
# quadratic arc trunk→tip; `ctrl_*` is the bow. Small per-index jitter keeps the
# silhouette organic without any randomness (deterministic → stable in tests).
_TRUNK_X = 120
_BASE_Y = 174
_STEP = 21
_LEN = 38
_RISE = 16
# Deterministic "natural" variation, indexed by branch position.
_LEN_JITTER = (0.0, 4.0, -3.0, 5.0, -2.0, 3.0, -4.0, 2.0)
_RISE_JITTER = (0.0, 2.0, -1.0, 3.0, 1.0, -2.0, 2.0, -1.0)


class Rubric:
    def __init__(self) -> None:
        # (claim_id, passed, category) in insertion order. category powers the
        # maturation panel; branches() ignores it (the tree shape is unchanged).
        self._growth: list[tuple[str, bool, str]] = []

    def record_growth(self, claim_id: str, passed: bool, category: str = "") -> None:
        """Sprout/replace the branch for this claim (latest improve wins)."""
        self._growth = [(c, p, cat) for (c, p, cat) in self._growth if c != claim_id]
        self._growth.append((claim_id, bool(passed), category))

    def reset(self) -> None:
        self._growth = []

    def branches(self) -> list[dict]:
        """Seed branch + one branch per recorded improve, with drawable coords."""
        rows: list[tuple[str, str]] = [(SEED_CHECK_ID, "seed")]
        rows += [(cid, "green" if passed else "amber") for cid, passed, _cat in self._growth]

        last = len(rows) - 1
        out: list[dict] = []
        for i, (claim_id, status) in enumerate(rows):
            side = -1 if i % 2 == 0 else 1
            j = i % len(_LEN_JITTER)
            length = _LEN + _LEN_JITTER[j]
            rise = _RISE + _RISE_JITTER[j]
            y = _BASE_Y - i * _STEP
            x_tip = _TRUNK_X + side * length
            y_tip = y - rise
            # Bow the branch: control point sits out along the limb and lower,
            # so the arc lifts toward its leafy tip rather than running straight.
            ctrl_x = _TRUNK_X + side * (length * 0.55)
            ctrl_y = y + 3
            out.append(
                {
                    "claim_id": claim_id,
                    "status": status,
                    "new": i == last and status != "seed",
                    "x1": _TRUNK_X,
                    "y1": y,
                    "x2": x_tip,
                    "y2": y_tip,
                    "ctrl_x": ctrl_x,
                    "ctrl_y": ctrl_y,
                    # foliage cluster anchored at the tip (template fans 3 leaves)
                    "leaf_cx": x_tip,
                    "leaf_cy": y_tip,
                    "side": side,
                }
            )
        return out

    # ── maturation panel (DISPLAY state; derived from the same _growth log) ──

    def _family_set(self) -> set:
        """Distinct FAILURE families seen (clean is the control, never a family)."""
        return {cat for _, _, cat in self._growth if cat not in ("", "clean")}

    def checks(self) -> list[dict]:
        """One row per minted failure-family check (NOT per claim). version = count
        of DISTINCT contributing claim_ids in that family — a re-click of the same
        failure does not sharpen the check; only a new example does."""
        from web.mock_stream import rung, rung_diff  # display copy only (lazy import)

        families: dict[str, dict] = {}
        for cid, passed, cat in self._growth:
            if cat in ("", "clean"):
                continue
            f = families.setdefault(cat, {"claims": [], "passed": False})
            if cid not in f["claims"]:
                f["claims"].append(cid)
            f["passed"] = passed  # latest improve in this family wins
        # the family touched by the MOST RECENT improve (None if that improve was a
        # clean control — so the clean beat highlights nothing).
        last = self._growth[-1] if self._growth else None
        last_cat = last[2] if last and last[2] not in ("", "clean") else None
        rows: list[dict] = []
        for cat, f in families.items():
            version = len(f["claims"])
            rows.append(
                {
                    "category": cat,
                    "label": CATEGORY_LABELS.get(cat, cat),
                    "version": version,
                    "minted_from": version,
                    # a minted check is NEVER vague: show the precise rung (v2+); the
                    # vague v1 rung surfaces only as the diff's strikethrough `from`.
                    "property": rung(cat, max(version, 2)),
                    "diff": rung_diff(cat, version) if version > 1 else None,
                    "status": "active",  # every minted failure-family check is active
                    "new": cat == last_cat,
                }
            )
        return rows

    def maturity(self) -> dict:
        """Coverage of the 5 failure families + improve count, for the meter."""
        fam = self._family_set()
        improves = len([1 for _, _, cat in self._growth if cat not in ("", "clean")])
        # animate ONLY a segment this most-recent improve FIRST covered — so a v2
        # bump on an already-covered family, and the clean beat, don't re-pulse.
        new_cat = None
        last = self._growth[-1] if self._growth else None
        if last and last[2] not in ("", "clean"):
            fam_claims = {cid for cid, _, c in self._growth if c == last[2]}
            if len(fam_claims) == 1:
                new_cat = last[2]
        return {
            "covered": len(fam),
            "total": len(FAILURE_CATEGORIES),
            "n_checks": len(fam),
            "n_improves": improves,
            "segments": [
                {"category": c, "label": CATEGORY_LABELS.get(c, c),
                 "filled": c in fam, "new": c == new_cat}
                for c in FAILURE_CATEGORIES
            ],
        }


# Process-wide rubric for the running harness.
RUBRIC = Rubric()
