"""增强 TAOR 主循环引擎（innovation_layer 核心）。

基于 smolagents Turn 轮次底座（base_deps/turn_loop.py 改写），
增强为 TAOR 七阶段循环（学习天蛇家族/Claude-Code 泄露资料思路）：

  1. SYSBOOT   预检：加载项目 skill 与规则文档，调取长期记忆，生成初始任务规划
  2. THINK     思考：结合上下文、记忆、工具列表，产出下一步行动决策
  3. ACT       行动：执行工具调用，捕获返回结果以及运行异常
  4. OBSERVE   观察：把工具结果写入会话日志，评估任务进度、风险等级
  5. BRANCH    状态分支判断：
       - 任务完成 → DONE（完整任务总结报告）
       - 连续多轮无进展/反复报错 → 回滚最近有效里程碑快照重试
       - 命中人机接力触发条件 → 保存里程碑快照，暂停循环，移交控制权
       - 其余 → 下一轮循环
  6. 每跑完 2-3 轮主循环，启动后台子 Agent 做记忆精炼（不阻塞主循环）
  7. 每一轮循环保存增量 diff 快照；里程碑快照仅在暂停、关键业务节点保存

组件接线：
  - 记忆路由：AdaptiveRetrievalRouter（创新点 1）
  - 后台精炼：BackgroundMemoryRefiner（创新点 2）
  - 三态控制：ThreeStateController（创新点 3）
  - 双层快照：SnapshotManager（创新点 4）
  - 动态压缩：AdaptiveCompressionScheduler（创新点 5）
  - LLM：Climber ModelAdapter；工具：ToolRegistry
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from agent_system.core_models import (
    LoopDecision,
    LoopReport,
    RiskLevel,
    RunMode,
    Snapshot,
    SystemEventType,
    TAORPhase,
    TaskReport,
    ToolCall,
    ToolClass,
    ToolDescriptor,
    ToolResult,
    new_id,
    now_utc,
)
from agent_system.innovation_layer.three_state_controller import (
    RiskPolicy,
    ThreeStateController,
    make_decision,
)

if TYPE_CHECKING:
    from agent_system.innovation_layer.adaptive_compression import AdaptiveCompressionScheduler
    from agent_system.innovation_layer.adaptive_retrieval import AdaptiveRetrievalRouter
    from agent_system.innovation_layer.background_refine import BackgroundMemoryRefiner
    from agent_system.innovation_layer.dual_snapshot import SnapshotManager

logger = logging.getLogger(__name__)

# 每跑完 2-3 轮启动一次后台精炼
MEMORY_REFINE_EVERY_ROUNDS = 3

# TAOR 主循环系统提示词
TAOR_SYSTEM_PROMPT = """你是运行在 TAOR 循环中的智能体。请遵循如下决策格式：

1. 每轮先思考：结合用户目标、长期记忆、可用工具，决定下一步动作。
2. 行动：调用最合适的工具完成当前子任务。
3. 观察：工具结果写回会话日志并评估进度/风险。
4. 若任务完成，输出最终总结（不再调用工具）。
5. 若需要拆分子任务，在"next_subtask"中输出下一个子任务描述。

