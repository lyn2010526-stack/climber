"""Agent personality definition system.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentPersonality:
    agent_id: str
    name: str
    description: str
    traits: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SoulManager:
    """Manage agent personality definitions.

    """

    def __init__(self, storage_path: str = "./data/souls"):
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._personalities: dict[str, AgentPersonality] = {}

    def define(self, personality: AgentPersonality) -> None:
        self._personalities[personality.agent_id] = personality
        self._save(personality)
        logger.info("soul_defined", agent_id=personality.agent_id)

    def get(self, agent_id: str) -> AgentPersonality | None:
        return self._personalities.get(agent_id)

    def list_all(self) -> list[AgentPersonality]:
        return list(self._personalities.values())

    def apply_to_session(self, agent_id: str, session: Any) -> None:
        personality = self._personalities.get(agent_id)
        if not personality:
            return
        if hasattr(session, "system_prompt"):
            personality_block = self._build_prompt_block(personality)
            if personality_block not in (session.system_prompt or ""):
                session.system_prompt = f"{personality_block}\n\n{session.system_prompt or ''}".strip()

    def _build_prompt_block(self, personality: AgentPersonality) -> str:
        lines = [f"# {personality.name}", personality.description]
        if personality.traits:
            lines.append("\n## Traits")
            lines.extend(f"- {trait}" for trait in personality.traits)
        if personality.rules:
            lines.append("\n## Rules")
            lines.extend(f"- {rule}" for rule in personality.rules)
        if personality.skills:
            lines.append("\n## Skills")
            lines.extend(f"- {skill}" for skill in personality.skills)
        return "\n".join(lines)

    def _save(self, personality: AgentPersonality) -> None:
        import json
        path = self._storage_path / f"{personality.agent_id}.json"
        data = {
            "agent_id": personality.agent_id,
            "name": personality.name,
            "description": personality.description,
            "traits": personality.traits,
            "rules": personality.rules,
            "skills": personality.skills,
            "metadata": personality.metadata,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_from_file(self, file_path: str) -> AgentPersonality:
        import json
        path = Path(file_path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        personality = AgentPersonality(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data.get("description", ""),
            traits=data.get("traits", []),
            rules=data.get("rules", []),
            skills=data.get("skills", []),
            metadata=data.get("metadata", {}),
        )
        self._personalities[personality.agent_id] = personality
        return personality


soul_manager = SoulManager()
