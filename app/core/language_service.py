"""Minimal, bounded Language Server Protocol client support."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class LanguageServiceError(RuntimeError):
    """Base error with a stable tool-facing code."""

    code = "language_service_error"


class JsonRpcProtocolError(LanguageServiceError):
    code = "json_rpc_protocol_error"


class JsonRpcResponseError(LanguageServiceError):
    code = "json_rpc_response_error"

    def __init__(self, error: Any) -> None:
        self.error = error
        super().__init__(f"Language server returned an error: {error}")


class WorkspacePathError(LanguageServiceError):
    code = "workspace_path_error"


class UnsupportedLanguageError(LanguageServiceError):
    code = "unsupported_language"


class ServerUnavailableError(LanguageServiceError):
    code = "server_unavailable"


def encode_json_rpc_message(message: Mapping[str, Any]) -> bytes:
    """Encode one JSON-RPC message using LSP stdio framing."""
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload


async def read_json_rpc_message(
    reader: asyncio.StreamReader,
    *,
    max_message_bytes: int,
    max_header_bytes: int = 8192,
) -> dict[str, Any]:
    """Read one bounded LSP stdio message."""
    if max_message_bytes <= 0 or max_header_bytes <= 0:
        raise ValueError("message and header limits must be positive")

    try:
        raw_headers = await reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError) as exc:
        raise JsonRpcProtocolError("Incomplete or oversized JSON-RPC header") from exc
    if len(raw_headers) > max_header_bytes:
        raise JsonRpcProtocolError("JSON-RPC header exceeds maximum size")

    content_lengths: list[str] = []
    for raw_line in raw_headers[:-4].split(b"\r\n"):
        try:
            name, value = raw_line.decode("ascii").split(":", 1)
        except (UnicodeDecodeError, ValueError) as exc:
            raise JsonRpcProtocolError("Malformed JSON-RPC header") from exc
        if name.strip().lower() == "content-length":
            content_lengths.append(value.strip())

    if len(content_lengths) != 1 or not content_lengths[0].isdecimal():
        raise JsonRpcProtocolError("Exactly one valid Content-Length header is required")
    content_length = int(content_lengths[0])
    if content_length <= 0:
        raise JsonRpcProtocolError("Content-Length must be positive")
    if content_length > max_message_bytes:
        raise JsonRpcProtocolError("JSON-RPC message exceeds maximum size")

    try:
        payload = await reader.readexactly(content_length)
        message = json.loads(payload.decode("utf-8"))
    except (asyncio.IncompleteReadError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JsonRpcProtocolError("Invalid JSON-RPC payload") from exc
    if not isinstance(message, dict):
        raise JsonRpcProtocolError("JSON-RPC payload must be an object")
    return message


class _Writer(Protocol):
    def write(self, data: bytes) -> None: ...

    async def drain(self) -> None: ...


class JsonRpcConnection:
    """Concurrent JSON-RPC connection with response correlation by request ID."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: _Writer,
        *,
        default_timeout: float = 10,
        max_message_bytes: int = 2_000_000,
    ) -> None:
        if default_timeout <= 0:
            raise ValueError("default_timeout must be positive")
        if max_message_bytes <= 0:
            raise ValueError("max_message_bytes must be positive")
        self._reader = reader
        self._writer = writer
        self._default_timeout = default_timeout
        self._max_message_bytes = max_message_bytes
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._write_lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._reader_error: BaseException | None = None
        self._closed = False

    async def request(self, method: str, params: Mapping[str, Any], timeout: float | None = None) -> Any:
        if self._closed:
            raise ServerUnavailableError("Language server connection is closed")
        self._ensure_reader()
        if self._reader_error is not None:
            raise ServerUnavailableError("Language server connection failed") from self._reader_error

        request_id = self._next_id
        self._next_id += 1
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params)})
            request_timeout = self._default_timeout if timeout is None else timeout
            return await asyncio.wait_for(future, request_timeout)
        finally:
            self._pending.pop(request_id, None)

    async def notify(self, method: str, params: Mapping[str, Any]) -> None:
        if self._closed:
            raise ServerUnavailableError("Language server connection is closed")
        await self._send({"jsonrpc": "2.0", "method": method, "params": dict(params)})

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task
        error = ServerUnavailableError("Language server connection closed")
        for future in self._pending.values():
            if not future.done():
                future.set_exception(error)
        self._pending.clear()

    def _ensure_reader(self) -> None:
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._read_loop())

    async def _send(self, message: Mapping[str, Any]) -> None:
        framed = encode_json_rpc_message(message)
        _, payload = framed.split(b"\r\n\r\n", 1)
        if len(payload) > self._max_message_bytes:
            raise JsonRpcProtocolError("JSON-RPC message exceeds maximum size")
        async with self._write_lock:
            self._writer.write(framed)
            await self._writer.drain()

    async def _read_loop(self) -> None:
        try:
            while not self._closed:
                message = await read_json_rpc_message(
                    self._reader,
                    max_message_bytes=self._max_message_bytes,
                )
                if "method" in message:
                    request_id = message.get("id")
                    if isinstance(request_id, (int, str)):
                        await self._send({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32601, "message": "Method not found"},
                        })
                    continue
                request_id = message.get("id")
                if not isinstance(request_id, int):
                    continue
                future = self._pending.get(request_id)
                if future is None or future.done():
                    continue
                if "error" in message:
                    future.set_exception(JsonRpcResponseError(message["error"]))
                elif "result" in message:
                    future.set_result(message["result"])
                else:
                    future.set_exception(JsonRpcProtocolError("JSON-RPC response has no result or error"))
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            self._reader_error = exc
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(ServerUnavailableError("Language server connection failed"))


