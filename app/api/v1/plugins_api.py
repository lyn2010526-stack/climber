"""Plugin marketplace, install and MCP server endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.v1._shared import _payload
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_plugins import MCPServerRecord, PluginRecord

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Plugins ────────────────────────────────────────────────────────────────

def _get_marketplace() -> list[dict[str, Any]]:
    """Return plugin marketplace catalog from settings."""
    from app.config import settings
    return list(settings.plugin_marketplace)


def _plugin_dict(p: PluginRecord) -> dict[str, Any]:
    return {
        "id": p.id,
        "plugin_key": p.plugin_key,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "version": p.version,
        "author": p.author,
        "type": p.type,
        "source": p.source,
        "status": p.status,
        "is_installed": p.status in ("installed", "enabled", "disabled"),
        "is_enabled": p.status == "enabled",
    }


@router.get("/plugins")
@router.get("/plugins/")
async def list_plugins(
    type: str = "",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        stmt = select(PluginRecord).order_by(PluginRecord.installed_at.desc())
        if type:
            stmt = stmt.where(PluginRecord.category == type)
        stmt = stmt.offset(offset).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        return [_plugin_dict(p) for p in rows]


@router.get("/plugins/marketplace")
@router.get("/plugins/marketplace/")
async def get_marketplace() -> list[dict[str, Any]]:
    async with async_session() as db:
        installed = {
            p.plugin_key
            for p in (await db.execute(select(PluginRecord))).scalars().all()
            if p.plugin_key
        }
    return [{**item, "is_installed": item["plugin_key"] in installed} for item in _get_marketplace()]


@router.get("/plugins/categories")
@router.get("/plugins/categories/")
async def get_plugin_categories() -> list[str]:
    async with async_session() as db:
        rows = (await db.execute(select(PluginRecord.category).distinct())).scalars().all()
    return sorted({*(r for r in (rows or []) if r), *(m["category"] for m in _get_marketplace())})


@router.post("/plugins/{plugin_key}/install")
async def install_plugin(plugin_key: str, request: Request) -> dict[str, Any]:
    entry = next((m for m in _get_marketplace() if m["plugin_key"] == plugin_key), None)
    data = await _payload(request)
    async with async_session() as db:
        existing = (
            await db.execute(select(PluginRecord).where(PluginRecord.plugin_key == plugin_key))
        ).scalars().first()
        if existing is not None:
            existing.status = "installed"
            await db.commit()
            await db.refresh(existing)
            return _plugin_dict(existing)

        plugin = PluginRecord(
            plugin_key=plugin_key,
            name=(entry or data).get("name", plugin_key),
            description=(entry or data).get("description", ""),
            category=(entry or data).get("category", "general"),
            version=(entry or data).get("version", "1.0.0"),
            author=(entry or data).get("author", ""),
            type=data.get("type", "skill"),
            source="marketplace" if entry else "custom",
            config=data.get("config", {}),
            status="installed",
        )
        db.add(plugin)
        await db.commit()
        await db.refresh(plugin)
        return _plugin_dict(plugin)


async def _find_plugin(db, plugin_id: str) -> PluginRecord | None:
    return (
        await db.execute(
            select(PluginRecord).where(
                (PluginRecord.id == plugin_id) | (PluginRecord.plugin_key == plugin_id)
            )
        )
    ).scalars().first()


async def _set_plugin_enabled(plugin_id: str, enabled: bool) -> dict:
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        plugin.status = "enabled" if enabled else "disabled"
        await db.commit()
        return {"ok": True, "id": plugin.id, "is_enabled": enabled, "status": plugin.status}


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict:
    return await _set_plugin_enabled(plugin_id, True)


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict:
    return await _set_plugin_enabled(plugin_id, False)


@router.delete("/plugins/{plugin_id}")
@router.post("/plugins/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str) -> dict:
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        await db.delete(plugin)
        await db.commit()
        return {"ok": True, "deleted": plugin_id}


@router.get("/plugins/{plugin_id}/status")
async def get_plugin_status(plugin_id: str) -> dict[str, Any]:
    async with async_session() as db:
        plugin = await _find_plugin(db, plugin_id)
        if plugin is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return {
            "id": plugin.id,
            "status": plugin.status,
            "is_installed": plugin.status in ("installed", "enabled", "disabled"),
        }


@router.post("/plugins/import")
async def import_plugin(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    key = data.get("plugin_key") or data.get("name")
    if not key:
        raise HTTPException(status_code=422, detail="plugin_key or name is required")
    async with async_session() as db:
        plugin = PluginRecord(
            plugin_key=key,
            name=data.get("name", key),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            type=data.get("type", "skill"),
            source="custom",
            source_url=data.get("source_url"),
            config=data.get("config", {}),
            status="installed",
        )
        db.add(plugin)
        await db.commit()
        await db.refresh(plugin)
        return _plugin_dict(plugin)


# ─── MCP ────────────────────────────────────────────────────────────────────



def _mcp_dict(m: MCPServerRecord) -> dict[str, Any]:
    return {
        "id": m.id,
        "plugin_id": m.plugin_id,
        "name": m.name,
        "command": m.command,
        "url": m.url,
        "args": m.args,
        "env": m.env,
        "status": m.status,
        "tools_count": m.tools_count,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }


@router.get("/mcp")
@router.get("/mcp/")
async def list_mcp_servers(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(MCPServerRecord)
                .order_by(MCPServerRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [_mcp_dict(m) for m in rows]


@router.post("/mcp")
@router.post("/mcp/")
async def create_mcp_server(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        server = MCPServerRecord(
            plugin_id=data.get("plugin_id"),
            name=data.get("name", "MCP Server"),
            command=data.get("command"),
            url=data.get("url"),
            args=data.get("args", []),
            env=data.get("env", {}),
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return _mcp_dict(server)


@router.post("/mcp/{server_id}/start")
async def start_mcp_server(server_id: str) -> dict[str, Any]:
    async with async_session() as db:
        server = (await db.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))).scalars().first()
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        server.status = "connected"
        await db.commit()
        return _mcp_dict(server)


@router.post("/mcp/{server_id}/stop")
async def stop_mcp_server(server_id: str) -> dict[str, Any]:
    async with async_session() as db:
        server = (await db.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))).scalars().first()
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        server.status = "stopped"
        await db.commit()
        return _mcp_dict(server)


@router.delete("/mcp/{server_id}")
async def delete_mcp_server(server_id: str) -> dict[str, Any]:
    async with async_session() as db:
        server = (await db.execute(select(MCPServerRecord).where(MCPServerRecord.id == server_id))).scalars().first()
        if server is None:
            raise HTTPException(status_code=404, detail="MCP server not found")
        await db.delete(server)
        await db.commit()
        return {"ok": True, "deleted": server_id}
