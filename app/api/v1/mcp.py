"""MCP (Model Context Protocol) server API endpoints.

Dead-code cleanup (2026-10-05): the ``/mcp`` GET/POST, ``/mcp/{id}/start``,
``/mcp/{id}/stop`` and ``/mcp/{id}`` DELETE handlers were never mounted —
``app/api/v1/__init__.py`` only extracts the ``/mcp/servers`` and
``/mcp/categories`` prefixes from this router — and the live versions exist in
``app/api/v1/routes/misc.py``.  They were removed per
``docs/audits/dead-code-scan.md``.  Only the market/catalog endpoints below
(``/mcp/servers*``, ``/mcp/categories``) are actually served from this file.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth_manager import require_admin
from app.storage import async_session
from app.storage.models_plugins import MCPServerRecord

router = APIRouter()

MCP_CATEGORIES = ["file-system", "database", "web", "code", "utility"]

_MARKET_SERVERS: list[dict[str, Any]] = [
    {
        "id": "filesystem",
        "name": "Filesystem",
        "description": "Read and write files",
        "category": "file-system",
        "author": "Scaffold",
        "is_builtin": True,
        "is_installed": False,
        "tags": ["files", "io"],
        "install_config": {},
        "popularity": 95,
    },
    {
        "id": "github",
        "name": "GitHub",
        "description": "Access GitHub repos and issues",
        "category": "code",
        "author": "GitHub",
        "is_builtin": True,
        "is_installed": False,
        "tags": ["git", "github"],
        "install_config": {},
        "popularity": 88,
    },
    {
        "id": "postgres",
        "name": "PostgreSQL",
        "description": "Query PostgreSQL databases",
        "category": "database",
        "author": "Scaffold",
        "is_builtin": True,
        "is_installed": False,
        "tags": ["sql", "database"],
        "install_config": {},
        "popularity": 72,
    },
    {
        "id": "brave-search",
        "name": "Brave Search",
        "description": "Web search via Brave",
        "category": "web",
        "author": "Brave",
        "is_builtin": True,
        "is_installed": False,
        "tags": ["search", "web"],
        "install_config": {},
        "popularity": 65,
    },
]


def _mcp_dict(m: MCPServerRecord) -> dict[str, Any]:
    from app.api.v1.common import mask_env_values

    return {
        "id": m.id,
        "plugin_id": m.plugin_id,
        "name": m.name,
        "command": m.command,
        "url": m.url,
        "args": m.args,
        "env": mask_env_values(m.env),
        "has_env": bool(m.env),
        "status": m.status,
        "tools_count": m.tools_count,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }


# Frontend-compatible routes: /mcp/servers
@router.get("/mcp/servers")
@router.get("/mcp/servers/")
async def list_mcp_market_servers() -> list[dict[str, Any]]:
    async with async_session() as db:
        installed = (await db.execute(select(MCPServerRecord))).scalars().all()
        installed_ids = {m.plugin_id for m in installed}
    return [{**s, "is_installed": s["id"] in installed_ids} for s in _MARKET_SERVERS]


@router.get("/mcp/categories")
@router.get("/mcp/categories/")
async def list_mcp_categories() -> list[str]:
    return MCP_CATEGORIES


@router.post("/mcp/servers/{server_id}/install")
async def install_mcp_server(
    server_id: str,
    _auth: dict[str, Any] = Depends(require_admin()),
) -> dict[str, Any]:
    async with async_session() as db:
        existing = (
            (
                await db.execute(
                    select(MCPServerRecord).where(MCPServerRecord.plugin_id == server_id)
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return _mcp_dict(existing)
        market = next((s for s in _MARKET_SERVERS if s["id"] == server_id), None)
        if market is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        server = MCPServerRecord(
            plugin_id=server_id,
            name=market["name"],
            url=market.get("url"),
            command=market.get("command"),
            args=market.get("args", []),
            env=market.get("env", {}),
            status="installed",
            tools_count=0,
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return _mcp_dict(server)


@router.delete("/mcp/servers/{server_id}")
async def delete_mcp_market_server(
    server_id: str,
    _auth: dict[str, Any] = Depends(require_admin()),
) -> dict[str, Any]:
    async with async_session() as db:
        server = (
            (
                await db.execute(
                    select(MCPServerRecord).where(MCPServerRecord.plugin_id == server_id)
                )
            )
            .scalars()
            .first()
        )
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        await db.delete(server)
        await db.commit()
        return {"ok": True, "deleted": server_id}
