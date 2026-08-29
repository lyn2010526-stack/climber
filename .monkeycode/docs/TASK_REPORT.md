# Climber 深度任务报告 — Architecture V2 与 Run 协议收口

- 生成日期：2026-08-29
- 分支：`fix-squash`
- 覆盖范围：本次会话全部任务（架构补充文档 A/B + 历史工作收口）

---

## 1. 任务总览

本轮完成三大块工作，全部通过验证并提交：

| 任务域 | 对应 Spec | 完成度 | 提交 |
|---|---|---|---|
| Architecture V2 核心模块（10 大模块） | `architecture-v2-core` | 21/21 | `ec6eb156` |
| 统一 Agent Run 协议 | `unified-agent-run-protocol` | 45/45 | `7205c3c1` `987047c4` |
| 历史工作收口（前端/部署/文档/进化记录） | — | 219 文件 | `e8c4975a` `1912f420` `a6e9920d` |

---

## 2. Architecture V2：10 大模块实现

输入为两份架构补充文档，核心诉求包括"插件化内核""自学习闭环""四层记忆""等效无限上下文"。

### 2.1 插件内核 `app/core/plugin_kernel/`（703 行）

- **PluginKernel** 只做三件事：
  1. 生命周期管理：卸载时反向撤销全部注册（零孤儿）
  2. 依赖注入：声明依赖自动按序挂载 / 反向卸载
  3. 类型化事件总线：订阅 / 发布 / 请求-响应，发布自动写 append-only 日志
- **配置即产品形态**：`set_profile` / `profile_delta` 支持 minimal / complete / offline / developer 四模式运行时切换，不重启
- 全组件插件化：模型适配器、自动化通道、沙箱、工具注册表、会话存储、Agent 主循环、感知、记忆、技能加载器、UI 面板均为插件

### 2.2 四层记忆 `app/core/four_layer_memory/`（529 行）

| 层级 | 实现 | 特性 |
|---|---|---|
| 短期 | `short_term.py` | 滑动窗口，记录式 evicted_turns（出窗可查） |
| 中期 | `medium_term.py` | 任务级记忆 |
| 长期 | `long_term.py` | MEMORY.md + USER.md 冻结快照注入，更新需用户确认 diff |
| 技能库 | `skill_store/` | 元数据常驻 + 内容按需加载 |

FTS5 索引 `fts5_index.py` 提供全文检索（FTS5 语法错误自动退化 LIKE）。

### 2.3 超长上下文「等效无限」`app/core/long_context/`（768 行）

6 方案全部实现：
1. RAG（`rag.py`，sqlite-vec 或 FTS5 回退，embedding 用 sha256 确定性回退）
2. 滑动窗口 + 自动摘要（`sliding_window.py`）
3. 分层记忆
4. 子 Agent 隔离
5. 上下文压缩（`compression.py`）
6. 外部状态 + 工具查询（`external_tools.py`）

固定 32K 预算裁剪次序（`budget.py`）：`tool_results > recent_turns > rag_results > history_summary > skill_index > long_term_memory`。`prefix_cache.py` 提供前缀缓存。

### 2.4 闭环自学习 `app/core/self_learning/`（483 行）

- **L1** `l1_realtime_fix.py`：出错实时修正技能文件，最多重试 3 次，版本历史可回滚
- **L2** `l2_distill.py`：复杂任务（>=3 步）后台蒸馏成 Markdown 技能
- **L3** `l3_steward.py`：技能库 >=10 或每 7 天审查（合并 / 归档 30 天未用 / 更新描述 / 可回滚报告）；成功率 <60% 自动标记进入 L1 队列

### 2.5 统一能力抽象 `app/core/capability/`（701 行）

- `CapabilityMeta`：ID / 名称 / 描述 / 类型 / 输入输出 JSON Schema / 成本画像 / 成功率 / 前置 / 副作用 / 可执行判断
- 7 类包装器（`adapters.py`）：本地工具 / MCP / Skill / HTTP / 子 Agent / 模型 / 感知
- 注册表（`registry.py`）：按成功率 0.5 / 成本 0.3 / 用户偏好 0.2 排序路由，失败 fallback 最多 3 个
- 能力市场（`market.py`）：`.cap` 打包，启动只加载核心 10 个，其余懒加载 + LRU 容量 50

### 2.6 事件溯源与观测 `app/core/integration/` + `trace_log/`

- 全链路 append-only 事件日志（`trace_log.py`，10 类事件），支持 Resume / Fork / Search / Replay / Trajectory 视图，JSONL 逐会话轮转
- 事件溯源（`event_sourcing.py`）：共享单一事件流 list，多 store 投影一致；轨迹归档用 `.archived` 后缀保留可回滚性

### 2.7 接线与开关

- `app/config.py`：`enable_arch_v2` master + 8 模块开关 + `is_arch_v2_active(name)`
- `.env.example`：9 个开关变量
- `app/main.py`：`_init_arch_v2()` / `_stop_arch_v2()` 接入 lifespan，实测全模块可实例化与关停

---

## 3. 统一 Agent Run 协议

核心需求：所有 Chat Turn 使用统一 Run 生命周期，兼容现有 SSE 契约。

### 3.1 协议核心 `app/core/run_protocol.py`（838 行）

