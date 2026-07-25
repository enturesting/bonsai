# honesty-gate

A tiny library + pytest plugin for one pattern worth naming: the **honesty
gate** — a build-failing lint proving that a self-improving system's source
code never references its held-out answer key, paired with a **Wilson
receipt** that reports improvement as direction + confidence interval, never
a bare percent.

Extracted from the Bonsai eval harness, where the same gate runs in CI. The
library here is themeless: it imports nothing from Bonsai and knows nothing
about it — you point it at your own dirs and your own forbidden targets.

## What it proves — and what it doesn't

- **It is a lint, not a sandbox.** The gate is a static regex scan over raw
  source text (comments and docstrings count). It proves the improving code
  doesn't *reference* the forbidden targets. It does **not** make cheating
  impossible: dynamic imports, filesystem indirection, or string assembly can
  evade a text scan. It guards the obvious leak and fails the build loudly —
  nothing more.
- **The gate never passes vacuously.** Unconfigured, or a scan that touches
  zero files, is a failure — a gate that scans nothing proves nothing.
- **A held-out score *agrees*, it never *proves*.** The receipt states
  agreement with a held-out reference as direction + counts + a 95% Wilson
  interval. At n ≈ 15–40 a bare percentage overclaims, so this package has no
  API that renders one.

## Importable checker seam (no pytest required)

```python
from honesty_gate import check, forbid_import, forbid_path, forbid_name

result = check(
    ["optimizer"],                       # source dirs to scan, recursively
    forbid_import("answer_key")          # import answer_key / from answer_key(.x) import
    + [forbid_path("goldset/"),          # the literal answer-key path
       forbid_name("load_answers")],     # the key loader, as a whole word
)

result.clean          # False if anything matched
result.files_scanned  # 0 means the gate proved nothing — treat as failure
result.violations     # structured: (file, line, pattern, excerpt) per hit
print(result.report())
```

Precision rules: `forbid_import` builds word-boundary patterns, so names that
merely contain the module name (`answer_key_stream`) never false-positive;
directories named `tests` are skipped by default (`exclude_dirs=`), because a
suite enforcing this gate legitimately names the forbidden patterns.

## pytest entrypoint

Declared as a `pytest11` entry point in `pyproject.toml`, so installing the
package registers the plugin. In a vendored/uninstalled checkout, load it
explicitly with `-p honesty_gate.plugin`. Configure in `pytest.ini` /
`tox.ini` / `setup.cfg` or `pyproject.toml` `[tool.pytest.ini_options]`:

```ini
[pytest]
honesty_gate_dirs            = optimizer
honesty_gate_forbid_imports  = answer_key
honesty_gate_forbid_patterns =
    goldset/
    \bload_answers\b
honesty_gate_exclude_dirs    = tests
```

Then enforce with the ready-made test — one import in any test file:

```python
from honesty_gate.testing import test_honesty_gate  # noqa: F401
```

or write custom assertions against the `honesty_gate` fixture:

```python
def test_gate(honesty_gate):
    result = honesty_gate.assert_clean()   # fails the build on any leak
    assert result.files_scanned > 10       # and on a vacuous scan, always
```

## Wilson receipt

```python
from honesty_gate import receipt, receipt_from_counts

r = receipt(before=[...], after=[...])   # paired verdicts on the SAME held-out items
str(r)
# 'improved — 6 → 11 / 15 · 95% CI [48.0%, 89.1%] · 5 helped, 0 hurt'

str(receipt_from_counts(11, 6, 15))      # counts only: no sign test, still an interval
# 'regressed — 11 → 6 / 15 · 95% CI [19.8%, 64.3%]'
```

The formatter always emits direction (`improved` / `unchanged` / `regressed`)
plus counts and the interval; a regression prints as a regression — the
receipt exists to expose exactly that case, never to dress it up.

## Running this package's tests

Standalone, without installing (installing would globally register the
`pytest11` entry point and change other suites' behavior):

```
cd honesty-gate && python -m pytest -q
```

The root `conftest.py` puts `src/` on `sys.path`; the plugin tests run the
plugin inside pytest's `pytester` fixture via explicit `-p` loading.

## Status

Not published to any index. MIT licensed.
