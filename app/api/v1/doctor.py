"""Diagnostic endpoint mirroring climber-doctor.py."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

logger = structlog.get_logger(__name__)


def _check_python_runtime() -> dict[str, Any]:
    return {
        "section": "python_runtime",
        "checks": [
            {
                "name": "python_version",
                "ok": sys.version_info >= (3, 11),
                "detail": sys.version.split()[0],
            },
        ],
    }


def _check_dependencies() -> dict[str, Any]:
    checks = []
    for mod in ("fastapi", "sqlalchemy", "aiosqlite", "structlog", "pydantic", "pydantic_settings"):
        try:
            m = __import__(mod)
            checks.append(
                {"name": mod, "ok": True, "detail": getattr(m, "__version__", "installed")}
            )
        except Exception as exc:
            logger.warning("doctor_dependency_check_failed", module=mod, error=str(exc))
            checks.append({"name": mod, "ok": False, "detail": "依赖检查失败"})
    return {"section": "core_dependencies", "checks": checks}


def _check_workspace() -> dict[str, Any]:
    # app/api/v1/doctor.py -> project root is four levels up.
    root = Path(__file__).resolve().parent.parent.parent.parent
    checks = []
    for rel in ("logs", "skills", "data", "workspace"):
        p = root / rel
        checks.append({"name": f"dir_{rel}", "ok": p.exists(), "detail": str(p)})
    return {"section": "workspace", "checks": checks}


def _check_services_sync() -> dict[str, Any]:
    from app.core.memory_guardian import get_memory_guardian
    from app.core.watchdog import get_watchdog
    from app.tools.browser_pool import get_browser_pool

    checks = []
    try:
        checks.append(
            {
                "name": "watchdog",
                "ok": get_watchdog().health().get("healthy", False),
                "detail": "running",
            }
        )
    except Exception as exc:
        logger.warning("doctor_watchdog_check_failed", error=str(exc))
        checks.append({"name": "watchdog", "ok": False, "detail": "watchdog 不可用"})
    try:
        checks.append(
            {
                "name": "memory_guardian",
                "ok": True,
                "detail": f"soft={get_memory_guardian().stats().get('soft_threshold')}, hard={get_memory_guardian().stats().get('hard_threshold')}",
            }
        )
    except Exception as exc:
        logger.warning("doctor_memory_guardian_check_failed", error=str(exc))
        checks.append({"name": "memory_guardian", "ok": False, "detail": "memory guardian 不可用"})
    try:
        checks.append(
            {"name": "browser_pool", "ok": True, "detail": str(get_browser_pool().stats())}
        )
    except Exception as exc:
        logger.warning("doctor_browser_pool_check_failed", error=str(exc))
        checks.append({"name": "browser_pool", "ok": False, "detail": "browser pool 不可用"})
    return {"section": "services", "checks": checks}


async def _check_database() -> dict[str, Any]:
    from app.storage import db_health

    checks = []
    try:
        check = await db_health()
        checks.append(
            {
                "name": "connected",
                "ok": check.get("connected", False),
                "detail": check.get("backend", "unknown"),
            }
        )
        if check.get("backend") == "sqlite":
            checks.append(
                {
                    "name": "wal_mode",
                    "ok": str(check.get("journal_mode", "")).lower() == "wal",
                    "detail": str(check.get("journal_mode")),
                }
            )
    except Exception as exc:
        logger.warning("doctor_database_check_failed", error=str(exc))
        checks.append({"name": "database_reachable", "ok": False, "detail": "数据库不可达"})
    return {"section": "database", "checks": checks}


async def _check_redis() -> dict[str, Any]:
    from app.storage.cache import get_redis

    checks = []
    try:
        redis = await get_redis()
        checks.append(
            {
                "name": "redis",
                "ok": redis is not None,
                "detail": "connected" if redis else "disabled",
            }
        )
    except Exception as exc:
        logger.warning("doctor_redis_check_failed", error=str(exc))
        checks.append({"name": "redis", "ok": False, "detail": "redis 不可用"})
    return {"section": "services", "checks": checks}


async def _run_diagnostics() -> dict[str, Any]:
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
