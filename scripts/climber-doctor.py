#!/usr/bin/env python3
"""Climber doctor: one-shot environment diagnostics.

Usage:
    python scripts/climber-doctor.py           # text report
    python scripts/climber-doctor.py --html    # HTML report
    python scripts/climber-doctor.py --json    # machine-readable
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

REPORT_VERSION = "0.1.0"


def _section(title: str) -> dict[str, Any]:
    return {"section": title, "checks": []}


def check(container: dict[str, Any], name: str, ok: bool, detail: str = "") -> None:
    container["checks"].append({"name": name, "ok": ok, "detail": detail})


def run_diagnostics() -> dict[str, Any]:
    report: dict[str, Any] = {
        "version": REPORT_VERSION,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": sys.version.split()[0],
        },
        "sections": [],
    }

    # ── Python runtime ──────────────────────────────────────────────────────
    py = _section("python_runtime")
    check(py, "python_version", sys.version_info >= (3, 11), f"{sys.version.split()[0]} {'OK' if sys.version_info >= (3, 11) else 'need 3.11+'}")
    report["sections"].append(py)

    # ── Core dependencies ───────────────────────────────────────────────────
    deps = _section("core_dependencies")
    for mod in ("fastapi", "sqlalchemy", "aiosqlite", "structlog", "pydantic", "pydantic_settings"):
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "unknown")
            check(deps, mod, True, ver)
        except Exception as exc:
            check(deps, mod, False, str(exc))
    for mod in ("playwright", "chromadb", "psutil", "telegram"):
        try:
            __import__(mod)
            check(deps, mod, True, "installed")
        except Exception:
            check(deps, mod, False, "missing (optional)")
    report["sections"].append(deps)

    # ── Database ─────────────────────────────────────────────────────────────
    db = _section("database")
    try:
        from app.config import settings
        from app.storage import db_health

        check(db, "database_url_configured", bool(settings.database_url), settings.database_url)
        import asyncio
        health = asyncio.run(db_health())
        check(db, "database_connected", health.get("connected", False), health.get("backend", "unknown"))
        if health.get("backend") == "sqlite":
            check(db, "wal_mode", str(health.get("journal_mode", "")).lower() == "wal", str(health.get("journal_mode")))
    except Exception as exc:
        check(db, "database_reachable", False, str(exc))
    report["sections"].append(db)

    # ── Workspace layout ─────────────────────────────────────────────────────
    layout = _section("workspace_layout")
    root = Path(__file__).resolve().parent.parent
    for rel in ("logs", "skills", "data", "workspace"):
        p = root / rel
        exists = p.exists()
        check(layout, f"dir_{rel}", exists, str(p))
    report["sections"].append(layout)

    healthy = all(c["ok"] for s in report["sections"] for c in s["checks"])
    report["healthy"] = healthy
    return report


def render_text(report: dict[str, Any]) -> str:
    lines = [f"Climber doctor v{report['version']}", "=" * 40]
    for section in report["sections"]:
        lines.append(f"\n[{section['section']}]")
        for c in section["checks"]:
            mark = "OK" if c["ok"] else "FAIL"
            lines.append(f"  [{mark}] {c['name']}: {c['detail']}")
    lines.append(f"\nOverall: {'HEALTHY' if report['healthy'] else 'UNHEALTHY'}")
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    rows = []
    for section in report["sections"]:
        for c in section["checks"]:
            color = "#15803d" if c["ok"] else "#b91c1c"
            mark = "OK" if c["ok"] else "FAIL"
            rows.append(f"<tr><td>{section['section']}</td><td>{c['name']}</td><td style='color:{color}'>{mark}</td><td>{c['detail']}</td></tr>")
    return f"""<!doctype html>
<html><head><title>Climber doctor</title><style>body{{font-family:sans-serif;margin:2rem}}table{{border-collapse:collapse}}th,td{{border:1px solid #ccc;padding:.5rem 1rem}}</style></head>
<body><h1>Climber doctor v{report['version']}</h1>
<p>Overall: <strong style='color:#15803d'>{'HEALTHY' if report['healthy'] else 'UNHEALTHY'}</strong></p>
<table><tr><th>Section</th><th>Check</th><th>Status</th><th>Detail</th></tr>{''.join(rows)}</table></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Climber doctor diagnostics")
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_diagnostics()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.html:
        print(render_html(report))
    else:
        print(render_text(report))
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
