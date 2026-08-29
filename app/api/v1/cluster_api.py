"""Cluster node endpoints.

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
from app.storage.models_platform import Cluster

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Cluster ────────────────────────────────────────────────────────────────

@router.get("/cluster")
@router.get("/cluster/")
async def list_cluster_nodes(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Cluster)
                .order_by(Cluster.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [
            {
                "id": n.id,
                "name": n.name,
                "endpoint": n.endpoint,
                "role": n.role,
                "status": n.status,
                "capabilities": n.capabilities or [],
                "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
            }
            for n in rows
        ]


@router.post("/cluster")
@router.post("/cluster/")
@router.post("/cluster/create")
async def create_cluster_node(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    if not data.get("name"):
        raise HTTPException(status_code=422, detail="name is required")
    async with async_session() as db:
        node = Cluster(
            name=data["name"],
            endpoint=data.get("endpoint", ""),
            role=data.get("role", "worker"),
            status=data.get("status", "offline"),
            capabilities=data.get("capabilities", []),
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return {"id": node.id, "name": node.name, "endpoint": node.endpoint, "status": node.status}


@router.get("/cluster/status")
async def get_cluster_status() -> dict[str, Any]:
    async with async_session() as db:
        rows = (await db.execute(select(Cluster))).scalars().all()
        online = [n for n in rows if n.status == "online"]
        return {
            "status": "ok",
            "total_nodes": len(rows),
            "online_nodes": len(online),
            "nodes": [{"id": n.id, "name": n.name, "status": n.status, "role": n.role} for n in rows],
        }


@router.get("/cluster/stats")
@router.get("/cluster/stats/")
async def get_cluster_stats() -> dict[str, Any]:
    async with async_session() as db:
        rows = (await db.execute(select(Cluster))).scalars().all()
        total = len(rows)
        online = sum(1 for n in rows if n.status == "online")
        offline = total - online
        roles: dict[str, int] = {}
        for n in rows:
            roles[n.role] = roles.get(n.role, 0) + 1
        return {
            "total": total,
            "online": online,
            "offline": offline,
            "roles": roles,
        }


@router.delete("/cluster/{node_id}")
async def delete_cluster_node(node_id: str) -> dict:
    async with async_session() as db:
        node = (await db.execute(select(Cluster).where(Cluster.id == node_id))).scalar_one_or_none()
        if node is None:
            raise HTTPException(status_code=404, detail="Node not found")
        await db.delete(node)
        await db.commit()
        return {"ok": True, "deleted": node_id}
