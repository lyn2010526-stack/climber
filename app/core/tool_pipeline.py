"""Tool execution pipeline with prioritization, debugging, and approval support."""

from __future__ import annotations

import structlog
from typing import Any

from app.core import AgentEvent, AgentEventType, MessageRole
from app.core.parallel import ParallelToolExecutor, ToolExecutionResult
from app.core.tool_prioritizer import ToolPrioritizer

logger = structlog.get_logger()


class ToolExecutionResult:
    """Result of a single tool execution."""

    def __init__(self, tool_name: str, result: str, error: str | None, success: bool, arguments: dict | None = None, tool_call_id: str = ""):
        self.tool_name = tool_name
        self.result = result
        self.error = error
        self.success = success
        self.arguments = arguments or {}
        self.tool_call_id = tool_call_id


class ToolExecutionPipeline:
    """Orchestrates tool execution with prioritization, debugging, and approval."""

    def __init__(
        self,
        executor: ParallelToolExecutor,
        prioritizer: ToolPrioritizer,
        debug_loop: Any = None,
        approval_gate: Any = None,
        validator: Any = None,
    ) -> None:
        self.executor = executor
        self.prioritizer = prioritizer
        self.debug_loop = debug_loop
        self.approval_gate = approval_gate
        self.validator = validator

    async def execute(
        self,
        tool_calls: list[dict[str, Any]],
        session: Any,
    ) -> list[ToolExecutionResult]:
        """Execute tool calls through the pipeline."""
        results: list[ToolExecutionResult] = []

        for tc in tool_calls:
            tc_name = tc.get("function", {}).get("name", "")
            tc_args = tc.get("function", {}).get("arguments", {})
            tc_id = tc.get("id", "")
            if isinstance(tc_args, str):
                try:
                    import json
                    tc_args = json.loads(tc_args)
                except Exception as e:
                    logger.warning("tool_pipeline.json_parse_failed", error=str(e))

            # Approval gate check
            if self.approval_gate is not None:
                try:
                    allowed = await self.approval_gate.check(tc_name, tc_args)
                    if not allowed:
                        results.append(ToolExecutionResult(
                            tool_name=tc_name,
                            result="",
                            error="Permission denied by approval gate",
                            success=False,
                            arguments=tc_args,
                            tool_call_id=tc_id,
                        ))
                        continue
                except Exception as e:
                    results.append(ToolExecutionResult(
                        tool_name=tc_name,
                        result="",
                        error=f"Approval gate error: {e}",
                        success=False,
                        arguments=tc_args,
                        tool_call_id=tc_id,
                    ))
                    continue

            # Execute tool
            try:
                tool_results = await self.executor.execute_all([tc])
                for tr in tool_results:
                    self.prioritizer.record_outcome(tr.tool_name, tr.success, tr.duration_ms)

                    # Debug loop
                    if self.debug_loop and not tr.success and hasattr(session, 'debug_attempts'):
                        fixed = await self._attempt_debug(session, tr)
                        if fixed is not None:
                            tr = fixed

                    results.append(ToolExecutionResult(
                        tool_name=tr.tool_name,
                        result=tr.result,
                        error=tr.error,
                        success=tr.success,
                        arguments=tc_args,
                        tool_call_id=tc_id,
                    ))
            except Exception as e:
                results.append(ToolExecutionResult(
                    tool_name=tc_name,
                    result="",
                    error=str(e),
                    success=False,
                    arguments=tc_args,
                    tool_call_id=tc_id,
                ))

        return results

    async def _attempt_debug(self, session: Any, tr: Any) -> Any | None:
        """Run the debug loop for a failed tool result."""
        tool_name = tr.tool_name
        key = tool_name
        session.debug_attempts[key] = session.debug_attempts.get(key, 0) + 1
        original_args = tr.arguments or {}

        async def retry_callback(retry_tool: str, retry_args: dict[str, Any]) -> str:
            result = await self.executor.execute(retry_tool, retry_args)
            return str(result)

        try:
            result = await self.debug_loop.recover(
                tool_name=tool_name,
                arguments=original_args,
                error_output=tr.error or tr.result,
                retry_callback=retry_callback,
            )
            if result.success and result.output:
                logger.info("tool_pipeline.debug_recovered", tool=tool_name, attempt=result.attempt)
                tr.error = ""
                tr.result = result.output
                tr.success = True
                return tr
        except Exception as e:
            logger.warning("tool_pipeline.debug_failed", tool=tool_name, error=str(e))
        return None

    def to_events(self, results: list[ToolExecutionResult], tool_calls: list[dict[str, Any]]) -> list[AgentEvent]:
        """Convert execution results to AgentEvents."""
        events = []
        for i, tc in enumerate(tool_calls):
            tc_name = tc.get("function", {}).get("name", "")
            tc_args = tc.get("function", {}).get("arguments", {})
            events.append(AgentEvent(
                type=AgentEventType.TOOL_CALL,
                data={"id": tc.get("id"), "name": tc_name, "arguments": tc_args},
            ))

        # Build lookup from tool_call_id to tool_call for matching
        tc_by_id = {tc.get("id", ""): tc for tc in tool_calls}

        for r in results:
            event_data = {"tool_name": r.tool_name, "result": r.result, "error": r.error}
            if r.tool_call_id and r.tool_call_id in tc_by_id:
                event_data["tool_call_id"] = r.tool_call_id
            elif r.tool_call_id:
                logger.warning("tool_pipeline.to_events_no_match", tool_call_id=r.tool_call_id, tool_name=r.tool_name)
                event_data["tool_call_id"] = r.tool_call_id
            events.append(AgentEvent(
                type=AgentEventType.TOOL_RESULT,
                data=event_data,
            ))

        return events

    def append_to_messages(self, session: Any, results: list[ToolExecutionResult]) -> None:
        """Append tool results to session messages."""
        for r in results:
            msg: dict[str, Any] = {
                "role": MessageRole.TOOL,
                "content": r.result,
                "tool_call_id": r.tool_call_id,
                "name": r.tool_name,
            }
            session.messages.append(msg)
