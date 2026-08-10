"""Code-first agent that generates Python actions.

Implements a ReAct-style agent that:
1. Generates code from LLM
2. Parses code from output
3. Executes code in sandbox
4. Stores execution logs/observations
5. Loops until final_answer or max_steps

Inspired by HuggingFace smolagents.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.engine.code_executor import (
    ExecutionResult,
    ExecutionStatus,
    SafeExecutor,
)
from app.engine.planning import Plan, Planner
from app.engine.stream_output import (
    DefaultStreamOutput,
    StreamOutput,
)
from app.engine.tool_collection import ToolCollection

logger = structlog.get_logger()


@dataclass
class StepResult:
    """Result of a single agent step."""
    step_number: int
    code: str
    execution_result: ExecutionResult | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    observations: str = ""


@dataclass
class AgentResult:
    """Result of a complete agent run."""
    task: str
    final_answer: Any = None
    steps: list[StepResult] = field(default_factory=list)
    total_steps: int = 0
    success: bool = False
    error: str | None = None
    plan: Plan | None = None


class CodeAgent:
    """Agent that generates Python code as actions.

    Uses a ReAct loop where the LLM generates code, the code is executed
    in a safe AST interpreter, and observations are fed back to the LLM.
    """

    def __init__(
        self,
        model: Any,
        tools: dict[str, Callable] | ToolCollection | None = None,
        executor: SafeExecutor | None = None,
        max_steps: int = 10,
        planning_interval: int | None = None,
        harness: Any = None,
        stream_output: StreamOutput | None = None,
        system_prompt_override: str | None = None,
    ):
        self.model = model
        self.max_steps = max_steps
        self.planning_interval = planning_interval
        self.harness = harness
        self.stream_output = stream_output or DefaultStreamOutput()
        self.system_prompt_override = system_prompt_override

        # Setup tools
        if isinstance(tools, ToolCollection):
            self.tool_collection = tools
        elif tools is not None:
            self.tool_collection = ToolCollection.from_functions(tools)
        else:
            self.tool_collection = ToolCollection()

        # Setup executor
        self.executor = executor or SafeExecutor(self.tool_collection.tools)

        # Setup planner
        self.planner = Planner(model=model)

    async def run(self, task: str, stream: bool = False) -> AgentResult:
        """Run the code agent on a task.

        Args:
            task: The task description to solve.
            stream: Whether to stream intermediate output.

        Returns:
            AgentResult with final answer and execution steps.
        """
        result = AgentResult(task=task)
        conversation: list[dict[str, Any]] = []

        # Create plan if planning is enabled
        if self.planning_interval is not None:
            plan = await self.planner.create_plan(task)
            result.plan = plan
            await self.stream_output.on_plan_update(plan)

        # Build system prompt
        system_prompt = self._build_system_prompt(task)

        # Add initial user message
        conversation.append({"role": "user", "content": task})

        for step_num in range(1, self.max_steps + 1):
            await self.stream_output.on_step_start(step_num, task)

            try:
                step_result = await self._execute_step(
                    step_num, system_prompt, conversation, stream
                )
                result.steps.append(step_result)

                if step_result.error:
                    await self.stream_output.on_error(step_result.error)

                # Check for final answer
                if step_result.execution_result and step_result.execution_result.output is not None:
                    output = step_result.execution_result.output
                    final = self._extract_final_answer(output)
                    if final is not None:
                        result.final_answer = final
                        result.success = True
                        result.total_steps = step_num
                        await self.stream_output.on_final_answer(str(final))
                        return result

                # Update plan if enabled
                if result.plan and self.planning_interval:
                    if step_num % self.planning_interval == 0:
                        result.plan = await self.planner.update_plan(
                            result.plan,
                            step_num - 1,
                            step_result.execution_result.output if step_result.execution_result else None,
                            step_result.error,
                        )
                        await self.stream_output.on_plan_update(result.plan)

                await self.stream_output.on_step_end(step_num, step_result.execution_result)

            except Exception as e:
                logger.error("agent.step_error", step=step_num, error=str(e))
                result.error = str(e)
                await self.stream_output.on_error(str(e))
                break

        result.total_steps = len(result.steps)
        return result

    async def run_stream(self, task: str) -> AsyncIterator[dict[str, Any]]:
        """Run the agent with streaming output.

        Yields dict events for each step of execution.
        """
        conversation: list[dict[str, Any]] = []
        system_prompt = self._build_system_prompt(task)
        conversation.append({"role": "user", "content": task})

        if self.planning_interval is not None:
            plan = await self.planner.create_plan(task)
            yield {"type": "plan", "data": plan.to_context()}

        for step_num in range(1, self.max_steps + 1):
            yield {"type": "step_start", "step": step_num}

            try:
                step_result = await self._execute_step(
                    step_num, system_prompt, conversation, stream=True
                )

                yield {
                    "type": "step_result",
                    "step": step_num,
                    "code": step_result.code,
                    "output": step_result.execution_result.output if step_result.execution_result else None,
                    "error": step_result.error,
                }

                if step_result.execution_result and step_result.execution_result.output is not None:
                    output = step_result.execution_result.output
                    final = self._extract_final_answer(output)
                    if final is not None:
                        yield {"type": "final_answer", "answer": final}
                        return

            except Exception as e:
                yield {"type": "error", "error": str(e)}
                return

        yield {"type": "max_steps_reached", "steps": self.max_steps}

    async def _execute_step(
        self,
        step_num: int,
        system_prompt: str,
        conversation: list[dict[str, Any]],
        stream: bool = False,
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        messages = [{"role": "system", "content": system_prompt}, *conversation]

        # Generate code from LLM
        if stream:
            response_text = await self._stream_chat(messages)
        else:
            response = await self.model.chat(messages)
            response_text = response if isinstance(response, str) else getattr(response, "content", str(response))

        # Parse code from output
        code = self._extract_code(response_text)
        if not code:
            return StepResult(
                step_number=step_num,
                code="",
                error="No code found in model output",
            )

        # Execute code
        exec_result = self.executor.execute(code)
        await self.stream_output.on_code_execution(
            code,
            str(exec_result.output) if exec_result.output else "",
            exec_result.error,
        )

        # Build observations
        observations = self._build_observations(exec_result)

        # Track tool calls
        tool_calls = self._extract_tool_calls(code)

        # Add to conversation
        conversation.append({"role": "assistant", "content": response_text})
        conversation.append({"role": "user", "content": observations})

        return StepResult(
            step_number=step_num,
            code=code,
            execution_result=exec_result,
            tool_calls=tool_calls,
            error=exec_result.error if exec_result.status != ExecutionStatus.SUCCESS else None,
            observations=observations,
        )

    async def _stream_chat(self, messages: list[dict[str, Any]]) -> str:
        """Stream chat response and collect full text."""
        full_text = ""
        try:
            async for token in self.model.stream(messages):
                full_text += token
                await self.stream_output.on_token(token)
        except NotImplementedError:
            response = await self.model.chat(messages)
            full_text = response if isinstance(response, str) else getattr(response, "content", str(response))
        return full_text

    def _build_system_prompt(self, task: str) -> str:
        """Build the system prompt with tool definitions."""
        if self.system_prompt_override:
            return self.system_prompt_override

        tools = self.tool_collection.get_definitions(format="openai")

        if self.harness:
            return self.harness.format_system_prompt(task, tools)

        # Default system prompt
        tool_descriptions = self._format_tools_for_prompt(tools)

        return f"""You are a helpful coding assistant that solves tasks by writing Python code.

