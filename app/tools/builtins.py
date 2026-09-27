"""Built-in tools that come with the agent engine."""

from __future__ import annotations

import ast
import importlib
import json
import math
import re
import shutil
import subprocess
import urllib.parse
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select

from app.core.di import resolve as di_resolve
from app.tools import redact_error_text, tool
from app.utils.ssrf import blocked_reason

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
        if isinstance(node, ast.Name) and node.id not in _SAFE_EVAL_BUILTINS and node.id not in local_vars:
            raise ValueError(f"Unsupported name in math expression: {node.id}")
    return eval(compile(tree, "<calculator>", "eval"), {"__builtins__": _SAFE_EVAL_BUILTINS}, local_vars)

# Register browser tools so they are available in the tool registry
# (native_tools registers screen/browser-style tools and lives in this package too)
importlib.import_module("app.tools.browser_tools")

# Absolute paths of the external binaries used below, resolved once so a
# writable PATH entry ahead of the real binary cannot substitute another
# executable. None means "unavailable" and the call is skipped.
_PATCH_BIN: str | None = shutil.which("patch")
_DOCKER_BIN: str | None = shutil.which("docker")


@tool(description="Get the current date and time")
async def get_datetime() -> str:
    return datetime.now(UTC).isoformat()


@tool(description="Fetch content from a URL")
async def fetch_url(url: str) -> str:
    try:
        reason = blocked_reason(url)
        if reason is not None:
            return f"Error fetching URL: request blocked by SSRF protection ({reason})"
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            resp = await client.get(url, headers={"User-Agent": "AgentEngine/0.1"})
            resp.raise_for_status()
            text = resp.text[:5000]
            return f"URL: {url}\nStatus: {resp.status_code}\n\n{text}"
    except Exception as e:
        return f"Error fetching URL: {redact_error_text(e)}"


@tool(description="Search the web for current information, news, facts, or documentation. Use when the user asks about recent events, current data, or information you don't know. Returns text snippets from search results.")
async def web_search(query: str) -> str:
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        # Certificate verification stays on. A previous fallback retried with
        # verify=False, which turned any TLS error into a full downgrade and let
        # a network attacker read and rewrite search results.
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            text = resp.text
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()[:3000]
        return f"Search results for: {query}\n\n{text}"
    except Exception as e:
        return f"Search error: {redact_error_text(e)}"


