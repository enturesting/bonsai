"""Standalone test bootstrap: the package is NOT installed (a globally
registered pytest11 entry point would change the behavior of any suite on the
machine), so put src/ on sys.path here and let the plugin tests load the
plugin explicitly with `-p honesty_gate.plugin` inside pytester runs."""
import os
import sys

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

pytest_plugins = ["pytester"]
