"""web/state.py — in-memory rubric grow/prune history for the bonsai viz.

This is DISPLAY state only. /web records a branch when it observes an improve's
`score` event (via web.sse.sse_events' observer hook); it never mints or prunes
checks itself — that lives in /loop. A single process-wide RUBRIC backs the demo.
"""
from __future__ import annotations

# The canonical first check (CONTRACTS §0): the seed the tree grows from.
SEED_CHECK_ID = "numeric-cites-source"

# SVG geometry (viewBox 0 0 240 200): branches climb the trunk, alternating sides.
_TRUNK_X = 120
_BASE_Y = 172
_STEP = 22
_LEN = 36
_RISE = 14


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
            y = _BASE_Y - i * _STEP
            x_tip = _TRUNK_X + side * _LEN
            y_tip = y - _RISE
            out.append(
                {
                    "claim_id": claim_id,
                    "status": status,
                    "new": i == last and status != "seed",
                    "x1": _TRUNK_X,
                    "y1": y,
                    "x2": x_tip,
                    "y2": y_tip,
                    "leaf_cx": x_tip,
                    "leaf_cy": y_tip,
                }
            )
        return out


# Process-wide rubric for the running harness.
RUBRIC = Rubric()