- `RunStatus` / `RunRecord` / `RunEvent` / `MessageEnvelope` / `StartRun` / `ResumeRun` / `RunHandle` / `ReplayPage`
- 统一状态转换表 + 结构化状态冲突错误（`RunStateConflictError`）
- 事件幂等（`(run_id, event_id)`、`(run_id, sequence)` 唯一约束）、execution token fencing、终态 fencing
- `list_runs` / `RunPage`（session/status/user 过滤，offset 分页）
- `attach_checkpoint` 关联校验（`CheckpointScopeMismatchError`）

### 3.2 存储双实现

- `app/storage/run_store.py`（609 行）：SQLAlchemy RunStore，条件更新实现状态转换，事务内序号分配实现事件幂等
- 内存 fake 复用相同状态与错误语义

### 3.3 配套能力

- `agent_run_adapter.py`：AgentEngine adapter，`current_turn_id` 关联 `run_id`，`AgentEvent` 映射持久化 `RunEvent`
- `event_replay.py`：有界事件缓冲 + gap 检测 + 回放
- `raw_payload.py`：`standard` 策略（脱敏/摘要/截断）+ `debug` 策略（Fernet 加密全量载荷、`expires_at` 过期、清理）
- `run_cleanup.py`：陈旧 Run 回收（>max_age 置 FAILED，error code `stale_run`）+ 过期载荷清理，watchdog 周期任务
- `/api/v1/runs`：7 个管理端点（详情/列表/事件/cancel/resume）

### 3.4 Chat 兼容接入

- `chat.py` 切换统一运行时，保持现有事件名和数据字段，replay 走持久化事件并补充 `run_id`
- `agent_engine.py` 新增公共访问器：`get_session` / `register_session` / `get_session_lock` / `drop_session_lock` / `has_active_session`（消除 API 层直访私有属性）

---

## 4. 遗留问题修复

| 问题 | 根因 | 修复 |
|---|---|---|
| 预存失败测试 `test_chat_applies_model_override_to_in_memory_session` | 历史 chat.py 重构改用 `engine.get_session()`，测试 mock 的 Engine 缺该方法 | 补 `get_session`/`register_session` mock，与真实 AgentEngine 一致 |
| `.gitignore` 误吞核心文件 | `run_*.py` 未锚定根目录，匹配任意深度，导致 `app/core/run_protocol.py`、`app/storage/run_store.py`、`app/core/run_cleanup.py` 从未入库 | 改为 `/run_*.py` 仅匹配根目录 |

---

## 5. 验证证据

### 5.1 后端全量回归

```
1964 passed, 16 skipped in 1366.01s (0:22:46)
EXIT=0
```

基线演进：2026-08-10 `1487/50/0` → 2026-08-21 `1660/16/0` → 2026-08-29 `1964/16/0`

### 5.2 定向回归

- run 协议 10 套件：**85 passed**
- architecture-v2 新测试 8 文件：**56 passed**
- emergent + hard_guard：通过

### 5.3 前端

- vitest：**50 文件 / 205 passed**
- tsc `--noEmit`：无错误

### 5.4 静态检查

- ruff：全部新模块 `All checks passed!`

---

## 6. Git 提交明细（本次收口）

| 提交 | 内容 | 规模 |
|---|---|---|
| `ec6eb156` | architecture-v2 10 大模块 + 接线 + specs | 50 文件 / +5542 |
| `7205c3c1` | run 协议 + middleware + 基础设施 | 51 文件 / +9673 |
| `987047c4` | chat/engine 接入 + API 域拆分 + 安全加固 | 62 文件 / +3857/-1155 |
| `e8c4975a` | 前端 iOS 化 + API 域模块 + 类型 + 测试 | 75 文件 / +2337/-826 |
| `1912f420` | 部署/CI/evolution/文档/tasks | 31 文件 / +1260/-140 |
| `a6e9920d` | specs tasklist 收口 | 1 文件 |

**合计：6 commit，270 文件变更，+22669 行**

---

## 7. 代码规模

| 维度 | 数值 |
|---|---|
| Python 后端 | 434 文件 / 87,566 行 |
| 测试文件 | 146 |
| 前端源文件 | 211 |
| 新增模块 | plugin_kernel(703) trace_log(367) four_layer_memory(529) skill_store(360) self_learning(483) capability(701) long_context(768) integration(189) emergent(1008) security(986) |

---

## 8. Specs 完成度

| Spec | requirements | design | tasklist |
|---|---|---|---|
| `architecture-v2-core` | 完成 | 完成 | 21/21 |
| `fourth-gen-emergent-modules` | 完成 | 完成 | 17/17 |
| `unified-agent-run-protocol` | 完成 | 完成 + research | 45/45 |

---

## 9. 残余风险与后续建议

- **RAG embedding** 当前为 sha256 确定性回退，生产部署应注入真实 embedding 函数（模型服务可用时）
- **run 事件表** 与既有 Turn 表存在关联，长线运行需关注序列号分配与归档策略（`.archived` 回滚保留机制已建）
- **能力市场** 启动只加载核心 10 能力，懒加载 LRU 容量 50，需在真实负载下验证缓存命中率
- **前端** iOS 化仍在进行（55+ 页面目标），本轮完成核心页面与测试基建，未全量 iOS 化
- **开源对标**：battle-plan.md Phase 2-7（LangGraph 兼容层、Mem0 集成、OPA、E2B、OpenLLMetry 等）为后续迭代方向，本轮未实施
