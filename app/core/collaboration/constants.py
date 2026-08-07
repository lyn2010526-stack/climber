"""Constants for group collaboration engine."""

from collections.abc import Callable
from typing import Any

# Task execution timeout (seconds)
TASK_TIMEOUT: int = 300

# Maximum retry attempts for agent execution
MAX_RETRIES: int = 2

# Model fallback mapping for degradation
FALLBACK_MODELS: dict[str, tuple[str, str]] = {
    "gpt-4o": ("openai", "gpt-4o-mini"),
    "claude-3-5-sonnet": ("anthropic", "claude-3-haiku"),
    "gemini-1.5-pro": ("google", "gemini-1.5-flash"),
    "step-2": ("stepfun", "step-1-8k"),
}

# Registry for Python callable callbacks (step and task callbacks)
CALLBACK_REGISTRY: dict[str, Callable[..., Any]] = {}


def register_callback(name: str, fn: Callable[..., Any]) -> None:
    """Register a named callback for use as step_callback or task_callback.

    Args:
        name: The callback name.
        fn: The callable to register.
    """
    CALLBACK_REGISTRY[name] = fn
