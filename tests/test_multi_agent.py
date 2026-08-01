# tests/test_multi_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.engine.multi_agent import MultiAgentOrchestrator, SubTask


class AsyncIterator:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._items:
            return self._items.pop(0)
        raise StopAsyncIteration


@pytest.fixture
def engine():
    mock = MagicMock()
    mock.create_session = AsyncMock(return_value=MagicMock(session_id="child-1"))

    async def _run(session, task):
        yield MagicMock(type="TEXT", data={"content": "done"})

    mock.run = _run
    return mock

@pytest.fixture
def orchestrator(engine):
    return MultiAgentOrchestrator(engine)

@pytest.mark.asyncio
async def test_fork_single_subagent(orchestrator):
    result = await orchestrator.fork(task="Write a function", context={"lang": "python"})
    assert result.success
    assert result.output is not None

@pytest.mark.asyncio
async def test_coordinate_parallel_tasks(orchestrator):
    tasks = [SubTask("t1", "Task one"), SubTask("t2", "Task two")]
    results = await orchestrator.coordinate(tasks, max_concurrency=2)
    assert len(results) == 2

@pytest.mark.asyncio
async def test_team_collaboration(orchestrator):
    result = await orchestrator.team(
        task="Build a web scraper",
        roles=["planner", "coder", "reviewer"],
    )
    assert result is not None
