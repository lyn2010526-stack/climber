"""Fire-and-forget notification helpers for the agent engine.

Extracted from ``app.core.agent_engine``. All sends go through the engine's
``_spawn`` hook so background task tracking stays on the facade.
"""

from __future__ import annotations

from typing import Any


def send_start_notification(engine: Any, session: Any) -> None:
    """Send notification when agent starts.

    Args:
        engine: The AgentEngine instance providing the spawn hook.
        session: The agent session.
    """
    try:
        from app.services.notifications import notification_service

        engine._spawn(
            notification_service.agent_message(session.agent_id or "Agent", "开始执行任务...")
        )
    except Exception:
        pass


def send_completion_notification(engine: Any, session: Any, result: Any) -> None:
    """Send notification when agent completes.

    Args:
        engine: The AgentEngine instance providing the spawn hook.
        session: The agent session.
        result: The final ChatResult.
    """
    try:
        from app.services.notifications import notification_service

        engine._spawn(
            notification_service.task_complete(
                f"Agent {session.agent_id}",
                result.content[:100] if result and result.content else None,
            )
        )
    except Exception:
        pass


def send_failure_notification(engine: Any, session: Any, error: str) -> None:
    """Send notification when agent fails.

    Args:
        engine: The AgentEngine instance providing the spawn hook.
        session: The agent session.
        error: The error message.
    """
    try:
        from app.services.notifications import notification_service

        engine._spawn(notification_service.task_failed(f"Agent {session.agent_id}", error))
    except Exception:
        pass
