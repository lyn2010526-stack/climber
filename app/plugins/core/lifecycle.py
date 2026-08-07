"""Plugin lifecycle management.

Manages the state transitions and lifecycle operations for plugins,
including initialization, activation, pausing, and shutdown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.plugins.core.base import (
    PluginContext,
    PluginError,
    PluginInterface,
    PluginManifest,
    PluginNotFoundError,
    PluginState,
    PluginStateError,
)
from app.plugins.core.registry import PluginRegistry, get_registry

logger = logging.getLogger(__name__)


class LifecycleState(StrEnum):
    """Extended lifecycle states for detailed tracking."""

    CREATED = "created"
    VALIDATING = "validating"
    VALIDATED = "validated"
    RESOLVING_DEPENDENCIES = "resolving_dependencies"
    DEPENDENCIES_RESOLVED = "dependencies_resolved"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    ACTIVATING = "activating"
    ACTIVE = "active"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class LifecycleEvent:
    """Record of a lifecycle state transition."""

    plugin_name: str
    from_state: LifecycleState
    to_state: LifecycleState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None
    duration_ms: float | None = None


@dataclass
class LifecycleStats:
    """Statistics for plugin lifecycle operations."""

    total_initializations: int = 0
    total_activations: int = 0
    total_pauses: int = 0
    total_shutdowns: int = 0
    total_errors: int = 0
    avg_init_duration_ms: float = 0.0
    avg_activate_duration_ms: float = 0.0


class LifecycleManager:
    """Manages plugin lifecycle transitions.

    Orchestrates the full lifecycle of plugins from registration
    through shutdown, tracking state transitions and timing.
    """

    def __init__(self, registry: PluginRegistry | None = None) -> None:
        self._registry = registry or get_registry()
        self._lifecycle_states: dict[str, LifecycleState] = {}
        self._contexts: dict[str, PluginContext] = {}
        self._events: list[LifecycleEvent] = []
        self._stats = LifecycleStats()

    @property
    def stats(self) -> LifecycleStats:
        """Get lifecycle statistics."""
        return self._stats

    @property
    def events(self) -> list[LifecycleEvent]:
        """Get all recorded lifecycle events."""
        return list(self._events)

    def get_lifecycle_state(self, name: str) -> LifecycleState:
        """Get the current lifecycle state of a plugin.

        Args:
            name: Plugin name.

        Returns:
            Current lifecycle state.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._lifecycle_states:
            raise PluginNotFoundError(name)
        return self._lifecycle_states[name]

    def get_context(self, name: str) -> PluginContext:
        """Get the plugin context.

        Args:
            name: Plugin name.

        Returns:
            Plugin context.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._contexts:
            raise PluginNotFoundError(name)
        return self._contexts[name]

    async def initialize(
        self,
        name: str,
        config: dict[str, Any] | None = None,
        services: dict[str, Any] | None = None,
    ) -> PluginContext:
        """Initialize a plugin.

        Args:
            name: Plugin name.
            config: Plugin configuration.
            services: Shared services.

        Returns:
            The initialized plugin context.

        Raises:
            PluginNotFoundError: If plugin not found.
            PluginStateError: If plugin is not in valid state.
            PluginError: If initialization fails.
        """
        plugin = self._registry.get(name)
        manifest = self._registry.get_manifest(name)
        current = self._lifecycle_states.get(name, LifecycleState.CREATED)

        if current not in (LifecycleState.CREATED, LifecycleState.VALIDATED):
            raise PluginStateError(name, PluginState(current), PluginState.REGISTERED)

        start = datetime.utcnow()
        self._transition(name, LifecycleState.INITIALIZING)

        context = PluginContext(
            config=config or {},
            services=services or {},
            state=PluginState.INITIALIZING,
        )

        try:
            await plugin.initialize(context)
            context.state = PluginState.ACTIVE
            self._registry.set_state(name, PluginState.ACTIVE)
            self._contexts[name] = context

            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self._transition(name, LifecycleState.INITIALIZED)
            self._transition(name, LifecycleState.ACTIVATING)
            self._transition(name, LifecycleState.ACTIVE)

            self._stats.total_initializations += 1
            self._update_avg_init(duration)

            logger.info("Plugin initialized: %s (%.1fms)", name, duration)
            return context

        except Exception as e:
            context.state = PluginState.ERROR
            context.error_message = str(e)
            self._transition(name, LifecycleState.ERROR, error=str(e))
            self._stats.total_errors += 1
            raise PluginError(f"Initialization failed: {e}", name, e) from e

    async def activate(self, name: str) -> None:
        """Activate a paused plugin.

        Args:
            name: Plugin name.

        Raises:
            PluginNotFoundError: If plugin not found.
            PluginStateError: If plugin is not paused.
        """
        plugin = self._registry.get(name)
        current = self._lifecycle_states.get(name)

        if current != LifecycleState.PAUSED:
            raise PluginStateError(name, PluginState(current or "registered"), PluginState.PAUSED)

        start = datetime.utcnow()
        self._transition(name, LifecycleState.RESUMING)

        try:
            await plugin.activate()
            self._registry.set_state(name, PluginState.ACTIVE)
            if name in self._contexts:
                self._contexts[name].state = PluginState.ACTIVE

            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self._transition(name, LifecycleState.ACTIVE)

            self._stats.total_activations += 1
            self._update_avg_activate(duration)

            logger.info("Plugin activated: %s (%.1fms)", name, duration)

        except Exception as e:
            self._transition(name, LifecycleState.ERROR, error=str(e))
            self._stats.total_errors += 1
            raise PluginError(f"Activation failed: {e}", name, e) from e

    async def deactivate(self, name: str) -> None:
        """Deactivate a plugin temporarily.

        Args:
            name: Plugin name.

        Raises:
            PluginNotFoundError: If plugin not found.
            PluginStateError: If plugin is not active.
        """
        plugin = self._registry.get(name)
        current = self._lifecycle_states.get(name)

        if current != LifecycleState.ACTIVE:
            raise PluginStateError(name, PluginState(current or "registered"), PluginState.ACTIVE)

        self._transition(name, LifecycleState.PAUSING)

        try:
            await plugin.deactivate()
            self._registry.set_state(name, PluginState.PAUSED)
            if name in self._contexts:
                self._contexts[name].state = PluginState.PAUSED

            self._transition(name, LifecycleState.PAUSED)
            self._stats.total_pauses += 1

            logger.info("Plugin deactivated: %s", name)

        except Exception as e:
            self._transition(name, LifecycleState.ERROR, error=str(e))
            self._stats.total_errors += 1
            raise PluginError(f"Deactivation failed: {e}", name, e) from e

    async def shutdown(self, name: str) -> None:
        """Shutdown a plugin and release resources.

        Args:
            name: Plugin name.

        Raises:
            PluginNotFoundError: If plugin not found.
        """
        plugin = self._registry.get(name)
        current = self._lifecycle_states.get(name)

        if current == LifecycleState.STOPPED:
            return

        self._transition(name, LifecycleState.STOPPING)

        try:
            await plugin.shutdown()
            self._registry.set_state(name, PluginState.STOPPED)
            if name in self._contexts:
                self._contexts[name].state = PluginState.STOPPED

            self._transition(name, LifecycleState.STOPPED)
            self._stats.total_shutdowns += 1

            logger.info("Plugin shutdown: %s", name)

        except Exception as e:
            self._registry.set_state(name, PluginState.ERROR)
            self._transition(name, LifecycleState.ERROR, error=str(e))
            self._stats.total_errors += 1
            logger.error("Plugin shutdown error [%s]: %s", name, e)

    async def shutdown_all(self) -> None:
        """Shutdown all plugins in dependency order."""
        order = self._registry.resolve_startup_order()
        for name in reversed(order):
            if self._lifecycle_states.get(name) not in (
                LifecycleState.STOPPED,
                LifecycleState.CREATED,
            ):
                await self.shutdown(name)

    async def health_check(self, name: str) -> dict[str, Any]:
        """Perform health check on a plugin.

        Args:
            name: Plugin name.

        Returns:
            Health status dictionary.
        """
        plugin = self._registry.get(name)
        return await plugin.health_check()

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """Perform health check on all active plugins.

        Returns:
            Dictionary mapping plugin names to health status.
        """
        results: dict[str, dict[str, Any]] = {}
        for name in self._registry.list_plugins(state=PluginState.ACTIVE):
            try:
                results[name] = await self.health_check(name)
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
        return results

    def get_events(self, name: str | None = None) -> list[LifecycleEvent]:
        """Get lifecycle events.

        Args:
            name: Filter by plugin name.

        Returns:
            List of lifecycle events.
        """
        if name is None:
            return list(self._events)
        return [e for e in self._events if e.plugin_name == name]

    def _transition(
        self,
        name: str,
        to_state: LifecycleState,
        error: str | None = None,
    ) -> None:
        """Record a lifecycle state transition."""
        from_state = self._lifecycle_states.get(name, LifecycleState.CREATED)
        self._lifecycle_states[name] = to_state

        event = LifecycleEvent(
            plugin_name=name,
            from_state=from_state,
            to_state=to_state,
            error=error,
        )
        self._events.append(event)

    def _update_avg_init(self, duration: float) -> None:
        """Update average initialization duration."""
        n = self._stats.total_initializations
        self._stats.avg_init_duration_ms = (
            (self._stats.avg_init_duration_ms * (n - 1) + duration) / n
        )

    def _update_avg_activate(self, duration: float) -> None:
        """Update average activation duration."""
        n = self._stats.total_activations
        self._stats.avg_activate_duration_ms = (
            (self._stats.avg_activate_duration_ms * (n - 1) + duration) / n
        )


__all__ = [
    "LifecycleManager",
    "LifecycleState",
    "LifecycleEvent",
    "LifecycleStats",
]
