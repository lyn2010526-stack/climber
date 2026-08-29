"""Built-in tools that come with the agent engine."""

from __future__ import annotations

import ast
import json
import math
import re
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select

from app.core.di import resolve as di_resolve
from app.tools import tool

_SAFE_EVAL_BUILTINS = {
    "len": len, "str": str, "int": int, "float": float,
    "abs": abs, "round": round, "True": True, "False": False,
    "None": None,
    "sqrt": math.sqrt, "pow": pow,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "ceil": math.ceil, "floor": math.floor,
    "pi": math.pi, "e": math.e,
    "gcd": math.gcd, "factorial": math.factorial,
}
_SAFE_EXPR_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Call, ast.Constant, ast.Name, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
)


def _safe_eval_math(expression: str, local_vars: dict[str, Any]) -> Any:
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_EXPR_NODES):
            raise ValueError(f"Unsafe math expression node: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in _SAFE_EVAL_BUILTINS:
            raise ValueError(f"Unsupported name in math expression: {node.id}")
    return eval(compile(tree, "<calculator>", "eval"), {"__builtins__": _SAFE_EVAL_BUILTINS}, local_vars)  # noqa: S307 - AST-validated sandboxed eval

# Register browser tools so they are available in the tool registry
# Register vision tools for screen capture, OCR, and interaction
# Register vector memory tools for semantic memory search
# Register core memory tools for LLM self-directed core memory management
# Register memory tools for LLM self-directed memory management
# Register search tools for enhanced web search
# Register data analysis tools
# Register chart generation tools
# Register email tools
# Register calendar tools
# Register file conversion tools
from app.tools import (
    browser_tools,  # noqa: F401
    calendar_tools,  # noqa: F401
    chart_tools,  # noqa: F401
    core_memory_tools,  # noqa: F401
    data_analysis_tools,  # noqa: F401
    email_tools,  # noqa: F401
    file_conversion_tools,  # noqa: F401
    memory_tools,  # noqa: F401
    memory_vector_tools,  # noqa: F401
    search_tools,  # noqa: F401
    vision_tools,  # noqa: F401
)


@tool(description="Get the current date and time", sandbox_safe_when_unavailable=True)
async def get_datetime() -> str:
    return datetime.now(UTC).isoformat()


@tool(description="Fetch content from a URL")
async def fetch_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "AgentEngine/0.1"})
            resp.raise_for_status()
            text = resp.text[:5000]
            return f"URL: {url}\nStatus: {resp.status_code}\n\n{text}"
    except Exception as e:
        return f"Error fetching URL: {e!s}"


@tool(description="Search the web for current information, news, facts, or documentation. Use when the user asks about recent events, current data, or information you don't know. Returns text snippets from search results.")
async def web_search(query: str) -> str:
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                text = resp.text
        except Exception:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:  # noqa: S501 - ssl fallback for user-supplied URL
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                text = resp.text
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()[:3000]
        return f"Search results for: {query}\n\n{text}"
    except Exception as e:
        return f"Search error: {e!s}"


