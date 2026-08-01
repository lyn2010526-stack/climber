"""Plugin API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.v1.helpers import payload as _payload
from app.storage import async_session
from app.storage.models_plugins import PluginRecord

router = APIRouter()

MARKETPLACE: list[dict[str, Any]] = [
    {"plugin_key": "web-scraper", "name": "\u7f51\u9875\u6293\u53d6\u5668", "description": "\u6293\u53d6\u5e76\u89e3\u6790\u7f51\u9875\u5185\u5bb9\u4e3a\u7ed3\u6784\u5316\u6570\u636e", "category": "data", "version": "1.0.0", "author": "climber"},
    {"plugin_key": "code-runner", "name": "\u4ee3\u7801\u6267\u884c\u5668", "description": "\u5728\u672c\u5730\u6c99\u7bb1\u4e2d\u6267\u884c Python \u4ee3\u7801\u7247\u6bb5", "category": "dev", "version": "1.0.0", "author": "climber"},
    {"plugin_key": "file-watcher", "name": "\u6587\u4ef6\u76d1\u542c\u5668", "description": "\u76d1\u542c\u672c\u5730\u76ee\u5f55\u53d8\u5316\u5e76\u89e6\u53d1\u5de5\u4f5c\u6d41", "category": "automation", "version": "1.0.0", "author": "climber"},
]


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
async def list_plugins(type: str = "") -> list[dict[str, Any]]:
    async with async_session() as db:
        stmt = select(PluginRecord).order_by(PluginRecord.installed_at.desc())
        if type:
            stmt = stmt.where(PluginRecord.category == type)
        rows = (await db.execute(stmt)).scalars().all()
        return [_plugin_dict(p) for p in rows]


@router.get("/plugins/marketplace")
@router.get("/plugins/marketplace/")
async def get_marketplace() -> list[dict[str, Any]]:
    async with async_session() as db:
        installed = {p.plugin_key for p in (await db.execute(select(PluginRecord))).scalars().all() if p.plugin_key}
    return [{**item, "is_installed": item["plugin_key"] in installed} for item in MARKETPLACE]


@router.get("/plugins/categories")
@router.get("/plugins/categories/")
async def get_plugin_categories() -> list[str]:
    async with async_session() as db:
        rows = (await db.execute(select(PluginRecord.category).distinct())).scalars().all()
    return sorted({*(r for r in (rows or []) if r), *(m["category"] for m in MARKETPLACE)})


@router.post("/plugins/{plugin_key}/install")
async def install_plugin(plugin_key: str, request: Request) -> dict[str, Any]:
    entry = next((m for m in MARKETPLACE if m["plugin_key"] == plugin_key), None)
    data = await _payload(request)
    async with async_session() as db:
        existing = (await db.execute(select(PluginRecord).where(PluginRecord.plugin_key == plugin_key))).scalars().first()
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
    return (await db.execute(
        select(PluginRecord).where((PluginRecord.id == plugin_id) | (PluginRecord.plugin_key == plugin_id))
    )).scalars().first()


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
        return {"id": plugin.id, "status": plugin.status, "is_installed": plugin.status in ("installed", "enabled", "disabled")}


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