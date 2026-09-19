"""Tests for the self-contained memory MCP stdio server."""

from __future__ import annotations

import json

from app.tools.memory_mcp_server import handle_frame, tool_definitions


def _call(name: str, arguments: dict) -> dict:
    return handle_frame(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    )


def _tool_text(resp: dict) -> dict:
    text = resp["result"]["content"][0]["text"]
    return json.loads(text)


def test_tools_list_lists_expected_tools() -> None:
    resp = handle_frame({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {t["name"] for t in resp["result"]["tools"]}
    assert {"memory_write", "memory_search", "memory_status"} <= names
    assert len(tool_definitions()) == len(resp["result"]["tools"])


def test_initialize_returns_server_info() -> None:
    resp = handle_frame(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "t", "version": "1"}}}
    )
    result = resp["result"]
    assert result["serverInfo"]["name"] == "memory-mcp-server"
    assert result["capabilities"].get("tools") == {}
    assert result["protocolVersion"]


def test_write_then_search_hit() -> None:
    user = "test-user-1"
    write = _call(
        "memory_write",
        {"content": "The API gateway routes on port 9000", "importance": 0.9, "tags": ["infra"], "user_id": user},
    )
    assert write["result"]["isError"] is False
    memory_id = json.loads(write["result"]["content"][0]["text"])["memory_id"]

    search = _call("memory_search", {"query": "API gateway routing", "user_id": user})
    assert search["result"]["isError"] is False
    payload = json.loads(search["result"]["content"][0]["text"])
    assert payload["count"] >= 1
    assert any(m["memory_id"] == memory_id for m in payload["results"])


def test_search_no_match_returns_empty_without_crash() -> None:
    user = "test-user-2"
    resp = _call("memory_search", {"query": "zzzz-no-match-abc", "limit": 0, "user_id": user})
    assert resp["result"]["isError"] is False
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["count"] == 0
    assert payload["results"] == []


def test_unknown_tool_returns_error_structure() -> None:
    resp = _call("does_not_exist", {})
    assert resp["result"]["isError"] is True
    assert json.loads(resp["result"]["content"][0]["text"])["error"]


def test_default_user_id_isolation() -> None:
    resp = _call("memory_search", {"query": "API gateway", "user_id": "other-user"})
    assert resp["result"]["isError"] is False
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["results"] == []


def test_missing_required_argument_returns_error() -> None:
    resp = _call("memory_write", {})
    assert resp["result"]["isError"] is True
    assert "content" in json.loads(resp["result"]["content"][0]["text"])["error"]


def test_notification_returns_none() -> None:
    assert handle_frame({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_returns_jsonrpc_error() -> None:
    resp = handle_frame({"jsonrpc": "2.0", "id": 1, "method": "bogus/method"})
    assert resp["error"]["code"] == -32601


def test_memory_status_reports_counts() -> None:
    user = "test-user-3"
    _call("memory_write", {"content": "status probe record", "user_id": user})
    resp = _call("memory_status", {"user_id": user})
    assert resp["result"]["isError"] is False
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["total"] >= 1
    assert payload["active"] >= 1
