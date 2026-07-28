"""Plugin Manager — hot-reload support for skills and MCP servers.

- Plugin lifecycle management
- Sidekick-AI plugin system concept
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import structlog

from app.storage import async_session
from app.storage.models_platform import Skill
from app.storage.models_plugins import MCPServerRecord
from sqlalchemy import select

logger = structlog.get_logger()


class PluginManager:
    """Manage skill and MCP server lifecycle, including hot-reload."""

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or Path(__file__).resolve().parent.parent.parent / "skills"
        self._loaded_modules: dict[str, Any] = {}

    async def reload_skill(self, skill_id: str) -> bool:
        """Hot-reload a skill module."""
        async with async_session() as db:
            result = await db.execute(select(Skill).where(Skill.id == skill_id))
            skill = result.scalar_one_or_none()
            if skill is None:
                return False
            skill_path = Path(skill.prompt_template).parent if skill.prompt_template else self.skills_dir / skill.name
            if not skill_path.exists():
                return False
            init = skill_path / "__init__.py"
            if not init.exists():
                return False
            module_name = f"skill_{skill.name}_{skill_id}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            try:
                spec = importlib.util.spec_from_file_location(module_name, init)
                if spec is None or spec.loader is None:
                    return False
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                self._loaded_modules[skill_id] = module
                skill.use_count += 1
                await db.commit()
                logger.info("skill_reloaded", skill_id=skill_id, name=skill.name)
                return True
            except Exception as e:
                logger.warning("skill_reload_failed", skill_id=skill_id, error=str(e))
                return False

    async def unload_skill(self, skill_id: str) -> bool:
        """Unload a skill module."""
        module = self._loaded_modules.pop(skill_id, None)
        if module is None:
            return False
        module_name = getattr(module, "__name__", None)
        if module_name and module_name in sys.modules:
            del sys.modules[module_name]
        logger.info("skill_unloaded", skill_id=skill_id)
        return True

    async def get_loaded_skills(self) -> list[str]:
        return list(self._loaded_modules.keys())


# Global singleton
plugin_manager = PluginManager()
