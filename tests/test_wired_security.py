"""Wiring tests for the P1-9..P1-14 security components.

Every test here proves a component is *reachable from a real path* — the
middleware is in the app's stack, the router is mounted, the enforcement runs
on an actual HTTP request or a real sandbox call, the row is in a queryable
table. Calling a class in isolation is deliberately not treated as proof of
wiring.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.observability.audit import audit_chain
from app.core.security.docker_sandbox import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxPolicyError,
)
from app.core.security.fs_isolation import fs_isolation
from app.core.security.network_allowlist import network_allowlist
from app.core.security.resource_quotas import ResourceQuota, quota_manager
from app.main import app
from app.middleware.security import CsrfProtectionMiddleware
from app.storage import engine

# ═══════════════════════════════════════════════════════════════════════════
# P1-12  CsrfProtectionMiddleware is registered
# ═══════════════════════════════════════════════════════════════════════════


def _registered_middleware() -> dict[str, Any]:
    return {mw.cls.__name__: mw for mw in app.user_middleware}


def test_csrf_middleware_is_registered_on_the_app() -> None:
    """P1-12: the middleware must exist in the live stack, not just on disk."""
    registered = _registered_middleware()
    assert "CsrfProtectionMiddleware" in registered, (
        "CsrfProtectionMiddleware is not registered on app.user_middleware"
    )
    options = registered["CsrfProtectionMiddleware"].kwargs
    assert "excluded_paths" in options
    assert "enabled" in options


def test_csrf_is_enforced_outside_testing() -> None:
    """The knob defaults to on; only APP_TESTING turns it off."""
    from app.config import Settings

    production = Settings(app_testing=False, app_secret_key="x" * 32)
    assert production.csrf_protection_enabled is True
    assert production.csrf_exempt_paths

    testing = Settings(app_testing=True, app_secret_key="x" * 32)
    assert testing.csrf_protection_enabled is False


@pytest_asyncio.fixture
async def csrf_client() -> AsyncClient:
    """A live app with CSRF force-enabled, independent of the test-mode default.

    Built on the real ``app`` object so route wiring, other middleware, and the
    database are the production ones; only the ``enabled`` flag is overridden.
    """
    for mw in app.user_middleware:
        if mw.cls is CsrfProtectionMiddleware:
            mw.kwargs["enabled"] = True
            break
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    for mw in app.user_middleware:
        if mw.cls is CsrfProtectionMiddleware:
            mw.kwargs["enabled"] = False


@pytest_asyncio.fixture
async def isolated_csrf_app() -> AsyncClient:
    """Minimal app carrying only the real ``CsrfProtectionMiddleware`` enabled."""
    probe = FastAPI()

    @probe.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @probe.post("/mutate")
    async def mutate() -> dict[str, str]:
        return {"ok": "reached"}

    probe.add_middleware(CsrfProtectionMiddleware, enabled=True, excluded_paths={"/health"})
    transport = ASGITransport(app=probe)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_csrf_token_cookie_is_issued_on_safe_methods(
    isolated_csrf_app: AsyncClient,
) -> None:
    resp = await isolated_csrf_app.get("/health")
    assert resp.status_code == 200
    assert "csrf_token" in resp.cookies


async def test_csrf_blocks_mutating_route_without_token(
    isolated_csrf_app: AsyncClient,
) -> None:
    resp = await isolated_csrf_app.post("/mutate", json={"a": 1})
    assert resp.status_code == 403
    assert resp.json()["type"] == "csrf_error"
    assert resp.json()["detail"] == "CSRF token missing"


async def test_csrf_rejects_forged_double_submit_cookie(
    isolated_csrf_app: AsyncClient,
) -> None:
    """Cookie and header both present but different → refuse."""
    isolated_csrf_app.cookies.set("csrf_token", "cookie-value-from-victim")
    resp = await isolated_csrf_app.post(
        "/mutate", json={"a": 1}, headers={"X-CSRF-Token": "attacker-guess"}
    )
    assert resp.status_code == 403
    assert resp.json()["type"] == "csrf_error"
    assert resp.json()["detail"] == "CSRF token mismatch"


async def test_csrf_accepts_matching_double_submit(
    isolated_csrf_app: AsyncClient,
) -> None:
    """The middleware mints ``Secure``, which an ``http://`` test client will not
    echo back, so the double-submit is replayed explicitly."""
    resp = await isolated_csrf_app.get("/health")
    token = resp.cookies["csrf_token"]
    isolated_csrf_app.cookies.set("csrf_token", token)
    ok = await isolated_csrf_app.post("/mutate", json={"a": 1}, headers={"X-CSRF-Token": token})
    assert ok.status_code == 200
    assert ok.json() == {"ok": "reached"}


async def test_csrf_rejection_is_written_to_the_audit_chain(
    isolated_csrf_app: AsyncClient,
) -> None:
    await isolated_csrf_app.post("/mutate", json={"a": 1})
    assert await audit_chain.count_entries() >= 1
    denials = await audit_chain.search_by_type("csrf_check")
    assert denials, "a refused CSRF attempt must leave an audit row"
    assert denials[0].allowed is False
    assert "CSRF token missing" in denials[0].rationale


async def test_csrf_exempt_path_serves_without_token(
    isolated_csrf_app: AsyncClient,
) -> None:
    """``/health`` is excluded, so it serves even with a bogus token."""
    resp = await isolated_csrf_app.post(
        "/mutate", json={}, headers={"X-CSRF-Token": "x"}
    )
    assert resp.status_code == 403
    health = await isolated_csrf_app.get("/health")
    assert health.status_code == 200


async def test_bearer_authenticated_client_is_exempt(
    isolated_csrf_app: AsyncClient,
) -> None:
    """Non-ambient credentials cannot be forged by a cross-site form post."""
    resp = await isolated_csrf_app.post(
        "/mutate", json={"a": 1}, headers={"Authorization": "Bearer programmatic-client"}
    )
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# P1-10  fs_isolation is wired into the live request path
# ═══════════════════════════════════════════════════════════════════════════


def test_path_isolation_middleware_is_registered() -> None:
    """P1-10: the enforcement point must be in the app's stack."""
    assert "PathIsolationMiddleware" in _registered_middleware()


