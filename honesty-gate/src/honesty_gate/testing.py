"""Ready-made enforcement test. Import it into any test file in your suite:

    from honesty_gate.testing import test_honesty_gate  # noqa: F401

pytest collects the imported function; it uses the `honesty_gate` fixture from
honesty_gate.plugin, so the plugin must be loaded (installed, or `-p
honesty_gate.plugin`) and configured in your ini/toml. It fails — never
passes vacuously — when the gate is unconfigured or scans zero files.

This module deliberately imports nothing, so it stays importable without
pytest installed.
"""


def test_honesty_gate(honesty_gate):
    """Build-failing gate: the scanned source references no forbidden target."""
    honesty_gate.assert_clean()
