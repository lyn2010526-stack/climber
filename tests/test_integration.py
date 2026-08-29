"""Integration test - full conversation flow with mocked model."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools import register_builtins


class MockOpenAIResponse:
    """Mock httpx responses for OpenAI API (non-streaming)."""

    def __init__(self, content: str, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls

    def json(self) -> dict:
        result = {
            "choices": [{
                "message": {
                    "content": self.content,
                    "role": "assistant",
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        if self.tool_calls:
            result["choices"][0]["message"]["tool_calls"] = self.tool_calls
        return result

    def raise_for_status(self):
        pass

    @property
    def status_code(self):
        return 200


class MockStreamingOpenAIResponse:
    """Mock httpx streaming response for OpenAI API."""

    def __init__(self, content: str, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls
        self.status_code = 200
        self._closed = False

    def raise_for_status(self):
        pass

    async def aiter_bytes(self):
        """Generate SSE-formatted streaming bytes."""
        if self.content:
            words = self.content.split(" ")
            for i, word in enumerate(words):
                if self._closed:
                    return
                chunk = {
                    "choices": [{
                        "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                        "finish_reason": None,
                    }],
                    "usage": None,
                }
                yield f"data: {json.dumps(chunk)}\n".encode()

        if self.tool_calls:
            for tc in self.tool_calls:
                if self._closed:
                    return
                chunk = {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": json.dumps(tc["function"]["arguments"]),
                                },
                            }],
                        },
                        "finish_reason": "tool_calls",
                    }],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                }
                yield f"data: {json.dumps(chunk)}\n".encode()

        if not self._closed:
            yield b"data: [DONE]\n"

    async def aclose(self):
        self._closed = True


@pytest.fixture
def client():
    """Create test client with fresh state."""
    # Clear engine sessions
    from app.api.v1 import get_engine
    if hasattr(get_engine, "_engine"):
        get_engine._engine.sessions.clear()
    # Register builtins
    register_builtins()
    with TestClient(app) as c:
        yield c


def test_full_chat_flow_with_tool(client: TestClient):
    """Test: create agent -> session -> chat with tool call -> session history."""
    import httpx

    from app.api.v1.chat import get_engine

    # Use BYPASS permission mode for tests to avoid ASK blocking
    from app.core.permission_rules import PermissionConfig, PermissionMode
    engine = get_engine()
    engine._default_permission_config = PermissionConfig(mode=PermissionMode.BYPASS)

    # Create agent (no auth required in local mode)
    resp = client.post('/api/v1/agents', json={
        'name': 'Calculator Agent',
        'system_prompt': 'You are a calculator assistant.',
        'provider': 'openai',
        'model_id': 'gpt-4o',
        'api_key': 'sk-test-key',
    })
    assert resp.status_code == 200
    agent_id = resp.json()['id']

    # Create session
    resp = client.post('/api/v1/sessions', json={'agent_id': agent_id})
    assert resp.status_code == 200
    session_id = resp.json()['session_id']

    # Mock the httpx call - first returns tool call, second returns final answer
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return MockStreamingOpenAIResponse(
                content="",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "arguments": {"expression": "2 + 2"},
                    },
                }],
            )
        return MockStreamingOpenAIResponse(content="The answer is 4.")


    responses = [
        MockStreamingOpenAIResponse(
            content="",
            tool_calls=[{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "calculator",
                    "arguments": {"expression": "2 + 2"},
                },
            }],
        ),
        MockStreamingOpenAIResponse(content="The answer is 4."),
    ]
    iter(responses)

    _send_iter = iter(responses)

    async def fake_send(*args, **kwargs):
        return next(_send_iter)

    with patch.object(httpx.AsyncClient, 'send', side_effect=fake_send):
        # Send a chat message
        resp = client.post(
            f'/api/v1/sessions/{session_id}/chat',
            json={'message': 'What is 2 + 2?'},
        )
        assert resp.status_code == 200

        # Parse SSE events - format is "event: X\r\ndata: Y\r\n\r\n"
        event_names = []
        event_data = []
        for line in resp.text.split('\n'):
            line = line.strip()
            if line.startswith('event: '):
                event_names.append(line[7:])
            elif line.startswith('data: '):
                event_data.append(json.loads(line[6:]))

        # Should have events
        assert len(event_data) > 0
        # Should have tool_call and tool_result events
        assert 'tool_call' in event_names
        assert 'tool_result' in event_names
        # Should have text content from tool result
        text_contents = [d.get('content', '') for d in event_data]
        assert any('4' in c for c in text_contents)


def test_list_tools_endpoint(client: TestClient):
    """Test that tools endpoint returns registered tools."""
    resp = client.get('/api/v1/tools')
    assert resp.status_code == 200
    tools = resp.json()
    assert len(tools) > 0
    tool_names = [t['name'] for t in tools]
    assert 'calculator' in tool_names
    assert 'web_search' in tool_names


def test_delete_session(client: TestClient):
    """Test session deletion."""
    # Create agent + session
    resp = client.post('/api/v1/agents', json={
        'name': 'Test', 'provider': 'openai', 'model_id': 'gpt-4o', 'api_key': 'sk-test',
    })
    agent_id = resp.json()['id']

    resp = client.post('/api/v1/sessions', json={'agent_id': agent_id})
    session_id = resp.json()['session_id']

    # Delete session
    resp = client.delete(f'/api/v1/sessions/{session_id}')
    assert resp.status_code == 200

    # Verify it's gone
    resp = client.get(f'/api/v1/sessions/{session_id}')
    assert resp.status_code == 404


def test_rename_session(client: TestClient):
    """Session titles can be renamed and are reflected by detail and list APIs."""
    resp = client.post('/api/v1/sessions', json={'title': 'Original'})
    assert resp.status_code == 200
    session_id = resp.json()['session_id']

    resp = client.patch(f'/api/v1/sessions/{session_id}', json={'title': '  Project Alpha  '})
    assert resp.status_code == 200
    assert resp.json()['title'] == 'Project Alpha'

    detail = client.get(f'/api/v1/sessions/{session_id}')
    assert detail.status_code == 200
    assert detail.json()['title'] == 'Project Alpha'

    sessions = client.get('/api/v1/sessions').json()
    renamed = next(session for session in sessions if session['id'] == session_id)
    assert renamed['title'] == 'Project Alpha'


def test_rename_session_rejects_empty_title(client: TestClient):
    resp = client.post('/api/v1/sessions', json={'title': 'Original'})
    session_id = resp.json()['session_id']

    resp = client.patch(f'/api/v1/sessions/{session_id}', json={'title': '   '})
    assert resp.status_code == 422


def test_unauthorized_access(client: TestClient):
    """Test that unauthorized requests work in guest mode (default user)."""
    resp = client.get('/api/v1/agents')
    assert resp.status_code == 200  # Guest mode - no auth required

    resp = client.get('/api/v1/agents', headers={'Authorization': 'Bearer invalid-token'})
    assert resp.status_code == 200  # Invalid token falls back to default user


def test_health_endpoint(client: TestClient):
    """Test /health returns proper format with dependency checks."""
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'ok'
    assert data['version'] == '0.2.0'
    assert 'chroma' in data
    assert data['chroma'] in ('ok', 'unavailable')


def test_error_handling_middleware():
    """Test that 500 errors return proper JSON without exposing internals."""
    from fastapi import HTTPException

    from app.main import app

    @app.get('/_test/internal-error')
    async def trigger_error():
        raise RuntimeError("secret internal details")

    @app.get('/_test/http-error')
    async def trigger_http_error():
        raise HTTPException(status_code=403, detail="forbidden resource")

    test_client = TestClient(app, raise_server_exceptions=False)

    resp = test_client.get('/_test/internal-error')
    assert resp.status_code == 500
    data = resp.json()
    assert data['detail'] == 'Internal server error'
    assert data['type'] == 'internal_error'
    assert 'secret' not in str(data)

    resp = test_client.get('/_test/http-error')
    assert resp.status_code == 403
    data = resp.json()
    assert data['detail'] == 'forbidden resource'
    assert data['type'] == 'http_error'


def test_session_clear_endpoint(client: TestClient):
    """Test clearing session messages."""
    resp = client.post('/api/v1/agents', json={
        'name': 'Clear Test', 'provider': 'openai', 'model_id': 'gpt-4o', 'api_key': 'sk-test',
    })
    agent_id = resp.json()['id']

    resp = client.post('/api/v1/sessions', json={'agent_id': agent_id})
    session_id = resp.json()['session_id']

    resp = client.post(f'/api/v1/sessions/{session_id}/clear')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'cleared'

    resp = client.get(f'/api/v1/sessions/{session_id}/messages')
    assert resp.status_code == 200
    assert resp.json()['messages'] == []

    resp = client.post(f'/api/v1/sessions/{session_id}/clear')
    assert resp.status_code == 200


def test_platform_stats_endpoint(client: TestClient):
    """Test stats endpoint returns platform statistics."""
    resp = client.get('/api/v1/stats')
    assert resp.status_code == 200
    data = resp.json()
    assert 'total_users' in data


def test_fourth_gen_default_third_gen_mode():
    """Master switch OFF by default → pure third-gen, nothing wired."""
    from app.config import settings
    from app.main import _init_fourth_gen

    original = settings.enable_fourth_gen
    try:
        settings.enable_fourth_gen = False
        assert _init_fourth_gen() is None
    finally:
        settings.enable_fourth_gen = original


def test_fourth_gen_full_wiring_then_rollback():
    """Enabling all modules wires A-D; disabling falls back to third-gen."""
    from app.config import settings
    from app.main import _init_fourth_gen

    originals = {
        'master': settings.enable_fourth_gen,
        'auto': settings.enable_autodiscovery,
        'meta': settings.enable_meta_agent,
        'goal': settings.enable_goal_centered,
        'swarm': settings.enable_swarm,
    }
    try:
        settings.enable_fourth_gen = True
        settings.enable_autodiscovery = True
        settings.enable_meta_agent = True
        settings.enable_goal_centered = True
        settings.enable_swarm = True

        handles = _init_fourth_gen()
        assert handles is not None
        assert 'autodiscovery' in handles
        assert 'meta_agent' in handles
        assert 'goal_centered' in handles
        assert 'swarm' in handles

        # Fall back: master off → third-gen only
        settings.enable_fourth_gen = False
        assert _init_fourth_gen() is None
    finally:
        settings.enable_fourth_gen = originals['master']
        settings.enable_autodiscovery = originals['auto']
        settings.enable_meta_agent = originals['meta']
        settings.enable_goal_centered = originals['goal']
        settings.enable_swarm = originals['swarm']
