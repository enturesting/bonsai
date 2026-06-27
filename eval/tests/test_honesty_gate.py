"""
HARD RAIL: /loop's shipping code must NEVER import the /eval package or read the
gold set. One leak kills the honesty claim — this test fails the build if it happens.

Precision notes (so the rail catches real leaks, not innocent look-alikes):
- Uses word-boundary import patterns so names like `eval_stream` / `evaluate`
  (which merely CONTAIN "eval") don't false-positive.
- Skips loop/tests/ — /loop ships its own parallel honesty check there, which
  legitimately contains the forbidden patterns as the strings it scans for.
  The rail is about /loop's runtime source, not its test fixtures.
"""
import glob
import os
import re

LOOP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "loop"))

# Real violations only: importing the `eval` package, or touching the gold set.
_FORBIDDEN = [
    re.compile(r"\bimport\s+eval\b"),   # `import eval`            (NOT `import eval_stream`)
    re.compile(r"\bfrom\s+eval\b"),     # `from eval import ...`   (NOT `from .engine import eval_stream`)
    re.compile(r"\bfrom\s+eval\."),     # `from eval.scoring import ...`
    re.compile(r"eval/gold"),           # reading the gold directory
    re.compile(r"\bload_gold\b"),       # calling the gold loader
]


def _loop_source_files():
    for path in glob.glob(os.path.join(LOOP_DIR, "**", "*.py"), recursive=True):
        if os.sep + "tests" + os.sep in path:
            continue  # /loop's own honesty check legitimately names the patterns
        yield path


def test_loop_never_references_gold_or_eval():
    offenders = []
    for path in _loop_source_files():
        with open(path, encoding="utf-8") as f:
            src = f.read()
        hits = [p.pattern for p in _FORBIDDEN if p.search(src)]
        if hits:
            offenders.append((os.path.relpath(path, LOOP_DIR), hits))
    assert not offenders, (
        f"honesty-gate LEAK — /loop source references gold/eval: {offenders}. "
        "The grower/pruner must never see the frozen gold set."
    )
