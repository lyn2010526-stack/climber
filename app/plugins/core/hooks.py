"""Plugin hook system.

Provides a mechanism for plugins to register hooks that are called
at specific points in the application lifecycle, enabling extensibility
without modifying core code.
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar, overload

from app.plugins.core.base import PluginError

logger = logging.getLogger(__name__)

T = TypeVar("T")
HookCallback = Callable[..., Coroutine[Any, Any, Any] | Any]


@dataclass
class HookRegistration:
    """Registration record for a hook callback."""

    callback: HookCallback
    plugin_name: str
    priority: int = 0
    once: bool = False
    registered_at: datetime = field(default_factory=datetime.utcnow)
    call_count: int = 0
    total_duration_ms: float = 0.0


@dataclass
class HookResult:
    """Result of executing a hook."""

    hook_name: str
    results: list[Any] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    total_duration_ms: float = 0.0

    @property
    def success(self) -> bool:
        """Check if hook execution had no errors."""
        return len(self.errors) == 0

    @property
    def has_results(self) -> bool:
        """Check if any results were produced."""
        return len(self.results) > 0


class HookManager:
    """Manages plugin hook registration and execution.

    Supports priority ordering, one-time hooks, error isolation,
    and both sync and async callbacks.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookRegistration]] = defaultdict(list)
        self._global_middleware: list[HookCallback] = []

    @property
    def hook_names(self) -> list[str]:
        """Get all registered hook names."""
        return list(self._hooks.keys())

    @property
    def hook_count(self) -> int:
        """Get total number of registered hook callbacks."""
        return sum(len(regs) for regs in self._hooks.values())

    def register(
        self,
        hook_name: str,
        callback: HookCallback,
        plugin_name: str = "",
        priority: int = 0,
        once: bool = False,
    ) -> None:
        """Register a hook callback.

        Args:
            hook_name: Name of the hook point.
            callback: Function to call when hook is triggered.
            plugin_name: Name of the registering plugin.
            priority: Execution priority (higher = earlier).
            once: If True, callback is removed after first call.
        """
        if not callable(callback):
            raise PluginError(f"Hook callback must be callable, got {type(callback)}")

        registration = HookRegistration(
            callback=callback,
            plugin_name=plugin_name,
            priority=priority,
            once=once,
        )

        self._hooks[hook_name].append(registration)
        self._hooks[hook_name].sort(key=lambda r: r.priority, reverse=True)

        logger.debug(
            "Hook registered: %s (plugin=%s, priority=%d, once=%s)",
            hook_name,
            plugin_name,
            priority,
            once,
        )

    def unregister(
        self,
        hook_name: str,
        callback: HookCallback | None = None,
        plugin_name: str | None = None,
    ) -> int:
        """Unregister hook callbacks.

        Args:
            hook_name: Name of the hook point.
            callback: Specific callback to remove.
            plugin_name: Remove all callbacks from this plugin.

        Returns:
            Number of callbacks removed.
        """
        if hook_name not in self._hooks:
            return 0

        original_count = len(self._hooks[hook_name])

        if callback is not None:
            self._hooks[hook_name] = [
                r for r in self._hooks[hook_name] if r.callback != callback
            ]
        elif plugin_name is not None:
            self._hooks[hook_name] = [
                r for r in self._hooks[hook_name] if r.plugin_name != plugin_name
            ]

        removed = original_count - len(self._hooks[hook_name])

        if not self._hooks[hook_name]:
            del self._hooks[hook_name]

        return removed

    def unregister_all(self, plugin_name: str) -> int:
        """Unregister all hooks from a plugin.

        Args:
            plugin_name: Plugin name.

        Returns:
            Total number of callbacks removed.
        """
        total = 0
        for hook_name in list(self._hooks.keys()):
            total += self.unregister(hook_name, plugin_name=plugin_name)
        return total

    async def execute(self, hook_name: str, *args: Any, **kwargs: Any) -> HookResult:
        """Execute all callbacks registered for a hook.

        Args:
            hook_name: Name of the hook to execute.
            *args: Positional arguments to pass to callbacks.
            **kwargs: Keyword arguments to pass to callbacks.

        Returns:
            HookResult containing all results and errors.
        """
        result = HookResult(hook_name=hook_name)
        start = datetime.utcnow()

        registrations = list(self._hooks.get(hook_name, []))
        to_remove: list[HookRegistration] = []

        for reg in registrations:
            try:
                if inspect.iscoroutinefunction(reg.callback):
                    callback_result = await reg.callback(*args, **kwargs)
                else:
                    callback_result = reg.callback(*args, **kwargs)

                result.results.append(callback_result)
                reg.call_count += 1

            except Exception as e:
                error_msg = str(e)
                result.errors.append((reg.plugin_name or "unknown", error_msg))
                logger.warning(
                    "Hook error [%s] from %s: %s",
                    hook_name,
                    reg.plugin_name,
                    error_msg,
                )

            if reg.once:
                to_remove.append(reg)

        for reg in to_remove:
            self._hooks[hook_name].remove(reg)
            if not self._hooks[hook_name]:
                del self._hooks[hook_name]

        result.total_duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return result

    async def execute_filter(
        self,
        hook_name: str,
        initial_value: T,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute hooks as a filter chain.

        Each callback receives the result of the previous callback,
        enabling data transformation pipelines.

        Args:
            hook_name: Name of the hook.
            initial_value: Starting value to pass through the chain.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The final transformed value.
        """
        value = initial_value
        registrations = list(self._hooks.get(hook_name, []))

        for reg in registrations:
            try:
                if inspect.iscoroutinefunction(reg.callback):
                    value = await reg.callback(value, *args, **kwargs)
                else:
                    value = reg.callback(value, *args, **kwargs)
            except Exception as e:
                logger.warning(
                    "Filter hook error [%s] from %s: %s",
                    hook_name,
                    reg.plugin_name,
                    e,
                )

        return value

    async def execute_until(
        self,
        hook_name: str,
        predicate: Callable[[Any], bool],
        *args: Any,
        **kwargs: Any,
    ) -> HookResult:
        """Execute hooks until a condition is met.

        Args:
            hook_name: Name of the hook.
            predicate: Function that returns True to stop execution.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            HookResult with results up to the stopping point.
        """
        result = HookResult(hook_name=hook_name)
        start = datetime.utcnow()

        for reg in self._hooks.get(hook_name, []):
            try:
                if inspect.iscoroutinefunction(reg.callback):
                    callback_result = await reg.callback(*args, **kwargs)
                else:
                    callback_result = reg.callback(*args, **kwargs)

                result.results.append(callback_result)

                if predicate(callback_result):
                    break

            except Exception as e:
                result.errors.append((reg.plugin_name or "unknown", str(e)))

        result.total_duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return result

    def has_hooks(self, hook_name: str) -> bool:
        """Check if any callbacks are registered for a hook.

        Args:
            hook_name: Name of the hook.

        Returns:
            True if callbacks are registered.
        """
        return hook_name in self._hooks and len(self._hooks[hook_name]) > 0

    def get_registrations(self, hook_name: str) -> list[HookRegistration]:
        """Get all registrations for a hook.

        Args:
            hook_name: Name of the hook.

        Returns:
            List of hook registrations.
        """
        return list(self._hooks.get(hook_name, []))

    def clear(self) -> None:
        """Clear all registered hooks."""
        self._hooks.clear()
        self._global_middleware.clear()


def hook(hook_name: str, priority: int = 0, once: bool = False) -> Callable[[HookCallback], HookCallback]:
    """Decorator to register a function as a hook callback.

    Args:
        hook_name: Name of the hook point.
        priority: Execution priority (higher = earlier).
        once: If True, callback is removed after first call.

    Returns:
        Decorator function.

    Example:
        @hook("before_request", priority=10)
        async def log_request(request):
            print(f"Request: {request}")
    """
    def decorator(func: HookCallback) -> HookCallback:
        func._hook_metadata = {  # type: ignore[attr-defined]
            "hook_name": hook_name,
            "priority": priority,
            "once": once,
        }
        return func
    return decorator


def before(hook_name: str, priority: int = 10) -> Callable[[HookCallback], HookCallback]:
    """Decorator to register a 'before' hook.

    Args:
        hook_name: Name of the target hook point.
        priority: Execution priority.

    Returns:
        Decorator function.
    """
    return hook(f"before_{hook_name}", priority=priority)


def after(hook_name: str, priority: int = 10) -> Callable[[HookCallback], HookCallback]:
    """Decorator to register an 'after' hook.

    Args:
        hook_name: Name of the target hook point.
        priority: Execution priority.

    Returns:
        Decorator function.
    """
    return hook(f"after_{hook_name}", priority=priority)


_hook_manager: HookManager | None = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance.

    Returns:
        The global HookManager singleton.
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def reset_hook_manager() -> None:
    """Reset the global hook manager (for testing)."""
    global _hook_manager
    _hook_manager = None


__all__ = [
    "HookManager",
    "HookRegistration",
    "HookResult",
    "hook",
    "before",
    "after",
    "get_hook_manager",
    "reset_hook_manager",
]
