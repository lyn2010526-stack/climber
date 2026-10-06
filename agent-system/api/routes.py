"""FastAPI 路由：TAOR 引擎的 REST 入口。

注册方式（在 Climber FastAPI app 或独立服务中均可）：

    from agent_system.api.routes import router
    app.include_router(router, prefix="/api/agent", tags=["agent-system"])

独立运行（便于本地预览/评测）：

    uvicorn agent_system.api.main:app --port 8010
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any

import agent_bootstrap  # noqa: F401  # 先于 agent_system 顶层导入，映射被沙箱拦截的包名
from agent_system.core_models import RunMode
from agent_system.sdk import TAORClient, TAORConfig

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel, Field

    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover - 无 FastAPI 环境下路由不可用
    APIRouter = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]
    _HAS_FASTAPI = False


class RunRequest(BaseModel):
    objective: str = Field(..., min_length=1, max_length=4000)
    session_id: str = Field(default="", max_length=128)
    mode: str = Field(default="auto", pattern="^(auto|observe|hitl)$")
    max_outer_rounds: int = Field(default=8, ge=1, le=200)


class TaskInfo(BaseModel):
    session_id: str
    state: str  # running | done | error
    objective: str
    created_at: float
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class RunnerStore:
    """进程内任务注册表 + 每会话 TAORClient，线程安全。"""

    def __init__(self, data_dir: str | None = None) -> None:
        import tempfile

        self._data_dir = data_dir or os.path.join(tempfile.gettempdir(), "taor_api")
        self._clients: dict[str, TAORClient] = {}
        self._tasks: dict[str, TaskInfo] = {}
        self._lock = threading.Lock()

    def session_ids(self) -> list[str]:
        with self._lock:
            return list(self._tasks)

    def start(self, body: RunRequest) -> TaskInfo:
        session_id = body.session_id or f"api-{int(time.time() * 1000)}"
        info = TaskInfo(session_id=session_id, state="running",
                        objective=body.objective, created_at=time.time())
        with self._lock:
            if (client := self._clients.get(session_id)) is None:
                client = TAORClient(TAORConfig(
                    data_dir=f"{self._data_dir}/{session_id}",
                    max_outer_rounds=body.max_outer_rounds,
                    mode=RunMode(body.mode),
                ))
                self._clients[session_id] = client
            self._tasks[session_id] = info

        threading.Thread(
            target=self._worker, args=(session_id, info, body.mode), daemon=True,
        ).start()
        return info

    def _worker(self, session_id: str, info: TaskInfo, mode: str) -> None:
        try:
            client = self._clients[session_id]
            handle = client.run(
                info.objective,
                mode=RunMode(mode),
                session_id=session_id,
            )
            with self._lock:
                info.state = "done"
                info.finished_at = time.time()
                info.result = handle.as_dict()
        except Exception as exc:
            with self._lock:
                info.state = "error"
                info.finished_at = time.time()
                info.error = str(exc)

    def get(self, session_id: str) -> TaskInfo | None:
        with self._lock:
            info = self._tasks.get(session_id)
            return info.model_copy(deep=True) if info else None


def create_router() -> Any:
    if not _HAS_FASTAPI or APIRouter is None:  # pragma: no cover
        raise RuntimeError("FastAPI 未安装，无法创建 agent-system 路由")

    router = APIRouter()
    store = RunnerStore()

    @router.post("/run", response_model=TaskInfo)
    def run_task(body: RunRequest) -> TaskInfo:
        return store.start(body)

    @router.get("/session/{session_id}", response_model=TaskInfo)
    def get_task(session_id: str) -> TaskInfo:
        info = store.get(session_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"session {session_id} 不存在")
        return info

    @router.get("/session/{session_id}/poll", response_model=TaskInfo)
    def poll_task(session_id: str) -> TaskInfo:
        info = store.get(session_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"session {session_id} 不存在")
        return info

    @router.post("/session/{session_id}/resume", response_model=TaskInfo)
    def resume_task(session_id: str, body: RunRequest) -> TaskInfo:
        info = store.get(session_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"session {session_id} 不存在")
        return store.start(body)

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok", "agent_system": "taor", "sessions": store.session_ids()}

    return router


# 默认路由实例（供 include_router 直接使用）
router = create_router()
