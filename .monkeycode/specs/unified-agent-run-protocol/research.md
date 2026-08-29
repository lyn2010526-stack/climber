# 对标调研：开源 Agent Harness / Run 协议

本文记录统一 Run 协议切片对标的开源项目结论，作为后续增量的设计依据。调研时间 2026-08，全部基于各项目公开文档。

## 对标对象

### 1. LangGraph（checkpoint / 恢复语义）
- Checkpoint 以 `parent_checkpoint_id` 构成血缘链，`checkpoint_id` 时间有序（恢复时按 `ORDER BY checkpoint_id DESC` 取最新）。
- Interrupt 表达为 `pending_writes`：中断状态不特殊建模，就是"尚未完成的写"，靠 `Command(resume=...)` 恢复。
- 副作用必须幂等：恢复会重放节点，副作用由执行者自行保证不重复。

### 2. OpenAI Agents SDK（Sessions / 可观测性）
- Sessions 仅承载对话记忆，无内建崩溃恢复；恢复依赖外部持久化。
- OTEL tracing 是一等公民。

### 3. OpenHands（事件流架构）
- 每轮交互固定 4 状态事件流；沙箱按 session 隔离。

### 4. DeepSeek Harness（dsh，202k stars，Everything is a Plugin）
- **双事件平面**：`SessionEvent`（append-only 持久日志、唯一事实源，LLM 历史由 `deriveMessages()` 从日志派生）与 `agent/*` 事件（仅观察/拦截在途工作、不持久化）。
- **Model-visible ⟺ logged 不变式**：到达模型请求的任何内容必须可从日志重构，运行时断言校验。
- **Fail-closed 事件词汇表**：`SessionEventMap` 成员读时必需——不认识类型的构建方拒绝读取日志；仅结构性变更 bump `SESSION_FORMAT_VERSION`。
- **结构化终止原因**：`TurnEndReason` = completed / aborted{cause} / blocked / error / max-tokens / interrupted；`interrupted` 仅由崩溃恢复合成、循环自身从不自发；崩溃孤儿 turn 由持久化后端在 reload 时关闭。
- **中断标记**：中途取消时已交付前缀定稿为 `assistant/message(interrupted: true)`。
- **Waterfall 拦截事件**：`agent/pre-step`、`agent/request`、`llm/stream`、`tools/*` 为可改写/拒绝的中间件链（必须调 `next()`）；`agent/turn-stopping` 串行无 next。
- **Fork 边界**：`fork(source, boundary)` 要求前缀结束于开放 turn 之外，拒绝静默裁剪；`session/end-seed` 标记种子历史来源。
- **防御模式**：清理必须 await quiescence（kill 后等待退出）；派发器内容纳回调异常；正交结果独立上报；注册即效果（返回 disposer）。

### 5. PenguinHarness（1.8k stars，本地优先多 Agent 平台）
- **六层运行模型**：Project → Agent → Workspace → Session → Task → Request；Task≈一次执行目标（含多个连续 Request）。
- **Trace 为恢复唯一事实源**：无独立 session 数据库；恢复时只重放已提交轮次（`request_end.status === "completed"` 为提交判据），tool_call/output 配对保持完整，未完成模型输出允许丢失；崩溃尾部截断行被容忍跳过。
- **日志只记实际发生**：中断后 carry-over（已完成工具结果结构化重发、未完成者填 `[interrupted: tool aborted by user]`、未完成模型输出压为 `[turn_aborted]` 文本）只进模型上下文，绝不写入 Trace。
- **字段保真（fidelity）**：provider 不透明载荷（思考签名、加密推理等）逐字节存 Trace 并原样回传——部分模型要求历史重放 byte-for-byte；这是 Trace 存原始信封而非后处理格式的原因之一。
- **写入耐久细节**：单条 `write(2)` 原子追加；恢复前探测文件尾部撕裂行；并发生产者的追加在 writer 内串行。
- **重连重试阶梯**：失败分类为 taxonomy（timeout / malformed / failed；auth 排除且永不重试）；run 内最多 5 次指数退避（2s→4s→8s→16s→30s）；事件携带 `retry_in_ms`、`attempt` 序号、`[turn_retried]` 块；工具绝不重跑。
- **审批审计**：`approval_decision` 持久事件；approve 缺省时拒绝一切（保守默认）；denial 产生合成 aborted 输出供模型反应。
- **中途 steering**：`session.steer()` 排队用户消息，下次输入组装时以 `[user_steering]` 块投递；作为真实用户输入写入 Trace。
- **Subagent 边界**：子消息进各自 Session 的 Trace，父 Trace 仅留单个 `subagent` 指针事件（记子 Session id）。
- **Compaction**：上下文压缩时 Trace 轮转（一文件=一个完整模型上下文）；压缩请求保持工具集不变以命中 prompt cache；中途崩溃的压缩在下次加载时补写 `compaction_end(failed)` 并丢弃半写摘要。
- **模型切换**：开新 Session + `[model_switch_from]` 来源块，不跨模型注入历史（fidelity 无法跨模型），由模型按需读源 Trace。
- **并发模型**：单 Session 同时只跑一个 Task；并发请求拒绝（409）。

