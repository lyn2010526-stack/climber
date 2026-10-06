# Pi 双层 Loop 长任务引擎落地方案（2026-10-04）

> 用户主任务：对齐 Codex 桌面工作台，开发基于 pi-agent 双层 runLoop 的简易智能体项目。
> 参考源：`/tmp/opencode/pi`（earendil-works/pi，agent-loop.ts:163-321 双层循环 + agent.ts:188-613 Agent 状态机）、
> `/tmp/opencode/harness`（deepseek-harness，一切皆插件 / agent-loop）、`/tmp/opencode/codex_ui_spec.md`（codex TUI spec）。
> 本文件是长任务进度锚点，每实现一项更新状态。

## 1. Pi 双层循环语义（对齐基准）

来源：`packages/agent/src/agent-loop.ts:163-321`（`runLoop` 双层 while）+ `agent.ts:299-306`（steer/followUp 双队列）。

```
外层 while True:
    hasMoreToolCalls = True
    内层 while hasMoreToolCalls or pendingMessages:
        - 组装上下文（steering 消息先入队）
        - 流式 LLM 调用（streamAssistantResponse）
        - 解析 tool_calls；有则执行工具（串/并行），回填 toolResult
        - hasMoreToolCalls = 本批还有工具调用
        - 检查 steering 队列，有则注入继续
    # 内层退出，Agent 本要停：检查外层继续条件
    follow_up = pollFollowUp()
    若有 follow-up 或 explicitContinuation: continue 外层
    无：break → agent_end
```

两条队列语义（Pi `agent.ts:299-306`）：

| 队列 | 生命周期 | 典型场景 | Pi 方法 |
|---|---|---|---|
| Steering | 内层循环中途注入，打断当前工具链，立即改当前任务 | 运行时插话"不要改这个文件" | `agent.steer()` |
| Follow-up | 外层循环在 agent 本要停时触发下一轮，续命长任务 | 用户/Agent 预排"完成后提交代码" | `agent.followUp()` |

Pi 的关键内置数：steering 可配置轮询间隔并入工具执行中（interruptible tools）；`finishTurn` hook 可返回 `{action: "continue"/"end"}` 驱动显式续跑；`runLoop` 结束时才发 `agent_end`。

## 2. Climber 现状与差距（gap analysis）

### 2.1 现状（已核实）

- 内层循环已有：`app/core/engine/runner.py:137-323` `iteration_loop`，ReAct「LLM→工具→回填」，上限 `session.max_iterations`（默认 10），**模型不再返回 tool_call 即停**（:299-306）。
- steering 已有：`runner.py:179,300` 消费 `SessionInputQueue.claim(kind="steering")`（`input_queue.py:110-123`），注入为 USER 消息。
- 外层循环已有雏形：`app/core/agent_engine.py:315-400` `while True`，每轮（TURN）结束后 `claim("follow_up")`（:390），有则开新轮，空则 break。
- 双队列表已存在：`SessionInput`（kind=steering/follow_up，status queued/started/applied/completed/blocked/failed）。
- 无进展检测已有（内层）：空响应两次（`runner.py:261-277`）、只读工具批重复两次（:287-296）→ PAUSED。
- 前端已消费 steering/follow_up：`useChat.ts:221-242` submitInput、`api.ts:539-541` startSessionInputs。

### 2.2 差距（本次要补的）

| # | 差距 | 现状 | 目标（对齐 Pi + 用户要求） |
|---|---|---|---|
| G1 | **Agent 自生成 Follow-up** | follow-up 只能用户外部提交；代理不能自己排下一个子任务 | 内层正常结束后，Agent 自动决策是否生成下一个子任务并写入 follow-up 队列，自动续跑，无需用户输入"继续" |
| G2 | **外层无进展暂停** | 无进展检测只在内层单轮内；外层 follow-up 可无限续跑 | 连续两轮整体任务无进展 → 禁止生成新 follow-up，暂停循环，输出全部状态等待人类 |
| G3 | **轮级状态输出契约** | 只有 TURN_STARTED/TURN_DONE + RUNTIME_REPORT | 每轮结束输出：当前进度、已完成列表、Follow-up 待执行队列（用户第 5 条） |
| G4 | **模型续跑决策事件** | 无 | 内层退出后的"是否自续跑"决策需有事件（LOOP_DECISION/PENDING_FOLLOWUP），前端可见 |
| G5 | **队列清空才结束** | 外层 break 即是结束，无显式空队列判定 | follow-up 队列清空才 `agent_end`（用户第 6 条） |
| G6 | **steering hot-inject**（可选） | steering 只在迭代边界消费；工具执行中不轮询 | 工具执行期间可注入（Pi interruptible）；低优先 |

## 3. 设计：Pi-compatible 双层 Loop

### 3.1 总体结构

```
agent_engine.run (外层驱动，已有 while True)
  └─ run_locked
       └─ iteration_loop = 内层 ReAct（已有）
            └─ 正常退出（无 tool_call 且无 steering）后：
                 └─ NEW agent_continue_decision 步骤（G1）
                      模型决策：finished? / next_subtask?
                      ├─ finished(yes)      → 不排 follow-up → 外层 claim follow_up 若无 → break(agent_end)
                      └─ next_subtask(yes)  → 写 SessionInput(follow_up, source=agent) → 外层下一轮续跑
```

新增的 `agent_continue_decision` 是内层与总部之的"续命闸门"，语义对应 Pi 外层循环的 `getFollowUpMessages()` + `finishTurn{action}`。

### 3.2 续跑决策产生器（G1）

