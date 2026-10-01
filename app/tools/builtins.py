"""Built-in tools that come with the agent engine."""

from __future__ import annotations

import ast
import json
import math
import re
import urllib.parse
from datetime import datetime
from typing import Any

import httpx

from app.core.di import resolve as di_resolve
from app.core.security.network_allowlist import network_allowlist
from app.tools import native_tools, tool
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
from app.tools import browser_tools  # noqa: E402, F401


def _outbound_denial(url: str) -> str:
    """Return why an outbound request is denied, or an empty string when allowed.

    Every tool that talks to the network goes through here before opening a
    connection: the SSRF layer rejects loopback, private, link-local and cloud
    metadata destinations, and the network allowlist applies its domain policy.
    """
    reason = blocked_reason(url)
    if reason:
        return reason
    allowed, allowlist_reason = network_allowlist.check_url(url)
    if not allowed:
        return f"blocked by network allowlist: {allowlist_reason}"
    return ""


def _validated_path(path: str, writable: bool) -> tuple[bool, str]:
    """Check a filesystem path against the shared native_tools path policy.

    Accessing the validator through the module keeps the lookup dynamic and
    avoids importing a private name directly from a sibling module.
    """
    return native_tools._validate_file_path(path, writable=writable)  # noqa: SLF001


@tool(description="Get the current date and time")
async def get_datetime() -> str:
    return datetime.now().isoformat()


@tool(description="Fetch content from a URL")
async def fetch_url(url: str) -> str:
    try:
        reason = _outbound_denial(url)
        if reason:
            return f"Error fetching URL: {reason}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            current_url = url
            for redirects in range(6):
                resp = await client.get(current_url, headers={"User-Agent": "AgentEngine/0.1"})
                if not resp.has_redirect_location:
                    break
                if redirects == 5:
                    return "Error fetching URL: too many redirects (maximum 5)"
                current_url = urllib.parse.urljoin(str(resp.url), resp.headers["location"])
                reason = _outbound_denial(current_url)
                if reason:
                    return f"Error fetching URL: redirect blocked: {reason}"
            resp.raise_for_status()
            text = resp.text[:5000]
            return f"URL: {url}\nStatus: {resp.status_code}\n\n{text}"
    except httpx.TimeoutException:
        return "Error fetching URL: request timed out (15s timeout)"
    except Exception as e:
        return f"Error fetching URL: {e!s}"


@tool(description="Search the web for current information, news, facts, or documentation. Use when the user asks about recent events, current data, or information you don't know. Returns text snippets from search results.")
async def web_search(query: str) -> str:
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
        reason = _outbound_denial(url)
        if reason:
            return f"Search error: {reason}"
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            text = resp.text
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()[:3000]
        return f"Search results for: {query}\n\n{text}"
    except Exception as e:
        return f"Search error: {e!s}"


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
        return f"Error: {e!s}"


@tool(description="Get current weather conditions for any city worldwide. Use when the user asks about weather, temperature, or forecast for a specific location. Returns temperature, humidity, wind speed, and conditions.")
async def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        reason = _outbound_denial(url)
        if reason:
            return f"Weather error: {reason}"
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


@tool(description="Read content from a file on the local filesystem. Use when the user wants to view, analyze, or reference an existing file. Returns up to 10,000 characters.")
async def read_file(path: str) -> str:
    valid, reason = _validated_path(path, writable=False)
    if not valid:
        return f"Error reading file: {reason}"
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        return content[:10000]
    except Exception as e:
        return f"Error reading file: {e!s}"


@tool(description="Write content to a file on the local filesystem. Use when the user wants to create a new file or overwrite an existing one. Automatically creates parent directories if needed.")
async def write_file(path: str, content: str) -> str:
    valid, reason = _validated_path(path, writable=True)
    if not valid:
        return f"Error writing file: {reason}"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written: {path}"
    except Exception as e:
        return f"Error writing file: {e!s}"


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
        return f"Error listing directory: {e!s}"


@tool(description="Run a shell command and return output")
async def run_command(command: str) -> str:
    sandbox = di_resolve("SandboxExecutor")
    return await sandbox.execute(command)


@tool(description="Generate an image using a text description (via pollinations.ai)")
async def generate_image(prompt: str) -> str:
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=1024&nologo=true"
        reason = _outbound_denial(url)
        if reason:
            return f"Image generation error: {reason}"
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
        reason = _outbound_denial(url)
        if reason:
            return f"Translation error: {reason}"
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
        reason = _outbound_denial(url)
        if reason:
            return f"Wikipedia error: {reason}"
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


