"""Ollama adapter for self-hosted local models."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core import ChatResult
from app.models import ModelAdapter, ModelCapability
from app.services.ollama_queue import ollama_offline_queue


class OllamaAdapter(ModelAdapter):
    """Ollama adapter for running local models (Llama, Mistral, Qwen, etc.)."""

    def __init__(self, model_id: str, api_key: str, base_url: str | None = None, capabilities: "ModelCapability | None" = None):
        self._model_id = model_id
        self._api_key = api_key
        self._base_url = (base_url or "http://localhost:11434").rstrip("/")
        self._capabilities = capabilities

    @property
    def provider(self) -> str:
        return "ollama"

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
            tools=False,
            vision=False,
            embedding=False,
            max_tokens=4096,
        )

    async def _is_ollama_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def _make_request(self, payload: dict[str, Any], stream: bool = False) -> Any:
        async with httpx.AsyncClient(timeout=120) as client:
            if stream:
                async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                    resp.raise_for_status()
                    return resp
            else:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        payload: dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
            },
        }
        if tools:
            payload["tools"] = tools

        if not await self._is_ollama_reachable():
            yield ChatResult(
                content="\n[Ollama offline. Request queued for retry when connection is restored.]",
                tool_calls=[],
                finish_reason="offline",
            )
            await ollama_offline_queue.enqueue(payload)
            return

        try:
            resp = await self._make_request(payload, stream=True)
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("done"):
                    yield ChatResult(
                        content="",
                        tool_calls=[],
                        finish_reason="stop",
                        tokens_used=0,
                    )
                    break
                msg = chunk.get("message", {})
                if msg.get("content"):
                    yield ChatResult(
                        content=msg["content"],
                        tool_calls=[],
                        finish_reason=None,
                        tokens_used=0,
                    )
        except Exception as e:
            yield ChatResult(
                content=f"\n[Error: {str(e)}]",
                tool_calls=[],
                finish_reason="error",
            )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload: dict[str, Any] = {
            "model": self._model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
            },
        }

        if tools:
            payload["tools"] = tools

        if not await self._is_ollama_reachable():
            await ollama_offline_queue.enqueue(payload)
            return ChatResult(
                content="Ollama offline. Request queued for retry when connection is restored.",
                tool_calls=[],
                finish_reason="offline",
            )

        try:
            data = await self._make_request(payload, stream=False)
            message = data.get("message", {})
            content = message.get("content", "")

            tool_calls: list[dict[str, Any]] = []
            for tc in message.get("tool_calls", []):
                func = tc.get("function", {})
                args = func.get("arguments", {})
                tool_calls.append({
                    "id": func.get("name", ""),
                    "type": "function",
                    "function": {
                        "name": func.get("name", ""),
                        "arguments": args if isinstance(args, dict) else {},
                    },
                })

            return ChatResult(
                content=content,
                tool_calls=tool_calls,
                finish_reason="stop" if not data.get("done") else data.get("done_reason", "stop"),
            )
        except Exception as e:
            return ChatResult(
                content=f"Error: {str(e)}",
                tool_calls=[],
                finish_reason="error",
            )
