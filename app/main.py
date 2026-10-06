"""FastAPI application entry point with production lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_router
from app.config import settings
from app.core.di import ScopeContext
from app.core.di import register as di_register
from app.core.di import resolve as di_resolve
from app.core.error_handlers import register_exception_handlers
from app.core.interfaces import IExecutor, IModelAdapter, ISkillRegistry, IToolRegistry
from app.core.logging_setup import configure_logging, get_recent_logs
from app.core.memory_guardian import get_memory_guardian
from app.core.observability.api import router as observability_router
from app.core.watchdog import get_watchdog
from app.middleware.auth import AuthMiddleware
from app.middleware.metrics import APP_INFO, MetricsMiddleware, metrics_endpoint
from app.middleware.security import (
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)
from app.storage import db_health, init_db
from app.storage.cache import close_redis, get_redis
from app.tools import register_builtins

logger = structlog.get_logger()

_missing = []
for name in ("playwright", "chromadb", "psutil"):
    if importlib.util.find_spec(name) is None:
        print(f"ERROR: Missing required dependency {name}, run scripts/init-env.sh")
        _missing.append(name)
del importlib, _missing

_APP_VERSION = "0.2.0"

FRONTEND_DIR = Path(__file__).parent.parent / "frontend-react" / "dist"

STATIC_AUTH_DIR = Path(__file__).parent / "static" / "auth"


def _register_core_services() -> None:
    from app.core.agent_engine import AgentEngine
    from app.core.auto_loop import AutoLoopEngine
    from app.core.executor import (
        CrewExecutorAdapter,
        SkillComposerExecutorAdapter,
        UnifiedExecutor,
        WorkflowExecutorAdapter,
    )
    from app.core.sandbox import SandboxConfig, SandboxExecutor
    from app.core.skill_composition import SkillComposer
    from app.models.registry import ModelRegistry
    from app.multi_agent.crew import Crew
    from app.skills.definitions import register_builtin_skills
    from app.skills.registry import LegacySkillRegistry, SkillRegistry
    from app.tools import tool_registry as global_tool_registry
    from app.tools.mcp_client import MCPRegistry
    from app.workflow.engine import WorkflowEngine

    model_registry = ModelRegistry()
    skill_registry = SkillRegistry()
    try:
        register_builtin_skills(skill_registry)
    except Exception as exc:
        logger.warning("Builtin skill registration failed", error=str(exc))
    tool_registry_instance = global_tool_registry
    mcp_registry_instance = MCPRegistry()
    sandbox = SandboxExecutor(SandboxConfig())
    agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry_instance)
    auto_loop_engine = AutoLoopEngine()

    di_register(IModelAdapter, model_registry)
    di_register(IToolRegistry, tool_registry_instance)
    di_register(ISkillRegistry, LegacySkillRegistry(skill_registry))
    di_register("ModelRegistry", model_registry)
    di_register("ToolRegistry", tool_registry_instance)
    di_register("SkillRegistry", skill_registry)
    di_register("MCPRegistry", mcp_registry_instance)
    di_register("SandboxExecutor", sandbox)
    di_register("AgentEngine", agent_engine)
    di_register("AutoLoopEngine", auto_loop_engine)

    workflow_engine = WorkflowEngine(engine=agent_engine, model_registry=model_registry)
    skill_composer = SkillComposer(skill_registry=skill_registry)
    unified = UnifiedExecutor()
    unified.register_adapter("workflow", WorkflowExecutorAdapter(workflow_engine))
    unified.register_adapter("crew", CrewExecutorAdapter(Crew([], [], agent_engine)))
    unified.register_adapter("skill", SkillComposerExecutorAdapter(skill_composer))
    di_register(IExecutor, unified)
    di_register("UnifiedExecutor", unified)
    di_register("SkillComposer", skill_composer)


def _local_ip() -> str:
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


SHUTDOWN_STEP_TIMEOUT = 10.0


async def _run_cleanup_step(name: str, coro) -> None:
    """Run one teardown step with a hard timeout and failure isolation.

    A hanging or raising teardown coroutine must never block or abort the
    remaining teardown steps, so each step is individually timed and guarded.
    """
    try:
        await asyncio.wait_for(coro, timeout=SHUTDOWN_STEP_TIMEOUT)
    except TimeoutError:
        logger.warning("lifecycle_teardown_timeout", step=name)
    except Exception as exc:
        logger.warning("lifecycle_teardown_failed", step=name, error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_dir = configure_logging(settings.app_log_level)
    logger.info(
        "Agent Engine starting",
        debug=settings.app_debug,
        version=_APP_VERSION,
        log_dir=str(log_dir),
    )

    with ScopeContext("app_lifespan"):
        _register_core_services()

        cleanups: list[tuple[str, Callable[[], Any]]] = []

        def defer(name: str, coro_factory: Callable[[], Any]) -> None:
            """Register a teardown step to run in reverse order."""
            cleanups.append((name, coro_factory))

        try:
            await init_db()
            health = await db_health()
            logger.info(
                "Database ready",
                backend=health.get("backend"),
                journal_mode=health.get("journal_mode"),
            )

            from app.core.auth_manager import initialize_auth_system

            admin_creds = await initialize_auth_system()
            if admin_creds:
                logger.info(
                    "Auth system initialized",
                    admin_username=admin_creds["username"],
                    admin_password_set=True,
                    bootstrap_password_generated=admin_creds.get("bootstrap_generated", False),
                )

            redis = await get_redis()
            if redis:
                logger.info("Redis cache connected")
            else:
                logger.info("Redis unavailable, using in-process cache")
            defer("redis", close_redis)

            register_builtins()

            auto_loop_engine = di_resolve("AutoLoopEngine")
            _wire_auto_loop_runner(auto_loop_engine)
            recovered = await auto_loop_engine.recover_interrupted_sessions()
            if recovered:
                logger.info("Recovered interrupted sessions", count=recovered)
            # R12-H42: teardown must cancel and await the auto-loop monitor and
            # every running task so CANCELLED status is persisted on shutdown.
            defer("auto_loop", auto_loop_engine.stop)

            watchdog = get_watchdog()
            watchdog.register("auto_loop", auto_loop_engine.run_forever)
            await watchdog.start()
            defer("watchdog", watchdog.stop)
            logger.info("Watchdog started")

            guardian = get_memory_guardian()

            async def _relieve_memory() -> None:
                from app.tools.browser_pool import get_browser_pool

                reclaimed = await get_browser_pool().reclaim_idle()
                logger.info("memory_relief_applied", browser_sessions_reclaimed=reclaimed)

            guardian.register_relief(_relieve_memory)

            async def _evict_caches() -> None:
                try:
                    from app.skills.memory_manager import persistent_memory

                    cleared = persistent_memory.clear()
                    logger.info(
                        "memory_relief_caches_evicted", cache="persistent_memory", entries=cleared
                    )
                except Exception as exc:
                    logger.warning(
                        "memory_relief_cache_evict_failed",
                        cache="persistent_memory",
                        error=str(exc),
                    )
                try:
                    di_resolve("AgentEngine").tool_prioritizer.clear_caches()
                    logger.info("memory_relief_caches_evicted", cache="tool_prioritizer")
                except Exception as exc:
                    logger.warning(
                        "memory_relief_cache_evict_failed", cache="tool_prioritizer", error=str(exc)
                    )

            guardian.register_relief(_evict_caches)
            await guardian.start()
            defer("memory_guardian", guardian.stop)

            try:
                from app.tools.browser_pool import get_browser_pool

                pool = get_browser_pool()
                defer("browser_pool", pool.close_all)
            except Exception as exc:
                logger.warning("browser_pool_teardown_setup_failed", error=str(exc))

            try:
                from app.services.telegram_bot import configure_bot, start_telegram_bot

                model_registry = di_resolve("ModelRegistry")
                tool_registry = di_resolve("ToolRegistry")
                configure_bot(model_registry, tool_registry)
                telegram_started = await start_telegram_bot()
                if telegram_started:
                    logger.info("Telegram remote control enabled")
                    from app.services.telegram_bot import stop_telegram_bot

                    defer("telegram_bot", stop_telegram_bot)
            except Exception as e:
                logger.warning("Telegram bot startup skipped", error=str(e))

            from app.services.notifications import notification_service

            app.state.notification_service = notification_service

            from app.core.execution.event_bus import get_task_event_bus

            event_bus = get_task_event_bus()
            di_register("EventBus", event_bus)
            app.state.event_bus = event_bus
            defer("event_bus", event_bus.close)

            # R12-H43: teardown must drain tracked background work (task worker
            # runs plus engine fire-and-forget spawns) before closing the DB.
            # Registered last-to-run-first so drain precedes engine dispose.
            defer("db_engine", _dispose_db_engine)
            defer("background_tasks", _drain_background_tasks)

            APP_INFO.info({"version": _APP_VERSION, "debug": str(settings.app_debug)})

            if settings.enable_lan_access:
                logger.info("LAN access enabled", url=f"http://{_local_ip()}:{settings.port}")
        except Exception:
            logger.error(
                "startup failed, rolling back started services in reverse order", exc_info=True
            )
            for name, coro_factory in reversed(cleanups):
                await _run_cleanup_step(name, coro_factory())
            raise

        try:
            yield
        finally:
            for name, coro_factory in reversed(cleanups):
                await _run_cleanup_step(name, coro_factory())
            from app.models.anthropic_adapter import AnthropicAdapter
            from app.models.openai_adapter import OpenAIAdapter

            await _run_cleanup_step("openai_adapter_client", OpenAIAdapter.close_client())
            await _run_cleanup_step("anthropic_adapter_client", AnthropicAdapter.close_client())
            logger.info("Agent Engine shutting down")


async def _drain_background_tasks() -> None:
    """Wait for tracked background work to settle before closing resources.

    Covers the task worker's active runs and the agent engine's fire-and-forget
    spawns (notifications, memory reflection, evolution ticks). A bounded timeout
    keeps shutdown fast even when a handler hangs.
    """
    pending: list[asyncio.Task] = []
    with contextlib.suppress(Exception):
        from app.core.task_worker import task_manager

        pending.extend(task_manager._active_tasks.values())
    with contextlib.suppress(Exception):
        agent_engine = di_resolve("AgentEngine")
        pending.extend(agent_engine._background_tasks)
    if not pending:
        return
    logger.info("main.draining_background_tasks", count=len(pending))
    done, _ = await asyncio.wait(pending, timeout=SHUTDOWN_STEP_TIMEOUT)
    for task in done:
        if not task.cancelled() and task.exception() is not None:
            logger.warning("main.background_task_failed", error=str(task.exception()))


async def _dispose_db_engine() -> None:
    """Release the SQLAlchemy engine's connection pool."""
    try:
        from app.storage import engine as _db_engine

        await _db_engine.dispose()
    except Exception as exc:
        logger.warning("main.db_engine_dispose_failed", error=str(exc))


