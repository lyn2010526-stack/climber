from __future__ import annotations

from pathlib import Path

import pytest

from app.core.agent_engine import AgentEngine
from app.core.language_service import LanguageServerConfig, LanguageServiceManager
from app.core.permission_controller import READ_ONLY_TOOLS
from app.tools import tool_registry
from app.tools.code_intelligence_tools import code_intelligence, create_code_intelligence_tool


class StubManager:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def diagnostics(self, file_path: str) -> list[dict[str, str]]:
        self.calls.append(("diagnostics", file_path))
        return [{"message": "problem"}]

    async def document_symbols(self, file_path: str) -> list[dict[str, str]]:
        self.calls.append(("document_symbols", file_path))
        return [{"name": "symbol"}]

    async def hover(self, file_path: str, line: int, character: int) -> dict[str, str]:
        self.calls.append(("hover", file_path, line, character))
        return {"contents": "int"}


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["diagnostics", "document_symbols", "hover"])
async def test_single_tool_contract_dispatches_to_injected_manager(action: str) -> None:
    manager = StubManager()
    handler = create_code_intelligence_tool(manager)

    result = await handler(action=action, file_path="example.py", line=2, character=5)

    assert result["ok"] is True
    assert result["action"] == action
    assert result["result"]
    assert manager.calls[0][0] == action


@pytest.mark.asyncio
async def test_unknown_action_fails_closed_without_calling_manager() -> None:
    manager = StubManager()
    handler = create_code_intelligence_tool(manager)

    result = await handler(action="references", file_path="example.py")

    assert result == {
        "ok": False,
        "error": {"code": "invalid_action", "message": "Unsupported code intelligence action: references"},
    }
    assert manager.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("file_name", "expected_code"),
    [("example.unknown", "unsupported_language"), ("example.py", "server_unavailable")],
)
async def test_unknown_suffix_and_missing_server_fail_closed(
    tmp_path: Path,
    file_name: str,
    expected_code: str,
) -> None:
    source = tmp_path / file_name
    source.write_text("value = 1\n", encoding="utf-8")
    manager = LanguageServiceManager(tmp_path, {})
    handler = create_code_intelligence_tool(manager)

    result = await handler(action="diagnostics", file_path=str(source))

    assert result["ok"] is False
    assert result["error"]["code"] == expected_code


@pytest.mark.asyncio
async def test_out_of_workspace_path_fails_closed_before_server_start(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")
    starts = 0

    async def factory(config: LanguageServerConfig, root: Path):
        nonlocal starts
        starts += 1
        raise AssertionError("server must not start")

    config = LanguageServerConfig(argv=("server", "--stdio"), language_id="python")
    manager = LanguageServiceManager(workspace, {".py": config}, client_factory=factory)
    handler = create_code_intelligence_tool(manager)

    result = await handler(action="hover", file_path=str(outside), line=0, character=0)

    assert result["ok"] is False
    assert result["error"]["code"] == "workspace_path_error"
    assert starts == 0


@pytest.mark.asyncio
async def test_unconfigured_global_tool_fails_closed() -> None:
    result = await code_intelligence(action="diagnostics", file_path="example.py")

    assert result["ok"] is False
    assert result["error"]["code"] == "server_unavailable"


def test_tool_schema_exposes_one_bounded_contract() -> None:
    definition = tool_registry.get_tool("code_intelligence")

    assert definition is not None
    assert definition.parameters["properties"]["action"]["enum"] == [
        "diagnostics",
        "document_symbols",
        "hover",
    ]
    assert definition.parameters["additionalProperties"] is False


def test_code_intelligence_is_classified_as_read_only_file_access() -> None:
    assert "code_intelligence" in READ_ONLY_TOOLS
    assert AgentEngine._FILE_TOOLS["code_intelligence"] == ("file_path", "read")
