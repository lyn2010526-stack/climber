"""Anthropic model adapter with streaming support."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.core import ChatResult
from app.models import ModelAdapter, ModelCapability

logger = structlog.get_logger()


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Messages API with streaming."""

    _client: httpx.AsyncClient | None = None

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        capabilities: ModelCapability | None = None,
    ):
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._capabilities = capabilities

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None

    @property
    def provider(self) -> str:
        return "anthropic"

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
            max_tokens=200_000,
        )

    def _convert_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        converted: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content")

            if role == "system":
                system_parts.append(content or "")
                continue
            if role == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": content or "",
                    }],
                })
                continue
            if role == "assistant" and msg.get("tool_calls"):
                anthropic_content: list[dict[str, Any]] = []
                if content:
                    anthropic_content.append({"type": "text", "text": content})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    anthropic_content.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": args,
                    })
                converted.append({"role": "assistant", "content": anthropic_content})
                continue

            converted.append({"role": role, "content": content or ""})

        system = "\n\n".join(system_parts) if system_parts else None
        return system, converted

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for t in tools:
            func = t.get("function", {})
            result.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            })
        return result

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Stream Anthropic Messages API with token-level granularity."""
        system, converted_msgs = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self._model_id,
            "messages": converted_msgs,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = self._convert_tools(tools)

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        current_tool_id = None
        current_tool_name = None
        current_tool_input = ""
        tokens_used = 0

        try:
            client = self.get_client()
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/messages",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type")

                        if etype == "message_start":
                            usage = event.get("message", {}).get("usage", {})
                            tokens_used = usage.get("input_tokens", 0)

                        elif etype == "content_block_start":
                            block = event.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_id = block.get("id")
                                current_tool_name = block.get("name")
                                current_tool_input = ""

                        elif etype == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield ChatResult(
                                    content=delta.get("text", ""),
                                    tool_calls=[],
                                    finish_reason=None,
                                    tokens_used=tokens_used,
                                )
                            elif delta.get("type") == "input_json_delta":
                                current_tool_input += delta.get("partial_json", "")

                        elif etype == "content_block_stop":
                            if current_tool_id and current_tool_name:
                                try:
                                    args = json.loads(current_tool_input) if current_tool_input else {}
                                except json.JSONDecodeError:
                                    args = {}
                                yield ChatResult(
                                    content="",
                                    tool_calls=[{
                                        "id": current_tool_id,
                                        "type": "function",
                                        "function": {
                                            "name": current_tool_name,
                                            "arguments": args,
                                        },
                                    }],
                                    finish_reason="tool_use",
                                    tokens_used=tokens_used,
                                )
                            current_tool_id = None
                            current_tool_name = None
                            current_tool_input = ""

                        elif etype == "message_delta":
                            tokens_used += event.get("usage", {}).get("output_tokens", 0)

        except Exception as e:
            logger.error("Anthropic streaming error", error=str(e))
            yield ChatResult(
                content=f"\n[Error: {e!s}]",
                tool_calls=[],
                finish_reason="error",
                tokens_used=tokens_used,
            )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Non-streaming chat."""
        full_content = ""
        tool_calls = []
        finish_reason = "stop"
        tokens_used = 0

        async for chunk in self.stream_chat(messages, tools, **kwargs):
            full_content += chunk.content
            if chunk.tool_calls:
                tool_calls = chunk.tool_calls
            if chunk.finish_reason:
                finish_reason = chunk.finish_reason
            tokens_used = max(tokens_used, chunk.tokens_used)

        return ChatResult(
            content=full_content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            tokens_used=tokens_used,
        )
