"""
HARD RAIL: /loop's shipping code must NEVER import the /eval package or read the
gold set. One leak kills the honesty claim — this test fails the build if it happens.

The checker itself lives in eval/honesty.py so the /web "try to cheat it" station
can run the SAME functions this test runs (the station's claim "the exact check CI
runs" must be literally true). This file stays the build-failing enforcement point;
the injected-leak tests below prove the refactor didn't weaken the gate.
"""
from eval.honesty import lint_source, run_honesty_lint


def test_loop_never_references_gold_or_eval():
    result = run_honesty_lint()
    assert result["clean"], (
        f"honesty-gate LEAK — /loop source references gold/eval: {result['offenders']}. "
        "The grower/pruner must never see the frozen gold set."
    )
    # the gate scanning zero files would pass vacuously — make that impossible
    assert result["files_scanned"] > 0


def test_gate_fails_on_an_injected_leak(tmp_path):
    """The rail must FAIL on a leak, not merely pass on clean source: a loop-shaped
    dir with a file that reads the gold set is reported as an offender."""
    (tmp_path / "sneaky.py").write_text(
        'import json\n\nwith open("eval/gold/g-clean-breach-notification.json") as f:\n'
        "    answers = json.load(f)\n",
        encoding="utf-8",
    )
    (tmp_path / "clean.py").write_text("from loop.engine import eval_stream\n", encoding="utf-8")
    result = run_honesty_lint(loop_dir=str(tmp_path))
    assert not result["clean"]
    assert result["files_scanned"] == 2
    [(path, hits)] = result["offenders"]
    assert path == "sneaky.py"
    assert "eval/gold" in hits


def test_gate_counts_comments_and_skips_only_tests_dirs(tmp_path):
    """Raw-text scan: a leak hidden in a comment still fails; loop/tests/ is the
    ONLY carve-out (its parallel rail legitimately names the patterns)."""
    (tmp_path / "pruner.py").write_text(
        "# TODO(dev): peek at eval/gold before pruning, just this once\nRUBRIC_MIN = 3\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_rail.py").write_text('PATTERNS = ["load_gold", "eval/gold"]\n', encoding="utf-8")
    result = run_honesty_lint(loop_dir=str(tmp_path))
    assert result["files_scanned"] == 1  # tests/ excluded from the scan
    assert result["offenders"] == [("pruner.py", ["eval/gold"])]


def test_lint_source_catches_leaks_and_ignores_innocent_lookalikes():
    """The shared text core (also what the station lints snippets with)."""
    assert lint_source("from eval.scoring import load_gold") == [
        r"\bfrom\s+eval\b", r"\bfrom\s+eval\.", r"\bload_gold\b",
    ]
    assert lint_source("import eval") == [r"\bimport\s+eval\b"]
    # names that merely CONTAIN "eval" must never false-positive
    assert lint_source("from loop.engine import eval_stream\nscore = evaluate(x)\n") == []
