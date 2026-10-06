"""非阻塞后台记忆精炼子 Agent（innovation_layer，创新点 2）。

复用 claw-code 子 Agent 隔离运行能力（base_deps/background_fork.py）；
复用 hindsight 事实抽取（fact_extract）、Mnemosyne 记忆生命周期（memory_lifecycle）。

后台工作：
  - 读取主 Agent 会话日志，抽取结构化事实
  - 提取失败案例存入独立失败经验库
  - 合并重复记忆、清理过期记忆、下调可信度偏低记忆的权重
  - 更新 SQLite 记忆库
  - 输出记忆审计日志
  - 全程不改动主 Agent 内存数据，不阻塞主循环（异步后台任务）

创新点：市面上子 Agent 多用于读取文件查询信息；本方案后台隔离进程自动做
事实抽取、记忆去重、过期清理、失败案例沉淀，不抢占主 Agent 的模型上下文。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from agent_system.base_deps.memory_lifecycle import MemoryLifecycle
from agent_system.core_models import (
    MemoryAuditEntry,
    MemoryItem,
    MemoryKind,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from agent_system.base_deps.mem_fts5_sqlite import Fts5Store

logger = logging.getLogger(__name__)


@dataclass
class RefinementResult:
    """一次后台精炼的结果（含审计日志）。"""

    audits: list[MemoryAuditEntry] = field(default_factory=list)
    facts_added: int = 0
    failures_added: int = 0
    duplicates_merged: int = 0
    expired: int = 0
    downgraded: int = 0
    duration_ms: float = 0.0
    triggered_by: str = ""


class BackgroundMemoryRefiner:
    """后台记忆精炼子 Agent（隔离运行，不阻塞主循环）。"""

    def __init__(
        self,
        store: Fts5Store,
        session_log_provider: Callable[[str], str] | None = None,
        max_concurrent: int = 2,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.store = store
        self.lifecycle = MemoryLifecycle(store)
        self._session_log_provider = session_log_provider
        self._max_concurrent = max_concurrent
        self._loop = loop
        self._tasks: set[asyncio.Task] = set()
        self._results: list[RefinementResult] = []

    def start_refinement(self, session_id: str, session_log: str | None = None,
                         context: str = "", triggered_by: str = "") -> str:
        """异步启动一次后台精炼（fire-and-forget，不阻塞主循环）。

        复用 claw-code 子 Agent 隔离运行能力：在独立 asyncio.Task 中执行，
        异常被隔离，不传播到主 Agent。
        """
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.get_running_loop()
        task = self._loop.create_task(
            self._run_refinement(session_id, session_log, context, triggered_by),
            name=f"memory-refine:{session_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task.get_name()

    async def _run_refinement(self, session_id: str, session_log: str | None,
                              context: str, triggered_by: str) -> RefinementResult:
        import time
        started = time.monotonic()
        try:
            log_text = session_log
            if log_text is None and self._session_log_provider is not None:
                log_text = self._session_log_provider(session_id)
            if not log_text:
                result = RefinementResult(triggered_by=triggered_by)
                self._results.append(result)
                return result

            # 1) 抽取结构化事实入库
            fact_audits = self.lifecycle.extract_and_store(log_text, session_id, context)
            # 2) 失败案例独立沉淀
            failure_audits = self._extract_failures(log_text, session_id)
            # 3) 合并重复 / TTL 清理 / 衰减 / 低可信降权
            merge_audits = self.lifecycle.merge_duplicates()
            expire_audits = self.lifecycle.expire_ttl()
            decay_audits = self.lifecycle.decay_all()
            low_trust_audits = self.lifecycle.downgrade_low_trust()

            all_audits = fact_audits + failure_audits + merge_audits + expire_audits + decay_audits + low_trust_audits
            result = RefinementResult(
                audits=all_audits,
                facts_added=len(fact_audits),
                failures_added=len(failure_audits),
                duplicates_merged=sum(1 for a in merge_audits if a.action == "merge"),
                expired=sum(1 for a in expire_audits if a.action == "expire"),
                downgraded=sum(1 for a in (decay_audits + low_trust_audits) if a.action == "downgrade"),
                duration_ms=(time.monotonic() - started) * 1000,
                triggered_by=triggered_by,
            )
            self._results.append(result)
            logger.info("memory_refinement_done session_id=%s facts=%s audits=%s",
                        session_id, result.facts_added, len(all_audits))
            return result  # noqa: TRY300 - 隔离运行中保留 try 包裹以便统一异常兜底
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # 隔离失败：记录但不阻塞主循环（claw-code 子 Agent 隔离思路）
            logger.warning("memory_refinement_failed session_id=%s error=%s",
                           session_id, type(exc).__name__)
            result = RefinementResult(triggered_by=triggered_by)
            result.audits.append(MemoryAuditEntry(
                action="kept_below_trust", reason=f"精炼失败隔离: {type(exc).__name__}",
            ))
            self._results.append(result)
            return result

    def _extract_failures(self, session_log: str, session_id: str) -> list[MemoryAuditEntry]:
        """从会话日志提取失败案例，存入独立失败经验库（kind=failure）。"""
        audits: list[MemoryAuditEntry] = []
        markers = ["失败", "error", "Error", "exception", "Exception", "traceback", "Traceback"]
        lines = session_log.splitlines()
        for i, line in enumerate(lines):
            if not any(m in line for m in markers):
                continue
            # 收集失败行及其上下文（前后各 2 行）
            window = "\n".join(lines[max(0, i - 2): i + 3])
            item = MemoryItem(
                kind=MemoryKind.FAILURE,
                text=window[:2000],
                title=f"失败案例: {line.strip()[:80]}",
                doc_type="failure",
                trust_score=0.3,   # 失败案例可信度默认较低
                source_session=session_id,
                metadata={"marker": next((m for m in markers if m in line), ""), "line": i},
            )
            existing_id = self.store.upsert(item)
            audits.append(MemoryAuditEntry(
                action="add", memory_id=existing_id, kind=MemoryKind.FAILURE,
                text_preview=item.text[:50], score_after=item.trust_score,
                reason="失败案例沉淀入库",
            ))
        return audits

    async def wait_all(self) -> list[RefinementResult]:
        """等待所有后台精炼完成（供评测/收尾使用，不阻塞主循环常态）。"""
        if self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(*list(self._tasks))
        return list(self._results)

    def last_results(self) -> list[RefinementResult]:
        return list(self._results)
