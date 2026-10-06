"""Permission management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1.chat import get_engine
from app.core.auth_manager import get_current_user, require_admin, require_scopes
from app.core.permission_rules import (
    PermissionConfig,
    PermissionMode,
    PermissionRule,
    PermissionTier,
    RuleDecision,
)

router = APIRouter()


class PermissionResolveRequest(BaseModel):
    tool_call_id: str
    decision: str


class PermissionRuleSchema(BaseModel):
    decision: str
    tool: str
    pattern: str | None = None
    description: str = ""


class PermissionConfigUpdate(BaseModel):
    mode: str | None = None
    tier: str | None = None
    rules: list[PermissionRuleSchema] | None = None
    allowed_tools: list[str] | None = None
    denied_tools: list[str] | None = None


@router.post("/resolve")
async def resolve_permission(
    request: PermissionResolveRequest,
    _user: str = Depends(get_current_user),
    _auth: dict = Depends(require_scopes("write")),
):
    engine = get_engine()
    tool_call_id = request.tool_call_id
    decision = request.decision

    if decision not in ("allow", "allow_session", "allow_always", "deny"):
        raise HTTPException(status_code=400, detail=f"Invalid decision: {decision}")

    success = engine.resolve_permission(tool_call_id, decision, owner_id=_auth["id"])
    if not success:
        raise HTTPException(status_code=404, detail=f"No pending permission request for tool_call_id: {tool_call_id}")

    return {"status": "resolved", "tool_call_id": tool_call_id, "decision": decision}


@router.get("/config")
async def get_permission_config(_auth: dict = Depends(require_admin())):
    # Reading the policy discloses the enforced mode together with the
    # allowed_tools/denied_tools allow- and deny-lists, so this endpoint carries
    # the same admin gate as the write path below. The path is absent from
    # `auth_public_endpoints` and from the middleware's public prefixes, and the
    # frontend reaches it through the authenticated API client, so nothing here
    # is designed to be readable anonymously.
    # `require_admin` is a dependency factory: it has to be called here, and
    # passing the bare function would hand FastAPI a callable that only builds
    # the checker without ever running it, leaving the route unauthenticated.
    engine = get_engine()
    config = engine.get_permission_config()

    return {
        "mode": config.mode.value,
        "tier": config.tier.value,
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
async def update_permission_config(
    update: PermissionConfigUpdate,
    _auth: dict = Depends(require_admin()),
):
    engine = get_engine()
    current = engine.get_permission_config()

    mode = current.mode
    if update.mode is not None:
        try:
            mode = PermissionMode(update.mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {update.mode}") from None

    tier = current.tier
    if update.tier is not None:
        try:
            tier = PermissionTier(update.tier)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tier: {update.tier}") from None

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
        tier=tier,
    )
    engine.update_permission_config(new_config)

    return {"status": "updated", "mode": mode.value, "tier": tier.value}
