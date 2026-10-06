"""Coverage tests for app.core.engine.react_loop.ReActLoopExecutor."""

from __future__ import annotations

from typing import Any

from app.core import AgentEventType, ChatResult, ContextConfig
from app.core.engine.react_loop import ReActLoopExecutor
from app.core.session import AgentSession
from app.core.task_state_machine import TaskState


class _Caps:
    def __init__(self, streaming: bool = False, max_tokens: int | None = None) -> None:
        self.streaming = streaming
        self.max_tokens = max_tokens


class FakeAdapter:
    """Deterministic adapter: pops responses in order."""

    def __init__(
        self,
        responses: list[Any],
        *,
        streaming: bool = False,
        max_tokens: int | None = None,
    ) -> None:
        self.responses = list(responses)
        self.capabilities = _Caps(streaming=streaming, max_tokens=max_tokens)
        self.chat_calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    async def chat(self, messages: Any, tools: Any = None, **kwargs: Any) -> ChatResult:
        self.chat_calls.append({"messages": messages, "tools": tools, "kwargs": kwargs})
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def stream_chat(self, messages: Any, tools: Any = None, **kwargs: Any) -> Any:
        self.stream_calls.append({"messages": messages, "tools": tools, "kwargs": kwargs})
        item = self.responses.pop(0)

        async def gen() -> Any:
            if isinstance(item, BaseException):
                raise item
            for chunk in item:
                yield chunk

        return gen()


class FakeModelRegistry:
    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter
        self.calls: list[dict[str, Any]] = []

    def get_or_create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.adapter


class FakeToolRegistry:
    def __init__(self, result: str = "tool-result") -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        self.calls.append((name, arguments))
        return self.result


class FakeCheckpoints:
    def __init__(self, raise_on_save: bool = False, set_stop_on_save: bool = False) -> None:
        self.saved: list[Any] = []
        self.raise_on_save = raise_on_save
        self.set_stop_on_save = set_stop_on_save
        self.session: AgentSession | None = None

    async def save(self, _parent: Any, cp: Any, checkpoint_id: str | None = None) -> None:
        self.saved.append((cp, checkpoint_id))
        if self.set_stop_on_save and self.session is not None:
            self.session._stop_requested = True
        if self.raise_on_save:
            raise RuntimeError("checkpoint down")


class FakePrioritizer:
    def __init__(self) -> None:
        self.outcomes: list[tuple[str, bool, float]] = []

    def record_outcome(self, name: str, success: bool, duration_ms: float) -> None:
        self.outcomes.append((name, success, duration_ms))


def _build(
    adapter: FakeAdapter,
    *,
    tool_registry: FakeToolRegistry | None = None,
    checkpoints: FakeCheckpoints | None = None,
) -> tuple[ReActLoopExecutor, FakeToolRegistry, FakeCheckpoints, FakePrioritizer]:
    tool_registry = tool_registry or FakeToolRegistry()
    checkpoints = checkpoints or FakeCheckpoints()
    prioritizer = FakePrioritizer()
    executor = ReActLoopExecutor(
        model_registry=FakeModelRegistry(adapter),  # type: ignore[arg-type]
        tool_registry=tool_registry,  # type: ignore[arg-type]
        checkpoint_store=checkpoints,  # type: ignore[arg-type]
        tool_prioritizer=prioritizer,  # type: ignore[arg-type]
        build_tools_fn=lambda tools, task_description=None: [{"name": "dummy"}],
    )
    return executor, tool_registry, checkpoints, prioritizer


async def _session(max_iterations: int = 5, **kwargs: Any) -> AgentSession:
    session = AgentSession(
        provider="p", model_id="m", api_key="k", max_iterations=max_iterations, **kwargs
    )
    await session.state_machine.transition(TaskState.PROCESSING, trigger="start")
    return session


async def _collect(
    executor: ReActLoopExecutor, session: AgentSession, message: str = "hi", **kw: Any
) -> list[Any]:
    return [event async for event in executor.execute(session, message, **kw)]


async def test_simple_completion_non_streaming() -> None:
    adapter = FakeAdapter([ChatResult(content="hello", tool_calls=[], tokens_used=5)])
    executor, _tools, checkpoints, _prio = _build(adapter)
    session = await _session()

    events = await _collect(executor, session)

    types = [e.type for e in events]
    assert types[0] is AgentEventType.THINKING
    assert AgentEventType.TEXT in types
    assert AgentEventType.CHECKPOINT in types
    assert types[-1] is AgentEventType.DONE
    assert events[-1].data["content"] == "hello"
    assert events[-1].data["tokens_used"] == 5
    assert events[-1].data["status"] == "completed"
    assert session.state_machine.state is TaskState.COMPLETED
    assert session.messages[-1] == {"role": "assistant", "content": "hello"}
    assert len(checkpoints.saved) == 1
    assert checkpoints.saved[0][1] == f"{session.session_id}-1"


