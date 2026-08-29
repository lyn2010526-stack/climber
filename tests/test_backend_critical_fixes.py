"""Regression tests for backend routing, configuration, and tool hardening."""

from __future__ import annotations

import asyncio
import subprocess
from urllib.parse import unquote, urlsplit

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.api.v1 import cluster_api, cost_api, groups_api, tasks_api
from app.api.v1 import router as api_router
from app.config import Settings
from app.core.parallel import ParallelToolExecutor
from app.core.tool_runtime import ToolRuntime
from app.tools.builtins import container_exec
from app.tools.native_tools import open_browser


def _route_keys(router) -> list[tuple[str, str]]:
    keys = []
    for route in router.routes:
        if isinstance(route, APIRoute):
            keys.extend((method, route.path) for method in route.methods)
        elif included_router := getattr(route, "original_router", None):
            keys.extend(_route_keys(included_router))
    return keys


def test_consolidated_routes_are_registered_once():
    keys = _route_keys(api_router)
    relevant = [key for key in keys if key[1].startswith(("/cost", "/cluster", "/groups", "/tasks"))]
    expected = {
        *_route_keys(cost_api.router),
        *_route_keys(cluster_api.router),
        *_route_keys(groups_api.router),
        *_route_keys(tasks_api.router),
    }

    assert set(relevant) == expected
    assert len(relevant) == len(set(relevant))


def test_cors_rejects_wildcard_with_credentials():
    with pytest.raises(ValidationError, match="must not contain"):
        Settings(CORS_ORIGINS="*", cors_allow_credentials=True)


def test_cors_allows_wildcard_without_credentials():
    settings = Settings(CORS_ORIGINS="*", cors_allow_credentials=False)

    assert settings.cors_origins_list == ["*"]
    assert settings.cors_allow_credentials is False


def test_connection_urls_encode_special_characters_in_component_passwords():
    password = "p@ss:/?#%"

    settings = Settings(
        database_host="postgres",
        database_port=5432,
        database_user="climber",
        database_password=password,
        database_name="climber",
        redis_host="redis",
        redis_port=6379,
        redis_password=password,
        redis_db=0,
    )

    assert make_url(settings.database_url).password == password
    redis_url = urlsplit(settings.redis_url)
    assert unquote(redis_url.password or "") == password
    assert redis_url.hostname == "redis"


class _ConcurrencyProbe:
    def __init__(self) -> None:
        self.active = 0
        self.maximum = 0

    async def run(self) -> str:
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return "ok"


class _ProbeRegistry:
    def __init__(self, probe: _ConcurrencyProbe) -> None:
        self.probe = probe

    async def execute(self, _name: str, _arguments: dict) -> str:
        return await self.probe.run()


@pytest.mark.asyncio
async def test_parallel_executor_limits_concurrency_to_ten():
    probe = _ConcurrencyProbe()
    executor = ParallelToolExecutor(_ProbeRegistry(probe))
    calls = [{"function": {"name": "probe", "arguments": {}}} for _ in range(25)]

    await executor.execute_all(calls)

    assert probe.maximum == 10


@pytest.mark.asyncio
async def test_tool_runtime_limits_concurrency_to_ten():
    probe = _ConcurrencyProbe()
    runtime = ToolRuntime()
    runtime.register_local("probe", "probe", {}, probe.run)

    await runtime.execute_many([("probe", {}) for _ in range(25)])

    assert probe.maximum == 10


@pytest.mark.asyncio
async def test_container_exec_uses_argument_list_and_preserves_shell_command(monkeypatch):
    captured: dict = {}

    def fake_run(arguments, **kwargs):
        captured["arguments"] = arguments
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(arguments, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = await container_exec("worker.1", "printf 'a b' | wc -c", "/app")

    assert result == "ok"
    assert captured["arguments"] == [
        "docker", "exec", "-w", "/app", "--", "worker.1", "sh", "-c", "printf 'a b' | wc -c",
    ]
    assert captured["kwargs"]["shell"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("container", ["worker/name", "worker name", "worker;id"])
async def test_container_exec_rejects_invalid_container_names(container):
    assert await container_exec(container, "true") == "Error: invalid container name"


@pytest.mark.asyncio
async def test_container_exec_rejects_empty_command():
    assert await container_exec("worker", "  ") == "Error: command must not be empty"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["file:///tmp/page.html", "javascript:alert(1)", "https:///missing-host", "example.com"])
async def test_open_browser_rejects_invalid_urls(url):
    assert await open_browser(url) == "Error: URL must include an http or https scheme and host"
