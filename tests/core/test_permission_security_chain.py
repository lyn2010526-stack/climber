"""End-to-end security gates for the three-tier permission chain."""

from __future__ import annotations

import sqlite3

from app.core.engine.validation import validate_tool_call
from app.core.observability.audit import AuditChain, security_audit_chain
from app.core.permission_rules import PermissionConfig, PermissionRule, PermissionTier, RuleDecision
from app.core.security_sandbox import CodeSandbox, PermissionOverlay, SecuritySandbox, SandboxConfig


async def _awaitable(value):
    return value


class _Session:
    agent_id = "agent"
    user_id = "user"
    _approved_tool_calls: set[str] = set()

    def __init__(self, config: PermissionConfig) -> None:
        self.permission_config = config


class _Registry:
    def get_tool(self, _name: str):
        return None


def test_permission_tiers_preserve_read_and_restrict_writes(tmp_path) -> None:
    read_only = PermissionConfig(tier=PermissionTier.READ_ONLY)
    assert read_only.evaluate("read_file", {"path": "a.py"}) == RuleDecision.ALLOW
    assert read_only.evaluate("write_file", {"path": "a.py"}) == RuleDecision.DENY

    partial = PermissionConfig(tier=PermissionTier.PARTIAL_WRITE)
    assert partial.evaluate("write_file", {"path": "a.py"}) == RuleDecision.ASK
    assert partial.evaluate("run_command", {"command": "echo ok"}) == RuleDecision.DENY

    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    allowed, reason = validate_tool_call(
        _Session(read_only), "write_file", {"path": str(tmp_path / "a.py"), "content": "x"},
        sandbox=sandbox, tool_registry=_Registry(),
    )
    assert allowed is False
    assert "Permission denied by rules" in reason


def test_validation_chain_blocks_script_before_execution(tmp_path) -> None:
    config = PermissionConfig(
        tier=PermissionTier.FULL_WRITE,
        rules=[PermissionRule(RuleDecision.ALLOW, "run_command")],
    )
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    allowed, reason = validate_tool_call(
        _Session(config), "run_command", {"command": "echo ok", "code": "import os\nresult = 1"},
        sandbox=sandbox, tool_registry=_Registry(),
    )
    assert allowed is False
    assert "Script preflight blocked" in reason
    assert security_audit_chain.search_by_type("script_denied")


def test_sandbox_hazard_interception_remains_before_execution(tmp_path) -> None:
    sandbox = SecuritySandbox(SandboxConfig(workdir=str(tmp_path)))
    allowed, reason = sandbox.validate_command("rm -rf /")
    assert allowed is False
    assert "hazard pattern" in reason


def test_audit_buffers_storage_failure_and_retries() -> None:
    chain = AuditChain()
    chain._conn.close()
    entry = chain.log_decision("permission_denied", rationale="blocked")
    assert entry.id
    assert len(chain._pending_events) == 1

    chain._conn = sqlite3.connect(":memory:", check_same_thread=False)
    chain._conn.row_factory = sqlite3.Row
    chain._create_tables()
    assert chain.retry_pending() == 1
    assert chain.count_entries() == 1


async def test_cache_failure_falls_back_to_source(monkeypatch) -> None:
    from app.storage import cache as cache_module

    class BrokenRedis:
        async def get(self, _key):
            raise RuntimeError("redis unavailable")

        async def set(self, *_args, **_kwargs):
            raise RuntimeError("redis unavailable")

    calls = 0

    @cache_module.cached(ttl=1, key_prefix="security-test")
    async def source() -> str:
        nonlocal calls
        calls += 1
        return "safe-fallback"

    monkeypatch.setattr(cache_module, "get_redis", lambda: _awaitable(BrokenRedis()))
    assert await source() == "safe-fallback"
    assert calls == 1


def test_code_sandbox_rejects_empty_preflight() -> None:
    result = CodeSandbox().preflight_script(" ")
    assert result.allowed is False
    assert "empty script" in result.reason