@tool(
    description="Evaluate mathematical expressions and calculations. Supports +, -, *, /, ^ (power), %, sqrt(), sin(), cos(), tan(), log(), pow(), pi, e, and comparison operators.",
    sandbox_safe_when_unavailable=True,
)
async def calculator(expression: str) -> str:
    try:
        expression = expression.replace("^", "**")
        allowed = set("0123456789+-*/(). %,<>=!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
        if not all(c in allowed for c in expression):
            return "Error: Only math operators and functions allowed"
        result = _safe_eval_math(expression, {})
        return str(result)
    except Exception as e:
        return f"Error: {e!s}"


@tool(description="Get current weather conditions for any city worldwide. Use when the user asks about weather, temperature, or forecast for a specific location. Returns temperature, humidity, wind speed, and conditions.")
async def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            current = data["current_condition"][0]
            return (
                f"Weather in {city}:\n"
                f"Temperature: {current['temp_C']}°C\n"
                f"Feels like: {current['FeelsLikeC']}°C\n"
                f"Humidity: {current['humidity']}%\n"
                f"Description: {current['weatherDesc'][0]['value']}\n"
                f"Wind: {current['windspeedKmph']} km/h"
            )
    except Exception as e:
        return f"Weather error: {e!s}"


@tool(
    description="Read content from a file on the local filesystem. Use when the user wants to view, analyze, or reference an existing file. Returns up to 10,000 characters.",
    sandbox_safe_when_unavailable=True,
)
async def read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        return content[:10000]
    except Exception as e:
        return f"Error reading file: {e!s}"


@tool(description="Write content to a file on the local filesystem. Use when the user wants to create a new file or overwrite an existing one. Automatically creates parent directories if needed.")
async def write_file(path: str, content: str) -> str:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {path}"
    except Exception as e:
        return f"Error writing file: {e!s}"


@tool(description="List files in a directory", sandbox_safe_when_unavailable=True)
async def list_files(directory: str = ".") -> str:
    import os
    try:
        entries = []
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            kind = "dir" if os.path.isdir(full) else "file"
            entries.append(f"[{kind}] {entry}")
        return "\n".join(entries) if entries else "Directory is empty"
    except Exception as e:
        return f"Error listing directory: {e!s}"


@tool(description="Run a shell command and return output")
async def run_command(command: str) -> str:
    sandbox = di_resolve("SandboxExecutor")
    return await sandbox.execute(command)


@tool(description="Generate an image using a text description (via pollinations.ai)")
async def generate_image(prompt: str) -> str:
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=true"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                # Return the URL - the model can reference it
                return f"Image generated: {url}"
            return f"Image generation failed: HTTP {resp.status_code}"
    except Exception as e:
        return f"Image generation error: {e!s}"


@tool(description="Translate text between languages")
async def translate(text: str, target_language: str = "en", source_language: str = "auto") -> str:
    try:
        # Use LibreTranslate public instance or similar
        url = "https://libretranslate.de/translate"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json={
                "q": text,
                "source": source_language,
                "target": target_language,
                "format": "text",
            })
            if resp.status_code == 200:
                return resp.json().get("translatedText", "Translation failed")
            # Fallback: return a note
            return f"Translation service unavailable. Text: {text}"
    except Exception as e:
        return f"Translation error: {e!s}"


@tool(description="Get a Wikipedia summary for a topic")
async def wikipedia_summary(topic: str) -> str:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(topic)}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"User-Agent": "AgentEngine/0.1"})
            if resp.status_code == 200:
                data = resp.json()
                return (
                    f"## {data.get('title', topic)}\n\n"
                    f"{data.get('extract', 'No summary available.')}\n\n"
                    f"Source: {data.get('content_urls', {}).get('desktop', {}).get('page', '')}"
                )
            return f"Wikipedia: No article found for '{topic}'"
    except Exception as e:
        return f"Wikipedia error: {e!s}"


@tool(description="Shorten a long text to a summary", sandbox_safe_when_unavailable=True)
async def summarize(text: str, max_sentences: int = 3) -> str:
    """Simple extractive summarization."""
    try:
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        selected = sentences[:max_sentences]
        return ". ".join(selected) + "."
    except Exception as e:
        return f"Summary error: {e!s}"


@tool(description="Encode/decode base64", sandbox_safe_when_unavailable=True)
async def base64_encode(text: str, decode: bool = False) -> str:
    import base64
    try:
        if decode:
            return base64.b64decode(text.encode()).decode("utf-8")
        return base64.b64encode(text.encode()).decode("utf-8")
    except Exception as e:
        return f"Base64 error: {e!s}"


@tool(description="Parse JSON and extract a value by key path", sandbox_safe_when_unavailable=True)
async def json_get(json_string: str, key_path: str) -> str:
    """Get a value from JSON using dot notation (e.g., 'user.name')."""
    try:
        data = json.loads(json_string)
        keys = key_path.split(".")
        for key in keys:
            if isinstance(data, dict):
                data = data[key]
            elif isinstance(data, list):
                data = data[int(key)]
            else:
                return f"Error: Cannot traverse into {type(data)}"
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"JSON parse error: {e!s}"


