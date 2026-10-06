"""Coverage tests for app/multi_agent/flow.py (decorators + FlowExecutor + Flow)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.core.agent_engine as agent_engine_module
import app.core.di as di
import app.storage as storage_module
import app.workflow.engine as engine_module
import app.workflow.templates as templates_module
from app.multi_agent.flow import (
    Flow,
    FlowExecutor,
    FlowState,
    FlowStatus,
    listen,
    listen_or,
    listen_route,
    router,
    start,
)
from app.storage import Base
from app.storage.models_platform import Workflow as WorkflowModel
from app.workflow import Workflow

# ── decorators / state ────────────────────────────────────────────────────


def test_decorators_set_markers() -> None:
    @start()
    def entry(state):
        return "e"

    assert entry._flow_start is True  # type: ignore[attr-defined]

    @listen("other", entry)
    def listener(state):
        return "l"

    assert listener._flow_listens == ["other", "entry"]  # type: ignore[attr-defined]
    assert listener._flow_trigger == "all"  # type: ignore[attr-defined]

    @listen_or("a", "b")
    def or_listener(state):
        return "o"

    assert or_listener._flow_trigger == "any"  # type: ignore[attr-defined]

    @router(entry)
    def route(state):
        return "r"

    assert route._flow_returns_routes is True  # type: ignore[attr-defined]
    assert route._flow_router_for == ["entry"]  # type: ignore[attr-defined]

    @listen_route(route, "label")
    def routed(state):
        return "x"

    assert routed._flow_route_label == "label"  # type: ignore[attr-defined]
    assert routed._flow_trigger == "route"  # type: ignore[attr-defined]


def test_decorators_ignore_non_str_non_callable() -> None:
    @listen(123, "real")  # type: ignore[arg-type]
    def listener(state):
        return None

    assert listener._flow_listens == ["real"]  # type: ignore[attr-defined]

    @listen_or(object())
    def or_listener(state):
        return None

    assert or_listener._flow_listens == []  # type: ignore[attr-defined]

    @router(42, "label")  # type: ignore[arg-type]
    def route(state):
        return None

    assert route._flow_router_for == ["label"]  # type: ignore[attr-defined]


def test_flow_status_and_state() -> None:
    assert set(FlowStatus) == {
        FlowStatus.PENDING,
        FlowStatus.RUNNING,
        FlowStatus.COMPLETED,
        FlowStatus.FAILED,
    }
    state = FlowState()
    assert state.flow_id
    assert state.results == {}
    # extra="allow" -> arbitrary attributes are accepted
    state.custom_key = 123
    assert state.custom_key == 123


# ── FlowExecutor ──────────────────────────────────────────────────────────


class DemoFlow:
    label = "demo"  # non-callable public attribute (ignored by discovery)

    def plain_method(self, state: FlowState) -> str:
        return "plain"

    @start()
    async def begin(self, state: FlowState) -> str:
        return "begin-result"

    @listen(begin)
    def all_listener(self, state: FlowState) -> str:
        return "all-result"

    @listen_or(begin, all_listener)
    def any_listener(self, state: FlowState) -> str:
        return "any-result"

    @router(all_listener)
    async def decide(self, state: FlowState) -> str:
        return "yes"

    @listen_route(decide, "yes")
    async def route_yes(self, state: FlowState) -> str:
        return "route-result"


class FailingFlow:
    @start()
    async def explode(self, state: FlowState) -> str:
        raise RuntimeError("boom")


class ExceptionReturnFlow:
    @start()
    def returns_exception(self, state: FlowState) -> Exception:
        return ValueError("returned")


def _executor() -> FlowExecutor:
    return FlowExecutor(
        agent_engine=SimpleNamespace(),
        model_registry=SimpleNamespace(),
        tool_registry=SimpleNamespace(),
    )


async def test_executor_runs_full_flow() -> None:
    ex = _executor()
    state = await ex.execute(DemoFlow(), initial_state={"input_value": 42})
    assert state.input_value == 42
    assert state.results["begin"] == "begin-result"
    assert state.results["all_listener"] == "all-result"
    assert state.results["any_listener"] == "any-result"
    assert state.results["decide"] == "yes"
    assert state.results["route_yes"] == "route-result"
    assert state.errors == {}


async def test_executor_records_failures() -> None:
    ex = _executor()
    state = await ex.execute(FailingFlow())
    assert "explode" in state.errors
    assert "boom" in state.errors["explode"]
    assert "explode" not in state.results


async def test_executor_treats_exception_result_as_failure() -> None:
    ex = _executor()
    state = await ex.execute(ExceptionReturnFlow())
    assert "returns_exception" in state.errors


async def test_discover_methods_and_run_method() -> None:
    ex = _executor()
    inst = DemoFlow()
    methods = ex._discover_methods(inst)
    assert [n for n, _ in methods["start"]] == ["begin"]
    assert {n for n, _, _ in methods["listen"]} == {"all_listener", "any_listener"}
    assert [n for n, _ in methods["router"]] == ["decide"]
    assert [n for n, _, _ in methods["listen_route"]] == ["route_yes"]

    # _run_method handles async and sync callables
    assert await ex._run_method(inst.begin, FlowState(), inst) == "begin-result"
    assert await ex._run_method(inst.all_listener, FlowState(), inst) == "all-result"


async def test_find_triggered_methods_directly() -> None:
    ex = _executor()
    inst = DemoFlow()
    methods = ex._discover_methods(inst)

    triggered = ex._find_triggered_methods(methods, {"begin"}, set(), FlowState(), {})
    names = {n for n, _ in triggered}
    assert "all_listener" in names
    assert "any_listener" in names
    assert "decide" not in names

    triggered2 = ex._find_triggered_methods(
        methods, {"begin", "all_listener"}, set(), FlowState(), {}
    )
    names2 = {n for n, _ in triggered2}
    assert "decide" in names2

    # router route value drives listen_route
    state = FlowState()
    state.results["decide"] = "yes"
    triggered3 = ex._find_triggered_methods(
        methods, {"begin", "all_listener", "decide"}, set(), state, {}
    )
    assert "route_yes" in {n for n, _ in triggered3}

    # already-completed / running methods are not retriggered
    triggered4 = ex._find_triggered_methods(
        methods, {"begin", "all_listener"}, set(), FlowState(), {"decide": object()}
    )
    assert "decide" not in {n for n, _ in triggered4}
    triggered5 = ex._find_triggered_methods(
        methods, {"begin", "all_listener", "any_listener"}, set(), FlowState(), {}
    )
    assert "all_listener" not in {n for n, _ in triggered5}

    # nothing completed -> both "all" and "any" listeners stay dormant
    triggered6 = ex._find_triggered_methods(methods, set(), set(), FlowState(), {})
    assert {n for n, _ in triggered6} == set()

    # router completed but with a non-matching label -> route branch not taken
    state_bad = FlowState()
    state_bad.results["decide"] = "no"
    triggered7 = ex._find_triggered_methods(
        methods, {"begin", "all_listener", "decide"}, set(), state_bad, {}
    )
    assert "route_yes" not in {n for n, _ in triggered7}


# ── Flow named runner ─────────────────────────────────────────────────────


def test_match_template_variants() -> None:
    assert Flow("tool_use")._match_template({}) is not None
    assert Flow("TOOL USE")._match_template({}) is not None
    assert Flow("tool-use")._match_template({}) is not None
    assert Flow("Simple QA")._match_template({}) is not None
    assert Flow("simulation experiment")._match_template({}) is not None
    assert Flow("definitely-not-a-template")._match_template({}) is None


def test_match_template_type_error(monkeypatch) -> None:
    class FakeTemplates:
        @staticmethod
        def list_templates():
            return [{"id": "boom", "name": "Boom"}]

        @staticmethod
        def boom(**kwargs):
            raise TypeError("bad template call")

    monkeypatch.setattr(templates_module, "WorkflowTemplates", FakeTemplates)
    assert Flow("boom")._match_template({}) is None


async def test_resolve_workflow_template() -> None:
    wf = await Flow("tool_use")._resolve_workflow({})
    assert isinstance(wf, Workflow)


@pytest_asyncio.fixture
async def flow_db(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(storage_module, "async_session", maker)
    yield maker
    await engine.dispose()


async def test_resolve_workflow_from_db(flow_db) -> None:
    async with flow_db() as db:
        db.add(
            WorkflowModel(
                id="wf-db-1",
                name="db-flow",
                description="from db",
                nodes=[{"id": "n1", "type": "llm", "name": "N1"}],
                edges=[{"source": "n1", "target": "n1"}],
            )
        )
        await db.commit()

    wf = await Flow("db-flow")._resolve_workflow({})
    assert wf.id == "wf-db-1"
    assert wf.description == "from db"
    assert wf.nodes[0].id == "n1"


async def test_resolve_workflow_not_found(flow_db) -> None:
    with pytest.raises(ValueError, match="not found"):
        await Flow("missing-flow")._resolve_workflow({})


async def test_execute_unknown_workflow_returns_failed(flow_db) -> None:
    result = await Flow("missing-flow").execute({})
    assert result["status"] == FlowStatus.FAILED.value
    assert result["workflow"] == "missing-flow"
    assert "not found" in result["error"]


class _FakeResultObj:
    def model_dump(self) -> dict:
        return {"status": "completed", "workflow": "tool_use"}


class _FakeEngine:
    def __init__(self, engine=None, **kwargs) -> None:
        self.engine = engine

    async def execute(self, workflow, user_inputs=None, user_id="system"):
        return _FakeResultObj()


class _FailingEngine:
    def __init__(self, engine=None, **kwargs) -> None:
        pass

    async def execute(self, workflow, user_inputs=None, user_id="system"):
        raise RuntimeError("engine exploded")


async def test_flow_execute_success(monkeypatch) -> None:
    monkeypatch.setattr(engine_module, "WorkflowEngine", _FakeEngine)
    monkeypatch.setattr(di, "resolve", lambda name: SimpleNamespace(name=name))

    progress: list[tuple[int, int, str]] = []

    async def on_progress(cur: int, total: int, msg: str) -> None:
        progress.append((cur, total, msg))

    result = await Flow("tool_use").execute({"user_id": "u1"}, on_progress=on_progress)
    assert result == {"status": "completed", "workflow": "tool_use"}
    assert progress[0] == (0, 1, "Starting workflow 'tool_use'")
    assert progress[-1] == (1, 1, "Workflow complete")


async def test_flow_execute_engine_failure(monkeypatch) -> None:
    monkeypatch.setattr(engine_module, "WorkflowEngine", _FailingEngine)
    monkeypatch.setattr(di, "resolve", lambda name: SimpleNamespace(name=name))
    result = await Flow("tool_use").execute({})
    assert result["status"] == FlowStatus.FAILED.value
    assert "engine exploded" in result["error"]


async def test_flow_execute_di_keyerror_fallback(monkeypatch) -> None:
    class FakeAgentEngine:
        def __init__(self) -> None:
            self.kind = "fake"

    def raise_keyerror(name):
        raise KeyError(name)

    monkeypatch.setattr(engine_module, "WorkflowEngine", _FakeEngine)
    monkeypatch.setattr(di, "resolve", raise_keyerror)
    monkeypatch.setattr(agent_engine_module, "AgentEngine", FakeAgentEngine)

    result = await Flow("tool_use").execute({"user_id": "u2"})
    assert result["status"] == "completed"


async def test_executor_empty_flow_returns_immediately() -> None:
    class Empty:
        pass

    ex = _executor()
    state = await ex.execute(Empty())
    assert state.results == {}
    assert state.flow_id


async def test_executor_agent_loop_yields() -> None:
    # A flow whose start method awaits guarantees the polling loop yields.
    class SlowFlow:
        @start()
        async def go(self, state: FlowState) -> str:
            await asyncio.sleep(0)
            return "ok"

    state = await _executor().execute(SlowFlow())
    assert state.results["go"] == "ok"
