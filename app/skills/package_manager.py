"""Skill package manager."""

from __future__ import annotations

from typing import Any


class SkillPackageManager:
    """Manages skill packages."""

    def __init__(self) -> None:
        self._packages: dict[str, dict[str, Any]] = {}

    def get(self, skill_id: str) -> dict[str, Any] | None:
        return self._packages.get(skill_id)

    def register(self, skill_id: str, package: dict[str, Any]) -> None:
        self._packages[skill_id] = package

    def list_all(self) -> list[dict[str, Any]]:
        return list(self._packages.values())


_manager: SkillPackageManager | None = None


def get_skill_manager() -> SkillPackageManager:
    """Get the global skill package manager singleton."""
    global _manager
    if _manager is None:
        _manager = SkillPackageManager()
    return _manager