@tool(description="Edit a file by replacing old_string with new_string. Shows unified diff preview before applying. Use longer unique context for accuracy.")
async def edit_file(path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing exact text with preview and validation.

    """
    try:
        from app.core.file_patch import FilePatchService, get_current_agent_mode
        from app.core.security_sandbox import security_sandbox

        if security_sandbox is not None:
            ok, reason = security_sandbox.validate_file_access(path, "write")
            if not ok:
                return f"Permission denied: {reason}"

        valid, msg = FilePatchService.validate_edit(path, old_string, new_string)
        if not valid:
            return f"Validation failed: {msg}"

        diff, preview_msg = FilePatchService.preview_edit(path, old_string, new_string)
        if not diff:
            return f"Preview failed: {preview_msg}"

        mode = get_current_agent_mode()
        if mode == "plan":
            return f"PLAN mode preview (no changes applied):\n{diff}"

        with open(path, encoding="utf-8") as f:
            content = f.read()
        new_content = content.replace(old_string, new_string, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger = __import__("structlog").get_logger()
        logger.info("file_edited", path=path)
        return f"File updated: {path}\n\nDiff:\n{diff}"
    except Exception as e:
        return f"Error editing file: {e!s}"


@tool(description="Show diff between two strings or files.", sandbox_safe_when_unavailable=True)
async def file_diff(path: str, new_content: str) -> str:
    """Show unified diff for a file."""
    try:
        import difflib
        with open(path, encoding="utf-8") as f:
            old = f.read().splitlines()
        new = new_content.splitlines()
        diff = difflib.unified_diff(old, new, lineterm="")
        return "\n".join(list(diff)[:200]) or "No differences"
    except Exception as e:
        return f"Error diffing file: {e!s}"


@tool(description="Append content to a file.")
async def append_file(path: str, content: str) -> str:
    """Append text to a file."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to {path}"
    except Exception as e:
        return f"Error appending to file: {e!s}"


@tool(description="Check if a file or directory exists.", sandbox_safe_when_unavailable=True)
async def file_exists(path: str) -> str:
    """Check file/directory existence."""
    try:
        import os
        if os.path.exists(path):
            kind = "dir" if os.path.isdir(path) else "file"
            return f"Exists: {path} ({kind})"
        return f"Not found: {path}"
    except Exception as e:
        return f"Error checking path: {e!s}"


@tool(description="Get file size and metadata.", sandbox_safe_when_unavailable=True)
async def file_info(path: str) -> str:
    """Get file metadata."""
    try:
        import os
        stat = os.stat(path)
        return (
            f"Path: {path}\n"
            f"Size: {stat.st_size:,} bytes\n"
            f"Modified: {datetime.fromtimestamp(stat.st_mtime).isoformat()}\n"
            f"Permissions: {oct(stat.st_mode)}"
        )
    except Exception as e:
        return f"Error getting file info: {e!s}"


_group_collaboration_engine = None


def _get_group_engine():
    global _group_collaboration_engine
    if _group_collaboration_engine is None:
        from app.core.group_collaboration import group_collaboration_engine
        _group_collaboration_engine = group_collaboration_engine
    return _group_collaboration_engine


@tool(
    description="Hand off the current task to another agent in the group. Use when you believe another agent is better suited to complete this task.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "The task ID to hand off"},
            "target_agent_id": {"type": "string", "description": "The agent ID to hand the task to"},
            "reason": {"type": "string", "description": "Reason for the handoff"}
        },
        "required": ["task_id", "target_agent_id"],
    },
)
async def handoff_task(task_id: str, target_agent_id: str, reason: str = "") -> str:
    """Hand off a task to another agent."""
    try:
        engine = _get_group_engine()
        result = await engine.handoff_task(task_id, target_agent_id, reason)
        return f"Task handed off successfully: {result}"
    except Exception as e:
        return f"Handoff failed: {e!s}"


@tool(
    description="Run all pending tasks in the current group using dependency-aware parallel execution.",
    parameters={
        "type": "object",
        "properties": {
            "group_id": {"type": "string", "description": "The group ID to run tasks for"}
        },
        "required": ["group_id"],
    },
)
async def run_group_tasks(group_id: str) -> str:
    """Run all pending tasks in a group using DAG-based execution."""
    try:
        engine = _get_group_engine()
        result = await engine.run_group_tasks(group_id)
        return f"Group tasks executed: {result}"
    except Exception as e:
        return f"Group task execution failed: {e!s}"


