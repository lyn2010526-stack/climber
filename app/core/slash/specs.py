"""Slash command specifications and the built-in command registry.

Pure data + validation rules: no FastAPI, no storage, no engine imports, so the
registry is trivially unit-testable. HTTP wiring lives in
``app.api.v1.routes.chat_commands``; execution orchestration lives in
``app.core.slash.service``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

COMMAND_PREFIX = "/"

# Reasoning levels map 1:1 onto ReasoningMode values (app/core/reasoning/base.py).
REASONING_LEVELS: tuple[str, ...] = ("auto", "tree", "deep", "debate")


class SlashCommandError(ValueError):
    """A matched command failed argument validation."""


@dataclass(frozen=True)
class ArgSpec:
    """One positional argument slot of a slash command."""

    name: str
    required: bool = False
    # When set, the raw argument must be one of these values (case-insensitive).
    choices: tuple[str, ...] | None = None
    greedy: bool = False  # consumes every remaining token (e.g. /help <command>)
    description: str = ""


@dataclass(frozen=True)
class SlashCommandSpec:
    """A registered slash command."""

    name: str
    summary: str
    usage: str
    args: tuple[ArgSpec, ...] = ()
    aliases: tuple[str, ...] = ()
    # True when executing the command streams a model turn (retry/passthrough).
    streaming: bool = False
    # Stop works while a turn is running; every other command waits for idle.
    allowed_while_streaming: bool = False

    def matches(self, token: str) -> bool:
        """Case-insensitive name/alias match for the first input token."""
        lowered = token.lower()
        return lowered in {self.name, *self.aliases}


@dataclass
class ParseOutcome:
    """Result of parsing one user input string.

    kind:
      - "command": a registered command matched; ``args`` validated.
      - "passthrough": not a command; the raw input goes to the agent verbatim.
      - "error": the command matched but arguments are invalid. Deliberately
        *not* passed through — "/clear all" must never reach the model.
    """

    kind: str
    raw: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    error: str | None = None
    spec: SlashCommandSpec | None = None

    @property
    def is_command(self) -> bool:
        return self.kind == "command"


class CommandRegistry:
    """Name-keyed registry of slash command specs."""

    def __init__(self) -> None:
        self._commands: dict[str, SlashCommandSpec] = {}

    def register(self, spec: SlashCommandSpec) -> None:
        keys = [spec.name, *spec.aliases]
        for key in keys:
            if key in self._commands:
                raise SlashCommandError(f"Duplicate slash command: {key}")
        for key in keys:
            self._commands[key] = spec

    def get(self, name: str) -> SlashCommandSpec | None:
        """Lookup by name or alias, case-insensitive."""
        return self._commands.get(name.lower())

    def all_commands(self) -> list[SlashCommandSpec]:
        """Unique command specs in registration order (aliases deduplicated)."""
        seen: set[str] = set()
        ordered: list[SlashCommandSpec] = []
        for spec in self._commands.values():
            if spec.name in seen:
                continue
            seen.add(spec.name)
            ordered.append(spec)
        return ordered


def _validate_args(spec: SlashCommandSpec, tokens: list[str]) -> list[str]:
    """Validate raw tokens against the spec and return normalized args."""
    positional = tuple(a for a in spec.args if not a.greedy)
    greedy = next((a for a in spec.args if a.greedy), None)

    if greedy is None:
        if len(tokens) > len(positional):
            raise SlashCommandError(
                f"Command /{spec.name} accepts no more than {len(positional)} argument(s)"
            )
    else:
        required_count = sum(1 for a in positional if a.required)
        if len(tokens) < required_count:
            raise SlashCommandError(f"Missing required argument for /{spec.name}")

    if greedy is None and any(a.required for a in positional) and len(tokens) < len(positional):
        missing = positional[len(tokens)]
        raise SlashCommandError(f"Missing required argument <{missing.name}> for /{spec.name}")

    normalized: list[str] = []
    for index, arg_spec in enumerate(positional):
        if index >= len(tokens):
            break
        value = tokens[index]
        if arg_spec.choices is not None:
            lowered = value.lower()
            if lowered not in arg_spec.choices:
                raise SlashCommandError(
                    f"Invalid value '{value}' for <{arg_spec.name}>; "
                    f"expected one of: {', '.join(arg_spec.choices)}"
                )
            value = lowered
        normalized.append(value)
    if greedy is not None and len(tokens) > len(positional):
        normalized.append(" ".join(tokens[len(positional) :]).strip())
    return normalized


def parse_input(raw: str, registry: CommandRegistry) -> ParseOutcome:
    """Parse one chat input into a command, an error, or a passthrough.

    Only an *exact first-token match* against the registry triggers command
    handling. Free text that merely starts with "/" — a file path, a fraction,
    code — is passed through untouched.
    """
    text = (raw or "").strip()
    if not text.startswith(COMMAND_PREFIX):
        return ParseOutcome(kind="passthrough", raw=raw)

    stripped = text[len(COMMAND_PREFIX) :]
    if not stripped:
        # A bare "/" is not a command anyone registered; let the agent answer.
        return ParseOutcome(kind="passthrough", raw=raw)

    tokens = stripped.split()
    head = tokens[0].lower()
    spec = registry.get(head)

    if spec is None:
        return ParseOutcome(kind="passthrough", raw=raw)

    try:
        args = _validate_args(spec, tokens[1:])
    except SlashCommandError as exc:
        return ParseOutcome(kind="error", raw=raw, command=spec.name, error=str(exc), spec=spec)

    return ParseOutcome(kind="command", raw=raw, command=spec.name, args=args, spec=spec)


def command_catalog(registry: CommandRegistry) -> list[dict[str, Any]]:
    """JSON-ready command metadata for the frontend autocomplete palette."""
    catalog: list[dict[str, Any]] = []
    for spec in registry.all_commands():
        catalog.append(
            {
                "name": spec.name,
                "aliases": list(spec.aliases),
                "summary": spec.summary,
                "usage": spec.usage,
                "streaming": spec.streaming,
                "allowed_while_streaming": spec.allowed_while_streaming,
                "args": [
                    {
                        "name": arg.name,
                        "required": arg.required,
                        "choices": list(arg.choices) if arg.choices else None,
                        "description": arg.description,
                    }
                    for arg in spec.args
                ],
            }
        )
    return catalog