def _wire_auto_loop_runner(auto_loop_engine) -> None:
    """Wire owner-configured agent execution and persist reported progress."""
    from app.core.auto_loop import AutoLoopRecord
    from app.core.task_worker import handle_agent_run, resolve_owner_agent_payload

    async def autonomous_runner(record: AutoLoopRecord) -> None:
        payload = await resolve_owner_agent_payload(record.owner_id)

        async def on_progress(step: int, total: int, message: str = "") -> None:
            import time

            from app.core.auto_loop import AutoLoopTaskStatus

            record.current_step = step
            record.heartbeat_at = time.time()
            await auto_loop_engine._persist_status(record, AutoLoopTaskStatus.RUNNING)

        result = await handle_agent_run(
            payload={
                **payload,
                "objective": record.objective,
                "max_steps": record.max_steps,
            },
            on_progress=on_progress,
        )
        record.result = result

    auto_loop_engine.register_runner("autonomous", autonomous_runner)


app = FastAPI(
    title="Agent Engine",
    description="Production-grade AI Agent Platform",
    version=_APP_VERSION,
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RateLimitMiddleware, trusted_proxies=settings.trusted_proxies_list)
app.add_middleware(AuthMiddleware, public_endpoints=set(settings.auth_public_endpoints))
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Cache-Control",
        "X-Request-Id",
    ],
)

