from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.core.language_service import (
    JsonRpcConnection,
    JsonRpcProtocolError,
    LanguageServerConfig,
    LanguageServiceManager,
    ServerUnavailableError,
    UnsupportedLanguageError,
    WorkspacePathError,
    encode_json_rpc_message,
    read_json_rpc_message,
)


class BufferWriter:
    def __init__(self) -> None:
        self.data = bytearray()

    def write(self, data: bytes) -> None:
        self.data.extend(data)

    async def drain(self) -> None:
        return None


def make_reader(data: bytes = b"") -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    if data:
        reader.feed_data(data)
    return reader


def decode_frames(data: bytes) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    while data:
        header, data = data.split(b"\r\n\r\n", 1)
        length = int(header.removeprefix(b"Content-Length: "))
        payload, data = data[:length], data[length:]
        messages.append(json.loads(payload))
    return messages


@pytest.mark.asyncio
async def test_json_rpc_framing_uses_utf8_byte_length() -> None:
    message = {"jsonrpc": "2.0", "id": 1, "result": "类型"}
    framed = encode_json_rpc_message(message)
    header, payload = framed.split(b"\r\n\r\n", 1)

    assert header == f"Content-Length: {len(payload)}".encode()
    reader = make_reader(framed)
    assert await read_json_rpc_message(reader, max_message_bytes=1024) == message


@pytest.mark.asyncio
async def test_json_rpc_framing_rejects_duplicate_or_oversized_lengths() -> None:
    duplicate = make_reader(b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}")
    with pytest.raises(JsonRpcProtocolError, match="Content-Length"):
        await read_json_rpc_message(duplicate, max_message_bytes=1024)

    oversized = make_reader(b"Content-Length: 1025\r\n\r\n")
    with pytest.raises(JsonRpcProtocolError, match="maximum"):
        await read_json_rpc_message(oversized, max_message_bytes=1024)


def test_server_config_requires_explicit_argv() -> None:
    with pytest.raises(ValueError, match="argv"):
        LanguageServerConfig(argv="server --stdio", language_id="python")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_connection_correlates_out_of_order_responses() -> None:
    reader = make_reader()
    writer = BufferWriter()
    connection = JsonRpcConnection(reader, writer, default_timeout=1)

    first = asyncio.create_task(connection.request("first", {"value": 1}))
    second = asyncio.create_task(connection.request("second", {"value": 2}))
    await asyncio.sleep(0)

    requests = decode_frames(bytes(writer.data))
    ids = {request["method"]: request["id"] for request in requests}
    reader.feed_data(encode_json_rpc_message({"jsonrpc": "2.0", "id": ids["second"], "result": "two"}))
    reader.feed_data(encode_json_rpc_message({"jsonrpc": "2.0", "id": ids["first"], "result": "one"}))

    assert await first == "one"
    assert await second == "two"
    await connection.close()


@pytest.mark.asyncio
async def test_connection_rejects_server_request_without_consuming_matching_response() -> None:
    reader = make_reader()
    writer = BufferWriter()
    connection = JsonRpcConnection(reader, writer, default_timeout=1)

    request = asyncio.create_task(connection.request("client/request", {}))
    await asyncio.sleep(0)
    request_id = decode_frames(bytes(writer.data))[0]["id"]
    reader.feed_data(encode_json_rpc_message({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "workspace/configuration",
        "params": {},
    }))
    reader.feed_data(encode_json_rpc_message({"jsonrpc": "2.0", "id": request_id, "result": "ok"}))

    assert await request == "ok"
    frames = decode_frames(bytes(writer.data))
    assert frames[-1]["error"]["code"] == -32601
    await connection.close()


