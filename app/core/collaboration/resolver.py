"""API key and base URL resolution helpers."""

from __future__ import annotations

import os

from app.core.api_key_crypto import decrypt_api_key


def resolve_api_key(provider: str, stored_key: str | None) -> str:
    """Resolve API key from member config or environment variable fallback.

    Args:
        provider: The model provider name (e.g., "openai", "anthropic").
        stored_key: The encrypted API key stored in the database.

    Returns:
        The decrypted API key string, or empty string if not available.
    """
    if stored_key:
        return decrypt_api_key(stored_key)
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "stepfun": "STEPFUN_API_KEY",
        "ollama": "",
    }
    var = env_map.get(provider.lower())
    if var:
        return os.environ.get(var, "")
    return ""


def resolve_base_url(provider: str, stored_url: str | None) -> str | None:
    """Resolve base_url from member config or environment variable fallback.

    Args:
        provider: The model provider name.
        stored_url: The base URL stored in the database.

    Returns:
        The resolved base URL, or None if not available.
    """
    if stored_url:
        return stored_url
    env_map = {
        "stepfun": "STEPFUN_BASE_URL",
        "ollama": "OLLAMA_BASE_URL",
    }
    var = env_map.get(provider.lower())
    return os.environ.get(var) if var else None
