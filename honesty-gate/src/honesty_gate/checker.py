"""honesty_gate.checker — the importable gate. A lint, not a sandbox.

The pattern this package names: a self-improving system must not be able to
read its own held-out answer key. This module proves the narrow, checkable
part of that claim — that the improving code's RAW SOURCE TEXT never
references the forbidden targets (imports of the scoring package, paths to
the answer key, names of its loader). Comments and docstrings count; any
match fails the gate.

What it does NOT do: it is not a sandbox and does not make cheating
impossible. Dynamic imports, filesystem indirection, or string assembly can
evade a text scan. The gate guards the obvious leak and fails the build
loudly — nothing more, and it should be described as nothing more.

Precision rules (so the gate catches real leaks, not innocent look-alikes):
- `forbid_import("key")` builds word-boundary patterns, so names that merely
  CONTAIN the module name (`key_stream`, `monkey`) never false-positive.
- Directories named in `exclude_dirs` (default: `tests`) are skipped — a
  suite that enforces this same gate legitimately contains the forbidden
  patterns as the strings it scans for. The gate is about runtime source,
  not test fixtures.
- A scan that touches zero files is reported as `files_scanned == 0`; the
  pytest entrypoint refuses to let that pass vacuously.

No third-party imports here: this seam must stay importable anywhere,
with or without pytest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

Patternish = Union[str, "re.Pattern[str]"]
PathLike = Union[str, "Path"]


@dataclass(frozen=True)
class Violation:
    """One forbidden reference: where it is and what matched."""

    file: str      # path label (source dir spelling + relative path, or the label given)
    line: int      # 1-indexed line of the FIRST match of this pattern in the file
    pattern: str   # the regex pattern string that matched
    excerpt: str   # the offending source line, stripped


@dataclass(frozen=True)
class CheckResult:
    """Structured outcome of one gate run."""

    clean: bool
    files_scanned: int
    violations: Tuple[Violation, ...]

    def report(self) -> str:
        """Human-readable summary. Never overclaims: 'clean' means only that
        this text scan matched nothing — it is a lint verdict, not a proof."""
        if self.clean:
            return (
                f"clean — {self.files_scanned} file(s) scanned, "
                "0 forbidden references (a lint verdict, not a sandbox)"
            )
        lines = [
            f"{len(self.violations)} forbidden reference(s) "
            f"across {self.files_scanned} file(s) scanned:"
        ]
        for v in self.violations:
            lines.append(f"  {v.file}:{v.line} — pattern `{v.pattern}` — {v.excerpt}")
        return "\n".join(lines)


def forbid_import(module: str) -> List[str]:
    """Word-boundary patterns forbidding any import of `module`:
    `import m`, `from m import ...`, `from m.sub import ...` — but never a
    name that merely contains it (`m_stream`, `prefix_m`)."""
    m = re.escape(module)
    return [rf"\bimport\s+{m}\b", rf"\bfrom\s+{m}\b", rf"\bfrom\s+{m}\."]


def forbid_path(fragment: str) -> str:
    """Pattern forbidding a literal path fragment (e.g. the answer-key dir)."""
    return re.escape(fragment)


def forbid_name(name: str) -> str:
    """Pattern forbidding a bare name as a whole word (e.g. the key loader)."""
    return rf"\b{re.escape(name)}\b"


def compile_forbidden(forbidden: Iterable[Patternish]) -> List["re.Pattern[str]"]:
    """Accept pattern strings or precompiled regexes; return compiled regexes."""
    return [p if isinstance(p, re.Pattern) else re.compile(p) for p in forbidden]


def lint_source(
    src: str,
    forbidden: Iterable[Patternish],
    file: str = "<text>",
) -> List[Violation]:
    """The shared text core: forbidden patterns matched in ONE blob of source.

    Raw-text semantics: comments and docstrings count. Each pattern is
    reported at most once per blob, at the line of its first match (fix it,
    rerun). Returns [] when clean. Results are sorted by line.
    """
    violations: List[Violation] = []
    lines = src.splitlines()
    for pattern in compile_forbidden(forbidden):
        match = pattern.search(src)
        if match is None:
            continue
        line_no = src.count("\n", 0, match.start()) + 1
        excerpt = lines[line_no - 1].strip() if line_no <= len(lines) else ""
        violations.append(
            Violation(file=file, line=line_no, pattern=pattern.pattern, excerpt=excerpt)
        )
    violations.sort(key=lambda v: (v.line, v.pattern))
    return violations


def check(
    source_dirs: Union[PathLike, Sequence[PathLike]],
    forbidden: Iterable[Patternish],
    *,
    exclude_dirs: Sequence[str] = ("tests",),
    base_dir: Optional[PathLike] = None,
) -> CheckResult:
    """The full gate, usable without pytest: scan every `*.py` under each
    source dir (recursively), skipping any subdirectory named in
    `exclude_dirs`, and report structured violations.

    `source_dirs` may be one path or a sequence; each is resolved against
    `base_dir` (when given), and violation `file` labels keep the caller's
    spelling — scanning "optimizer" labels offenders "optimizer/core.py".

    A missing or empty dir yields zero scanned files and `clean=True`;
    enforcement layers must treat `files_scanned == 0` as a failure so the
    gate can never pass vacuously.
    """
    if isinstance(source_dirs, (str, Path)):
        source_dirs = [source_dirs]
    patterns = compile_forbidden(forbidden)
    excluded = set(exclude_dirs)
    violations: List[Violation] = []
    files_scanned = 0
    for given in source_dirs:
        root = Path(base_dir, given) if base_dir is not None else Path(given)
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(root)
            if excluded.intersection(rel.parts[:-1]):
                continue  # an enforcing test suite legitimately names the patterns
            files_scanned += 1
            src = path.read_text(encoding="utf-8", errors="replace")
            violations.extend(lint_source(src, patterns, file=str(Path(given) / rel)))
    return CheckResult(
        clean=not violations,
        files_scanned=files_scanned,
        violations=tuple(violations),
    )
