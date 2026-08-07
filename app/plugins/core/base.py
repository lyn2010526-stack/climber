"""Plugin base classes and interfaces.

Defines the foundational types and protocols for the plugin system,
including plugin manifests, contexts, and the base plugin interface.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class PluginState(StrEnum):
    """Plugin lifecycle states."""

    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


class PluginPriority(StrEnum):
    """Plugin execution priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class PluginManifest:
    """Plugin metadata and configuration.

    Contains all metadata required to identify, load, and manage a plugin.
    """

    name: str
    version: str
    description: str = ""
    author: str = ""
    entry_point: str = ""
    dependencies: list[str] = field(default_factory=list)
    priority: PluginPriority = PluginPriority.NORMAL
    tags: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    min_platform_version: str = "1.0.0"


@dataclass
class PluginContext:
    """Runtime context for plugin execution.

    Provides plugins with access to shared services, configuration,
    and metadata during their lifecycle.
    """

    plugin_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: dict[str, Any] = field(default_factory=dict)
    services: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    state: PluginState = PluginState.REGISTERED
    created_at: datetime = field(default_factory=datetime.utcnow)
    error_message: str | None = None

    def get_service(self, name: str) -> Any:
        """Retrieve a service by name.

        Args:
            name: Service identifier.

        Returns:
            The service instance.

        Raises:
            KeyError: If service is not found.
        """
        if name not in self.services:
            raise KeyError(f"Service '{name}' not found in plugin context")
        return self.services[name]

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value.

        Args:
            key: Metadata key.
            default: Default value if key not found.

        Returns:
            Metadata value or default.
        """
        return self.metadata.get(key, default)


@runtime_checkable
class PluginInterface(Protocol):
    """Protocol defining the plugin interface.

    All plugins must implement these methods to participate in the
    plugin lifecycle and hook system.
    """

    manifest: PluginManifest

    async def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin with the given context.

        Called once when the plugin is first loaded. Use this method
        to set up resources, register hooks, and prepare for execution.

        Args:
            context: Plugin runtime context with configuration and services.

        Raises:
            PluginError: If initialization fails.
        """
        ...

    async def activate(self) -> None:
        """Activate the plugin for execution.

        Called after initialization when the plugin should begin
        processing events and handling requests.

        Raises:
            PluginError: If activation fails.
        """
        ...

    async def deactivate(self) -> None:
        """Deactivate the plugin temporarily.

        Called when the plugin should pause execution without
        releasing resources. Can be reactivated later.
        """
        ...

    async def shutdown(self) -> None:
        """Shutdown the plugin and release all resources.

        Called when the plugin is being permanently removed.
        Must release all resources and cleanup state.
        """
        ...

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the plugin.

        Returns:
            Dictionary containing health status information.
        """
        ...


class PluginBase:
    """Base class for plugins with default implementations.

    Provides a convenient base for plugins that don't need full
    control over their lifecycle. Override methods as needed.
    """

    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest
        self._context: PluginContext | None = None
        self._state: PluginState = PluginState.REGISTERED

    @property
    def context(self) -> PluginContext:
        """Get the plugin context.

        Returns:
            The current plugin context.

        Raises:
            RuntimeError: If plugin has not been initialized.
        """
        if self._context is None:
            raise RuntimeError("Plugin not initialized")
        return self._context

    @property
    def state(self) -> PluginState:
        """Get current plugin state."""
        return self._state

    async def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin."""
        self._context = context
        self._state = PluginState.ACTIVE

    async def activate(self) -> None:
        """Activate the plugin."""
        self._state = PluginState.ACTIVE

    async def deactivate(self) -> None:
        """Deactivate the plugin."""
        self._state = PluginState.PAUSED

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        self._state = PluginState.STOPPED
        self._context = None

    async def health_check(self) -> dict[str, Any]:
        """Perform health check.

        Returns:
            Health status dictionary.
        """
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "state": self._state.value,
            "healthy": self._state == PluginState.ACTIVE,
        }


class PluginError(Exception):
    """Base exception for plugin operations."""

    def __init__(self, message: str, plugin_name: str = "", cause: Exception | None = None) -> None:
        self.plugin_name = plugin_name
        self.cause = cause
        super().__init__(f"[{plugin_name}] {message}" if plugin_name else message)


class PluginNotFoundError(PluginError):
    """Raised when a plugin is not found."""

    def __init__(self, plugin_name: str) -> None:
        super().__init__(f"Plugin '{plugin_name}' not found", plugin_name)


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies cannot be resolved."""

    def __init__(self, plugin_name: str, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(
            f"Missing dependencies for '{plugin_name}': {', '.join(missing)}",
            plugin_name,
        )


class PluginStateError(PluginError):
    """Raised when an operation is invalid for the current state."""

    def __init__(self, plugin_name: str, current: PluginState, required: PluginState) -> None:
        self.current = current
        self.required = required
        super().__init__(
            f"Plugin '{plugin_name}' is {current.value}, required: {required.value}",
            plugin_name,
        )
