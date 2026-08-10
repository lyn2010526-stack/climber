"""Diagnostic endpoint mirroring climber-doctor.py."""

from __future__ import annotations

import platform
import sys

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _check_python_runtime() -> dict:
    return {
        "section": "python_runtime",
        "checks": [
            {"name": "python_version", "ok": sys.version_info >= (3, 11), "detail": sys.version.split()[0]},
        ],
    }


def _check_dependencies() -> dict:
    checks = []
    for mod in ("fastapi", "sqlalchemy", "aiosqlite", "structlog", "pydantic", "pydantic_settings"):
        try:
            m = __import__(mod)
            checks.append({"name": mod, "ok": True, "detail": getattr(m, "__version__", "installed")})
        except Exception as exc:
            checks.append({"name": mod, "ok": False, "detail": str(exc)})
    return {"section": "core_dependencies", "checks": checks}


def _check_workspace() -> dict:
    from app.config import BASE_DIR

    root = BASE_DIR
    checks = []
    for rel in ("logs", "skills", "data", "workspace"):
        p = root / rel
        ok = p.exists()
        detail = str(p)
        if not ok:
            try:
                p.mkdir(parents=True, exist_ok=True)
                ok = True
            except OSError as exc:
                detail = f"{p}: {exc}"
        checks.append({"name": f"dir_{rel}", "ok": ok, "detail": detail})
    return {"section": "workspace", "checks": checks}


def _check_services_sync() -> dict:
    from app.core.memory_guardian import get_memory_guardian
    from app.core.watchdog import get_watchdog
    from app.tools.browser_pool import get_browser_pool

    checks = []
    try:
        checks.append({"name": "watchdog", "ok": get_watchdog().health().get("healthy", False), "detail": "running"})
    except Exception as exc:
        checks.append({"name": "watchdog", "ok": False, "detail": str(exc)})
    try:
        checks.append({"name": "memory_guardian", "ok": True, "detail": f"soft={get_memory_guardian().stats().get('soft_threshold')}, hard={get_memory_guardian().stats().get('hard_threshold')}"})
    except Exception as exc:
        checks.append({"name": "memory_guardian", "ok": False, "detail": str(exc)})
    try:
        checks.append({"name": "browser_pool", "ok": True, "detail": str(get_browser_pool().stats())})
    except Exception as exc:
        checks.append({"name": "browser_pool", "ok": False, "detail": str(exc)})
    return {"section": "services", "checks": checks}


async def _check_database() -> dict:
    from app.storage import db_health

    checks = []
    try:
        check = await db_health()
        checks.append({"name": "connected", "ok": check.get("connected", False), "detail": check.get("backend", "unknown")})
        if check.get("backend") == "sqlite":
            checks.append({"name": "wal_mode", "ok": str(check.get("journal_mode", "")).lower() == "wal", "detail": str(check.get("journal_mode"))})
    except Exception as exc:
        checks.append({"name": "database_reachable", "ok": False, "detail": str(exc)})
    return {"section": "database", "checks": checks}


async def _check_redis() -> dict:
    from app.storage.cache import get_redis

    checks = []
    try:
        redis = await get_redis()
        checks.append({"name": "redis", "ok": redis is not None, "detail": "connected" if redis else "disabled"})
    except Exception as exc:
        checks.append({"name": "redis", "ok": False, "detail": str(exc)})
    return {"section": "services", "checks": checks}


async def _run_diagnostics() -> dict:
    sections = [
        _check_python_runtime(),
        _check_dependencies(),
    ]

    sections.append(await _check_database())

    svc = _check_services_sync()
    svc["checks"].extend((await _check_redis())["checks"])
    sections.append(svc)

    sections.append(_check_workspace())

    healthy = all(c["ok"] for s in sections for c in s["checks"])
    return {
        "version": "0.1.0",
        "platform": {"system": platform.system(), "python": sys.version.split()[0]},
        "sections": sections,
        "healthy": healthy,
    }


@router.get("/")
@router.get("")
async def doctor() -> JSONResponse:
    report = await _run_diagnostics()
    status = 200 if report["healthy"] else 503
    return JSONResponse(report, status_code=status)
