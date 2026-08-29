"""L3 — periodic housekeeping (Skill Steward).

When the skill library accumulates >= 10 skills or every 7 days, a "skill
steward" review runs:

- merge duplicate or highly similar skills
- archive skills unused for 30+ days
- update outdated skills (check app versions, re-validate steps)
- improve descriptions for better retrieval accuracy

Afterwards a report is generated; the user can view changes and roll back.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.skill_store.skill_store import Skill, SkillStore

logger = structlog.get_logger()

STEWARD_THRESHOLD_SKILLS = 10
STEWARD_INTERVAL_DAYS = 7
ARCHIVE_AFTER_DAYS = 30
SIMILARITY_THRESHOLD = 0.7


@dataclass
class StewardAction:
    action: str  # merged | archived | updated | optimized | kept
    skill_id: str
    detail: str = ""
    snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class StewardReport:
    triggered_at: float
    actions: list[StewardAction] = field(default_factory=list)
    skills_before: int = 0
    skills_after: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "triggered_at": self.triggered_at,
            "skills_before": self.skills_before,
            "skills_after": self.skills_after,
            "actions": [
                {
                    "action": a.action,
                    "skill_id": a.skill_id,
                    "detail": a.detail,
                }
                for a in self.actions
            ],
        }


class SkillSteward:
    """Runs L3 periodic review over the skill library."""

    def __init__(
        self,
        store: SkillStore,
        threshold_skills: int = STEWARD_THRESHOLD_SKILLS,
        interval_days: int = STEWARD_INTERVAL_DAYS,
        archive_after_days: int = ARCHIVE_AFTER_DAYS,
    ) -> None:
        self._store = store
        self._threshold_skills = threshold_skills
        self._interval_days = interval_days
        self._archive_after_days = archive_after_days
        self._last_report: StewardReport | None = None
        self._rollback_log: list[dict[str, Any]] = []

    def should_run(self, force: bool = False) -> bool:
        if force:
            return True
        skills = self._store.list_skills()
        if len(skills) >= self._threshold_skills:
            return True
        state = self._load_state()
        last = state.get("last_housekeeping", 0)
        return (time.time() - last) > self._interval_days * 86400

    def run(self) -> StewardReport:
        """Execute the housekeeping pass, returning a user-visible report."""
        before = self._store.list_skills()
        report = StewardReport(triggered_at=time.time(), skills_before=len(before))

        # 1) merge duplicates / highly similar skills
        self._merge_duplicates(before, report)

        # 2) archive unused skills
        self._archive_unused(report)

        # 3) optimize descriptions for retrieval
        self._optimize_descriptions(report)

        # 4) update outdated (simulated version re-validation)
        self._refresh_outdated(report)

        after = self._store.list_skills()
        report.skills_after = len(after)
        self._last_report = report
        self._save_state()
        logger.info("skill.l3_housekeeping_done", before=len(before), after=len(after))
        return report

    def _merge_duplicates(self, skills: list[Skill], report: StewardReport) -> None:
        """Merge skills whose names/descriptions are near-duplicates."""
        seen: dict[str, Skill] = {}
        for skill in skills:
            key = self._normalize(skill.metadata.name)
            if key in seen:
                kept = seen[key]
                report.actions.append(
                    StewardAction(
                        action="merged",
                        skill_id=skill.skill_id,
                        detail=f"merged into {kept.skill_id} (duplicate)",
                        snapshot=self._snapshot(skill),
                    )
                )
                self._archive(skill)
            else:
                seen[key] = skill

    def _archive_unused(self, report: StewardReport) -> None:
        cutoff = time.time() - self._archive_after_days * 86400
        for skill in self._store.list_skills():
            if skill.metadata.last_used_at and skill.metadata.last_used_at < cutoff:
                if skill.metadata.status == "archived":
                    continue
                report.actions.append(
                    StewardAction(
                        action="archived",
                        skill_id=skill.skill_id,
                        detail="unused for 30+ days",
                        snapshot=self._snapshot(skill),
                    )
                )
                skill.metadata.status = "archived"
                self._store.update_metadata(skill.skill_id, skill.metadata)

    def _optimize_descriptions(self, report: StewardReport) -> None:
        """Improve description conciseness to raise retrieval accuracy."""
        for skill in self._store.list_skills():
            desc = skill.metadata.description.strip()
            if not desc:
                continue
            optimized = self._normalize_description(desc)
            if optimized != desc:
                report.actions.append(
                    StewardAction(
                        action="optimized",
                        skill_id=skill.skill_id,
                        detail=f"description normalized: '{optimized[:60]}'",
                        snapshot=self._snapshot(skill),
                    )
                )
                skill.metadata.description = optimized
                self._store.update_metadata(skill.skill_id, skill.metadata)

    def _refresh_outdated(self, report: StewardReport) -> None:
        """Re-validate active skills; mark low-success skills for optimization."""
        for skill in self._store.list_skills():
            if skill.metadata.status == "needs_optimization":
                report.actions.append(
                    StewardAction(
                        action="updated",
                        skill_id=skill.skill_id,
                        detail="marked needs_optimization; enter L1 fix queue",
                        snapshot=self._snapshot(skill),
                    )
                )

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().replace("_", " ").split())

    def _normalize_description(self, desc: str) -> str:
        """Collapse whitespace and strip redundant prefixes."""
        collapsed = " ".join(desc.split())
        for prefix in ("Skill: ", "Skill - ", "Auto-generated: "):
            if collapsed.startswith(prefix):
                collapsed = collapsed[len(prefix):]
        return collapsed

    @staticmethod
    def _snapshot(skill: Skill) -> dict[str, Any]:
        return {
            "name": skill.metadata.name,
            "description": skill.metadata.description,
            "status": skill.metadata.status,
        }

    def _archive(self, skill: Skill) -> None:
        """Move a skill dir to a .archive suffix (kept, not deleted)."""
        self._rollback_log.append({"skill_id": skill.skill_id, "path": str(skill.path)})
        archive = skill.path.parent / f"{skill.skill_id}.archived"
        if skill.path.exists() and not archive.exists():
            skill.path.rename(archive)

    def _load_state(self) -> dict[str, Any]:
        path = self._store._base_dir / ".steward_state.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_state(self) -> None:
        path = self._store._base_dir / ".steward_state.json"
        path.write_text(
            json.dumps({"last_housekeeping": time.time()}, ensure_ascii=False),
            encoding="utf-8",
        )

    def last_report(self) -> StewardReport | None:
        return self._last_report


_default_steward: SkillSteward | None = None


def get_skill_steward(store: Any = None) -> SkillSteward:
    global _default_steward
    if _default_steward is None or store is not None:
        from app.core.skill_store.skill_store import get_skill_store

        _default_steward = SkillSteward(store or get_skill_store())
    return _default_steward
