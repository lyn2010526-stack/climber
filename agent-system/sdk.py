"""TAOR 智能体引擎 SDK（程序化入口）。

提供 `TAORClient` 门面：装配引擎组件（记忆存储/快照/精炼/检索/压缩/控制器），
以 同步 `run(...)` 与 异步 `arun(...)` 两种用法暴露：
运行 / 续跑 / 报告 / 记忆审计 / 快照 / 事件流。

同步用法（阻塞，适合 CLI / 脚本 / 教学）：

    client = TAORClient(TAORConfig(data_dir="/tmp/k"))
    handle = client.run("查询并按部门汇总")
    handle.report.status   # completed / paused / rolled_back ...
    handle.audit()         # 记忆审计日志
    handle.snapshots()     # 双层快照列表

异步用法（并发调度 / HTTP 后端）：

    await client.arun("...")
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from agent_system.core_models import MemoryAuditEntry, RunMode, TaskReport, ToolDescriptor
from agent_system.innovation_layer.adaptive_compression import AdaptiveCompressionScheduler
from agent_system.innovation_layer.adaptive_retrieval import AdaptiveRetrievalRouter
from agent_system.innovation_layer.background_refine import BackgroundMemoryRefiner
from agent_system.innovation_layer.dual_snapshot import SnapshotManager
from agent_system.innovation_layer.taor_engine import TAOREngine, TAOROptions
from agent_system.innovation_layer.three_state_controller import ThreeStateController

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class TAORConfig:
    """客户端数据目录与运行参数。"""

    data_dir: str = field(
        default_factory=lambda: os.path.join(tempfile.gettempdir(), "taor_sdk"))
    mode: RunMode = RunMode.AUTO
    max_outer_rounds: int = 8
    max_stall_rounds: int = 2
    milestone_every: int = 5
    memory_refine_every: int = 3
    seed_memory: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SDKRunHandle:
    """一次运行的任务句柄。"""

    session_id: str
    objective: str
    report: TaskReport | None = field(default=None)
    events: list[dict[str, Any]] = field(default_factory=list)
    audits: list[MemoryAuditEntry] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "objective": self.objective,
            "report": asdict(self.report) if self.report else None,
            "events": self.events,
            "audits": [asdict(a) for a in self.audits],
            "snapshots": self.snapshots,
        }


class TAORClient:
    """TAOR 引擎程序化门面（纯 Python，不依赖 HTTP）。"""

    def __init__(self, config: TAORConfig | None = None) -> None:
        from agent_system.base_deps.mem_fts5_sqlite import Fts5Store

        self.config = config or TAORConfig()
        os.makedirs(self.config.data_dir, exist_ok=True)
        prefix = os.path.join(self.config.data_dir, "taor")
        self._store = Fts5Store(f"{prefix}_memory.db")
        self._snapshots = SnapshotManager(f"{prefix}_snapshots.db")
        self._refiner = BackgroundMemoryRefiner(store=self._store)
        self._router = AdaptiveRetrievalRouter(fts_store=self._store)
        self._compressor = AdaptiveCompressionScheduler()
        self._controller = ThreeStateController(mode=self.config.mode)
        self._seq = 0
        self._seed_memories()

    @property
    def store(self):
        return self._store

    @property
    def snapshot_manager(self):
        return self._snapshots

    @property
    def refiner(self):
        return self._refiner

    def _seed_memories(self) -> None:
        for entry in self.config.seed_memory:
            self._store.upsert(_memory_from_dict(entry))

    # ---- 同步运行（阻塞，子线程中文档友好） ----
    def run(self, objective: str, *,
            mode: RunMode | None = None,
            llm_call: Callable | None = None,
            tool_executor: Callable | None = None,
            tools: list[ToolDescriptor] | None = None,
            session_id: str = "") -> SDKRunHandle:
        """同步运行。未提供 llm/tool 时使用确定性 demo。"""
        import asyncio

        from agent_system import demo

        mode = mode or self.config.mode
        llm = llm_call or demo.deterministic_llm()
        tools = tools or demo.DEMO_TOOLS
        execute = tool_executor or demo.DEMO_TOOL_EXECUTOR
        self._seq += 1
        session_id = session_id or f"sdk-{self._seq}"

        handle = SDKRunHandle(session_id=session_id, objective=objective)

        async def emit(event_type, data):
            handle.events.append({"event": event_type.value, "data": data})

        async def _runner():

            engine = self._build_engine(mode, llm, execute, tools, emit)
            handle.report = await engine.run(session_id, objective)
            await self._refiner.wait_all()
            handle.audits = _flatten_audits(self._refiner.last_results())
            handle.snapshots = self.snapshot_manager.list_snapshots(session_id)

        asyncio.run(_runner())
        return handle

    def _build_engine(self, mode, llm, execute, tools, emit) -> TAOREngine:
        return TAOREngine(
            llm_call=llm, tool_executor=execute,
            router=self._router, snapshot_mgr=self._snapshots,
            refiner=self._refiner, compressor=self._compressor,
            controller=ThreeStateController(mode=mode),
            tool_descriptors=tools,
            options=TAOROptions(
                max_outer_rounds=self.config.max_outer_rounds,
                max_stall_rounds=self.config.max_stall_rounds,
                milestone_every=self.config.milestone_every,
                memory_refine_every=self.config.memory_refine_every,
                mode=mode,
            ),
            emit=emit,
        )

    def audit(self) -> list[dict[str, Any]]:
        return [asdict(a) for a in _flatten_audits(self._refiner.last_results())]

    def resume(self, objective: str, session_id: str):
        """续跑：当前实现重建会话 (真实续跑复用快照 loader 接入点)。"""
        return self.run(objective, session_id=session_id)


# 适配 MemoryItem 从 dict 构造（避免暴露 storage 细节到 SDK 顶部）
from agent_system.core_models import MemoryItem, MemoryKind  # noqa: E402


def _memory_from_dict(d: dict[str, Any]) -> MemoryItem:
    return MemoryItem(
        kind=getattr(MemoryKind, d.get("kind", "RULE")),
        text=d.get("text", ""),
        title=d.get("title"),
        doc_type=d.get("doc_type", "rule"),
        doc_length=len(d.get("text", "")),
        trust_score=d.get("trust_score", 0.5),
    )


def _flatten_audits(results) -> list[MemoryAuditEntry]:
    audits: list[MemoryAuditEntry] = []
    for result in results:
        audits.extend(result.audits)
    return audits
