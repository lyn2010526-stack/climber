"""Tests for STRICT permission mode, tool name normalization and DENY precedence."""

from __future__ import annotations

from typing import Any

import pytest

from app.core.engine.validation import validate_tool_call
from app.core.permission_rules import (
    MODE_CONFIGS,
    PermissionConfig,
    PermissionMode,
    PermissionRule,
    RuleDecision,
    get_default_config,
    normalize_tool_name,
)
from app.core.session import AgentSession


class _StubSession:
    """Minimal session surface used by validate_tool_call."""

    def __init__(self, permission_config: PermissionConfig | None) -> None:
        self.agent_id = "agent-1"
        self.user_id = "user-1"
        self.permission_config = permission_config
        self._approved_tool_calls: set[str] = set()


class _StubRegistry:
    """Tool registry stub — the engine always passes a real registry."""

    def get_tool(self, _name: str) -> None:
        return None


def _session(config: PermissionConfig) -> _StubSession:
    return _StubSession(config)


def _validate(session: Any, tool_name: str, arguments: dict[str, Any]) -> tuple[bool, Any]:
    return validate_tool_call(session, tool_name, arguments, tool_registry=_StubRegistry())


# ---------------------------------------------------------------------------
# STRICT mode
# ---------------------------------------------------------------------------


def test_strict_mode_denies_unlisted_tools() -> None:
    config = PermissionConfig(mode=PermissionMode.STRICT)

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.DENY
    assert config.evaluate("run_command", {"command": "ls"}) == RuleDecision.DENY
    assert config.evaluate("web_search", {"query": "x"}) == RuleDecision.DENY


def test_strict_mode_denies_where_default_mode_asks() -> None:
    strict = PermissionConfig(mode=PermissionMode.STRICT)
    default = PermissionConfig(mode=PermissionMode.DEFAULT)

    assert strict.evaluate("write_file", {"path": "a.py"}) == RuleDecision.DENY
    assert default.evaluate("write_file", {"path": "a.py"}) == RuleDecision.ASK


def test_strict_mode_allows_explicitly_allowed_tools() -> None:
    config = PermissionConfig(
        mode=PermissionMode.STRICT,
        rules=[
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "git status"),
        ],
    )

    assert config.evaluate("read_file", {"path": "a.py"}) == RuleDecision.ALLOW
    assert config.evaluate("run_command", {"command": "git status"}) == RuleDecision.ALLOW
    # Pattern does not match, so the tool falls back to the strict default.
    assert config.evaluate("run_command", {"command": "rm -rf /tmp/x"}) == RuleDecision.DENY
    assert config.evaluate("write_file", {"path": "a.py", "content": "x"}) == RuleDecision.DENY


def test_strict_mode_ask_rule_wins_over_fallback_and_deny_rule_wins_over_ask() -> None:
    config = PermissionConfig(
        mode=PermissionMode.STRICT,
        rules=[
            PermissionRule(RuleDecision.ASK, "web_search"),
            PermissionRule(RuleDecision.ASK, "run_command"),
            PermissionRule(RuleDecision.DENY, "run_command", "rm -rf *"),
        ],
    )

    assert config.evaluate("web_search", {"query": "docs"}) == RuleDecision.ASK
    assert config.evaluate("run_command", {"command": "ls -la"}) == RuleDecision.ASK
    assert config.evaluate("run_command", {"command": "rm -rf /tmp/x"}) == RuleDecision.DENY


def test_strict_mode_whitelist_grants_access_and_deny_rule_still_wins() -> None:
    config = PermissionConfig(
        mode=PermissionMode.STRICT,
        allowed_tools=["edit_file", "file_delete"],
    )

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.ALLOW
    assert config.evaluate("write_file", {"path": "a.py"}) == RuleDecision.DENY

    # An explicit DENY rule overrides the whitelist entry.
    config.rules = [PermissionRule(RuleDecision.DENY, "file_delete")]
    assert config.evaluate("file_delete", {"path": "a.py"}) == RuleDecision.DENY


