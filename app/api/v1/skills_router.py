"""Skill API endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.v1.common import current_user_id
from app.api.v1.helpers import DEFAULT_USER
from app.api.v1.helpers import payload as _payload
from app.core.api_key_crypto import decrypt_api_key
from app.core.task_worker import TaskStatus, task_manager
from app.storage import async_session
from app.storage.database import Agent, ApiKey
from app.storage.models_platform import Skill

router = APIRouter()

_FACTORY_TOOLS = {
    "code_executor": ["run_command"],
    "web_search": ["web_search"],
    "file_manager": ["read_file", "write_file", "list_files"],
    "data_analyzer": ["calculator"],
    "task_planner": [],
    "code_reviewer": ["read_file", "list_files"],
}

_FACTORY_PROMPTS = {
    "senior-engineer": "Act as a senior software engineer. Plan carefully and produce a complete, verifiable result.",
    "code-reviewer": "Act as a code reviewer. Focus on correctness, regressions, security, and missing tests.",
    "architect": "Act as a system architect. Focus on clear boundaries, tradeoffs, and maintainability.",
    "research-analyst": "Act as a research analyst. Distinguish evidence, assumptions, and conclusions.",
    "data-scientist": "Act as a data scientist. Use reproducible analysis and explain the evidence.",
}


def _sse(event_type: str, data: dict[str, Any]) -> str:
    payload = json.dumps({"type": event_type, "data": data})
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _factory_agent_payload(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(data.get("agent_id") or "").strip()
    requested_provider = str(data.get("provider") or "").strip()
    requested_model = str(data.get("model") or "").strip()
    if bool(requested_provider) != bool(requested_model):
        raise HTTPException(status_code=422, detail="provider and model must be selected together")
    if agent_id and requested_provider:
        raise HTTPException(status_code=422, detail="Select either an agent or a provider/model pair")

    async with async_session() as db:
        agent_query = (
            select(Agent)
            .where(Agent.user_id == user_id, Agent.is_active)
            .order_by(Agent.created_at.desc(), Agent.id.desc())
        )
        if agent_id:
            agent_query = agent_query.where(Agent.id == agent_id)
        agents = (await db.scalars(agent_query)).all()
        if agent_id and not agents:
            raise HTTPException(status_code=404, detail="Active agent not found for current owner")
        keys = (
            await db.scalars(
                select(ApiKey)
                .where(ApiKey.user_id == user_id, ApiKey.is_active)
                .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
            )
        ).all()

        # A newer incomplete agent must not hide an older configured agent.
        candidates = [None] if requested_provider else agents
        credential_error = ""
        for agent in candidates:
            provider = (agent.provider if agent else requested_provider).strip()
            model = (agent.model_id if agent else requested_model).strip()
            if not provider or not model:
                continue
            try:
                api_key = decrypt_api_key(agent.api_key_encrypted or "").strip() if agent else ""
            except ValueError as exc:
                credential_error = str(exc)
                api_key = ""
            base_url = agent.base_url if agent else None
            if not api_key:
                for key in keys:
                    if key.provider != provider:
                        continue
                    try:
                        api_key = decrypt_api_key(key.api_key_encrypted or "").strip()
                    except ValueError as exc:
                        credential_error = str(exc)
                        continue
                    if api_key or provider == "ollama":
                        base_url = base_url or key.base_url
                        break
            # Keyless Ollama is a configuration option, not a health check.
            if api_key or provider == "ollama":
                break
        else:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Configure an active agent with a model and matching provider API key "
                    "for the current owner, or select a provider and model using a saved API key. "
                    "Open API Keys (apikeys) to configure credentials."
                    + (f" {credential_error}" if credential_error else "")
                ),
            )
        agent_tools = list(agent.tool_ids or []) if agent else []

    requested_tools = [
        tool
        for skill in data.get("skills", [])
        for tool in _FACTORY_TOOLS.get(str(skill), [])
    ]
    tools = list(dict.fromkeys(requested_tools or agent_tools))
    prompt_name = str(data.get("prompt_template", "senior-engineer"))
    system_prompt = _FACTORY_PROMPTS.get(prompt_name, _FACTORY_PROMPTS["senior-engineer"])
    if agent and agent.system_prompt:
        system_prompt = f"{agent.system_prompt}\n\n{system_prompt}"

    return {
        "objective": str(data.get("goal", "")).strip(),
        "user_id": user_id,
        "agent_id": agent.id if agent else None,
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "system_prompt": system_prompt,
        "tools": tools,
        "factory_skills": [str(skill) for skill in data.get("skills", [])],
        "max_steps": 10,
    }


def _skill_dict(s: Skill) -> dict[str, Any]:
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


@router.get("/skills")
@router.get("/skills/")
async def list_skills() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(Skill).order_by(Skill.created_at.desc()))).scalars().all()
        return [_skill_dict(s) for s in rows]


@router.post("/skills")
@router.post("/skills/")
async def create_skill(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    async with async_session() as db:
        skill = Skill(
            user_id=DEFAULT_USER,
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


async def _set_skill_enabled(skill_id: str, enabled: bool, user_id: str) -> dict:
    async with async_session() as db:
        skill = (
            await db.execute(
                select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id)
            )
        ).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        skill.is_enabled = enabled
        await db.commit()
        return {"ok": True, "id": skill_id, "is_enabled": enabled}


@router.post("/skills/{skill_id}/enable")
async def enable_skill(skill_id: str, request: Request) -> dict:
    return await _set_skill_enabled(skill_id, True, current_user_id(request))


@router.post("/skills/{skill_id}/disable")
async def disable_skill(skill_id: str, request: Request) -> dict:
    return await _set_skill_enabled(skill_id, False, current_user_id(request))


@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str, request: Request) -> dict:
    user_id = current_user_id(request)
    async with async_session() as db:
        skill = (
            await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
        ).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        await db.delete(skill)
        await db.commit()
        return {"ok": True, "deleted": skill_id}


@router.patch("/skills/{skill_id}")
async def update_skill(skill_id: str, request: Request) -> dict[str, Any]:
    data = await _payload(request)
    user_id = current_user_id(request)
    async with async_session() as db:
        skill = (
            await db.execute(select(Skill).where(Skill.id == skill_id, Skill.user_id == user_id))
        ).scalar_one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        if "name" in data:
            skill.name = data["name"]
        if "description" in data:
            skill.description = data["description"]
        if "category" in data:
            skill.category = data["category"]
        if "prompt_template" in data:
            skill.prompt_template = data["prompt_template"]
        if "tools" in data:
            skill.tools = data["tools"]
        if "enabled" in data:
            skill.is_enabled = bool(data["enabled"])
        await db.commit()
        await db.refresh(skill)
        return _skill_dict(skill)


@router.post("/skills/autonomous/run")
async def run_autonomous_skill(request: Request) -> StreamingResponse:
    data = await _payload(request)
    goal = str(data.get("goal", "")).strip()
    if not goal:
        raise HTTPException(status_code=422, detail="goal is required")

    owner_id = current_user_id(request)
    task_payload = await _factory_agent_payload(owner_id, data)
    task_id = await task_manager.submit(
        "factory_run", task_payload, owner_id=owner_id
    )

    async def stream() -> AsyncIterator[str]:
        queue = task_manager.subscribe(task_id)
        try:
            yield _sse("factory_config", {
                "task_id": task_id,
                "agent_id": task_payload["agent_id"],
                "provider": task_payload["provider"],
                "model": task_payload["model"],
            })
            while True:
                if await request.is_disconnected():
                    await task_manager.cancel(task_id)
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield _sse(event["type"], event["data"])
                except TimeoutError:
                    pass
                status = await task_manager.get_status(
                    task_id, owner_id=owner_id
                )
                if status is None or status["status"] in {
                    TaskStatus.COMPLETED.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.CANCELLED.value,
                }:
                    while not queue.empty():
                        event = queue.get_nowait()
                        yield _sse(event["type"], event["data"])
                    if status is None:
                        yield _sse("factory_failed", {
                            "task_id": task_id,
                            "error": "Factory task status is unavailable",
                        })
                    elif status["status"] in {TaskStatus.FAILED.value, TaskStatus.CANCELLED.value}:
                        yield _sse("factory_failed", {
                            "task_id": task_id,
                            "status": status["status"],
                            "error": status.get("error") or status["status"],
                        })
                    else:
                        yield _sse("factory_completed", {"task_id": task_id})
                    break
        except asyncio.CancelledError:
            await task_manager.cancel(task_id)
            raise
        finally:
            task_manager.unsubscribe(task_id, queue)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
