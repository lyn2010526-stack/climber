"""Canary tokens for detecting leaks of gated content.

Pure-function port of the rebuff SDK canary mechanism (Apache-2.0,
https://github.com/protectai/rebuff): a random token is embedded into
content as an HTML comment, and later, exact substring matching against
untrusted output reveals whether the content leaked. The leak event itself
is scored by the safety gate via ``screen(canary_leaked=True)``.

The module performs zero I/O and zero model calls; identical inputs always
produce identical outputs.
"""

from __future__ import annotations

import secrets

CANARY_TOKEN_LENGTH: int = 4


def generate_canary() -> str:
    """Return a fresh canary token with 4 bytes of entropy (8 hex chars)."""
    return f"CANARY[{secrets.token_hex(CANARY_TOKEN_LENGTH)}]"


def insert_canary(content: str, canary: str) -> str:
    """Append the canary to content as an HTML comment."""
    return f"{content}<!-- {canary} -->"


def detect_canary_leak(text: str, canary: str) -> bool:
    """Return True when the exact canary token appears in text."""
    return bool(canary) and canary in text
