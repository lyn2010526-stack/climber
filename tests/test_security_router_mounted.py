"""Tests for the mounted security API and its network allowlist policy.

Covers the app/core/security package being reachable over HTTP and the
allowlist decisions enforced before any tool opens an outbound connection.
"""

from __future__ import annotations

import asyncio
import socket
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security.api import fs_isolation_manager
from app.core.security.network_allowlist import NetworkAllowlist, network_allowlist
from app.main import app

if TYPE_CHECKING:
    from collections.abc import Iterator

INTERNAL_TARGETS = [
    "http://127.0.0.1/",
    "http://127.0.0.53:8080/admin",
    "http://10.0.0.5/",
    "http://172.16.0.1/",
    "http://172.31.255.1/",
    "http://192.168.1.1/",
    "http://169.254.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://[fd00::1]/",
    "http://localhost:8000/admin",
    "http://metadata.google.internal/",
]

PUBLIC_TARGETS = [
    "https://example.com/",
    "https://api.github.com/repos",
    "https://en.wikipedia.org/wiki/Main_Page",
]


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def public_dns() -> Iterator[None]:
    """Resolve every hostname to a public address so checks stay offline."""

    def _getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port or 80))]

    with patch("app.utils.ssrf.socket.getaddrinfo", _getaddrinfo):
        yield


@pytest.fixture
def restore_security_state() -> Iterator[None]:
    """Keep module-level security singletons isolated from other tests."""
    original_config = fs_isolation_manager.config
    original_mode = network_allowlist.strict_domain_mode
    original_domains = network_allowlist.get_allowed_domains()
    yield
    fs_isolation_manager.config = original_config
    network_allowlist.strict_domain_mode = original_mode
    for domain in original_domains:
        network_allowlist.add_allowed_domain(domain)
    for domain in network_allowlist.get_allowed_domains():
        if domain not in original_domains:
            network_allowlist.remove_allowed_domain(domain)


# --- Router mounting ---


def test_security_router_is_mounted() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/v1/security/quotas" in paths
    assert "/api/v1/security/fs-config" in paths
    assert "/api/v1/security/network-allowlist" in paths
    assert "/api/v1/security/network-allowlist/{domain}" in paths


def test_security_routes_answer_over_http(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/security/quotas").status_code == 200
    assert api_client.get("/api/v1/security/fs-config").status_code == 200
    assert api_client.get("/api/v1/security/network-allowlist").status_code == 200


def test_quotas_endpoints_round_trip(api_client: TestClient, restore_security_state) -> None:
    listed = api_client.get("/api/v1/security/quotas")
    assert listed.status_code == 200
    assert "_default" in listed.json()["quotas"]

    updated = api_client.put(
        "/api/v1/security/quotas",
        json={"agent_id": "agent-a3", "cpu_cores": 1.5, "memory_mb": 256},
    )
    assert updated.status_code == 200
    assert updated.json()["quota"]["memory_mb"] == 256

    reloaded = api_client.get("/api/v1/security/quotas")
    assert reloaded.json()["quotas"]["agent-a3"]["memory_mb"] == 256


def test_fs_config_update_persists_and_keeps_blocked_paths(
    api_client: TestClient, restore_security_state
) -> None:
    updated = api_client.put(
        "/api/v1/security/fs-config",
        json={"allowed_paths": ["/srv/data"], "max_file_size_mb": 12},
    )
    assert updated.status_code == 200

    fetched = api_client.get("/api/v1/security/fs-config")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["allowed_paths"] == ["/srv/data"]
    assert body["max_file_size_mb"] == 12
    assert "/etc/shadow" in body["blocked_paths"]


def test_network_allowlist_endpoints(api_client: TestClient, restore_security_state) -> None:
    initial = api_client.get("/api/v1/security/network-allowlist")
    assert initial.status_code == 200
    assert initial.json()["strict_domain_mode"] is False

    added = api_client.post("/api/v1/security/network-allowlist", json={"domain": "example.com"})
    assert added.status_code == 200
    assert "example.com" in added.json()["allowed_domains"]

    scoped = api_client.put(
        "/api/v1/security/network-allowlist/policy", json={"strict_domain_mode": True}
    )
    assert scoped.status_code == 200
    assert scoped.json()["strict_domain_mode"] is True
    assert api_client.get("/api/v1/security/network-allowlist").json()["strict_domain_mode"] is True

    removed = api_client.delete("/api/v1/security/network-allowlist/example.com")
    assert removed.status_code == 200
    assert "example.com" not in removed.json()["allowed_domains"]


# --- Allowlist decisions ---


@pytest.mark.parametrize("url", INTERNAL_TARGETS)
def test_allowlist_rejects_internal_and_metadata_targets(url: str) -> None:
    ok, reason = NetworkAllowlist().check_url(url)
    assert ok is False
    assert reason


@pytest.mark.parametrize("url", PUBLIC_TARGETS)
def test_allowlist_allows_public_targets(url: str, public_dns: None) -> None:
    ok, reason = NetworkAllowlist().check_url(url)
    assert ok is True, reason


def test_allowlist_rejects_allowlisted_loopback() -> None:
    allowlist = NetworkAllowlist(["127.0.0.1", "localhost"])
    assert allowlist.is_allowed("127.0.0.1") is True

    ok, reason = allowlist.check_url("http://127.0.0.1:8080/admin")
    assert ok is False
    assert reason


def test_allowlist_rejects_hostname_resolving_to_internal_address() -> None:
    def _getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", port or 80))]

    with patch("app.utils.ssrf.socket.getaddrinfo", _getaddrinfo):
        ok, reason = NetworkAllowlist().check_url("http://attacker.example/latest/meta-data/")

    assert ok is False
    assert "non-public" in reason


def test_strict_domain_mode_scopes_public_targets(public_dns: None) -> None:
    allowlist = NetworkAllowlist(["*.example.com"], strict_domain_mode=True)

    assert allowlist.check_url("https://docs.example.com/guide")[0] is True

    ok, reason = allowlist.check_url("https://api.github.com/repos")
    assert ok is False
    assert "not in the network allowlist" in reason


def test_fetch_url_tool_refuses_metadata_endpoint() -> None:
    from app.tools import builtins

    result = asyncio.run(builtins.fetch_url("http://169.254.169.254/latest/meta-data/"))
    assert "blocked" in result
    assert "169.254.169.254" in result
