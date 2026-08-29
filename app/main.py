"""FastAPI application entry point with production lifecycle."""

from __future__ import annotations

import asyncio
import importlib.util
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_router
from app.config import settings
from app.core.di import ScopeContext
from app.core.di import register as di_register
from app.core.di import resolve as di_resolve
from app.core.interfaces import IExecutor, IModelAdapter, ISkillRegistry, IToolRegistry
from app.core.logging_setup import configure_logging, get_recent_logs, write_crash_dump
from app.core.memory_guardian import get_memory_guardian
from app.core.slow_query_logger import install as install_slow_query_logger
from app.core.watchdog import get_watchdog
from app.middleware.metrics import APP_INFO, MetricsMiddleware, metrics_endpoint
from app.middleware.security import (
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)
from app.storage import db_health, init_db
from app.storage.cache import close_redis, get_redis
from app.tools import register_builtins


def _default_workdir() -> str:
    """Resolve the workspace root that the sandbox should confine commands to."""
    return os.environ.get("CLIMBER_SANDBOX_WORKDIR") or os.getcwd()

logger = structlog.get_logger()

_missing = []
for name in ('playwright', 'chromadb', 'psutil'):
    if importlib.util.find_spec(name) is None:
        print(f"ERROR: Missing required dependency {name}, run scripts/init-env.sh")
        _missing.append(name)
del importlib, _missing

_APP_VERSION = "0.2.0"

FRONTEND_DIR = None
for _candidate in (
    Path(__file__).parent.parent / "frontend" / "dist",
    Path(__file__).parent.parent / "frontend-react" / "dist",
):
    if (_candidate / "index.html").is_file():
        FRONTEND_DIR = _candidate
        break
del _candidate


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
    from app.core.scheduler import TaskScheduler
    from app.core.skill_composition import SkillComposer
    from app.models.registry import ModelRegistry
    from app.multi_agent.crew import Crew
    from app.skills.registry import LegacySkillRegistry, SkillRegistry
    from app.tools import tool_registry as global_tool_registry
    from app.tools.mcp_client import MCPRegistry
    from app.workflow.engine import WorkflowEngine

    model_registry = ModelRegistry()
    skill_registry = SkillRegistry()
    tool_registry_instance = global_tool_registry
    mcp_registry_instance = MCPRegistry()
    sandbox = SandboxExecutor(SandboxConfig(workdir=_default_workdir()))
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


