"""MCP (Model Context Protocol) server API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.v1.helpers import payload as _payload
from app.storage import async_session
from app.storage.models_plugins import MCPServerRecord

router = APIRouter()


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
async def list_mcp_servers() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(MCPServerRecord).order_by(MCPServerRecord.created_at.desc()))).scalars().all()
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