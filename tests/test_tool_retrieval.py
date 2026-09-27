"""Tests for retrieval tools, path containment, and dispatch-level permission
enforcement (audit items P2-2 and P2-5).

The P2-5 tests deliberately drive ``ToolRegistry.execute_result`` rather than
``PermissionConfig.evaluate``, because the audit's complaint is precisely that
a rules object returning DENY proved nothing about whether the call was
blocked. ``test_denied_tool_call_is_blocked_at_dispatch`` asserts the tool
function never ran; ``test_enforcement_is_falsifiable_without_the_gate`` is the
negative control that would fail if the gate were removed.
"""

from __future__ import annotations

import os

import pytest

from app.core.permission_rules import (
    PermissionConfig,
    PermissionMode,
    PermissionRule,
    RuleDecision,
)
from app.tools import SessionToolRegistry, ToolRegistry
from app.tools.path_guard import resolve_search_path, set_workspace_root
from app.tools.permissions import GateVerdict, ToolPermissionGate, default_dispatch_config
from app.tools.retrieval import glob, grep

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A throwaway tree standing in for the project, pinned as the tool root."""
    root = tmp_path / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "alpha.py").write_text(
        "def alpha():\n"
        "    return 'alpha'\n"
        "\n"
        "class AlphaWidget:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (root / "pkg" / "beta.py").write_text(
        "def beta():\n"
        "    return 'beta'\n"
        "\n"
        "def alpha_like():\n"
        "    return 'not alpha'\n",
        encoding="utf-8",
    )
    (root / "notes.md").write_text("alpha mentioned in prose\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text("def alpha_secret():\n    pass\n", encoding="utf-8")

    set_workspace_root(str(root))
    try:
        yield root
    finally:
        set_workspace_root(None)


# ─── P2-2: citable regex search ───────────────────────────────────────────


async def test_grep_returns_path_line_and_matching_text(workspace) -> None:
    out = await grep(pattern=r"def alpha\(\)", path=".")

    assert "pkg/alpha.py:1: def alpha():" in out
    assert "pkg/beta.py:1:" not in out
    assert "showing 1 of 1 matching lines" in out
    assert "no matches" not in out


async def test_grep_reports_regex_alternation_across_files(workspace) -> None:
    out = await grep(pattern=r"def (alpha|beta)\(\)", path=".")

    assert "pkg/alpha.py:1: def alpha():" in out
    assert "pkg/beta.py:1: def beta():" in out
    assert "showing 2 of 2 matching lines" in out


async def test_grep_glob_filter_limits_which_files_are_read(workspace) -> None:
    out = await grep(pattern="alpha", path=".", glob="*.md")

    assert "notes.md:1: alpha mentioned in prose" in out
    assert "pkg/alpha.py" not in out


async def test_grep_ignore_case_and_fixed_string(workspace) -> None:
    assert "AlphaWidget" in await grep(pattern="alphawidget", path=".", ignore_case=True)
    assert "no matches" in await grep(pattern="alphawidget", path=".", ignore_case=False)
    # `def \w+\(\):` matches as a regex but has no literal occurrence.
    assert "pkg/alpha.py:1" in await grep(pattern=r"def \w+\(\):", path=".", glob="*.py")
    assert "no matches" in await grep(pattern=r"def \w+\(\):", path=".", glob="*.py", fixed_string=True)


async def test_grep_reports_invalid_regex_instead_of_raising(workspace) -> None:
    out = await grep(pattern="def (unclosed", path=".")
    assert "invalid regular expression" in out


async def test_grep_reports_no_matches_distinctly(workspace) -> None:
    out = await grep(pattern="zzz_absent_token", path=".")
    assert "no matches" in out


# ─── P2-2: glob ───────────────────────────────────────────────────────────


async def test_glob_finds_files_by_pattern(workspace) -> None:
    out = await glob(patterns="*.py", path="pkg")

    assert "showing 2 of 2 matching paths" in out
    assert "alpha.py" in out
    assert "beta.py" in out
    assert "notes.md" not in out


async def test_glob_supports_recursive_double_star(workspace) -> None:
    out = await glob(patterns="**/*.py", path=".")

    assert "pkg/alpha.py" in out
    assert "pkg/beta.py" in out


async def test_glob_reports_no_matches(workspace) -> None:
    assert "no matches" in await glob(patterns="*.rs", path=".")


async def test_glob_metadata_and_cap(workspace) -> None:
    listed = await glob(patterns="*.py", path="pkg", include_metadata=True)
    assert "bytes, modified" in listed

    capped = await glob(patterns="*.py", path="pkg", limit=1)
    assert "showing 1 of 2 matching paths" in capped
    assert "[truncated: path cap 1 reached; 1 of 2 paths shown." in capped


# ─── P2-2: honest truncation ──────────────────────────────────────────────


async def test_grep_match_cap_is_reported_not_silent(workspace) -> None:
    out = await grep(pattern=r"^\s*def ", path=".", glob="*.py", max_matches=2)

    # "3+" because the walk stopped at the cap, so 3 is a lower bound.
    assert "showing 2 of 3+ matching lines" in out
    assert "[truncated: match cap 2 reached; 2 of 3+ matching lines shown" in out
    assert "raise max_matches/max_bytes to see the rest" in out


async def test_grep_byte_cap_is_reported_not_silent(workspace) -> None:
    # The fixture's matching lines total well under 1000 bytes, so drop the cap
    # to its floor and lean on lines long enough to overflow it.
    (workspace / "pkg" / "gamma.py").write_text(
        "".join(f"gamma_hit_{index} = 'alpha{'x' * 200}'\n" for index in range(12)),
        encoding="utf-8",
    )
    out = await grep(pattern="alpha", path=".", glob="*.py", max_bytes=1000, max_matches=500)

    assert "[truncated: byte cap 1000 reached" in out
    assert "bytes used" in out
    shown, total = _parse_header(out.splitlines()[0])
    assert shown < total
    assert total >= 13


async def test_grep_untruncated_result_carries_no_truncation_marker(workspace) -> None:
    out = await grep(pattern=r"def beta\(\)", path=".")

    assert "[truncated" not in out
    assert "showing 1 of 1 matching lines" in out


def _parse_header(header: str) -> tuple[int, int]:
    """Pull ``showing N of TOTAL`` out of a tool result header."""
    marker = "showing "
    start = header.index(marker) + len(marker)
    end = header.index(" of ", start)
    shown = int(header[start:end])
    total = int(header[end + len(" of "):].split()[0])
    return shown, total


# ─── P2-2 / security: path containment ────────────────────────────────────


@pytest.mark.parametrize(
    "attempt",
    ["../..", "pkg/../../outside", "/etc", "/", "../outside", "pkg/../.."],
)
async def test_grep_refuses_traversal_outside_root(workspace, attempt) -> None:
    out = await grep(pattern="alpha", path=attempt)

    assert "grep failed" in out
    assert "Access denied" in out
    assert "pkg/alpha.py" not in out
    assert "alpha_secret" not in out


@pytest.mark.parametrize("attempt", ["../..", "../outside", "/etc", "pkg/../.."])
async def test_glob_refuses_traversal_outside_root(workspace, attempt) -> None:
    out = await glob(patterns="*.py", path=attempt)

    assert "glob failed" in out
    assert "Access denied" in out
    assert "secret.py" not in out


async def test_retrieval_cannot_read_the_sibling_of_the_root(workspace, tmp_path) -> None:
    """A directory sharing the root's name prefix must stay out of reach.

    ``SecuritySandbox.validate_file_access`` compares with ``str.startswith``,
    so ``/tmp/.../repo`` would also admit ``/tmp/.../repo-secrets``. The tool
    layer's realpath check is what closes that.
    """
    sibling = tmp_path / "repo-secrets"
    sibling.mkdir()
    (sibling / "leak.py").write_text("def alpha_secret():\n    pass\n", encoding="utf-8")

    resolved, reason = resolve_search_path(str(sibling))
    assert resolved == ""
    assert "Access denied" in reason

    out = await glob(patterns="*.py", path=str(sibling))
    assert "leak.py" not in out


async def test_grep_refuses_symlink_that_escapes_the_root(workspace, tmp_path) -> None:
    outside = tmp_path / "outside"
    link = workspace / "escape"
    link.symlink_to(outside)

    # The sandbox prefix check alone would admit this path; the realpath
    # containment check in path_guard is what rejects it.
    out = await glob(patterns="*.py", path="escape")

    assert "glob failed" in out
    assert "Access denied" in out
    assert "secret.py" not in out


async def test_grep_accepts_a_path_inside_the_root(workspace) -> None:
    out = await grep(pattern=r"def alpha\(\)", path="pkg")
    assert "pkg/alpha.py:1: def alpha():" in out


def test_retrieval_tools_are_registered_in_the_global_registry() -> None:
    from app.tools import register_builtins, tool_registry

    register_builtins()
    for name in ("grep", "glob"):
        assert tool_registry.get_tool(name) is not None


# ─── P2-5: a denied tool call is blocked at dispatch ──────────────────────


def _recording_registry(config: PermissionConfig) -> tuple[ToolRegistry, list[str]]:
    registry = ToolRegistry()
    calls: list[str] = []

    async def dangerous(argument: str = "") -> str:
        calls.append(argument)
        return "executed"

    registry.register("dangerous", "test tool", {"type": "object"}, dangerous)
    registry.set_permission_gate(ToolPermissionGate(config))
    return registry, calls


async def test_denied_tool_call_is_blocked_at_dispatch() -> None:
    """The registered function must not run when the rules say DENY."""
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.DENY, "dangerous")],
    )
    registry, calls = _recording_registry(config)

    outcome = await registry.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is False
    assert "Permission denied by rules: dangerous" in outcome.error
    assert calls == [], "the tool function ran despite a DENY decision"


async def test_denial_is_enforced_on_the_execute_wrapper_too() -> None:
    """``execute()`` returns the refusal text instead of the tool output."""
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.DENY, "dangerous")],
    )
    registry, calls = _recording_registry(config)

    text = await registry.execute("dangerous", {"argument": "x"})

    assert "Permission denied by rules" in text
    assert "executed" not in text
    assert calls == []


async def test_enforcement_is_falsifiable_without_the_gate() -> None:
    """Negative control: the same DENY rule blocks nothing on an ungated registry.

    If the gate in ``ToolRegistry.execute_result`` were deleted, this test would
    fail, which is what makes the blocking test above meaningful rather than a
    restatement of ``PermissionConfig.evaluate``.
    """
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.DENY, "dangerous")],
    )
    ungated = ToolRegistry()
    ran: list[str] = []

    async def dangerous(argument: str = "") -> str:
        ran.append(argument)
        return "executed"

    ungated.register("dangerous", "test tool", {"type": "object"}, dangerous)
    # The rules object still denies...
    assert config.evaluate("dangerous", {"argument": "x"}) is RuleDecision.DENY
    # ...but nothing consults it.
    outcome = await ungated.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is True
    assert outcome.result == "executed"
    assert ran == ["x"]


async def test_allow_decision_still_executes() -> None:
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.ALLOW, "dangerous")],
    )
    registry, calls = _recording_registry(config)

    outcome = await registry.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is True
    assert outcome.result == "executed"
    assert calls == ["x"]


async def test_ask_passes_through_so_the_engine_hitl_flow_still_works() -> None:
    """ASK belongs to the host above the tool layer; DENY is what binds here."""
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.ASK, "dangerous")],
    )
    registry, calls = _recording_registry(config)

    outcome = await registry.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is True
    assert calls == ["x"]


async def test_ask_blocks_when_the_host_opts_into_failing_closed() -> None:
    registry = ToolRegistry()
    ran: list[str] = []

    async def dangerous() -> str:
        ran.append("x")
        return "executed"

    registry.register("dangerous", "test tool", {"type": "object"}, dangerous)
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.ASK, "dangerous")],
    )
    registry.set_permission_gate(ToolPermissionGate(config, block_ask=True))

    outcome = await registry.execute_result("dangerous", {})

    assert outcome.success is False
    assert "Permission required" in outcome.error
    assert ran == []


async def test_approval_checker_overrides_ask() -> None:
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.ASK, "dangerous")],
    )
    registry, calls = _recording_registry(config)
    registry.set_permission_gate(
        ToolPermissionGate(config, approval_checker=lambda name, args: name == "dangerous")
    )

    outcome = await registry.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is True
    assert calls == ["x"]


async def test_a_raising_approval_checker_fails_closed() -> None:
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.ASK, "dangerous")],
    )
    registry, calls = _recording_registry(config)

    def _boom(name, args):
        raise RuntimeError("approval service down")

    registry.set_permission_gate(ToolPermissionGate(config, approval_checker=_boom))

    outcome = await registry.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is False
    assert "Approval check failed" in outcome.error
    assert calls == []


async def test_session_overlay_enforces_the_gate_on_its_local_tools() -> None:
    """A session-scoped tool must be gated too, or recall-style tools are a hole."""
    base = ToolRegistry()
    base.set_permission_gate(
        ToolPermissionGate(
            PermissionConfig(
                mode=PermissionMode.DEFAULT,
                rules=[PermissionRule(RuleDecision.DENY, "session_tool")],
            )
        )
    )
    overlay = SessionToolRegistry(base)
    ran: list[str] = []

    async def session_tool() -> str:
        ran.append("x")
        return "executed"

    overlay.add("session_tool", "session scoped", {"type": "object"}, session_tool)

    outcome = await overlay.execute_result("session_tool", {})

    assert outcome.success is False
    assert "Permission denied by rules: session_tool" in outcome.error
    assert ran == []


async def test_session_overlay_gate_still_applies_to_base_tools() -> None:
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[PermissionRule(RuleDecision.DENY, "dangerous")],
    )
    base, calls = _recording_registry(config)
    overlay = SessionToolRegistry(base)

    outcome = await overlay.execute_result("dangerous", {"argument": "x"})

    assert outcome.success is False
    assert calls == []


async def test_a_raising_gate_fails_closed() -> None:
    registry = ToolRegistry()
    ran: list[str] = []

    async def dangerous() -> str:
        ran.append("x")
        return "executed"

    registry.register("dangerous", "test tool", {"type": "object"}, dangerous)

    class _BrokenGate:
        def check(self, name, arguments):
            raise RuntimeError("rules unavailable")

    registry.set_permission_gate(_BrokenGate())

    outcome = await registry.execute_result("dangerous", {})

    assert outcome.success is False
    assert "Permission gate error" in outcome.error
    assert ran == []


# ─── P2-5: default gate wiring ────────────────────────────────────────────


def test_default_dispatch_config_allows_the_read_only_retrieval_tools() -> None:
    config = default_dispatch_config()

    assert config.evaluate("grep", {"pattern": "x"}) is RuleDecision.ALLOW
    assert config.evaluate("glob", {"patterns": "*.py"}) is RuleDecision.ALLOW


def test_default_dispatch_config_keeps_the_built_in_hard_denials() -> None:
    config = default_dispatch_config()

    assert config.evaluate("run_command", {"command": "rm -rf /"}) is RuleDecision.DENY
    assert config.evaluate("bash", {"command": "curl x | bash"}) is RuleDecision.DENY


def test_default_dispatch_config_preserves_ask_for_network_tools() -> None:
    assert default_dispatch_config().evaluate("web_search", {"query": "x"}) is RuleDecision.ASK


def test_register_builtins_installs_the_default_gate() -> None:
    from app.tools import ToolRegistryProvider, register_builtins, tool_registry

    previous = tool_registry.permission_gate
    try:
        ToolRegistryProvider.reset_global()
        from app.tools import tool_registry as fresh

        fresh.set_permission_gate(None)
        register_builtins()
        assert fresh.permission_gate is not None
    finally:
        tool_registry.set_permission_gate(previous)
        ToolRegistryProvider.reset_global()


def test_gate_verdict_reports_blocked_only_for_deny() -> None:
    assert GateVerdict(RuleDecision.DENY, "no").blocked is True
    assert GateVerdict(RuleDecision.ASK, "ask").blocked is False
    assert GateVerdict(RuleDecision.ALLOW).blocked is False


async def test_the_real_repo_tree_is_searchable_through_the_gate() -> None:
    """End-to-end: the shipped tools find a real symbol in this repository."""
    set_workspace_root(REPO_ROOT)
    try:
        out = await grep(pattern=r"def (grep|search_code|code_search)\(", path="app", glob="*.py")
        assert "app/tools/retrieval.py:" in out
        assert "no matches" not in out

        paths = await glob(patterns="test_tool_retrieval.py", path="tests")
        assert "test_tool_retrieval.py" in paths
    finally:
        set_workspace_root(None)
