"""Flow system — event-driven multi-agent orchestration (CrewAI style).

Decorators define execution flow:
- @start(): entry points, multiple run in parallel
- @listen(method): triggers when method completes
- @router(method): returns string label for conditional branching
- and_(), or_(): combine multiple listeners
"""

from __future__ import annotations

import asyncio
import inspect
import uuid
from collections.abc import Callable
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.core.agent_engine import AgentEngine
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry

logger = structlog.get_logger()


class FlowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowState(BaseModel):
    """Type-safe state shared across flow methods."""
    flow_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    results: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Decorator markers ──

def start() -> Callable:
    """Mark a method as a flow entry point."""
    def decorator(func: Callable) -> Callable:
        func._flow_start = True  # type: ignore[attr-defined]
        return func
    return decorator


def listen(*methods: str | Callable) -> Callable:
    """Mark a method to trigger when specified methods complete."""
    method_names = []
    for m in methods:
        if callable(m) and hasattr(m, '__name__'):
            method_names.append(m.__name__)
        elif isinstance(m, str):
            method_names.append(m)

    def decorator(func: Callable) -> Callable:
        func._flow_listens = method_names  # type: ignore[attr-defined]
        func._flow_trigger = "all"  # type: ignore[attr-defined]
        return func
    return decorator


def listen_or(*methods: str | Callable) -> Callable:
    """Listen to multiple methods, fire when ANY completes."""
    method_names = []
    for m in methods:
        if callable(m) and hasattr(m, '__name__'):
            method_names.append(m.__name__)
        elif isinstance(m, str):
            method_names.append(m)

    def decorator(func: Callable) -> Callable:
        func._flow_listens = method_names  # type: ignore[attr-defined]
        func._flow_trigger = "any"  # type: ignore[attr-defined]
        return func
    return decorator


def router(*methods: str | Callable) -> Callable:
    """Mark a method as a conditional router.

    The decorated method must return a string label.
    Methods decorated with @listen(label) will match that label.
    """
    method_names = []
    for m in methods:
        if callable(m) and hasattr(m, '__name__'):
            method_names.append(m.__name__)
        elif isinstance(m, str):
            method_names.append(m)

    def decorator(func: Callable) -> Callable:
        func._flow_router_for = method_names  # type: ignore[attr-defined]
        func._flow_returns_routes = True  # type: ignore[attr-defined]
        return func
    return decorator


def listen_route(router_method: Callable, route_label: str) -> Callable:
    """Listen to a router method for a specific route label."""
    def decorator(func: Callable) -> Callable:
        func._flow_listens = [router_method.__name__]  # type: ignore[attr-defined]
        func._flow_route_label = route_label  # type: ignore[attr-defined]
        func._flow_trigger = "route"  # type: ignore[attr-defined]
        return func
    return decorator


# ── Flow executor ──


