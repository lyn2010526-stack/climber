"""Tool self-extension system.

Enables the agent to create new tools at runtime when existing tools are
insufficient. The flow:
1. Agent identifies a capability gap
2. System generates a Python function for the new tool
3. L1 static analysis validates the code
4. L2 sandbox executes a smoke test
5. On success, the tool is registered in ToolRegistry
"""

from __future__ import annotations

import asyncio
import textwrap
from dataclasses import dataclass, field
from typing import Any

import structlog

import ast

from app.core.sandbox import SandboxConfig, SandboxExecutor
from app.tools import tool_registry

logger = structlog.get_logger()


@dataclass
class ToolCreationRequest:
    """Request to create a new tool."""
    name: str
    description: str
    code: str  # Python function source
    parameters: dict[str, Any] = field(default_factory=dict)
    smoke_test_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCreationResult:
    """Result of a tool creation attempt."""
    success: bool
    tool_name: str
    message: str
    validation_issues: list[str] = field(default_factory=list)
    test_output: str = ""


class ToolSelfExtender:
    """Creates and registers new tools at runtime."""

    def __init__(self) -> None:
        self._sandbox = SandboxExecutor(SandboxConfig(
            timeout_seconds=15,
            max_output_bytes=5000,
            max_memory_mb=128,
        ))

    async def create_tool(self, request: ToolCreationRequest) -> ToolCreationResult:
        """Create and register a new tool after validation."""

        # 1. Validate name
        if not self._is_valid_name(request.name):
            return ToolCreationResult(
                success=False,
                tool_name=request.name,
                message=f"Invalid tool name: '{request.name}'",
            )

        # 2. Check for duplicates
        if tool_registry.get_tool(request.name):
            return ToolCreationResult(
                success=False,
                tool_name=request.name,
                message=f"Tool '{request.name}' already exists",
            )

        # 3. L1 Static analysis (AST-based)
        issues = self._validate_code_safety(request.code)
        if issues:
            return ToolCreationResult(
                success=False,
                tool_name=request.name,
                message="Code failed safety validation",
                validation_issues=issues,
            )

        # 4. L2 Sandbox smoke test
        test_result = await self._run_smoke_test(request)
        if not test_result.success:
            return ToolCreationResult(
                success=False,
                tool_name=request.name,
                message=f"Smoke test failed: {test_result.message}",
                test_output=test_result.test_output,
            )

        # 5. Register the tool
        try:
            self._register_tool(request)
            logger.info("tool_self_extended", tool_name=request.name)
            return ToolCreationResult(
                success=True,
                tool_name=request.name,
                message=f"Tool '{request.name}' created and registered",
                test_output=test_result.test_output,
            )
        except Exception as e:
            return ToolCreationResult(
                success=False,
                tool_name=request.name,
                message=f"Registration failed: {e}",
            )

    def _is_valid_name(self, name: str) -> bool:
        """Check if tool name is valid Python identifier."""
        if not name or not name.replace("_", "").isalnum():
            return False
        if name[0].isdigit():
            return False
        return True

    def _validate_code_safety(self, code: str) -> list[str]:
        """AST-based static analysis for code safety."""
        issues: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]

        # Walk AST to detect dangerous patterns
        dangerous_imports = {"os", "subprocess", "shutil", "socket", "ctypes",
                            "multiprocessing", "threading", "importlib"}
        dangerous_calls = {"eval", "exec", "compile", "__import__", "open"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_module = alias.name.split(".")[0]
                    if root_module in dangerous_imports:
                        issues.append(f"Dangerous import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_module = node.module.split(".")[0]
                    if root_module in dangerous_imports:
                        issues.append(f"Dangerous import from: {node.module}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_calls:
                        issues.append(f"Dangerous call: {node.func.id}")

        return issues

    async def _run_smoke_test(self, request: ToolCreationRequest) -> ToolCreationResult:
        """Execute the tool code in sandbox to verify it works."""

        test_code = textwrap.dedent(f"""
import asyncio
import json
import sys

{request.code}

async def _test():
    try:
        result = await {request.name}(**{request.smoke_test_args!r})
        print(json.dumps({{"ok": True, "result": str(result)[:500]}}))
    except TypeError:
        try:
            result = {request.name}(**{request.smoke_test_args!r})
            print(json.dumps({{"ok": True, "result": str(result)[:500]}}))
        except Exception as e2:
            print(json.dumps({{"ok": False, "error": str(e2)}}))
    except Exception as e:
        print(json.dumps({{"ok": False, "error": str(e)}}))

asyncio.run(_test())
""")

        import tempfile as _tf
        import os as _os

        fd, tmp_path = _tf.mkstemp(suffix=".py")
        output = ""
        try:
            _os.write(fd, test_code.encode())
            _os.close(fd)
            output = await self._sandbox.execute(f"python3 {tmp_path}")
        except Exception as e:
            return ToolCreationResult(
                success=False, tool_name=request.name,
                message=f"Sandbox error: {e}",
            )
        finally:
            _os.unlink(tmp_path)

        output = output.strip()

        if not output:
            return ToolCreationResult(
                success=False, tool_name=request.name,
                message="No output from smoke test",
            )

        try:
            data = json.loads(output.split("\n")[-1])
            if data.get("ok"):
                return ToolCreationResult(
                    success=True, tool_name=request.name,
                    message="Smoke test passed",
                    test_output=data.get("result", ""),
                )
            else:
                return ToolCreationResult(
                    success=False, tool_name=request.name,
                    message=data.get("error", "Unknown error"),
                    test_output=output,
                )
        except (json.JSONDecodeError, IndexError):
            if "Error" not in output and "Traceback" not in output:
                return ToolCreationResult(
                    success=True, tool_name=request.name,
                    message="Smoke test passed (non-JSON output)",
                    test_output=output[:500],
                )
            return ToolCreationResult(
                success=False, tool_name=request.name,
                message=f"Test output: {output[:200]}",
                test_output=output,
            )

    def _register_tool(self, request: ToolCreationRequest) -> None:
        """Dynamically register the function as a callable tool."""

        # Create async wrapper
        namespace: dict[str, Any] = {}
        exec(request.code, namespace)
        func = namespace.get(request.name)

        if func is None:
            raise ValueError(f"Function '{request.name}' not found in code")

        tool_registry.register(
            name=request.name,
            description=request.description,
            parameters=request.parameters,
            func=func,
        )

    def list_self_created_tools(self) -> list[str]:
        """List tools that were created at runtime (not built-in)."""
        builtins = {
            "read_file", "write_file", "edit_file", "run_command",
            "web_search", "fetch_url", "browser_navigate", "browser_screenshot",
            "browser_click", "browser_type", "browser_extract_links", "browser_extract_text",
            "store_memory", "search_memories", "remember_user_fact",
        }
        return [
            t.name for t in tool_registry.list_tools()
            if t.name not in builtins
        ]


import json  # noqa: E402

_extender: ToolSelfExtender | None = None


def get_tool_extender() -> ToolSelfExtender:
    global _extender
    if _extender is None:
        _extender = ToolSelfExtender()
    return _extender
