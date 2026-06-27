"""
HARD RAIL: /loop must NEVER reference the gold set or import /eval.
One leak kills the honesty claim. This test fails the build if it happens.
"""
import glob
import os

LOOP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "loop"))

_FORBIDDEN = ("eval/gold", "eval.gold", "from eval", "import eval", "load_gold")


def test_loop_never_references_gold_or_eval():
    offenders = []
    for path in glob.glob(os.path.join(LOOP_DIR, "**", "*.py"), recursive=True):
        with open(path, encoding="utf-8") as f:
            src = f.read()
        if any(tok in src for tok in _FORBIDDEN):
            offenders.append(os.path.relpath(path, LOOP_DIR))
    assert not offenders, (
        f"honesty-gate LEAK — /loop references gold/eval in: {offenders}. "
        "The grower/pruner must never see the frozen gold set."
    )
