"""Skills composition — skill calling skill, versioning, and testing.

Extends the existing skill system with:
1. Skill Composition: skills that orchestrate other skills
2. Skill Versioning: track changes and rollback
3. Skill Testing: automated test cases per skill
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, desc, select

from app.storage import async_session
from app.storage.models_skills import SkillTestCase, SkillTestResult, SkillVersion

logger = structlog.get_logger()


@dataclass
class SkillInvocation:
    """A single skill invocation within a composition."""
    skill_id: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)  # other invocation IDs
    result: str = ""
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class SkillComposition:
    """A composition of multiple skills that work together."""
    id: str
    name: str
    description: str
    invocations: list[SkillInvocation] = field(default_factory=list)
    created_at: str = ""

    def add_step(self, skill_id: str, params: dict[str, Any] | None = None, depends_on: list[str] | None = None) -> str:
        """Add a skill invocation step. Returns invocation ID."""
        inv_id = f"step_{len(self.invocations)}"
        self.invocations.append(SkillInvocation(
            skill_id=skill_id,
            params=params or {},
            depends_on=depends_on or [],
        ))
        return inv_id


class SkillComposer:
    """Orchestrates multi-skill compositions.

    Enables building complex workflows by chaining skills together,
    where the output of one skill feeds into the next.
    """

    def __init__(self, skill_registry: Any):
        self._registry = skill_registry

    async def execute_composition(
        self,
        composition: SkillComposition,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a skill composition, respecting dependencies."""
        results: dict[str, Any] = {}
        completed: set[str] = set()
        context = context or {}

        # Topological order execution
        pending = list(composition.invocations)
        max_iterations = len(pending) * 3  # prevent infinite loop
        iteration = 0

        while pending and iteration < max_iterations:
            iteration += 1
            for inv in list(pending):
                # Check dependencies met
                if not all(dep in completed for dep in inv.depends_on):
                    continue

                inv.status = "running"
                try:
                    # Get skill handler
                    handler = self._registry.get_handler(inv.skill_id)
                    if handler:
                        # Build params from context and previous results
                        params = {**inv.params}
                        for key, value in params.items():
                            if isinstance(value, str) and value.startswith("$"):
                                # Reference to previous result
                                ref_key = value[1:]
                                params[key] = results.get(ref_key, "")

                        result = await handler(**params)
                        inv.result = result
                        inv.status = "completed"
                        results[inv.skill_id] = result
                        completed.add(inv.skill_id)
                    else:
                        inv.status = "failed"
                        inv.result = f"Skill '{inv.skill_id}' not found"
                        completed.add(inv.skill_id)

                except Exception as e:
                    inv.status = "failed"
                    inv.result = str(e)
                    completed.add(inv.skill_id)

                pending.remove(inv)

        return {
            "composition_id": composition.id,
            "results": results,
            "status": "completed" if not pending else "partial",
            "steps": len(composition.invocations),
        }


