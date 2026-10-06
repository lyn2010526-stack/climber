"""Dual closed-loop hooks: user profile loop, prompt evolution, metacognition.

Extracted from ``app.core.agent_engine``. The coordinator and orchestrator
stay advisory: every hook degrades silently when the subsystem is
unavailable so a failure never blocks a normal agent run.
"""

from __future__ import annotations

from contextlib import aclosing
from contextvars import ContextVar
from typing import Any

_meta_session: ContextVar[tuple[Any, Any] | None] = ContextVar("meta_session", default=None)


def install_metacognition_scope(engine: Any) -> None:
    """Bind the existing iteration facade to a task-local owning session."""
    if getattr(engine, "metacognition_scope_installed", False):
        return
    iteration_loop = engine._iteration_loop  # noqa: SLF001 - engine facade composition point

    async def scoped(session: Any, executor: Any, compressor: Any):
        token = _meta_session.set((engine, session))
        try:
            async with aclosing(iteration_loop(session, executor, compressor)) as events:
                async for event in events:
                    yield event
        finally:
            _meta_session.reset(token)

    engine._iteration_loop = scoped  # noqa: SLF001 - preserve the existing facade signature
    engine.metacognition_scope_installed = True


def dual_loop_coordinator(engine: Any) -> Any:
    """Lazily build the dual-loop coordinator; None when unavailable.

    Args:
        engine: The AgentEngine instance caching the coordinator.

    Returns:
        The DualLoopCoordinator instance, or None if the module cannot be
        imported or constructed.
    """
    coordinator = getattr(engine, "_dual_loop", None)
    if coordinator is None:
        try:
            from app.core.engine.dual_loop import DualLoopCoordinator
            coordinator = DualLoopCoordinator()
            engine._dual_loop = coordinator
        except Exception:
            return None
    return coordinator


def metacognition_orchestrator(engine: Any) -> Any:
    """Lazily build the metacognition orchestrator; None when unavailable.

    Args:
        engine: The AgentEngine instance caching the orchestrator.

    Returns:
        MetacognitionOrchestrator instance, or None when the subsystem
        cannot be imported.
    """
    binding = _meta_session.get()
    if binding is not None and binding[0] is engine:
        session = binding[1]
        if getattr(session, "metacognition_disabled", False):
            return None
        configured = getattr(engine, "_metacognition", None)
        if configured is False or (configured is not None and not configured.enabled):
            return None
        if getattr(session, "metacognition_orchestrator", None) is None:
            from app.core.metacognition.production import build_session_orchestrator

            session.metacognition_orchestrator = build_session_orchestrator(engine, session)
        return session.metacognition_orchestrator
    if getattr(engine, "_metacognition", None) is None:
        try:
            from app.core.metacognition import MetacognitionOrchestrator

            engine._metacognition = MetacognitionOrchestrator()
        except Exception:
            engine._metacognition = False
    return engine._metacognition or None


def metacognition_enabled(engine: Any) -> bool:
    """Whether the main loop should run the metacognition stage.

    Args:
        engine: The AgentEngine instance.

    Returns:
        True when an enabled orchestrator is available.
    """
    orchestrator = engine.metacognition
    return bool(orchestrator and getattr(orchestrator, "enabled", True))


async def inject_profile_context(engine: Any, session: Any, message: str) -> None:
    """Inject the user-profile context into session context (dual loop 1).

    Args:
        engine: The AgentEngine instance.
        session: The agent session.
        message: The user query the profile is adapted to.
    """
    try:
        from app.core import MessageRole

        profile_marker = "<!-- PROFILE_CONTEXT -->"
        # Clear stale injections before any read that can fail or observe revoked consent.
        session.messages[:] = [
            msg for msg in session.messages
            if not (
                msg.get("role") == MessageRole.SYSTEM
                and isinstance(msg.get("content"), str)
                and msg["content"].startswith(profile_marker)
            )
        ]
        coordinator = dual_loop_coordinator(engine)
        if coordinator is None:
            return
        user_id = getattr(session, "user_id", None) or "local"
        profile_context = await coordinator.profile_context(user_id, message)
        if profile_context:
            session.messages.insert(-1, {"role": MessageRole.SYSTEM, "content": profile_marker + "\n" + profile_context})
    except Exception:
        pass


def record_profile_outcome(engine: Any, session: Any, message: str) -> None:
    """Feed the finished run back into the user profile (fire-and-forget).

    Args:
        engine: The AgentEngine instance.
        session: The agent session.
        message: The user instruction of this run.
    """
    try:
        coordinator = dual_loop_coordinator(engine)
        if coordinator is None:
            return
        from app.core.task_state_machine import TaskState
        outcome = "success" if session.state_machine.state == TaskState.COMPLETED else "failure"
        metrics = getattr(session, "metrics", None)
        user_id = getattr(session, "user_id", None) or "local"
        engine._spawn(
            coordinator.record_run_outcome(
                user_id,
                message,
                outcome=outcome,
                interrupted=bool(getattr(session, "_stop_requested", False)),
                retried=bool(int(getattr(metrics, "retry_count", 0) or 0) > 0),
                reasoning_level=current_reasoning_level(session),
                tool=last_tool_name(session),
            )
        )
    except Exception:
        pass


def tick_evolution(engine: Any, session: Any) -> None:
    """Advance the genetic evolution tick counter (fire-and-forget).

    Args:
        engine: The AgentEngine instance.
        session: The agent session.
    """
    try:
        coordinator = dual_loop_coordinator(engine)
        if coordinator is None:
            return
        user_id = getattr(session, "user_id", None) or "local"
        engine._spawn(coordinator.evolution_tick(user_id))
    except Exception:
        pass


def current_reasoning_level(session: Any) -> str:
    """Read this run's reasoning level, falling back to "standard".

    Args:
        session: The agent session carrying optional context data.

    Returns:
        The configured reasoning level string.
    """
    context = getattr(session, "context", None)
    if isinstance(context, dict):
        context_data = context.get("context_data")
        if isinstance(context_data, dict):
            level = context_data.get("reasoning_level")
            if isinstance(level, str) and level:
                return level
        level = context.get("reasoning_level")
        if isinstance(level, str) and level:
            return level
    return "standard"


def last_tool_name(session: Any) -> str | None:
    """Name of the last tool executed in this run, or None.

    Args:
        session: The agent session.

    Returns:
        The last tool name found in the message history.
    """
    for msg in reversed(getattr(session, "messages", []) or []):
        if not isinstance(msg, dict):
            continue
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            continue
        first = tool_calls[0] if isinstance(tool_calls[0], dict) else {}
        name = (first.get("function") or {}).get("name")
        if name:
            return str(name)
    return None
