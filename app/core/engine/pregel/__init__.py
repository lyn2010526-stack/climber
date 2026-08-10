"""Pregel-style execution engine with checkpoint persistence and HITL support.

Inspired by LangGraph's architecture: super-step execution, channel-based
state aggregation, checkpoint persistence, and human-in-the-loop interrupts.

Usage:
    from app.core.engine.pregel import StateGraph, Command

    class MyState(TypedDict):
        messages: Annotated[list, add]
        next_node: str | None

    def chatbot(state: MyState) -> dict:
        return {"messages": [response], "next_node": "tools"}

    def tools_node(state: MyState) -> Command:
        return Command(goto="chatbot", update={"messages": [tool_result]})

    graph = StateGraph(MyState)
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", tools_node)
    graph.add_edge("chatbot", "tools")
    graph.set_entry_point("chatbot")
    app = graph.compile()
    result = await app.invoke({"messages": [user_input]})
"""

from app.core.engine.pregel.checkpoint import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointConfig,
    InMemoryCheckpointSaver,
    SqliteCheckpointSaver,
)
from app.core.engine.pregel.command import Command
from app.core.engine.pregel.engine import ExecutionResult, PregelEngine, SuperStepResult
from app.core.engine.pregel.graph import CompiledGraph, StateGraph
from app.core.engine.pregel.hitl import HITLManager, Interrupt
from app.core.engine.pregel.policies import DefaultErrorHandler, RetryPolicy, TimeoutPolicy
from app.core.engine.pregel.state import GraphState, StateReducer, merge_states
from app.core.engine.pregel.streaming import (
    StreamEvent,
    StreamEventType,
    StreamManager,
    stream_events,
)

__all__ = [
    "BaseCheckpointSaver",
    # Checkpoint
    "Checkpoint",
    "CheckpointConfig",
    # Command
    "Command",
    "CompiledGraph",
    "DefaultErrorHandler",
    "ExecutionResult",
    # State
    "GraphState",
    # HITL
    "HITLManager",
    "InMemoryCheckpointSaver",
    "Interrupt",
    # Engine
    "PregelEngine",
    # Policies
    "RetryPolicy",
    "SqliteCheckpointSaver",
    # Graph
    "StateGraph",
    "StateReducer",
    # Streaming
    "StreamEvent",
    "StreamEventType",
    "StreamManager",
    "SuperStepResult",
    "TimeoutPolicy",
    "merge_states",
    "stream_events",
]