若连续两轮没有实质进展，主动停止并输出全部状态。"""


@dataclass
class TAOROptions:
    """TAOR 主循环运行选项。"""

    mode: RunMode = RunMode.AUTO
    max_outer_rounds: int = 10
    max_stall_rounds: int = 2  # 连续无进展次数上限（触发回滚）
    milestone_every: int | None = None  # 每 N 轮存里程碑（None=关闭）
    memory_refine_every: int = MEMORY_REFINE_EVERY_ROUNDS
    risk_policy: RiskPolicy | None = None

    def __post_init__(self) -> None:
        if self.max_outer_rounds <= 0:
            raise ValueError("max_outer_rounds must be > 0")


class TAOREngine:
    """TAOR 主循环引擎。"""

    # 事件类型直出（转成 SSE 在 API 层）
    Event = SystemEventType

    def __init__(
        self,
        llm_call=None,  # await llm_call(messages, tools) -> ChatResult-like
        tool_executor=None,  # await tool_executor(ToolCall) -> ToolResult
        router: AdaptiveRetrievalRouter | None = None,
        snapshot_mgr: SnapshotManager | None = None,
        refiner: BackgroundMemoryRefiner | None = None,
        compressor: AdaptiveCompressionScheduler | None = None,
        controller: ThreeStateController | None = None,
        tool_descriptors: list[Any] | None = None,
        skill_loader: Any | None = None,  # 加载项目 skill/规则文档
        options: TAOROptions | None = None,
        emit=None,  # async emit(event_type, data) 事件回调
    ) -> None:
        self.llm_call = llm_call
        self.tool_executor = tool_executor
        self.router = router
        self.snapshot_mgr = snapshot_mgr
        self.refiner = refiner
        self.compressor = compressor
        self.controller = controller or ThreeStateController()
        self.tool_descriptors = tool_descriptors or []
        self.skill_loader = skill_loader
        self.options = options or TAOROptions()
        self._emit = emit
        self._session_log: list[dict[str, Any]] = []
        self._messages: list[dict[str, Any]] = []

    # ---- 事件 ----

    async def _emit_event(self, event_type: SystemEventType, data: dict[str, Any]) -> None:
        if self._emit is not None:
            await self._emit(event_type, data)

    # ---- 主循环入口 ----

    async def run(
        self, session_id: str, objective: str, context: dict[str, Any] | None = None
    ) -> TaskReport:
        """运行 TAOR 主循环，返回任务报告。

        Args:
            session_id: 会话/任务 ID
            objective: 用户任务目标
            context: 附加上下文（项目根目录、技能路径等）
        """
        context = context or {}
        started = now_utc()
        report = TaskReport(
            task_id=session_id,
            objective=objective,
            mode=self.options.mode,
            status="running",
            started_at=started,
        )
        self._session_log = []
        self._messages = [{"role": "system", "content": TAOR_SYSTEM_PROMPT}]

        # 阶段 0: SYSBOOT 预检
        await self._phase_sysboot(session_id, objective, context, report)

        stall_count = 0
        round_no = 0
        terminal = False

        while round_no < self.options.max_outer_rounds and not terminal:
            round_no += 1

            # 阶段 2: 规划/思考
            plan_message = await self._phase_think(session_id, round_no, context, report)
            if plan_message is None:
                break  # 模型判定完成

            # 阶段 3: 行动（处理工具调用）
            result = await self._phase_act(session_id, round_no, plan_message, context, report)

            # 阶段 4: 观察
            observation = await self._phase_observe(session_id, round_no, result, context, report)

            # 阶段 5/6: 状态分支判断
            stall_count = stall_count + 1 if observation["no_progress"] else 0
            no_tool_calls = not (plan_message.get("tool_calls") or [])
            decision = await self._phase_branch(
                session_id, round_no, observation, stall_count, report, no_tool_calls=no_tool_calls
            )

            # 每一轮保存增量 diff 快照
            if self.snapshot_mgr is not None:
                snap = self.snapshot_mgr.save_incremental(
                    session_id,
                    decision.next_phase,
                    messages_delta=self._session_log[-2:],
                    changed_state={"round": round_no, "last_result": str(result)[:200]},
                )
                await self._emit_event(
                    SystemEventType.SNAPSHOT_SAVED, {"id": snap.id, "round": round_no}
                )

            # 每 2-3 轮启动后台记忆精炼（不阻塞）
            if self.refiner is not None and round_no % self.options.memory_refine_every == 0:
                self.refiner.start_refinement(
                    session_id,
                    session_log=json.dumps(self._session_log, ensure_ascii=False),
                    context=objective,
                    triggered_by=f"round_{round_no}",
                )
                await self._emit_event(SystemEventType.MEMORY_REFINED, {"round": round_no})

            # 分支决策
            if decision.done:
                report.status = "completed"
                terminal = True
                self._merge_report(report, observation)
                report.result_summary = (
                    getattr(self, "_last_assistant_content", "") or observation["text_output"]
                )[:500]
                break
            if decision.yield_control:
                report.status = "yielded"
                terminal = True
                self._merge_report(report, observation)
                # 保存里程碑快照（人机接力暂停）
                if self.snapshot_mgr is not None:
                    milestone = self.snapshot_mgr.save_milestone(
                        session_id,
                        TAORPhase.YIELD,
                        state={"round": round_no, "objective": objective},
                        messages=self._session_log,
                        label="yield_pause",
                    )
                    await self._emit_event(
                        SystemEventType.MILESTONE_SAVED,
                        {
                            "id": milestone.id,
                            "reason": decision.reason,
                        },
                    )
                await self._emit_event(
                    SystemEventType.YIELD_PENDING,
                    {
                        "reason": decision.reason,
                    },
                )
                redecided = await self._handle_yield_resume()
                if not redecided:
                    break
                terminal = False  # 用户选择继续/修改规划/回滚后恢复循环
                stall_count = 0
                continue
            if decision.rollback:
                report.rollbacks += 1
                self._merge_report(report, observation)
                _milestone = self._rollback(session_id, round_no)
                stall_count = 0
                if _milestone is None:
                    break  # 无里程碑可回滚
                continue

        report.outer_rounds = round_no
        report.finished_at = now_utc()

        # 非终止退出（回滚无里程碑 / 达最大轮数 / 模型无输出）补终态
        if report.status == "running":
            if report.rollbacks > 0:
                report.status = "rolled_back"
            elif round_no >= self.options.max_outer_rounds:
                report.status = "max_rounds"
            else:
                report.status = "aborted"

        # 收尾之记忆精炼（可选）
        if self.refiner is not None:
            self.refiner.start_refinement(
                session_id,
                session_log=json.dumps(self._session_log, ensure_ascii=False),
                context=objective,
                triggered_by="end",
            )

        await self._emit_event(
            SystemEventType.DONE,
            {
                "status": report.status,
                "rounds": round_no,
                "completed_tasks": report.completed_tasks,
                "result_summary": report.result_summary,
            },
        )
        return report

    # ---- 各阶段 ----

    async def _phase_sysboot(
        self, session_id: str, objective: str, context: dict[str, Any], report: TaskReport
    ) -> None:
        """阶段 0: 预检 - 加载技能/规则文档 + 长期记忆 + 初始规划。"""
        await self._emit_event(SystemEventType.PHASE_CHANGED, {"phase": TAORPhase.SYSBOOT.value})
        skills_context = ""
        if self.skill_loader is not None:
            try:
                skills_context = await self.skill_loader.load(objective, context)
            except Exception as exc:
                logger.warning("skill_load_failed error=%s", type(exc).__name__)
        # 调取长期记忆
        memory_context = ""
        if self.router is not None:
            mems = await self.router.retrieve(
                objective,
                doc_type="conversation",
                doc_length=len(objective),
                top_k=5,
            )
            if mems:
                memory_context = "\n".join(f"- {m.item.text}" for m in mems[:3])
        if skills_context or memory_context:
            self._messages.append(
                {
                    "role": "system",
                    "content": f"[项目技能/规则]\n{skills_context}\n[相关记忆]\n{memory_context}",
                }
            )

    async def _phase_think(
        self, session_id: str, round_no: int, context: dict[str, Any], report: TaskReport
    ) -> dict[str, Any] | None:
        """阶段 1-2: 规划/思考 - 产出下一步决策（文本 + 可能的工具调用）。"""
        await self._emit_event(
            SystemEventType.PHASE_CHANGED, {"phase": TAORPhase.THINK.value, "round": round_no}
        )
        if round_no > 1:
            self._messages.append(
                {
                    "role": "user",
                    "content": f"(第 {round_no} 轮) 继续完成任务。若已完成请输出最终总结；"
                    f"否则给出下一步行动或调用工具。",
                }
            )
        # 动态上下文压缩（创新点 5）
        if self.compressor is not None:
            max_tokens = (
                int(context.get("max_tokens") or 16000) if isinstance(context, dict) else 16000
            )
            decision = self.compressor.decide(
                context_tokens=_estimate_tokens(self._messages),
                max_tokens=max_tokens,
                task_type=self.options.mode.value
                if self.options.mode == RunMode.OBSERVE
                else "general",
                stall_rounds=report.retries,
                round_number=round_no,
            )
            if decision.should_compress:
                await self._emit_event(
                    SystemEventType.CONTEXT_COMPRESSED,
                    {
                        "strength": decision.strength,
                        "strategy": decision.strategy,
                        "reason": decision.reason,
                    },
                )
                self._messages = await self.compressor.compress_messages(self._messages, decision)
        # 调用 LLM 产出决策
        tools = self._llm_tools()
        result = await self._call_llm(self._messages, tools)
        report.inner_turns += 1
        if result is None:
            return None
        await self._emit_event(SystemEventType.THINKING, {"round": round_no})
        # 追加 assistant 消息，保持跨轮上下文连续
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": result.content or ""}
        if getattr(result, "tool_calls", None):
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id") or new_id("tc_"),
                    "type": "function",
                    "function": {
                        "name": tc.get("function", {}).get("name", tc.get("name", "")),
                        "arguments": json.dumps(
                            tc.get("function", {}).get("arguments", tc.get("arguments", {})),
                            ensure_ascii=False,
                        ),
                    },
                }
                for tc in result.tool_calls
            ]
        self._messages.append(assistant_msg)
        self._last_assistant_content = result.content or ""
        if result.tool_calls:
            return {"tool_calls": result.tool_calls, "content": result.content or ""}
        # 无工具调用：检查是否输出完成总结
        return {"tool_calls": [], "content": result.content or ""}

    async def _phase_act(
        self,
        session_id: str,
        round_no: int,
        plan: dict[str, Any],
        context: dict[str, Any],
        report: TaskReport,
    ) -> list[ToolResult]:
        """阶段 3: 行动 - 执行工具调用，捕获结果与异常。"""
        await self._emit_event(
            SystemEventType.PHASE_CHANGED, {"phase": TAORPhase.ACT.value, "round": round_no}
        )
        results: list[ToolResult] = []
        tool_calls = plan.get("tool_calls") or []
        if not tool_calls:
            return results

        # 观察复盘模式：写/改/执行/网络工具禁用（三态控制器）
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", tc.get("name", ""))
            desc = self._find_tool(name)
            allowed, reason = self.controller.allow_tool(desc if desc else name)
            if not allowed:
                results.append(
                    ToolResult(
                        tool_call_id=tc.get("id", new_id("tc_")),
                        name=name,
                        content=None,
                        is_error=True,
                        error=reason,
                    )
                )
                await self._emit_event(
                    SystemEventType.TOOL_RESULT,
                    {
                        "name": name,
                        "error": reason,
                        "blocked": True,
                    },
                )
                continue
            call = ToolCall(
                name=name,
                arguments=_parse_args(
                    tc.get("function", {}).get("arguments", tc.get("arguments", {}))
                ),
                tool_call_id=tc.get("id", new_id("tc_")),
            )
            await self._emit_event(
                SystemEventType.TOOL_CALL, {"name": name, "arguments": call.arguments}
            )
            try:
                started = time.monotonic()
                r = await self.tool_executor(call)
                r.duration_ms = (time.monotonic() - started) * 1000
            except Exception as exc:
                r = ToolResult(
                    tool_call_id=call.tool_call_id,
                    name=name,
                    content=None,
                    is_error=True,
                    error=str(exc),
                )
            results.append(r)
            report.tool_calls += 1
            await self._emit_event(
                SystemEventType.TOOL_RESULT,
                {
                    "name": name,
                    "is_error": r.is_error,
                    "error": r.error,
                },
            )
            # 观察复盘控制器统计失败
            if r.is_error:
                self.controller.register_failure()
            else:
                self.controller.register_success()
        return results

    async def _phase_observe(
        self,
        session_id: str,
        round_no: int,
        results: list[ToolResult],
        context: dict[str, Any],
        report: TaskReport,
    ) -> dict[str, Any]:
        """阶段 4: 观察 - 工具结果写会话日志，评估进度与风险。"""
        await self._emit_event(
            SystemEventType.PHASE_CHANGED, {"phase": TAORPhase.OBSERVE.value, "round": round_no}
        )
        text_output = ""
        tool_errors = 0
        has_side_effect = False
        tools_used: list[dict[str, str]] = []
        if results:
            body = []
            for r in results:
                if r.is_error:
                    tool_errors += 1
                    body.append(f"[tool:{r.name} error] {r.error}")
                else:
                    has_side_effect = has_side_effect or bool(r.content)
                    body.append(f"[tool:{r.name}] {str(r.content)[:200]}")
                tools_used.append({"name": r.name, "tool_class": self._tool_class(r.name).value})
            text_output = "\n".join(body)
            self._session_log.append(
                {
                    "round": round_no,
                    "type": "tools",
                    "result": text_output,
                }
            )
            self._messages.append(
                {
                    "role": "tool",
                    "tool_call_id": results[-1].tool_call_id if results else "",
                    "content": text_output or "",
                }
            )
        # 风险评估（依据本轮实际用到的工具）
        risk = RiskLevel.LOW
        if any(r.is_error for r in results):
            risk = RiskLevel.MEDIUM
        if any(
            self._tool_class(r.name) in (ToolClass.WRITE, ToolClass.EXEC, ToolClass.NETWORK)
            for r in results
        ):
            risk = max(risk, RiskLevel.MEDIUM)
        observation = {
            "text_output": text_output,
            "tool_errors": tool_errors,
            "has_side_effect": has_side_effect,
            "tool_calls_this_round": len(results),
            "tools_used": tools_used,
            "no_progress": (tool_errors > 0 and not has_side_effect),
            "risk": risk.value,
        }
        await self._emit_event(
            SystemEventType.OBSERVATION,
            {
                "round": round_no,
                "tool_errors": tool_errors,
                "no_progress": observation["no_progress"],
            },
        )
        return observation

    async def _phase_branch(
        self,
        session_id: str,
        round_no: int,
        observation: dict[str, Any],
        stall_count: int,
        report: TaskReport,
        no_tool_calls: bool = False,
    ) -> LoopDecision:
        """阶段 5: 状态分支判断。"""
        await self._emit_event(
            SystemEventType.PHASE_CHANGED, {"phase": TAORPhase.BRANCH.value, "round": round_no}
        )

        # 条件 1：任务完成（本轮未调用任何工具 = 模型输出最终总结）
        if no_tool_calls:
            report.completed_tasks.append(f"第{round_no}轮: 完成")
            return make_decision(
                TAORPhase.DONE, done=True, reason="模型输出最终总结，无进一步工具调用"
            )

        # 条件 2：连续多轮无进展/反复报错 → 回滚最近里程碑
        if stall_count >= self.options.max_stall_rounds:
            report.retries += 1
            return make_decision(
                TAORPhase.ROLLBACK,
                rollback=True,
                reason=f"连续 {stall_count} 轮无进展，回滚到最近里程碑重试",
                risk_level=RiskLevel.MEDIUM,
            )

        # 条件 3：人机接力触发（三态控制器自动评估）
        hi_risk_tool = next(
            (
                t
                for t in (observation.get("tools_used") or [])
                if t["tool_class"]
                in (ToolClass.WRITE.value, ToolClass.EXEC.value, ToolClass.NETWORK.value)
            ),
            None,
        )
        pause = self.controller.evaluate_pause(
            risk_level=RiskLevel.MEDIUM if observation["tool_errors"] else RiskLevel.LOW,
            candidates=[],
            tool_class=ToolClass(hi_risk_tool["tool_class"]) if hi_risk_tool else None,
            tool_name=hi_risk_tool["name"] if hi_risk_tool else None,
        )
        if pause.should_pause:
            report.completed_tasks.append(f"第{round_no}轮: 触发人机接力暂停")
            return make_decision(
                TAORPhase.YIELD,
                yield_control=True,
                reason=pause.reason,
                risk_level=RiskLevel.MEDIUM,
            )

        # 条件 4：其余进入下一轮
        report.completed_tasks.append(f"第{round_no}轮")
        return make_decision(TAORPhase.THINK, reason="进入下一轮循环")

    # ---- 工具/上下文接口 ----

    def _find_tool(self, name: str) -> ToolDescriptor | None:
        """按名称找工具描述（工具权限/风险判定用）。"""
        for t in self.tool_descriptors:
            if t.name == name:
                return t
        return None

    def _tool_class(self, name: str) -> ToolClass:
        desc = self._find_tool(name)
        return desc.tool_class if desc else ToolClass.READ

    def _llm_tools(self) -> list[dict[str, Any]] | None:
        """构造 LLM 工具定义（对接 Climber ToolRegistry 思路）。"""
        if not self.tool_descriptors:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters or {"type": "object", "properties": {}},
                },
            }
            for t in self.tool_descriptors
        ]

    async def _call_llm(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None):
        """调用 Climber ModelAdapter 兼容接口。"""
        if self.llm_call is None:
            # 无 LLM：控制器决策（供评测 mock）
            class _FakeResult:
                content: ClassVar[str] = ""
                tool_calls: ClassVar[list[dict[str, Any]]] = []
                tokens_used: ClassVar[int] = 0

            return _FakeResult()
        return await self.llm_call(messages, tools)

    def _rollback(self, session_id: str, round_no: int) -> Snapshot | None:
        """回滚到最近有效里程碑快照（创新点 4 附加逻辑）。"""
        if self.snapshot_mgr is None:
            return None
        milestone = self.snapshot_mgr.rollback_to_milestone(session_id)
        if milestone is not None:
            logger.info(
                "taor_rollback session_id=%s round=%s milestone=%s",
                session_id,
                round_no,
                milestone.id,
            )
        return milestone

    async def _handle_yield_resume(self) -> bool:
        """人机接力恢复。默认经外部决策回调；无回调则保持暂停。

        上层（SDK/HTTP）通过 resume_after_yield() 注入用户的
        继续/修改规划/回滚/补充知识库决策。
        """
        yield_cb = getattr(self, "_yield_callback", None)
        if yield_cb is not None:
            decision = yield_cb()
            if isinstance(decision, str):
                return decision in {"continue", "resume", "修改规划", "回滚", "继续"}
            return bool(decision)
        return False

    def set_yield_callback(self, callback) -> None:
        """设置人机接力恢复回调：返回 True 继续，False 保持暂停。"""
        self._yield_callback = callback

    def resume(self, decision: str | bool = True) -> None:
        """外部恢复：True/'continue'/'resume' 继续循环。"""
        self.set_yield_callback(lambda: decision)

    # ---- 报告 ----

    def _merge_report(self, report: TaskReport, observation: dict[str, Any]) -> None:
        report.tokens_used += getattr(observation, "tokens_used", 0) or 0

    def get_session_log(self) -> list[dict[str, Any]]:
        return list(self._session_log)

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    # ---- Loop report（用户规范：每轮输出进度/已完成/follow-up 队列） ----

    def build_loop_report(
        self,
        *,
        session_id: str = "",
        outer_round: int = 0,
        inner_turn: int = 0,
        phase: TAORPhase = TAORPhase.THINK,
        progress: str = "",
        completed: list[str] | None = None,
        pending: list[str] | None = None,
        followup: list[str] | None = None,
        risk: RiskLevel = RiskLevel.LOW,
        tokens: int = 0,
    ) -> LoopReport:
        return LoopReport(
            session_id=session_id,
            outer_round=outer_round,
            inner_turn=inner_turn,
            phase=phase,
            progress=progress,
            completed_tasks=completed or [],
            pending_tasks=pending or [],
            followup_queue=followup or [],
            risk_level=risk,
            tokens_used=tokens,
        )


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """粗估消息 token 数（压缩调度用）。"""
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += max(1, len(content) // 3)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += max(1, len(str(part.get("text", ""))) // 3)
    return total


def _parse_args(raw: Any) -> dict[str, Any]:
    """解析 LLM 传入的工具参数（OpenAI 格式为 JSON 字符串）。"""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        with contextlib.suppress(ValueError):
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
    return {"raw": raw} if raw else {}
