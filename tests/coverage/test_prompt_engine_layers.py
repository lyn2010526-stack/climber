"""Coverage tests for app.core.prompt_engine.engine."""

from __future__ import annotations

from app.core.prompt_engine.engine import MODEL_ADAPTATIONS, PromptEngine
from app.core.prompt_engine.models import (
    ModelAdaptation,
    PromptLayer,
    PromptTemplate,
    RuntimeContext,
)


def _engine() -> PromptEngine:
    return PromptEngine()


def test_defaults_and_layer_fragments() -> None:
    engine = _engine()
    base = engine.get_layer_fragments(PromptLayer.IMMUTABLE_BASE)
    assert len(base) == 1
    assert engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE) == []
    assert engine.get_layer_fragments(PromptLayer.DYNAMIC_RUNTIME) == []


def test_register_fragments_and_remove() -> None:
    engine = _engine()
    b = engine.register_base_fragment("base", priority=5)
    s = engine.register_session_fragment("session", priority=2)
    r = engine.register_runtime_fragment("runtime", condition="autonomous_mode")
    assert b and s and r

    assert len(engine.get_layer_fragments(PromptLayer.IMMUTABLE_BASE)) == 2
    assert [f.content for f in engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE)] == [
        "session"
    ]
    assert engine.remove_fragment(s) is True
    assert engine.remove_fragment("nope") is False


def test_clear_layer_variants() -> None:
    engine = _engine()
    engine.register_session_fragment("s")
    engine.register_runtime_fragment("r")

    engine.clear_layer(PromptLayer.SESSION_TEMPLATE)
    assert engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE) == []

    engine.clear_layer(PromptLayer.DYNAMIC_RUNTIME)
    assert engine.get_layer_fragments(PromptLayer.DYNAMIC_RUNTIME) == []

    engine.clear_layer(PromptLayer.IMMUTABLE_BASE)
    # base layer is re-initialized with the immutable default
    assert len(engine.get_layer_fragments(PromptLayer.IMMUTABLE_BASE)) == 1

    # unknown layer value is a no-op
    engine.clear_layer(99)  # type: ignore[arg-type]
    assert len(engine.get_layer_fragments(PromptLayer.IMMUTABLE_BASE)) == 1


def test_assemble_prompt_skips_empty_fragments_and_adds_reflection() -> None:
    engine = _engine()
    engine.register_session_fragment("   ")
    engine.register_base_fragment("   ")
    engine.register_runtime_fragment("   ")
    prompt = engine.assemble_prompt(RuntimeContext(), include_reflection=True)
    assert "[TOOL CALL REFLECTION]" in prompt


def test_build_runtime_parts_all_flags() -> None:
    engine = _engine()
    ctx = RuntimeContext(
        autonomous_mode=True,
        sandbox_enabled=True,
        mcp_ready=True,
        permission_level="high_risk",
        active_skills=["alpha", "beta"],
        task_objective="Build a thing",
        multi_agent_mode=True,
        memory_retrieval_enabled=True,
        fault_recovery_enabled=True,
    )
    prompt = engine.assemble_prompt(ctx)
    assertions = [
        "[AUTONOMOUS AGENT MODE]",
        "[SANDBOX MODE ACTIVE]",
        "[MCP SERVICES ACTIVE]",
        "[HIGH-RISK PERMISSIONS GRANTED]",
        "ACTIVE SKILLS",
        "alpha",
        "[CURRENT OBJECTIVE]",
        "[TASK PLANNING]",
        "[MULTI-AGENT COLLABORATION]",
        "[MEMORY RETRIEVAL]",
        "[FAULT RECOVERY]",
    ]
    for text in assertions:
        assert text in prompt


def test_runtime_fragment_conditions() -> None:
    engine = _engine()
    engine.register_runtime_fragment("autonomous-only", condition="autonomous_mode")
    engine.register_runtime_fragment("skill-only", condition="skill_active:special")
    engine.register_runtime_fragment("always")

    ctx = RuntimeContext(autonomous_mode=False, active_skills=[])
    prompt = engine.assemble_prompt(ctx)
    assert "autonomous-only" not in prompt
    assert "skill-only" not in prompt
    assert "always" in prompt

    ctx2 = RuntimeContext(autonomous_mode=True, active_skills=["special"])
    prompt2 = engine.assemble_prompt(ctx2)
    assert "autonomous-only" in prompt2
    assert "skill-only" in prompt2