## 对本项目的印证（已做对的）

| 我们的设计 | 对标印证 |
|---|---|
| run_events 持久事件 + 仅直播的合成事件分离 | dsh 双事件平面；disposal 不是第三种状态 |
| 条件 SQL transition + fencing token | LangGraph 提交判据；Penguin request_end 判据 |
| 会话锁单会话串行活动 Run | Penguin 409 并发拒绝；dsh turn 串行 |
| stale_run 恢复（start 时无活跃执行器 → FAILED） | dsh interrupted 由持久层合成；Penguin 恢复重放已提交轮次 |
| adapter 为唯一新 seam | dsh 能力缝三角色（Definition/Provider/Consumer） |
| raw payload standard 提取 + digest | Penguin fidelity 佐证 raw 原始信封（debug 策略）必要性 |
| 迁移链单调递进、无兼容垫片 | dsh 预发布立场：foundation over blast radius |

## 收敛的候选改进（按性价比排序）

| # | 改进 | 证据来源 | 规模 | 状态 |
|---|---|---|---|---|
| 1 | Fail-closed 事件词汇表：读时校验 event_type，未知类型拒绝/显式标记而非静默放行 | dsh | 小 | 实施中 |
| 2 | 结构化终止原因 + interrupted 标记：崩溃恢复合成与真实失败区分；replay 可识别恢复来源 | dsh + Penguin | 中 | 实施中 |
| 3 | cancel 等待 quiescence：transition 后 await 驱动器退出 | dsh 防御模式 | 小中 | 待办 |
| 4 | 协议级重试分类 + 退避阶梯 + attempt/retry_in_ms 事件 | Penguin | 中 | 待办 |
| 5 | raw payload debug 策略：原始信封逐字节加密保存、过期清理（fidelity 证据强化必要性） | Penguin + dsh | 既定待办（第五增量第 2 项） |
| 6 | 审批决策持久审计事件；缺省拒绝的保守默认 | Penguin + dsh | 后续增量 |
| 7 | Model-visible ⟺ logged 不变式；历史从事件流派生 | dsh + Penguin | 长期 |
| 8 | Waterfall 拦截点（pre-step/request/tools） | dsh | 长期 |
| 9 | Fork 边界语义：显式 boundary + 种子标记（session/end-seed 等价物） | dsh | 后续增量 |
| 10 | Subagent 指针事件模式 | Penguin | 后续增量（Group Task adapter） |
| 11 | 中途 steering / inbox 队列 | Penguin + dsh | 后续增量 |
| 12 | Compaction 上下文轮转 | dsh + Penguin | 长期 |

## 不采纳项

- **不引入** `@prismshadow/penguin-core` 或 TypeScript 双运行时：我们是 Python/FastAPI 栈，仅借鉴语义。
- **不采纳** dsh 的插件树/Cordis 组合体系：超出本切片范围，adapter 单 seam 已足够。
- **不采纳** Penguin 的文件型 Trace 存储：SQL 事件表提供条件更新与 fencing，优于 JSONL 追加语义；但"单写入路径串行 + 提交判据"思想已体现在 RunStore。
