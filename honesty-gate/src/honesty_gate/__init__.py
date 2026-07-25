"""honesty-gate — a build-failing lint (not a sandbox) for self-improving
systems, plus a Wilson receipt that never renders improvement as a bare percent.

Importable seam (no pytest required):

    from honesty_gate import check, forbid_import, forbid_path, forbid_name
    result = check(["optimizer"], forbid_import("answer_key"))

The pytest entrypoint lives in `honesty_gate.plugin` (declared as a
`pytest11` entry point) and is only imported when pytest loads it — importing
this package pulls in stdlib only.
"""
from .checker import (
    CheckResult,
    Violation,
    check,
    compile_forbidden,
    forbid_import,
    forbid_name,
    forbid_path,
    lint_source,
)
from .receipt import (
    Receipt,
    format_receipt,
    receipt,
    receipt_from_counts,
    sign_test,
    wilson,
)

__version__ = "0.1.0"

__all__ = [
    "CheckResult",
    "Violation",
    "check",
    "compile_forbidden",
    "forbid_import",
    "forbid_name",
    "forbid_path",
    "lint_source",
    "Receipt",
    "format_receipt",
    "receipt",
    "receipt_from_counts",
    "sign_test",
    "wilson",
    "__version__",
]
