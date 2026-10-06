"""Dual closed-loop integration tests: profile loop x genetic evolution loop.

Covers the full algorithm layer end to end on the code actually present in the
repository: the persisted profile loop (ProfileStore), the genetic prompt
evolution engine, the DualLoopCoordinator bridge, the agent-engine hooks, and
the silent degradation paths.

Parallel-task interfaces still in flight are probed at module level and the
affected cases are skipped via ``pytest.mark.skipif`` so the file always
collects cleanly, no matter which branches are merged.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.core.profile as profile_package
import app.core.profile.loop as profile_loop_module
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.engine.dual_loop import (
    EVOLUTION_TICK_INTERVAL,
    DualLoopCoordinator,
)
from app.core.engine.run_storage import RunStorage
from app.core.profile import ProfileEvent, ProfileLoopService, ProfileSummary
from app.core.profile.persistence import ProfileStore
from app.core.profile.settings import NOTICE_VERSION
from app.core.prompts.evolution import (
    EvolutionConfig,
    PromptEvolutionEngine,
    PromptGenome,
    aggregate_scores,
    bootstrap_population,
    load_population,
    save_population,
)
from app.core.task_state_machine import TaskState
from app.storage import Base, async_session
from app.storage.models_prompt_genome import PromptGenomeRow
from app.storage.repository_prompt_genome import get_best_genome
from app.storage.repository_user_profile import get_snapshot, list_events

NOW = datetime(2026, 9, 30, tzinfo=UTC)

# --- Parallel-task interface probes (task C extensions) -------------------------

HAS_PROFILE_BLEND = hasattr(profile_package, "blend") or hasattr(profile_loop_module, "blend")
HAS_PROFILE_RECORD_RUN = hasattr(ProfileStore, "record_run")
HAS_PROMPT_HINTS = "prompt_hints" in ProfileSummary.__dataclass_fields__


def _user_id() -> str:
    return str(uuid.uuid4())


async def _enable_learning(user: str) -> None:
    await ProfileStore().update_settings(user, enabled=True, consent_version=NOTICE_VERSION)


def _profile_event(**kwargs: object) -> ProfileEvent:
    defaults: dict[str, object] = {
        "instruction": "fix the login bug",
        "task_type": "debugging",
        "outcome": "success",
        "occurred_at": NOW,
    }
    defaults.update(kwargs)
    return ProfileEvent(**defaults)  # type: ignore[arg-type]


# --- Profile closed loop: mixed outcomes move every rate the right way ----------


def test_profile_summary_rates_follow_mixed_outcomes() -> None:
    service = ProfileLoopService()
    for _ in range(5):
        service.record(_profile_event(task_type="debugging", outcome="success"))
    for _ in range(3):
        service.record(_profile_event(task_type="review", outcome="failure"))
    service.record(_profile_event(task_type="debugging", outcome="failure", retried=True))
    service.record(_profile_event(task_type="debugging", outcome="failure", interrupted=True))

    summary = service.summary(as_of=NOW)
    assert summary.success_rate == pytest.approx(0.5)
    assert summary.retry_rate == pytest.approx(0.1)
    assert summary.interruption_rate == pytest.approx(0.1)
    assert summary.task_preferences
    assert summary.confidence == pytest.approx(1.0)


async def test_profile_store_round_trip_through_database() -> None:
    user = _user_id()
    await _enable_learning(user)
    store = ProfileStore()
    await store.record_event(
        user, instruction="fix the login bug", task_type="debugging", outcome="success"
    )
    await store.record_event(
        user, instruction="refactor storage", task_type="refactoring", outcome="success"
    )
    await store.record_event(
        user,
        instruction="write docs",
        task_type="documentation",
        outcome="failure",
        feedback="negative",
    )
    await store.record_event(
        user, instruction="retry deploy", task_type="deployment", outcome="failure", retried=True
    )
    await store.record_event(
        user, instruction="stop run", task_type="coding", outcome="failure", interrupted=True
    )

    summary = await store.summary(user)
    assert summary.success_rate == pytest.approx(0.4)
    assert 0.0 < summary.retry_rate <= 0.2
    assert 0.0 < summary.interruption_rate <= 0.2

    async with async_session() as db:
        assert len(await list_events(db, user)) == 5

    replayed = await ProfileStore().summary(user)
    assert replayed.success_rate == summary.success_rate
    assert replayed.retry_rate == summary.retry_rate
    assert replayed.interruption_rate == summary.interruption_rate

    async with async_session() as db:
        snapshot = await get_snapshot(db, user)
    assert snapshot is not None
    assert snapshot.payload["success_rate"] == summary.success_rate
    assert snapshot.payload["retry_rate"] == summary.retry_rate
    assert snapshot.payload["interruption_rate"] == summary.interruption_rate


async def test_profile_store_suggestions_are_non_empty_after_samples() -> None:
    user = _user_id()
    await _enable_learning(user)
    store = ProfileStore()
    await store.record_event(
        user,
        instruction="fix the login bug",
        task_type="debugging",
        outcome="success",
        tool="terminal",
    )
    hints = await store.suggestions(user, "fix another bug")
    assert hints["current_instruction"] == "fix another bug"
    assert hints["profile_may_not_override_current_instruction"] is True
    assert hints["suggestions"]["task_type"] == "debugging"


@pytest.mark.skipif(
    not HAS_PROMPT_HINTS,
    reason="pending task C: ProfileSummary.prompt_hints is not delivered yet",
)
async def test_profile_summary_exposes_prompt_hints() -> None:
    user = _user_id()
    await _enable_learning(user)
    store = ProfileStore()
    await store.record_event(
        user, instruction="fix the login bug", task_type="debugging", outcome="success"
    )
    summary = await store.summary(user)
    assert summary.prompt_hints


@pytest.mark.skipif(
    not HAS_PROFILE_RECORD_RUN,
    reason="pending task C: ProfileStore.record_run is not delivered yet (current API is record_event)",
)
async def test_profile_store_record_run_mixed_outcomes() -> None:
    user = _user_id()
    await _enable_learning(user)
    store = ProfileStore()
    await store.record_run(user, instruction="fix the login bug", outcome="success")
    await store.record_run(user, instruction="retry deploy", outcome="failure", retried=True)
    summary = await store.summary(user)
    assert summary.success_rate == pytest.approx(0.5)
    assert summary.retry_rate == pytest.approx(0.5)


# --- Evolution closed loop: bootstrap, non-decreasing best, persistence ---------


def _length_evaluator(genome: PromptGenome) -> dict[str, float]:
    words = len(genome.prompt_text.split())
    has_goal = "goal" in genome.prompt_text
    return {
        "task_success": (0.3 if has_goal else 0.1) + min(0.6, words * 0.02),
        "metaphor_comprehension": 0.8 if has_goal else 0.2,
        "meta_correction": 0.5,
        "safety_violation": 0.0,
    }


def test_bootstrap_population_seeds_mutated_variants() -> None:
    population = bootstrap_population(
        "Restate the user's underlying goal before acting.", 6, random_seed=42
    )
    assert len(population) == 6
    assert len({genome.id for genome in population}) == 6
    assert population[0].prompt_text == "Restate the user's underlying goal before acting."
    assert all(genome.prompt_text for genome in population)


def test_evolution_best_composite_never_decreases() -> None:
    population = bootstrap_population(
        "Restate the user's underlying goal before acting.", 6, random_seed=42
    )
    engine = PromptEvolutionEngine(
        EvolutionConfig(population_size=6, elite_count=2, max_generations=5, random_seed=42)
    )
    final, history = engine.run_evolution(population, _length_evaluator)
    assert len(history) >= 1
    assert history == sorted(history)
    final_best = max(engine.composite(genome) for genome in final)
    assert final_best >= history[0] - 1e-9


def test_min_improvement_stops_evolution_on_plateau() -> None:
    population = bootstrap_population(
        "Restate the user's underlying goal before acting.", 4, random_seed=7
    )
    engine = PromptEvolutionEngine(
        EvolutionConfig(
            population_size=4, elite_count=2, max_generations=8, min_improvement=10.0, random_seed=7
        )
    )
    _final, history = engine.run_evolution(population, _length_evaluator)
    assert len(history) < 8

    patient_engine = PromptEvolutionEngine(
        EvolutionConfig(
            population_size=4, elite_count=2, max_generations=3, min_improvement=0.0, random_seed=7
        )
    )
    patient_population = bootstrap_population(
        "Restate the user's underlying goal before acting.", 4, random_seed=7
    )
    _patient_final, patient_history = patient_engine.run_evolution(
        patient_population, _length_evaluator
    )
    assert len(patient_history) == 3


def test_aggregate_scores_folds_scoremaps() -> None:
    first = {"task_success": 1.0, "metaphor_comprehension": 0.4, "safety_violation": 0.0}
    second = {"task_success": 0.5, "metaphor_comprehension": 0.6}
    folded = aggregate_scores([first, second])
    assert folded["task_success"] == pytest.approx(0.75)
    assert folded["metaphor_comprehension"] == pytest.approx(0.5)
    assert folded["safety_violation"] == pytest.approx(0.0)


async def _genome_session_factory(tmp_path: object, name: str):
    tmp_engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / name}")
    async with tmp_engine.begin() as connection:
        await connection.run_sync(
            lambda conn: Base.metadata.create_all(conn, tables=[PromptGenomeRow.__table__])
        )
    return tmp_engine, async_sessionmaker(tmp_engine, expire_on_commit=False)


async def test_population_save_load_round_trip(tmp_path) -> None:
    population = bootstrap_population(
        "Restate the user's underlying goal before acting.", 4, random_seed=42
    )
    engine = PromptEvolutionEngine(
        EvolutionConfig(population_size=4, elite_count=2, max_generations=2, random_seed=42)
    )
    final, _history = engine.run_evolution(population, _length_evaluator)
    latest_generation = max(genome.generation for genome in final)
    latest = [genome for genome in final if genome.generation == latest_generation]

    tmp_engine, factory = await _genome_session_factory(tmp_path, "roundtrip.db")
    written = await save_population("user-a", latest, session_factory=factory)
    assert written == len(latest)

    loaded = await load_population("user-a", session_factory=factory)
    assert {genome.id for genome in loaded} == {genome.id for genome in latest}
    saved_by_id = {genome.id: genome for genome in latest}
    for genome in loaded:
        saved = saved_by_id[genome.id]
        assert genome.prompt_text == saved.prompt_text
        assert genome.model_params == saved.model_params
        assert genome.scores == saved.scores
        assert genome.generation == saved.generation
        assert genome.parent_ids == saved.parent_ids
    await tmp_engine.dispose()


async def test_load_returns_latest_generation_and_best_genome(tmp_path) -> None:
    population = bootstrap_population(
        "Restate the user's underlying goal before acting.", 4, random_seed=1
    )
    engine = PromptEvolutionEngine(
        EvolutionConfig(population_size=4, elite_count=2, max_generations=2, random_seed=1)
    )
    final, _history = engine.run_evolution(population, _length_evaluator)

    tmp_engine, factory = await _genome_session_factory(tmp_path, "latest.db")
    await save_population("user-b", final, session_factory=factory)

    loaded = await load_population("user-b", session_factory=factory)
    latest_generation = max(genome.generation for genome in final)
    assert {genome.id for genome in loaded} == {
        genome.id for genome in final if genome.generation == latest_generation
    }

    async with factory() as db:
        best = await get_best_genome(db, "user-b")
    assert best is not None
    composites = {genome.id: engine.composite(genome) for genome in final}
    assert composites[best.id] == max(composites.values())
    await tmp_engine.dispose()


# --- Dual-loop linkage ----------------------------------------------------------


async def test_profile_context_gated_by_confidence() -> None:
    user = _user_id()
    await _enable_learning(user)
    coordinator = DualLoopCoordinator()
    assert await coordinator.profile_context(user, "fix the login bug") == ""

    for _ in range(6):
        await coordinator.record_run_outcome(
            user, "fix the login bug", outcome="success", tool="terminal"
        )

    context = await coordinator.profile_context(user, "fix another bug")
    assert context
    assert "User behavior profile" in context
    assert "confidence" in context
    assert "task_preferences" in context


async def test_evolution_tick_threshold_and_repeat_safety() -> None:
    user = _user_id()
    coordinator = DualLoopCoordinator()
    for _ in range(EVOLUTION_TICK_INTERVAL - 1):
        await coordinator.evolution_tick(user)
    assert coordinator._run_counters[user] == EVOLUTION_TICK_INTERVAL - 1

    await coordinator.evolution_tick(user)
    assert coordinator._run_counters[user] == 0

    for _ in range(EVOLUTION_TICK_INTERVAL * 2):
        await coordinator.evolution_tick(user)


async def test_record_runs_then_evolution_tick_is_repeatable() -> None:
    user = _user_id()
    await _enable_learning(user)
    coordinator = DualLoopCoordinator()
    for index in range(EVOLUTION_TICK_INTERVAL):
        outcome = "success" if index % 2 else "failure"
        await coordinator.record_run_outcome(user, f"fix bug number {index}", outcome=outcome)
        await coordinator.evolution_tick(user)
        await coordinator.evolution_tick(user)
    assert coordinator._run_counters[user] == 0

    store = ProfileStore()
    summary = await store.summary(user)
    assert summary.success_rate == pytest.approx(0.5)


async def test_record_run_outcome_maps_invalid_outcome_and_empty_instruction() -> None:
    user = _user_id()
    await _enable_learning(user)
    coordinator = DualLoopCoordinator()
    await coordinator.record_run_outcome(user, "do things", outcome="nonsense")
    await coordinator.record_run_outcome(user, "   ", outcome="success")

    store = ProfileStore()
    summary = await store.summary(user)
    assert summary.success_rate == 0.0
    async with async_session() as db:
        assert len(await list_events(db, user)) == 1


async def test_evolution_tick_calls_module_entry_when_available(monkeypatch) -> None:
    import app.core.prompts.evolution as evolution_module

    calls: list[str] = []

    async def entry(user_id: str) -> None:
        calls.append(user_id)

    monkeypatch.setattr(evolution_module, "run_evolution_tick", entry, raising=False)
    coordinator = DualLoopCoordinator()
    for _ in range(EVOLUTION_TICK_INTERVAL):
        await coordinator.evolution_tick("user-tick")
    assert calls == ["user-tick"]


# --- Agent-engine hook wiring ---------------------------------------------------


class _RecordingCoordinator:
    """Test double that records dual-loop calls without touching storage."""

    def __init__(self) -> None:
        self.context_calls: list[tuple[str, str]] = []
        self.outcome_calls: list[dict[str, object]] = []
        self.tick_calls: list[str] = []
        self.next_context = ""

    async def profile_context(self, user_id: str, instruction: str) -> str:
        self.context_calls.append((user_id, instruction))
        return self.next_context

    async def record_run_outcome(self, user_id: str, instruction: str, **kwargs: object) -> None:
        self.outcome_calls.append({"user_id": user_id, "instruction": instruction, **kwargs})

    async def evolution_tick(self, user_id: str) -> None:
        self.tick_calls.append(user_id)


def _hook_session(state: TaskState = TaskState.COMPLETED) -> SimpleNamespace:
    return SimpleNamespace(
        user_id="hook-user",
        messages=[{"role": "user", "content": "fix the login bug"}],
        state_machine=SimpleNamespace(state=state),
        metrics=SimpleNamespace(retry_count=2),
        _stop_requested=False,
        context={},
    )


def _hook_engine() -> AgentEngine:
    return AgentEngine(
        model_registry=object(),
        tool_registry=object(),
        checkpoint_store=InMemoryCheckpointStore(),
        run_store=RunStorage(),
    )


async def _drain(engine: AgentEngine) -> None:
    if engine._background_tasks:
        await asyncio.gather(*engine._background_tasks)


async def test_engine_inject_profile_context_inserts_and_replaces_marker() -> None:
    engine = _hook_engine()
    fake = _RecordingCoordinator()
    engine._dual_loop = fake
    fake.next_context = "User behavior profile (advisory only)"

    session = _hook_session()
    session.session_id = "session-archive"
    await engine._inject_profile_context(session, "fix the login bug")
    assert fake.context_calls == [("hook-user", "fix the login bug")]
    assert session.messages[0]["content"].startswith("<!-- PROFILE_CONTEXT -->")
    assert session.messages[-1]["role"] == "user"

    await engine._inject_profile_context(session, "fix another bug")
    assert fake.context_calls[-1] == ("hook-user", "fix another bug")
    assert len(session.messages) == 2
    assert "User behavior profile" in session.messages[0]["content"]


async def test_engine_record_profile_outcome_maps_session_state() -> None:
    engine = _hook_engine()
    fake = _RecordingCoordinator()
    engine._dual_loop = fake

    engine._record_profile_outcome(_hook_session(TaskState.COMPLETED), "fix the login bug")
    await _drain(engine)
    assert len(fake.outcome_calls) == 1
    call = fake.outcome_calls[0]
    assert call["user_id"] == "hook-user"
    assert call["instruction"] == "fix the login bug"
    assert call["outcome"] == "success"
    assert call["retried"] is True

    engine._record_profile_outcome(_hook_session(TaskState.FAILED), "fix again")
    await _drain(engine)
    assert fake.outcome_calls[1]["outcome"] == "failure"


async def test_engine_tick_evolution_forwards_user() -> None:
    engine = _hook_engine()
    fake = _RecordingCoordinator()
    engine._dual_loop = fake

    engine._tick_evolution(_hook_session())
    await _drain(engine)
    assert fake.tick_calls == ["hook-user"]


async def test_engine_archives_instruction_with_plain_language_parse(monkeypatch) -> None:
    engine = _hook_engine()
    session = _hook_session()
    session.session_id = "session-archive"
    session.current_turn_id = "turn-archive"
    captured = {}

    class FakeDB:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def commit(self):
            return None

    class FakeTrace:
        id = "trace-archive"

    async def fake_create(db, payload, **kwargs):
        captured.update(payload)
        return FakeTrace(), False

    monkeypatch.setattr("app.storage.async_session", lambda: FakeDB())
    monkeypatch.setattr("app.storage.repository_instruction_traces.create_trace", fake_create)
    await engine._archive_instruction(session, "实现搜索，必须保留原文")
    assert captured["raw_text"] == "实现搜索，必须保留原文"
    assert captured["session_id"] == session.session_id
    assert captured["turn_id"] == "turn-archive"
    assert captured["task_spec"]["main_goal"] == "实现搜索，必须保留原文"
    assert session._instruction_trace_id == "trace-archive"


# --- Degradation paths ----------------------------------------------------------


class _UnavailableStore:
    """Simulates a profile backend whose construction itself fails."""

    def __init__(self) -> None:
        raise RuntimeError("profile backend unavailable")


class _ExplodingStore:
    """Constructs fine but fails on every storage operation."""

    async def summary(self, _user_id: str) -> ProfileSummary:
        raise RuntimeError("read failed")

    async def record_event(self, *_args: object, **_kwargs: object) -> object:
        raise RuntimeError("write failed")

    async def suggestions(self, _user_id: str, _instruction: str) -> dict[str, object]:
        raise RuntimeError("read failed")


class _DisabledStore:
    """Constructs and works, but the profile loop is switched off."""

    async def summary(self, _user_id: str) -> ProfileSummary:
        return ProfileSummary({}, {}, {}, 0.0, 0.0, 0.0, 0.0, (), False)

    async def record_event(self, *_args: object, **_kwargs: object) -> object:
        return object()

    async def suggestions(self, _user_id: str, _instruction: str) -> dict[str, object]:
        return {}


async def test_coordinator_degrades_when_store_construction_fails(monkeypatch) -> None:
    monkeypatch.setattr("app.core.profile.persistence.ProfileStore", _UnavailableStore)
    coordinator = DualLoopCoordinator()
    assert await coordinator.profile_context("user-x", "fix the bug") == ""
    await coordinator.record_run_outcome("user-x", "fix the bug", outcome="success")
    await coordinator.evolution_tick("user-x")


async def test_coordinator_swallows_store_runtime_failures(monkeypatch) -> None:
    monkeypatch.setattr("app.core.profile.persistence.ProfileStore", _ExplodingStore)
    coordinator = DualLoopCoordinator()
    assert await coordinator.profile_context("user-x", "fix the bug") == ""
    await coordinator.record_run_outcome("user-x", "fix the bug", outcome="success")
    await coordinator.evolution_tick("user-x")


async def test_coordinator_omits_context_for_disabled_profile(monkeypatch) -> None:
    monkeypatch.setattr("app.core.profile.persistence.ProfileStore", _DisabledStore)
    coordinator = DualLoopCoordinator()
    assert await coordinator.profile_context("user-x", "fix the bug") == ""