def _read_positive_int_env(name: str, default: int) -> int:
    """Read a positive integer env var, falling back to ``default`` on error."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("env.invalid_int", name=name, raw=raw)
        return default
    return value if value > 0 else default


async def _run_cleanup_loop() -> None:
    """Periodically sweep stale Runs and expired raw payloads.

    Kept alive by the watchdog; the outer loop never returns so the sweeper
    survives individual pass failures (each pass is internally isolated).
    """
    import asyncio
    from datetime import UTC, datetime, timedelta

    from app.core.run_cleanup import (
        cleanup_expired_raw_payloads,
        cleanup_stale_runs,
    )
    from app.storage import async_session
    from app.storage.run_store import SQLAlchemyRunStore

    stale_max_age = timedelta(minutes=_read_positive_int_env("RUN_STALE_MAX_AGE_MINUTES", 120))
    interval = timedelta(minutes=_read_positive_int_env("RUN_CLEANUP_INTERVAL_MINUTES", 30))

    while True:
        try:
            store = SQLAlchemyRunStore(session_factory=async_session)
            await cleanup_stale_runs(store, max_age=stale_max_age, now=datetime.now(UTC))
            await cleanup_expired_raw_payloads(store, now=datetime.now(UTC))
        except Exception as exc:
            logger.warning("run_cleanup.pass_failed", error=str(exc), exc_info=True)
        await asyncio.sleep(interval.total_seconds())


def _local_ip() -> str:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        logger.warning("local_ip.udp_lookup_failed", lookup="udp_route", exc_info=True)
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            logger.debug("local_ip.hostname_lookup_failed", lookup="hostname", fallback="127.0.0.1", exc_info=True)
            return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_dir = configure_logging(settings.app_log_level)
    logger.info("Agent Engine starting", debug=settings.app_debug, version=_APP_VERSION, log_dir=str(log_dir))

    with ScopeContext("app_lifespan"):
        _register_core_services()

        try:
            await init_db()
            health = await db_health()
            logger.info("Database ready", backend=health.get("backend"), journal_mode=health.get("journal_mode"))
        except Exception as e:
            logger.warning("Database initialization failed", error=str(e))

        install_slow_query_logger(threshold_ms=int(os.environ.get("SLOW_QUERY_THRESHOLD_MS", "100")))

        redis = await get_redis()
        if redis:
            logger.info("Redis cache connected")
        else:
            logger.info("Redis unavailable, using in-process cache")

        register_builtins()
        main_engine = di_resolve("AgentEngine")
        main_engine.start()
        from app.core.agent_engine import set_main_engine
        set_main_engine(main_engine)

        auto_loop_engine = di_resolve("AutoLoopEngine")
        recovered = await auto_loop_engine.recover_interrupted_sessions()
        if recovered:
            logger.info("Recovered interrupted sessions", count=recovered)

        try:
            from app.core.group_collaboration import group_collaboration_engine

            recovered_group_tasks = await group_collaboration_engine.recover_stale_running_tasks()
            if recovered_group_tasks:
                logger.info("Recovered stale group tasks", count=recovered_group_tasks)
        except Exception as e:
            logger.warning("Group task recovery skipped", error=str(e))

        task_scheduler = di_resolve("TaskScheduler")
        watchdog = get_watchdog()
        watchdog.register("scheduler", lambda: _run_scheduler(task_scheduler))
        watchdog.register("auto_loop", auto_loop_engine.run)
        watchdog.register("run_cleanup", _run_cleanup_loop)
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
            from app.services.telegram_bot import configure_bot, start_telegram_bot
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

        fourth_gen = await _init_fourth_gen()
        if fourth_gen:
            app.state.fourth_gen = fourth_gen
            logger.info("fourth_gen.enabled", modules=[k for k in fourth_gen if k not in ("bus", "registry", "guard")])

        arch_v2 = await _init_arch_v2()
        if arch_v2:
            app.state.arch_v2 = arch_v2
            logger.info("arch_v2.enabled", modules=list(arch_v2.keys()))

        APP_INFO.info({"version": _APP_VERSION, "debug": str(settings.app_debug)})

        if settings.enable_lan_access:
            logger.info("LAN access enabled", url=f"http://{_local_ip()}:{settings.port}")

        yield

        fourth_gen = getattr(app.state, "fourth_gen", None)
        if fourth_gen:
            await _stop_fourth_gen(fourth_gen)

        arch_v2 = getattr(app.state, "arch_v2", None)
        if arch_v2:
            await _stop_arch_v2(arch_v2)

        await watchdog.stop()
        await guardian.stop()
        try:
            from app.core.agent_engine import get_main_engine
            _eng = get_main_engine()
            if _eng:
                await _eng.stop()
        except Exception as exc:
            logger.warning("main.agent_engine_stop_failed", error=str(exc))
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
        from app.models.anthropic_adapter import AnthropicAdapter
        from app.models.openai_adapter import OpenAIAdapter
        await OpenAIAdapter.close_client()
        await AnthropicAdapter.close_client()
        logger.info("Agent Engine shutting down")


async def _run_scheduler(scheduler):
    while True:
        await scheduler.run_pending()
        await asyncio.sleep(30)


async def _init_fourth_gen() -> dict[str, Any] | None:
    """Wire up the fourth-generation emergent modules (master-gated).

    Returns a dict of started module handles (empty/None when the master
    switch is OFF — the system then runs purely in third-gen mode).
    """
    if not settings.enable_fourth_gen:
        # Master switch off → pure third-gen mode, nothing wired.
        return None
    from app.core.emergent.autodiscovery import AutodiscoveryEngine
    from app.core.emergent.goal_centered import GoalCenteredPlanner
    from app.core.emergent.meta_agent import MetaAgent
    from app.core.emergent.snapshot import get_structural_snapshot_manager
    from app.core.emergent.swarm import DEFAULT_BEES, SwarmCoordinator
    from app.core.event_bus import get_event_bus
    from app.core.metacognition.capability_discovery import CapabilityDiscovery
    from app.core.sandbox import default_sandbox
    from app.core.security import get_hard_guard
    from app.core.session_snapshot import session_snapshot_manager

    bus = get_event_bus()
    registry = CapabilityDiscovery()
    guard = get_hard_guard()

    # Register protected components so no module can replace them.
    guard.register_protected("event_bus", bus)
    guard.register_protected("sandbox_executor", default_sandbox)
    guard.register_protected("session_snapshot_manager", session_snapshot_manager)
    guard.register_protected("hard_guard", guard)

    # Wire the structural snapshot manager to dump/restore real state.
    snap_mgr = get_structural_snapshot_manager()
    snap_mgr.registry_dump = lambda: registry.list_capabilities()
    snap_mgr.graph_dump = lambda: {"note": "pregel graph dumps wired in main"}
    snap_mgr.switches_dump = lambda: {
        "enable_fourth_gen": settings.enable_fourth_gen,
        "enable_autodiscovery": settings.enable_autodiscovery,
        "enable_meta_agent": settings.enable_meta_agent,
        "enable_goal_centered": settings.enable_goal_centered,
        "enable_swarm": settings.enable_swarm,
    }

    async def _snap() -> str:
        return await snap_mgr.capture("emergent-change")

    handles: dict[str, Any] = {"bus": bus, "registry": registry, "guard": guard}

    if settings.is_fourth_gen_mod_active("autodiscovery"):
        engine = AutodiscoveryEngine(registry=registry, sandbox=default_sandbox)
        engine.set_event_bus(bus)
        engine.set_snapshot_fn(_snap)
        handles["autodiscovery"] = engine
        logger.info("fourth_gen.autodiscovery_enabled")

    if settings.is_fourth_gen_mod_active("meta_agent"):
        meta = MetaAgent(event_bus=bus, snapshot_fn=_snap)
        await meta.start_monitoring()
        handles["meta_agent"] = meta
        logger.info("fourth_gen.meta_agent_enabled")

    if settings.is_fourth_gen_mod_active("goal_centered"):
        planner = GoalCenteredPlanner(registry=registry, snapshot_fn=_snap)
        handles["goal_centered"] = planner
        logger.info("fourth_gen.goal_centered_enabled")

    if settings.is_fourth_gen_mod_active("swarm"):
        swarm = SwarmCoordinator(event_bus=bus, bees=list(DEFAULT_BEES))
        handles["swarm"] = swarm
        logger.info("fourth_gen.swarm_enabled")

    return handles


async def _stop_fourth_gen(handles: dict[str, Any] | None) -> None:
    """Gracefully stop started fourth-gen modules."""
    if not handles:
        return
    meta = handles.get("meta_agent")
    if meta is not None:
        try:
            await meta.stop_monitoring()
        except Exception as exc:
            logger.warning("fourth_gen.meta_agent_stop_failed", error=str(exc))
    logger.info("fourth_gen.shutdown_complete")


async def _init_arch_v2() -> dict[str, Any] | None:
    """Wire up the architecture-v2 modules (plugin kernel, 4-layer memory,
    capability routing, long-context management, self-learning, trace log,
    skill store, integration). Master-gated by ENABLE_ARCH_V2.

    Returns a dict of started module handles (empty/None when the master
    switch is OFF — the system then runs purely in legacy mode).
    """
    if not settings.enable_arch_v2:
        return None
    from app.core.capability.registry import CapabilityRegistry
    from app.core.four_layer_memory.long_term import LongTermMemory
    from app.core.four_layer_memory.medium_term import MediumTermMemory
    from app.core.four_layer_memory.short_term import ShortTermMemory
    from app.core.long_context.budget import ContextBudgetManager
    from app.core.long_context.prefix_cache import PrefixCache
    from app.core.plugin_kernel import PluginKernel
    from app.core.self_learning.l1_realtime_fix import RealtimeFixer
    from app.core.self_learning.l2_distill import BackgroundDistiller
    from app.core.self_learning.l3_steward import SkillSteward
    from app.core.skill_store.skill_store import SkillStore
    from app.core.trace_log.trace_log import TraceLog

    handles: dict[str, Any] = {}

    trace_dir = str(Path(settings.log_dir) / "trace_log")
    if settings.is_arch_v2_active("trace_log"):
        trace = TraceLog(base_dir=trace_dir)
        handles["trace_log"] = trace
        logger.info("arch_v2.trace_log_enabled", dir=trace_dir)

    skill_store: SkillStore | None = None
    if settings.is_arch_v2_active("skill_store"):
        skill_store = SkillStore(base_dir=str(Path(settings.workspace_dir) / "skills"))
        handles["skill_store"] = skill_store
        logger.info("arch_v2.skill_store_enabled")

    if settings.is_arch_v2_active("plugin_kernel"):
        from app.core.plugin_kernel import get_default_event_bus
        from app.core.plugin_kernel.profiles import ALL_PROFILES, ProfileConfig

        trace = handles.get("trace_log")

        async def _trace_sink(event: dict[str, Any]) -> None:
            await trace.append(
                event.get("type", "event"),
                {k: v for k, v in event.items() if k not in ("id", "type", "ts")},
                event.get("session_id", "default"),
            )

        bus = get_default_event_bus(trace_sink=_trace_sink if trace else None)
        kernel = PluginKernel(event_bus=bus)
        profile_mode = os.environ.get("ARCH_V2_PROFILE", "developer")
        if profile_mode not in ALL_PROFILES:
            profile_mode = "developer"
        profile = ProfileConfig(mode=profile_mode)
        kernel.set_profile(profile)
        handles["plugin_kernel"] = kernel
        handles["event_bus"] = bus
        logger.info(
            "arch_v2.plugin_kernel_enabled",
            profile=profile.mode,
            plugins=profile.all_plugin_ids(),
        )

    if settings.is_arch_v2_active("four_layer_memory"):
        mem_base = str(Path(settings.log_dir) / "memory")
        short_term = ShortTermMemory()
        medium_term = MediumTermMemory()
        long_term = LongTermMemory(base_dir=mem_base)
        handles["memory_short_term"] = short_term
        handles["memory_medium_term"] = medium_term
        handles["memory_long_term"] = long_term
        logger.info("arch_v2.four_layer_memory_enabled")

    if settings.is_arch_v2_active("capability"):
        registry = CapabilityRegistry()
        handles["capability_registry"] = registry
        logger.info("arch_v2.capability_enabled")

    if settings.is_arch_v2_active("self_learning") and skill_store is not None:
        l1 = RealtimeFixer(store=skill_store)
        l2 = BackgroundDistiller(store=skill_store)
        l3 = SkillSteward(store=skill_store)
        handles["self_learning_l1"] = l1
        handles["self_learning_l2"] = l2
        handles["self_learning_l3"] = l3
        logger.info("arch_v2.self_learning_enabled")

    if settings.is_arch_v2_active("long_context"):
        budget = ContextBudgetManager()
        prefix_cache = PrefixCache()
        handles["context_budget"] = budget
        handles["prefix_cache"] = prefix_cache
        logger.info("arch_v2.long_context_enabled")

    if settings.is_arch_v2_active("integration"):
        from app.core.integration.event_sourcing import EventSourcingManager
        from app.core.integration.protocol_router import ProtocolRouter

        es_manager = EventSourcingManager()
        proto_router = ProtocolRouter()
        handles["event_sourcing_manager"] = es_manager
        handles["protocol_router"] = proto_router
        logger.info("arch_v2.integration_enabled")

    return handles


async def _stop_arch_v2(handles: dict[str, Any] | None) -> None:
    """Gracefully shut down started arch-v2 modules."""
    if not handles:
        return
    kernel = handles.get("plugin_kernel")
    if kernel is not None:
        try:
            await kernel.shutdown()
        except Exception as exc:
            logger.warning("arch_v2.plugin_kernel_shutdown_failed", error=str(exc))
    logger.info("arch_v2.shutdown_complete")


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
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    dump = write_crash_dump(exc, {"path": request.url.path, "method": request.method})
    logger.error("Unhandled exception", error=str(exc), error_type=type(exc).__name__, path=request.url.path, crash_dump=str(dump) if dump else None, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "type": "internal_error"})


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
        logger.debug("health.dependency_check_failed", dependency="redis", exc_info=True)
        checks["redis"] = "unavailable"
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.vector_store_path)
        client.heartbeat()
        checks["chroma"] = "ok"
    except Exception:
        logger.debug("health.dependency_check_failed", dependency="chroma", exc_info=True)
        checks["chroma"] = "unavailable"
    try:
        checks["watchdog"] = get_watchdog().health()
    except Exception as e:
        logger.debug("health.dependency_check_failed", dependency="watchdog", exc_info=True)
        checks["watchdog"] = {"error": str(e)}
    try:
        checks["memory"] = get_memory_guardian().stats()
    except Exception as e:
        logger.debug("health.dependency_check_failed", dependency="memory", exc_info=True)
        checks["memory"] = {"error": str(e)}
    try:
        from app.tools.browser_pool import get_browser_pool
        checks["browser_pool"] = get_browser_pool().stats()
    except Exception as e:
        logger.debug("health.browser_pool_check_failed", exc_info=True)
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


if FRONTEND_DIR:
    for _static_dir in ("css", "js", "assets"):
        _static_path = FRONTEND_DIR / _static_dir
        if _static_path.is_dir():
            app.mount(f"/{_static_dir}", StaticFiles(directory=_static_path), name=_static_dir)

    @app.get("/")
    async def serve_frontend():
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
