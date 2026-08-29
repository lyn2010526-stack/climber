"""Middleware Configuration Manager — dynamic loading and lifecycle management.

Provides:
- Dynamic middleware registration and removal
- Configuration-driven middleware stack
- Middleware dependency resolution
- Runtime middleware state inspection
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.middleware import MiddlewareBase, MiddlewareChain

logger = structlog.get_logger()


@dataclass
class MiddlewareConfig:
    """Configuration for a single middleware."""
    name: str
    class_path: str  # e.g., "app.core.middleware_self_healing.SelfHealingMiddleware"
    enabled: bool = True
    priority: int = 100  # Lower = higher priority (executed first)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class MiddlewareState:
    """Runtime state of a middleware."""
    name: str
    enabled: bool
    hooks: list[str]
    call_count: int = 0
    error_count: int = 0


class MiddlewareConfigManager:
    """Manages middleware configuration and lifecycle.

    Usage:
        manager = MiddlewareConfigManager()
        manager.register("self_healing", "app.core.middleware_self_healing.SelfHealingMiddleware", config={"max_retries": 3})
        chain = manager.build_chain()
    """

    def __init__(self):
        self._configs: dict[str, MiddlewareConfig] = {}
        self._instances: dict[str, MiddlewareBase] = {}
        self._states: dict[str, MiddlewareState] = {}

    def register(
        self,
        name: str,
        class_path: str,
        enabled: bool = True,
        priority: int = 100,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Register a middleware configuration."""
        self._configs[name] = MiddlewareConfig(
            name=name,
            class_path=class_path,
            enabled=enabled,
            priority=priority,
            config=config or {},
        )
        logger.info("middleware.registered", name=name, class_path=class_path)

    def unregister(self, name: str) -> None:
        """Remove a middleware configuration."""
        self._configs.pop(name, None)
        self._instances.pop(name, None)
        self._states.pop(name, None)
        logger.info("middleware.unregistered", name=name)

    def enable(self, name: str) -> None:
        """Enable a middleware."""
        if name in self._configs:
            self._configs[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable a middleware."""
        if name in self._configs:
            self._configs[name].enabled = False

    def _load_middleware(self, config: MiddlewareConfig) -> MiddlewareBase | None:
        """Dynamically load a middleware class."""
        try:
            module_path, class_name = config.class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(**config.config)
        except Exception as e:
            logger.error("middleware.load_failed", name=config.name, error=str(e))
            return None

    def build_chain(self) -> MiddlewareChain:
        """Build a MiddlewareChain from registered configurations."""
        middlewares = []

        # Sort by priority
        sorted_configs = sorted(
            self._configs.values(),
            key=lambda c: c.priority,
        )

        for config in sorted_configs:
            if not config.enabled:
                continue

            # Reuse cached instance or load new one
            if config.name not in self._instances:
                instance = self._load_middleware(config)
                if instance is None:
                    continue
                self._instances[config.name] = instance

            instance = self._instances[config.name]

            # Track state
            hooks = [
                hook for hook in [
                    "on_reasoning", "on_acting", "on_compress_context",
                    "on_check_permission", "on_system_prompt",
                ]
                if instance.is_implemented(hook)
            ]
            self._states[config.name] = MiddlewareState(
                name=config.name,
                enabled=config.enabled,
                hooks=hooks,
            )

            middlewares.append(instance)

        return MiddlewareChain(middlewares)

    def get_state(self) -> list[dict[str, Any]]:
        """Get the state of all registered middlewares."""
        return [
            {
                "name": state.name,
                "enabled": state.enabled,
                "hooks": state.hooks,
                "call_count": state.call_count,
                "error_count": state.error_count,
            }
            for state in self._states.values()
        ]

    def get_config(self, name: str) -> dict[str, Any] | None:
        """Get configuration for a specific middleware."""
        config = self._configs.get(name)
        if config is None:
            return None
        return {
            "name": config.name,
            "class_path": config.class_path,
            "enabled": config.enabled,
            "priority": config.priority,
            "config": config.config,
        }

    def list_configs(self) -> list[dict[str, Any]]:
        """List all registered middleware configurations."""
        return [self.get_config(name) for name in self._configs]

    def export_config(self) -> list[dict[str, Any]]:
        """Export all middleware configurations as a list of dicts (for YAML/JSON file)."""
        return [
            {
                "name": cfg.name,
                "class_path": cfg.class_path,
                "enabled": cfg.enabled,
                "priority": cfg.priority,
                "config": cfg.config,
            }
            for cfg in self._configs.values()
        ]

    def import_config(self, config_list: list[dict[str, Any]]) -> int:
        """Import middleware configurations from a list of dicts (from YAML/JSON file).

        Returns the number of middlewares imported.
        """
        imported = 0
        for entry in config_list:
            name = entry.get("name")
            class_path = entry.get("class_path")
            if not name or not class_path:
                logger.warning("Skipping invalid middleware config entry", entry=entry)
                continue
            self.register(
                name=name,
                class_path=class_path,
                enabled=entry.get("enabled", True),
                priority=entry.get("priority", 100),
                config=entry.get("config", {}),
            )
            imported += 1
        return imported

    @staticmethod
    def load_from_file(path: str) -> MiddlewareConfigManager:
        """Load middleware configuration from a YAML or JSON file.

        Supported extensions: .yaml, .yml, .json
        """
        import json
        import os

        ext = os.path.splitext(path)[1].lower()
        with open(path) as f:
            if ext in (".yaml", ".yml"):
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError as err:
                    raise ImportError("PyYAML is required to load .yaml/.yml config files. Install with: pip install pyyaml") from err
            elif ext == ".json":
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file extension: {ext}. Use .yaml, .yml, or .json")

        if not isinstance(data, list):
            raise ValueError("Config file must contain a list of middleware entries")

        manager = MiddlewareConfigManager()
        manager.import_config(data)
        return manager

    def save_to_file(self, path: str) -> None:
        """Save current middleware configuration to a YAML or JSON file."""
        import json
        import os

        ext = os.path.splitext(path)[1].lower()
        data = self.export_config()

        with open(path, "w") as f:
            if ext in (".yaml", ".yml"):
                try:
                    import yaml
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                except ImportError as err:
                    raise ImportError("PyYAML is required to save .yaml/.yml config files.") from err
            elif ext == ".json":
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported config file extension: {ext}. Use .yaml, .yml, or .json")


# Global config manager instance
_config_manager: MiddlewareConfigManager | None = None


def get_middleware_config_manager() -> MiddlewareConfigManager:
    """Get the global middleware configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = MiddlewareConfigManager()
        # Register default middlewares
        _config_manager.register(
            "self_healing",
            "app.core.middleware_self_healing.SelfHealingMiddleware",
            priority=10,
            config={"max_retries": 2},
        )
        _config_manager.register(
            "permission",
            "app.core.middleware_permission.PermissionMiddleware",
            priority=20,
            config={"max_calls_per_minute": 120},
        )
        _config_manager.register(
            "tracing",
            "app.core.middleware_tracing.TracingMiddleware",
            priority=90,
            config={"emit_events": True},
        )
    return _config_manager
