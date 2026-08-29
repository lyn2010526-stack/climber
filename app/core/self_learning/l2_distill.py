"""L2 — background distillation.

After every complex task (>= 3 operations), a background lightweight agent
thread reviews the whole execution (each operation, results, screenshots,
durations), decides whether a reusable pattern exists, and if so generates a
Markdown operation-skill file. The generated skill is added to the skill
library and its metadata is immediately injected into subsequent sessions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.skill_store.skill_store import SkillMetadata, SkillStore

logger = structlog.get_logger()

MIN_OPERATIONS = 3


@dataclass
class OperationRecord:
    operation: str
    result: Any = None
    screenshot: str = ""
    ts: float = field(default_factory=time.time)


@dataclass
class DistillResult:
    skill_id: str
    created: bool
    reason: str = ""


class BackgroundDistiller:
    """Fork a lightweight distillation pass over a completed task."""

    def __init__(self, store: SkillStore, min_operations: int = MIN_OPERATIONS) -> None:
        self._store = store
        self._min_operations = min_operations

    async def distill(
        self,
        task_title: str,
        operations: list[OperationRecord],
        app_list: list[str] | None = None,
    ) -> DistillResult:
        """Analyze a completed task and generate a skill if a reusable pattern exists.

        Runs in-process as a lightweight background task; callers that want a
        true fork may schedule this via asyncio.create_task.
        """
        if len(operations) < self._min_operations:
            return DistillResult(skill_id="", created=False, reason="too few operations")

        repeated = self._detect_repeatable_pattern(operations)
        if not repeated:
            return DistillResult(skill_id="", created=False, reason="no reusable pattern")

        skill_id = self._make_skill_id(task_title)
        steps = "\n".join(
            f"{i}. {op.operation}" for i, op in enumerate(operations, start=1)
        )
        instruction = self._build_instruction(task_title, steps, app_list or [])
        meta = SkillMetadata(
            name=skill_id,
            description=f"Automatically distilled from task: {task_title}",
            tags=["auto-distilled"],
            app=app_list or [],
            version="1.0.0",
            success_rate=1.0,
            use_count=0,
            status="active",
        )
        skill = self._store.create(skill_id, meta, instruction)
        logger.info("skill.l2_distilled", skill_id=skill.skill_id, ops=len(operations))
        return DistillResult(skill_id=skill.skill_id, created=True, reason="distilled")

    def _detect_repeatable_pattern(self, operations: list[OperationRecord]) -> bool:
        """A pattern is reusable when operations contain stable verb-object steps."""
        verbs = {op.operation.split()[0] if op.operation else "" for op in operations}
        meaningful = {v.lower() for v in verbs if v}
        # generic single verbs rarely form a reusable business skill
        generic = {"click", "tap", "get", "set", "return"}
        if meaningful and not meaningful.issubset(generic):
            return True
        return False

    @staticmethod
    def _make_skill_id(task_title: str) -> str:
        words = "".join(c if c.isalnum() else "_" for c in task_title.lower()).split("_")
        words = [w for w in words if w]
        return "_".join(words[:4]) or "distilled_skill"

    def _build_instruction(self, title: str, steps: str, apps: list[str]) -> str:
        app_line = ", ".join(apps) if apps else "unknown"
        return (
            f"# {title}\n\n"
            f"## Trigger\nUse this skill when: the task resembles '{title}'.\n\n"
            f"## Steps\n{steps}\n\n"
            f"## Notes\n- Applicable apps: {app_line}\n"
            "- If an element is not found, re-locate it (UI may have changed).\n"
            "- Keep a screenshot before each critical operation for audit.\n"
        )
