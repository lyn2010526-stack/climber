"""Editable anchored UI rules; account scope is explicit in every response."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth_manager import require_scopes
from app.core.ui_rules import RuleKind, list_rules, save_rule

router = APIRouter(prefix="/ui/rules", tags=["ui-rules"])


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(max_length=32000)
    revision: str | None = Field(default=None, min_length=64, max_length=64)


@router.get("")
async def get_rules(auth: dict[str, Any] = Depends(require_scopes("read"))) -> list[dict[str, Any]]:
    return await list_rules(auth["id"])


@router.put("/{kind}")
async def put_rule(
    kind: RuleKind, body: RuleUpdate, auth: dict[str, Any] = Depends(require_scopes("write"))
) -> dict[str, Any]:
    try:
        return await save_rule(auth["id"], kind, body.content, body.revision)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
