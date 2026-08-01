"""FastAPI application entry point with production lifecycle."""

from __future__ import annotations

import importlib.util
import asyncio
import structlog
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_router
from app.config import settings
from app.core.di import register as di_register, resolve as di_resolve, ScopeContext
from app.core.logging_setup import configure_logging, get_recent_logs, write_crash_dump
from app.core.memory_guardian import get_memory_guardian
from app.core.watchdog import get_watchdog
from app.core.interfaces import IModelAdapter, IToolRegistry, ISkillRegistry, IExecutor
from app.middleware.metrics import MetricsMiddleware, metrics_endpoint, APP_INFO
from app.middleware.security import SecurityHeadersMiddleware, RequestValidationMiddleware
from app.storage import db_health, init_db
from app.storage.cache import get_redis, close_redis
from app.tools import register_builtins

logger = structlog.get_logger()

_missing = []
for name in ('playwright', 'chromadb', 'psutil'):
    if importlib.util.find_spec(name) is None:
        print(f"ERROR: Missing required dependency {name}, run scripts/init-env.sh")
        _missing.append(name)
del importlib, _missing

_APP_VERSION = "0.2.0"

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def _register_core_services() -> None:
    from app.core.agent_engine import AgentEngine
    from app.core.auto_loop import AutoLoopEngine
    from app.core.scheduler import TaskScheduler
    from app.core.skill_composition import SkillComposer
    from app.models.registry import ModelRegistry
    from app.models.openai_adapter import OpenAIAdapter
    from app.models.anthropic_adapter import AnthropicAdapter
    from app.skills.registry import SkillRegistry, LegacySkillRegistry
    from app.tools.mcp_client import MCPRegistry
    from app.tools import tool_registry as global_tool_registry
    from app.core.sandbox import SandboxExecutor, SandboxConfig
    from app.workflow.engine import WorkflowEngine
    from app.multi_agent.crew import Crew
    from app.core.executor import UnifiedExecutor, WorkflowExecutorAdapter, CrewExecutorAdapter, SkillComposerExecutorAdapter

    model_registry = ModelRegistry()
    skill_registry = SkillRegistry()
    tool_registry_instance = global_tool_registry
    mcp_registry_instance = MCPRegistry()
    sandbox = SandboxExecutor(SandboxConfig())
    agent_engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry_instance)
    auto_loop_engine = AutoLoopEngine()
    task_scheduler = TaskScheduler()

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
    di_register("TaskScheduler", task_scheduler)

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_dir = configure_logging(settings.app_log_level)
    logger.info("Agent Engine starting", debug=settings.app_debug, version=_APP_VERSION, log_dir=str(log_dir))

    with ScopeContext("app_lifespan") as scope:
        _register_core_services()

        try:
            await init_db()
            health = await db_health()
            logger.info("Database ready", backend=health.get("backend"), journal_mode=health.get("journal_mode"))
        except Exception as e:
            logger.warning("Database initialization failed", error=str(e))

        redis = await get_redis()
        if redis:
            logger.info("Redis cache connected")
        else:
            logger.info("Redis unavailable, using in-process cache")

        register_builtins()

        auto_loop_engine = di_resolve("AutoLoopEngine")
        recovered = await auto_loop_engine.recover_interrupted_sessions()
        if recovered:
            logger.info("Recovered interrupted sessions", count=recovered)

        task_scheduler = di_resolve("TaskScheduler")
        watchdog = get_watchdog()
        watchdog.register("scheduler", lambda: _run_scheduler(task_scheduler))
        watchdog.register("auto_loop", auto_loop_engine.start)
        await watchdog.start()
        logger.info("Task scheduler started under watchdog")

        guardian = get_memory_guardian()

        async def _relieve_memory() -> None:
            from app.tools.browser_pool import get_browser_pool
            reclaimed = await get_browser_pool().reclaim_idle()
            logger.info("memory_relief_applied", browser_sessions_reclaimed=reclaimed)

        guardian.register_relief(_relieve_memory)
        await guardian.start()

        try:
            from app.services.telegram_bot import start_telegram_bot, configure_bot
            model_registry = di_resolve("ModelRegistry")
            tool_registry = di_resolve("ToolRegistry")
            configure_bot(model_registry, tool_registry)
            telegram_started = await start_telegram_bot()
            if telegram_started:
                logger.info("Telegram remote control enabled")
        except Exception as e:
            logger.warning("Telegram bot startup skipped", error=str(e))

        from app.services.notifications import notification_service
        app.state.notification_service = notification_service

        APP_INFO.info({"version": _APP_VERSION, "debug": str(settings.app_debug)})

        if settings.enable_lan_access:
            logger.info("LAN access enabled", url=f"http://{_local_ip()}:{settings.port}")

        yield

        await watchdog.stop()
        await guardian.stop()
        try:
            from app.tools.browser_pool import get_browser_pool
            await get_browser_pool().close_all()
        except Exception as e:
            logger.warning("Browser pool teardown failed", error=str(e))
        try:
            from app.services.telegram_bot import stop_telegram_bot
            await stop_telegram_bot()
        except Exception as exc:
            logger.warning("main.telegram_bot_stop_failed", error=str(exc))
        await close_redis()
        from app.models.openai_adapter import OpenAIAdapter
        from app.models.anthropic_adapter import AnthropicAdapter
        await OpenAIAdapter.close_client()
        await AnthropicAdapter.close_client()
        logger.info("Agent Engine shutting down")


async def _run_scheduler(scheduler):
    while True:
        await scheduler.run_pending()
        await asyncio.sleep(30)


app = FastAPI(
    title="Agent Engine",
    description="Production-grade AI Agent Platform",
    version=_APP_VERSION,
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    dump = write_crash_dump(exc, {"path": request.url.path, "method": request.method})
    logger.error("Unhandled exception", error=str(exc), error_type=type(exc).__name__, path=request.url.path, crash_dump=str(dump) if dump else None, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "type": "internal_error", "error": type(exc).__name__, "crash_dump": str(dump) if dump else None})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "type": "http_error"})


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
        or not checks.get("watchdog", {}).get("healthy", True)
    )
    checks["status"] = "degraded" if degraded else "ok"
    return checks


@app.get("/health/logs")
async def health_logs(lines: int = 200, errors_only: bool = False) -> dict:
    return {"lines": get_recent_logs(lines=min(lines, 2000), error_only=errors_only), "log_dir": settings.log_dir}


@app.get("/metrics")
async def metrics():
    return await metrics_endpoint()


if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend_spa(request: Request, full_path: str):
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    async def redirect_to_frontend():
        return JSONResponse({
            "message": "Climber Agent Engine API",
            "frontend": "http://localhost:5173",
            "docs": "/docs",
            "health": "/health"
        })