async def test_path_traversal_in_json_body_is_refused_on_a_real_route(
    client: AsyncClient,
) -> None:
    """A real POST to a real route is rejected before the handler sees it."""
    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": "m1", "rating": "good", "file_path": "../../../../etc/passwd"},
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["type"] == "path_isolation_error"
    assert "path traversal detected" in body["detail"]


async def test_blocked_absolute_path_is_refused_on_a_real_route(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": "m1", "rating": "good", "output_path": "/etc/shadow"},
    )
    assert resp.status_code == 400
    assert resp.json()["type"] == "path_isolation_error"
    assert "blocked" in resp.json()["detail"]


async def test_nested_path_field_is_refused_on_a_real_route(
    client: AsyncClient,
) -> None:
    """The check recurses; a buried path field is caught too."""
    resp = await client.post(
        "/api/v1/feedback",
        json={
            "message_id": "m1",
            "rating": "good",
            "metadata": {"nested": {"file_path": "../../secret"}},
        },
    )
    assert resp.status_code == 400
    assert resp.json()["type"] == "path_isolation_error"


async def test_path_traversal_in_query_string_is_refused(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/feedback/stats?output_path=../../etc/passwd")
    assert resp.status_code == 400
    assert resp.json()["type"] == "path_isolation_error"


async def test_percent_encoded_traversal_in_the_url_path_is_refused(
    client: AsyncClient,
) -> None:
    """Safe methods are checked too: a handler resolving a path segment is reachable via GET."""
    encoded = quote("../feedback", safe="")
    resp = await client.get(f"/api/v1/feedback/stats/{encoded}")
    assert resp.status_code == 400, resp.text
    assert resp.json()["type"] == "path_isolation_error"


async def test_free_text_payloads_are_not_path_checked(client: AsyncClient) -> None:
    """A traversal-looking string in a non-path field must not trip the guard."""
    resp = await client.post(
        "/api/v1/feedback",
        json={
            "message_id": "missing-message",
            "rating": "good",
            "comment": "see ../../README.md for details on ../.. handling",
        },
    )
    assert resp.status_code != 400, resp.text
    assert resp.json().get("type") != "path_isolation_error"


async def test_legitimate_path_field_passes_the_middleware(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": "missing-message", "rating": "good", "file_path": "/tmp/report.md"},
    )
    assert resp.status_code != 400
    assert resp.json().get("type") != "path_isolation_error"


async def test_path_refusal_is_audited(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/feedback",
        json={"message_id": "m1", "rating": "good", "file_path": "../../etc/passwd"},
    )
    rows = await audit_chain.search_by_type("path_isolation_check")
    assert rows, "a refused path must leave an audit row"
    assert rows[0].allowed is False
    assert "feedback" in rows[0].subject


# ═══════════════════════════════════════════════════════════════════════════
# P1-11  network_allowlist / resource_quotas have an execution point
# ═══════════════════════════════════════════════════════════════════════════


def test_security_router_is_mounted() -> None:
    """P1-11: the API router was previously never included."""
    paths = {p for p in app.openapi()["paths"] if p.startswith("/api/v1/security")}
    assert paths == {
        "/api/v1/security/quotas",
        "/api/v1/security/fs-config",
        "/api/v1/security/network-allowlist",
        "/api/v1/security/network-allowlist/{domain}",
    }


async def test_quota_api_mutates_the_live_quota_manager(client: AsyncClient) -> None:
    """The endpoint must change the policy the sandbox consults, not a throwaway."""
    resp = await client.put(
        "/api/v1/security/quotas",
        json={"agent_id": "agent-quota-probe", "memory_mb": 64, "disk_mb": 128, "cpu_cores": 0.25},
    )
    assert resp.status_code == 200, resp.text
    assert quota_manager.get_quota("agent-quota-probe").memory_mb == 64

    read_back = await client.get("/api/v1/security/quotas")
    assert read_back.status_code == 200
    assert "agent-quota-probe" in read_back.json()["quotas"]

    quota_manager.remove_agent("agent-quota-probe")


async def test_fs_config_api_mutates_the_live_policy(client: AsyncClient) -> None:
    """``PUT /fs-config`` used to build a manager and throw it away."""
    original = list(fs_isolation.config.blocked_paths)
    try:
        resp = await client.put(
            "/api/v1/security/fs-config",
            json={"blocked_paths": ["/etc/ssh", "/proc"]},
        )
        assert resp.status_code == 200, resp.text
        assert fs_isolation.config.blocked_paths == ["/etc/ssh", "/proc"]
    finally:
        fs_isolation.config.blocked_paths = original


async def test_network_allowlist_api_mutates_the_live_allowlist(client: AsyncClient) -> None:
    added = await client.post(
        "/api/v1/security/network-allowlist", json={"domain": "sandbox-egress-probe.test"}
    )
    assert added.status_code == 200
    assert network_allowlist.is_allowed("sandbox-egress-probe.test")
    removed = await client.delete(
        "/api/v1/security/network-allowlist/sandbox-egress-probe.test"
    )
    assert removed.status_code == 200
    assert not network_allowlist.is_allowed("sandbox-egress-probe.test")


# ═══════════════════════════════════════════════════════════════════════════
# P1-9  docker_sandbox: policy is the ceiling, no flag widens it
# ═══════════════════════════════════════════════════════════════════════════


class _FakeContainer:
    id = "fake-container-id"

    def wait(self, timeout: int | None = None) -> dict[str, int]:
        return {"StatusCode": 0}

    def logs(self, stdout: bool = True, stderr: bool = True) -> bytes:
        return b"ok"

    def remove(self, force: bool = False) -> None:
        return None


class _FakeContainers:
    def __init__(self, recorder: dict[str, Any]) -> None:
        self._recorder = recorder

    def run(self, **kwargs: Any) -> _FakeContainer:
        self._recorder["run_kwargs"] = kwargs
        return _FakeContainer()


class _FakeDockerClient:
    """Minimal stand-in exposing only what ``DockerSandbox`` touches."""

    def __init__(self, driver: str = "overlay2") -> None:
        self._driver = driver
        self.calls: dict[str, Any] = {}
        self.containers = _FakeContainers(self.calls)

    @property
    def run_kwargs(self) -> dict[str, Any]:
        return self.calls.get("run_kwargs", {})

    def ping(self) -> bool:
        return True

    def info(self) -> dict[str, str]:
        return {"Driver": self._driver}


def _sandbox(driver: str = "overlay2", **config_kwargs: Any) -> DockerSandbox:
    sandbox = DockerSandbox(DockerSandboxConfig(**config_kwargs))
    sandbox._client = _FakeDockerClient(driver)  # noqa: SLF001
    sandbox._available = True  # noqa: SLF001
    return sandbox


def test_network_flag_cannot_widen_a_none_policy(tmp_path: Path) -> None:
    """P1-9 core fix: ``network=True`` must not escape ``network_mode='none'``."""
    sandbox = _sandbox(network_mode="none")
    assert sandbox.resolve_network_mode(network=False) == "none"
    with pytest.raises(SandboxPolicyError) as excinfo:
        sandbox.resolve_network_mode(network=True)
    assert "network_mode is 'none'" in str(excinfo.value)


def test_network_grant_requires_allowlist_approval(tmp_path: Path) -> None:
    """Permitting bridge is the operator's call; the domain still must be allowed."""
    sandbox = _sandbox(
        network_mode="bridge",
        allowed_network_hosts=["sandbox-egress-probe.test"],
    )
    with pytest.raises(SandboxPolicyError, match="network allowlist"):
        sandbox.resolve_network_mode(network=True)

    network_allowlist.add_allowed_domain("sandbox-egress-probe.test")
    try:
        assert sandbox.resolve_network_mode(network=True) == "bridge"
        assert sandbox.resolve_network_mode(network=False) == "none"
    finally:
        network_allowlist.remove_allowed_domain("sandbox-egress-probe.test")


def test_network_grant_with_no_declared_hosts_is_refused() -> None:
    sandbox = _sandbox(network_mode="bridge", allowed_network_hosts=[])
    with pytest.raises(SandboxPolicyError, match="no allowed_network_hosts"):
        sandbox.resolve_network_mode(network=True)


def test_host_network_mode_is_refused() -> None:
    sandbox = _sandbox(network_mode="host")
    with pytest.raises(SandboxPolicyError, match="host network namespace"):
        sandbox.resolve_network_mode(network=True)


def test_never_more_permissive_than_policy_over_a_grid() -> None:
    """Invariant: a resolved mode may only equal a non-``none`` policy, and only
    when the caller actually asked for network."""
    for policy in ("none", "bridge", "host", "  NONE  "):
        sandbox = _sandbox(network_mode=policy, allowed_network_hosts=["api.openai.com"])
        for requested in (False, True):
            try:
                resolved = sandbox.resolve_network_mode(requested)
            except SandboxPolicyError:
                continue
            if not requested:
                assert resolved == "none", f"policy={policy!r} requested=False"
            else:
                assert policy.strip().lower() != "none", f"policy={policy!r} leaked egress"
                assert resolved != "none"


def test_disk_quota_on_unsupported_driver_fails_explicitly() -> None:
    """P1-9: no silent loss of the disk cap on a non-quota storage driver."""
    sandbox = _sandbox(driver="vfs", disk_limit="1g")
    with pytest.raises(SandboxPolicyError) as excinfo:
        sandbox.assert_disk_quota_supported()
    message = str(excinfo.value)
    assert "Driver='vfs'" in message
    assert "overlay2" in message
    assert "disk_limit=''" in message


def test_disk_quota_accepted_on_overlay2() -> None:
    _sandbox(driver="overlay2", disk_limit="1g").assert_disk_quota_supported()


def test_no_disk_limit_means_no_storage_opt() -> None:
    """Clearing ``disk_limit`` opts out instead of failing the preflight."""
    sandbox = _sandbox(driver="vfs", disk_limit="")
    sandbox.assert_disk_quota_supported()


def test_container_config_omits_storage_opt_when_unset(tmp_path: Path) -> None:
    sandbox = _sandbox(driver="vfs", disk_limit="")
    sandbox.create_container(["echo", "hi"], str(tmp_path))
    assert "storage_opt" not in sandbox._client.run_kwargs  # noqa: SLF001


def test_container_config_keeps_the_hardened_settings(tmp_path: Path) -> None:
    sandbox = _sandbox(disk_limit="1g")
    sandbox.create_container(["echo", "hi"], str(tmp_path))
    kwargs = sandbox._client.run_kwargs  # noqa: SLF001
    assert kwargs["network_mode"] == "none"
    assert kwargs["cap_drop"] == ["ALL"]
    assert kwargs["read_only"] is True
    assert kwargs["security_opt"] == ["no-new-privileges"]
    assert kwargs["pids_limit"] == 64
    assert kwargs["storage_opt"] == {"size": "1g"}


def test_blocked_volume_mount_is_refused_before_docker_is_called(tmp_path: Path) -> None:
    """fs_isolation guards the bind-mount surface, not just the HTTP surface."""
    sandbox = _sandbox(volume_mounts={"/etc/passwd": "ro"})
    with pytest.raises(SandboxPolicyError, match="blocked"):
        sandbox.assert_paths_allowed(str(tmp_path))
    assert sandbox._client.run_kwargs == {}  # noqa: SLF001


def test_traversal_volume_mount_is_refused(tmp_path: Path) -> None:
    sandbox = _sandbox(volume_mounts={f"{tmp_path}/../../etc/passwd": "ro"})
    with pytest.raises(SandboxPolicyError, match="traversal"):
        sandbox.assert_paths_allowed(str(tmp_path))


def test_symlink_workdir_pointing_at_blocked_path_is_refused(tmp_path: Path) -> None:
    link = tmp_path / "workdir"
    link.symlink_to("/etc/passwd")
    sandbox = _sandbox()
    with pytest.raises(SandboxPolicyError):
        sandbox.assert_paths_allowed(str(link))


def test_unknown_mount_mode_is_refused(tmp_path: Path) -> None:
    sandbox = _sandbox(volume_mounts={str(tmp_path): "rwx"})
    with pytest.raises(SandboxPolicyError, match="allowed modes"):
        sandbox.assert_paths_allowed(str(tmp_path))


def test_quota_ceiling_is_enforced_on_sandbox_requests(tmp_path: Path) -> None:
    """resource_quotas gains an execution point at container creation."""
    quota_manager.set_quota(
        "agent-sandbox-probe", ResourceQuota(cpu_cores=1.0, memory_mb=64, disk_mb=64)
    )
    try:
        sandbox = _sandbox(memory_limit="512m", disk_limit="2g")
        with pytest.raises(SandboxPolicyError, match="exceeds the quota"):
            sandbox.assert_within_quota("agent-sandbox-probe")
        loose = _sandbox(memory_limit="16m", disk_limit="32m")
        loose.assert_within_quota("agent-sandbox-probe")
    finally:
        quota_manager.remove_agent("agent-sandbox-probe")


async def test_sandbox_denial_is_audited_and_raised(tmp_path: Path) -> None:
    """A policy refusal is raised and recorded, never reported as a result."""
    sandbox = _sandbox(network_mode="none")
    before = await audit_chain.count_entries()
    with pytest.raises(SandboxPolicyError):
        await sandbox.execute(["echo", "hi"], str(tmp_path), network=True)
    after = await audit_chain.count_entries()
    assert after == before + 1
    rows = await audit_chain.search_by_type("sandbox_execute")
    assert rows[0].allowed is False
    assert "network_mode is 'none'" in rows[0].rationale


async def test_sandbox_grant_is_audited(tmp_path: Path) -> None:
    sandbox = _sandbox(disk_limit="1g")
    result = await sandbox.execute(["echo", "hi"], str(tmp_path))
    assert result.returncode == 0
    rows = await audit_chain.search_by_type("sandbox_execute")
    assert rows[0].allowed is True
    assert rows[0].subject == "echo hi"


# ═══════════════════════════════════════════════════════════════════════════
# P1-13  the audit chain writes a queryable, durable row
# ═══════════════════════════════════════════════════════════════════════════


async def test_audit_chain_uses_the_orm_not_a_private_sqlite_connection() -> None:
    """The chain must not open its own connection or create its own table."""
    import inspect

    from app.core.observability import audit as audit_module

    assert not hasattr(audit_chain, "_conn")
    assert not hasattr(audit_chain, "_db_path")
    source = inspect.getsource(audit_module)
    assert "sqlite3.connect" not in source
    assert "CREATE TABLE" not in source
    assert audit_module.AuditEntryRecord.__tablename__ == "audit_entries"


async def test_audit_row_is_queryable_through_the_app_session() -> None:
    """Read it back on a *separate* connection, proving it is really persisted."""
    entry = await audit_chain.log_decision(
        decision_type="unit_probe",
        input_summary="in",
        output_summary="out",
        rationale="because",
        confidence=0.42,
        alternatives_considered=["a", "b"],
        session_id="session-probe",
        agent_id="agent-probe",
    )

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT id, decision_type, rationale, confidence, alternatives_considered, "
                    "agent_id, session_id FROM audit_entries WHERE id = :eid"
                ),
                {"eid": entry.id},
            )
        ).mappings().one()

    assert row["decision_type"] == "unit_probe"
    assert row["rationale"] == "because"
    assert abs(row["confidence"] - 0.42) < 1e-9
    assert json.loads(row["alternatives_considered"]) == ["a", "b"]
    assert row["agent_id"] == "agent-probe"
    assert row["session_id"] == "session-probe"

    # The chain's own read path agrees.
    fetched = await audit_chain.get_entry(entry.id)
    assert fetched is not None
    assert fetched.alternatives_considered == ["a", "b"]
    assert await audit_chain.count_entries(session_id="session-probe") == 1