class FakeLanguageServer:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.notifications: list[tuple[str, dict[str, Any]]] = []
        self.requests: list[tuple[str, dict[str, Any]]] = []
        self.closed = False

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        self.notifications.append((method, params))

    async def request(self, method: str, params: dict[str, Any], timeout: float | None = None) -> Any:
        self.requests.append((method, params))
        response = self.responses[method]
        if callable(response):
            response = response()
        if isinstance(response, Exception):
            raise response
        if inspect.isawaitable(response):
            return await response
        return response

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_manager_supports_diagnostics_symbols_hover_and_close(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text("value = 1\n", encoding="utf-8")
    server = FakeLanguageServer(
        {
            "textDocument/diagnostic": {"kind": "full", "items": [{"message": "problem"}]},
            "textDocument/documentSymbol": [{"name": "value"}],
            "textDocument/hover": {"contents": "int"},
        }
    )
    created: list[tuple[LanguageServerConfig, Path]] = []

    async def factory(config: LanguageServerConfig, workspace: Path) -> FakeLanguageServer:
        created.append((config, workspace))
        return server

    config = LanguageServerConfig(argv=("pyright-langserver", "--stdio"), language_id="python")
    manager = LanguageServiceManager(tmp_path, {".py": config}, client_factory=factory)

    assert await manager.diagnostics(source) == {"kind": "full", "items": [{"message": "problem"}]}
    source.write_text("value = 2\n", encoding="utf-8")
    assert await manager.document_symbols(source) == [{"name": "value"}]
    assert await manager.hover(source, line=3, character=4) == {"contents": "int"}

    assert created == [(config, tmp_path.resolve())]
    assert [method for method, _ in server.notifications] == ["textDocument/didOpen", "textDocument/didChange"]
    assert server.notifications[-1][1]["textDocument"]["version"] == 2
    assert server.requests[-1][1]["position"] == {"line": 3, "character": 4}
    await manager.close()
    assert server.closed


@pytest.mark.asyncio
async def test_manager_serializes_concurrent_document_open(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text("value = 1\n", encoding="utf-8")
    response_ready = asyncio.Event()

    async def response() -> dict[str, Any]:
        await response_ready.wait()
        return {"items": []}

    server = FakeLanguageServer({"textDocument/diagnostic": response})

    async def factory(config: LanguageServerConfig, workspace: Path) -> FakeLanguageServer:
        return server

    config = LanguageServerConfig(argv=("server", "--stdio"), language_id="python")
    manager = LanguageServiceManager(tmp_path, {".py": config}, client_factory=factory)
    first = asyncio.create_task(manager.diagnostics(source))
    second = asyncio.create_task(manager.diagnostics(source))
    await asyncio.sleep(0)
    response_ready.set()
    await asyncio.gather(first, second)

    assert [method for method, _ in server.notifications].count("textDocument/didOpen") == 1
    await manager.close()


@pytest.mark.asyncio
async def test_manager_rejects_oversized_document_before_starting_server(tmp_path: Path) -> None:
    source = tmp_path / "large.py"
    source.write_text("x" * 101, encoding="utf-8")
    starts = 0

    async def factory(config: LanguageServerConfig, workspace: Path) -> FakeLanguageServer:
        nonlocal starts
        starts += 1
        return FakeLanguageServer({})

    config = LanguageServerConfig(argv=("server", "--stdio"), language_id="python")
    manager = LanguageServiceManager(
        tmp_path,
        {".py": config},
        max_document_bytes=100,
        client_factory=factory,
    )

    with pytest.raises(WorkspacePathError, match="maximum"):
        await manager.diagnostics(source)
    assert starts == 0


@pytest.mark.asyncio
async def test_manager_fails_closed_before_starting_server(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")
    unknown = tmp_path / "file.unknown"
    unknown.write_text("value\n", encoding="utf-8")
    python_file = tmp_path / "file.py"
    python_file.write_text("value\n", encoding="utf-8")
    starts = 0

    async def factory(config: LanguageServerConfig, workspace: Path) -> FakeLanguageServer:
        nonlocal starts
        starts += 1
        return FakeLanguageServer({})

    manager = LanguageServiceManager(tmp_path, {}, client_factory=factory)

    with pytest.raises(WorkspacePathError):
        await manager.diagnostics(outside)
    with pytest.raises(UnsupportedLanguageError):
        await manager.diagnostics(unknown)
    with pytest.raises(ServerUnavailableError):
        await manager.diagnostics(python_file)
    assert starts == 0


@pytest.mark.asyncio
async def test_manager_applies_timeout_and_result_truncation(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text("value = 1\n", encoding="utf-8")

    async def slow_response() -> dict[str, str]:
        await asyncio.sleep(1)
        return {"contents": "late"}

    server = FakeLanguageServer({"textDocument/hover": slow_response()})

    async def factory(config: LanguageServerConfig, workspace: Path) -> FakeLanguageServer:
        return server

    config = LanguageServerConfig(argv=("server", "--stdio"), language_id="python")
    manager = LanguageServiceManager(
        tmp_path,
        {".py": config},
        timeout=0.01,
        max_result_chars=40,
        client_factory=factory,
    )
    with pytest.raises(TimeoutError):
        await manager.hover(source, 0, 0)

    server.responses["textDocument/hover"] = {"contents": "x" * 100}
    result = await manager.hover(source, 0, 0)
    assert result["truncated"] is True
    assert len(result["preview"]) == 40
