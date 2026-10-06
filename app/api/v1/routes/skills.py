"""Skill CRUD API endpoints."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_manager import require_scopes
from sqlalchemy import select

from app.core.principal import CurrentPrincipal, Principal
from app.core.skill_composition import skill_tester, skill_version_manager
from app.schemas.api_v1.base import EmptyRequest
from app.schemas.api_v1.skills import (
    SkillCreateRequest,
    SkillTestCaseCreateRequest,
    SkillVersionCreateRequest,
)
from app.storage import async_session
from app.storage.models_platform import Skill
from app.storage.models_skills import SkillTestCase, SkillVersion

if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger(__name__)

router = APIRouter()

_PROMPT_VARIABLE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


async def _owned_skill(db: Any, skill_id: str, user_id: str) -> Skill | None:
    """Fetch a skill owned by the given user, or None."""
    return (
        await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
    ).scalar_one_or_none()


async def _require_owned_skill(db: Any, skill_id: str, user_id: str) -> Skill:
    """Fetch a skill owned by the given user, or raise 404."""
    skill = await _owned_skill(db, skill_id, user_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


async def _validated_tools(tools: list[str]) -> list[str]:
    """Check tool names against the global tool registry; raise 400 on unknowns.

    Empty and None lists pass through unchanged, keeping the existing semantics
    where a skill may be created without tool bindings.
    """
    if not tools:
        return tools
    from app.tools import tool_registry

    known = {definition.name for definition in tool_registry.list_tools()}
    unknown = sorted({name for name in tools if name not in known})
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tools: {', '.join(unknown)}",
        )
    return tools


def _json_string_list(raw: Any) -> list[str]:
    """Parse a text JSON column that stores a list of strings."""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return [raw] if raw else []
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    return [str(item) for item in raw or []]


def _static_prompt_handler(prompt_template: str) -> Callable[..., Any]:
    """Build a deterministic handler that renders the prompt template.

    Static test mode needs no LLM engine: the rendered prompt is the output,
    template variables missing from the input params fail the run, and the
    expected-substring assertion is evaluated by SkillTester on the rendered
    text.
    """

    async def _handler(**params: Any) -> str:
        variables = set(_PROMPT_VARIABLE_RE.findall(prompt_template))
        missing = sorted(variables - params.keys())
        if missing:
            raise ValueError("missing required variables: " + ", ".join(missing))
        rendered = prompt_template
        for name in variables:
            rendered = rendered.replace("{" + name + "}", str(params[name]))
        return rendered

    return _handler


@router.get("/skills")
@router.get("/skills/", include_in_schema=False)
async def list_skills(principal: CurrentPrincipal) -> list[dict[str, Any]]:
    """List the current user's skills ordered by creation date (newest first)."""
    user_id = principal.subject_id
    async with async_session() as db:
        rows = (
            (
                await db.execute(
                    select(Skill).where(Skill.user_id == user_id).order_by(Skill.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [_skill_dict(s) for s in rows]


@router.post("/skills")
@router.post("/skills/", include_in_schema=False)
async def create_skill(
    payload: SkillCreateRequest, principal: CurrentPrincipal, _auth: dict = Depends(require_scopes("write"))
) -> dict[str, Any]:
    """Create a new skill."""
    data = payload.model_dump()
    data["tools"] = await _validated_tools(data.get("tools") or [])
    user_id = principal.subject_id
    async with async_session() as db:
        skill = Skill(
            user_id=user_id,
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            prompt_template=data.get("prompt_template", ""),
            tools=data.get("tools", []),
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return _skill_dict(skill)


@router.post("/skills/{skill_id}/enable")
async def enable_skill(
    skill_id: str,
    principal: CurrentPrincipal,
    payload: EmptyRequest | None = None,
    _auth: dict = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Enable a skill by ID."""
    del payload
    return await _set_skill_enabled(skill_id, True, principal)


@router.post("/skills/{skill_id}/disable")
async def disable_skill(
    skill_id: str,
    principal: CurrentPrincipal,
    payload: EmptyRequest | None = None,
    _auth: dict = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Disable a skill by ID."""
    del payload
    return await _set_skill_enabled(skill_id, False, principal)


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: str, principal: CurrentPrincipal, _auth: dict = Depends(require_scopes("write"))
) -> dict[str, bool | str]:
    """Delete a skill by ID."""
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _owned_skill(db, skill_id, user_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        await db.delete(skill)
        await db.commit()
        return {"ok": True, "deleted": skill_id}


async def _set_skill_enabled(skill_id: str, enabled: bool, principal: Principal) -> dict[str, Any]:
    """Set a skill's enabled status.

    Args:
        skill_id: The skill ID to update.
        enabled: True to enable, False to disable.
        request: The HTTP request used to resolve the current user.

    Returns:
        A dictionary with the updated status.
    """
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _owned_skill(db, skill_id, user_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill.is_enabled = enabled
        await db.commit()
        return {"ok": True, "id": skill_id, "is_enabled": enabled}


def _skill_dict(s: Skill) -> dict[str, Any]:
    """Convert a Skill model instance to a response dictionary.

    Args:
        s: The Skill database model instance.

    Returns:
        A dictionary with skill fields for API response.
    """
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "category": s.category,
        "prompt_template": s.prompt_template,
        "tools": s.tools or [],
        "is_enabled": s.is_enabled,
        "use_count": s.use_count,
        "path": f"skills/{s.category}/{s.name}.yaml",
    }


async def _mark_active_version(db: Any, skill_id: str, version_id: str) -> list[str]:
    """Activate one version and deprecate every previously active version.

    The SkillVersion table has no dedicated deprecated_at column, so the
    existing ``is_active`` flag carries the lifecycle: exactly the version
    referenced by ``Skill.active_version_id`` is active; all other versions
    are deprecated. Returns the IDs deprecated by this call.
    """
    rows = (
        (await db.execute(select(SkillVersion).where(SkillVersion.skill_id == skill_id)))
        .scalars()
        .all()
    )
    deprecated: list[str] = []
    for row in rows:
        if row.id == version_id:
            row.is_active = True
        elif row.is_active:
            row.is_active = False
            deprecated.append(row.id)
    return deprecated


@router.post("/skills/{skill_id}/versions")
async def create_skill_version(
    skill_id: str,
    principal: CurrentPrincipal,
    payload: SkillVersionCreateRequest | None = None,
    _auth: dict = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Store the skill's current content as a new version and make it active."""
    data = payload.model_dump() if payload is not None else {}
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _require_owned_skill(db, skill_id, user_id)
        prompt = data.get("prompt")
        if prompt is None:
            prompt = skill.prompt_template or ""
        tools = data.get("tools")
        if tools is None:
            tools = list(skill.tools or [])
        else:
            tools = await _validated_tools(tools)
        existing_count = len(
            (await db.execute(select(SkillVersion.id).where(SkillVersion.skill_id == skill_id)))
            .scalars()
            .all()
        )
        version_label = data.get("version") or f"v{existing_count + 1}"
        version_id = await skill_version_manager.create_version(
            skill_id=skill_id,
            version=version_label,
            prompt=prompt,
            tools=tools,
            author=data.get("author") or user_id,
            changelog=data.get("changelog", ""),
        )
        deprecated = await _mark_active_version(db, skill_id, version_id)
        skill.active_version_id = version_id
        await db.commit()
        return {
            "ok": True,
            "skill_id": skill_id,
            "version_id": version_id,
            "version": version_label,
            "active_version_id": version_id,
            "deprecated_version_ids": deprecated,
        }


@router.get("/skills/{skill_id}/versions")
async def list_skill_versions(skill_id: str, principal: CurrentPrincipal) -> dict[str, Any]:
    """List the versions of a skill, marking the currently active one."""
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _require_owned_skill(db, skill_id, user_id)
        active_version_id = skill.active_version_id
    versions = await skill_version_manager.get_versions(skill_id)
    return {
        "skill_id": skill_id,
        "active_version_id": active_version_id,
        "versions": versions,
    }


@router.post("/skills/{skill_id}/versions/{version_id}/activate")
async def activate_skill_version(
    skill_id: str, version_id: str, principal: CurrentPrincipal, _auth: dict = Depends(require_scopes("write"))
) -> dict[str, Any]:
    """Activate a stored version and deprecate the previously active one."""
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _require_owned_skill(db, skill_id, user_id)
        version = (
            await db.execute(
                select(SkillVersion).where(
                    SkillVersion.id == version_id, SkillVersion.skill_id == skill_id
                )
            )
        ).scalar_one_or_none()
        if version is None:
            raise HTTPException(status_code=404, detail="Skill version not found")
        deprecated = await _mark_active_version(db, skill_id, version_id)
        skill.active_version_id = version_id
        await db.commit()
        return {
            "ok": True,
            "skill_id": skill_id,
            "active_version_id": version_id,
            "version": version.version,
            "deprecated_version_ids": deprecated,
        }


@router.post("/skills/{skill_id}/test-cases")
async def create_test_case(
    skill_id: str,
    principal: CurrentPrincipal,
    payload: SkillTestCaseCreateRequest | None = None,
    _auth: dict = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Add a test case for a skill."""
    data = payload.model_dump()
    user_id = principal.subject_id
    async with async_session() as db:
        await _require_owned_skill(db, skill_id, user_id)
    test_id = await skill_tester.add_test_case(
        skill_id=skill_id,
        name=data["name"],
        input_params=data["input_params"],
        expected_output_contains=data["expected_output_contains"],
        expected_tools=data["expected_tools"],
        timeout_seconds=data["timeout_seconds"],
    )
    return {"ok": True, "skill_id": skill_id, "test_case_id": test_id}


def _test_case_dict(t: SkillTestCase) -> dict[str, Any]:
    """Convert a SkillTestCase row into an API response dictionary."""
    try:
        input_params = json.loads(t.input_params or "{}")
    except ValueError:
        input_params = {}
    return {
        "id": t.id,
        "skill_id": t.skill_id,
        "name": t.name,
        "input_params": input_params if isinstance(input_params, dict) else {},
        "expected_output_contains": t.expected_output_contains or "",
        "expected_tools": _json_string_list(t.expected_tools),
        "timeout_seconds": t.timeout_seconds,
        "is_active": bool(t.is_active),
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("/skills/{skill_id}/test-cases")
async def list_test_cases(skill_id: str, principal: CurrentPrincipal) -> dict[str, Any]:
    """List the test cases of a skill."""
    user_id = principal.subject_id
    async with async_session() as db:
        await _require_owned_skill(db, skill_id, user_id)
        rows = (
            (
                await db.execute(
                    select(SkillTestCase)
                    .where(SkillTestCase.skill_id == skill_id)
                    .order_by(SkillTestCase.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return {"skill_id": skill_id, "test_cases": [_test_case_dict(row) for row in rows]}


@router.post("/skills/{skill_id}/test-cases/{case_id}/run")
async def run_test_case(
    skill_id: str, case_id: str, principal: CurrentPrincipal, _auth: dict = Depends(require_scopes("write"))
) -> dict[str, Any]:
    """Run one test case in static mode and persist a SkillTestResult.

    Static mode renders the skill's prompt template with the test case input,
    fails on missing template variables, and lets SkillTester apply the
    deterministic expected-substring assertion. No LLM engine is involved.
    """
    user_id = principal.subject_id
    async with async_session() as db:
        skill = await _require_owned_skill(db, skill_id, user_id)
        test_case = (
            await db.execute(
                select(SkillTestCase).where(
                    SkillTestCase.id == case_id, SkillTestCase.skill_id == skill_id
                )
            )
        ).scalar_one_or_none()
        if test_case is None:
            raise HTTPException(status_code=404, detail="Test case not found")
        handler = _static_prompt_handler(skill.prompt_template or "")
    result = await skill_tester.run_test(case_id, handler)
    result["source"] = "static"
    result.setdefault("skill_id", skill_id)
    return result
