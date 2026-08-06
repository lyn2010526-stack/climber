"""Google Gemini adapter."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core import ChatResult
from app.models import ModelAdapter, ModelCapability


class GoogleGeminiAdapter(ModelAdapter):
    """Google Gemini adapter using the native Google AI API format."""

    def __init__(self, model_id: str, api_key: str, base_url: str | None = None, capabilities: ModelCapability | None = None):
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
            embedding=False,
            max_tokens=8192,
        )

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Gemini doesn't support true streaming in this adapter, yield full result."""
        result = await self.chat(messages, tools, **kwargs)
        if result.content:
            yield ChatResult(content=result.content, tool_calls=[], finish_reason=None, tokens_used=result.tokens_used)
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
                contents.append({
                    "role": "user",
                    "parts": [{"text": content or ""}],
                })
                continue

            gemini_role = "user" if role == "user" else "model"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content or ""}],
            })

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
            payload["tools"] = [{
                "functionDeclarations": [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "parameters": t["function"].get("parameters", {}),
                    }
                    for t in tools
                ]
            }]

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
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "type": "function",
                    "function": {
                        "name": fc.get("name", ""),
                        "arguments": args if isinstance(args, dict) else {},
                    },
                })

        return ChatResult(
            content="".join(text_parts),
            tool_calls=tool_calls,
            finish_reason=candidate.get("finishReason", "STOP").lower(),
        )
