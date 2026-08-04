"""Tool API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.di import resolve as di_resolve

router = APIRouter()


@router.get("/tools")
@router.get("/tools/")
async def list_tools() -> list[dict[str, Any]]:
    import app.tools.builtins  # noqa: F401
    tool_registry = di_resolve("ToolRegistry")
    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters}
        for t in tool_registry.list_tools()
    ]