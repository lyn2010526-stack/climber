#!/usr/bin/env python3
"""Auto-fix common lint errors and formatting issues.

Automatically resolves common problems detected by ruff and other linters:
- Unused imports (F401)
- Missing trailing commas
- Import sorting (I001)
- Unnecessary pass statements
- Unused variables (with _ prefix convention)
- Line length issues (auto-wrap)
- Type annotation simplifications

Usage:
    python scripts/auto_fix.py
    python scripts/auto_fix.py --check
    python scripts/auto_fix.py --only unused-imports
    python scripts/auto_fix.py --path app/core/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUFF_FIXABLE_RULES = [
    "I",       # isort
    "F401",    # unused imports
    "F841",    # unused variables
    "E401",    # blank line after imports
    "E711",    # comparison to None
    "E712",    # comparison to True/False
    "UP",      # pyupgrade
    "SIM",     # flake8-simplify
    "PERF",    # perflint
    "RUF",     # ruff-specific
]

FIX_CATEGORIES = {
    "imports": ["I", "F401"],
    "formatting": ["E", "W"],
    "pyupgrade": ["UP"],
    "simplify": ["SIM"],
    "security": ["S"],
    "all": RUFF_FIXABLE_RULES,
}


@dataclass
class FixResult:
    category: str
    rule: str
    file_path: str
    line: int
    description: str
    action: str


@dataclass
class AutoFixReport:
    timestamp: str
    duration_seconds: float
    total_fixes: int
    fixes_by_category: dict[str, int] = field(default_factory=dict)
    fixes_by_file: dict[str, int] = field(default_factory=dict)
    remaining_issues: int = 0
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 2),
            "total_fixes": total_fixes,
            "fixes_by_category": self.fixes_by_category,
            "fixes_by_file": self.fixes_by_file,
            "remaining_issues": self.remaining_issues,
        }


def run_command(
    args: list[str],
    cwd: Path = PROJECT_ROOT,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def get_affected_files(path: str) -> list[Path]:
    target = PROJECT_ROOT / path
    if target.is_file():
        return [target]
    if target.is_dir():
        return list(target.rglob("*.py"))
    return list(PROJECT_ROOT.rglob("*.py"))


def run_ruff_check(path: str, select: list[str] | None = None) -> str:
    cmd = ["ruff", "check", path]
    if select:
        cmd.extend(["--select", ",".join(select)])
    result = run_command(cmd)
    return result.stdout


def run_ruff_fix(
    path: str,
    select: list[str] | None = None,
    unsafe: bool = False,
) -> tuple[int, str]:
    cmd = ["ruff", "check", path, "--fix"]
    if unsafe:
        cmd.append("--unsafe-fixes")
    if select:
        cmd.extend(["--select", ",".join(select)])

    before = run_ruff_check(path, select)

    result = run_command(cmd)

    after = run_ruff_check(path, select)

    before_count = before.count("\n") if before else 0
    after_count = after.count("\n") if after else 0
    fixes_applied = max(0, before_count - after_count)

    return fixes_applied, result.stdout + result.stderr


def run_ruff_format(path: str) -> tuple[int, str]:
    before = run_command(["ruff", "format", path, "--check"]).stdout

    result = run_command(["ruff", "format", path])

    after = run_command(["ruff", "format", path, "--check"]).stdout

    before_count = before.count("\n") if before else 0
    after_count = after.count("\n") if after else 0
    fixes_applied = max(0, before_count - after_count)

    return fixes_applied, result.stdout + result.stderr


def fix_unused_imports(path: str) -> tuple[int, str]:
    return run_ruff_fix(path, select=["F401"])


def fix_import_sorting(path: str) -> tuple[int, str]:
    return run_ruff_fix(path, select=["I"])


def fix_pyupgrade(path: str) -> tuple[int, str]:
    return run_ruff_fix(path, select=["UP"])


def fix_simplify(path: str) -> tuple[int, str]:
    return run_ruff_fix(path, select=["SIM"], unsafe=True)


def fix_formatting(path: str) -> tuple[int, str]:
    return run_ruff_format(path)


def auto_fix_category(category: str, path: str) -> tuple[int, str]:
    handlers = {
        "imports": lambda p: (
            fix_unused_imports(p)[0] + fix_import_sorting(p)[0],
            fix_unused_imports(p)[1] + fix_import_sorting(p)[1],
        ),
        "pyupgrade": fix_pyupgrade,
        "simplify": fix_simplify,
        "formatting": fix_formatting,
        "all": lambda p: run_ruff_fix(p, select=RUFF_FIXABLE_RULES, unsafe=True),
    }

    handler = handlers.get(category)
    if handler:
        return handler(path)
    return 0, f"Unknown category: {category}"


def parse_ruff_output(output: str) -> dict[str, int]:
    rule_counts: dict[str, int] = {}
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        for part in parts:
            if part.startswith("F") or part.startswith("E") or part.startswith("W"):
                rule_counts[part] = rule_counts.get(part, 0) + 1
                break
    return rule_counts


def format_report_text(report: AutoFixReport) -> str:
    lines = [
        f"Auto-Fix Report - {report.timestamp}",
        f"Duration: {report.duration_seconds:.1f}s",
        f"Total fixes applied: {report.total_fixes}",
        "-" * 60,
    ]

    if report.fixes_by_category:
        lines.append("Fixes by category:")
        for cat, count in sorted(report.fixes_by_category.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat:20s} {count}")

    if report.fixes_by_file:
        lines.append("Fixes by file:")
        for f, count in sorted(report.fixes_by_file.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {f:40s} {count}")

    lines.append(f"\nRemaining issues: {report.remaining_issues}")
    lines.append("-" * 60)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto-fix lint and formatting issues")
    parser.add_argument("--check", action="store_true", help="Only check, do not fix")
    parser.add_argument(
        "--only",
        choices=list(FIX_CATEGORIES.keys()),
        default="all",
        help="Fix only specific category",
    )
    parser.add_argument(
        "--path", default="app/", help="Target path (file or directory)"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--unsafe", action="store_true", help="Allow unsafe fixes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.monotonic()

    if args.check:
        output = run_ruff_check(args.path)
        issues = [line for line in output.strip().split("\n") if line]
        print(f"Found {len(issues)} issues (no changes made):")
        for issue in issues[:50]:
            print(f"  {issue}")
        return 0 if not issues else 1

    category = args.only
    fixes_count, output = auto_fix_category(category, args.path)

    duration = time.monotonic() - start
    remaining_output = run_ruff_check(args.path)
    remaining = len([l for l in remaining_output.strip().split("\n") if l])

    report = AutoFixReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_seconds=duration,
        total_fixes=fixes_count,
        fixes_by_category={category: fixes_count},
        remaining_issues=remaining,
        raw_output=output,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report_text(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
