"""Local skill package management.

Climber skills are plain directories that contain a ``.skill.json`` manifest
and optional Python modules, prompt templates, and tool bundles. This module
scans the ``skills/`` directory, loads manifests, and can install skills from
a URL or local path.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import structlog

from app.storage import async_session
from app.storage.models_platform import Skill
from sqlalchemy import select

logger = structlog.get_logger()

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"
SKILL_MANIFEST = ".skill.json"


def _skill_manifest_path(skill_dir: Path) -> Path | None:
    for candidate in (skill_dir / SKILL_MANIFEST, skill_dir / "manifest.json"):
        if candidate.exists():
            return candidate
    return None


def scan_skills() -> list[dict[str, Any]]:
    """Return metadata for every skill found under the skills directory."""
    if not SKILLS_DIR.exists():
        return []
    results: list[dict[str, Any]] = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        manifest = _skill_manifest_path(entry)
        if manifest is None:
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data.setdefault("path", str(entry))
            results.append(data)
        except Exception as exc:
            logger.warning("skill_manifest_invalid", path=str(manifest), error=str(exc))
    return results


async def ensure_skill_registered(skill_meta: dict[str, Any]) -> dict[str, Any]:
    """Persist a scanned skill to the database if not already present."""
    async with async_session() as db:
        existing = (
            await db.execute(select(Skill).where(Skill.name == skill_meta.get("name")))
        ).scalar_one_or_none()
        if existing is not None:
            return {
                "id": existing.id,
                "name": existing.name,
                "is_enabled": existing.is_enabled,
                "use_count": existing.use_count,
            }
        skill = Skill(
            user_id="default-user",
            name=skill_meta.get("name", Path(skill_meta.get("path", "")).name),
            description=skill_meta.get("description", ""),
            category=skill_meta.get("category", "general"),
            prompt_template=skill_meta.get("prompt_template", ""),
            tools=skill_meta.get("tools", []),
            is_enabled=skill_meta.get("enabled", True),
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return {
            "id": skill.id,
            "name": skill.name,
            "is_enabled": skill.is_enabled,
            "use_count": skill.use_count,
        }


async def load_skill_module(skill_path: Path, module_name: str) -> Any | None:
    """Dynamically import a Python module from a skill directory."""
    init = skill_path / "__init__.py"
    target = skill_path / f"{module_name}.py"
    if not target.exists() and not init.exists():
        return None
    spec = importlib.util.spec_from_file_location(module_name, target if target.exists() else init)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        logger.warning("skill_module_load_failed", module=module_name, error=str(exc))
        return None


async def toggle_skill(skill_name: str, enabled: bool) -> dict[str, Any] | None:
    """Toggle skill enabled status at runtime."""
    async with async_session() as db:
        skill = (
            await db.execute(select(Skill).where(Skill.name == skill_name))
        ).scalar_one_or_none()
        if skill is None:
            return None
        skill.is_enabled = enabled
        await db.commit()
        await db.refresh(skill)
        return {
            "id": skill.id,
            "name": skill.name,
            "is_enabled": skill.is_enabled,
            "use_count": skill.use_count,
        }


async def get_enabled_skills(user_id: str = "default-user") -> list[dict[str, Any]]:
    """Get all enabled skills for a user."""
    async with async_session() as db:
        result = (
            await db.execute(
                select(Skill).where(Skill.user_id == user_id, Skill.is_enabled == True)
            )
        ).scalars().all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "tools": s.tools,
                "is_enabled": s.is_enabled,
                "use_count": s.use_count,
            }
            for s in result
        ]