class FlowExecutor:
    """Executes Flow classes by analyzing decorators and running methods."""

    def __init__(
        self,
        agent_engine: AgentEngine,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
    ):
        self.agent_engine = agent_engine
        self.model_registry = model_registry
        self.tool_registry = tool_registry

    async def execute(
        self,
        flow_instance: Any,
        initial_state: dict[str, Any] | None = None,
    ) -> FlowState:
        """Execute a flow instance."""
        state = FlowState()
        if initial_state:
            for k, v in initial_state.items():
                setattr(state, k, v)

        state.flow_id = state.flow_id or str(uuid.uuid4())[:8]

        # Discover methods
        methods = self._discover_methods(flow_instance)
        completed: set[str] = set()
        failed: set[str] = set()
        running_tasks: dict[str, asyncio.Task] = {}

        # Start methods run first
        start_methods = methods.get("start", [])
        for name, method in start_methods:
            task = asyncio.create_task(self._run_method(method, state, flow_instance))
            running_tasks[name] = task

        # Main execution loop
        while running_tasks:
            done, _ = await asyncio.wait(
                running_tasks.values(),
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                # Find method name for this task
                method_name = None
                for name, t in running_tasks.items():
                    if t is task:
                        method_name = name
                        break

                if method_name is None:
                    continue

                del running_tasks[method_name]

                try:
                    result = task.completed_result() if hasattr(task, 'completed_result') else task.result()
                    if isinstance(task.result(), Exception):
                        raise task.result()
                    completed.add(method_name)
                    state.results[method_name] = result
                except Exception as e:
                    failed.add(method_name)
                    state.errors[method_name] = str(e)
                    logger.error("Flow method failed", method=method_name, error=str(e))

                # Find triggered methods
                triggered = self._find_triggered_methods(
                    methods, completed, failed, state, running_tasks,
                )
                for name, method in triggered:
                    if name not in running_tasks and name not in completed:
                        task = asyncio.create_task(
                            self._run_method(method, state, flow_instance),
                        )
                        running_tasks[name] = task

        # Determine final status
        if failed:
            logger.warning("Flow completed with errors", flow_id=state.flow_id, errors=list(failed))
        else:
            logger.info("Flow completed", flow_id=state.flow_id, methods=list(completed))

        return state

    async def _run_method(
        self,
        method: Callable,
        state: FlowState,
        instance: Any,
    ) -> Any:
        """Run a single flow method."""
        # method is already a bound method (from getattr), so just pass state
        result = method(state)
        if inspect.isawaitable(result):
            return await result
        return result

    def _discover_methods(self, instance: Any) -> dict[str, list[tuple[str, Callable]]]:
        """Categorize methods by their flow role."""
        methods: dict[str, list[tuple[str, Callable]]] = {
            "start": [],
            "listen": [],
            "router": [],
            "listen_route": [],
        }

        for name in dir(instance):
            if name.startswith("_"):
                continue
            attr = getattr(instance, name, None)
            if not callable(attr):
                continue

            is_start = getattr(attr, '_flow_start', False)
            listens = getattr(attr, '_flow_listens', None)
            is_router = getattr(attr, '_flow_returns_routes', False)
            route_label = getattr(attr, '_flow_route_label', None)
            trigger = getattr(attr, '_flow_trigger', 'all')

            if is_start:
                methods["start"].append((name, attr))
            elif is_router:
                methods["router"].append((name, attr))
            elif route_label is not None:
                methods["listen_route"].append((name, attr, route_label))
            elif listens:
                methods["listen"].append((name, attr, trigger))

        return methods

    def _find_triggered_methods(
        self,
        methods: dict,
        completed: set[str],
        failed: set[str],
        state: FlowState,
        running: dict[str, asyncio.Task],
    ) -> list[tuple[str, Callable]]:
        """Find methods that should run now."""
        triggered: list[tuple[str, Callable]] = []

        # Check router methods (listen to their deps like "all" trigger)
        for entry in methods.get("router", []):
            name, method = entry
            listens = getattr(method, '_flow_router_for', [])
            if name in completed or name in running:
                continue
            if all(m in completed for m in listens):
                triggered.append((name, method))

        # Check listen methods
        for entry in methods.get("listen", []):
            name, method, trigger = entry
            listens = getattr(method, '_flow_listens', [])
            if name in completed or name in running:
                continue

            if trigger == "any":
                if any(m in completed for m in listens):
                    triggered.append((name, method))
            else:  # "all"
                if all(m in completed for m in listens):
                    triggered.append((name, method))

        # Check listen_route methods
        for entry in methods.get("listen_route", []):
            name, method, route_label = entry
            listens = getattr(method, '_flow_listens', [])
            if name in completed or name in running:
                continue

            router_method_name = listens[0] if listens else None
            if router_method_name and router_method_name in completed:
                router_result = state.results.get(router_method_name, "")
                if router_result == route_label:
                    triggered.append((name, method))

        return triggered
