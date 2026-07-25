"""honesty_gate.checker — the importable seam: structured violations
(file, line, matched pattern) from a raw-text scan. Usable without pytest.

Fixture theme is deliberately generic (an "optimizer" that must not read an
"answer_key"): the library is themeless by design.
"""
from honesty_gate import (
    Violation,
    check,
    forbid_import,
    forbid_name,
    forbid_path,
    lint_source,
)

FORBIDDEN = forbid_import("answer_key") + [
    forbid_path("goldset/"),
    forbid_name("load_answers"),
]


def test_forbid_import_matches_real_imports_only():
    pats = forbid_import("answer_key")
    assert lint_source("import answer_key", pats)
    assert lint_source("from answer_key import load", pats)
    assert lint_source("from answer_key.scoring import agree", pats)
    # names that merely CONTAIN the module name never false-positive
    assert lint_source("import answer_key_stream", pats) == []
    assert lint_source("from optimizer.engine import answer_key_stream", pats) == []


def test_lint_source_reports_file_line_and_pattern():
    src = "x = 1\n# TODO: peek at goldset/items.json, just this once\nk = load_answers()\n"
    violations = lint_source(src, FORBIDDEN, file="optimizer/core.py")
    assert violations == [
        Violation(
            file="optimizer/core.py",
            line=2,
            pattern=forbid_path("goldset/"),
            excerpt="# TODO: peek at goldset/items.json, just this once",
        ),
        Violation(
            file="optimizer/core.py",
            line=3,
            pattern=forbid_name("load_answers"),
            excerpt="k = load_answers()",
        ),
    ]


def test_lint_source_raw_text_semantics_comments_and_docstrings_count():
    assert lint_source('"""never do `from answer_key import x` here"""', FORBIDDEN)
    assert lint_source("# import answer_key\npass\n", FORBIDDEN)


def test_lint_source_reports_each_pattern_once_at_first_match():
    src = "a = load_answers()\nb = load_answers()\n"
    violations = lint_source(src, FORBIDDEN)
    assert len(violations) == 1
    assert violations[0].line == 1


def test_check_scans_tree_skips_tests_dirs_and_labels_relative_to_given_dir(tmp_path):
    pkg = tmp_path / "optimizer"
    pkg.mkdir()
    (pkg / "core.py").write_text("from answer_key import load\n", encoding="utf-8")
    (pkg / "util.py").write_text("from optimizer.engine import improve\n", encoding="utf-8")
    tests = pkg / "tests"
    tests.mkdir()
    # an enforcing test suite legitimately names the patterns — excluded by default
    (tests / "test_rail.py").write_text('PATTERNS = ["load_answers", "goldset/"]\n', encoding="utf-8")

    result = check(["optimizer"], FORBIDDEN, base_dir=tmp_path)
    assert result.files_scanned == 2  # tests/ excluded
    assert not result.clean
    [v] = result.violations
    assert (v.file, v.line) == ("optimizer/core.py", 1)
    assert v.pattern in forbid_import("answer_key")


def test_check_exclude_dirs_is_overridable(tmp_path):
    pkg = tmp_path / "optimizer"
    (pkg / "tests").mkdir(parents=True)
    (pkg / "tests" / "test_x.py").write_text("import answer_key\n", encoding="utf-8")
    strict = check([pkg], FORBIDDEN, exclude_dirs=())
    assert strict.files_scanned == 1 and not strict.clean
    default = check([pkg], FORBIDDEN)
    assert default.files_scanned == 0 and default.clean


def test_check_multiple_dirs_and_clean_result(tmp_path):
    for name in ("alpha", "beta"):
        d = tmp_path / name
        d.mkdir()
        (d / "mod.py").write_text("value = 1\n", encoding="utf-8")
    result = check(["alpha", "beta"], FORBIDDEN, base_dir=tmp_path)
    assert result.clean
    assert result.files_scanned == 2
    assert result.violations == ()
    assert "clean" in result.report() and "2 file(s) scanned" in result.report()


def test_check_missing_dir_is_zero_scanned_never_a_crash(tmp_path):
    result = check(["no_such_dir"], FORBIDDEN, base_dir=tmp_path)
    assert result.clean and result.files_scanned == 0  # enforcement layers must fail this


def test_report_names_file_line_and_pattern(tmp_path):
    pkg = tmp_path / "optimizer"
    pkg.mkdir()
    (pkg / "sneaky.py").write_text("import json\nk = open('goldset/items.json')\n", encoding="utf-8")
    report = check(["optimizer"], FORBIDDEN, base_dir=tmp_path).report()
    assert "optimizer/sneaky.py:2" in report
    assert "goldset/" in report
