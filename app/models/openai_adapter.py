"""OpenAI-compatible model adapter with streaming support."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncIterator

import httpx
import structlog

from app.core import ChatResult
from app.models import ModelAdapter, ModelCapability

logger = structlog.get_logger()


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI Chat Completions API and compatible providers."""

    _client: httpx.AsyncClient | None = None

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
    ):
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def _build_payload(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "stream": stream,
        }
        if stream:
            payload["stream_options"] = {"include_usage": True}
        if tools:
            payload["tools"] = tools
        payload.update(kwargs)
        return payload

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

    @staticmethod
    def _parse_tool_calls_from_delta(tool_calls_delta: list[dict]) -> list[dict]:
        """Parse tool calls from OpenAI streaming delta format."""
        result = []
        for tc in tool_calls_delta:
            idx = tc.get("index", 0)
            while len(result) <= idx:
                result.append({
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                })
            if tc.get("id"):
                result[idx]["id"] = tc["id"]
            if tc.get("function", {}).get("name"):
                result[idx]["function"]["name"] = tc["function"]["name"]
            if tc.get("function", {}).get("arguments"):
                result[idx]["function"]["arguments"] += tc["function"]["arguments"]
        return result

    @staticmethod
    def _parse_xml_tool_calls(text: str) -> list[dict]:
        """Parse XML-style tool calls like <function=browser_navigate>..."""
        results: list[dict] = []
        for m in re.finditer(r'<function=([^>]+)>(.*?)</\1>', text, re.DOTALL | re.IGNORECASE):
            name = m.group(1).strip()
            args_text = m.group(2).strip()
            args: dict[str, Any] = {}
            if args_text:
                try:
                    args = json.loads(args_text)
                except json.JSONDecodeError:
                    args = {"text": args_text}
            results.append({
                "id": "",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            })
        return results

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        """Stream chat with token-level granularity."""
        payload = self._build_payload(messages, tools, stream=True, **kwargs)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        accumulated_content = ""
        accumulated_tool_calls: list[dict] = []
        finish_reason = None
        tokens_used = 0

        import time
        timeout = kwargs.get("timeout", 120)
        start_time = time.monotonic()
        try:
            client = self.get_client()
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=headers,
                content=json.dumps(payload, ensure_ascii=False).encode(),
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if time.monotonic() - start_time > timeout:
                        logger.warning("stream_chat_total_timeout", timeout=timeout, model=self._model_id)
                        break
                    if not line or line == "data: [DONE]":
                        continue
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        accumulated_content += delta["content"]
                    if delta.get("tool_calls"):
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            while len(accumulated_tool_calls) <= idx:
                                accumulated_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                })
                            if tc.get("id"):
                                accumulated_tool_calls[idx]["id"] = tc["id"]
                            if tc.get("function", {}).get("name"):
                                accumulated_tool_calls[idx]["function"]["name"] = tc["function"]["name"]
                            if tc.get("function", {}).get("arguments"):
                                accumulated_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]
                    if chunk.get("usage"):
                        tokens_used = chunk["usage"].get("total_tokens", tokens_used)
                    if chunk.get("choices", [{}])[0].get("finish_reason"):
                        finish_reason = chunk["choices"][0]["finish_reason"]
                    yield ChatResult(
                        content=accumulated_content,
                        tool_calls=list(accumulated_tool_calls),
                        finish_reason=finish_reason,
                        tokens_used=tokens_used,
                    )
        except Exception as exc:  # pragma: no cover
            logger.error("stream_chat_failed", error=str(exc), model=self._model_id)
            raise

    async def _chat_non_streaming(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Non-streaming chat completion for providers that don't support stream."""
        payload = self._build_payload(messages, tools, stream=False, **kwargs)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            client = self.get_client()
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                content=json.dumps(payload, ensure_ascii=False).encode(),
                timeout=kwargs.get("timeout", 120),
            )
            response.raise_for_status()
            data = response.json()
            choice = data.get("choices", [{}])[0].get("message", {})
            content = choice.get("content", "") or ""
            tool_calls = choice.get("tool_calls", [])
            if isinstance(tool_calls, list):
                parsed_tool_calls = []
                for tc in tool_calls:
                    if tc.get("type") == "function":
                        parsed_tool_calls.append({
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": tc.get("function", {}),
                        })
                tool_calls = parsed_tool_calls
            else:
                tool_calls = []
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
            return ChatResult(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                tokens_used=tokens_used,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("chat_failed", error=str(exc), model=self._model_id)
            raise

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Non-streaming chat completion."""
        chunks: list[ChatResult] = []
        async for chunk in self.stream_chat(messages, tools, **kwargs):
            chunks.append(chunk)
        if not chunks:
            return ChatResult(content="", tool_calls=[], finish_reason="stop", tokens_used=0)
        last = chunks[-1]
        all_tool_calls: list[dict] = []
        for c in chunks:
            if c.tool_calls:
                all_tool_calls = c.tool_calls
        total_tokens = max(c.tokens_used or 0 for c in chunks)
        return ChatResult(
            content=last.content or "",
            tool_calls=all_tool_calls,
            finish_reason=last.finish_reason or "stop",
            tokens_used=total_tokens,
        )

    @property
    def capabilities(self) -> ModelCapability:
        return ModelCapability(
            streaming=True,
            function_calling=True,
            vision=False,
            max_context_length=128000,
            supports_system_prompt=True,
        )

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._api_key = value
