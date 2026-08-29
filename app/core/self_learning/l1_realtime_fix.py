"""L1 — realtime fix.

When a skill fails mid-execution (wrong coordinates, UI changed after an app
update, element not found), analyze the failure, patch the skill file
(coordinates / selectors / steps), retry up to ``max_retries`` times, and
record each fix in the skill's version history for rollback.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.skill_store.skill_store import SkillStore

logger = structlog.get_logger()


@dataclass
class FixRecord:
    skill_id: str
    reason: str
    patch: str
    old_instruction: str
    new_instruction: str
    ts: float = field(default_factory=time.time)


class RealtimeFixer:
    """Applies L1 realtime fixes to failing skills with version history."""

    def __init__(self, store: SkillStore, max_retries: int = 3) -> None:
        self._store = store
        self._max_retries = max_retries
        self._history: list[FixRecord] = []

    def fix(
        self,
        skill_id: str,
        error: str,
        old_instruction: str,
    ) -> tuple[bool, str]:
        """Attempt a fix; returns (fixed, new_instruction).

        The fix is a best-effort textual correction based on the error
        message (e.g. updating coordinates or selectors), limited to
        ``max_retries`` patch attempts.
        """
        attempts = 0
        current = old_instruction
        while attempts < self._max_retries:
            patched = self._apply_patch(current, error, skill_id)
            if patched == current or not patched:
                break
            current = patched
            attempts += 1
        if current == old_instruction:
            return False, old_instruction
        record = FixRecord(
            skill_id=skill_id,
            reason=error,
            patch=f"auto-fix #{attempts} for error: {error[:120]}",
            old_instruction=old_instruction,
            new_instruction=current,
        )
        self._history.append(record)
        if self._store.update_instruction(skill_id, current):
            logger.info("skill.l1_fixed", skill_id=skill_id, attempts=attempts)
        return True, current

    def _apply_patch(self, instruction: str, error: str, skill_id: str) -> str:
        """Heuristic patch: try to correct obvious structural issues."""
        patched = instruction
        # If the error mentions a missing/invalid element, add a "retry/verify
        # step" hint to the skill's error-handling section if absent.
        if re.search(r"element not found|not found|timeout", error, re.IGNORECASE):
            hint = "\n- If the element is not found, re-locate it (UI may have changed) before continuing.\n"
            if "not found" not in patched.lower():
                patched = patched + hint
        # If coordinates are referenced and a coordinate error is reported,
        # normalize "click( x, y )" spacing which is a common typo source.
        if re.search(r"coordinate|invalid position|out of bounds", error, re.IGNORECASE):
            patched = re.sub(r"click\(\s*(\d+)\s*,\s*(\d+)\s*\)", r"click(\1, \2)", patched)
        return patched

    def history(self) -> list[dict[str, Any]]:
        return [
            {
                "skill_id": r.skill_id,
                "reason": r.reason,
                "patch": r.patch,
                "ts": r.ts,
            }
            for r in self._history
        ]

    def rollback(self, skill_id: str) -> bool:
        """Roll back the most recent fix for a skill."""
        for record in reversed(self._history):
            if record.skill_id == skill_id:
                restored = self._store.update_instruction(skill_id, record.old_instruction)
                if restored:
                    self._history.remove(record)
                    return True
        return False
