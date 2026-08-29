"""Skill three-level loading + skill library.

Every operation skill is a directory containing:

  skills/<skill_id>/
    SKILL.md          # trigger conditions + detailed execution steps
    metadata.json     # name, description, tags, app, version, success rate
    references/       # screenshots, UI element templates, parameter templates

Loading strategy:
  level 1 metadata   — skill name + description injected every session
  level 2 instruction— full SKILL.md loaded via load_skill when needed
  level 3 reference  — references/* files read on demand via read_reference
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

SKILLS_DIR_DEFAULT = "data/skills"

REFERENCE_DIR = "references"
SKILL_MD = "SKILL.md"
METADATA_JSON = "metadata.json"


@dataclass
class SkillMetadata:
    """metadata.json contents."""

    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    app: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    success_rate: float = 0.0
    use_count: int = 0
    avg_duration_ms: float = 0.0
    last_used_at: float = 0.0
    status: str = "active"  # active | needs_optimization | archived

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "app": self.app,
            "version": self.version,
            "success_rate": self.success_rate,
            "use_count": self.use_count,
            "avg_duration_ms": self.avg_duration_ms,
            "last_used_at": self.last_used_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillMetadata:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            app=data.get("app", []),
            version=data.get("version", "1.0.0"),
            success_rate=float(data.get("success_rate", 0.0)),
            use_count=int(data.get("use_count", 0)),
            avg_duration_ms=float(data.get("avg_duration_ms", 0.0)),
            last_used_at=float(data.get("last_used_at", 0.0)),
            status=data.get("status", "active"),
        )


@dataclass
class Skill:
    """A single skill directory with three-level loadable parts."""

    skill_id: str
    path: Path
    metadata: SkillMetadata

    def load_instruction(self) -> str:
        """Level 2: full SKILL.md content."""
        path = self.path / SKILL_MD
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def read_reference(self, name: str) -> bytes:
        """Level 3: read a reference file (text or binary)."""
        path = self.path / REFERENCE_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"reference not found: {name}")
        return path.read_bytes()

    def list_references(self) -> list[str]:
        ref_dir = self.path / REFERENCE_DIR
        if not ref_dir.exists():
            return []
        return [p.name for p in sorted(ref_dir.iterdir()) if p.is_file()]

    def to_metadata_payload(self) -> dict[str, Any]:
        """Level 1: cheap name+description payload for prompt injection."""
        return {
            "id": self.skill_id,
            "name": self.metadata.name,
            "description": self.metadata.description[:1024],
            "tags": self.metadata.tags,
            "app": self.metadata.app,
            "version": self.metadata.version,
            "status": self.metadata.status,
        }


class SkillStore:
    """Scans, loads, saves, and tracks skills under a base directory."""

    def __init__(self, base_dir: str | Path = SKILLS_DIR_DEFAULT) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ── scanning ──

    def list_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        for entry in sorted(self._base_dir.iterdir()):
            if not entry.is_dir():
                continue
            meta_path = entry / METADATA_JSON
            if not meta_path.exists():
                continue
            try:
                meta = SkillMetadata.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, ValueError):
                logger.warning("skill.metadata_invalid", skill_id=entry.name)
                continue
            skills.append(Skill(skill_id=entry.name, path=entry, metadata=meta))
        return skills

    def get(self, skill_id: str) -> Skill | None:
        for skill in self.list_skills():
            if skill.skill_id == skill_id:
                return skill
        return None

    # ── metadata index (level 1) ──

    def metadata_index(self) -> list[dict[str, Any]]:
        """All skill names + descriptions for session-start injection."""
        return [s.to_metadata_payload() for s in self.list_skills()]

    # ── create / update ──

    def create(
        self,
        skill_id: str,
        metadata: SkillMetadata,
        instruction: str,
        references: dict[str, bytes] | None = None,
    ) -> Skill:
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", skill_id)
        skill_dir = self._base_dir / safe_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / SKILL_MD).write_text(instruction, encoding="utf-8")
        (skill_dir / METADATA_JSON).write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if references:
            ref_dir = skill_dir / REFERENCE_DIR
            ref_dir.mkdir(parents=True, exist_ok=True)
            for name, content in references.items():
                (ref_dir / name).write_bytes(content)
        return Skill(skill_id=safe_id, path=skill_dir, metadata=metadata)

    def update_instruction(self, skill_id: str, instruction: str) -> bool:
        skill = self.get(skill_id)
        if skill is None:
            return False
        (skill.path / SKILL_MD).write_text(instruction, encoding="utf-8")
        return True

    def update_metadata(self, skill_id: str, metadata: SkillMetadata) -> bool:
        skill = self.get(skill_id)
        if skill is None:
            return False
        (skill.path / METADATA_JSON).write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    def record_usage(self, skill_id: str, success: bool, duration_ms: float = 0.0) -> None:
        """Update usage stats and auto-mark skills under 60% success rate."""
        skill = self.get(skill_id)
        if skill is None:
            return
        meta = skill.metadata
        meta.use_count += 1
        if success:
            meta.success_rate = (
                meta.success_rate * (meta.use_count - 1) + 1.0
            ) / meta.use_count
        else:
            meta.success_rate = (
                meta.success_rate * (meta.use_count - 1)
            ) / meta.use_count
        meta.last_used_at = time.time()
        if meta.avg_duration_ms:
            meta.avg_duration_ms = (meta.avg_duration_ms + duration_ms) / 2
        else:
            meta.avg_duration_ms = duration_ms
        if meta.use_count >= 3 and meta.success_rate < 0.6:
            meta.status = "needs_optimization"
        elif meta.success_rate >= 0.6:
            meta.status = "active"
        self.update_metadata(skill_id, meta)


_default_skill_store: SkillStore | None = None


def get_skill_store(base_dir: str | Path = SKILLS_DIR_DEFAULT) -> SkillStore:
    global _default_skill_store
    if _default_skill_store is None:
        _default_skill_store = SkillStore(base_dir=base_dir)
    return _default_skill_store
