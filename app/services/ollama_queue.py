"""Offline queue for Ollama requests."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Coroutine

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    request_id: str
    payload: dict[str, Any]
    callback: Callable[[], Awaitable[None]] | None = None
    created_at: float = field(default_factory=time.time)
    retries: int = 0
    max_retries: int = 3


class OllamaOfflineQueue:
    MAX_QUEUE_SIZE = 100
    RETRY_INTERVAL = 30  # seconds
    HEALTH_CHECK_URL = "http://localhost:11434/api/tags"

    def __init__(self) -> None:
        self._queue: deque[QueuedRequest] = deque(maxlen=self.MAX_QUEUE_SIZE)
        self._ollama_online: bool = False
        self._processing: bool = False
        self._last_check: float = 0.0
        self._lock = asyncio.Lock()

    async def enqueue(self, payload: dict[str, Any], callback: Callable[[], Awaitable[None]] | None = None) -> str:
        request_id = f"ollama-{int(time.time() * 1000)}"
        req = QueuedRequest(
            request_id=request_id,
            payload=payload,
            callback=callback,
        )
        async with self._lock:
            self._queue.append(req)
        logger.info("ollama_request_queued", request_id=request_id, queue_size=len(self._queue))
        return request_id

    async def process_queue(self) -> None:
        if self._processing:
            return
        self._processing = True
        try:
            while self._queue:
                if not await self._check_ollama_health():
                    break
                req = self._queue[0]
                try:
                    if req.callback:
                        await req.callback()
                    self._queue.popleft()
                    logger.info("ollama_request_processed", request_id=req.request_id, queue_size=len(self._queue))
                except Exception as e:
                    req.retries += 1
                    if req.retries >= req.max_retries:
                        self._queue.popleft()
                        logger.warning("ollama_request_failed", request_id=req.request_id, error=str(e))
                    else:
                        logger.info("ollama_request_retry", request_id=req.request_id, retry=req.retries)
                        await asyncio.sleep(self.RETRY_INTERVAL)
        finally:
            self._processing = False

    async def _check_ollama_health(self) -> bool:
        now = time.time()
        if now - self._last_check < 5:
            return self._ollama_online

        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(self.HEALTH_CHECK_URL)
                self._ollama_online = resp.status_code == 200
        except Exception:
            self._ollama_online = False

        self._last_check = now
        if self._ollama_online:
            logger.info("ollama_back_online")
        else:
            logger.debug("ollama_still_offline")
        return self._ollama_online

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def is_ollama_online(self) -> bool:
        return self._ollama_online


ollama_offline_queue = OllamaOfflineQueue()
