from datetime import UTC, datetime, timedelta

import pytest

from app.core.profile import PrivacyBoundaryError, ProfileEvent, ProfileLoopService
from app.core.profile.loop import OnlineKMeans, embed_event

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


# --- Feature hashing embedding -------------------------------------------------


def test_embed_event_is_deterministic_and_unit_normalized() -> None:
    vector_a = embed_event(event(task_type="coding", tool="terminal"))
    vector_b = embed_event(event(task_type="coding", tool="terminal"))
    assert vector_a == vector_b
    norm = sum(component * component for component in vector_a) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-9)


def test_embed_event_differs_for_different_events() -> None:
    coding_vector = embed_event(event(task_type="coding", tool="terminal"))
    browsing_vector = embed_event(event(task_type="browsing", tool="browser"))
    assert coding_vector != browsing_vector


def test_embed_event_respects_requested_dimension() -> None:
    vector = embed_event(event(), dim=6)
    assert len(vector) == 6


# --- Incremental online clustering ---------------------------------------------


def test_online_kmeans_seeds_distinct_clusters_before_updating() -> None:
    model = OnlineKMeans(k=2, dim=3)
    first_id, first_distance = model.partial_fit((1.0, 0.0, 0.0))
    second_id, second_distance = model.partial_fit((0.0, 1.0, 0.0))
    assert {first_id, second_id} == {0, 1}
    assert first_distance == 0.0
    assert second_distance == 0.0
    assert model.is_seeded is True


def test_online_kmeans_assigns_nearest_centroid_after_seeding() -> None:
    model = OnlineKMeans(k=2, dim=2)
    model.partial_fit((1.0, 0.0))
    model.partial_fit((0.0, 1.0))
    cluster_id, _distance = model.partial_fit((0.9, 0.1))
    assert cluster_id == 0


def test_online_kmeans_updates_centroid_toward_new_points() -> None:
    model = OnlineKMeans(k=1, dim=1)
    model.partial_fit((0.0,))
    for _ in range(50):
        model.partial_fit((1.0,))
    cluster_id, distance = model.partial_fit((1.0,))
    assert cluster_id == 0
    assert distance < 0.1


def test_online_kmeans_rejects_mismatched_dimension() -> None:
    model = OnlineKMeans(k=1, dim=2)
    with pytest.raises(ValueError, match="dimensional vector"):
        model.partial_fit((1.0,))


def test_online_kmeans_rejects_non_positive_weight() -> None:
    model = OnlineKMeans(k=1, dim=1)
    with pytest.raises(ValueError, match="weight must be positive"):
        model.partial_fit((1.0,), weight=0.0)


# --- Persona clustering integrated into the profile summary --------------------


def test_summary_exposes_persona_cluster_after_recording() -> None:
    service = ProfileLoopService(persona_clusters=2)
    service.record(event(task_type="coding", tool="terminal"))
    summary = service.summary(as_of=NOW)
    assert summary.persona_cluster is not None
    assert 0.0 <= summary.persona_cluster_confidence <= 1.0


def test_disabled_mode_leaves_persona_cluster_unset() -> None:
    service = ProfileLoopService(enabled=False)
    service.record(event())
    summary = service.summary(as_of=NOW)
    assert summary.persona_cluster is None
    assert summary.persona_cluster_confidence == 0.0


def test_repeated_similar_events_raise_persona_cluster_confidence() -> None:
    service = ProfileLoopService(persona_clusters=3)
    for _ in range(20):
        service.record(event(task_type="coding", tool="terminal", occurred_at=NOW))
    summary = service.summary(as_of=NOW)
    assert summary.persona_cluster_confidence > 0.3
