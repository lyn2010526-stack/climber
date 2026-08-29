"""External state tooling — context is a workbench, not a warehouse.

The agent does not hold large amounts of information directly; it queries
external state through tools. Only the currently-required result is kept in
context and discarded after use.

Tools:
- search_memory(query, limit=5): full-text + semantic search over history
- read_skill(skill_id): read full skill content (level 2)
- get_task_history(task_id): full operation history for a task
- query_log(event_type, time_range): query the event log
- get_app_state(package_name): current state for an app (simulated)
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.four_layer_memory.fts5_index import get_fts5_index
from app.core.skill_store.skill_store import get_skill_store

logger = structlog.get_logger()


class ExternalStateTools:
    """Implementation of the external-state query tools."""

    def __init__(self, memory_index: Any = None, skill_store: Any = None) -> None:
        self._memory_index = memory_index or get_fts5_index()
        self._skill_store = skill_store or get_skill_store()

    async def search_memory(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        try:
            return self._memory_index.search(query, limit=limit)
        except Exception as exc:
            logger.warning("external_state.search_memory_failed", error=str(exc))
            return []

    async def read_skill(self, skill_id: str) -> str:
        skill = self._skill_store.get(skill_id)
        if skill is None:
            return ""
        return skill.load_instruction()

    async def get_task_history(self, task_id: str, medium_term_memory: Any = None) -> list[dict[str, Any]]:
        if medium_term_memory is not None:
            return medium_term_memory.get_task_history(task_id)
        return []

    async def query_log(self, event_type: str, time_range: Any = None, trace_log: Any = None) -> list[dict[str, Any]]:
        if trace_log is None:
            return []
        events = await trace_log.read(
            session_id="default",
            event_type=event_type,
            time_range=time_range,
        )
        return [e.to_dict() for e in events]

    async def get_app_state(self, package_name: str) -> dict[str, Any]:
        """Return the current state for an app (placeholder projection).

        In a device-automation deployment this queries the actual accessibility
        service; here it returns a stub so the interface contract holds.
        """
        return {
            "package": package_name,
            "running": False,
            "source": "external_state_tools",
            "note": "simulated state; wire to accessibility service in device deployments",
        }


_default_tools: ExternalStateTools | None = None


def get_external_state_tools() -> ExternalStateTools:
    global _default_tools
    if _default_tools is None:
        _default_tools = ExternalStateTools()
    return _default_tools
