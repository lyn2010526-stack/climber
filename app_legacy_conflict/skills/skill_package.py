"""Skill package schema and serialization.

Defines the .skill.json format for import/export/sharing.
Based on MonkeyCode Skill format + OpenClaw SOUL.md standardization.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    RESTRICTED = "restricted"


class FailureStrategy(str, Enum):
    RETRY = "retry"
    ABORT = "abort"
    ASK_USER = "ask_user"


class SkillPackage(BaseModel):
    """Serialized skill package format (.skill.json).

    This is the canonical format for importing, exporting, and sharing skills.
    """

    schema_version: str = "1.0"
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    category: str = "core"
    icon: str = ""
    system_prompt: str = ""
    tags: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    mcp_dependencies: list[str] = Field(default_factory=list)
    tool_whitelist: list[str] = Field(default_factory=list)
    tool_blacklist: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    max_iterations: int = 10
    timeout_seconds: int = 300
    failure_strategy: FailureStrategy = FailureStrategy.ASK_USER
    requires_admin: bool = False

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_json(cls, data: str) -> "SkillPackage":
        return cls.model_validate_json(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillPackage":
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, path: Path | str) -> "SkillPackage":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Skill package not found: {p}")
        return cls.from_json(p.read_text(encoding="utf-8"))

    def save_to_file(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")

    def validate_package(self) -> list[str]:
        """Validate package integrity. Returns list of issues (empty = valid)."""
        issues: list[str] = []
        if not self.id or not self.id.strip():
            issues.append("Missing skill id")
        if not self.name or not self.name.strip():
            issues.append("Missing skill name")
        if not self.system_prompt or not self.system_prompt.strip():
            issues.append("Missing system_prompt")
        if self.max_iterations < 1:
            issues.append("max_iterations must be >= 1")
        if self.timeout_seconds < 1:
            issues.append("timeout_seconds must be >= 1")
        if self.risk_level == RiskLevel.RESTRICTED:
            self.requires_admin = True
        return issues