app.include_router(api_router, prefix="/api/v1")

app.include_router(observability_router)

register_exception_handlers(app)


def create_app() -> FastAPI:
    """Create a FastAPI application instance.

    The application is a module-level singleton; this factory exists so
    tests and tooling can obtain the configured app through a stable API.
    """
    return app


@app.get("/health")
async def health() -> dict:
    checks: dict = {"status": "ok", "version": _APP_VERSION}
    try:
        checks["database"] = await db_health()
    except Exception as e:
        checks["database"] = {"connected": False, "error": str(e)}
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "disabled"
    except Exception:
        checks["redis"] = "unavailable"
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.vector_store_path)
        client.heartbeat()
        checks["chroma"] = "ok"
    except Exception:
        checks["chroma"] = "unavailable"
    try:
        checks["watchdog"] = get_watchdog().health()
    except Exception as e:
        checks["watchdog"] = {"error": str(e)}
    try:
        checks["memory"] = get_memory_guardian().stats()
    except Exception as e:
        checks["memory"] = {"error": str(e)}
    try:
        from app.tools.browser_pool import get_browser_pool

        checks["browser_pool"] = get_browser_pool().stats()
    except Exception as e:
        checks["browser_pool"] = {"error": str(e)}

    degraded = (
        not checks.get("database", {}).get("connected", False)
        or not checks.get("database", {}).get("schema_ready", True)
        or not checks.get("watchdog", {}).get("healthy", True)
    )
    checks["status"] = "degraded" if degraded else "ok"
    if degraded:
        return JSONResponse(status_code=503, content=checks)
    return checks


