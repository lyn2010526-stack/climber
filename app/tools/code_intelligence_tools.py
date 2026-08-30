"""Single bounded tool contract for workspace code intelligence."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from app.core.language_service import LanguageServiceError, ServerUnavailableError
from app.tools import tool


class CodeIntelligenceManager(Protocol):
    async def diagnostics(self, file_path: str) -> Any: ...

    async def document_symbols(self, file_path: str) -> Any: ...

    async def hover(self, file_path: str, line: int, character: int) -> Any: ...


CodeIntelligenceHandler = Callable[..., Awaitable[dict[str, Any]]]
_manager: CodeIntelligenceManager | None = None
_ACTIONS = ("diagnostics", "document_symbols", "hover")


def configure_code_intelligence(manager: CodeIntelligenceManager | None) -> None:
    """Inject the process-wide manager from the application composition root."""
    global _manager
    _manager = manager


def create_code_intelligence_tool(manager: CodeIntelligenceManager) -> CodeIntelligenceHandler:
    """Create an isolated handler for tests, tenants, or alternate workspaces."""

    async def handler(
        action: str,
        file_path: str,
        line: int = 0,
        character: int = 0,
    ) -> dict[str, Any]:
        return await _execute(manager, action, file_path, line, character)

    return handler


async def _execute(
    manager: CodeIntelligenceManager,
    action: str,
    file_path: str,
    line: int,
    character: int,
) -> dict[str, Any]:
    if action not in _ACTIONS:
        return _error("invalid_action", f"Unsupported code intelligence action: {action}")
    try:
        if action == "diagnostics":
            result = await manager.diagnostics(file_path)
        elif action == "document_symbols":
            result = await manager.document_symbols(file_path)
        else:
            result = await manager.hover(file_path, line, character)
    except LanguageServiceError as exc:
        return _error(exc.code, str(exc))
    except TimeoutError:
        return _error("timeout", "Language server request timed out")
    except (OSError, UnicodeError, ValueError) as exc:
        return _error("invalid_request", str(exc))
    return {"ok": True, "action": action, "file_path": file_path, "result": result}


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


@tool(
    name="code_intelligence",
    description="Get bounded LSP diagnostics, document symbols, or hover information for a workspace file.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": list(_ACTIONS)},
            "file_path": {"type": "string"},
            "line": {"type": "integer", "minimum": 0, "default": 0},
            "character": {"type": "integer", "minimum": 0, "default": 0},
        },
        "required": ["action", "file_path"],
        "additionalProperties": False,
    },
)
async def code_intelligence(
    action: str,
    file_path: str,
    line: int = 0,
    character: int = 0,
) -> dict[str, Any]:
    """Execute one code-intelligence operation against the injected manager."""
    if _manager is None:
        error = ServerUnavailableError("Code intelligence manager is not configured")
        return _error(error.code, str(error))
    return await _execute(_manager, action, file_path, line, character)