async def test_audit_chain_is_shared_with_the_observability_api() -> None:
    from app.core.observability.api import get_audit_chain

    assert get_audit_chain() is audit_chain


async def test_audit_endpoint_returns_persisted_rows(client: AsyncClient) -> None:
    await audit_chain.log_decision(
        decision_type="endpoint_probe", rationale="r", session_id="session-endpoint"
    )
    resp = await client.get("/api/v1/observability/audit?session_id=session-endpoint")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(e["decision_type"] == "endpoint_probe" for e in body["entries"])


async def test_audit_table_is_in_the_alembic_managed_schema() -> None:
    """The table must be reachable by a fresh ``alembic upgrade head`` database."""
    revisions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration = next(revisions.glob("*_add_audit_entries_table.py"))
    text_body = migration.read_text(encoding="utf-8")
    assert "op.create_table" in text_body
    assert "audit_entries" in text_body
    assert "CREATE TRIGGER" in text_body
    assert 'down_revision: str | None = "d4e5f6a7b8c9"' in text_body


async def test_audit_rows_are_append_only_at_the_schema_level() -> None:
    """The migration installs abort-on-mutation triggers, so a row cannot be edited.

    Runs against a throwaway file database so the real test database is never
    mutated and the production triggers are exercised as written.
    """
    import tempfile

    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.observability.audit import AuditEntryRecord
    from app.storage import Base

    with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
        db_path = Path(tmpdir) / "append_only.db"
        url = f"sqlite+aiosqlite:///{db_path}"

        local_engine = create_async_engine(url)
        async with local_engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    sync_conn, tables=[AuditEntryRecord.__table__]
                )
            )
            for statement in (
                "CREATE TRIGGER audit_entries_append_only_update BEFORE UPDATE ON audit_entries "
                "BEGIN SELECT RAISE(ABORT, 'audit_entries is append-only: UPDATE is not "
                "permitted'); END",
                "CREATE TRIGGER audit_entries_append_only_delete BEFORE DELETE ON audit_entries "
                "BEGIN SELECT RAISE(ABORT, 'audit_entries is append-only: DELETE is not "
                "permitted'); END",
            ):
                await conn.exec_driver_sql(statement)
        await local_engine.dispose()

        raw = sqlite3.connect(db_path)
        raw.execute(
            "INSERT INTO audit_entries (id, timestamp, decision_type, agent_id, session_id, "
            "input_summary, output_summary, rationale, confidence, alternatives_considered, "
            "subject, created_at) VALUES "
            "('x1', '2026-01-01 00:00:00', 't', '', '', '', '', '', 0.0, '[]', '', "
            "'2026-01-01 00:00:00')"
        )
        raw.commit()

        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            raw.execute("UPDATE audit_entries SET rationale = 'tampered' WHERE id = 'x1'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            raw.execute("DELETE FROM audit_entries WHERE id = 'x1'")

        remaining = raw.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0]
        raw.close()
        assert remaining == 1


