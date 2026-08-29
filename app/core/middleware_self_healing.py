"""Self-healing middleware — automatic retry and recovery for failed tool calls.

Wraps the existing DebugLoopEngine and adds middleware-based composition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.middleware import MiddlewareBase

if TYPE_CHECKING:
    from app.core.agent_engine import AgentEngine, AgentSession

logger = structlog.get_logger()


class SelfHealingMiddleware(MiddlewareBase):
    """Middleware that automatically retries failed tool calls.

    Uses the existing DebugLoopEngine for error analysis and fix generation,
    but wraps it in the middleware interface for composable usage.

    Configuration:
        max_retries: Maximum number of retry attempts per tool call (default: 2)
        retry_delay: Base delay between retries in seconds (default: 1.0)
        backoff_factor: Exponential backoff multiplier (default: 1.5)
        skip_patterns: Error patterns that should not be retried
    """

    def __init__(
        self,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        backoff_factor: float = 1.5,
        skip_patterns: list[str] | None = None,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.skip_patterns = skip_patterns or [
            "blocked by sandbox",
            "permission denied",
            "command blocked by safety policy",
        ]
        self._debug_loop = None

    def _get_debug_loop(self, engine: AgentEngine):
        """Get or create the DebugLoopEngine instance."""
        if self._debug_loop is None:
            self._debug_loop = getattr(engine, "debug_loop", None)
        return self._debug_loop

    def _should_skip(self, error: str) -> bool:
        """Check if the error should not be retried."""
        error_lower = error.lower()
        return any(pattern.lower() in error_lower for pattern in self.skip_patterns)

    async def on_acting(
        self,
        engine: AgentEngine,
        session: AgentSession,
        input_kwargs: dict[str, Any],
        next_handler: Any,
    ) -> Any:
        """Intercept tool execution and retry on failure."""
        # Execute original handler
        results = []
        async for event in next_handler():
            results.append(event)

        # Check for failures and attempt recovery
        for result in results:
            if hasattr(result, "error") and result.error and not self._should_skip(result.error):
                recovered = await self._attempt_recovery(
                    engine=engine,
                    session=session,
                    tool_name=getattr(result, "tool_name", "unknown"),
                    arguments=getattr(result, "arguments", {}),
                    error=result.error,
                )
                if recovered:
                    result.error = ""
                    result.result = recovered
                    result.success = True

        # Yield all results
        for event in results:
            yield event

    async def _attempt_recovery(
        self,
        engine: AgentEngine,
        session: AgentSession,
        tool_name: str,
        arguments: dict[str, Any],
        error: str,
    ) -> str | None:
        """Attempt to recover from a tool failure using DebugLoop."""
        debug_loop = self._get_debug_loop(engine)
        if debug_loop is None:
            return None

        try:
            async def retry_callback(name: str, args: dict[str, Any]) -> str:
                return await engine.tool_registry.execute(name, args)

            async def get_file_content(path: str | None) -> str:
                if path:
                    try:
                        with open(path) as f:
                            return f.read()
                    except Exception:
                        return ""
                return ""

            result = await debug_loop.handle_tool_error(
                tool_name=tool_name,
                arguments=arguments,
                error_output=error,
                get_file_content=get_file_content,
                retry_callback=retry_callback,
            )

            if result.success:
                logger.info(
                    "self_healing.recovered",
                    tool=tool_name,
                    attempt=result.attempt,
                    fix=result.fix_used,
                )
                return result.output

            return None
        except Exception as e:
            logger.warning("self_healing.recovery_failed", error=str(e))
            return None
