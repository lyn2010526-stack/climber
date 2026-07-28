"""Plugin system abstraction.

"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class Plugin:
    id: str
    name: str
    description: str
    version: str
    functions: dict[str, Callable] = field(default_factory=dict)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """Manage plugins with hot-load/unload support.

    """

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.id] = plugin
        logger.info("plugin_registered", plugin_id=plugin.id, name=plugin.name)

    def unregister(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            return True
        return False

    def get(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def enable(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.enabled = True
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.enabled = False
            return True
        return False

    async def load_from_module(self, plugin_id: str, module_path: str) -> Plugin:
        """Dynamically load a plugin from a Python module."""
        try:
            module = importlib.import_module(module_path)
            plugin = getattr(module, "plugin", None)
            if not isinstance(plugin, Plugin):
                raise ValueError(f"Module {module_path} does not define a plugin")
            self.register(plugin)
            return plugin
        except Exception as e:
            logger.error("plugin_load_failed", plugin_id=plugin_id, module=module_path, error=str(e))
            raise


plugin_manager = PluginManager()
