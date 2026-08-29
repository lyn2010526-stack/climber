"""Permission management API endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1.chat import get_engine
from app.core.auth import get_current_user
from app.core.permission_rules import (
    PermissionConfig,
    PermissionMode,
    PermissionRule,
    RuleDecision,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


class PermissionResolveRequest(BaseModel):
    tool_call_id: str
    decision: str


class PermissionRuleSchema(BaseModel):
    decision: str
    tool: str
    pattern: str | None = None
    description: str = ""


class PermissionConfigUpdate(BaseModel):
    mode: Literal[
        PermissionMode.DEFAULT,
        PermissionMode.ACCEPT_EDITS,
        PermissionMode.PLAN,
        PermissionMode.AUTO,
    ] | None = None
    rules: list[PermissionRuleSchema] | None = None
    allowed_tools: list[str] | None = None
    denied_tools: list[str] | None = None


@router.post("/resolve")
async def resolve_permission(
    request: PermissionResolveRequest,
    user_id: str = Depends(get_current_user),
):
    engine = get_engine()
    tool_call_id = request.tool_call_id
    decision = request.decision

    if decision not in ("allow", "deny"):
        raise HTTPException(status_code=400, detail=f"Invalid decision: {decision}")

    success = await engine.resolve_permission_async(tool_call_id, decision, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"No pending permission request for tool_call_id: {tool_call_id}")

    return {"status": "resolved", "tool_call_id": tool_call_id, "decision": decision}


@router.get("/config")
async def get_permission_config():
    engine = get_engine()
    config = engine.get_permission_config()

    return {
        "mode": config.mode.value,
        "rules": [
            {
                "decision": r.decision.value,
                "tool": r.tool,
                "pattern": r.pattern,
                "description": r.description,
            }
            for r in config.rules
        ],
        "allowed_tools": config.allowed_tools,
        "denied_tools": config.denied_tools,
    }


@router.put("/config")
async def update_permission_config(update: PermissionConfigUpdate):
    engine = get_engine()
    current = engine.get_permission_config()

    mode = current.mode
    if update.mode:
        try:
            mode = PermissionMode(update.mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {update.mode}") from None

    rules = current.rules
    if update.rules is not None:
        rules = []
        for r in update.rules:
            try:
                decision = RuleDecision(r.decision)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid rule decision: {r.decision}") from None
            rules.append(PermissionRule(
                decision=decision,
                tool=r.tool,
                pattern=r.pattern,
                description=r.description,
            ))

    allowed_tools = current.allowed_tools
    if update.allowed_tools is not None:
        allowed_tools = update.allowed_tools

    denied_tools = current.denied_tools
    if update.denied_tools is not None:
        denied_tools = update.denied_tools

    new_config = PermissionConfig(
        mode=mode,
        rules=rules,
        allowed_tools=allowed_tools,
        denied_tools=denied_tools,
    )
    engine.update_permission_config(new_config)

    return {"status": "updated", "mode": mode.value}