def test_evaluate_condition_all_paths() -> None:
    engine = _engine()
    assert (
        engine._evaluate_condition("autonomous_mode", RuntimeContext(autonomous_mode=True)) is True
    )
    assert (
        engine._evaluate_condition("sandbox_enabled", RuntimeContext(sandbox_enabled=True)) is True
    )
    assert engine._evaluate_condition("mcp_ready", RuntimeContext(mcp_ready=True)) is True
    assert (
        engine._evaluate_condition("high_risk", RuntimeContext(permission_level="high_risk"))
        is True
    )
    assert (
        engine._evaluate_condition("skill_active:abc", RuntimeContext(active_skills=["abc"]))
        is True
    )
    assert engine._evaluate_condition("model_is:qwen", RuntimeContext(model_id="qwen-max")) is True
    assert engine._evaluate_condition("unknown-condition", RuntimeContext()) is True
    # non-string condition triggers the defensive exception path
    assert engine._evaluate_condition(123, RuntimeContext()) is True  # type: ignore[arg-type]


def test_model_adaptation_lookup_and_register() -> None:
    engine = _engine()
    assert engine.get_model_adaptation("") is None
    assert engine.get_model_adaptation("qwen-2.5") is MODEL_ADAPTATIONS["qwen"]
    assert engine.get_model_adaptation("unknown-model") is None

    custom = ModelAdaptation(model_id="custom", system_prefix="PRE", system_suffix="POST")
    engine.register_model_adaptation(custom)
    assert engine.get_model_adaptation("custom-v1") is custom


def test_apply_model_adaptation_variants() -> None:
    engine = _engine()
    assert engine._apply_model_adaptation("prompt", "") == "prompt"
    adapted = engine._apply_model_adaptation("prompt", "qwen-72b")
    assert "prompt" in adapted
    assert adapted != "prompt"
    assert engine._apply_model_adaptation("prompt", "unknown") == "prompt"


def test_model_adaptation_adapt_base_prompt() -> None:
    adaptation = ModelAdaptation(
        model_id="m",
        system_prefix="prefix-text",
        system_suffix="suffix-text",
        tool_instruction="tool-text",
    )
    result = adaptation.adapt_base_prompt("base")
    assert result == "prefix-text\n\nbase\n\ntool-text\n\nsuffix-text"

    plain = ModelAdaptation(model_id="m")
    assert plain.adapt_base_prompt("only-base") == "only-base"


def test_enforce_token_budget_variants() -> None:
    engine = _engine()
    engine.set_token_budget(1000)
    assert engine._enforce_token_budget("short") == "short"

    engine.set_token_budget(0)
    huge = "x" * 4000
    assert engine._enforce_token_budget(huge) == ""

    engine.set_token_budget(500)
    trimmed = engine._enforce_token_budget(huge)
    assert len(trimmed) < len(huge)
    assert len(trimmed) > 0


def test_reflection_and_token_budget_setters() -> None:
    engine = _engine()
    engine.set_reflection_prompt("custom reflection")
    prompt = engine.assemble_prompt(RuntimeContext(), include_reflection=True)
    assert "custom reflection" in prompt

    engine.set_token_budget(50)
    assert engine._token_budget == 50


def test_apply_template_and_estimate_tokens() -> None:
    engine = _engine()
    template = PromptTemplate(name="persona", content="Hello {{name}}", variables={"name": "World"})
    engine.apply_template(template)
    frags = engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE)
    assert any("Hello World" in f.content for f in frags)

    engine.apply_template(template, variables={"name": "Override"})
    frags2 = engine.get_layer_fragments(PromptLayer.SESSION_TEMPLATE)
    assert any("Hello Override" in f.content for f in frags2)

    count = engine.estimate_token_count(RuntimeContext())
    assert count > 0


def test_runtime_custom_variables_rendered() -> None:
    engine = _engine()
    engine.register_runtime_fragment("Value: {{custom}}")
    ctx = RuntimeContext(custom_variables={"custom": "rendered"})
    prompt = engine.assemble_prompt(ctx)
    assert "Value: rendered" in prompt
