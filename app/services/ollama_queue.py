"""Offline queue for Ollama requests."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OllamaQueueFullError(RuntimeError):
    """Raised when the offline queue is already at capacity."""


@dataclass
class QueuedRequest:
    request_id: str
    payload: dict[str, Any]
    callback: Callable[[], Awaitable[None]] | None = None
    base_url: str | None = None
    created_at: float = field(default_factory=time.time)
    retries: int = 0
    max_retries: int = 3


class OllamaOfflineQueue:
    MAX_QUEUE_SIZE = 100
    RETRY_INTERVAL = 30  # seconds
    HEALTH_CHECK_URL = "http://localhost:11434/api/tags"

    def __init__(self) -> None:
        self._queue: deque[QueuedRequest] = deque()
        self._ollama_online: bool = False
        self._processing: bool = False
        self._last_check: float = 0.0
        self._lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def enqueue(
        self,
        payload: dict[str, Any],
        callback: Callable[[], Awaitable[None]] | None = None,
        base_url: str | None = None,
    ) -> str:
        request_id = f"ollama-{int(time.time() * 1000)}"
        req = QueuedRequest(
            request_id=request_id,
            payload=payload,
            callback=callback,
            base_url=base_url,
        )
        async with self._lock:
            if len(self._queue) >= self.MAX_QUEUE_SIZE:
                raise OllamaQueueFullError(
                    f"Offline queue is full ({self.MAX_QUEUE_SIZE} pending requests)"
                )
            self._queue.append(req)
        # stdlib logger 不支持自定义 kwargs，此调用形参非法（潜在 bug，已上报）。
        logger.info(  # type: ignore[call-arg]
            "ollama_request_queued", request_id=request_id, queue_size=len(self._queue)
        )
        self._schedule_processing()
        return request_id

    def _schedule_processing(self) -> None:
        """Kick the consumption loop once, guarded by ``_processing``.

        Keeps strong references to the created tasks so they are not
        garbage-collected mid-flight; completed tasks are pruned.
        """
        task = asyncio.create_task(self.process_queue())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

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
                    else:
                        await self._execute_payload(req)
                    self._queue.popleft()
                    logger.info(  # type: ignore[call-arg]
                        "ollama_request_processed",
                        request_id=req.request_id,
                        queue_size=len(self._queue),
                    )
                except Exception as e:
                    req.retries += 1
                    if req.retries >= req.max_retries:
                        self._queue.popleft()
                        logger.warning(  # type: ignore[call-arg]
                            "ollama_request_failed", request_id=req.request_id, error=str(e)
                        )
                    else:
                        logger.info(  # type: ignore[call-arg]
                            "ollama_request_retry", request_id=req.request_id, retry=req.retries
                        )
                        await asyncio.sleep(self.RETRY_INTERVAL)
        finally:
            self._processing = False

    async def _execute_payload(self, req: QueuedRequest) -> None:
        """Post a queued payload to Ollama, completing the consumption chain.

        A queued request without a callback has nowhere for the reply to go,
        so it is replayed to the model for a side-effect-carrying retry.
        """
        base = (req.base_url or self.HEALTH_CHECK_URL.rsplit("/", 1)[0]).rstrip("/")
        payload = dict(req.payload)
        payload["stream"] = False
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{base}/api/chat", json=payload)
            resp.raise_for_status()

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
