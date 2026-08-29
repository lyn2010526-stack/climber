"""PluginKernel — minimal everything-is-a-plugin kernel.

The kernel does exactly three things:
1. Lifecycle management: mount/unmount with dependency ordering, and full
   reversal of all registrations on unmount (no orphan state).
2. Dependency injection: plugins talk to each other through services
   registered under string keys.
3. Event bus: typed pub/sub + request-response; published events are
   automatically written to an append-only trace log when a sink is set.

Core components are themselves plugins. The kernel has no privileged
hard-coded core other than lifecycle / DI / event plumbing.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from app.core.plugin_kernel.event_bus import TypedEventBus
from app.core.plugin_kernel.types import Plugin, PluginContext

logger = structlog.get_logger()


class PluginConflictError(RuntimeError):
    """Raised on duplicate plugin ids or service key collisions."""


class PluginDependencyError(RuntimeError):
    """Raised when a dependency is missing or circular."""


class PluginKernel:
    """Mountable plugin container with dependency management and hot-swap."""

    def __init__(
        self,
        event_bus: TypedEventBus | None = None,
        trace_sink: Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self.event_bus = event_bus or TypedEventBus(trace_sink=trace_sink)
        self._plugins: dict[str, Plugin] = {}
        self._services: dict[str, tuple[Any, str]] = {}  # key -> (service, owner)
        self._subscriptions: list[tuple[str, Any, str]] = []  # (event_type, handler, owner)
        self._request_regs: list[tuple[str, Any, str]] = []  # (request_type, handler, owner)
        self._mounted_order: list[str] = []
        self._profile: Any | None = None

    def set_profile(self, profile: Any) -> None:
        """Bind a profile config (see profiles.py).

        Stores the profile and records which plugin ids it resolves to. Real
        mounting of profile plugins happens when those ids are registered via
        :meth:`register`; call :meth:`apply_profile` after registering.
        """
        self._profile = profile

    def get_profile(self) -> Any | None:
        return self._profile

    def profile_delta(self) -> tuple[list[str], list[str]]:
        """Compute (to_mount, to_unmount) between the bound profile's plugin
        ids and the currently mounted set. Empty when no profile is bound."""
        if self._profile is None:
            return [], []
        desired = set(self._profile.all_plugin_ids())
        current = set(self._mounted_order)
        to_mount = sorted(desired - current)
        to_unmount = sorted(current - desired)
        return to_mount, to_unmount

    # ── plugin registry ──

    def register(self, plugin: Plugin) -> None:
        """Register a plugin class instance without mounting it."""
        if not plugin.id:
            raise PluginConflictError("plugin id must not be empty")
        if plugin.id in self._plugins:
            raise PluginConflictError(f"plugin already registered: {plugin.id}")
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def list_mounted(self) -> list[str]:
        return list(self._mounted_order)

    def is_mounted(self, plugin_id: str) -> bool:
        return plugin_id in self._mounted_order

    def unregister(self, plugin_id: str) -> None:
        self._plugins.pop(plugin_id, None)

    # ── dependency resolution ──

    def _resolve_mount_order(self, plugin_id: str) -> list[str]:
        """Return a topologically-ordered list of plugin ids to mount.

        Raises PluginDependencyError for missing or circular dependencies.
        """
        order: list[str] = []
        state: dict[str, int] = {}  # 0=visiting 1=done

        def visit(pid: str, trail: list[str]) -> None:
            if pid in self._plugins and pid in state:
                if state[pid] == 0:
                    raise PluginDependencyError(
                        f"circular dependency: {' -> '.join([*trail, pid])}"
                    )
                return
            if pid not in self._plugins:
                raise PluginDependencyError(f"missing dependency '{pid}' for plugin '{plugin_id}'")
            state[pid] = 0
            plugin = self._plugins[pid]
            for dep in plugin.dependencies:
                visit(dep, [*trail, pid])
            state[pid] = 1
            if pid not in order:
                order.append(pid)

        visit(plugin_id, [])
        return order

    # ── lifecycle ──

    async def mount(self, plugin_id: str) -> None:
        """Mount a plugin and (recursively) its unmet dependencies."""
        for pid in self._resolve_mount_order(plugin_id):
            if pid in self._mounted_order:
                continue
            await self._mount_one(pid)

    async def _mount_one(self, plugin_id: str) -> None:
        plugin = self._plugins[plugin_id]
        ctx = PluginContext(plugin_id, self)
        try:
            await plugin.on_mount(ctx)
        except Exception as exc:
            # Roll back anything the plugin registered before failing.
            await self._rollback_owner(plugin_id)
            logger.warning("plugin.mount_failed", plugin=plugin_id, error=str(exc))
            raise
        self._mounted_order.append(plugin_id)
        logger.info("plugin.mounted", plugin=plugin_id, version=plugin.version)

    async def unmount(self, plugin_id: str, cascade: bool = False) -> list[str]:
        """Unmount a plugin, reversing all its registrations.

        When ``cascade`` is True, plugins depending on this one are unmounted
        first; otherwise unmount fails if other mounted plugins depend on it.
        Returns the list of unmounted plugin ids (in unmount order).
        """
        if plugin_id not in self._mounted_order:
            return []
        dependents = self._mounted_dependents(plugin_id)
        if dependents and not cascade:
            raise PluginConflictError(
                f"plugin '{plugin_id}' is still depended on by {dependents}; "
                "use cascade=True to unmount them"
            )
        unmounted: list[str] = []
        for dep in dependents:
            unmounted.extend(await self.unmount(dep, cascade=True))
        unmounted.append(plugin_id)
        await self._unmount_one(plugin_id)
        return unmounted

    def _mounted_dependents(self, plugin_id: str) -> list[str]:
        deps: list[str] = []
        for pid in self._mounted_order:
            plugin = self._plugins.get(pid)
            if plugin and plugin_id in plugin.dependencies:
                deps.append(pid)
        return deps

    async def _unmount_one(self, plugin_id: str) -> None:
        plugin = self._plugins.get(plugin_id)
        if plugin is not None:
            try:
                await plugin.on_unmount()
            except Exception as exc:
                logger.warning("plugin.unmount_failed", plugin=plugin_id, error=str(exc))
        self._rollback_owner(plugin_id)
        if plugin_id in self._mounted_order:
            self._mounted_order.remove(plugin_id)
        logger.info("plugin.unmounted", plugin=plugin_id)

    def _rollback_owner(self, plugin_id: str) -> None:
        """Reverse all registrations owned by a plugin (no orphans)."""
        for key in list(self._services):
            if self._services[key][1] == plugin_id:
                self._services.pop(key, None)
        for event_type, handler, owner in list(self._subscriptions):
            if owner == plugin_id:
                self.event_bus.unsubscribe(event_type, handler)
                self._subscriptions.remove((event_type, handler, owner))
        for request_type, handler, owner in list(self._request_regs):
            if owner == plugin_id:
                self.event_bus.unregister_request_handler(request_type, owner=owner)
                self._request_regs.remove((request_type, handler, owner))

    def subscribe_owned(
        self, event_type: str, handler: Any, owner: str = ""
    ) -> None:
        """Subscribe on behalf of a plugin, tracking for rollback."""
        self.event_bus.subscribe(event_type, handler, owner=owner)
        self._subscriptions.append((event_type, handler, owner))

    def register_request_owned(
        self, request_type: str, handler: Any, owner: str = ""
    ) -> None:
        """Register a request handler on behalf of a plugin."""
        self.event_bus.register_request_handler(request_type, handler, owner=owner)
        self._request_regs.append((request_type, handler, owner))

    # ── dependency injection (service locator) ──

    def register_service(self, key: str, service: Any, owner: str = "") -> None:
        if key in self._services and self._services[key][1] != owner:
            raise PluginConflictError(
                f"service '{key}' already registered by '{self._services[key][1]}'"
            )
        self._services[key] = (service, owner)

    def unregister_service(self, key: str, owner: str = "") -> None:
        existing = self._services.get(key)
        if existing is not None and (not owner or existing[1] == owner):
            self._services.pop(key, None)

    def get_service(self, key: str) -> Any:
        if key not in self._services:
            raise KeyError(f"service not registered: {key}")
        return self._services[key][0]

    def has_service(self, key: str) -> bool:
        return key in self._services

    def list_services(self) -> list[str]:
        return list(self._services.keys())

    # ── event bridge ──

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        await self.event_bus.publish(event_type, data)

    async def request(self, request_type: str, payload: dict[str, Any]) -> Any:
        return await self.event_bus.request(request_type, payload)

    # ── shutdown ──

    async def shutdown(self) -> None:
        """Unmount every mounted plugin in reverse mount order."""
        while self._mounted_order:
            await self._unmount_one(self._mounted_order[-1])
