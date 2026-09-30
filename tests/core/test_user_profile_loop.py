from datetime import UTC, datetime, timedelta

import pytest

from app.core.profile import ProfileEvent, ProfileLoopService, PrivacyBoundaryError


NOW = datetime(2026, 9, 30, tzinfo=UTC)


def event(**kwargs: object) -> ProfileEvent:
    defaults: dict[str, object] = {
        "instruction": "完成任务",
        "task_type": "coding",
        "outcome": "success",
        "occurred_at": NOW,
    }
    defaults.update(kwargs)
    return ProfileEvent(**defaults)  # type: ignore[arg-type]


def test_recent_event_has_more_weight_than_old_event() -> None:
    service = ProfileLoopService(half_life_days=10)
    service.record(event(task_type="recent", occurred_at=NOW))
    service.record(event(task_type="old", occurred_at=NOW - timedelta(days=10)))
    summary = service.summary(as_of=NOW)
    assert summary.task_preferences["recent"] > summary.task_preferences["old"]


def test_old_events_decay_exponentially() -> None:
    service = ProfileLoopService(half_life_days=10)
    service.record(event(task_type="now", occurred_at=NOW))
    service.record(event(task_type="past", occurred_at=NOW - timedelta(days=10)))
    assert service.summary(as_of=NOW).task_preferences["now"] > service.summary(as_of=NOW).task_preferences["past"]


def test_success_reinforces_preference() -> None:
    service = ProfileLoopService()
    service.record(event(task_type="coding", outcome="success"))
    assert service.summary(as_of=NOW).success_rate == 1.0
    assert service.summary(as_of=NOW).task_preferences["coding"] > 0.5


def test_failure_and_negative_feedback_calibrate_down() -> None:
    service = ProfileLoopService()
    service.record(event(task_type="coding", outcome="failure", feedback="negative"))
    assert service.summary(as_of=NOW).success_rate == 0.0
    assert service.summary(as_of=NOW).task_preferences["coding"] < 0.5


def test_interruption_and_retry_are_exposed() -> None:
    service = ProfileLoopService()
    service.record(event(interrupted=True, retried=True, outcome="failure"))
    summary = service.summary(as_of=NOW)
    assert summary.interruption_rate == 1.0
    assert summary.retry_rate == 1.0


def test_tool_preference_is_recorded() -> None:
    service = ProfileLoopService()
    service.record(event(tool="terminal"))
    assert service.summary(as_of=NOW).tool_preferences["terminal"] > 0


def test_disabled_mode_discards_events_and_context() -> None:
    service = ProfileLoopService(enabled=False)
    assert service.record(event()) is False
    summary = service.summary(as_of=NOW)
    assert summary.enabled is False
    assert summary.confidence == 0.0
    assert service.auxiliary_context("当前明确指令") ["suggestions"] == {
        "task_type": None,
        "tool": None,
        "reasoning_level": None,
    }


def test_current_instruction_has_priority_over_profile_hint() -> None:
    service = ProfileLoopService()
    service.record(event(task_type="coding", tool="terminal"))
    context = service.auxiliary_context("请使用浏览器完成当前任务", as_of=NOW)
    assert context["current_instruction"] == "请使用浏览器完成当前任务"
    assert context["profile_may_not_override_current_instruction"] is True
    assert context["profile_role"] == "auxiliary_context"


def test_external_privacy_sources_are_rejected() -> None:
    service = ProfileLoopService()
    with pytest.raises(PrivacyBoundaryError):
        service.record(event(source="purchase_history"))
