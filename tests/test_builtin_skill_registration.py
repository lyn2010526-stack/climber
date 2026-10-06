"""Tests for wiring the builtin skills into the runtime SkillRegistry.

Covers the single registration entry point in app.skills.definitions:
declared-vs-registered parity, per-skill assertions driven by the real
definition list, idempotency, and failure isolation.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.skills.definitions import (
    BUILTIN_HANDLER_MAP,
    BUILTIN_SKILLS,
    builtin_skill_ids,
    register_builtin_skills,
)
from app.skills.registry import SkillCategory, SkillInfo, SkillRegistry

DECLARED_IDS = builtin_skill_ids()


def test_definitions_declare_unique_skill_ids() -> None:
    assert DECLARED_IDS
    assert len(DECLARED_IDS) == 29
    assert len(DECLARED_IDS) == len(set(DECLARED_IDS))
    assert set(BUILTIN_HANDLER_MAP) == set(DECLARED_IDS)


def test_discipline_skills_are_declared_with_expected_tags() -> None:
    by_id = {info.id: info for info in BUILTIN_SKILLS}
    assert {"verification", "quality"} <= set(by_id["verification_discipline"].tags)
    assert {"search", "research"} <= set(by_id["search_discipline"].tags)
    assert {"ui", "design"} <= set(by_id["ui_design_discipline"].tags)
    assert by_id["verification_discipline"].name
    assert by_id["search_discipline"].system_prompt
    assert by_id["ui_design_discipline"].system_prompt


def test_research_derived_skills_declare_bounded_contracts() -> None:
    by_id = {info.id: info for info in BUILTIN_SKILLS}
    assert {"delegation", "verification"} <= set(by_id["delegation_packet"].tags)
    assert {"memory", "retrieval"} <= set(by_id["typed_memory_recall"].tags)
    assert "acceptance criteria" in by_id["delegation_packet"].system_prompt
    assert "LOG" in by_id["typed_memory_recall"].system_prompt


def test_registration_covers_every_declared_skill() -> None:
    registry = SkillRegistry()
    register_builtin_skills(registry)

    registered_ids = [skill["id"] for skill in registry.list_skills()]
    assert sorted(registered_ids) == sorted(DECLARED_IDS)
    assert len(registered_ids) == len(BUILTIN_SKILLS)


@pytest.mark.parametrize("skill_id", DECLARED_IDS)
def test_declared_skill_is_registered_with_handler(skill_id: str) -> None:
    registry = SkillRegistry()
    register_builtin_skills(registry)

    info = registry.get(skill_id)
    assert info is not None
    assert info.id == skill_id
    assert info.category in set(SkillCategory)
    assert registry.get_handler(skill_id) is BUILTIN_HANDLER_MAP[skill_id]


def test_registration_is_idempotent() -> None:
    registry = SkillRegistry()
    register_builtin_skills(registry)
    first = registry.list_skills()

    second_pass = register_builtin_skills(registry)

    assert second_pass == 0
    assert registry.list_skills() == first


def test_repeated_constructor_registrations_keep_count_stable() -> None:
    registry = SkillRegistry()
    for _ in range(3):
        register_builtin_skills(registry)

    assert len(registry.list_skills()) == len(BUILTIN_SKILLS)


def test_existing_registration_is_preserved() -> None:
    custom = SkillInfo(
        id=DECLARED_IDS[0],
        name="Override",
        description="Overrides a builtin",
        category=SkillCategory.CORE,
    )

    async def sentinel_handler(value: str = "") -> str:
        return value

    registry = SkillRegistry()
    registry.register(custom, sentinel_handler)

    assert register_builtin_skills(registry) == len(DECLARED_IDS) - 1
    preserved = registry.get(custom.id)
    assert preserved is not None
    assert preserved.name == "Override"
    assert registry.get_handler(custom.id) is sentinel_handler


def test_skill_without_handler_is_skipped_and_others_still_register(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_id = DECLARED_IDS[0]
    handlers = {k: v for k, v in BUILTIN_HANDLER_MAP.items() if k != missing_id}
    monkeypatch.setattr("app.skills.definitions.BUILTIN_HANDLER_MAP", handlers)

    registry = SkillRegistry()
    registered = register_builtin_skills(registry)

    assert registered == len(DECLARED_IDS) - 1
    assert registry.get(missing_id) is None
    assert registry.get_handler(missing_id) is None
    for skill_id in DECLARED_IDS[1:]:
        assert registry.get_handler(skill_id) is handlers[skill_id]


def test_failing_registration_does_not_block_remaining_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_id = DECLARED_IDS[0]
    original_register = SkillRegistry.register

    def _register(
        self: SkillRegistry, skill: SkillInfo, handler: Callable | None = None
    ) -> None:
        if skill.id == broken_id:
            raise RuntimeError("registration exploded")
        original_register(self, skill, handler)

    monkeypatch.setattr(SkillRegistry, "register", _register)

    registry = SkillRegistry()
    registered = register_builtin_skills(registry)

    assert registered == len(DECLARED_IDS) - 1
    assert registry.get(broken_id) is None
    for skill_id in DECLARED_IDS[1:]:
        assert registry.get_handler(skill_id) is BUILTIN_HANDLER_MAP[skill_id]
