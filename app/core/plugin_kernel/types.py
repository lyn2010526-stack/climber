"""Plugin kernel type definitions.

Implements the "everything is a plugin" contract: plugins declare
dependencies, expose services, subscribe to typed events, and are mounted
/unmounted at runtime without restart.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Protocol

Handler = Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]
RequestHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]


class Service(Protocol):
    """Marker protocol for services exposed by plugins.

    Any object that a plugin wants to make available to other plugins can be
    registered under a string key; the protocol is purely documentation.
    """

    __slots__ = ()


@dataclass
class PluginMeta:
    """Static metadata describing a plugin before it is mounted."""

    id: str
    version: str = "1.0.0"
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    category: str = "core"
    required_modes: list[str] = field(default_factory=list)


class PluginContext:
    """Handed to a plugin at mount time.

    Provides dependency injection (services), typed event pub/sub and the
    request-response channel. Unmounting a plugin reverses every registration
    made through this context.
    """

    def __init__(self, plugin_id: str, kernel: Any) -> None:
        self.plugin_id = plugin_id
        self._kernel = kernel

    def get_service(self, key: str) -> Service:
        return self._kernel.get_service(key)

    def register_service(self, key: str, service: Service) -> None:
        self._kernel.register_service(key, service, owner=self.plugin_id)

    def unregister_service(self, key: str) -> None:
        self._kernel.unregister_service(key, owner=self.plugin_id)

    def subscribe(self, event_type: str, handler: Handler) -> Any:
        return self._kernel.subscribe_owned(event_type, handler, owner=self.plugin_id)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        self._kernel.event_bus.unsubscribe(event_type, handler)

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        await self._kernel.event_bus.publish(event_type, data)

    async def request(self, request_type: str, payload: dict[str, Any]) -> Any:
        return await self._kernel.event_bus.request(request_type, payload)

    def register_request_handler(self, request_type: str, handler: RequestHandler) -> None:
        self._kernel.register_request_owned(
            request_type, handler, owner=self.plugin_id
        )


class Plugin:
    """Base class for all mountable plugins.

    Subclasses set ``id`` / ``version`` / ``dependencies`` as class
    attributes and implement :meth:`on_mount` / :meth:`on_unmount`.
    """

    id: str = ""
    version: str = "1.0.0"
    description: str = ""
    dependencies: list[str] = []
    category: str = "core"
    required_modes: list[str] = []

    def __init__(self) -> None:
        self._context: PluginContext | None = None

    @property
    def context(self) -> PluginContext:
        if self._context is None:
            raise RuntimeError(f"plugin '{self.id}' is not mounted")
        return self._context

    async def on_mount(self, context: PluginContext) -> None:
        """Initialize the plugin; register services/events through context."""
        self._context = context

    async def on_unmount(self) -> None:
        """Reverse every registration made in on_mount."""
        self._context = None

    def meta(self) -> PluginMeta:
        return PluginMeta(
            id=self.id,
            version=self.version,
            description=self.description,
            dependencies=list(self.dependencies),
            category=self.category,
            required_modes=list(self.required_modes),
        )

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        await self.context.emit(event_type, data)

    async def request(self, request_type: str, payload: dict[str, Any]) -> Any:
        return await self.context.request(request_type, payload)
