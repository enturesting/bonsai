"""honesty_gate.plugin — the pytest entrypoint: ini/toml-configured dirs +
the ready-made test + the fixture. The package is deliberately NOT installed,
so every pytester run loads the plugin explicitly with `-p honesty_gate.plugin`
(exactly how a vendored checkout would)."""

PLUGIN = ("-p", "honesty_gate.plugin")

READY_MADE = "from honesty_gate.testing import test_honesty_gate  # noqa: F401\n"


def configure(pytester, dirs="optimizer"):
    pytester.makeini(
        f"""
        [pytest]
        honesty_gate_dirs = {dirs}
        honesty_gate_forbid_imports = answer_key
        honesty_gate_forbid_patterns =
            goldset/
            \\bload_answers\\b
        """
    )


def test_gate_fails_on_a_leak_and_names_the_offender(pytester):
    configure(pytester)
    pkg = pytester.mkdir("optimizer")
    pkg.joinpath("core.py").write_text("from answer_key import load\n", encoding="utf-8")
    pkg.joinpath("clean.py").write_text("value = 1\n", encoding="utf-8")
    pytester.makepyfile(test_gate=READY_MADE)
    result = pytester.runpytest(*PLUGIN)
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*honesty-gate LEAK*", "*optimizer/core.py:1*"])


def test_gate_passes_on_clean_source(pytester):
    configure(pytester)
    pkg = pytester.mkdir("optimizer")
    pkg.joinpath("core.py").write_text("value = 1\n", encoding="utf-8")
    pytester.makepyfile(test_gate=READY_MADE)
    pytester.runpytest(*PLUGIN).assert_outcomes(passed=1)


def test_gate_skips_tests_dirs_by_default(pytester):
    configure(pytester)
    tests_dir = pytester.mkdir("optimizer").joinpath("tests")
    tests_dir.mkdir()
    # the enforcing suite names the patterns — that must not fail the gate
    tests_dir.joinpath("test_rail.py").write_text(
        'PATTERNS = ["load_answers", "goldset/"]\n', encoding="utf-8"
    )
    pytester.path.joinpath("optimizer", "core.py").write_text("value = 1\n", encoding="utf-8")
    pytester.makepyfile(test_gate=READY_MADE)
    pytester.runpytest(*PLUGIN).assert_outcomes(passed=1)


def test_unconfigured_gate_fails_never_passes_vacuously(pytester):
    pytester.makepyfile(test_gate=READY_MADE)
    result = pytester.runpytest(*PLUGIN)
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*not configured*Refusing to pass vacuously*"])


def test_zero_files_scanned_fails_never_passes_vacuously(pytester):
    configure(pytester, dirs="no_such_dir")
    pytester.makepyfile(test_gate=READY_MADE)
    result = pytester.runpytest(*PLUGIN)
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*scanned zero files*"])


def test_fixture_exposes_structured_result_for_custom_assertions(pytester):
    configure(pytester)
    pkg = pytester.mkdir("optimizer")
    pkg.joinpath("core.py").write_text("# goldset/ would be a leak\n", encoding="utf-8")
    pkg.joinpath("util.py").write_text("value = 1\n", encoding="utf-8")
    pytester.makepyfile(
        test_custom="""
        def test_custom(honesty_gate):
            result = honesty_gate.run()
            assert result.files_scanned == 2
            assert not result.clean
            [v] = result.violations
            assert (v.file, v.line) == ("optimizer/core.py", 1)
        """
    )
    pytester.runpytest(*PLUGIN).assert_outcomes(passed=1)


def test_toml_configuration_works(pytester):
    pytester.makepyprojecttoml(
        """
        [tool.pytest.ini_options]
        honesty_gate_dirs = ["optimizer"]
        honesty_gate_forbid_imports = ["answer_key"]
        """
    )
    pkg = pytester.mkdir("optimizer")
    pkg.joinpath("core.py").write_text("import answer_key\n", encoding="utf-8")
    pytester.makepyfile(test_gate=READY_MADE)
    result = pytester.runpytest(*PLUGIN)
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*optimizer/core.py:1*"])
