"""Plugin system core module.

Provides plugin registration, lifecycle management, hook mechanism,
and sandbox isolation capabilities.
"""

from __future__ import annotations

from app.plugins.core.registry import PluginRegistry, get_registry
from app.plugins.core.lifecycle import LifecycleManager, LifecycleState
from app.plugins.core.hooks import HookManager, hook, before, after
from app.plugins.core.sandbox import SandboxContext, SandboxExecutor, SandboxConfig
from app.plugins.core.base import PluginBase, PluginManifest, PluginContext

__all__ = [
    "PluginRegistry",
    "get_registry",
    "LifecycleManager",
    "LifecycleState",
    "HookManager",
    "hook",
    "before",
    "after",
    "SandboxContext",
    "SandboxExecutor",
    "SandboxConfig",
    "PluginBase",
    "PluginManifest",
    "PluginContext",
]
