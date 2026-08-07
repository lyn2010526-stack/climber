"""Skill package manager."""
from __future__ import annotations
from typing import Any, Optional


class SkillPackageManager:
    """Manages skill packages."""
    
    def __init__(self):
        self._packages = {}
    
    def get(self, skill_id: str) -> Optional[dict]:
        return self._packages.get(skill_id)
    
    def register(self, skill_id: str, package: dict) -> None:
        self._packages[skill_id] = package
    
    def list_all(self) -> list[dict]:
        return list(self._packages.values())


def get_skill_manager() -> SkillPackageManager:
    """Get the global skill package manager."""
    return SkillPackageManager()
