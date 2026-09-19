"""Contained file operations, not an OS/process sandbox.

Use a dedicated workspace without concurrent untrusted filesystem writers.
Resolve checks cannot prevent a concurrent symlink replacement race.
"""

import os
import signal
import subprocess
from contextlib import suppress
from pathlib import Path

COMMAND_OUTPUT_LIMIT = 8000

_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "SHELL",
    "USER",
    "LOGNAME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LC_MESSAGES",
    "LC_COLLATE",
    "LC_NUMERIC",
    "LC_TIME",
    "TMPDIR",
    "TEMP",
    "TERM",
    "TZ",
    "NODE_ENV",
)


class WorkspaceSandbox:
    def __init__(
        self,
        root: str | Path,
        max_bytes: int = 65536,
        allow_commands: bool = False,
        command_timeout: float = 120,
        command_env: dict[str, str] | None = None,
    ):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Workspace must be a directory")
        self.max_bytes = max_bytes
        self.allow_commands = bool(allow_commands)
        self.command_timeout = float(command_timeout)
        self.command_env = dict(command_env or {})
        self.spawned_pgids: set[int] = set()

    def resolve(self, path: str) -> Path:
        if not isinstance(path, str) or not path or Path(path).is_absolute():
            raise ValueError("Expected a nonempty relative path")
        candidate = (self.root / path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Path escapes workspace")
        if any(part == ".git" or part.startswith(".env") for part in candidate.relative_to(self.root).parts):
            raise ValueError("Protected workspace path")
        return candidate

    def execute(self, name: str, arguments: dict) -> dict:
        if name == "run_command":
            if not self.allow_commands:
                raise ValueError("Tool disabled or unknown; command execution is unavailable")
            return self._run_command(arguments)
        if name not in {"read_file", "write_file", "list_files"}:
            raise ValueError("Tool disabled or unknown; command execution is unavailable")
        expected = {"path", "content"} if name == "write_file" else {"path"}
        if set(arguments) != expected:
            raise ValueError("Invalid tool arguments")
        path = self.resolve(arguments["path"])
        if name == "list_files":
            entries = []
            for child in path.iterdir():
                if len(entries) >= 500:
                    raise ValueError("Directory exceeds 500 entries")
                try:
                    self.resolve(str(child.relative_to(self.root)))
                except ValueError:
                    continue
                entries.append(child.name + ("/" if child.is_dir() else ""))
            return {"entries": sorted(entries)}
        if name == "read_file":
            if not path.is_file():
                raise ValueError("Expected a regular file")
            with path.open("rb") as stream:
                data = stream.read(self.max_bytes + 1)
            if len(data) > self.max_bytes:
                raise ValueError("File exceeds byte limit")
            return {"content": data.decode("utf-8")}
        content = arguments["content"]
        if not isinstance(content, str) or len(content.encode("utf-8")) > self.max_bytes:
            raise ValueError("Content must be text within byte limit")
        if path.exists() and (not path.is_file() or path.stat().st_nlink > 1):
            raise ValueError("Expected a regular file with one hard link")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"written_bytes": len(content.encode("utf-8"))}

    def _sandbox_env(self) -> dict:
        env = {}
        for key in _ENV_ALLOWLIST:
            if key in os.environ:
                env[key] = os.environ[key]
        for key, value in os.environ.items():
            if key.startswith("npm_config_") and "auth" not in key.lower():
                env[key] = value
        env.update(self.command_env)
        return env

    def _run_command(self, arguments: dict) -> dict:
        if set(arguments) != {"command"}:
            raise ValueError("Invalid tool arguments")
        command = arguments["command"]
        if not isinstance(command, str) or not command.strip() or len(command) > 8000:
            raise ValueError("Command must be nonempty text within 8000 characters")
        env = self._sandbox_env()
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(self.root),
            env=env,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        self.spawned_pgids.add(process.pid)
        timed_out = False
        try:
            output, _ = process.communicate(timeout=self.command_timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        output = output or ""
        if len(output) > COMMAND_OUTPUT_LIMIT:
            output = "[truncated]\n" + output[-COMMAND_OUTPUT_LIMIT:]
        exit_code = process.returncode if not timed_out else -1
        if timed_out:
            output += f"\n[command killed after {self.command_timeout}s timeout]"
        return {"exit_code": exit_code, "output": output}

    @property
    def tools(self) -> list:
        return TOOLS + [COMMAND_TOOL] if self.allow_commands else TOOLS


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }
    for name, description, properties in [
        ("list_files", "List one directory, using . for root", {"path": {"type": "string"}}),
        ("read_file", "Read a UTF-8 file", {"path": {"type": "string"}}),
        ("write_file", "Write a UTF-8 file", {"path": {"type": "string"}, "content": {"type": "string"}}),
    ]
]

COMMAND_TOOL = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": "Run one shell command in the workspace root and return exit code plus output",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}