@tool(description="Evaluate mathematical expressions and calculations. Supports +, -, *, /, ^ (power), %, sqrt(), sin(), cos(), tan(), log(), pow(), pi, e, and comparison operators.")
async def calculator(expression: str) -> str:
    try:
        expression = expression.replace("^", "**")
        allowed = set("0123456789+-*/(). %,<>=!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
        if not all(c in allowed for c in expression):
            return "Error: Only math operators and functions allowed"
        result = _safe_eval_math(expression, {})
        return str(result)
    except Exception as e:
        return f"Error: {redact_error_text(e)}"


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
        return f"Weather error: {redact_error_text(e)}"


@tool(description="Read content from a file on the local filesystem. Use when the user wants to view, analyze, or reference an existing file. Returns up to 10,000 characters.")
async def read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        return content[:10000]
    except Exception as e:
        return f"Error reading file: {redact_error_text(e)}"


@tool(description="Write content to a file on the local filesystem. Use when the user wants to create a new file or overwrite an existing one. Automatically creates parent directories if needed.")
async def write_file(path: str, content: str) -> str:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {path}"
    except Exception as e:
        return f"Error writing file: {redact_error_text(e)}"


@tool(description="List files in a directory")
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
        return f"Error listing directory: {redact_error_text(e)}"


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
        return f"Image generation error: {redact_error_text(e)}"


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
        return f"Translation error: {redact_error_text(e)}"


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
        return f"Wikipedia error: {redact_error_text(e)}"


@tool(description="Shorten a long text to a summary")
async def summarize(text: str, max_sentences: int = 3) -> str:
    """Simple extractive summarization."""
    try:
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        selected = sentences[:max_sentences]
        return ". ".join(selected) + "."
    except Exception as e:
        return f"Summary error: {redact_error_text(e)}"


@tool(description="Encode/decode base64")
async def base64_encode(text: str, decode: bool = False) -> str:
    import base64
    try:
        if decode:
            return base64.b64decode(text.encode()).decode("utf-8")
        return base64.b64encode(text.encode()).decode("utf-8")
    except Exception as e:
        return f"Base64 error: {redact_error_text(e)}"


@tool(description="Parse JSON and extract a value by key path")
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
        return f"JSON parse error: {redact_error_text(e)}"


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
        return f"Error editing file: {redact_error_text(e)}"


@tool(description="Show diff between two strings or files.")
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
        return f"Error diffing file: {redact_error_text(e)}"


@tool(description="Append content to a file.")
async def append_file(path: str, content: str) -> str:
    """Append text to a file."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Appended to {path}"
    except Exception as e:
        return f"Error appending to file: {redact_error_text(e)}"


@tool(description="Check if a file or directory exists.")
async def file_exists(path: str) -> str:
    """Check file/directory existence."""
    try:
        import os
        if os.path.exists(path):
            kind = "dir" if os.path.isdir(path) else "file"
            return f"Exists: {path} ({kind})"
        return f"Not found: {path}"
    except Exception as e:
        return f"Error checking path: {redact_error_text(e)}"


@tool(description="Get file size and metadata.")
async def file_info(path: str) -> str:
    """Get file metadata."""
    try:
        import os
        stat = os.stat(path)
        return (
            f"Path: {path}\n"
            f"Size: {stat.st_size:,} bytes\n"
            f"Modified: {datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()}\n"
            f"Permissions: {oct(stat.st_mode)}"
        )
    except Exception as e:
        return f"Error getting file info: {redact_error_text(e)}"


def _get_group_engine():
    from app.core.group_collaboration import get_group_collaboration_engine

    return get_group_collaboration_engine()


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
        return f"Handoff failed: {redact_error_text(e)}"


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
        return f"Group task execution failed: {redact_error_text(e)}"


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
        import tempfile

        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist"

        if _PATCH_BIN is None:
            return "Error applying patch: patch utility not found in PATH"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as pf:
            pf.write(patch)
            patch_file = pf.name

        try:
            # S603 audit: argv is a fixed literal list plus the tool's own
            # arguments; file_path arrives as a separate argv element, so an
            # agent cannot inject extra patch options, and the diff travels
            # through a private temp file rather than the command line.
            result = subprocess.run(  # noqa: S603  # argv[0] is an absolute path from shutil.which()
                [_PATCH_BIN, "-p1", "--dry-run", "-i", patch_file, file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return f"Patch dry-run failed:\n{result.stderr}"

            result = subprocess.run(  # noqa: S603  # argv[0] is an absolute path from shutil.which()
                [_PATCH_BIN, "-p1", "-i", patch_file, file_path],
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
        return f"Error applying patch: {redact_error_text(e)}"


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
        return f"Error executing command: {redact_error_text(e)}"


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
    try:
        if _DOCKER_BIN is None:
            return "Error: Docker is not installed or not in PATH"

        full_cmd = [_DOCKER_BIN, "exec"]
        if workdir:
            full_cmd.extend(["-w", workdir])
        full_cmd.extend([container, "sh", "-c", command])

        # S603 audit: each variable stays one argv element, so container and
        # workdir cannot smuggle extra docker flags. `command` is intentionally
        # a shell string executed *inside* the container, which is why this tool
        # is classified as a command tool in core/engine/validation.py.
        result = subprocess.run(  # noqa: S603  # argv[0] is an absolute path from shutil.which()
            full_cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout or "(no output)"
        return f"Container exec failed (exit {result.returncode}):\n{result.stderr}"
    except FileNotFoundError:
        return "Error: Docker is not installed or not in PATH"
    except Exception as e:
        return f"Error executing in container: {redact_error_text(e)}"


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
            from app.tools import get_tool_registry
            # A fresh ToolRegistry() here would be empty, so the decomposer
            # agent would have no tools at all. Use the populated global.
            engine = AgentEngine(model_registry, get_tool_registry())
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
            return f"LLM decomposition failed: {redact_error_text(e)}"

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
        return f"Failed to parse decomposition plan: {redact_error_text(e)}\nRaw response: {response_text}"
    except Exception as e:
        return f"Auto-decomposition failed: {redact_error_text(e)}"


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
        return f"Error analyzing error: {redact_error_text(e)}"


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
        return f"Error suggesting fix: {redact_error_text(e)}"


# --- Self-editing core memory tools (Letta-style) ---
# The target user/agent is resolved from a server-side contextvar bound by the
# engine before the iteration loop (see app/core/memory_context.py). The model
# supplies only label/text, so it cannot redirect a write into another user's
# or agent's memory. Blocks flagged read_only are never mutated.


def _core_memory_scope_or_error() -> tuple[str, str] | str:
    """Resolve (user_id, agent_id) from server-side context, or an error str."""
    from app.core.memory_context import get_memory_scope

    user_id, agent_id = get_memory_scope()
    if not user_id:
        return "Error: no active user memory scope (cannot persist memory)"
    return user_id, agent_id or ""


@tool(
    description="Append a note to a persistent core memory block for this user/agent. "
    "Use to remember durable facts about the user, preferences, or project state. "
    "Creates the block if it does not exist. Never store secrets, tokens, or credentials.",
    parameters={
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "Memory block label (e.g. 'persona', 'user_profile', 'project')"},
            "text": {"type": "string", "description": "Text to append to the block"},
        },
        "required": ["label", "text"],
    },
)
async def core_memory_append(label: str, text: str) -> str:
    """Append text to a core memory block for the current user/agent."""
    try:
        scope = _core_memory_scope_or_error()
        if isinstance(scope, str):
            return scope
        user_id, agent_id = scope
        if not label.strip():
            return "Error: label must not be empty"
        if not text.strip():
            return "Error: text must not be empty"
        from app.core.core_memory import core_memory

        block = await core_memory.append_block(
            user_id=user_id, label=label.strip(), text=text.strip(), agent_id=agent_id or None
        )
        if block is None:
            return f"Error: could not append to block '{label}'"
        if block.read_only:
            return f"Block '{label}' is read-only; not modified"
        return f"Appended to core memory block '{label}' (now {len(block.value)} chars)"
    except Exception as e:
        return f"Error appending core memory: {redact_error_text(e)}"


@tool(
    description="Record a durable lesson learned from this task (a mistake fixed, a "
    "gotcha discovered, a workflow that worked). Lessons are injected back into future "
    "sessions only when they keyword-match the user's request. Keep it one crisp, "
    "actionable sentence. Never store secrets or credentials.",
    parameters={
        "type": "object",
        "properties": {
            "lesson": {"type": "string", "description": "One actionable lesson sentence"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional keyword tags improving future retrieval",
            },
        },
        "required": ["lesson"],
    },
)
async def save_lesson(lesson: str, tags: list[str] | None = None) -> str:
    """Persist a lesson as an episodic memory (memory_type='lesson')."""
    try:
        scope = _core_memory_scope_or_error()
        if isinstance(scope, str):
            return scope
        user_id, agent_id = scope
        if not lesson.strip():
            return "Error: lesson must not be empty"
        from app.core.persistent_memory import persistent_memory

        mem = await persistent_memory.create_episodic_memory(
            user_id=user_id,
            content=lesson.strip(),
            agent_id=agent_id or None,
            memory_type="lesson",
            importance=0.7,
            tags=[t.strip() for t in (tags or []) if t.strip()],
        )
        return f"Lesson saved (id={mem.id}); it will resurface when a future request matches it."
    except Exception as e:
        return f"Error saving lesson: {redact_error_text(e)}"


@tool(
    description="Replace old_text with new_text inside a persistent core memory block. "
    "Use to correct or update an existing remembered fact. Only edits the block for this "
    "user/agent; read-only blocks are never modified.",
    parameters={
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "Memory block label to edit"},
            "old_text": {"type": "string", "description": "Exact substring to replace"},
            "new_text": {"type": "string", "description": "Replacement text"},
        },
        "required": ["label", "old_text", "new_text"],
    },
)
async def core_memory_replace(label: str, old_text: str, new_text: str) -> str:
    """Replace a substring inside a core memory block for the current user/agent."""
    try:
        scope = _core_memory_scope_or_error()
        if isinstance(scope, str):
            return scope
        user_id, agent_id = scope
        if not label.strip():
            return "Error: label must not be empty"
        if not old_text:
            return "Error: old_text must not be empty"
        from app.core.core_memory import core_memory

        block = await core_memory.replace_in_block(
            user_id=user_id,
            label=label.strip(),
            old_text=old_text,
            new_text=new_text,
            agent_id=agent_id or None,
        )
        if block is None:
            return f"Error: block '{label}' not found"
        if block.read_only:
            return f"Block '{label}' is read-only; not modified"
        return f"Updated core memory block '{label}' (now {len(block.value)} chars)"
    except Exception as e:
        return f"Error editing core memory: {redact_error_text(e)}"


@tool(
    description="Run a real numerical experiment (1-D heat conduction, damped driven "
    "oscillator, or logistic growth) and return the measured outcome as JSON. Use it "
    "to test a physical or dynamical hypothesis numerically before committing to it.",
    parameters={
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "description": "Which model to run: heat, oscillator, or logistic",
            },
            "alpha": {"type": "number", "description": "Heat: thermal diffusivity"},
            "dx": {"type": "number", "description": "Heat: grid spacing"},
            "dt": {"type": "number", "description": "Time step (all models)"},
            "t_final": {"type": "number", "description": "Final simulated time"},
            "n_points": {"type": "number", "description": "Heat: grid points"},
            "source_temp": {"type": "number", "description": "Heat: source temperature"},
            "ambient_temp": {"type": "number", "description": "Heat: ambient temperature"},
            "mass": {"type": "number", "description": "Oscillator: mass"},
            "stiffness": {"type": "number", "description": "Oscillator: stiffness"},
            "damping": {"type": "number", "description": "Oscillator: damping coefficient"},
            "drive_force": {"type": "number", "description": "Oscillator: driving force"},
            "drive_freq": {"type": "number", "description": "Oscillator: driving frequency"},
            "growth_rate": {"type": "number", "description": "Logistic: intrinsic growth rate"},
            "initial_population": {"type": "number", "description": "Logistic: starting population"},
            "carrying_capacity": {"type": "number", "description": "Logistic: carrying capacity"},
        },
        "required": ["model"],
    },
)
async def simulate_experiment(
    model: str,
    alpha: float = 1e-4,
    dx: float = 0.02,
    dt: float = 1e-4,
    t_final: float = 5.0,
    n_points: int | None = None,
    source_temp: float | None = None,
    ambient_temp: float | None = None,
    mass: float = 1.0,
    stiffness: float = 1.0,
    damping: float = 0.1,
    drive_force: float = 0.5,
    drive_freq: float = 1.0,
    growth_rate: float = 0.5,
    initial_population: float = 10.0,
    carrying_capacity: float = 100.0,
) -> str:
    """Run a numerical experiment and return its JSON result.

    Args:
        model: One of heat, oscillator, logistic.
        alpha: Thermal diffusivity for the heat model.
        dx: Grid spacing for the heat model.
        dt: Time step shared by all models.
        t_final: Final simulated time.
        n_points: Grid point count for the heat model.
        source_temp: Source temperature for the heat model.
        ambient_temp: Ambient temperature for the heat model.
        mass: Mass for the oscillator model.
        stiffness: Stiffness for the oscillator model.
        damping: Damping coefficient for the oscillator model.
        drive_force: Driving force for the oscillator model.
        drive_freq: Driving frequency for the oscillator model.
        growth_rate: Intrinsic growth rate for the logistic model.
        initial_population: Starting population for the logistic model.
        carrying_capacity: Carrying capacity for the logistic model.

    Returns:
        A JSON string with the model, whether it converged, and the measured
        quantities that model reports.
    """
    params: dict[str, Any] = {"dt": dt, "t_final": t_final}
    if model == "heat":
        params.update({
            "alpha": alpha,
            "dx": dx,
            "n_points": int(n_points) if n_points else 200,
            "source_temp": 100.0 if source_temp is None else source_temp,
            "ambient_temp": 20.0 if ambient_temp is None else ambient_temp,
        })
    elif model == "oscillator":
        params.update({
            "mass": mass,
            "stiffness": stiffness,
            "damping": damping,
            "drive_force": drive_force,
            "drive_freq": drive_freq,
        })
    elif model == "logistic":
        params.update({
            "growth_rate": growth_rate,
            "initial_population": initial_population,
            "carrying_capacity": carrying_capacity,
        })
    try:
        from app.simulation.experiments import run_experiment

        return run_experiment(model, **params)
    except Exception as e:
        return f"Error running experiment: {redact_error_text(e)}"