async def test_resume_interrupted_continues_iteration() -> None:
    adapter = FakeAdapter([ChatResult(content="done", tokens_used=1)])
    executor, _t, _c, _p = _build(adapter)
    session = await _session(max_iterations=5)
    session._resume_interrupted = True
    session._last_iteration = 2

    events = await _collect(executor, session)

    assert session._resume_interrupted is False
    assert events[-1].type is AgentEventType.DONE
    assert events[-1].data["iterations"] == 3


async def test_llm_error_transitions_failed_and_calls_on_error() -> None:
    adapter = FakeAdapter([RuntimeError("boom")])
    executor, _t, _c, _p = _build(adapter)
    session = await _session()
    errors: list[str] = []

    events = await _collect(executor, session, on_error=errors.append)

    assert any(e.type is AgentEventType.ERROR for e in events)
    assert events[-1].type is AgentEventType.ERROR
    assert events[-1].data["error"] == "boom"
    assert errors == ["boom"]
    assert session.state_machine.state is TaskState.FAILED


async def test_llm_error_with_stop_requested_cancels() -> None:
    session_holder: dict[str, Any] = {}

    class _StopAdapter(FakeAdapter):
        async def chat(self, messages: Any, tools: Any = None, **kwargs: Any) -> ChatResult:
            session_holder["session"]._stop_requested = True
            raise RuntimeError("interrupted")

    adapter = _StopAdapter([])
    executor, _t, _c, _p = _build(adapter)
    session = await _session()
    session_holder["session"] = session

    events = await _collect(executor, session)

    assert any(e.type is AgentEventType.ERROR for e in events)
    assert session.state_machine.state is TaskState.CANCELLED


async def test_xml_tool_calls_extracted_and_executed() -> None:
    adapter = FakeAdapter(
        [
            ChatResult(content="<function=a>body</a>"),
            ChatResult(content="finished"),
        ]
    )
    executor, tools, checkpoints, prio = _build(adapter)
    session = await _session()

    events = await _collect(executor, session)

    types = [e.type for e in events]
    assert AgentEventType.TOOL_CALL in types
    assert AgentEventType.TOOL_RESULT in types
    assert len(tools.calls) == 1
    assert tools.calls[0] == ("a", {"text": "body"})
    assert prio.outcomes and prio.outcomes[0][0] == "a"
    assert len(checkpoints.saved) == 2
    assert events[-1].type is AgentEventType.DONE


async def test_tool_calls_then_finish() -> None:
    tool_call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "search", "arguments": '{"q": "x"}'},
    }
    adapter = FakeAdapter(
        [
            ChatResult(content="", tool_calls=[tool_call]),
            ChatResult(content="answer"),
        ]
    )
    executor, tools, _c, _p = _build(adapter)
    session = await _session()

    events = await _collect(executor, session)

    assert tools.calls == [("search", {"q": "x"})]
    tool_result_events = [e for e in events if e.type is AgentEventType.TOOL_RESULT]
    assert tool_result_events[0].data["result"] == "tool-result"
    assert {"role": "tool", "content": "tool-result", "tool_name": "search"} in session.messages
    assert events[-1].data["content"] == "answer"


async def test_max_iterations_with_tool_calls_fails() -> None:
    tool_call = {"id": "c", "type": "function", "function": {"name": "t", "arguments": "{}"}}
    adapter = FakeAdapter([ChatResult(content="", tool_calls=[tool_call])])
    executor, _t, _c, _p = _build(adapter)
    session = await _session(max_iterations=1)

    events = await _collect(executor, session)

    assert events[-1].type is AgentEventType.DONE
    assert events[-1].data["status"] == "max_iterations_reached"
    assert events[-1].data["iterations"] == 1
    assert session.state_machine.state is TaskState.FAILED


async def test_stop_requested_before_loop_cancels() -> None:
    adapter = FakeAdapter([])
    executor, _t, _c, _p = _build(adapter)
    session = await _session()
    session._stop_requested = True

    events = await _collect(executor, session)

    assert events[-1].type is AgentEventType.DONE
    assert events[-1].data["status"] == "stopped"
    assert events[-1].data["content"] == ""
    assert events[-1].data["tokens_used"] == 0
    assert session.state_machine.state is TaskState.CANCELLED


