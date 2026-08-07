"""Plugin registry for managing plugin registration and discovery.

Provides centralized plugin management including registration, unregistration,
lookup, and dependency resolution.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from app.plugins.core.base import (
    PluginBase,
    PluginDependencyError,
    PluginError,
    PluginInterface,
    PluginManifest,
    PluginNotFoundError,
    PluginState,
    PluginStateError,
)

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for all plugins.

    Manages plugin lifecycle from registration through shutdown.
    Supports dependency resolution, state management, and querying.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInterface] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._states: dict[str, PluginState] = {}
        self._dependencies: dict[str, set[str]] = {}
        self._dependents: dict[str, set[str]] = {}

    @property
    def plugin_count(self) -> int:
        """Get the number of registered plugins."""
        return len(self._plugins)

    @property
    def active_count(self) -> int:
        """Get the number of active plugins."""
        return sum(1 for s in self._states.values() if s == PluginState.ACTIVE)

    def register(
        self,
        plugin: PluginInterface,
        manifest: PluginManifest | None = None,
    ) -> None:
        """Register a plugin in the system.

        Args:
            plugin: The plugin instance to register.
            manifest: Optional manifest; uses plugin.manifest if not provided.

        Raises:
            PluginError: If plugin name is already registered.
            PluginDependencyError: If dependencies are not met.
        """
        manifest = manifest or plugin.manifest if hasattr(plugin, "manifest") else None
        if manifest is None:
            raise PluginError("Plugin must have a manifest")

        name = manifest.name
        if name in self._plugins:
            raise PluginError(f"Plugin '{name}' is already registered", name)

        self._resolve_dependencies(manifest.dependencies)

        self._plugins[name] = plugin
        self._manifests[name] = manifest
        self._states[name] = PluginState.REGISTERED
        self._dependencies[name] = set(manifest.dependencies)

        for dep in manifest.dependencies:
            if dep not in self._dependents:
                self._dependents[dep] = set()
            self._dependents[dep].add(name)

        logger.info("Plugin registered: %s v%s", name, manifest.version)

    def unregister(self, name: str, force: bool = False) -> None:
        """Unregister a plugin.

        Args:
            name: Plugin name to unregister.
            force: If True, unregister even if other plugins depend on it.

        Raises:
            PluginNotFoundError: If plugin is not registered.
            PluginError: If other plugins depend on this and force is False.
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)

        dependents = self._dependents.get(name, set())
        if dependents and not force:
            raise PluginError(
                f"Cannot unregister '{name}': depended upon by {', '.join(dependents)}",
                name,
            )

        if force and dependents:
            for dep_name in list(dependents):
                self.unregister(dep_name, force=True)

        del self._plugins[name]
        del self._manifests[name]
        del self._states[name]

        for dep in self._dependencies.pop(name, set()):
            if dep in self._dependents:
                self._dependents[dep].discard(name)

        self._dependents.pop(name, None)
        logger.info("Plugin unregistered: %s", name)

    def get(self, name: str) -> PluginInterface:
        """Get a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            The plugin instance.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._plugins:
            raise PluginNotFoundError(name)
        return self._plugins[name]

    def get_manifest(self, name: str) -> PluginManifest:
        """Get a plugin manifest by name.

        Args:
            name: Plugin name.

        Returns:
            The plugin manifest.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._manifests:
            raise PluginNotFoundError(name)
        return self._manifests[name]

    def get_state(self, name: str) -> PluginState:
        """Get the current state of a plugin.

        Args:
            name: Plugin name.

        Returns:
            Current plugin state.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._states:
            raise PluginNotFoundError(name)
        return self._states[name]

    def set_state(self, name: str, state: PluginState) -> None:
        """Set the state of a plugin.

        Args:
            name: Plugin name.
            state: New state.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._states:
            raise PluginNotFoundError(name)
        self._states[name] = state

    def list_plugins(
        self,
        state: PluginState | None = None,
        tag: str | None = None,
    ) -> list[str]:
        """List registered plugin names with optional filtering.

        Args:
            state: Filter by plugin state.
            tag: Filter by plugin tag.

        Returns:
            List of plugin names matching the filters.
        """
        names = list(self._plugins.keys())

        if state is not None:
            names = [n for n in names if self._states[n] == state]

        if tag is not None:
            names = [n for n in names if tag in self._manifests[n].tags]

        return names

    def get_all_manifests(self) -> dict[str, PluginManifest]:
        """Get all registered manifests.

        Returns:
            Dictionary mapping plugin names to manifests.
        """
        return dict(self._manifests)

    def has_plugin(self, name: str) -> bool:
        """Check if a plugin is registered.

        Args:
            name: Plugin name.

        Returns:
            True if plugin is registered.
        """
        return name in self._plugins

    def get_dependencies(self, name: str) -> list[str]:
        """Get direct dependencies of a plugin.

        Args:
            name: Plugin name.

        Returns:
            List of dependency plugin names.

        Raises:
            PluginNotFoundError: If plugin is not found.
        """
        if name not in self._dependencies:
            raise PluginNotFoundError(name)
        return list(self._dependencies[name])

    def get_all_dependencies(self, name: str) -> list[str]:
        """Get all transitive dependencies of a plugin.

        Args:
            name: Plugin name.

        Returns:
            Ordered list of all dependency names.
        """
        visited: set[str] = set()
        result: list[str] = []

        def _visit(n: str) -> None:
            if n in visited:
                return
            visited.add(n)
            for dep in self._dependencies.get(n, set()):
                _visit(dep)
            result.append(n)

        _visit(name)
        return result[:-1]

    def get_dependents(self, name: str) -> list[str]:
        """Get plugins that depend on the given plugin.

        Args:
            name: Plugin name.

        Returns:
            List of dependent plugin names.
        """
        return list(self._dependents.get(name, set()))

    def resolve_startup_order(self) -> list[str]:
        """Resolve plugin startup order based on dependencies.

        Returns:
            Ordered list of plugin names for startup.

        Raises:
            PluginError: If circular dependency detected.
        """
        visited: set[str] = set()
        temp_mark: set[str] = set()
        order: list[str] = []

        def _visit(n: str) -> None:
            if n in temp_mark:
                raise PluginError(f"Circular dependency detected involving '{n}'")
            if n in visited:
                return
            temp_mark.add(n)
            for dep in self._dependencies.get(n, set()):
                _visit(dep)
            temp_mark.discard(n)
            visited.add(n)
            order.append(n)

        for name in self._plugins:
            _visit(name)

        return order

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._manifests.clear()
        self._states.clear()
        self._dependencies.clear()
        self._dependents.clear()

    def __iter__(self) -> Iterator[str]:
        return iter(self._plugins)

    def __contains__(self, name: str) -> bool:
        return name in self._plugins

    def __len__(self) -> int:
        return len(self._plugins)

    def _resolve_dependencies(self, dependencies: list[str]) -> None:
        """Verify all dependencies are registered.

        Args:
            dependencies: List of required plugin names.

        Raises:
            PluginDependencyError: If any dependency is missing.
        """
        missing = [dep for dep in dependencies if dep not in self._plugins]
        if missing:
            raise PluginDependencyError("new_plugin", missing)


_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance.

    Returns:
        The global PluginRegistry singleton.
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None


__all__ = [
    "PluginRegistry",
    "get_registry",
    "reset_registry",
]
