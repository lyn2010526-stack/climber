# Climber 统一实施计划

> 基于 5 份需求文档和当前代码现状，整合为单一可执行路线图。
> 创建日期：2026-07-30
> 更新日期：2026-07-30（根据代码审计调整）

---

## 一、总体定位

**产品愿景**：纯本地、无云、离线可用的个人 AI Agent 工作台

**核心差异化**：
- 纯本地 SQLite 存储，数据绝对可控（对标 OpenClaw 本地优先架构）
- 三层安全沙箱（L1 静态分析 / L2 exec 进程隔离 / L3 Docker 容器）
- 四层记忆系统（L0 瞬时工作 / L1 情景 / L2 项目持久 / L3 全域 RAG）
- L0-L3 分层提示词体系（基座不可篡改 + Skill 动态加载 + 会话临时指令 + 用户输入）
- MCP + Skill 双生态，支持工具粒度权限管控
- 多智能体协作（规划 / 执行 / 审计角色化）
- 可观测运维（全链路 Trace + Token 仪表盘 + 告警）

---

## 二、已完成成果（不需要再做）

### 2.1 P0 核心链路修复
- Doctor 诊断端点、认证机制、token 传播、guest 模式、Sessions/Chat/Health API
- MCP SDK 迁移、注册表统一、群组协作运行时修复

### 2.2 状态持久化
- Checkpoint 持久化：`SQLiteCheckpointStore` 替换内存存储
- Session 状态机持久化：`TaskState` 写入数据库
- Turn 生命周期：独立 Turn 实体，支持暂停/恢复/取消

### 2.3 记忆系统
- MemoryItem.from_orm() wiring bug 修复
- MemoryToolSet ContextVar 注册修复
- 记忆衰减接入 cleanup 周期任务
- WorkingMemory L1 结构化
- IdentityMemory L4 接入 PromptEngine Layer 0
- 统一记忆协调器 HierarchicalMemory

### 2.4 安全沙箱 Phase 1-3
- L1 StaticAnalyzer：编码绕过检测、路径遍历、shell 注入、JSON Schema
- L2 ProcessSandbox：exec 替代 shell、资源限制（RLIMIT）、超时控制
- L3 DockerSandbox：ephemeral 容器、只读文件系统、网络隔离、资源配额
- SafetyPipeline 统一入口 + SafetyConfig

### 2.5 Phase A：单机稳定性（已全部完成）
- A1 浏览器池化：`browser_pool.py` — BrowserPool 最大 2 实例，LRU 淘汰，空闲 5 分钟回收，sweeper 后台任务
- A2 全局异常落盘：`logging_setup.py` — crash dump 写 `logs/crashes/`，error.log 轮转，敏感信息脱敏
- A3 Scheduler 看门狗：`watchdog.py` — scheduler + auto_loop 心跳检测，停止自动重启
- A4 SQLite 加固：`storage/__init__.py` — WAL 模式 + busy_timeout + 64MB cache + foreign_keys
- A5 内存治理器：`memory_guardian.py` — psutil 监控，超阈值触发 GC + 浏览器回收
- A6 Trace 模型：`core/tracing.py` — TraceStore + Span + SpanStatus/SpanKind，`models_traces.py` 持久化

### 2.6 Phase B：上下文治理与模型网关（已全部完成）
- B1 上下文预算：`compressor.py` — ContextCompressor + estimate_tokens + SUMMARIZE/SLIDING/TRUNCATE 策略
- B2 模型别名网关：`model_gateway.py` — ModelGateway + ModelCapability + 任务类型路由
- B3 多模型自动切换：Circuit Breaker + 故障自动 failover + 按任务类型选模型
- B4 本地通知：`utils/notifications.py` — notify-send(Linux) / osascript(Mac) / PowerShell(Win)