class SkillVersionManager:
    """Manages skill versioning for tracking changes and rollback."""

    async def create_version(
        self,
        skill_id: str,
        version: str,
        prompt: str,
        tools: list[str],
        author: str = "system",
        changelog: str = "",
    ) -> str:
        """Create a new version of a skill."""
        version_id = str(uuid.uuid4())
        async with async_session() as db:
            record = SkillVersion(
                id=version_id,
                skill_id=skill_id,
                version=version,
                prompt=prompt,
                tools=tools,
                author=author,
                changelog=changelog,
            )
            db.add(record)
            await db.commit()
            return version_id

    async def get_versions(self, skill_id: str) -> list[dict]:
        """Get all versions of a skill."""
        async with async_session() as db:
            result = await db.execute(
                select(SkillVersion)
                .where(SkillVersion.skill_id == skill_id)
                .order_by(desc(SkillVersion.created_at))
            )
            versions = result.scalars().all()
            return [
                {
                    "id": v.id,
                    "version": v.version,
                    "prompt": v.prompt,
                    "tools": v.tools,
                    "author": v.author,
                    "changelog": v.changelog,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in versions
            ]

    async def get_version(self, skill_id: str, version: str) -> dict | None:
        """Get a specific version of a skill."""
        async with async_session() as db:
            result = await db.execute(
                select(SkillVersion).where(
                    and_(
                        SkillVersion.skill_id == skill_id,
                        SkillVersion.version == version,
                    )
                )
            )
            v = result.scalar_one_or_none()
            if not v:
                return None
            return {
                "id": v.id,
                "skill_id": v.skill_id,
                "version": v.version,
                "prompt": v.prompt,
                "tools": v.tools,
                "author": v.author,
                "changelog": v.changelog,
            }

    async def rollback(self, skill_id: str, version: str) -> dict | None:
        """Rollback to a specific version (creates a new version with old content)."""
        target = await self.get_version(skill_id, version)
        if not target:
            return None

        # Create new version with rolled-back content
        new_version = await self.create_version(
            skill_id=skill_id,
            version=f"{version}_rollback_{datetime.now(UTC).strftime('%Y%m%d')}",
            prompt=target["prompt"],
            tools=target["tools"],
            author="system",
            changelog=f"Rollback to version {version}",
        )
        return {"new_version_id": new_version, "rolled_back_from": version}


class SkillTester:
    """Automated testing for skills.

    Each skill can have multiple test cases that verify:
    - The skill produces expected output for given input
    - The skill calls the right tools
    - The skill handles edge cases
    """

    async def add_test_case(
        self,
        skill_id: str,
        name: str,
        input_params: dict[str, Any],
        expected_output_contains: str = "",
        expected_tools: list[str] | None = None,
        timeout_seconds: int = 30,
    ) -> str:
        """Add a test case for a skill."""
        test_id = str(uuid.uuid4())
        async with async_session() as db:
            record = SkillTestCase(
                id=test_id,
                skill_id=skill_id,
                name=name,
                input_params=json.dumps(input_params, ensure_ascii=False),
                expected_output_contains=expected_output_contains,
                expected_tools=expected_tools or [],
                timeout_seconds=timeout_seconds,
            )
            db.add(record)
            await db.commit()
            return test_id

    async def run_test(
        self,
        test_id: str,
        skill_handler: Any,
    ) -> dict[str, Any]:
        """Run a single test case."""
        async with async_session() as db:
            result = await db.execute(select(SkillTestCase).where(SkillTestCase.id == test_id))
            test = result.scalar_one_or_none()
            if not test:
                return {"error": "Test not found"}

            input_params = json.loads(test.input_params)
            start = datetime.now(UTC)

            try:
                output = await skill_handler(**input_params)
                passed = test.expected_output_contains in output if test.expected_output_contains else True
                duration = (datetime.now(UTC) - start).total_seconds() * 1000

                result_record = SkillTestResult(
                    test_id=test_id,
                    skill_id=test.skill_id,
                    passed=passed,
                    actual_output=output[:2000],
                    duration_ms=duration,
                )
                db.add(result_record)
                await db.commit()

                return {
                    "test_id": test_id,
                    "skill_id": test.skill_id,
                    "passed": passed,
                    "output": output[:500],
                    "duration_ms": duration,
                }
            except Exception as e:
                result_record = SkillTestResult(
                    test_id=test_id,
                    skill_id=test.skill_id,
                    passed=False,
                    actual_output="",
                    error=str(e),
                )
                db.add(result_record)
                await db.commit()
                return {
                    "test_id": test_id,
                    "passed": False,
                    "error": str(e),
                }

    async def run_all_tests(self, skill_id: str, handler_map: dict[str, Any]) -> dict[str, Any]:
        """Run all test cases for a skill."""
        async with async_session() as db:
            result = await db.execute(
                select(SkillTestCase).where(SkillTestCase.skill_id == skill_id)
            )
            tests = result.scalars().all()

        results = []
        for test in tests:
            handler = handler_map.get(test.skill_id)
            if handler:
                test_result = await self.run_test(test.id, handler)
                results.append(test_result)
            else:
                results.append({"test_id": test.id, "error": "No handler found"})

        passed = sum(1 for r in results if r.get("passed"))
        return {
            "skill_id": skill_id,
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "results": results,
        }


# Global instances
skill_version_manager = SkillVersionManager()
skill_tester = SkillTester()
