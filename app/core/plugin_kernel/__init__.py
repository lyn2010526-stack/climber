"""Plugin kernel — everything is a plugin.

The kernel does exactly three things:
1. Lifecycle management (mount/unmount, dependency ordering, reverse cleanup)
2. Dependency injection (plugins talk through registered services)
3. Event bus (typed pub/sub + request-response, auto-traced)

Core components are themselves plugins. The kernel has no privileged
hard-coded core other than the three items above.
"""

from app.core.plugin_kernel.event_bus import TypedEventBus, get_default_event_bus
from app.core.plugin_kernel.kernel import PluginKernel
from app.core.plugin_kernel.profiles import (
    ALL_PROFILES,
    COMPLETE_PROFILE,
    DEVELOPER_PROFILE,
    MINIMAL_PROFILE,
    OFFLINE_PROFILE,
    ProfileConfig,
)
from app.core.plugin_kernel.types import Plugin, PluginContext, PluginMeta

__all__ = [
    "ALL_PROFILES",
    "COMPLETE_PROFILE",
    "DEVELOPER_PROFILE",
    "MINIMAL_PROFILE",
    "OFFLINE_PROFILE",
    "Plugin",
    "PluginContext",
    "PluginKernel",
    "PluginMeta",
    "ProfileConfig",
    "TypedEventBus",
    "get_default_event_bus",
]