### 2.7 Phase C：前端 UI（大部分已完成）
- C1 弹性三栏布局：`WorkspaceLayout.tsx` + react-resizable-panels
- C2 结构化消息渲染：`MessageRenderer.tsx` + @tanstack/react-virtual
- C3 Token 仪表盘：`TokenDashboard.tsx`
- C4 人工干预节点：`InterventionNode.tsx` + `InlineApproval.tsx` + `NativeApprovalDialog.tsx`
- C5 Skill 编辑器：`SkillEditor.tsx`
- C6 MCP 管理面板：`MCPManagementPanel.tsx`
- C7 记忆知识库编辑器：`MemoryKnowledgeBase.tsx`
- 额外已完成：CommandPalette、GlobalSearch、ContextMenu、SnapshotTimeline、SessionSidebar、DiffView、ReasoningPanel、ControlBar、StreamingIndicator、TaskChecklist、AutonomySlider、PermissionModeToggle

### 2.8 Phase D：L0-L3 提示词体系（部分完成）
- L0 基座提示词：`prompt_engineering.py` — 正负 Few-shot 样例 + 逃逸防御 + 统一分隔符
- L1 Skill 提示词：`prompt_engine/` — engine.py + models.py + template_repository.py
- Escape Defense：ESCAPE_PATTERNS 正则匹配 + 逃逸检测
- 四层分隔符：build_delimited_prompt() L0/L1/L2/L3 隔离

### 2.9 Phase E：多智能体协作（部分完成）
- Agent 角色化：`multi_agent/__init__.py` — AgentRole + AgentTask + TaskStatus
- Handoff 机制：`group_collaboration.py` — handoff_task() + HandoffMessage
- DAG 任务规划：`task_dag.py` — TaskDAG + TaskNode
- Crew 编排：`multi_agent/crew.py` — Crew 类，支持多 Agent 协作

---

## 三、待实施任务（按优先级）

### Phase D+：Skill 生态完善（1-2 周）

> 目标：Skill 可导入导出分享，支持 URL 安装

| # | 任务 | 当前状态 | 工作量 |
|---|---|---|---|
| D1 | **Skill 标准 JSON 包格式**：定义 `.skill.json` schema（名称/版本/依赖/提示词/风险等级/MCP清单/工具黑白名单） | 有 registry 但无标准包格式 | 3 天 |
| D2 | **Skill 导入导出**：序列化/反序列化 Skill 为可分享 JSON 包 | 未实现 | 2 天 |
| D3 | **本地技能包管理器 CLI**：`climber skills list/install/update/uninstall` | 未实现 | 3 天 |
| D4 | **URL 安装**：从 GitHub/Gitee URL 下载 Skill 包并安装 | 未实现 | 2 天 |
| D5 | **高危 Skill 权限管控**：逆向/渗透类标记高危，需管理员解锁 | 有风险等级字段但未强制 | 2 天 |

**验收标准**：
- `climber skills install https://github.com/user/skill-repo` 一键安装
- 导出 Skill 为 JSON 文件，可分享给他人安装
- 高危 Skill 安装时需管理员密码确认

---

### Phase E+：多智能体协作增强（2-3 周）

> 目标：规划/执行/审计角色化，结果交叉校验

| # | 任务 | 当前状态 | 工作量 |
|---|---|---|---|
| E1 | **角色化 Agent 模板**：预定义 Planner/Executor/Auditor/Researcher 角色模板 | 有 AgentRole 但无预定义模板 | 3 天 |
| E2 | **自省审计子模块**：每 N 轮强制反思，核对原始需求，检查执行偏差 | 有 metacognition 模块但需增强 | 4 天 |
| E3 | **结果聚合与交叉校验**：多 Agent 并行执行后结果自动合并，差异时告警 | 未实现 | 4 天 |
| E4 | **DAG 可视化**：前端展示任务依赖图和执行状态 | 有 TaskDAG 但无前端可视化 | 3 天 |