## Available Tools

{tool_descriptions}

## Instructions

Write Python code to solve the task. You can define functions, use loops,
conditionals, and call the available tools. Each response should contain
a single code block.

Use ```python to start your code block and ``` to end it.

When you have the final answer, call:
    final_answer(your_answer)

Your code will be executed in a safe sandbox."""

    def _format_tools_for_prompt(self, tools: list[dict]) -> str:
        """Format tool definitions for the prompt."""
        if not tools:
            return "No tools available."

        lines = []
        for tool in tools:
            func = tool.get("function", tool)
            name = func.get("name", "")
            desc = func.get("description", "")
            params = func.get("parameters", {})

            lines.append(f"### {name}")
            lines.append(desc)
            if params:
                props = params.get("properties", {})
                required = params.get("required", [])
                if props:
                    lines.append("Parameters:")
                    for pname, pinfo in props.items():
                        pdesc = pinfo.get("description", "")
                        ptype = pinfo.get("type", "any")
                        req_mark = " (required)" if pname in required else ""
                        lines.append(f"  - {pname} ({ptype}){req_mark}: {pdesc}")
            lines.append("")

        return "\n".join(lines)

    def _extract_code(self, response: str) -> str:
        """Extract Python code block from model output."""
        # Try ```python first
        matches = re.findall(r"```python\s*\n(.*?)```", response, re.DOTALL)
        if matches:
            return matches[-1].strip()

        # Try generic ```
        matches = re.findall(r"```\s*\n(.*?)```", response, re.DOTALL)
        if matches:
            return matches[-1].strip()

        # Try code after "Code:" or similar markers
        code_markers = [
            r"(?:Code|Response):\s*\n?(.*?)$",
            r"(?:Here(?:'s| is) the code):\s*\n?(.*?)$",
        ]
        for pattern in code_markers:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_final_answer(self, output: Any) -> Any:
        """Check if output contains a final_answer call result."""
        if output is None:
            return None

        output_str = str(output)
        if "final_answer" in output_str.lower():
            return output_str

        return None

    def _extract_tool_calls(self, code: str) -> list[dict[str, Any]]:
        """Extract tool calls from code."""
        calls = []
        for tool_name in self.tool_collection.tools:
            pattern = rf"\b{re.escape(tool_name)}\s*\("
            if re.search(pattern, code):
                calls.append({"tool": tool_name})
        return calls

    def _build_observations(self, exec_result: ExecutionResult) -> str:
        """Build observation string from execution result."""
        parts = []

        if exec_result.status == ExecutionStatus.SUCCESS:
            if exec_result.output is not None:
                parts.append(f"Output: {exec_result.output}")
            if exec_result.stdout:
                stdout = "\n".join(exec_result.stdout)
                parts.append(f"Stdout:\n{stdout}")
        elif exec_result.status == ExecutionStatus.BLOCKED:
            parts.append(f"Code was blocked: {exec_result.error}")
        elif exec_result.status == ExecutionStatus.TIMEOUT:
            parts.append(f"Execution timed out: {exec_result.error}")
        else:
            parts.append(f"Execution error: {exec_result.error}")

        parts.append("\nWhat would you like to do next?")
        return "\n".join(parts)

    async def plan(self, task: str) -> list[str]:
        """Generate a plan for the task."""
        plan = await self.planner.create_plan(task)
        return [step.description for step in plan.steps]

    def get_system_prompt(self) -> str:
        """Get the system prompt with tool definitions."""
        return self._build_system_prompt("")
