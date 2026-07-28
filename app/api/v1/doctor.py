"""Diagnostic endpoint mirroring climber-doctor.py."""

from __future__ import annotations

import asyncio
import platform
import sys

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _run_diagnostics() -> dict:
    from app.config import settings
    from app.storage import db_health
    from app.storage.cache import get_redis
    from app.core.memory_guardian import get_memory_guardian
    from app.core.watchdog import get_watchdog
    from app.tools.browser_pool import get_browser_pool

    sections: list[dict] = []

    # Python runtime
    py = {"section": "python_runtime", "checks": []}
    py["checks"].append({"name": "python_version", "ok": sys.version_info >= (3, 11), "detail": sys.version.split()[0]})
    sections.append(py)

    # Dependencies
    deps = {"section": "core_dependencies", "checks": []}
    for mod in ("fastapi", "sqlalchemy", "aiosqlite", "structlog", "pydantic", "pydantic_settings"):
        try:
            m = __import__(mod)
            deps["checks"].append({"name": mod, "ok": True, "detail": getattr(m, "__version__", "installed")})
        except Exception as exc:
            deps["checks"].append({"name": mod, "ok": False, "detail": str(exc)})
    sections.append(deps)

    # Database
    db = {"section": "database", "checks": []}
    try:
        check = db_health()
        db["checks"].append({"name": "connected", "ok": check.get("connected", False), "detail": check.get("backend", "unknown")})
        if check.get("backend") == "sqlite":
            db["checks"].append({"name": "wal_mode", "ok": str(check.get("journal_mode", "")).lower() == "wal", "detail": str(check.get("journal_mode"))})
    except Exception as exc:
        db["checks"].append({"name": "database_reachable", "ok": False, "detail": str(exc)})
    sections.append(db)

    # Services
    svc = {"section": "services", "checks": []}
    try:
        redis = get_redis()
        svc["checks"].append({"name": "redis", "ok": redis is not None, "detail": "connected" if redis else "disabled"})
    except Exception as exc:
        svc["checks"].append({"name": "redis", "ok": False, "detail": str(exc)})
    try:
        svc["checks"].append({"name": "watchdog", "ok": get_watchdog().health().get("healthy", False), "detail": "running"})
    except Exception as exc:
        svc["checks"].append({"name": "watchdog", "ok": False, "detail": str(exc)})
    try:
        svc["checks"].append({"name": "memory_guardian", "ok": True, "detail": f"soft={get_memory_guardian().stats().get('soft_threshold')}, hard={get_memory_guardian().stats().get('hard_threshold')}"})
    except Exception as exc:
        svc["checks"].append({"name": "memory_guardian", "ok": False, "detail": str(exc)})
    try:
        svc["checks"].append({"name": "browser_pool", "ok": True, "detail": str(get_browser_pool().stats())})
    except Exception as exc:
        svc["checks"].append({"name": "browser_pool", "ok": False, "detail": str(exc)})
    sections.append(svc)

    # Workspace
    ws = {"section": "workspace", "checks": []}
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    for rel in ("logs", "skills", "data", "workspace"):
        p = root / rel
        ws["checks"].append({"name": f"dir_{rel}", "ok": p.exists(), "detail": str(p)})
    sections.append(ws)

    healthy = all(c["ok"] for s in sections for c in s["checks"])
    return {"version": "0.1.0", "platform": {"system": platform.system(), "python": sys.version.split()[0]}, "sections": sections, "healthy": healthy}


@router.get("/")
@router.get("")
async def doctor() -> JSONResponse:
    try:
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, _run_diagnostics)
    except RuntimeError:
        report = _run_diagnostics()
    status = 200 if report["healthy"] else 503
    return JSONResponse(report, status_code=status)
