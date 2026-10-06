"""Contract tests for the versioned built-in prompt layer."""

from app.core.prompts import (
    build_injected_prompt,
    list_versions,
    resolve_active_prompt,
    validate_prompt_contract,
)


def test_active_version_is_selected_and_versions_include_history():
    prompt = resolve_active_prompt("core.system")
    assert prompt.version == "1.3.0"
    versions = list_versions("core.system")
    assert {item["version"] for item in versions} == {"1.3.0", "1.2.0", "1.1.0", "1.0.0", "0.9.0"}
    assert any(item["status"] == "deprecated" for item in versions)
    active = [item for item in versions if item["status"] == "active"]
    assert [item["version"] for item in active] == ["1.3.0"]


def test_deprecated_version_can_be_resolved_for_rollback():
    prompt = resolve_active_prompt("core.system", "0.9.0")
    assert prompt.version == "0.9.0"
    assert prompt.status.value == "deprecated"

    previous = resolve_active_prompt("core.system", "1.1.0")
    assert previous.version == "1.1.0"
    assert previous.status.value == "deprecated"


def test_injection_contains_every_mandatory_core_section_and_hides_chain_of_thought():
    bundle = build_injected_prompt(task_type="implementation")
    prompt = bundle["system_prompt"]
    for section in (
        "ROLE_AND_SCOPE",
        "TASK_WORKFLOW",
        "TOOL_CONTRACT",
        "PROGRESS_REPORTING",
        "VALIDATION_AND_RECOVERY",
        "SAFE_OUTPUT",
        "AUTHORIZATION_AND_RISK",
        "ENGINEERING_DISCIPLINE",
        "RESEARCH_AND_KNOWLEDGE",
        "ENVIRONMENT_CONTEXT",
        "DELEGATION_PACKET",
        "EVIDENCE_HANDOFF",
    ):
        assert f"[{section}]" in prompt
    assert "chain-of-thought" in prompt
    assert "private scratch work" in prompt
    assert "system_prompt" not in bundle["metadata"]


def test_core_contract_declares_all_sections_and_no_hidden_reasoning_request():
    prompt = resolve_active_prompt("core.system")
    assert prompt.sections == (
        "ROLE_AND_SCOPE",
        "TASK_WORKFLOW",
        "TOOL_CONTRACT",
        "PROGRESS_REPORTING",
        "VALIDATION_AND_RECOVERY",
        "SAFE_OUTPUT",
        "AUTHORIZATION_AND_RISK",
        "ENGINEERING_DISCIPLINE",
        "RESEARCH_AND_KNOWLEDGE",
        "ENVIRONMENT_CONTEXT",
        "DELEGATION_PACKET",
        "EVIDENCE_HANDOFF",
    )
    assert "reveal hidden chain-of-thought" in prompt.body
    assert "private scratch work" in prompt.body


def test_tool_contract_validation_reports_missing_and_wrong_contract():
    errors = validate_prompt_contract(
        {
            "body": "[ROLE_AND_SCOPE] x",
            "sections": ("ROLE_AND_SCOPE",),
            "version": "1.0.0",
            "source": "test",
            "tool_contract_version": "0.1",
        }
    )
    assert any("missing sections" in error for error in errors)
    assert "unsupported tool contract version" in errors


def test_model_adaptation_is_selected_without_external_dependencies():
    bundle = build_injected_prompt(model_id="qwen", task_type="review")
    assert "MODEL_ADAPTATION" in bundle["system_prompt"]
    assert "JSON-compatible tool arguments" in bundle["system_prompt"]
    assert "validation_summary" in bundle["metadata"]["visible_event_fields"]


def test_v1_3_prompt_contains_context_delegation_and_evidence_contracts():
    prompt = resolve_active_prompt("core.system")
    assert "allowed paths" in prompt.body
    assert "raw errors" in prompt.body
    assert "source, kind, confidence, and timestamp" in prompt.body