async def test_compression_via_context_config() -> None:
    adapter = FakeAdapter([ChatResult(content="ok")])
    executor, _t, _c, _p = _build(adapter)
    session = await _session()
    session.context_config = ContextConfig(max_tokens=1)
    session.messages = [{"role": "user", "content": "x" * 400}]

    events = await _collect(executor, session)

    assert any(e.type is AgentEventType.CONTEXT_COMPRESSION for e in events)


async def test_compression_via_adapter_max_tokens() -> None:
    adapter = FakeAdapter([ChatResult(content="ok")], max_tokens=1)
    executor, _t, _c, _p = _build(adapter)
    session = await _session()
    session.messages = [{"role": "user", "content": "x" * 400}]

    events = await _collect(executor, session)

    compression = [e for e in events if e.type is AgentEventType.CONTEXT_COMPRESSION]
    assert compression
    assert compression[0].data["limit"] == 1


async def test_streaming_assembles_content_and_tool_calls() -> None:
    chunk1 = ChatResult(
        content="Hel",
        tool_calls=[
            {"index": 0, "id": "call_1", "function": {"name": "search", "arguments": {"q": "x"}}},
            {"index": 1, "id": "call_2", "function": {"name": "other", "arguments": "{}"}},
        ],
    )
    chunk2 = ChatResult(
        content="lo",
        tool_calls=[
            {"index": 2, "function": {"name": "third", "arguments": 42}},
            {"index": 3, "function": {"arguments": "raw"}},
        ],
    )
    # Empty-content chunk that still carries a tool call without arguments:
    # exercises the falsy "chunk.content" and missing "arguments" branches.
    chunk3 = ChatResult(
        content="",
        tool_calls=[{"index": 4, "function": {"name": "noargs"}}],
    )
    adapter = FakeAdapter(
        [
            [chunk1, chunk2, chunk3],
            [ChatResult(content="done", tool_calls=[])],
        ],
        streaming=True,
    )
    executor, tools, _c, _p = _build(adapter)
    session = await _session()

    events = await _collect(executor, session)

    assert [e.data["content"] for e in events if e.type is AgentEventType.TEXT] == [
        "Hel",
        "lo",
        "done",
    ]
    assert tools.calls == [
        ("search", {"q": "x"}),
        ("other", {}),
        ("third", 42),
        ("", {}),
        ("noargs", {}),
    ]
    # Streamed content is not re-emitted as TEXT, but is appended once.
    assistant_texts = [m["content"] for m in session.messages if m.get("role") == "assistant"]
    assert assistant_texts == ["Hello", "", "done"]
    assert events[-1].data["content"] == "done"


async def test_streaming_tool_call_without_index_defaults_to_zero() -> None:
    chunk = ChatResult(
        content="hi",
        tool_calls=[{"id": "c1", "function": {"name": "solo", "arguments": "{}"}}],
    )
    adapter = FakeAdapter([[chunk], [ChatResult(content="bye")]], streaming=True)
    executor, tools, _c, _p = _build(adapter)
    session = await _session()

    await _collect(executor, session)

    assert tools.calls == [("solo", {})]


async def test_streaming_error_path() -> None:
    adapter = FakeAdapter([RuntimeError("stream broke")], streaming=True)
    executor, _t, _c, _p = _build(adapter)
    session = await _session()

    events = await _collect(executor, session)

    assert any(e.type is AgentEventType.ERROR for e in events)
    assert session.state_machine.state is TaskState.FAILED


async def test_outer_exception_from_checkpoint_save_failed() -> None:
    adapter = FakeAdapter([ChatResult(content="ok")])
    checkpoints = FakeCheckpoints(raise_on_save=True)
    executor, _t, _c, _p = _build(adapter, checkpoints=checkpoints)
    session = await _session()
    errors: list[str] = []

    events = await _collect(executor, session, on_error=errors.append)

    assert events[-1].type is AgentEventType.ERROR
    assert events[-1].data["error"] == "checkpoint down"
    assert errors == ["checkpoint down"]
    assert session.state_machine.state is TaskState.FAILED


async def test_outer_exception_with_stop_requested_cancels() -> None:
    adapter = FakeAdapter([ChatResult(content="ok")])
    checkpoints = FakeCheckpoints(raise_on_save=True, set_stop_on_save=True)
    executor, _t, _c, _p = _build(adapter, checkpoints=checkpoints)
    session = await _session()
    checkpoints.session = session

    events = await _collect(executor, session)

    assert events[-1].type is AgentEventType.ERROR
    assert session.state_machine.state is TaskState.CANCELLED
