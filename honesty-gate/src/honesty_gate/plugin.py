"""honesty_gate.plugin — the pytest entrypoint (declared as `pytest11` in pyproject.toml).

Configure in pytest.ini / tox.ini / setup.cfg / pyproject `[tool.pytest.ini_options]`:

    honesty_gate_dirs            = optimizer          # dirs to scan, relative to rootdir
    honesty_gate_forbid_imports  = answer_key         # module names -> word-boundary import patterns
    honesty_gate_forbid_patterns =                    # extra raw regexes, one per line
        goldset/
        \bload_answers\b
    honesty_gate_exclude_dirs    = tests              # dir names skipped (default: tests)

Then enforce with the ready-made test (one import in any test file):

    from honesty_gate.testing import test_honesty_gate  # noqa: F401

or write your own assertions against the `honesty_gate` fixture. The gate
refuses to pass vacuously: an unconfigured gate, or a scan that touches zero
files, FAILS instead of silently passing.

When this package is installed, the `pytest11` entry point loads this module
automatically; in a vendored/uninstalled checkout, load it explicitly with
`-p honesty_gate.plugin`.
"""
from __future__ import annotations

from typing import List, Sequence

import pytest

from .checker import CheckResult, Patternish, check, forbid_import


def pytest_addoption(parser):
    parser.addini(
        "honesty_gate_dirs",
        type="args",
        default=[],
        help="honesty-gate: source dirs to scan (relative to rootdir)",
    )
    parser.addini(
        "honesty_gate_forbid_imports",
        type="args",
        default=[],
        help="honesty-gate: module names whose import is forbidden (word-boundary patterns)",
    )
    parser.addini(
        "honesty_gate_forbid_patterns",
        type="linelist",
        default=[],
        help="honesty-gate: raw regex patterns that must not appear in scanned source",
    )
    parser.addini(
        "honesty_gate_exclude_dirs",
        type="args",
        default=["tests"],
        help="honesty-gate: directory names skipped during the scan (default: tests)",
    )


class HonestyGate:
    """The gate bound to this pytest run's ini/toml settings."""

    def __init__(
        self,
        source_dirs: Sequence[str],
        forbidden: Sequence[Patternish],
        exclude_dirs: Sequence[str],
        base_dir,
    ) -> None:
        self.source_dirs = list(source_dirs)
        self.forbidden = list(forbidden)
        self.exclude_dirs = tuple(exclude_dirs)
        self.base_dir = base_dir

    @property
    def configured(self) -> bool:
        return bool(self.source_dirs) and bool(self.forbidden)

    def run(self) -> CheckResult:
        """The raw structured result, for custom assertions."""
        return check(
            self.source_dirs,
            self.forbidden,
            exclude_dirs=self.exclude_dirs,
            base_dir=self.base_dir,
        )

    def assert_clean(self) -> CheckResult:
        """Fail the build on any forbidden reference — or on a vacuous scan."""
        __tracebackhide__ = True
        if not self.configured:
            pytest.fail(
                "honesty-gate is not configured — set honesty_gate_dirs plus "
                "honesty_gate_forbid_imports and/or honesty_gate_forbid_patterns "
                "in your pytest ini/toml. Refusing to pass vacuously."
            )
        result = self.run()
        if result.files_scanned == 0:
            pytest.fail(
                f"honesty-gate scanned zero files (dirs: {self.source_dirs}) — "
                "a gate that scans nothing proves nothing. Refusing to pass vacuously."
            )
        if not result.clean:
            pytest.fail(
                "honesty-gate LEAK — scanned source references a forbidden target:\n"
                + result.report()
            )
        return result


def gate_from_config(config) -> HonestyGate:
    """Build the configured gate from a pytest Config (ini/toml settings)."""
    forbidden: List[Patternish] = []
    for module in config.getini("honesty_gate_forbid_imports"):
        forbidden.extend(forbid_import(module))
    forbidden.extend(config.getini("honesty_gate_forbid_patterns"))
    return HonestyGate(
        source_dirs=config.getini("honesty_gate_dirs"),
        forbidden=forbidden,
        exclude_dirs=config.getini("honesty_gate_exclude_dirs"),
        base_dir=config.rootpath,
    )


@pytest.fixture
def honesty_gate(pytestconfig) -> HonestyGate:
    """The configured gate: `.assert_clean()` to enforce, `.run()` to inspect."""
    return gate_from_config(pytestconfig)
