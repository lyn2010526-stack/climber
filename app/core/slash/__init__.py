"""Chat slash commands: parsing, validation, and session-level control.

Public surface:
- :func:`parse_input` / :class:`CommandRegistry` — pure parsing (``specs``);
- :data:`default_registry` — the built-in command set (``registry``);
- :class:`SlashCommandService` — execution orchestration (``service``).
"""

from __future__ import annotations

from app.core.slash.registry import build_default_registry, default_registry
from app.core.slash.service import (
    SlashCommandService,
    SlashExecution,
    SlashReply,
    last_user_message,
)
from app.core.slash.specs import (
    COMMAND_PREFIX,
    REASONING_LEVELS,
    ArgSpec,
    CommandRegistry,
    ParseOutcome,
    SlashCommandError,
    SlashCommandSpec,
    command_catalog,
    parse_input,
)

__all__ = [
    "COMMAND_PREFIX",
    "REASONING_LEVELS",
    "ArgSpec",
    "CommandRegistry",
    "ParseOutcome",
    "SlashCommandError",
    "SlashCommandService",
    "SlashCommandSpec",
    "SlashExecution",
    "SlashReply",
    "build_default_registry",
    "command_catalog",
    "default_registry",
    "last_user_message",
    "parse_input",
]
