"""The crew executor registration in ``app/main.py``.

``_register_core_services`` wires an unconfigured ``CrewExecutorAdapter`` into
the unified executor. Crew agents and tasks are request-scoped, so startup must
not construct an executable empty crew.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.interfaces import ExecutionContext, ExecutionStatus


def _context() -> ExecutionContext:
    return ExecutionContext(session_id="s1", user_id="u1")


class _StubLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def _record(self, level: str, event: str, **fields: Any) -> None:
        self.records.append((level, event, fields))

    def warning(self, event: str, **fields: Any) -> None:
        self._record("warning", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._record("error", event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self._record("info", event, **fields)


async def test_empty_crew_adapter_refuses_instead_of_reporting_success() -> None:
    from app.core.executor import CrewExecutorAdapter

    adapter = CrewExecutorAdapter(None)

    assert adapter.is_configured is False
    result = await adapter.execute(_context())

    assert result.status == ExecutionStatus.FAILED
    assert result.output is None
    assert "unconfigured crew" in (result.error or "")
    assert result.metrics == {}


async def test_a_configured_crew_adapter_still_executes() -> None:
    from app.core.executor import CrewExecutorAdapter
    from app.multi_agent import AgentRole, AgentTask
    from app.multi_agent.crew import Crew

    class _Engine:
        def create_session(self, **kwargs: Any) -> str:
            return "s1"

        async def run(self, session: str, message: str):
            from app.core import AgentEvent, AgentEventType

            yield AgentEvent(type=AgentEventType.TEXT, data={"content": "done"})

    task = AgentTask(id="t1", agent_name="alpha", description="work", expected_output="result")
    agent = AgentRole(name="alpha", role="r", goal="g", backstory="b")
    adapter = CrewExecutorAdapter(Crew([agent], [task], engine=_Engine()))

    assert adapter.is_configured is True
    result = await adapter.execute(_context())

    assert result.status == ExecutionStatus.COMPLETED
    assert result.output == "done"
    assert result.metrics["crew_id"]


def test_startup_warns_that_the_registered_crew_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """The empty registration must be visible in the startup log."""
    import app.main as main_module
    from app.tools import ToolRegistry

    recorded: list[str] = []
    monkeypatch.setattr(main_module, "di_register", lambda *a, **k: recorded.append(str(a[0])))
    monkeypatch.setattr(ToolRegistry, "bootstrap_network_gate", classmethod(lambda cls: None))
    logger = _StubLogger()
    monkeypatch.setattr(main_module, "logger", logger)

    main_module._register_core_services()

    events = [event for _, event, _ in logger.records]
    assert "crew_executor_registered_unconfigured" in events
    assert "IExecutor" in " ".join(recorded)
