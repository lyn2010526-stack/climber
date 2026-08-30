"""OpenAI-compatible model adapter with streaming support."""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from app.core import ChatResult
from app.models import ModelAdapter, ModelCapability

logger = structlog.get_logger()


def _with_cache_usage(
    result: ChatResult,
    *,
    cached_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> ChatResult:
    result.cached_tokens = cached_tokens
    result.cache_creation_tokens = cache_creation_tokens
    return result


def _default_extra_body() -> dict[str, Any]:
    """Read extra request body params from MODEL_EXTRA_PARAMS (JSON).

    Used to inject provider-specific fields (e.g. reasoning_effort, thinking)
    into every request for this adapter. Keep the environment-variable path.
    """
    raw = os.environ.get("MODEL_EXTRA_PARAMS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        logger.warning("model_extra_params_invalid_json", raw=raw[:200])
    return {}


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI Chat Completions API and compatible providers."""

    _client: httpx.AsyncClient | None = None

    def __init__(
        self,
        model_id: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        capabilities: ModelCapability | None = None,
        extra_body: dict[str, Any] | None = None,
    ):
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._capabilities = capabilities
        if extra_body is None:
            extra_body = _default_extra_body()
        self._extra_body = extra_body or {}

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
        if tools:
            payload["tools"] = tools
        payload.update(self._extra_body)
        payload.update(kwargs)
        return payload

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(float(os.environ.get("MODEL_HTTP_TIMEOUT", "600")), connect=10.0),
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
        """Stream chat with idle-timeout watchdog.

        For providers like LongCat that keep the connection open without sending
        a standard ``data: [DONE]`` terminator, a background watchdog task
        monitors idle time.  If no bytes arrive within ``idle_timeout`` seconds
        the response is forcefully closed, causing ``aiter_bytes()`` to return
        and the generator to exit cleanly.
        """
        payload = self._build_payload(messages, tools, stream=True, **kwargs)
        import structlog
        structlog.get_logger().debug("adapter_request", model=self._model_id, message_count=len(messages), messages_preview=str(payload.get("messages", []))[:500])
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        total_timeout = kwargs.get("timeout", 120)
        idle_timeout = kwargs.get("idle_timeout", int(os.environ.get("MODEL_STREAM_IDLE_TIMEOUT", "120")))
        accumulated_content = ""
        accumulated_tool_calls: list[dict] = []
        finish_reason = None
        tokens_used = 0
        cached_tokens = 0
        cache_creation_tokens = 0
        reported_cached_tokens = 0

        def _consume_chunk(chunk: dict[str, Any]) -> tuple[ChatResult, bool]:
            nonlocal accumulated_content
            nonlocal accumulated_tool_calls
            nonlocal finish_reason
            nonlocal tokens_used
            nonlocal cached_tokens
            nonlocal cache_creation_tokens
            nonlocal reported_cached_tokens

            choices = chunk.get("choices") or [{}]
            delta = choices[0].get("delta", {})
            delta_content = delta.get("content") or ""
            if delta_content:
                accumulated_content += delta_content
            if delta.get("tool_calls"):
                new_calls = self._parse_tool_calls_from_delta(delta["tool_calls"])
                for i, tool_call in enumerate(new_calls):
                    while len(accumulated_tool_calls) <= i:
                        accumulated_tool_calls.append(
                            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                        )
                    if tool_call.get("id"):
                        accumulated_tool_calls[i]["id"] = tool_call["id"]
                    if tool_call.get("function", {}).get("name"):
                        accumulated_tool_calls[i]["function"]["name"] = tool_call["function"]["name"]
                    if tool_call.get("function", {}).get("arguments"):
                        args = tool_call["function"]["arguments"]
                        accumulated_tool_calls[i]["function"]["arguments"] += (
                            args if isinstance(args, str) else str(args)
                        )
            if chunk.get("usage"):
                usage = chunk["usage"]
                tokens_used = usage.get("total_tokens", tokens_used)
                details = usage.get("prompt_tokens_details", {})
                cached_tokens = details.get("cached_tokens", usage.get("cached_tokens", cached_tokens))
                cache_creation_tokens = details.get("cache_creation_tokens", cache_creation_tokens)
                if cached_tokens > reported_cached_tokens:
                    from app.middleware.metrics import record_provider_cached_tokens

                    record_provider_cached_tokens(
                        "openai",
                        self._model_id,
                        cached_tokens - reported_cached_tokens,
                    )
                    reported_cached_tokens = cached_tokens
            frame_finish_reason = choices[0].get("finish_reason")
            if frame_finish_reason:
                finish_reason = frame_finish_reason

            result = _with_cache_usage(
                ChatResult(
                    content=delta_content,
                    tool_calls=list(accumulated_tool_calls),
                    finish_reason=finish_reason,
                    tokens_used=tokens_used,
                    accumulated_content=accumulated_content,
                ),
                cached_tokens=cached_tokens,
                cache_creation_tokens=cache_creation_tokens,
            )
            return result, self._is_stream_terminated(chunk)

        client = self.get_client()
        response: httpx.Response | None = None
        watchdog_task: asyncio.Task | None = None
        idle_event = asyncio.Event()

        async def _watchdog():
            """Close the response when idle timeout fires."""
            try:
                while True:
                    try:
                        await asyncio.wait_for(
                            idle_event.wait(), timeout=idle_timeout
                        )
                        idle_event.clear()
                    except TimeoutError:
                        if response is not None:
                            logger.info(
                                "stream_idle_timeout",
                                model=self._model_id,
                                idle=idle_timeout,
                            )
                            await response.aclose()
                        return
            except asyncio.CancelledError:
                return

        try:
            watchdog_task = asyncio.create_task(_watchdog())
            response = await client.send(
                httpx.Request(
                    method="POST",
                    url=f"{self._base_url}/chat/completions",
                    headers=headers,
                    content=json.dumps(payload, ensure_ascii=False).encode(),
                ),
                stream=True,
            )
            response.raise_for_status()

            buffer = b""
            async for raw_bytes in response.aiter_bytes():
                idle_event.set()

                if not raw_bytes:
                    break

                buffer += raw_bytes
                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace").strip("\r")

                    if not line or line.startswith(":"):
                        continue

                    if line == "data: [DONE]":
                        # Final chunks carry the snapshot and metadata; content remains incremental.
                        if accumulated_content or accumulated_tool_calls:
                            yield _with_cache_usage(ChatResult(
                                content="",
                                tool_calls=list(accumulated_tool_calls),
                                finish_reason=finish_reason or "stop",
                                tokens_used=tokens_used,
                                accumulated_content=accumulated_content,
                            ), cached_tokens=cached_tokens, cache_creation_tokens=cache_creation_tokens)
                        return

                    if not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if not data_str:
                        continue

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    result, terminated = _consume_chunk(chunk)
                    yield result
                    if terminated:
                        return

            # Process any remaining data in buffer (no trailing newline)
            if buffer.strip():
                line = buffer.decode("utf-8", errors="replace").strip("\r")
                if line.startswith("data:") and line[5:].strip():
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        if accumulated_content or accumulated_tool_calls:
                            yield _with_cache_usage(ChatResult(
                                content="",
                                tool_calls=list(accumulated_tool_calls),
                                finish_reason=finish_reason or "stop",
                                tokens_used=tokens_used,
                                accumulated_content=accumulated_content,
                            ), cached_tokens=cached_tokens, cache_creation_tokens=cache_creation_tokens)
                        return
                    try:
                        chunk = json.loads(data_str)
                        result, _terminated = _consume_chunk(chunk)
                        yield result
                    except json.JSONDecodeError:
                        pass

        except httpx.ReadTimeout:
            logger.warning("stream_read_timeout", model=self._model_id)
            yield ChatResult(
                content="",
                tool_calls=list(accumulated_tool_calls),
                finish_reason=finish_reason or "stop",
                tokens_used=tokens_used,
                accumulated_content=accumulated_content,
            )
        except TimeoutError:
            logger.warning("stream_total_timeout", model=self._model_id, timeout=total_timeout)
            yield ChatResult(
                content="",
                tool_calls=list(accumulated_tool_calls),
                finish_reason=finish_reason or "stop",
                tokens_used=tokens_used,
                accumulated_content=accumulated_content,
            )
        except Exception as exc:
            logger.error("stream_chat_failed", error=str(exc), model=self._model_id)
            raise
        finally:
            if watchdog_task and not watchdog_task.done():
                watchdog_task.cancel()
                try:
                    await watchdog_task
                except asyncio.CancelledError:
                    pass
            if response is not None:
                await response.aclose()

    @staticmethod
    def _is_stream_terminated(chunk: dict[str, Any]) -> bool:
        """Check if this SSE frame signals end of stream.

        Handles multiple non-standard termination signals from various providers
        (LongCat, Kimi, DeepSeek, etc.).
        """
        if chunk.get("lastOne") is True:
            return True
        if chunk.get("stream_end") is True:
            return True
        if chunk.get("is_last") is True:
            return True
        if chunk.get("end_of_stream") is True:
            return True
        choices = chunk.get("choices", [])
        if choices and choices[0].get("finish_reason"):
            return True
        return False

    async def _chat_non_streaming(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Non-streaming chat completion for providers that don't support stream."""
        payload = self._build_payload(messages, tools, stream=False, **kwargs)
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
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
            details = usage.get("prompt_tokens_details", {})
            cached_tokens = details.get("cached_tokens", usage.get("cached_tokens", 0))
            cache_creation_tokens = details.get("cache_creation_tokens", 0)
            if cached_tokens:
                from app.middleware.metrics import record_provider_cached_tokens

                record_provider_cached_tokens("openai", self._model_id, cached_tokens)
            finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
            return _with_cache_usage(ChatResult(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                tokens_used=tokens_used,
            ), cached_tokens=cached_tokens, cache_creation_tokens=cache_creation_tokens)
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
        kwargs.pop("stream", None)
        chunks: list[ChatResult] = []
        async for chunk in self.stream_chat(messages, tools, **kwargs):
            chunks.append(chunk)
        if not chunks:
            return ChatResult(content="", tool_calls=[], finish_reason="stop", tokens_used=0)
        full_content = next(
            (chunk.accumulated_content for chunk in reversed(chunks) if chunk.accumulated_content),
            "".join(c.content or "" for c in chunks),
        )
        all_tool_calls: list[dict] = []
        for c in chunks:
            if c.tool_calls:
                all_tool_calls = c.tool_calls
        total_tokens = max((c.tokens_used or 0 for c in chunks), default=0)
        cached_tokens = max((getattr(c, "cached_tokens", 0) for c in chunks), default=0)
        cache_creation_tokens = max(
            (getattr(c, "cache_creation_tokens", 0) for c in chunks),
            default=0,
        )
        return _with_cache_usage(ChatResult(
            content=full_content or "",
            tool_calls=all_tool_calls,
            finish_reason=chunks[-1].finish_reason or "stop",
            tokens_used=total_tokens,
            accumulated_content=full_content or "",
        ), cached_tokens=cached_tokens, cache_creation_tokens=cache_creation_tokens)

    @property
    def capabilities(self) -> ModelCapability:
        if self._capabilities is not None:
            return self._capabilities
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
