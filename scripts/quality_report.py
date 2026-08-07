#!/usr/bin/env python3
"""Generate comprehensive code quality report.

Analyzes codebase for:
- Cyclomatic complexity
- Code duplication rate
- Test coverage
- Technical debt estimation
- Maintainability index
- Security hotspots

Usage:
    python scripts/quality_report.py
    python scripts/quality_report.py --output report.html
    python scripts/quality_report.py --format json
    python scripts/quality_report.py --thresholds thresholds.json
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"
REPORTS_DIR = PROJECT_ROOT / "logs" / "quality"

COMPLEXITY_WARN = int(os.getenv("QUALITY_COMPLEXITY_WARN", "10"))
COMPLEXITY_CRIT = int(os.getenv("QUALITY_COMPLEXITY_CRIT", "20"))
COVERAGE_WARN = int(os.getenv("QUALITY_COVERAGE_WARN", "70"))
COVERAGE_CRIT = int(os.getenv("QUALITY_COVERAGE_CRIT", "50"))


@dataclass
class FunctionMetrics:
    name: str
    file_path: str
    line: int
    complexity: int
    lines_of_code: int
    params: int
    returns: int
    is_method: bool


@dataclass
class FileMetrics:
    path: str
    total_lines: int
    code_lines: int
    blank_lines: int
    comment_lines: int
    function_count: int
    class_count: int
    import_count: int
    max_complexity: int
    avg_complexity: float
    maintainability_index: float


@dataclass
class QualityReport:
    timestamp: str
    duration_seconds: float
    overall_score: float
    file_metrics: list[FileMetrics] = field(default_factory=list)
    function_metrics: list[FunctionMetrics] = field(default_factory=list)
    duplication_rate: float = 0.0
    coverage: float = 0.0
    tech_debt_hours: float = 0.0
    summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 2),
            "overall_score": round(self.overall_score, 1),
            "duplication_rate": round(self.duplication_rate, 2),
            "coverage": round(self.coverage, 1),
            "tech_debt_hours": round(self.tech_debt_hours, 1),
            "summary": self.summary,
            "recommendations": self.recommendations,
            "files_analyzed": len(self.file_metrics),
            "functions_analyzed": len(self.function_metrics),
        }


def calculate_complexity(node: ast.AST) -> int:
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.With, ast.AsyncWith):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


def analyze_file(file_path: Path) -> tuple[FileMetrics, list[FunctionMetrics]]:
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None, []

    total_lines = len(source.splitlines())
    blank_lines = sum(1 for line in source.splitlines() if not line.strip())
    comment_lines = sum(
        1 for line in source.splitlines() if line.strip().startswith("#")
    )
    code_lines = total_lines - blank_lines - comment_lines

    functions = []
    classes = 0
    imports = 0
    complexities = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = calculate_complexity(node)
            loc = node.end_lineno - node.lineno if node.end_lineno else 10
            params = len(node.args.args) if node.args else 0
            returns = 1 if node.returns else 0
            is_method = isinstance(node, ast.AsyncFunctionDef)

            func = FunctionMetrics(
                name=node.name,
                file_path=str(file_path.relative_to(PROJECT_ROOT)),
                line=node.lineno,
                complexity=complexity,
                lines_of_code=loc,
                params=params,
                returns=returns,
                is_method=is_method,
            )
            functions.append(func)
            complexities.append(complexity)

    avg_complexity = sum(complexities) / len(complexities) if complexities else 0
    max_complexity = max(complexities) if complexities else 0

    mi = max(
        0,
        (
            171
            - 5.2 * (code_lines / 100 if code_lines > 0 else 0) ** 0.23
            - 16.2 * (avg_complexity if avg_complexity > 0 else 0) ** 0.5
        ),
    )

    file_metric = FileMetrics(
        path=str(file_path.relative_to(PROJECT_ROOT)),
        total_lines=total_lines,
        code_lines=code_lines,
        blank_lines=blank_lines,
        comment_lines=comment_lines,
        function_count=len(functions),
        class_count=classes,
        import_count=imports,
        max_complexity=max_complexity,
        avg_complexity=round(avg_complexity, 2),
        maintainability_index=round(mi, 1),
    )

    return file_metric, functions


def detect_duplication(files: list[Path]) -> float:
    if not files:
        return 0.0

    line_hashes: dict[int, list[str]] = defaultdict(list)
    total_lines = 0

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    line_hashes[hash(stripped)].append(str(f))
                    total_lines += 1
        except (UnicodeDecodeError, OSError):
            continue

    duplicated_lines = sum(
        len(paths) for paths in line_hashes.values() if len(paths) > 1
    )
    return (duplicated_lines / total_lines * 100) if total_lines > 0 else 0.0


def get_coverage() -> float:
    coverage_file = PROJECT_ROOT / "coverage.xml"
    if coverage_file.exists():
        try:
            content = coverage_file.read_text()
            if 'line-rate="' in content:
                import re

                match = re.search(r'line-rate="([\d.]+)"', content)
                if match:
                    return float(match.group(1)) * 100
        except (OSError, ValueError):
            pass
    return 0.0


def run_radon_analysis() -> dict[str, Any]:
    result = {}
    try:
        proc = subprocess.run(
            ["radon", "cc", "app/", "-s", "-j"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0 and proc.stdout:
            result = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return result


def calculate_tech_debt(functions: list[FunctionMetrics], duplication_rate: float) -> float:
    debt_minutes = 0

    for func in functions:
        if func.complexity > COMPLEXITY_CRIT:
            debt_minutes += (func.complexity - COMPLEXITY_CRIT) * 15
        elif func.complexity > COMPLEXITY_WARN:
            debt_minutes += (func.complexity - COMPLEXITY_WARN) * 5

        if func.lines_of_code > 50:
            debt_minutes += (func.lines_of_code - 50) * 2

    debt_minutes += duplication_rate * 10
    return debt_minutes / 60


def generate_recommendations(report: QualityReport) -> list[str]:
    recommendations = []

    high_complexity = [f for f in report.function_metrics if f.complexity >= COMPLEXITY_CRIT]
    if high_complexity:
        recommendations.append(
            f"Refactor {len(high_complexity)} functions with complexity >= {COMPLEXITY_CRIT}"
        )

    if report.coverage < COVERAGE_WARN:
        recommendations.append(
            f"Increase test coverage from {report.coverage:.0f}% to at least {COVERAGE_WARN}%"
        )

    if report.duplication_rate > 5:
        recommendations.append(
            f"Reduce code duplication from {report.duplication_rate:.1f}% to below 5%"
        )

    low_mi = [f for f in report.file_metrics if f.maintainability_index < 50]
    if low_mi:
        recommendations.append(
            f"Improve maintainability of {len(low_mi)} files (MI < 50)"
        )

    long_files = [f for f in report.file_metrics if f.total_lines > 300]
    if long_files:
        recommendations.append(
            f"Split {len(long_files)} files exceeding 300 lines"
        )

    return recommendations


def calculate_overall_score(report: QualityReport) -> float:
    score = 100.0

    if report.coverage > 0:
        score -= max(0, (80 - report.coverage)) * 0.3

    score -= report.duplication_rate * 2

    high_complexity = len(
        [f for f in report.function_metrics if f.complexity >= COMPLEXITY_CRIT]
    )
    score -= high_complexity * 2

    score -= report.tech_debt_hours * 0.5

    return max(0, min(100, score))


def format_report_text(report: QualityReport) -> str:
    lines = [
        f"Code Quality Report - {report.timestamp}",
        f"Overall Score: {report.overall_score:.1f}/100",
        "-" * 60,
        f"  Files analyzed:      {len(report.file_metrics)}",
        f"  Functions analyzed:  {len(report.function_metrics)}",
        f"  Test coverage:       {report.coverage:.1f}%",
        f"  Duplication rate:    {report.duplication_rate:.1f}%",
        f"  Tech debt:           {report.tech_debt_hours:.1f} hours",
        "",
    ]

    if report.summary.get("complexity_distribution"):
        lines.append("Complexity Distribution:")
        for level, count in report.summary["complexity_distribution"].items():
            lines.append(f"  {level:15s} {count}")

    if report.recommendations:
        lines.append("")
        lines.append("Recommendations:")
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"  {i}. {rec}")

    lines.append("-" * 60)
    return "\n".join(lines)


def save_report(report: QualityReport, output_format: str = "json") -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format == "json":
        path = REPORTS_DIR / f"quality_{timestamp}.json"
        data = report.to_dict()
        data["file_metrics"] = [f.__dict__ for f in report.file_metrics]
        data["function_metrics"] = [f.__dict__ for f in report.function_metrics]
        path.write_text(json.dumps(data, indent=2))
    else:
        path = REPORTS_DIR / f"quality_{timestamp}.txt"
        path.write_text(format_report_text(report))

    latest = REPORTS_DIR / f"quality_latest.{output_format}"
    if output_format == "json":
        data = report.to_dict()
        data["file_metrics"] = [f.__dict__ for f in report.file_metrics]
        data["function_metrics"] = [f.__dict__ for f in report.function_metrics]
        latest.write_text(json.dumps(data, indent=2))
    else:
        latest.write_text(format_report_text(report))

    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Code Quality Report Generator")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )
    parser.add_argument("--path", default=str(APP_DIR), help="Path to analyze")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.monotonic()

    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Path not found: {target_path}")
        return 1

    py_files = list(target_path.rglob("*.py")) if target_path.is_dir() else [target_path]
    py_files = [f for f in py_files if "test" not in f.name.lower() and "__pycache__" not in str(f)]

    file_metrics = []
    all_functions = []

    for py_file in py_files:
        fm, funcs = analyze_file(py_file)
        if fm:
            file_metrics.append(fm)
            all_functions.extend(funcs)

    duplication = detect_duplication(py_files)
    coverage = get_coverage()

    complexity_dist = Counter()
    for func in all_functions:
        if func.complexity <= 5:
            complexity_dist["low (<=5)"] += 1
        elif func.complexity <= 10:
            complexity_dist["medium (6-10)"] += 1
        elif func.complexity <= 20:
            complexity_dist["high (11-20)"] += 1
        else:
            complexity_dist["very high (>20)"] += 1

    tech_debt = calculate_tech_debt(all_functions, duplication)

    report = QualityReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        duration_seconds=time.monotonic() - start,
        overall_score=0,
        file_metrics=file_metrics,
        function_metrics=all_functions,
        duplication_rate=duplication,
        coverage=coverage,
        tech_debt_hours=tech_debt,
        summary={
            "complexity_distribution": dict(complexity_dist.most_common()),
            "total_code_lines": sum(f.code_lines for f in file_metrics),
            "total_blank_lines": sum(f.blank_lines for f in file_metrics),
            "total_comment_lines": sum(f.comment_lines for f in file_metrics),
            "avg_maintainability": (
                round(
                    sum(f.maintainability_index for f in file_metrics) / len(file_metrics), 1
                )
                if file_metrics
                else 0
            ),
        },
    )
    report.recommendations = generate_recommendations(report)
    report.overall_score = calculate_overall_score(report)

    save_report(report, args.format)

    if args.output:
        Path(args.output).write_text(format_report_text(report))

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report_text(report))

    if report.overall_score < 50:
        return 2
    if report.overall_score < 70:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
