"""Thinking-level and permission-tier endpoints for the settings panel.

Routes (paths are absolute so the router drops into ``app/api/v1/generic.py``
without a prefix):
- ``GET /reasoning/levels``                         — thinking-level catalog + model params
- ``GET /reasoning/permission-tiers``               — three-tier view + per-tool decisions
- ``GET /reasoning/sessions/{sid}/reasoning-level`` — current per-session level
- ``PUT /reasoning/sessions/{sid}/reasoning-level`` — set the per-session level

The ``reasoning_level`` key in ``Session.context_data`` is the same store the
``/level`` slash command writes (``app/core/slash/service.py``), so both entry
points stay in sync without a schema migration. The level reaches the model as
injected ``stream_chat``/``chat`` kwargs via :class:`LevelAwareModelRegistry`
(the same per-request rebinding seam ``chat.py`` uses for credentials).

Note: this router is not yet included by ``app/api/v1/generic.py``; until that
one-line include lands, the routes are exercised by mounting the router
directly (see ``tests/core/test_reasoning_levels.py``).
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.v1.chat import get_engine
from app.core.agent_engine import AgentEngine
from app.core.auth import get_current_user
from app.core.auth_manager import require_admin, require_scopes
from app.core.permission_rules import PermissionMode, PermissionTier
from app.storage import async_session
from app.storage.database import Session as SessionModel

router = APIRouter(tags=["reasoning"])

ThinkingLevel = Literal["low", "medium", "high"]

REASONING_LEVELS: tuple[ThinkingLevel, ...] = ("low", "medium", "high")
DEFAULT_REASONING_LEVEL: ThinkingLevel = "medium"

# One row per level; all three values must stay pairwise distinct so a level
# change is always observable in the outgoing model payload. reasoning_effort
# uses the OpenAI o-series vocabulary; the other adapters read max_tokens and
# temperature from kwargs and ignore the rest.
LEVEL_PARAMS: dict[ThinkingLevel, dict[str, Any]] = {
    "low": {"max_tokens": 4096, "temperature": 0.2, "reasoning_effort": "low"},
    "medium": {"max_tokens": 8192, "temperature": 0.5, "reasoning_effort": "medium"},
    "high": {"max_tokens": 16384, "temperature": 0.8, "reasoning_effort": "high"},
}


def level_params(level: str) -> dict[str, Any]:
    """Map a level id onto its model-call parameters; raises on unknown ids."""
    try:
        return dict(LEVEL_PARAMS[level])  # type: ignore[index]  # level validated via KeyError below
    except KeyError:
        raise ValueError(f"Unknown thinking level: {level}") from None


def level_from_context(context_data: dict[str, Any] | None) -> ThinkingLevel:
    """Read the persisted level, falling back to the default when unset."""
    value = (context_data or {}).get("reasoning_level")
    return value if value in LEVEL_PARAMS else DEFAULT_REASONING_LEVEL


# The three plain-language tiers the settings panel offers, and the enforced
# mode each one writes through the existing PUT /permissions/config write path.
TIER_MODES: dict[str, PermissionMode] = {
    PermissionTier.READ_ONLY.value: PermissionMode.PLAN,
    PermissionTier.PARTIAL_WRITE.value: PermissionMode.DEFAULT,
    PermissionTier.FULL_WRITE.value: PermissionMode.AUTO,
}

# Canonical tool names the tier view reports decisions for; aliases are folded
# in by the rule engine itself, so reporting the canonical set is enough.
_CANONICAL_TOOLS: tuple[str, ...] = (
    "read_file",
    "list_directory",
    "search",
    "glob",
    "write_file",
    "edit_file",
    "append_file",
    "apply_patch",
    "file_exists",
    "file_info",
    "file_diff",
    "run_command",
    "web_search",
    "file_delete",
)


class LevelUpdate(BaseModel):
    level: ThinkingLevel


def _level_out(level: str) -> dict[str, Any]:
    return {"id": level, **level_params(level)}


@router.get("/reasoning/levels")
async def list_reasoning_levels(_user: str = Depends(get_current_user)) -> dict[str, Any]:
    """Catalog of thinking levels with the parameters each one sends."""
    return {
        "levels": [_level_out(level) for level in REASONING_LEVELS],
        "default": DEFAULT_REASONING_LEVEL,
    }


@router.get("/reasoning/permission-tiers")
async def get_permission_tiers(
    engine: AgentEngine = Depends(get_engine),
    _auth: dict[str, Any] = Depends(require_admin()),
) -> dict[str, Any]:
    """Three-tier permission view plus each canonical tool's live decision.

    The per-tool states are derived from the enforced config, so this read
    carries the same admin gate as ``GET /permissions/config``.
    """
    tiers = [{"id": tier_id, "mode": mode.value} for tier_id, mode in TIER_MODES.items()]
    config = engine.get_permission_config()
    mode_value = getattr(getattr(config, "mode", None), "value", None)
    tool_states: list[dict[str, str]] = []
    if config is not None:
        tool_states = [
            {"tool": tool, "decision": config.evaluate(tool).value} for tool in _CANONICAL_TOOLS
        ]
    return {
        "tiers": tiers,
        "current": {
            "mode": mode_value,
            "tier": config.tier.value if config is not None else None,
        },
        "tool_states": tool_states,
    }


@router.get("/reasoning/sessions/{session_id}/reasoning-level")
async def get_session_reasoning_level(
    session_id: str,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Current thinking-level override for one owned session."""
    level = await _load_session_level(session_id, user_id)
    return {
        "session_id": session_id,
        "level": level,
        "params": _level_out(level),
    }


