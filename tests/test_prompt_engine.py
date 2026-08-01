"""Tests for the three-layer prompt engine."""

from __future__ import annotations

import pytest

from app.core.prompt_engine.engine import PromptEngine
from app.core.prompt_engine.models import (
    ModelAdaptation,
    PromptFragment,
    PromptLayer,
    PromptTemplate,
    RuntimeContext,
)
from app.core.prompt_engine.template_repository import PromptTemplateRepository


class TestPromptLayer:
    def test_layer_ordering(self) -> None:
        assert PromptLayer.IMMUTABLE_BASE < PromptLayer.SESSION_TEMPLATE
        assert PromptLayer.SESSION_TEMPLATE < PromptLayer.DYNAMIC_RUNTIME


class TestPromptFragment:
    def test_render_without_context(self) -> None:
        fragment = PromptFragment(content="Hello world", layer=PromptLayer.IMMUTABLE_BASE)
        assert fragment.render() == "Hello world"

    def test_render_with_context(self) -> None:
        fragment = PromptFragment(
            content="Hello {{name}}", layer=PromptLayer.IMMUTABLE_BASE
        )
        assert fragment.render({"name": "Alice"}) == "Hello Alice"

    def test_render_multiple_variables(self) -> None:
        fragment = PromptFragment(
            content="{{greeting}} {{name}}",
            layer=PromptLayer.SESSION_TEMPLATE,
        )
        result = fragment.render({"greeting": "Hi", "name": "Bob"})
        assert result == "Hi Bob"


class TestPromptTemplate:
    def test_render_with_variables(self) -> None:
        template = PromptTemplate(
            name="Test",
            content="You are a {{role}} specialist.",
            variables={"role": "coding"},
        )
        assert template.render() == "You are a coding specialist."

    def test_render_with_override_variables(self) -> None:
        template = PromptTemplate(
            name="Test",
            content="You are a {{role}} specialist.",
            variables={"role": "coding"},
        )
        result = template.render({"role": "research"})
        assert result == "You are a research specialist."

    def test_to_dict_roundtrip(self) -> None:
        template = PromptTemplate(
            name="Test",
            description="A test template",
            content="Hello {{name}}",
            variables={"name": "World"},
            tags=["test"],
        )
        data = template.to_dict()
        restored = PromptTemplate.from_dict(data)
        assert restored.name == template.name
        assert restored.content == template.content
        assert restored.variables == template.variables
        assert restored.tags == template.tags