**验收标准**：
- 用户设定目标后，Planner 自动拆分子任务，Executor 并行执行，Auditor 校验结果
- 前端可看到 DAG 任务图和每个节点的执行状态
- 多 Agent 结果有差异时自动告警

---

### Phase F+：部署体验完善（1-2 周）

> 目标：一键启动，离线可用

| # | 任务 | 当前状态 | 工作量 |
|---|---|---|---|
| F1 | **诊断工具 `climber doctor`**：一键检查环境、依赖、端口、数据库、模型连通性 | 有 /health 端点但无 CLI 工具 | 2 天 |
| F2 | **离线 PWA**：前端缓存静态资源，断网可对话（Ollama 本地模型） | 未实现 | 3 天 |
| F3 | **前端状态持久化增强**：Zustand store → localStorage，审批/任务进度刷新不丢 | 部分实现 | 2 天 |

**验收标准**：
- `climber doctor` 输出 HTML 诊断报告
- 断网后仍可访问前端并与本地 Ollama 模型对话
- 刷新页面后审批队列和任务进度不丢失

---

### Phase G：代码质量与架构收敛（2-3 周）

> 目标：清理重复实现，统一接口，提升可维护性

| # | 任务 | 当前状态 | 工作量 |
|---|---|---|---|
| G1 | **合并重复 PluginManager**：`plugin_system.py` / `mcp.py` / `registry.py` 三选一 | 3 套实现并存 | 3 天 |
| G2 | **合并重复 Sandbox**：`security_sandbox.py` / `sandbox.py` 统一 | 2 套实现 | 2 天 |
| G3 | **统一 Memory 接口**：PersistentMemory / HierarchicalMemory / WorkingMemory 统一为 MemoryBackend 协议 | 3 套实现 | 4 天 |
| G4 | **前端 API Client 收敛**：50+ 处散点 fetch 统一为类型安全 ApiClient | 大量 any + 散点 fetch | 5 天 |
| G5 | **AgentEngine 拆分**：684 行按职责拆分为 SessionManager / TurnExecutor / CheckpointManager / TaskManager | 单文件巨人 | 5 天 |

**验收标准**：
- Plugin/Sandbox 各只有一套实现
- 前端所有 API 调用通过统一 ApiClient
- AgentEngine 拆分为 4 个独立模块，每个 < 200 行

---

## 四、路线图（调整后）

| 阶段 | 内容 | 时间 |
|---|---|---|
| 立即 | Phase D+：Skill 生态完善 | 1-2 周 |
| 短期 | Phase E+：多智能体协作增强 | 2-3 周 |
| 短期 | Phase F+：部署体验完善 | 1-2 周 |
| 中期 | Phase G：代码质量与架构收敛 | 2-3 周 |

---

## 五、关键设计原则

1. **先阅读成熟方案，再实现**：每个任务开始前，先查阅参考项目的对应源码，梳理业务流程/数据结构/状态流转，再动手。
2. **不重复造轮子**：优先用开源项目已验证的方案，不凭空自创复杂机制。
3. **真实实现，不是空壳**：每个功能必须有真实逻辑，禁止假状态、假数据、提示词包装。
4. **分阶段可回滚**：每完成一个 Phase 跑全量回归，确保不破坏已有功能。
5. **本地优先**：所有数据 SQLite 文件存储，不引入 Redis/Postgres 强依赖。
6. **最小侵入**：不动 `AgentEngine.run()` 签名、不动现有消息循环、不动 SSE 流式响应，新功能通过依赖注入接入。

---

## 六、风险与约束

- 访问同一 SQLite 测试库的 pytest 测试域必须串行执行，避免 teardown 竞争
- Docker 测试在不可用环境下自动跳过（已做降级处理）
- 工作树当前不干净（大量未提交修改），每完成一个 Phase 提交一次
- 循环必须有硬上限（审查最多 5 轮、假设路径最多 3 条）