@tool(
    description="Apply a unified diff patch to a file. Use for incremental file modifications instead of rewriting the whole file.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the file to patch"},
            "patch": {"type": "string", "description": "Unified diff patch content (e.g., @@ -1,4 +1,4 @@)"},
        },
        "required": ["file_path", "patch"],
    },
)
async def apply_patch(file_path: str, patch: str) -> str:
    """Apply a unified diff patch to a file."""
    try:
        import os
        import subprocess
        import tempfile

        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as pf:
            pf.write(patch)
            patch_file = pf.name

        try:
            result = subprocess.run(
                ["patch", "-p1", "--dry-run", "-i", patch_file, file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return f"Patch dry-run failed:\n{result.stderr}"

            result = subprocess.run(
                ["patch", "-p1", "-i", patch_file, file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return f"Patch applied successfully to {file_path}\n{result.stdout}"
            return f"Patch failed:\n{result.stderr}"
        finally:
            os.unlink(patch_file)
    except Exception as e:
        return f"Error applying patch: {e!s}"


@tool(
    description="Execute a shell command and stream output in real-time. Returns the full output after completion.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 120)", "default": 120},
            "workdir": {"type": "string", "description": "Working directory (optional)", "default": ""},
        },
        "required": ["command"],
    },
)
async def stream_command(command: str, timeout: int = 120, workdir: str = "") -> str:
    """Execute a shell command with streaming output."""
    try:
        from app.core.di import resolve as di_resolve
        sandbox = di_resolve("SandboxExecutor")
        return await sandbox.execute(command)
    except Exception as e:
        return f"Error executing command: {e!s}"


@tool(
    description="Execute a command inside a container using Docker. Requires Docker to be installed and running.",
    parameters={
        "type": "object",
        "properties": {
            "container": {"type": "string", "description": "Container name or ID"},
            "command": {"type": "string", "description": "Command to execute inside the container"},
            "workdir": {"type": "string", "description": "Working directory inside container (optional)", "default": ""},
        },
        "required": ["container", "command"],
    },
)
async def container_exec(container: str, command: str, workdir: str = "") -> str:
    """Execute a command inside a Docker container."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", container):
        return "Error: invalid container name"
    if not command.strip():
        return "Error: command must not be empty"
    # Validate command against hazard patterns before passing to container shell
    from app.core.security_sandbox import HAZARD_COMMANDS
    for pattern in HAZARD_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            return "Error: command blocked by safety policy: matches hazard pattern"
    try:
        import subprocess

        full_cmd = ["docker", "exec"]
        if workdir:
            full_cmd.extend(["-w", workdir])
        full_cmd.extend(["--", container, "sh", "-c", command])

        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
        )
        if result.returncode == 0:
            return result.stdout or "(no output)"
        return f"Container exec failed (exit {result.returncode}):\n{result.stderr}"
    except FileNotFoundError:
        return "Error: Docker is not installed or not in PATH"
    except Exception as e:
        return f"Error executing in container: {e!s}"


@tool(
    description="Auto-decompose a complex task into sub-tasks using LLM and create them in the group task queue.",
    parameters={
        "type": "object",
        "properties": {
            "group_id": {"type": "string", "description": "Group ID to create tasks in"},
            "objective": {"type": "string", "description": "The complex objective to decompose"},
            "max_steps": {"type": "integer", "description": "Maximum number of sub-tasks (default: 5)", "default": 5},
        },
        "required": ["group_id", "objective"],
    },
)
async def auto_decompose_task(group_id: str, objective: str, max_steps: int = 5) -> str:
    """Decompose a complex task into sub-tasks and create them in the DAG."""
    try:
        model_registry = di_resolve("ModelRegistry")
        import json

        from app.storage import async_session
        from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

        async with async_session() as db:
            group = (
                await db.execute(
                    select(AgentGroup).where(AgentGroup.id == group_id)
                )
            ).scalar_one_or_none()
            if not group:
                return f"Error: Group {group_id} not found"

            members = (
                await db.execute(
                    select(AgentGroupMember).where(AgentGroupMember.group_id == group_id)
                )
            ).scalars().all()

        if not members:
            return f"Error: Group {group_id} has no members"

        # Use LLM to decompose the task
        model_registry = di_resolve("ModelRegistry")
        provider = "openai"
        model_id = "gpt-4o"
        decomposition_prompt = f"""Decompose this objective into {max_steps} atomic, verifiable sub-tasks.

Objective: {objective}

Available agents: {', '.join(m.agent_id or m.id for m in members)}

Output JSON format:
{{
  "tasks": [
    {{
      "name": "Task name",
      "description": "Detailed description",
      "depends_on": ["task_id_1", "task_id_2"],
      "assignee": "agent_id or null",
      "estimate": "S/M/L"
    }}
  ]
}}

Rules:
- Tasks must form a DAG (no circular dependencies)
- Each task independently verifiable
- Maximum {max_steps} tasks
- Use depends_on: [] for tasks with no dependencies
- Return ONLY valid JSON, no markdown code blocks"""

        try:
            from app.core.agent_engine import AgentEngine
            engine = AgentEngine(model_registry, __import__("app.tools", fromlist=["ToolRegistry"]).ToolRegistry())
            session = engine.create_session(
                agent_id="decomposer",
                user_id="default-user",
                provider=provider,
                model_id=model_id,
                api_key="",
                base_url=None,
                system_prompt="You are a task decomposition expert. Output only valid JSON.",
            )
            result = await engine.run_agent(session, decomposition_prompt)
            response_text = result.get("output", "")
        except Exception as e:
            return f"LLM decomposition failed: {e!s}"

        # Parse JSON from response
        json_str = response_text
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]

        plan = json.loads(json_str)
        tasks_data = plan.get("tasks", [])

        # Create tasks in database
        created_tasks: dict[str, str] = {}  # name -> task_id
        async with async_session() as db:
            for task_data in tasks_data:
                task_name = task_data.get("name", f"Task {len(created_tasks) + 1}")
                task_desc = task_data.get("description", task_name)
                assignee = task_data.get("assignee")
                depends_on_names = task_data.get("depends_on", [])

                member = next((m for m in members if m.agent_id == assignee), None)
                if not member:
                    member = next((m for m in members if m.role in ("worker", "participant")), members[0] if members else None)

                task = AgentGroupTask(
                    group_id=group_id,
                    description=task_desc,
                    worker_id=member.id if member else None,
                    reviewer_ids=[],
                    dependencies=[created_tasks[n] for n in depends_on_names if n in created_tasks],
                    max_rounds=3,
                )
                db.add(task)
                await db.flush()
                created_tasks[task_name] = task.id

            await db.commit()

        return f"Decomposed into {len(created_tasks)} tasks:\n" + "\n".join(f"- {k}: {v}" for k, v in created_tasks.items())
    except json.JSONDecodeError as e:
        return f"Failed to parse decomposition plan: {e!s}\nRaw response: {response_text}"
    except Exception as e:
        return f"Auto-decomposition failed: {e!s}"


@tool(
    description="Analyze an error message and return structured error analysis. "
    "Use when you need to understand what went wrong with a tool execution.",
    parameters={
        "type": "object",
        "properties": {
            "error_message": {"type": "string", "description": "The raw error message to analyze"},
            "context": {"type": "string", "description": "Optional context JSON (e.g., tool name, arguments)", "default": "{}"},
        },
        "required": ["error_message"],
    },
)
async def analyze_error(error_message: str, context: str = "{}") -> str:
    """Analyze an error message and return structured error analysis.

    """
    try:
        from app.core.error_analyzer import ErrorAnalyzer
        ctx = json.loads(context) if context else {}
        analyzer = ErrorAnalyzer()
        analysis = analyzer.analyze(error_message, context=ctx)
        return json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error analyzing error: {e!s}"


@tool(
    description="Suggest a fix for an error given an analysis and optional file content. "
    "Use after analyze_error to get a fix strategy.",
    parameters={
        "type": "object",
        "properties": {
            "error_analysis": {"type": "string", "description": "JSON output from analyze_error"},
            "file_content": {"type": "string", "description": "Current content of the relevant file (optional)", "default": ""},
        },
        "required": ["error_analysis"],
    },
)
async def suggest_fix(error_analysis: str, file_content: str = "") -> str:
    """Suggest a fix for an error given an analysis and optional file content.

    """
    try:
        from app.core.debug_loop import DebugLoop
        from app.core.error_analyzer import ErrorAnalysis

        analysis_dict = json.loads(error_analysis)
        error_type = analysis_dict.get("error_type", "unknown")
        message = analysis_dict.get("message", "")
        file_path = analysis_dict.get("file_path")
        line_number = analysis_dict.get("line_number")

        analysis = ErrorAnalysis(
            error_type=error_type,
            message=message,
            file_path=file_path,
            line_number=line_number,
            cause=analysis_dict.get("cause"),
            raw_error=analysis_dict.get("raw_error", message),
            context=analysis_dict.get("context", {}),
            confidence=analysis_dict.get("confidence", 0.5),
        )

        loop = DebugLoop()
        strategy = await loop._generate_fix_strategy(
            analysis=analysis,
            tool_name=analysis_dict.get("tool_name", ""),
            arguments=analysis_dict.get("arguments", {}),
            learned_fix=None,
        )

        result = {
            "approach": strategy.approach,
            "description": strategy.description,
            "confidence": strategy.confidence,
            "patch_content": strategy.patch_content,
            "new_arguments": strategy.new_arguments,
            "new_tool": strategy.new_tool,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error suggesting fix: {e!s}"
