"""子 Agent 隔离运行机制（base_deps）。

改写自 claw-code `background_fork.py` 的设计思路：把一段任务放进
独立作用域/进程隔离执行，宿主与子任务互不影响，子任务失败不污染
宿主内存。供后台记忆精炼（innovation_layer/background_refine.py）
与未来长任务分片复用。

实现为进程级隔离（`multiprocessing` 或 `concurrent.futures.ProcessPoolExecutor`）：
  - 子任务跑在独立进程，持有独立内存/文件句柄
  - 通过 `fork_payload`（JSON 可序列化）传入任务描述
  - 结果/异常经 Queue 回传，宿主读取后自行反序列化
  - 提供同步 `run_forked` 与异步 `run_forked_async` 两个入口
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import multiprocessing
import os
import time
from dataclasses import dataclass
from typing import Any

_TASK_TIMEOUT_SECONDS = 60


@dataclass
class ForkResult:
    """一次隔离运行的结果。"""

    ok: bool
    value: Any = None
    error: str | None = None
    worker_pid: int = 0
    duration_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "value": self.value,
            "error": self.error,
            "worker_pid": self.worker_pid,
            "duration_ms": round(self.duration_ms, 2),
        }


def _worker_main(queue, payload_json: str, _timeout_seconds: int) -> None:
    """在子进程中执行的入口：解包 payload，执行 fn，结果写回队列。"""
    try:
        payload = json.loads(payload_json)
        fn_ref = payload["fn_ref"]
        args = payload.get("args", [])
        kwargs = payload.get("kwargs", {})
        # fn 以 `module:qualname` 形式注册，子进程自行导入（claw-code 隔离思路）
        import importlib

        mod_name, _, qual = fn_ref.partition(":")
        fn = importlib.import_module(mod_name)
        for part in qual.split("."):
            fn = getattr(fn, part)
        with contextlib.suppress(TimeoutError):
            result = fn(*args, **kwargs)
        queue.put({"ok": True, "value": result})
    except Exception as exc:
        queue.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def run_forked(fn, *args, timeout_seconds: int = _TASK_TIMEOUT_SECONDS,
               **kwargs) -> ForkResult:
    """同步隔离运行：把 fn(*args, **kwargs) 放到独立进程执行。

    fn 必须是可导入的函数（`module:qualname` 形式），参数与返回值需
    JSON 可序列化；未注册的局部函数走回退：in-process 执行（仅测试/轻任务）。
    """
    started = time.monotonic()
    mod_name = getattr(fn, "__module__", "")
    qual = getattr(fn, "__qualname__", "")
    if not (mod_name and qual and "." in qual):
        # 局部/未注册函数：降级为进程内隔离（try/except），记录差异
        try:
            value = fn(*args, **kwargs)
            return ForkResult(ok=True, value=value, worker_pid=os.getpid(),
                              duration_ms=(time.monotonic() - started) * 1000)
        except Exception as exc:
            return ForkResult(ok=False, error=f"{type(exc).__name__}: {exc}",
                              worker_pid=os.getpid(),
                              duration_ms=(time.monotonic() - started) * 1000)

    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    payload = json.dumps({"fn_ref": f"{mod_name}:{qual}", "args": list(args), "kwargs": kwargs})
    proc = ctx.Process(target=_worker_main, args=(queue, payload, timeout_seconds), daemon=True)
    proc.start()
    try:
        item = queue.get(timeout=timeout_seconds + 5)
        worker_pid = proc.pid or 0
        proc.join(timeout=2)
        return ForkResult(ok=bool(item.get("ok")), value=item.get("value"),
                          error=item.get("error"), worker_pid=worker_pid,
                          duration_ms=(time.monotonic() - started) * 1000)
    except Exception as exc:
        proc.terminate()
        proc.join(timeout=2)
        return ForkResult(ok=False, error=f"fork timeout/failure: {exc}",
                          worker_pid=proc.pid or 0,
                          duration_ms=(time.monotonic() - started) * 1000)


async def run_forked_async(fn, *args, timeout_seconds: int = _TASK_TIMEOUT_SECONDS,
                           **kwargs) -> ForkResult:
    """异步隔离运行：把隔离任务放到线程池，不阻塞事件循环。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: run_forked(fn, *args, timeout_seconds=timeout_seconds, **kwargs)
    )
