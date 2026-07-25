"""The honesty-gate lint, as an importable function. Verification-only.

This module IS the check CI runs: eval/tests/test_honesty_gate.py calls
`run_honesty_lint()` and fails the build on any offender, and the /web
"try to cheat it" station calls the SAME functions — so the verdict a visitor
sees is the CI verdict, never a re-implementation that could drift. Keep this
seam dependency-free (stdlib only, no model, no keys, no web imports): the
plugin extraction will mirror its exact shape.

A lint, not a sandbox: a static regex scan of /loop's raw source text
(comments and docstrings count). It proves the loop's shipping code doesn't
reference the held-out gold set — nothing more.

Precision notes (so the rail catches real leaks, not innocent look-alikes):
- Word-boundary import patterns, so names that merely CONTAIN "eval"
  (`eval_stream`, `evaluate`) never false-positive.
- Skips loop/tests/ — /loop ships its own parallel honesty check there, which
  legitimately contains the forbidden patterns as the strings it scans for.
  The rail is about /loop's runtime source, not its test fixtures.
"""
from __future__ import annotations

import glob
import os
import re

LOOP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "loop"))

# Real violations only: importing the `eval` package, or touching the gold set.
FORBIDDEN = [
    re.compile(r"\bimport\s+eval\b"),   # `import eval`            (NOT `import eval_stream`)
    re.compile(r"\bfrom\s+eval\b"),     # `from eval import ...`   (NOT `from .engine import eval_stream`)
    re.compile(r"\bfrom\s+eval\."),     # `from eval.scoring import ...`
    re.compile(r"eval/gold"),           # reading the gold directory
    re.compile(r"\bload_gold\b"),       # calling the gold loader
]


def lint_source(src: str) -> list[str]:
    """Forbidden patterns matched in ONE blob of source text.

    The shared core: the CI gate lints every real /loop file with it, and the
    "try to cheat it" station lints example snippets AS TEXT with it — the
    same rule either way. Returns the matched pattern strings (empty = clean).
    """
    return [p.pattern for p in FORBIDDEN if p.search(src)]


def loop_source_files(loop_dir: str = LOOP_DIR):
    """Every /loop runtime source file (recursive), skipping loop/tests/."""
    for path in sorted(glob.glob(os.path.join(loop_dir, "**", "*.py"), recursive=True)):
        if os.sep + "tests" + os.sep in path:
            continue  # /loop's own honesty check legitimately names the patterns
        yield path


def run_honesty_lint(loop_dir: str = LOOP_DIR) -> dict:
    """The full gate, exactly as CI runs it: scan /loop's source, report leaks.

    Returns {"clean": bool, "files_scanned": int,
             "offenders": [(relpath, [matched pattern strings]), ...]}.
    """
    offenders: list[tuple[str, list[str]]] = []
    files_scanned = 0
    for path in loop_source_files(loop_dir):
        files_scanned += 1
        with open(path, encoding="utf-8") as f:
            src = f.read()
        hits = lint_source(src)
        if hits:
            offenders.append((os.path.relpath(path, loop_dir), hits))
    return {"clean": not offenders, "files_scanned": files_scanned, "offenders": offenders}
