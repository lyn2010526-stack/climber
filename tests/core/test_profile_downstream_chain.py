from app.core.instruction import understand_instruction
from app.core.profile import ProfileEvent, ProfileLoopService
from app.core.vector_memory import rank_with_profile


def test_profile_context_reaches_instruction_without_overriding_goal() -> None:
    service = ProfileLoopService()
    service.record(ProfileEvent("完成", "coding", "success", tool="terminal"))
    context = service.auxiliary_context("修复导出")
    result = understand_instruction("修复导出", profile_context=context)
    assert result.main_goal == "修复导出"
    assert "profile_task_type:coding" in result.profile_evidence
    assert result.to_task_spec()["profile_evidence"]


def test_profile_ranking_is_bounded_and_empty_safe() -> None:
    context = {
        "enabled": True,
        "confidence": 1.0,
        "task_preferences": {"coding": 1.0},
        "tool_preferences": {},
        "reasoning_preferences": {},
    }
    documents = [
        {"id": "a", "score": 0.8, "metadata": {"task_type": "review"}},
        {"id": "b", "score": 0.7, "metadata": {"task_type": "coding"}},
    ]
    ranked = rank_with_profile(documents, context)
    assert ranked[0]["id"] == "b"
    assert rank_with_profile([], context) == []
    assert rank_with_profile(documents, None) == documents


def test_profile_regression_evaluation_is_safe_for_empty_profile() -> None:
    result = ProfileLoopService().regression_evaluation("coding")
    assert result == {
        "expected_task_type": "coding",
        "predicted_task_type": None,
        "matched": False,
        "confidence": 0.0,
        "has_signal": False,
    }
