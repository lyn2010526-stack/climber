"""Plugin: reporting - Plugin system."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Protocol


class ReportingPluginInterface(Protocol):
    """Plugin interface."""

    name: str
    version: str

    def initialize(self, config: dict[str, Any]) -> None: ...
    def execute(self, context: dict[str, Any]) -> dict[str, Any]: ...
    def shutdown(self) -> None: ...


@dataclass
class ReportingPluginManifest:
    """Plugin manifest."""
    name: str = ''
    version: str = '1.0.0'
    description: str = ''
    author: str = ''
    dependencies: list[str] = field(default_factory=list)
    entry_point: str = ''
    enabled: bool = True


@dataclass
class ReportingPluginContext:
    """Plugin context."""
    config: dict[str, Any] = field(default_factory=dict)
    services: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ReportingPluginManager:
    """Plugin manager."""

    def __init__(self):
        self._plugins: dict[str, ReportingPluginInterface] = {}
        self._manifests: dict[str, ReportingPluginManifest] = {}
        self._hooks: dict[str, list[callable]] = {}

    def register(self, plugin: ReportingPluginInterface, manifest: ReportingPluginManifest | None = None) -> None:
        """Register plugin."""
        self._plugins[plugin.name] = plugin
        if manifest:
            self._manifests[plugin.name] = manifest

    def unregister(self, name: str) -> bool:
        """Unregister plugin."""
        if name in self._plugins:
            self._plugins.pop(name)
            self._manifests.pop(name, None)
            return True
        return False

    def get(self, name: str) -> ReportingPluginInterface | None:
        """Get plugin."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[ReportingPluginManifest]:
        """List plugins."""
        return list(self._manifests.values())

    def load(self, module_path: str) -> ReportingPluginInterface | None:
        """Load plugin from module."""
        try:
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, 'ReportingPlugin', None)
            if plugin_class:
                return plugin_class()
        except ImportError:
            pass
        return None

    def execute(self, name: str, context: dict[str, Any]) -> dict[str, Any]:
        """Execute plugin."""
        plugin = self._plugins.get(name)
        if not plugin:
            return {'success': False, 'error': 'Plugin not found'}
        return plugin.execute(context)

    def register_hook(self, event: str, handler: callable) -> None:
        """Register hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    def trigger_hook(self, event: str, data: Any = None) -> list[Any]:
        """Trigger hook."""
        results = []
        for handler in self._hooks.get(event, []):
            results.append(handler(data))
        return results
