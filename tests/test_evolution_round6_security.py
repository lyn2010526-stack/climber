"""Round 6 security baseline: degraded read boundary when sandbox init fails.

Verifies that when the SecuritySandbox is unavailable, built-in and native
read-only tools still enforce a path boundary instead of reading any
host-readable file. Also covers native symlink escape and sibling-prefix
confusion.

All file access uses a temporary workspace root so assertions are hermetic.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.core import AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine
from app.core.permission_rules import PermissionConfig, PermissionMode
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry
from app.tools import builtins as builtins_mod
from app.tools import native_tools as native_mod

SECRET = "TOP-SECRET-R6-LEAK"


def _schema(**props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(props.keys())}


def _build_engine() -> AgentEngine:
    registry = ToolRegistry()

    registry.register(
        "read_file", "read", _schema(path={"type": "string"}),
        builtins_mod.read_file, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "list_files", "list", _schema(directory={"type": "string"}),
        builtins_mod.list_files, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "file_exists", "exists", _schema(path={"type": "string"}),
        builtins_mod.file_exists, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "file_info", "info", _schema(path={"type": "string"}),
        builtins_mod.file_info, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "file_diff", "diff", _schema(path={"type": "string"}, new_content={"type": "string"}),
        builtins_mod.file_diff, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "native_read_file", "nread", _schema(path={"type": "string"}),
        native_mod.native_read_file, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "native_list_dir", "nlist", _schema(path={"type": "string"}),
        native_mod.native_list_dir, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "process_video", "video", _schema(command={"type": "string"}),
        native_mod.process_video, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "process_image", "image", _schema(command={"type": "string"}),
        native_mod.process_image, sandbox_safe_when_unavailable=True,
    )
    registry.register(
        "write_file", "write", _schema(path={"type": "string"}, content={"type": "string"}),
        builtins_mod.write_file, sandbox_safe_when_unavailable=False,
    )
    registry.register(
        "echo", "pure", _schema(text={"type": "string"}),
        lambda text: text, sandbox_safe_when_unavailable=True,
    )

    engine = AgentEngine(model_registry=ModelRegistry(), tool_registry=registry)
    engine.sandbox = None
    engine.debug_loop = None
    engine._default_permission_config = PermissionConfig(mode=PermissionMode.BYPASS)
    return engine


def _session(engine: AgentEngine, tools: list[str] | None = None):
    return engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
        tools=tools,
    )


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> SimpleNamespace:
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("CLIMBER_SANDBOX_WORKDIR", str(ws))

    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text(SECRET)

    sibling = tmp_path / "ws-secrets"
    sibling.mkdir()
    sibling_file = sibling / "data.txt"
    sibling_file.write_text("sibling content")

    escape_link = ws / "escape.txt"
    escape_link.symlink_to(secret)

    inside = ws / "ok.txt"
    inside.write_text("allowed content")

    return SimpleNamespace(
        ws=ws,
        outside=outside,
        secret=secret,
        sibling_file=sibling_file,
        escape_link=escape_link,
        inside=inside,
    )


def test_read_file_outside_workspace_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "read_file", {"path": str(env.secret)})
    assert allowed is False


def test_read_file_sibling_prefix_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "read_file", {"path": str(env.sibling_file)})
    assert allowed is False


def test_read_file_symlink_escape_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "read_file", {"path": str(env.escape_link)})
    assert allowed is False


def test_read_file_inside_workspace_allowed(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "read_file", {"path": str(env.inside)})
    assert allowed is True


def test_file_info_outside_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "file_info", {"path": str(env.secret)})
    assert allowed is False


def test_file_exists_outside_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "file_exists", {"path": str(env.secret)})
    assert allowed is False


def test_file_diff_outside_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(
        _session(engine), "file_diff", {"path": str(env.secret), "new_content": "x"}
    )
    assert allowed is False


def test_list_files_traversal_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "list_files", {"directory": str(env.outside)})
    assert allowed is False


def test_native_read_file_symlink_escape_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "native_read_file", {"path": str(env.escape_link)})
    assert allowed is False


def test_native_list_dir_outside_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "native_list_dir", {"path": str(env.outside)})
    assert allowed is False


def test_write_file_still_denied(env: SimpleNamespace):
    engine = _build_engine()
    allowed, reason = engine._validate_tool_call(
        _session(engine), "write_file", {"path": str(env.inside), "content": "x"}
    )
    assert allowed is False
    assert "sandbox unavailable" in reason.lower()


def test_pure_tool_preserved(env: SimpleNamespace):
    engine = _build_engine()
    allowed, _ = engine._validate_tool_call(_session(engine), "echo", {"text": "hi"})
    assert allowed is True


@pytest.mark.asyncio
async def test_degraded_read_cannot_leak_secret_end_to_end(env: SimpleNamespace):
    from tests.test_agent_engine import FakeModelAdapter

    class _FakeMemory:
        async def format_memories_for_prompt(self, *args: Any, **kwargs: Any) -> str:
            return ""

        async def create_episodic_memory(self, **kwargs: Any) -> None:
            return None

    async def _noop_persist(*args: Any, **kwargs: Any) -> None:
        return None

    engine = _build_engine()
    engine.memory_service = _FakeMemory()
    engine._persist_message = _noop_persist

    tool_call = [{
        "id": "call_secret",
        "type": "function",
        "function": {"name": "read_file", "arguments": {"path": str(env.secret)}},
    }]
    engine.model_registry._models["fake:fake-model"] = FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="done", finish_reason="stop"),
    ])

    session = _session(engine, tools=["read_file"])
    events = [event async for event in engine.run(session, "read the secret")]

    result_event = next(event for event in events if event.type == AgentEventType.TOOL_RESULT)
    assert "denied" in result_event.data["error"].lower()

    serialized = " ".join(str(event.data) for event in events)
    assert SECRET not in serialized
    assert all(SECRET not in str(message) for message in session.messages)


def test_process_video_denied_when_sandbox_none(env: SimpleNamespace):
    engine = _build_engine()
    allowed, reason = engine._validate_tool_call(
        _session(engine), "process_video", {"command": "-i /etc/passwd -f null -"}
    )
    assert allowed is False
    assert "sandbox unavailable" in reason.lower()


def test_process_image_denied_when_sandbox_none(env: SimpleNamespace):
    engine = _build_engine()
    allowed, reason = engine._validate_tool_call(
        _session(engine), "process_image", {"command": "input.txt output.txt"}
    )
    assert allowed is False
    assert "sandbox unavailable" in reason.lower()
