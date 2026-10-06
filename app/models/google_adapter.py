"""Google Gemini adapter."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.core import ChatResult
from app.models import ModelAdapter, ModelCapability
from app.models.vision import is_image_reference, split_data_url

logger = structlog.get_logger()


class GoogleGeminiAdapter(ModelAdapter):
    """Google Gemini adapter using the native Google AI API format."""

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str | None = None,
        capabilities: ModelCapability | None = None,
    ):
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
        self._capabilities = capabilities

    @property
    def provider(self) -> str:
        return "google"

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._api_key = value

    @property
    def capabilities(self) -> ModelCapability:
        if self._capabilities is not None:
            return self._capabilities
        return ModelCapability(
            chat=True,
            streaming=True,
            tools=True,
            vision=True,
            file_attachments=False,
            embedding=False,
            max_tokens=8192,
        )

    @staticmethod
    def _convert_content(content: Any) -> list[dict[str, Any]]:
        """Map OpenAI vision content parts to Gemini parts; text becomes one text part."""
        if not isinstance(content, list):
            return [{"text": content or ""}]
        parts: list[dict[str, Any]] = []
        for part in content:
            if isinstance(part, str):
                parts.append({"text": part})
                continue
            if not isinstance(part, dict):
                continue
            part_type = part.get("type")
            if part_type == "text":
                parts.append({"text": str(part.get("text", ""))})
            elif part_type == "image_url":
                image_part = GoogleGeminiAdapter._gemini_image_part(
                    str((part.get("image_url") or {}).get("url", ""))
                )
                if image_part is not None:
                    parts.append(image_part)
                else:
                    logger.warning(
                        "chat_image_part_unmapped",
                        provider="google",
                        url_prefix=str(part)[:32],
                    )
        return parts or [{"text": ""}]

    @staticmethod
    def _gemini_image_part(url: str) -> dict[str, Any] | None:
        """Convert an image reference into a Gemini inline/file part."""
        split = split_data_url(url)
        if split is not None:
            media_type, payload = split
            return {"inline_data": {"mime_type": media_type, "data": payload}}
        if is_image_reference(url):
            return {"file_data": {"file_uri": url}}
        return None

    async def stream_chat(  # type: ignore[override]  # base declares async->AsyncIterator; impl is an async generator consumed via `async for`
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Yield the complete Gemini result once."""
        result = await self.chat(messages, tools, **kwargs)
        yield result

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Convert OpenAI-style messages to Gemini format
        contents: list[dict[str, Any]] = []
        system_parts: list[str] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content")

            if role == "system":
                system_parts.append(content or "")
                continue
            if role == "tool":
                # Tool result
                contents.append(
                    {
                        "role": "user",
                        "parts": [{"text": content or ""}],
                    }
                )
                continue

            gemini_role = "user" if role == "user" else "model"
            contents.append({"role": gemini_role, "parts": self._convert_content(content)})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4096),
            },
        }

        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        if tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": t["function"]["name"],
                            "description": t["function"].get("description", ""),
                            "parameters": t["function"].get("parameters", {}),
                        }
                        for t in tools
                    ]
                }
            ]

        url = f"{self._base_url}/models/{self._model_id}:generateContent?key={self._api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ChatResult(content="", finish_reason="error")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])

        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            if "functionCall" in part:
                fc = part["functionCall"]
                args = fc.get("args", {})
                tool_calls.append(
                    {
                        "id": str(uuid.uuid4()),
                        "type": "function",
                        "function": {
                            "name": fc.get("name", ""),
                            "arguments": args if isinstance(args, dict) else {},
                        },
                    }
                )

        return ChatResult(
            content="".join(text_parts),
            tool_calls=tool_calls,
            finish_reason=_canonical_finish_reason(candidate.get("finishReason")),
        )


def _canonical_finish_reason(raw: str | None) -> str:
    """Map Gemini ``finishReason`` to OpenAI-style canonical names.

    A naive ``.lower()`` turns ``MAX_TOKENS`` into ``max_tokens``, which
    consumers do not recognize; ``length`` is the canonical truncation
    signal. Safety-related reasons all collapse to ``content_filter``.
    """
    if not raw:
        return "stop"
    mapping = {
        "STOP": "stop",
        "MAX_TOKENS": "length",
        "SAFETY": "content_filter",
        "RECITATION": "content_filter",
        "PROHIBITED": "content_filter",
        "SPII": "content_filter",
        "IMAGE_SAFETY": "content_filter",
        "OTHER": "stop",
    }
    return mapping.get(raw.upper(), raw.lower())
