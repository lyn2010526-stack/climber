"""Self-contained stdio MCP server exposing the project memory system.

Implements a minimal subset of the MCP JSON-RPC protocol (initialize,
notifications/*, ping, tools/list, tools/call) over newline-delimited
JSON on stdin/stdout. No external `mcp` SDK is required: the package is
declared in requirements.txt but not guaranteed installed, so this module
speaks the wire protocol directly.

The memory backend reuses app.core.memory.lifecycle.MemoryLifecycleManager
(async + SQLAlchemy async_session). Sync wrappers bridge via asyncio.run().
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from app.core.memory.lifecycle import MemoryLifecycleManager, MemoryRetrieveResult

SERVER_NAME = "memory-mcp-server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"
DEFAULT_USER_ID = "mcp-external-agent"

_manager = MemoryLifecycleManager()
_tables_ready = False


def _run(coro: Any) -> Any:
    """Run an async coroutine to completion on a fresh event loop."""
    return asyncio.run(coro)


def _ensure_tables() -> None:
    """Create DB tables once (idempotent, safe alongside the main app)."""
    global _tables_ready
    if _tables_ready:
        return
    from app.storage import init_db

    _run(init_db())
    _tables_ready = True


def sync_write_memory(
    content: str,
    importance: float = 0.5,
    tags: list[str] | None = None,
    user_id: str = DEFAULT_USER_ID,
    memory_type: str = "general",
) -> dict[str, Any]:
    """Persist a memory through the lifecycle manager."""
    _ensure_tables()
    metadata = {"tags": tags or []} if tags else None
    result = _run(
        _manager.write_memory(
            content=content,
            user_id=user_id,
            memory_type=memory_type,
            importance=float(importance),
            metadata=metadata,
        )
    )
    return {
        "memory_id": result.memory_id,
        "content": result.content,
        "user_id": result.user_id,
        "memory_type": result.memory_type,
        "importance": result.importance,
        "created_at": result.created_at,
        "tags": tags or [],
    }


def sync_search_memory(
    query: str,
    limit: int = 5,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict[str, Any]]:
    """Retrieve memories ranked by keyword match + importance."""
    _ensure_tables()
    results: list[MemoryRetrieveResult] = _run(
        _manager.retrieve_memories(query=query, user_id=user_id, limit=max(0, int(limit)))
    )
    return [
        {
            "memory_id": r.memory_id,
            "content": r.content,
            "importance": r.importance,
            "score": r.score,
            "memory_type": r.memory_type,
            "created_at": r.created_at,
        }
        for r in results
    ]


def sync_memory_status(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Return counts of active and archived memories for a user."""
    _ensure_tables()
    from sqlalchemy import func, select

    from app.core.memory.lifecycle import MemoryRecord
    from app.storage import async_session

    async def _counts() -> dict[str, int]:
        async with async_session() as db:
            total = (
                await db.execute(
                    select(func.count())
                    .select_from(MemoryRecord)
                    .where(
                        MemoryRecord.user_id == user_id,
                        ~MemoryRecord.is_forgotten,
                    )
                )
            ).scalar() or 0
            archived = (
                await db.execute(
                    select(func.count())
                    .select_from(MemoryRecord)
                    .where(
                        MemoryRecord.user_id == user_id,
                        MemoryRecord.is_archived,
                        ~MemoryRecord.is_forgotten,
                    )
                )
            ).scalar() or 0
            return {"total": total, "archived": archived, "active": total - archived}

    counts = _run(_counts())
    counts["user_id"] = user_id
    return counts


def tool_definitions() -> list[dict[str, Any]]:
    """MCP tool schemas exposed by this server."""
    return [
        {
            "name": "memory_write",
            "description": "Write a new memory entry with optional importance and tags.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to store"},
                    "importance": {"type": "number", "default": 0.5},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "user_id": {"type": "string", "default": DEFAULT_USER_ID},
                },
                "required": ["content"],
            },
        },
        {
            "name": "memory_search",
            "description": "Search memories by keyword relevance and importance.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                    "user_id": {"type": "string", "default": DEFAULT_USER_ID},
                },
                "required": ["query"],
            },
        },
        {
            "name": "memory_status",
            "description": "Report memory counts for a user.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "default": DEFAULT_USER_ID},
                },
            },
        },
    ]


def _tool_map() -> dict[str, dict[str, Any]]:
    return {t["name"]: t for t in tool_definitions()}


def _text_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap tool output as an MCP text content result."""
    return {
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
        "isError": False,
    }


def _error_result(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
        "isError": True,
    }


def _run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    args = dict(arguments or {})
    tools = _tool_map()
    tool = tools.get(name)
    if tool is None:
        return _error_result(f"unknown tool: {name}")

    required = tool["inputSchema"].get("required", [])
    for field in required:
        if field not in args:
            return _error_result(f"missing required argument: {field}")

    user_id = str(args.pop("user_id", DEFAULT_USER_ID))
    if name == "memory_write":
        content = args.get("content")
        if not isinstance(content, str) or not content.strip():
            return _error_result("content must be a non-empty string")
        importance = args.get("importance", 0.5)
        try:
            importance = float(importance)
        except (TypeError, ValueError):
            return _error_result("importance must be a number")
        importance = max(0.0, min(1.0, importance))
        tags = args.get("tags")
        if tags is not None and not isinstance(tags, list):
            return _error_result("tags must be an array of strings")
        result = sync_write_memory(content, importance=importance, tags=tags or [], user_id=user_id)
        return _text_result(result)

    if name == "memory_search":
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return _error_result("query must be a non-empty string")
        limit = args.get("limit", 5)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return _error_result("limit must be an integer")
        results = sync_search_memory(query, limit=limit, user_id=user_id)
        return _text_result({"query": query, "count": len(results), "results": results})

    if name == "memory_status":
        return _text_result(sync_memory_status(user_id=user_id))

    return _error_result(f"unknown tool: {name}")


def handle_frame(frame: dict[str, Any]) -> dict[str, Any] | None:
    """Process a single JSON-RPC frame and return the response (None for notifications)."""
    jsonrpc = frame.get("jsonrpc")
    if jsonrpc != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": frame.get("id"),
            "error": {"code": -32600, "message": "invalid jsonrpc version"},
        }

    method = frame.get("method")
    frame_id = frame.get("id")
    if frame_id is None:
        return None

    params = frame.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    if method == "initialize":
        client_info = params.get("clientInfo", {})
        return {
            "jsonrpc": "2.0",
            "id": frame_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "clientInfo": client_info,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": frame_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": frame_id, "result": {"tools": tool_definitions()}}

    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or not name:
            return {"jsonrpc": "2.0", "id": frame_id, "error": {"code": -32602, "message": "missing tool name"}}
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return {
                "jsonrpc": "2.0",
                "id": frame_id,
                "error": {"code": -32602, "message": "arguments must be an object"},
            }
        return {"jsonrpc": "2.0", "id": frame_id, "result": _run_tool(name, arguments)}

    if method.startswith("notifications/"):
        return None

    return {
        "jsonrpc": "2.0",
        "id": frame_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main() -> None:
    """Run the stdio loop: read newline-delimited JSON-RPC from stdin."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            frame = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"parse error: {exc}"},
            }
        else:
            response = handle_frame(frame)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