@tool(description="Shorten a long text to a summary")
async def summarize(text: str, max_sentences: int = 3) -> str:
    """Simple extractive summarization."""
    try:
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        selected = sentences[:max_sentences]
        return ". ".join(selected) + "."
    except Exception as e:
        return f"Summary error: {e!s}"


@tool(description="Encode/decode base64")
async def base64_encode(text: str, decode: bool = False) -> str:
    import base64
    try:
        if decode:
            return base64.b64decode(text.encode()).decode("utf-8")
        return base64.b64encode(text.encode()).decode("utf-8")
    except Exception as e:
        return f"Base64 error: {e!s}"


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
        return f"Error checking path: {e!s}"


@tool(description="Get file size and metadata.")
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


# Dangerous shell patterns rejected before container_exec hands a command to
# `docker exec ... sh -c`; follows the SandboxConfig.blocked_patterns style in
# app/core/sandbox.py while staying import-free to avoid DI side effects.
_CONTAINER_EXEC_BLOCKED_PATTERNS: frozenset[str] = frozenset((
    r";",                            # semicolon command chaining
    r"`",                            # backtick command substitution
    r"\$\(",                         # $() command substitution
    r"&&",                           # logical AND chaining
    r"\|\|",                         # logical OR chaining
    r"\|\s*(ba|z|da|k)?sh\b",        # piping into a shell
    r"\brm\s+(-\w+\s+)*-\w*[rR]\w*",  # recursive rm (rm -rf and friends)
    r"sudo\s+",                      # privilege escalation
    r"chmod\s+777",                  # world-writable permissions
    r"chown\s+root",                 # ownership change to root
    r"curl\s+.*\|\s*sh",             # remote script execution
    r"wget\s+.*\|\s*sh",             # remote script execution
    r"dd\s+if=",                     # raw disk writes
    r"mkfs\.",                       # filesystem creation
    r"fdisk",                        # disk partitioning
    r":\(\)\{.*\|.*\};",             # fork bomb
    r">\s*/dev/sd",                  # raw device overwrite
    r"shutdown",                     # power control
    r"reboot",                       # power control
    r"init\s+[06]",                  # runlevel switch
    r"kill\s+-9\s+1",                # killing init
))


def _container_command_blocked(command: str) -> str:
    """Return the first dangerous pattern matched by the command, or "" if safe."""
    for pattern in _CONTAINER_EXEC_BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return pattern
    return ""


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
        import subprocess

        blocked_pattern = _container_command_blocked(command)
        if blocked_pattern:
            return f"Command rejected: dangerous pattern detected ({blocked_pattern})"

        full_cmd = ["docker", "exec"]
        if workdir:
            full_cmd.extend(["-w", workdir])
        full_cmd.extend([container, "sh", "-c", command])

        result = subprocess.run(
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
        return f"Error executing in container: {e!s}"


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
    description="Run a real numerical physics/engineering experiment (heat conduction, "
    "damped oscillator, logistic growth) and return structured JSON metrics. "
    "Divergent parameter sets are reported with converged=false and NaN so the "
    "simulation harness probes can reject and auto-adjust them.",
    parameters={
        "type": "object",
        "properties": {
            "model": {
                "type": "string",
                "enum": ["heat", "oscillator", "logistic"],
                "description": "Which numerical experiment to run",
            },
            "alpha": {"type": "number", "description": "Thermal diffusivity (heat)"},
            "dx": {"type": "number", "description": "Spatial step (heat)"},
            "dt": {"type": "number", "description": "Time step (all models)"},
            "t_final": {"type": "number", "description": "Simulated duration (heat)"},
            "n_points": {"type": "integer", "description": "Spatial resolution (heat)"},
            "source_temp": {"type": "number", "description": "Boundary temperature (heat)"},
            "ambient_temp": {"type": "number", "description": "Initial temperature (heat)"},
            "mass": {"type": "number", "description": "Mass (oscillator)"},
            "stiffness": {"type": "number", "description": "Spring stiffness (oscillator)"},
            "damping": {"type": "number", "description": "Damping coefficient (oscillator)"},
            "drive_amplitude": {"type": "number", "description": "Drive amplitude (oscillator)"},
            "drive_frequency": {"type": "number", "description": "Drive frequency (oscillator)"},
            "duration": {"type": "number", "description": "Simulated duration (oscillator/logistic)"},
            "growth_rate": {"type": "number", "description": "Growth rate (logistic)"},
            "carrying_capacity": {"type": "number", "description": "Carrying capacity (logistic)"},
            "initial_population": {"type": "number", "description": "Initial population (logistic)"},
        },
        "required": ["model"],
    },
)
async def simulate_experiment(model: str, **params: Any) -> str:
    """Run a real numerical experiment; see app.simulation.experiments."""
    from app.simulation.experiments import run_experiment

    return run_experiment(model, **params)
