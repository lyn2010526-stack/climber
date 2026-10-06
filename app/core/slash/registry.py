"""The built-in chat slash command registry.

One canonical instance (``default_registry``) shared by the API routes and any
future embedding. Command *execution* never lives here — see ``service.py``.
"""

from __future__ import annotations

from app.core.slash.specs import (
    REASONING_LEVELS,
    ArgSpec,
    CommandRegistry,
    SlashCommandSpec,
)

__all__ = ["REASONING_LEVELS", "build_default_registry", "default_registry"]


def build_default_registry() -> CommandRegistry:
    """Construct a fresh registry containing every built-in command."""
    registry = CommandRegistry()
    registry.register(
        SlashCommandSpec(
            name="help",
            summary="Show available slash commands and usage.",
            usage="/help [command]",
            args=(
                ArgSpec(
                    name="command",
                    required=False,
                    greedy=True,
                    description="Show detailed usage for one command",
                ),
            ),
        )
    )
    registry.register(
        SlashCommandSpec(
            name="model",
            summary="Show or switch the session model (provider:model_id).",
            usage="/model [provider:model_id]",
            args=(
                ArgSpec(
                    name="model_spec",
                    required=False,
                    description="provider:model_id, e.g. openai:gpt-4o-mini",
                ),
            ),
        )
    )
    registry.register(
        SlashCommandSpec(
            name="level",
            summary="Show or set the reasoning level for this session.",
            usage=f"/level [{'|'.join(REASONING_LEVELS)}]",
            args=(
                ArgSpec(
                    name="level",
                    required=False,
                    choices=REASONING_LEVELS,
                    description="Reasoning strategy",
                ),
            ),
        )
    )
    registry.register(
        SlashCommandSpec(
            name="clear",
            summary="Clear all messages in the current session.",
            usage="/clear",
        )
    )
    registry.register(
        SlashCommandSpec(
            name="retry",
            summary="Re-run the last user message as a fresh streaming turn.",
            usage="/retry",
            streaming=True,
        )
    )
    registry.register(
        SlashCommandSpec(
            name="stop",
            aliases=("cancel",),
            summary="Interrupt the turn that is currently running.",
            usage="/stop",
            allowed_while_streaming=True,
        )
    )
    registry.register(
        SlashCommandSpec(
            name="status",
            summary="Show session status, model, iteration and token counters.",
            usage="/status",
        )
    )
    return registry


default_registry = build_default_registry()