位置：runner.py 新增 `maybe_generate_followup(engine, session, result)`，在 `runner.py:299-306` 无 steered 且将 break 前调用。

规则（严格按用户约束）：
1. **只读不写改文件**：决策本身只是"生成下一个子任务描述"，不直接改文件；文件修改默认需审批（见 §4）。
2. **禁止无进展自续跑**：外层维护 `followup_no_progress` 计数。判定准则：
   - 本轮完成的可持久化工作（工具批有副作用、消息有实质新内容）视为进展；否则计入无进展。
   - 连续 2 轮无进展 → 强制暂停，清空自生成 follow-up，发 `RUNTIME_REPORT{paused, reason:"no_progress"}` + 全状态输出，等待人类。
3. **消耗预算**：复用 `session.max_iterations` 作为整体轮上限（外层轮数 ≤ max_iterations），撞顶转 PAUSED（沿用 max_iterations_reached 语义而非失败）。
4. 决策调用使用轻量提示 + 结构化输出（让模型返回 `{"finished": bool, "next_subtask": str|None, "reason": str}`）；不追加到 session.messages 主链，单独走 run_llm_single 防止污染上下文。
5. 生成 next_subtask 时用 `client_request_id = "agent-followup:" + uuid` 投递，落 `SessionInput(kind="follow_up")`。

### 3.3 外层无进展暂停（G2）

- 状态机：新增 `TaskState` 分支沿用 PENDING/RUNNING/PAUSED（不新增枚举，配合既有 runner PAUSED 语义）。
- 暂停输出：`PROGRESS{paused, reason}` + `RUNTIME_REPORT`（含全部队列状态）→ 等待用户 resume（复用 `POST /sessions/{id}/inputs/resume` 或 `/inputs/start`）。
- 恢复后清空无进展计数。

### 3.4 轮级状态输出（G3）

在 TURN_DONE 之后新增 `LOOP_STATUS` 事件（`app/core/__init__.py` AgentEventType 新增）：

```json
{
  "type": "loop_status",
  "data": {
    "outer_round": 3,
    "current_input": "<当前子任务>",
    "completed": ["subtask1", "subtask2"],
    "followup_queue": ["subtask3", "subtask4"],   // 含 user + agent 来源
    "steering_queue": [],
    "no_progress_count": 1
  }
}
```

来源：`SessionInputQueue.report()`（input_queue.py:125-149）+ 外层循环计数累积；前端渲染到 `LOOP_STATUS` 卡片（参考 deepseek-harness 的 agent-loop 事件流展示）。

### 3.5 队列清空才结束（G5)

`agent_engine.run` 外层 break 条件改为「claim follow_up 返回空 且 无 agent 自续跑挂起」；发 `agent_end`（映射为现有 DONE{status:completed}）+ 终结 LOOP_STATUS（followup_queue 空）。

### 3.6 事件协议扩展（G4）

`AgentEventType` 新增枚举（维持向后兼容，前端 normalizeChatEvent 未知事件归 unknown 不崩）：
- `LOOP_STATUS = "loop_status"`

## 4. 文件修改审批约束（用户第 4 条，产品行为）

- 任何文件新增/修改默认需展示变更内容等待确认才执行——接入现有审批栈（`permission_rules.py` / `engine/validation.py` / 前端 `FloatingPermissionDialog`）。
- 在 `agent_continue_decision` 决策后、执行 next_subtask 前，若涉及文件写操作则进入审批队列（blocked 状态），审批通过再继续。
- 决策本身不触发审批（只读推理）。

## 5. 前端落地（deepseek-harness 思考显示 + codex/中国审美）

- ChatInterface 新增「长任务循环面板」：轮数徽标、当前子任务、已完成列表、Follow-up 队列待办（LOOP_STATUS 驱动）。
- 思考显示参考 deepseek-harness `docs/user/guide` 的 agent-loop 事件流 + codex 思考档位胶囊（已有 ThinkingLevelSelect）；视觉保持现有 Codex 主题（纯白 + teal `#1F7A8C`），禁用暖灰近黑覆盖。
- Steering/Follow-up 输入框已有（AnchoredComposer 运行中输入），补充"Agent 自动续跑中"指示态。

## 6. 实施任务清单（派发）

1. [ ] 内层续命闸门 `maybe_generate_followup`（G1/G4）：runner.py + 轻量决策提示词 + 结构化解析。
2. [ ] 外层无进展计数与暂停（G2）：agent_engine.run 外层维护计数 + PROGRESS/RUNTIME_REPORT 输出。
3. [ ] LOOP_STATUS 事件与队列快照（G3/G5）：AgentEventType + input_queue 快照 + 外层 agent_end 终结。
4. [ ] SessionInput agent 来源与去重（G1 依赖）：client_request_id 前缀 + list 展示 source 标记。
5. [ ] 前端循环面板与事件消费（G5 依赖 G3 事件）：LOOP_STATUS 渲染 + 无进展暂停指示 + auto-continue 态。
6. [ ] 审批约束接线（文件修改等待确认）。
7. [ ] 测试：后端 `tests/core/test_engine_pi_dual_loop.py`（自续跑、无进展暂停、队列为空才结束、steering 打断续跑）+ 前端组件测试。
8. [ ] 回归：后端 pytest 分批、前端 typecheck/vitest、视觉复核。

## 7. 验证命令

```bash
# 后端定点
cd /workspace/climber && source venv/bin/activate
python3 -m pytest tests/core/test_engine_pi_dual_loop.py -q

# 前端
cd frontend-react && ./node_modules/.bin/vitest run src/components/agent --maxWorkers=1
npm run typecheck
```