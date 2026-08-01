"""Per-model prompt format emulation.

Provides model-specific prompt formatting and output parsing to ensure
correct interaction with different LLM providers (Claude, GPT, Qwen, etc.).
"""

from __future__ import annotations

import re
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


# Type alias for output parser function
OutputParser = Callable[[str], dict[str, Any]]


class Harness:
    """Per-model prompt format emulation.

    Encapsulates model-specific formatting for system prompts,
    tool definitions, and output parsing.
    """

    def __init__(
        self,
        name: str,
        system_template: str,
        output_parser: OutputParser,
        tool_format: str = "openai",
    ):
        self.name = name
        self.system_template = system_template
        self.output_parser = output_parser
        self.tool_format = tool_format

    def format_system_prompt(
        self,
        task: str,
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """Format the system prompt for this model."""
        return self.system_template.format(
            task=task,
            tools=self._format_tools(tools),
            **kwargs,
        )

    def format_messages(
        self,
        system_prompt: str,
        conversation: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Format messages for this model's API."""
        return [
            {"role": "system", "content": system_prompt},
            *conversation,
        ]

    def parse_output(self, output: str) -> dict[str, Any]:
        """Parse model output to extract code, thinking, and final answer."""
        return self.output_parser(output)

    def _format_tools(self, tools: list[dict[str, Any]]) -> str:
        """Format tool definitions for the system prompt."""
        if not tools:
            return "No tools available."

        lines = []
        for tool in tools:
            if self.tool_format == "openai":
                func = tool.get("function", tool)
                name = func.get("name", "")
                desc = func.get("description", "")
                params = func.get("parameters", {})
            elif self.tool_format == "anthropic":
                name = tool.get("name", "")
                desc = tool.get("description", "")
                params = tool.get("input_schema", {})
            else:
                name = tool.get("name", "")
                desc = tool.get("description", "")
                params = tool.get("parameters", {})

            lines.append(f"### {name}")
            lines.append(desc)
            if params:
                props = params.get("properties", {})
                if props:
                    lines.append("Parameters:")
                    for pname, pinfo in props.items():
                        pdesc = pinfo.get("description", "")
                        ptype = pinfo.get("type", "any")
                        lines.append(f"  - {pname} ({ptype}): {pdesc}")
            lines.append("")

        return "\n".join(lines)


def _parse_default_output(output: str) -> dict[str, Any]:
    """Default output parser for code agent responses.

    Extracts thinking, code blocks, and final answers from the response.
    """
    result: dict[str, Any] = {
        "thinking": "",
        "code": "",
        "final_answer": "",
        "raw": output,
    }

    # Extract code blocks
    code_blocks = re.findall(r"```python\s*\n(.*?)```", output, re.DOTALL)
    if code_blocks:
        result["code"] = code_blocks[-1].strip()

    # Extract final answer
    final_match = re.search(
        r"final_answer\s*\(.*?\)",
        output,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        result["final_answer"] = final_match.group(0)

    # Extract thinking (everything before first code block)
    if code_blocks:
        parts = output.split("```python", 1)
        if parts:
            result["thinking"] = parts[0].strip()
    else:
        result["thinking"] = output.strip()

    return result


def _parse_claude_output(output: str) -> dict[str, Any]:
    """Parse Claude-specific output format."""
    result: dict[str, Any] = {
        "thinking": "",
        "code": "",
        "final_answer": "",
        "raw": output,
    }

    # Claude often uses <thinking> tags
    thinking_match = re.search(
        r"<thinking>(.*?)</thinking>",
        output,
        re.DOTALL,
    )
    if thinking_match:
        result["thinking"] = thinking_match.group(1).strip()

    # Code blocks
    code_blocks = re.findall(r"```python\s*\n(.*?)```", output, re.DOTALL)
    if code_blocks:
        result["code"] = code_blocks[-1].strip()

    # Tool use (Anthropic format)
    tool_use_match = re.search(
        r"<tool_use>\s*(\w+)\s*(.*?)</tool_use>",
        output,
        re.DOTALL,
    )
    if tool_use_match:
        result["tool_name"] = tool_use_match.group(1)
        result["tool_input"] = tool_use_match.group(2).strip()

    # Final answer
    if not thinking_match:
        parts = output.split("```python", 1)
        if parts:
            result["thinking"] = parts[0].strip()

    final_match = re.search(
        r"final_answer\s*\(.*?\)",
        output,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        result["final_answer"] = final_match.group(0)

    return result


def _parse_gpt_output(output: str) -> dict[str, Any]:
    """Parse GPT-specific output format."""
    result: dict[str, Any] = {
        "thinking": "",
        "code": "",
        "final_answer": "",
        "raw": output,
    }

    # Code blocks
    code_blocks = re.findall(r"```python\s*\n(.*?)```", output, re.DOTALL)
    if code_blocks:
        result["code"] = code_blocks[-1].strip()

    # Extract reasoning (before code)
    if code_blocks:
        parts = output.split("```python", 1)
        if parts:
            result["thinking"] = parts[0].strip()
    else:
        result["thinking"] = output.strip()

    # Function call detection
    fn_call_match = re.search(
        r"```\s*\{\s*\"name\":\s*\"(\w+)\".*\}\s*```",
        output,
        re.DOTALL,
    )
    if fn_call_match:
        result["function_call"] = fn_call_match.group(1)

    # Final answer
    final_match = re.search(
        r"final_answer\s*\(.*?\)",
        output,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        result["final_answer"] = final_match.group(0)

    return result


def _parse_qwen_output(output: str) -> dict[str, Any]:
    """Parse Qwen-specific output format."""
    result: dict[str, Any] = {
        "thinking": "",
        "code": "",
        "final_answer": "",
        "raw": output,
    }

    # Qwen uses ```py or ```python
    code_blocks = re.findall(r"```p?y?\w*\s*\n(.*?)```", output, re.DOTALL)
    if code_blocks:
        result["code"] = code_blocks[-1].strip()

    # Final answer with Chinese markers
    final_match = re.search(
        r"final_answer\s*\(.*?\)",
        output,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        result["final_answer"] = final_match.group(0)

    # Thinking
    if code_blocks:
        parts = output.split("```py", 1)
        if parts:
            result["thinking"] = parts[0].strip()
    else:
        result["thinking"] = output.strip()

    return result


def _parse_deepseek_output(output: str) -> dict[str, Any]:
    """Parse DeepSeek-specific output format."""
    result: dict[str, Any] = {
        "thinking": "",
        "code": "",
        "final_answer": "",
        "raw": output,
    }

    # DeepSeek often provides thinking before code
    thinking_match = re.search(
        r"<think>(.*?)</think>",
        output,
        re.DOTALL,
    )
    if thinking_match:
        result["thinking"] = thinking_match.group(1).strip()
        remaining = output[thinking_match.end():]
    else:
        remaining = output

    # Code blocks
    code_blocks = re.findall(r"```python\s*\n(.*?)```", remaining, re.DOTALL)
    if code_blocks:
        result["code"] = code_blocks[-1].strip()

    # Final answer
    final_match = re.search(
        r"final_answer\s*\(.*?\)",
        remaining,
        re.IGNORECASE | re.DOTALL,
    )
    if final_match:
        result["final_answer"] = final_match.group(0)

    return result


class HarnessRegistry:
    """Registry of model-specific harnesses."""

    _harnesses: dict[str, Harness] = {}
    _default_harness: Harness | None = None

    @classmethod
    def register(cls, model_prefix: str, harness: Harness) -> None:
        """Register a harness for a model prefix."""
        cls._harnesses[model_prefix] = harness
        logger.info("harness.registered", model_prefix=model_prefix, harness=harness.name)

    @classmethod
    def get(cls, model_id: str) -> Harness:
        """Get the best harness for a model ID.

        Matches by prefix (e.g., "claude-sonnet" matches "claude" prefix).
        Falls back to default harness if no specific match found.
        """
        # Try exact match first
        if model_id in cls._harnesses:
            return cls._harnesses[model_id]

        # Try prefix matching
        for prefix, harness in cls._harnesses.items():
            if model_id.startswith(prefix):
                return harness

        # Return default
        if cls._default_harness is None:
            cls._default_harness = _create_default_harness()

        return cls._default_harness

    @classmethod
    def list_harnesses(cls) -> list[str]:
        """List all registered model prefixes."""
        return list(cls._harnesses.keys())

    @classmethod
    def set_default(cls, harness: Harness) -> None:
        """Set the default harness."""
        cls._default_harness = harness


def _create_default_harness() -> Harness:
    """Create the default harness."""
    return Harness(
        name="default",
        system_template=_DEFAULT_SYSTEM_TEMPLATE,
        output_parser=_parse_default_output,
        tool_format="openai",
    )


def _create_claude_harness() -> Harness:
    """Create Claude-specific harness."""
    return Harness(
        name="claude",
        system_template=_CLAUDE_SYSTEM_TEMPLATE,
        output_parser=_parse_claude_output,
        tool_format="anthropic",
    )


def _create_gpt_harness() -> Harness:
    """Create GPT-specific harness."""
    return Harness(
        name="gpt",
        system_template=_GPT_SYSTEM_TEMPLATE,
        output_parser=_parse_gpt_output,
        tool_format="openai",
    )


def _create_qwen_harness() -> Harness:
    """Create Qwen-specific harness."""
    return Harness(
        name="qwen",
        system_template=_QWEN_SYSTEM_TEMPLATE,
        output_parser=_parse_qwen_output,
        tool_format="openai",
    )


def _create_deepseek_harness() -> Harness:
    """Create DeepSeek-specific harness."""
    return Harness(
        name="deepseek",
        system_template=_DEEPSEEK_SYSTEM_TEMPLATE,
        output_parser=_parse_deepseek_output,
        tool_format="openai",
    )


# ─── System Prompt Templates ───────────────────────────────────────────────

_DEFAULT_SYSTEM_TEMPLATE = """You are a helpful coding assistant that solves tasks by writing Python code.

You have access to the following tools:
{tools}

Write Python code to solve the task. You can define functions, use loops,
conditionals, and call the available tools.

When you have the final answer, call:
    final_answer(your_answer)

Your code will be executed in a safe sandbox."""

_CLAUDE_SYSTEM_TEMPLATE = """You are a helpful coding assistant that solves tasks by writing Python code.

<tools>
{tools}
</tools>

Write Python code to solve the task. You can define functions, use loops,
conditionals, and call the available tools.

When you have the final answer, call:
    final_answer(your_answer)

Your code will be executed in a safe sandbox."""

_GPT_SYSTEM_TEMPLATE = """You are a helpful coding assistant that solves tasks by writing Python code.

## Available Tools

{tools}

## Instructions

Write Python code to solve the task. You can define functions, use loops,
conditionals, and call the available tools.

When you have the final answer, call:
    final_answer(your_answer)

Your code will be executed in a safe sandbox."""

_QWEN_SYSTEM_TEMPLATE = """You are a helpful coding assistant that solves tasks by writing Python code.

## Tools

{tasks}

Available tools:
{tools}

Write Python code to solve the task. You can define functions, use loops,
conditionals, and call the available tools.

When you have the final answer, call:
    final_answer(your_answer)

Your code will be executed in a safe sandbox."""

_DEEPSEEK_SYSTEM_TEMPLATE = """You are a helpful coding assistant that solves tasks by writing Python code.

## Available Tools

{tools}

## Instructions

Think through the problem step by step, then write Python code to solve it.
You can define functions, use loops, conditionals, and call available tools.

When you have the final answer, call:
    final_answer(your_answer)

Your code will be executed in a safe sandbox."""

# ─── Register default harnesses ──────────────────────────────────────────────

HarnessRegistry.register("claude", _create_claude_harness())
HarnessRegistry.register("gpt", _create_gpt_harness())
HarnessRegistry.register("gpt-4", _create_gpt_harness())
HarnessRegistry.register("gpt-3.5", _create_gpt_harness())
HarnessRegistry.register("qwen", _create_qwen_harness())
HarnessRegistry.register("deepseek", _create_deepseek_harness())
