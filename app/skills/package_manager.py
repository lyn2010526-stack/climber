"""Skill package manager."""

from __future__ import annotations


class SkillPackageManager:
    """Manages skill packages."""

    def __init__(self):
        self._packages = {}

    def get(self, skill_id: str) -> dict | None:
        return self._packages.get(skill_id)

    def register(self, skill_id: str, package: dict) -> None:
        self._packages[skill_id] = package

    def list_all(self) -> list[dict]:
        return list(self._packages.values())


_manager: SkillPackageManager | None = None


def get_skill_manager() -> SkillPackageManager:
    """Get the global skill package manager singleton."""
    global _manager
    if _manager is None:
        _manager = SkillPackageManager()
    return _manager
