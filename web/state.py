"""web/state.py — in-memory rubric grow/prune history for the bonsai viz.

This is DISPLAY state only. /web records a branch when it observes an improve's
`score` event (via web.sse.sse_events' observer hook); it never mints or prunes
checks itself — that lives in /loop. A single process-wide RUBRIC backs the demo.
"""
from __future__ import annotations

# The canonical first check (CONTRACTS §0): the seed the tree grows from.
SEED_CHECK_ID = "numeric-cites-source"

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
        self._growth: list[tuple[str, bool]] = []  # (claim_id, passed), insertion order

    def record_growth(self, claim_id: str, passed: bool) -> None:
        """Sprout/replace the branch for this claim (latest improve wins)."""
        self._growth = [(c, p) for (c, p) in self._growth if c != claim_id]
        self._growth.append((claim_id, bool(passed)))

    def reset(self) -> None:
        self._growth = []

    def branches(self) -> list[dict]:
        """Seed branch + one branch per recorded improve, with drawable coords."""
        rows: list[tuple[str, str]] = [(SEED_CHECK_ID, "seed")]
        rows += [(cid, "green" if passed else "amber") for cid, passed in self._growth]

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


# Process-wide rubric for the running harness.
RUBRIC = Rubric()
