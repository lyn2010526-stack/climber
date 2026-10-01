"""Image (vision) content helpers shared by chat and the model adapters.

The canonical wire format for image-bearing messages is the OpenAI vision
content-parts layout:
``[{"type": "text", "text": ...}, {"type": "image_url", "image_url": {"url": ...}}]``.
Every image reference is either a base64 data URL or an http(s) URL.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import Any

import structlog

logger = structlog.get_logger()

# Upper bound per message; keeps payloads and provider requests bounded.
MAX_CHAT_IMAGES = 4

_DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)$")
_HTTP_URL_RE = re.compile(r"^https?://\S+$")


def is_image_reference(value: Any) -> bool:
    """Return True for a base64 image data URL or an http(s) URL string."""
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("data:"):
        return _DATA_URL_RE.match(value) is not None
    return _HTTP_URL_RE.match(value) is not None


def validate_images(images: list[str] | None) -> list[str]:
    """Validate the chat ``images`` payload.

    Args:
        images: Optional list of base64 data URLs or http(s) URLs.

    Returns:
        The validated list (a shallow copy; empty when ``images`` is falsy).

    Raises:
        ValueError: On too many images or a malformed reference.
    """
    if not images:
        return []
    if len(images) > MAX_CHAT_IMAGES:
        raise ValueError(f"At most {MAX_CHAT_IMAGES} images per message are supported")
    for url in images:
        if not is_image_reference(url):
            raise ValueError("Each image must be a base64 data URL or an http(s) URL")
    return list(images)


def build_user_content(text: str, images: list[str] | None) -> str | list[dict[str, Any]]:
    """Build canonical user message content in OpenAI vision format.

    Returns the plain string when no images are present, otherwise content
    parts with the text first and one ``image_url`` part per image.
    """
    if not images:
        return text
    parts: list[dict[str, Any]] = []
    if text:
        parts.append({"type": "text", "text": text})
    parts.extend({"type": "image_url", "image_url": {"url": url}} for url in images)
    return parts


def image_parts(content: Any) -> list[dict[str, Any]]:
    """Return the ``image_url`` parts of message content; empty for plain text."""
    if not isinstance(content, list):
        return []
    return [part for part in content if isinstance(part, dict) and part.get("type") == "image_url"]


def content_text(content: Any) -> str:
    """Flatten message content to plain text, ignoring non-text parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return "" if content is None else str(content)


def split_data_url(url: str) -> tuple[str, str] | None:
    """Split a base64 image data URL into ``(media_type, base64_payload)``.

    Returns None when the URL is not a well-formed, decodable data URL.
    """
    match = _DATA_URL_RE.match(url)
    if match is None:
        return None
    media_type, payload = match.group(1), match.group(2)
    try:
        base64.b64decode(payload)
    except (binascii.Error, ValueError):
        return None
    return media_type, payload


def degrade_image_parts(
    messages: list[dict[str, Any]],
    *,
    provider: str,
    model_id: str,
) -> list[dict[str, Any]]:
    """Flatten OpenAI vision parts to plain text for providers without image support.

    Returns the original list untouched when no image parts exist, otherwise a
    copy with every ``image_url`` part removed. Each dropped image is covered by
    one warning log per request so the LLM call still completes without error.
    """
    dropped = sum(len(image_parts(msg.get("content"))) for msg in messages)
    if dropped == 0:
        return messages
    flattened = [
        {**msg, "content": content_text(msg.get("content"))}
        if image_parts(msg.get("content"))
        else msg
        for msg in messages
    ]
    logger.warning(
        "chat_images_dropped_provider_unsupported",
        provider=provider,
        model=model_id,
        dropped=dropped,
    )
    return flattened
