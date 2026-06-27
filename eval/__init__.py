"""Bonsai /eval — gold scoring + honest stats. Verification-only.

Package-level re-exports so the CONTRACTS §3 names resolve as `eval.<name>`
(e.g. `from eval import headline`). The improvement loop (`/loop`) must NEVER
import this package — that rail is enforced by eval/tests/test_honesty_gate.py.
`score_rubric` lazy-imports `loop.checker.run_check` inside the function, so
importing this package does not pull in /loop at module load.
"""
from eval.scoring import load_gold, score_rubric, headline
from eval.stats import wilson, sign_test

__all__ = ["load_gold", "score_rubric", "headline", "wilson", "sign_test"]
