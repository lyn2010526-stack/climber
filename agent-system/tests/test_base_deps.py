"""base_deps 与创新层单元测试（不依赖真实 LLM/DB）。"""

from __future__ import annotations

from agent_system.base_deps.checkpoint_sqlite import SqliteCheckpointStore
from agent_system.base_deps.mem_fts5_sqlite import Fts5Store
from agent_system.base_deps.summarize_conversation import (
    _auto_summary,
    estimate_tokens,
    sliding_window,
    summarize_middle,
)
from agent_system.core_models import MemoryItem, MemoryKind, RiskLevel, RunMode, TAORPhase
from agent_system.innovation_layer.adaptive_compression import AdaptiveCompressionScheduler
from agent_system.innovation_layer.adaptive_retrieval import AdaptiveRetrievalRouter
from agent_system.innovation_layer.dual_snapshot import SnapshotManager
from agent_system.innovation_layer.three_state_controller import RiskPolicy, ThreeStateController


class TestCheckpointStore:
    def test_save_load_latest(self, tmp_path):
        store = SqliteCheckpointStore(str(tmp_path / "ckpt.db"))
        store.save("t1", "c1", {"round": 1})
        store.save("t1", "c2", {"round": 2})
        store.save("t2", "c1", {"round": 99})
        assert store.load("t1", "c1") == {"round": 1}
        assert store.latest("t1") == "c2"
        assert store.load("t1") == {"round": 2}
        assert set(store.list_ids("t1")) == {"c1", "c2"}
        assert store.purge("t1") == 2
        assert store.load("t1") is None

    def test_overwrite_same_key(self, tmp_path):
        store = SqliteCheckpointStore(str(tmp_path / "ckpt.db"))
        store.save("t1", "c1", {"v": 1})
        store.save("t1", "c1", {"v": 2})
        assert store.load("t1", "c1") == {"v": 2}


class TestSummarize:
    def test_estimate_tokens(self):
        msgs = [{"role": "user", "content": "你好" * 3}]
        assert estimate_tokens(msgs) >= 2  # 6 字符按 3 字符/token 估算

    def test_sliding_window(self):
        msgs = [{"role": "user", "content": f"m{i}"} for i in range(10)]
        out = sliding_window(msgs, keep_ratio=0.5)
        assert len(out) == 5
        assert out[-1]["content"] == "m9"

    def test_summarize_middle(self):
        msgs = [{"role": "user", "content": f"m{i}"} for i in range(10)]
        out = summarize_middle(msgs, head=2, tail=2)
        assert len(out) == 5  # head(2) + summary(1) + tail(2)
        assert out[0]["content"] == "m0"
        assert out[-1]["content"] == "m9"
        assert out[2]["role"] == "system"

    def test_auto_summary_short(self):
        out = _auto_summary([{"role": "user", "content": "abc"}], max_chars=200)
        assert "user" in out


class TestAdaptiveRetrieval:
    def test_route_decision(self):
        router = AdaptiveRetrievalRouter()
        assert router.decide_route("q", doc_type="skill", doc_length=30) == "fts_chinese"
        assert (
            router.decide_route("q", doc_type="code", doc_length=3000) == "fts_chinese"
        )  # 无向量插件回退
        assert router.decide_route("q", doc_type="conversation", doc_length=800) == "hybrid"

    def test_retrieve_empty_ok(self, tmp_path):
        fts = Fts5Store(str(tmp_path / "router_test.db"))
        router = AdaptiveRetrievalRouter(fts_store=fts)
        mem = MemoryItem(
            kind=MemoryKind.SKILL,
            text="关于 python 项目结构的规则说明",
            title="项目结构规则",
            doc_type="skill",
            doc_length=20,
        )
        fts.upsert(mem)

        async def _run():
            return await router.retrieve("项目结构", top_k=5, doc_type="skill", doc_length=20)

        import asyncio

        results = asyncio.run(_run())
        assert results, "skill 文档应能被检索到"


class TestAdaptiveCompression:
    def test_simple_keeps_detail(self):
        sched = AdaptiveCompressionScheduler()
        d = sched.decide(context_tokens=100, max_tokens=1000, task_type="simple")
        assert not d.should_compress  # 简单任务低水位不压缩

    def test_complex_tightens(self):
        sched = AdaptiveCompressionScheduler()
        d = sched.decide(context_tokens=800, max_tokens=1000, task_type="complex")
        assert d.should_compress
        assert d.strength >= 0.7
        assert d.strategy in {"summarize", "full_rewrite"}

    def test_stall_increases_strength(self):
        sched = AdaptiveCompressionScheduler()
        base = sched.decide(context_tokens=800, max_tokens=1000, task_type="general")
        boosted = sched.decide(
            context_tokens=800, max_tokens=1000, task_type="general", stall_rounds=3
        )
        assert boosted.strength > base.strength


class TestThreeState:
    def test_hitl_pauses_on_multiple_candidates(self):
        ctl = ThreeStateController(mode=RunMode.HITL)
        d = ctl.evaluate_pause(candidates=["方案A", "方案B"])
        assert d.should_pause
        assert any(r["type"] == "multiple_candidates" for r in d.risks)

    def test_hitl_pauses_on_high_risk_tool(self):
        ctl = ThreeStateController(mode=RunMode.HITL)
        d = ctl.evaluate_pause(tool_name="write_file")
        assert d.should_pause
        assert any(r["type"] == "high_risk_operation" for r in d.risks)

    def test_auto_never_pauses(self):
        ctl = ThreeStateController(mode=RunMode.AUTO)
        assert not ctl.evaluate_pause(candidates=["a", "b"], tool_name="bash").should_pause

    def test_risk_policy(self):
        policy = RiskPolicy()
        assert policy.assess_tool("write_file") == RiskLevel.HIGH
        assert policy.assess_tool("query_db") == RiskLevel.LOW

    def test_observe_blocks_write(self):
        ctl = ThreeStateController(mode=RunMode.OBSERVE)
        allowed, reason = ctl.allow_tool("write_file")
        assert not allowed
        assert "观察复盘模式禁用" in reason
        allowed, _ = ctl.allow_tool("query_db")
        assert allowed


class TestDualSnapshot:
    def test_chain_rebuild(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path / "snap.db"))
        mgr.save_milestone(
            "s1",
            TAORPhase.PLAN,
            state={"step": 1},
            messages=[{"role": "user", "content": "m0"}],
            label="plan",
        )
        mgr.save_incremental(
            "s1",
            TAORPhase.ACT,
            messages_delta=[{"role": "assistant", "content": "a1"}],
            changed_state={"step": 2},
        )
        full = mgr.load_head("s1")
        assert full.state["step"] == 2
        assert len(full.diff["messages"]) == 2

    def test_rollback_to_milestone(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path / "snap.db"))
        mgr.save_milestone("s1", TAORPhase.PLAN, state={"step": 1}, messages=[], label="plan")
        mgr.save_incremental("s1", TAORPhase.ACT, messages_delta=[], changed_state={"step": 2})
        ms = mgr.rollback_to_milestone("s1")
        assert ms is not None
        assert ms.state["step"] == 1
        assert mgr.load_milestone("s1").id == ms.id

    def test_no_milestone_returns_none(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path / "snap.db"))
        mgr.save_incremental("s1", TAORPhase.ACT, messages_delta=[], changed_state={"step": 1})
        assert mgr.rollback_to_milestone("s1") is None