@app.get("/health/logs")
async def health_logs(lines: int = 200, errors_only: bool = False) -> dict:
    return {
        "lines": get_recent_logs(lines=min(lines, 2000), error_only=errors_only),
        "log_dir": settings.log_dir,
    }


@app.get("/metrics")
async def metrics():
    return await metrics_endpoint()


# Serve auth static files
auth_static_path = Path(__file__).parent / "static" / "auth"
if auth_static_path.exists():
    app.mount("/auth", StaticFiles(directory=str(auth_static_path), html=True), name="auth")
if FRONTEND_DIR.exists():
    frontend_index = FRONTEND_DIR / "index.html"
    if not frontend_index.is_file():
        raise RuntimeError(f"Static frontend deployment is incomplete: missing {frontend_index}")
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(frontend_index)

    @app.middleware("http")
    async def spa_fallback_middleware(request: Request, call_next):
        # SPA fallback: only intercept responses where the request was NOT
        # routed to a registered endpoint (i.e. a 404) and the path is not a
        # backend/API path. Registered routes, including dynamically added
        # ones, always take precedence.
        response = await call_next(request)
        if response.status_code == 404:
            path = request.url.path
            if (
                path.startswith(("/api/", "/docs", "/_test/"))
                or path == "/openapi.json"
                or path == "/health"
            ):
                return response
            file_path = (FRONTEND_DIR / path.lstrip("/")).resolve()
            if file_path.is_relative_to(FRONTEND_DIR.resolve()) and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_index)
        return response
else:

    @app.get("/")
    async def redirect_to_frontend():
        return JSONResponse(
            {
                "message": "Climber Agent Engine API",
                "frontend": "http://localhost:5173",
                "docs": "/docs",
                "health": "/health",
            }
        )
