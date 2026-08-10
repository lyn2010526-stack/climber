"""Reflection memory — persistent critique memory for DeepRefineStrategy.

Implements the Reflexion pattern (MIT, NeurIPS 2023): after failed attempts,
generate a self-reflection that captures what went wrong and how to improve.
The reflection persists across attempts, enabling cross-round learning.

"""

from __future__ import annotations

import time

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class ReflectionEntry(BaseModel):
    """A single reflection from a failed attempt."""

    attempt: int
    timestamp: float = Field(default_factory=time.time)
    failure_reason: str
    lesson: str
    suggested_approach: str


class ReflectionMemory:
    """Persistent reflection memory for cross-attempt learning.

    Stores lessons from failed attempts and generates guidance
    for subsequent attempts.
    """

    def __init__(self, max_entries: int = 10) -> None:
        self._entries: list[ReflectionEntry] = []
        self._max_entries = max_entries

    def add_reflection(
        self,
        attempt: int,
        failure_reason: str,
        lesson: str,
        suggested_approach: str,
    ) -> None:
        """Record a reflection from a failed attempt."""
        entry = ReflectionEntry(
            attempt=attempt,
            failure_reason=failure_reason,
            lesson=lesson,
            suggested_approach=suggested_approach,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        logger.debug(
            "reflection_added",
            attempt=attempt,
            total_reflections=len(self._entries),
        )

    def generate_guidance(self) -> str:
        """Generate guidance string from all reflections for the next attempt."""
        if not self._entries:
            return ""

        lines: list[str] = ["## Lessons from Previous Attempts"]
        lines.append("Reflect on these lessons before producing your output.")
        lines.append("")

        for entry in self._entries:
            lines.append(f"### Attempt {entry.attempt}")
            lines.append(f"**Failure**: {entry.failure_reason}")
            lines.append(f"**Lesson**: {entry.lesson}")
            lines.append(f"**Do Instead**: {entry.suggested_approach}")
            lines.append("")

        lines.append("---")
        lines.append("Apply these lessons to produce a better output.")
        return "\n".join(lines)

    def get_failure_patterns(self) -> list[str]:
        """Extract recurring failure patterns."""
        return [e.failure_reason for e in self._entries]

    @property
    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
