"""Configuration profiles — "configuration is product form".

Different profiles enable different plugin sets, producing fundamentally
different runtime modes without touching a single line of source code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Profile definitions ──

# Each profile is a mapping of plugin category -> list of plugin ids.
# The kernel uses this to decide which plugins to mount at startup.

MINIMAL_PROFILE: dict[str, list[str]] = {
    "model": ["local-model-adapter"],
    "automation": ["accessibility-channel"],
    "sandbox": ["basic-sandbox"],
    "tools": ["core-tools"],
    "storage": ["sqlite-storage"],
    "memory": ["short-term-memory"],
    "skill": ["skill-loader"],
}
"""Minimal mode: local model + basic tools + lightweight storage, low power."""

COMPLETE_PROFILE: dict[str, list[str]] = {
    "model": ["local-model-adapter", "cloud-model-adapter", "multi-model-router"],
    "automation": ["accessibility-channel", "shizuku-channel", "adb-channel"],
    "sandbox": ["basic-sandbox", "proot-sandbox", "js-sandbox"],
    "tools": ["core-tools", "communication-tools", "media-tools", "system-tools"],
    "storage": ["sqlite-storage", "file-storage", "external-storage"],
    "memory": [
        "short-term-memory",
        "medium-term-memory",
        "long-term-memory",
        "skill-library",
    ],
    "skill": ["skill-loader", "skill-market"],
    "agent": ["planning-agent", "execution-agent", "validation-agent"],
    "perception": ["screenshot", "ui-tree", "voice-input"],
    "ui": ["transparent-panel", "tool-cards", "thinking-display"],
    "debug": [],
}
"""Complete mode: all plugins enabled, full feature set."""

OFFLINE_PROFILE: dict[str, list[str]] = {
    "model": ["local-model-adapter"],
    "automation": ["accessibility-channel"],
    "sandbox": ["basic-sandbox"],
    "tools": ["core-tools"],
    "storage": ["sqlite-storage", "file-storage"],
    "memory": ["short-term-memory", "skill-library"],
    "skill": ["skill-loader"],
    "perception": ["screenshot", "ui-tree"],
    "ui": ["tool-cards"],
    "debug": [],
}
"""Offline mode: local model + local tools only, no network requests."""

DEVELOPER_PROFILE: dict[str, list[str]] = {
    **COMPLETE_PROFILE,
    "debug": [
        "debug-panel",
        "hot-reload",
        "event-log-viewer",
        "trajectory-replay",
    ],
}
"""Developer mode: same as complete + debugging tools."""

ALL_PROFILES: dict[str, dict[str, list[str]]] = {
    "minimal": MINIMAL_PROFILE,
    "complete": COMPLETE_PROFILE,
    "offline": OFFLINE_PROFILE,
    "developer": DEVELOPER_PROFILE,
}


@dataclass
class ProfileConfig:
    """A profile configuration that can be serialized to/from JSON/YAML."""

    mode: str = "complete"
    overrides: dict[str, list[str]] = field(default_factory=dict)
    disabled_plugins: list[str] = field(default_factory=list)

    def resolve(self) -> dict[str, list[str]]:
        """Resolve the effective plugin list for this profile.

        Starts from the base profile, applies overrides (merged per category),
        and removes disabled plugins.
        """
        base = dict(ALL_PROFILES.get(self.mode, COMPLETE_PROFILE))
        for category, plugins in self.overrides.items():
            if category in base:
                merged = list(base[category])
                for p in plugins:
                    if p not in merged:
                        merged.append(p)
                base[category] = merged
            else:
                base[category] = list(plugins)
        disabled = set(self.disabled_plugins)
        return {
            cat: [p for p in plugins if p not in disabled]
            for cat, plugins in base.items()
        }

    def all_plugin_ids(self) -> list[str]:
        result: list[str] = []
        for plugins in self.resolve().values():
            result.extend(plugins)
        return result