def test_mode_configs_provides_strict_config() -> None:
    assert PermissionMode.STRICT in MODE_CONFIGS

    config = MODE_CONFIGS[PermissionMode.STRICT]()
    assert config.mode == PermissionMode.STRICT
    assert config.evaluate("read_file", {"path": "a.py"}) == RuleDecision.ALLOW
    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.DENY
    assert config.evaluate("run_command", {"command": "rm -rf /tmp/x"}) == RuleDecision.DENY
    assert config.evaluate("run_command", {"command": "pytest -q"}) == RuleDecision.DENY


# ---------------------------------------------------------------------------
# Tool name normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("edit", "edit_file"),
        ("edit_file", "edit_file"),
        ("file_write", "write_file"),
        ("write_file", "write_file"),
        ("file_read", "read_file"),
        ("list_dir", "list_directory"),
        ("list_files", "list_directory"),
        ("list_directory", "list_directory"),
        ("bash", "run_command"),
        ("run_command", "run_command"),
        ("native_run", "run_command"),
        ("rm", "file_delete"),
        ("delete", "file_delete"),
        ("native_web_search", "web_search"),
        ("  EDIT_FILE  ", "edit_file"),
        ("edit_*", "edit_*"),
        ("*", "*"),
        ("", ""),
    ],
)
def test_normalize_tool_name(raw: str, canonical: str) -> None:
    assert normalize_tool_name(raw) == canonical


@pytest.mark.parametrize("rule_tool", ["edit", "edit_file"])
@pytest.mark.parametrize("call_tool", ["edit", "edit_file"])
def test_edit_alias_matches_edit_file_in_both_directions(rule_tool: str, call_tool: str) -> None:
    config = PermissionConfig(rules=[PermissionRule(RuleDecision.DENY, rule_tool)])

    assert config.evaluate(call_tool, {"path": "a.py"}) == RuleDecision.DENY


def test_deny_rule_written_with_old_alias_blocks_canonical_call() -> None:
    config = PermissionConfig(
        mode=PermissionMode.STRICT,
        rules=[PermissionRule(RuleDecision.DENY, "edit")],
        allowed_tools=["edit_file"],
    )

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.DENY


def test_allow_rule_written_with_old_alias_permits_canonical_call() -> None:
    config = PermissionConfig(
        mode=PermissionMode.STRICT,
        rules=[PermissionRule(RuleDecision.ALLOW, "edit")],
    )

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.ALLOW


def test_list_dir_alias_matches_list_files_and_list_directory() -> None:
    for call_tool in ("list_dir", "list_files", "list_directory"):
        config = PermissionConfig(rules=[PermissionRule(RuleDecision.DENY, "list_dir")])
        assert config.evaluate(call_tool, {"path": "."}) == RuleDecision.DENY


def test_bash_alias_pattern_matches_run_command_call() -> None:
    config = PermissionConfig(
        rules=[PermissionRule(RuleDecision.DENY, "bash", "rm -rf *")],
    )

    assert config.evaluate("run_command", {"command": "rm -rf build"}) == RuleDecision.DENY
    assert config.evaluate("bash", {"command": "rm -rf build"}) == RuleDecision.DENY
    assert config.evaluate("run_command", {"command": "ls -la"}) == RuleDecision.ASK


def test_edit_alias_pattern_matches_canonical_path_argument() -> None:
    config = PermissionConfig(
        rules=[PermissionRule(RuleDecision.DENY, "edit", "*.env")],
    )

    assert config.evaluate("edit_file", {"path": "secrets.env"}) == RuleDecision.DENY
    assert config.evaluate("edit_file", {"path": "app/main.py"}) == RuleDecision.ASK


def test_denied_tools_list_accepts_aliases() -> None:
    config = PermissionConfig(denied_tools=["edit"])

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.DENY


def test_allowed_tools_list_accepts_aliases() -> None:
    config = PermissionConfig(mode=PermissionMode.STRICT, allowed_tools=["edit"])

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.ALLOW


def test_glob_rule_still_matches_canonical_names() -> None:
    config = PermissionConfig(rules=[PermissionRule(RuleDecision.ALLOW, "edit_*")])

    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.ALLOW


def test_engine_validation_uses_the_same_normalization() -> None:
    config = PermissionConfig(rules=[PermissionRule(RuleDecision.DENY, "edit")])
    session = _session(config)

    allowed, reason = _validate(session, "edit_file", {"path": "a.py"})

    assert allowed is False
    assert "Permission denied by rules: edit_file" in reason