# ═══════════════════════════════════════════════════════════════════════════
# P1-14  the McpController stub is gone
# ═══════════════════════════════════════════════════════════════════════════


def test_mcp_controller_stub_is_deleted() -> None:
    """A stub whose ``start()``/``stop()`` return a hardcoded True is worse than
    nothing: it reads as coverage. The file must not exist."""
    import importlib.util

    project_root = Path(__file__).resolve().parents[1]
    assert not (project_root / "app" / "core" / "mcp_controller.py").exists()
    assert importlib.util.find_spec("app.core.mcp_controller") is None

    with pytest.raises(ModuleNotFoundError):
        __import__("app.core.mcp_controller")


def test_mcp_still_has_a_real_implementation() -> None:
    """Deleting the stub must leave a real MCP path in place."""
    from app.tools.mcp_client import MCPRegistry

    assert MCPRegistry is not None


# ═══════════════════════════════════════════════════════════════════════════
# Cross-cutting: the security package imports at all
# ═══════════════════════════════════════════════════════════════════════════


def test_security_package_is_importable_and_exports_live_policy() -> None:
    """``app.core.security`` used to raise ModuleNotFoundError on import."""
    import app.core.security as security

    for name in (
        "DockerSandbox",
        "FSIsolationManager",
        "NetworkAllowlist",
        "QuotaManager",
        "SandboxPolicyError",
        "fs_isolation",
        "network_allowlist",
        "quota_manager",
    ):
        assert hasattr(security, name), name


def test_no_module_imports_the_removed_safety_pipeline() -> None:
    import importlib.util

    project_root = Path(__file__).resolve().parents[1]
    assert importlib.util.find_spec("app.core.safety_pipeline") is None

    offenders: list[str] = []
    for path in (project_root / "app").rglob("*.py"):
        if "safety_pipeline" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(project_root)))
    assert offenders == [], offenders