@dataclass(frozen=True)
class LanguageServerConfig:
    """Explicit executable arguments and LSP language identifier."""

    argv: tuple[str, ...]
    language_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.argv, tuple) or not self.argv:
            raise ValueError("Language server argv must be a non-empty argument tuple")
        if any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in self.argv):
            raise ValueError("Language server argv contains an invalid argument")
        if not self.language_id:
            raise ValueError("language_id is required")


class LanguageServerClient(Protocol):
    async def request(self, method: str, params: dict[str, Any], timeout: float | None = None) -> Any: ...

    async def notify(self, method: str, params: dict[str, Any]) -> None: ...

    async def close(self) -> None: ...


class StdioLanguageServerClient:
    """Lifecycle wrapper around one explicitly configured LSP subprocess."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        connection: JsonRpcConnection,
        timeout: float,
    ) -> None:
        self._process = process
        self._connection = connection
        self._timeout = timeout
        self._closed = False

    @classmethod
    async def start(
        cls,
        config: LanguageServerConfig,
        workspace: Path,
        timeout: float,
    ) -> StdioLanguageServerClient:
        process = await asyncio.create_subprocess_exec(
            *config.argv,
            cwd=str(workspace),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if process.stdin is None or process.stdout is None:
            process.terminate()
            raise ServerUnavailableError("Language server stdio pipes are unavailable")
        connection = JsonRpcConnection(process.stdout, process.stdin, default_timeout=timeout)
        client = cls(process, connection, timeout)
        try:
            await connection.request(
                "initialize",
                {
                    "processId": None,
                    "rootUri": workspace.as_uri(),
                    "capabilities": {"textDocument": {"diagnostic": {}}},
                    "workspaceFolders": [{"uri": workspace.as_uri(), "name": workspace.name}],
                },
                timeout,
            )
            await connection.notify("initialized", {})
        except BaseException:
            await client.close()
            raise
        return client

    async def request(self, method: str, params: dict[str, Any], timeout: float | None = None) -> Any:
        return await self._connection.request(method, params, timeout)

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        await self._connection.notify(method, params)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._process.returncode is None:
            with contextlib.suppress(Exception):
                await self._connection.request("shutdown", {}, self._timeout)
            with contextlib.suppress(Exception):
                await self._connection.notify("exit", {})
            try:
                await asyncio.wait_for(self._process.wait(), self._timeout)
            except TimeoutError:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), self._timeout)
                except TimeoutError:
                    self._process.kill()
                    await self._process.wait()
        await self._connection.close()


ClientFactory = Callable[
    [LanguageServerConfig, Path],
    LanguageServerClient | Awaitable[LanguageServerClient],
]

_DEFAULT_LANGUAGE_IDS = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascriptreact",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".svelte": "svelte",
    ".ts": "typescript",
    ".tsx": "typescriptreact",
    ".vue": "vue",
}


class LanguageServiceManager:
    """Select and manage bounded language servers for one workspace."""

    def __init__(
        self,
        workspace: str | Path,
        servers: Mapping[str, LanguageServerConfig],
        *,
        timeout: float = 10,
        max_result_chars: int = 20_000,
        max_document_bytes: int = 2_000_000,
        language_ids: Mapping[str, str] | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.workspace = Path(workspace).expanduser().resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError("workspace must be a directory")
        if timeout <= 0 or max_result_chars <= 0 or max_document_bytes <= 0:
            raise ValueError("timeout and size limits must be positive")
        self._servers = {self._normalize_suffix(suffix): config for suffix, config in servers.items()}
        configured_language_ids = _DEFAULT_LANGUAGE_IDS if language_ids is None else language_ids
        self._language_ids = {
            self._normalize_suffix(suffix): language_id for suffix, language_id in configured_language_ids.items()
        }
        for suffix, config in self._servers.items():
            self._language_ids.setdefault(suffix, config.language_id)
        self._timeout = timeout
        self._max_result_chars = max_result_chars
        self._max_document_bytes = max_document_bytes
        self._client_factory = client_factory or self._start_client
        self._clients: dict[LanguageServerConfig, LanguageServerClient] = {}
        self._opened_documents: dict[tuple[LanguageServerConfig, str], tuple[int, str]] = {}
        self._document_locks: dict[tuple[LanguageServerConfig, str], asyncio.Lock] = {}
        self._client_lock = asyncio.Lock()
        self._closed = False

    async def diagnostics(self, file_path: str | Path) -> Any:
        return await self._query("textDocument/diagnostic", file_path)

    async def document_symbols(self, file_path: str | Path) -> Any:
        return await self._query("textDocument/documentSymbol", file_path)

    async def hover(self, file_path: str | Path, line: int, character: int) -> Any:
        if line < 0 or character < 0:
            raise ValueError("line and character must be non-negative")
        return await self._query(
            "textDocument/hover",
            file_path,
            {"position": {"line": line, "character": character}},
        )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        clients = list(self._clients.values())
        self._clients.clear()
        self._opened_documents.clear()
        self._document_locks.clear()
        if clients:
            await asyncio.gather(*(client.close() for client in clients), return_exceptions=True)

    async def _query(
        self,
        method: str,
        file_path: str | Path,
        extra_params: Mapping[str, Any] | None = None,
    ) -> Any:
        path, suffix, config = self._resolve_document(file_path)
        uri = path.as_uri()
        document_key = (config, uri)
        lock = self._document_locks.setdefault(document_key, asyncio.Lock())
        async with lock:
            text = await self._read_document(path)
            client = await self._get_client(config)
            opened_document = self._opened_documents.get(document_key)
            if opened_document is None:
                await asyncio.wait_for(
                    client.notify(
                        "textDocument/didOpen",
                        {
                            "textDocument": {
                                "uri": uri,
                                "languageId": self._language_ids[suffix],
                                "version": 1,
                                "text": text,
                            }
                        },
                    ),
                    self._timeout,
                )
                self._opened_documents[document_key] = (1, text)
            elif opened_document[1] != text:
                version = opened_document[0] + 1
                await asyncio.wait_for(
                    client.notify(
                        "textDocument/didChange",
                        {
                            "textDocument": {"uri": uri, "version": version},
                            "contentChanges": [{"text": text}],
                        },
                    ),
                    self._timeout,
                )
                self._opened_documents[document_key] = (version, text)
            params: dict[str, Any] = {"textDocument": {"uri": uri}}
            if extra_params:
                params.update(extra_params)
            result = await asyncio.wait_for(client.request(method, params, self._timeout), self._timeout)
            return self._truncate_result(result)

    async def _read_document(self, path: Path) -> str:
        def read_bounded() -> str:
            with path.open("rb") as source:
                payload = source.read(self._max_document_bytes + 1)
            if len(payload) > self._max_document_bytes:
                raise WorkspacePathError("Document exceeds maximum size")
            try:
                return payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise WorkspacePathError("Document must be valid UTF-8") from exc

        return await asyncio.to_thread(read_bounded)

    def _resolve_document(self, file_path: str | Path) -> tuple[Path, str, LanguageServerConfig]:
        candidate = Path(file_path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace / candidate
        try:
            path = candidate.resolve(strict=True)
            path.relative_to(self.workspace)
        except (OSError, RuntimeError, ValueError) as exc:
            raise WorkspacePathError(f"Path is outside the workspace or unavailable: {file_path}") from exc
        if not path.is_file():
            raise WorkspacePathError(f"Path is not a regular file: {file_path}")
        suffix = self._normalize_suffix(path.suffix)
        if suffix not in self._language_ids:
            raise UnsupportedLanguageError(f"Unsupported file suffix: {suffix or '<none>'}")
        config = self._servers.get(suffix)
        if config is None:
            raise ServerUnavailableError(f"No language server configured for suffix: {suffix}")
        return path, suffix, config

    async def _get_client(self, config: LanguageServerConfig) -> LanguageServerClient:
        if self._closed:
            raise ServerUnavailableError("Language service manager is closed")
        client = self._clients.get(config)
        if client is not None:
            return client
        async with self._client_lock:
            client = self._clients.get(config)
            if client is None:
                created = self._client_factory(config, self.workspace)
                client = await asyncio.wait_for(created, self._timeout) if inspect.isawaitable(created) else created
                self._clients[config] = client
        return client

    async def _start_client(self, config: LanguageServerConfig, workspace: Path) -> LanguageServerClient:
        return await StdioLanguageServerClient.start(config, workspace, self._timeout)

    def _truncate_result(self, result: Any) -> Any:
        serialized = json.dumps(result, ensure_ascii=False, default=str, separators=(",", ":"))
        if len(serialized) <= self._max_result_chars:
            return result
        return {"truncated": True, "preview": serialized[: self._max_result_chars]}

    @staticmethod
    def _normalize_suffix(suffix: str) -> str:
        normalized = suffix.lower()
        return normalized if normalized.startswith(".") else f".{normalized}"
