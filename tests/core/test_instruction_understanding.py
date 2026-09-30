from app.core.instruction import InstructionCandidate, understand_instruction
from app.core.observability.alignment import validate_instruction_goal


def test_short_sentence_is_understood():
    result = understand_instruction("修复登录超时")
    assert result.main_goal == "修复登录超时"
    assert result.progress == "understood"


def test_metaphor_is_retained_as_ambiguity():
    result = understand_instruction("把这个方案磨亮")
    assert "磨亮" in result.ambiguities
    assert result.progress == "needs_clarification"


def test_raw_text_and_special_characters_are_verbatim():
    raw = "请处理：中文\n  A&B <C> [原样]"
    assert understand_instruction(raw).raw_text == raw


def test_missing_goal_is_blocked():
    result = validate_instruction_goal("继续")
    assert result.status == "blocked"
    assert result.needs_clarification is True
    assert result.clarification_questions


def test_explicit_goal_is_ready():
    result = validate_instruction_goal("实现用户导出")
    assert result.status == "ready"
    assert result.goal == "实现用户导出"


def test_constraints_are_extracted():
    result = understand_instruction("实现导出，必须保留原文，只能修改核心模块")
    assert "必须保留原文" in result.constraints
    assert "只能修改核心模块" in result.constraints


def test_confidence_is_bounded_and_context_can_raise_it():
    without_context = understand_instruction("实现缓存")
    with_context = understand_instruction("实现缓存", context="当前任务是性能优化")
    assert 0.0 <= without_context.confidence <= 1.0
    assert 0.0 <= with_context.confidence <= 1.0
    assert with_context.confidence > without_context.confidence


def test_plain_language_summary_contains_progress():
    result = understand_instruction("实现搜索")
    assert "目标：实现搜索" in result.plain_language_summary
    assert "进度：understood" in result.plain_language_summary


def test_trace_payload_matches_existing_instruction_trace_fields():
    result = understand_instruction("实现搜索")
    payload = result.to_trace_payload(session_id="session-1", user_id="user-1")
    assert payload["raw_text"] == "实现搜索"
    assert payload["session_id"] == "session-1"
    assert payload["task_spec"]["main_goal"] == "实现搜索"
    assert payload["goal_preserved"] is True


def test_extension_candidates_are_appended_without_replacing_raw_instruction():
    candidate = InstructionCandidate("补充目标", "profile", 0.5)
    result = understand_instruction("实现基础目标", supplemental_candidates=[candidate])
    assert result.raw_text == "实现基础目标"
    assert result.main_goal == "实现基础目标"
    assert result.candidates[-1] == candidate
    assert result.to_task_spec()["raw_text"] == "实现基础目标"
