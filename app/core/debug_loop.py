"""Auto-debug loop for recovering from tool execution failures.

"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.error_analyzer import ErrorAnalysis, ErrorAnalyzer, ErrorType

logger = structlog.get_logger()


@dataclass
class FixStrategy:
    """Strategy for fixing an error."""

    approach: str  # "modify_code", "change_approach", "ask_user"
    description: str
    patch_content: str | None = None
    new_arguments: dict[str, Any] | None = None
    new_tool: str | None = None
    confidence: float = 0.5


@dataclass
class DebugResult:
    """Result of a debug attempt."""

    success: bool
    attempt: int
    max_attempts: int
    fix_used: str
    error: str | None = None
    output: str | None = None


@dataclass
class DebugMemory:
    """Learned fix patterns for future reference."""

    error_signature: str
    fix_description: str
    success_count: int = 1
    last_used: float = field(default_factory=time.time)


class DebugLoop:
    """Autonomous error analysis and recovery loop.

    Detects errors from tool execution, classifies them, generates fix strategies,
    auto-retries with fixes (up to max_attempts), and learns from successful fixes.

    """

    def __init__(
        self,
        model_registry: Any | None = None,
        max_attempts: int = 3,
        memory_file: str = ".agent_debug_memory.json",
    ):
        self.model_registry = model_registry
        self.max_attempts = max_attempts
        self.analyzer = ErrorAnalyzer()
        self._memory: list[DebugMemory] = []
        self._memory_file = memory_file
        self._load_memory()

    def _load_memory(self) -> None:
        try:
            with open(self._memory_file, encoding="utf-8") as f:
                data = json.load(f)
                self._memory = [DebugMemory(**m) for m in data.get("entries", [])]
        except (FileNotFoundError, json.JSONDecodeError):
            self._memory = []

    def _save_memory(self) -> None:
        try:
            with open(self._memory_file, "w", encoding="utf-8") as f:
                json.dump({
                    "entries": [
                        {
                            "error_signature": m.error_signature,
                            "fix_description": m.fix_description,
                            "success_count": m.success_count,
                            "last_used": m.last_used,
                        }
                        for m in self._memory
                    ]
                }, f)
        except Exception as e:
            logger.warning("debug_loop.save_memory_failed", error=str(e))

    async def handle_tool_error(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        error_output: str,
        get_file_content: Callable[[str | None], Coroutine[Any, Any, str]] | None = None,
        retry_callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, str]] | None = None,
    ) -> DebugResult:
        """Process a tool execution error and attempt auto-recovery.

        Args:
            tool_name: Name of the tool that failed
            arguments: Arguments passed to the tool
            error_output: Error output from the tool
            get_file_content: Optional callback to read file content for context
            retry_callback: Optional callback to retry with new arguments

        Returns:
            DebugResult with success status and details
        """
        analysis = self.analyzer.analyze(error_output, context={"tool_name": tool_name, "arguments": arguments})
        logger.info(
            "debug_loop.analyzed_error",
            tool=tool_name,
            error_type=analysis.error_type.value,
            file_path=analysis.file_path,
            line_number=analysis.line_number,
        )

        learned_fix = self._find_learned_fix(analysis)
        strategy = await self._generate_fix_strategy(
            analysis=analysis,
            tool_name=tool_name,
            arguments=arguments,
            learned_fix=learned_fix,
            get_file_content=get_file_content,
        )

        if strategy.approach == "modify_code" and strategy.patch_content:
            applied = await self._apply_patch(analysis, strategy)
            if not applied:
                strategy.approach = "change_approach"
                strategy.description += " (patch failed, switching approach)"

        if strategy.approach == "ask_user":
            logger.info("debug_loop.escalating_to_user", reason=strategy.description)
            return DebugResult(
                success=False,
                attempt=1,
                max_attempts=self.max_attempts,
                fix_used="escalate",
                error=f"AUTO-DEBUG: {strategy.description}",
            )

        if retry_callback is None:
            return DebugResult(
                success=False,
                attempt=1,
                max_attempts=self.max_attempts,
                fix_used="no_retry_callback",
                error="No retry callback provided",
            )

        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                retry_args = strategy.new_arguments or arguments
                retry_tool = strategy.new_tool or tool_name
                output = await retry_callback(retry_tool, retry_args)

                if self._is_success_output(output):
                    self._record_success(analysis, strategy)
                    logger.info("debug_loop.retry_succeeded", attempt=attempt, tool=retry_tool)
                    return DebugResult(
                        success=True,
                        attempt=attempt,
                        max_attempts=self.max_attempts,
                        fix_used=strategy.description,
                        output=output,
                    )

                last_error = output
                analysis = self.analyzer.analyze(output, context={"tool_name": retry_tool, "arguments": retry_args})
                strategy = await self._generate_fix_strategy(
                    analysis=analysis,
                    tool_name=retry_tool,
                    arguments=retry_args,
                    learned_fix=self._find_learned_fix(analysis),
                    get_file_content=get_file_content,
                )

            except Exception as e:
                last_error = str(e)

        logger.warning("debug_loop.max_attempts_reached", tool=tool_name, attempts=self.max_attempts)
        return DebugResult(
            success=False,
            attempt=self.max_attempts,
            max_attempts=self.max_attempts,
            fix_used=strategy.description,
            error=last_error or error_output,
        )

    async def _generate_fix_strategy(
        self,
        analysis: ErrorAnalysis,
        tool_name: str,
        arguments: dict[str, Any],
        learned_fix: str | None,
        get_file_content: Callable[[str | None], Coroutine[Any, Any, str]] | None = None,
    ) -> FixStrategy:
        """Generate a fix strategy based on error analysis."""

        if learned_fix:
            return FixStrategy(
                approach="modify_code",
                description=f"Apply learned fix: {learned_fix}",
                confidence=0.8,
            )

        if analysis.error_type == ErrorType.SYNTAX_ERROR:
            return FixStrategy(
                approach="change_approach",
                description=f"Syntax error in {analysis.file_path or 'unknown file'}: ask LLM to rewrite the code",
                confidence=0.7,
            )

        if analysis.error_type == ErrorType.FILE_NOT_FOUND:
            return FixStrategy(
                approach="modify_code",
                description=f"Create missing file {analysis.file_path or 'target'} or use correct path",
                new_arguments=self._suggest_path_fix(arguments),
                confidence=0.6,
            )

        if analysis.error_type == ErrorType.PERMISSION_ERROR:
            return FixStrategy(
                approach="ask_user",
                description=f"Permission denied: cannot access {analysis.file_path or 'resource'}. Manual intervention required.",
                confidence=0.3,
            )

        if analysis.error_type == ErrorType.NETWORK_ERROR:
            return FixStrategy(
                approach="change_approach",
                description="Network error: retry with exponential backoff or alternative endpoint",
                confidence=0.5,
            )

        if analysis.error_type == ErrorType.TIMEOUT:
            return FixStrategy(
                approach="modify_code",
                description="Timeout: increase timeout or simplify the request",
                new_arguments=self._suggest_timeout_fix(arguments),
                confidence=0.5,
            )

        if analysis.error_type == ErrorType.IMPORT_ERROR:
            return FixStrategy(
                approach="modify_code",
                description="Import error: install missing package or fix import path",
                confidence=0.6,
            )

        if analysis.error_type == ErrorType.AUTHENTICATION_ERROR:
            return FixStrategy(
                approach="ask_user",
                description="Authentication/authorization error: check credentials or permissions",
                confidence=0.3,
            )

        return FixStrategy(
            approach="change_approach",
            description="Unknown error: retry with modified arguments or alternative tool",
            confidence=0.4,
        )

    async def _apply_patch(self, analysis: ErrorAnalysis, strategy: FixStrategy) -> bool:
        """Attempt to apply a patch if the strategy provides one."""
        if not strategy.patch_content:
            return False
        if not analysis.file_path:
            return False
        try:
            if await self._write_patch(analysis.file_path, strategy.patch_content):
                logger.info("debug_loop.patch_applied", file=analysis.file_path)
                return True
        except Exception as e:
            logger.warning("debug_loop.patch_failed", error=str(e))
        return False

    async def _write_patch(self, file_path: str, patch_content: str) -> bool:
        """Write patch content to file (atomic)."""
        import os
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(patch_content)
        os.replace(tmp_path, file_path)
        return True

    def _suggest_path_fix(self, arguments: dict[str, Any]) -> dict[str, Any]:
        new_args = dict(arguments)
        for key in ("path", "file", "file_path", "directory", "dir"):
            if key in new_args and isinstance(new_args[key], str):
                val = new_args[key]
                if val.startswith("./"):
                    new_args[key] = val[2:]
                elif not val.startswith("/") and not val.startswith("~"):
                    new_args[key] = "./" + val
        return new_args

    def _suggest_timeout_fix(self, arguments: dict[str, Any]) -> dict[str, Any]:
        new_args = dict(arguments)
        for key in ("timeout", "max_time"):
            if key in new_args:
                try:
                    new_args[key] = min(int(new_args[key]) * 2, 300)
                except (ValueError, TypeError):
                    new_args[key] = 60
        return new_args

    def _is_success_output(self, output: str) -> bool:
        if not output:
            return False
        failure_indicators = [
            "Error:", "error:", "Traceback", "Exception", "Failed", "failed",
            "BLOCKED:", "TIMEOUT:", "Command exited with code", "Permission denied",
        ]
        lower = output.lower()
        if any(lower.startswith(ind.lower()) for ind in failure_indicators):
            return False
        return not ("exit code" in lower and "0" not in lower[:20])

    def _find_learned_fix(self, analysis: ErrorAnalysis) -> str | None:
        signature = f"{analysis.error_type.value}:{analysis.file_path or ''}:{analysis.line_number or ''}"
        matches = [m for m in self._memory if m.error_signature == signature]
        if not matches:
            return None
        matches.sort(key=lambda m: m.success_count, reverse=True)
        return matches[0].fix_description

    def _record_success(self, analysis: ErrorAnalysis, strategy: FixStrategy) -> None:
        signature = f"{analysis.error_type.value}:{analysis.file_path or ''}:{analysis.line_number or ''}"
        existing = next((m for m in self._memory if m.error_signature == signature), None)
        if existing:
            existing.success_count += 1
            existing.last_used = time.time()
        else:
            self._memory.append(DebugMemory(
                error_signature=signature,
                fix_description=strategy.description,
            ))
        self._save_memory()


class DebugLoopEngine:
    """Top-level debug loop integration point.

    Designed for injection into AgentEngine for post-tool-error recovery.
    """

    def __init__(self, model_registry: Any | None = None, max_attempts: int = 3):
        self.loop = DebugLoop(model_registry=model_registry, max_attempts=max_attempts)

    async def recover(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        error_output: str,
        get_file_content: Callable[[str | None], Coroutine[Any, Any, str]] | None = None,
        retry_callback: Callable[[str, dict[str, Any]], Coroutine[Any, Any, str]] | None = None,
    ) -> DebugResult:
        return await self.loop.handle_tool_error(
            tool_name=tool_name,
            arguments=arguments,
            error_output=error_output,
            get_file_content=get_file_content,
            retry_callback=retry_callback,
        )