@router.put("/reasoning/sessions/{session_id}/reasoning-level")
async def update_session_reasoning_level(
    session_id: str,
    update: LevelUpdate,
    user_id: str = Depends(get_current_user),
    _auth: dict[str, Any] = Depends(require_scopes("write")),
) -> dict[str, Any]:
    """Persist the per-session override (same store as the /level command)."""
    async with async_session() as db:
        row = await db.scalar(
            select(SessionModel).where(
                SessionModel.id == session_id,
                SessionModel.user_id == user_id,
            )
        )
        if row is None:
            raise HTTPException(404, detail="Session not found")
        context_data = dict(row.context_data or {})
        context_data["reasoning_level"] = update.level
        row.context_data = context_data
        await db.commit()
    return {
        "session_id": session_id,
        "level": update.level,
        "params": _level_out(update.level),
        "updated": True,
    }


async def _load_session_level(session_id: str, user_id: str) -> str:
    async with async_session() as db:
        row = await db.scalar(
            select(SessionModel).where(
                SessionModel.id == session_id,
                SessionModel.user_id == user_id,
            )
        )
    if row is None:
        raise HTTPException(404, detail="Session not found")
    return level_from_context(row.context_data)


class _LevelAdapter:
    """Proxy adapter that injects the level's parameters into every call.

    The engine calls ``stream_chat(messages=..., tools=...)`` with no kwargs,
    so binding at the registry is the only place a level can reach the wire
    without touching the engine. Callers may still override a parameter
    explicitly; explicit kwargs win over the level's.
    """

    def __init__(self, adapter: Any, params: dict[str, Any]) -> None:
        self._adapter = adapter
        self._params = params

    @property
    def capabilities(self) -> Any:
        return self._adapter.capabilities

    def __getattr__(self, name: str) -> Any:
        return getattr(self._adapter, name)

    async def chat(self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any) -> Any:
        merged = {**self._params, **kwargs}
        return await self._adapter.chat(messages=messages, tools=tools, **merged)

    async def stream_chat(
        self, messages: list[dict[str, Any]], tools: Any = None, **kwargs: Any
    ) -> Any:
        merged = {**self._params, **kwargs}
        async for chunk in self._adapter.stream_chat(messages=messages, tools=tools, **merged):
            yield chunk


class LevelAwareModelRegistry:
    """Bind a model registry to one thinking level.

    Mirrors the per-request credential binding of ``chat.py``'s
    ``_ChatModelRegistry``: the wrapper delegates lookup to the base registry
    and hands the engine a proxy that adds the level's parameters.
    """

    def __init__(self, registry: Any, params: dict[str, Any]) -> None:
        self._registry = registry
        self._params = dict(params)

    def get_or_create(
        self,
        provider: str,
        model_id: str = "",
        api_key: str = "",
        base_url: str | None = None,
    ) -> _LevelAdapter:
        adapter = self._registry.get_or_create(
            provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
        )
        return _LevelAdapter(adapter, self._params)

    def get_default(self) -> _LevelAdapter:
        return _LevelAdapter(self._registry.get_default(), self._params)