class TestPromptEngine:
    def test_initialization_has_base_prompt(self) -> None:
        engine = PromptEngine()
        fragments = engine.get_layer_fragments(PromptLayer.IMMUTABLE_BASE)
        assert len(fragments) >= 1

    def test_assemble_basic_prompt(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(model_id="test-model")
        prompt = engine.assemble_prompt(context)
        assert "Climber" in prompt
        assert "ReAct" in prompt

    def test_assemble_with_autonomous_mode(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(autonomous_mode=True)
        prompt = engine.assemble_prompt(context)
        assert "AUTONOMOUS" in prompt

    def test_assemble_with_sandbox(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(sandbox_enabled=True)
        prompt = engine.assemble_prompt(context)
        assert "SANDBOX" in prompt

    def test_assemble_with_mcp(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(mcp_ready=True)
        prompt = engine.assemble_prompt(context)
        assert "MCP" in prompt or "code search" in prompt.lower()

    def test_assemble_with_high_risk_permission(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(permission_level="high_risk")
        prompt = engine.assemble_prompt(context)
        assert "HIGH-RISK" in prompt

    def test_assemble_with_active_skills(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(active_skills=["web_search", "code_review"])
        prompt = engine.assemble_prompt(context)
        assert "web_search" in prompt
        assert "code_review" in prompt

    def test_assemble_with_objective(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(task_objective="Build a REST API")
        prompt = engine.assemble_prompt(context)
        assert "Build a REST API" in prompt

    def test_assemble_with_reflection(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext()
        prompt = engine.assemble_prompt(context, include_reflection=True)
        assert "REFLECTION" in prompt

    def test_session_fragment_can_be_added(self) -> None:
        engine = PromptEngine()
        fid = engine.register_session_fragment("Custom persona: be helpful")
        fragments = engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE)
        assert any(f.id == fid for f in fragments)

    def test_runtime_fragment_with_condition(self) -> None:
        engine = PromptEngine()
        engine.register_runtime_fragment(
            "Sandbox constraint", condition="sandbox_enabled"
        )
        context_no_sandbox = RuntimeContext(sandbox_enabled=False)
        context_with_sandbox = RuntimeContext(sandbox_enabled=True)
        prompt_no = engine.assemble_prompt(context_no_sandbox)
        prompt_yes = engine.assemble_prompt(context_with_sandbox)
        assert "Sandbox constraint" not in prompt_no
        assert "Sandbox constraint" in prompt_yes

    def test_clear_and_reinitialize_base(self) -> None:
        engine = PromptEngine()
        engine.clear_layer(PromptLayer.IMMUTABLE_BASE)
        fragments = engine.get_layer_fragments(PromptLayer.IMMUTABLE_BASE)
        assert len(fragments) == 1

    def test_remove_fragment(self) -> None:
        engine = PromptEngine()
        fid = engine.register_session_fragment("Temporary")
        assert engine.remove_fragment(fid)
        fragments = engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE)
        assert not any(f.id == fid for f in fragments)

    def test_remove_nonexistent_fragment(self) -> None:
        engine = PromptEngine()
        assert not engine.remove_fragment("nonexistent-id")

    def test_model_adaptation_qwen(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(model_id="qwen-turbo")
        prompt = engine.assemble_prompt(context)
        assert "QWEN" in prompt

    def test_model_adaptation_unknown_model(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(model_id="totally-unknown-model")
        prompt = engine.assemble_prompt(context)
        assert "Climber" in prompt

    def test_custom_model_adaptation(self) -> None:
        engine = PromptEngine()
        adaptation = ModelAdaptation(
            model_id="custom-model",
            system_prefix="[CUSTOM PREFIX]",
            system_suffix="[CUSTOM SUFFIX]",
        )
        engine.register_model_adaptation(adaptation)
        context = RuntimeContext(model_id="custom-model-v2")
        prompt = engine.assemble_prompt(context)
        assert "[CUSTOM PREFIX]" in prompt
        assert "[CUSTOM SUFFIX]" in prompt

    def test_apply_template(self) -> None:
        engine = PromptEngine()
        template = PromptTemplate(
            name="Test",
            content="You are a {{role}} expert.",
            variables={"role": "Python"},
        )
        engine.apply_template(template)
        context = RuntimeContext()
        prompt = engine.assemble_prompt(context)
        assert "Python expert" in prompt

    def test_estimate_token_count(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext()
        tokens = engine.estimate_token_count(context)
        assert tokens > 0

    def test_token_budget_enforcement(self) -> None:
        engine = PromptEngine()
        engine.set_token_budget(100)
        context = RuntimeContext()
        prompt = engine.assemble_prompt(context)
        assert len(prompt) // 4 <= 100

    def test_set_reflection_prompt(self) -> None:
        engine = PromptEngine()
        engine.set_reflection_prompt("Custom reflection prompt")
        context = RuntimeContext()
        prompt = engine.assemble_prompt(context, include_reflection=True)
        assert "Custom reflection prompt" in prompt

    def test_multi_agent_mode_adds_collaboration_prompt(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(multi_agent_mode=True)
        prompt = engine.assemble_prompt(context)
        assert "MULTI-AGENT COLLABORATION" in prompt
        assert "read_task_context" in prompt

    def test_memory_retrieval_adds_memory_prompt(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(memory_retrieval_enabled=True)
        prompt = engine.assemble_prompt(context)
        assert "MEMORY RETRIEVAL" in prompt
        assert "recall_memory" in prompt

    def test_fault_recovery_adds_recovery_prompt(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(fault_recovery_enabled=True)
        prompt = engine.assemble_prompt(context)
        assert "FAULT RECOVERY" in prompt
        assert "checkpoint" in prompt

    def test_combined_strategy_prompts(self) -> None:
        engine = PromptEngine()
        context = RuntimeContext(
            multi_agent_mode=True,
            memory_retrieval_enabled=True,
            fault_recovery_enabled=True,
        )
        prompt = engine.assemble_prompt(context)
        assert "MULTI-AGENT COLLABORATION" in prompt
        assert "MEMORY RETRIEVAL" in prompt
        assert "FAULT RECOVERY" in prompt


class TestPromptTemplateRepository:
    def test_builtins_loaded(self) -> None:
        repo = PromptTemplateRepository()
        builtins = repo.list_builtins()
        assert len(builtins) >= 4

    def test_create_template(self) -> None:
        repo = PromptTemplateRepository()
        template = repo.create(
            name="My Template",
            content="Hello {{name}}",
            variables={"name": "World"},
        )
        assert template.id
        assert template.name == "My Template"

    def test_get_template(self) -> None:
        repo = PromptTemplateRepository()
        created = repo.create(name="Test", content="Content")
        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.name == "Test"

    def test_list_by_tag(self) -> None:
        repo = PromptTemplateRepository()
        repo.create(name="Tagged", content="Content", tags=["code"])
        results = repo.list_by_tag("code")
        assert len(results) >= 1

    def test_update_template(self) -> None:
        repo = PromptTemplateRepository()
        created = repo.create(name="Original", content="Content")
        updated = repo.update(created.id, name="Updated")
        assert updated is not None
        assert updated.name == "Updated"

    def test_cannot_update_builtin(self) -> None:
        repo = PromptTemplateRepository()
        builtins = repo.list_builtins()
        if builtins:
            result = repo.update(builtins[0].id, name="Hacked")
            assert result is None

    def test_delete_template(self) -> None:
        repo = PromptTemplateRepository()
        created = repo.create(name="ToDelete", content="Content")
        assert repo.delete(created.id)
        assert repo.get(created.id) is None

    def test_cannot_delete_builtin(self) -> None:
        repo = PromptTemplateRepository()
        builtins = repo.list_builtins()
        if builtins:
            assert not repo.delete(builtins[0].id)

    def test_duplicate_template(self) -> None:
        repo = PromptTemplateRepository()
        created = repo.create(name="Original", content="Content")
        dup = repo.duplicate(created.id, "Copy")
        assert dup is not None
        assert dup.name == "Copy"
        assert dup.id != created.id

    def test_export_template(self) -> None:
        repo = PromptTemplateRepository()
        created = repo.create(name="Exportable", content="Content")
        exported = repo.export_template(created.id)
        assert exported is not None
        assert "Exportable" in exported

    def test_import_template(self) -> None:
        repo = PromptTemplateRepository()
        exported = repo.create(name="ImportSource", content="Import content")
        json_str = repo.export_template(exported.id)
        assert json_str is not None
        imported = repo.import_template(json_str)
        assert imported is not None
        assert imported.name == "ImportSource"

    def test_import_bulk(self) -> None:
        repo = PromptTemplateRepository()
        import json

        templates = [
            {"name": "T1", "content": "Content 1"},
            {"name": "T2", "content": "Content 2"},
        ]
        results = repo.import_bulk(json.dumps(templates))
        assert len(results) == 2

    def test_export_all_custom_only(self) -> None:
        repo = PromptTemplateRepository()
        repo.create(name="Custom1", content="Content1")
        exported = repo.export_all()
        import json

        data = json.loads(exported)
        assert isinstance(data, list)
        assert all(not item.get("is_builtin", False) for item in data)

    def test_list_custom(self) -> None:
        repo = PromptTemplateRepository()
        initial_count = len(repo.list_custom())
        repo.create(name="NewCustom", content="Content")
        assert len(repo.list_custom()) == initial_count + 1
