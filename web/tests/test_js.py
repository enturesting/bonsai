"""Run the node-based unit tests for web/static/main.js as part of pytest.

Keeps the JS score formatter honest in the same `pytest` run. Skips cleanly if
node isn't installed.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_NODE = shutil.which("node")
_TEST = Path(__file__).resolve().parent / "main.test.js"


@pytest.mark.skipif(_NODE is None, reason="node not installed")
def test_main_js_pure_formatters():
    result = subprocess.run(
        [_NODE, "--test", str(_TEST)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