def test_engine_validation_treats_aliases_like_canonical_names() -> None:
    session = _session(PermissionConfig())

    assert _validate(session, "list_files", {"path": "."})[0] is True
    assert _validate(session, "list_dir", {"path": "."})[0] is True
    assert _validate(session, "list_directory", {"dir": "."})[0] is True

    # An alias call gets the same decision as its canonical name; the payload keeps
    # the caller's own tool name so the executor can still find the tool.
    bash_reason = _validate(session, "bash", {"command": "npm test"})[1]
    assert isinstance(bash_reason, dict)
    assert bash_reason["requires_approval"] is True
    assert bash_reason["tool_name"] == "bash"
    assert isinstance(_validate(session, "run_command", {"command": "npm test"})[1], dict)


def test_engine_validation_applies_deny_rule_to_alias_call() -> None:
    session = _session(get_default_config())

    bash_result = _validate(session, "bash", {"command": "rm -rf /"})
    assert bash_result[0] is False
    assert bash_result[1] == "Permission denied by rules: bash"

    native_result = _validate(session, "native_run", {"command": "rm -rf /"})
    assert native_result[0] is False
    assert native_result[1] == "Permission denied by rules: native_run"


# ---------------------------------------------------------------------------
# DENY precedence
# ---------------------------------------------------------------------------


def test_deny_rule_wins_over_allowed_tools_whitelist() -> None:
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        allowed_tools=["read_file"],
        rules=[PermissionRule(RuleDecision.DENY, "edit_file")],
    )

    # The whitelist gate must not downgrade DENY to ASK.
    assert config.evaluate("edit_file", {"path": "a.py"}) == RuleDecision.DENY
    # Non-whitelisted tool without a matching rule still asks.
    assert config.evaluate("write_file", {"path": "a.py"}) == RuleDecision.ASK


def test_ask_rule_wins_over_allowed_tools_whitelist() -> None:
    config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        allowed_tools=["read_file"],
        rules=[PermissionRule(RuleDecision.ASK, "web_search")],
    )

    assert config.evaluate("web_search", {"query": "x"}) == RuleDecision.ASK


def test_validation_deny_survives_previously_approved_call() -> None:
    from app.core.engine.validation import _approval_key

    config = PermissionConfig(rules=[PermissionRule(RuleDecision.DENY, "edit_file")])
    session = _session(config)
    arguments = {"path": "a.py", "old_string": "x", "new_string": "y"}
    session._approved_tool_calls.add(_approval_key("edit_file", arguments))

    allowed, reason = _validate(session, "edit_file", arguments)

    assert allowed is False
    assert "Permission denied by rules: edit_file" in reason


def test_validation_approval_suppresses_ask_but_not_deny() -> None:
    from app.core.engine.validation import _approval_key

    ask_config = PermissionConfig(rules=[PermissionRule(RuleDecision.ASK, "edit_file")])
    session = _session(ask_config)
    arguments = {"path": "a.py", "old_string": "x", "new_string": "y"}
    session._approved_tool_calls.add(_approval_key("edit_file", arguments))

    assert _validate(session, "edit_file", arguments)[0] is True

    session.permission_config = PermissionConfig(
        rules=[PermissionRule(RuleDecision.DENY, "edit_file")]
    )

    assert _validate(session, "edit_file", arguments)[0] is False


def test_validation_without_approval_still_asks() -> None:
    session = _session(PermissionConfig(rules=[PermissionRule(RuleDecision.ASK, "edit_file")]))

    allowed, reason = _validate(session, "edit_file", {"path": "a.py"})

    assert allowed is False
    assert isinstance(reason, dict)
    assert reason["requires_approval"] is True


def test_real_session_default_config_still_allows_reads() -> None:
    session = AgentSession(agent_id="a", user_id="u", provider="openai", model_id="m", api_key="k")

    assert session.permission_config is not None
    assert _validate(session, "read_file", {"path": "a.py"})[0] is True
    assert _validate(session, "list_dir", {"path": "."})[0] is True
    # Default mode still asks for unlisted write/network tools.
    allowed, reason = _validate(session, "web_search", {"query": "x"})
    assert allowed is False
    assert isinstance(reason, dict)
    assert reason["requires_approval"] is True
