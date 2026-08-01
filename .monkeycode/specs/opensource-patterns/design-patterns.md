# Climber 开源项目设计模式吸收报告

> 基于 30 个开源 Agent 项目的代码级研究，提取可复用的设计模式、数据结构与状态流转规则。
> 所有实现将使用全新变量名与代码风格，标注参考来源，规避开源协议冲突。

---

## 一、任务调度器（参考：LangGraph + MonkeyCode）

### 1.1 核心状态机设计

**参考来源**：LangGraph `StateGraph` + MonkeyCode `Manager[I, S, M]`

```python
# 任务状态定义
class TaskState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 允许的状态转换矩阵
TRANSITIONS = {
    TaskState.PENDING: [TaskState.PROCESSING, TaskState.CANCELLED],
    TaskState.PROCESSING: [TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED],
    TaskState.PAUSED: [TaskState.PROCESSING, TaskState.CANCELLED],
    TaskState.FAILED: [TaskState.PROCESSING],  # 重试
}
```

**关键设计**：
- 状态存储在 SQLite（替代 MonkeyCode 的 Redis Hash）
- 每个状态变更记录 `from_state`、`updated_at`、`trigger`（触发源）
- 支持 Hook 链：状态切换前后执行自定义逻辑（日志、通知、清理）

### 1.2 有向状态图（DAG）执行引擎

**参考来源**：LangGraph `StateGraph` + `PregelLoop`

**核心数据结构**：
```python
@dataclass
class StateGraph:
    nodes: dict[str, NodeSpec]          # 节点名 → 可执行对象
    edges: list[Edge]                   # 确定性边
    branches: dict[str, Branch]         # 条件分支
    channels: dict[str, Channel]        # 状态通道（LastValue / Delta）
    checkpointer: Checkpointer          # 检查点存储

@dataclass
class NodeSpec:
    func: Callable                      # 可执行对象
    input_schema: type | None           # 输入模式
    retry: RetryPolicy | None           # 重试策略
    timeout: float | None               # 超时（秒）
    on_error: Callable | None           # 错误处理器

@dataclass
class Edge:
    source: str
    target: str | list[str]             # 多目标 = 扇入同步
    condition: Callable | None          # 条件函数
```

**执行模型**：
- **超级步（Superstep）**：每个超级步内，所有就绪节点并行执行
- **通道聚合**：节点输出通过 Channel reducer 聚合（LastValue / BinaryOperator）
- **动态路由**：节点可返回 `Command(target="next_node", update={...})` 动态决定下一跳

**Human-in-the-Loop**：
- `interrupt_before` / `interrupt_after` 配置
- 中断点持久化到检查点，支持恢复执行
- 恢复时通过 `Command(resume=...)` 携带用户输入

### 1.3 检查点快照机制

**参考来源**：LangGraph `checkpoint/` + OpenCode `Snapshot`

```python
@dataclass
class Checkpoint:
    thread_id: str                      # 会话/任务 ID
    step: int                           # 超级步序号
    channel_values: dict[str, Any]      # 所有通道快照
    channel_versions: dict[str, int]    # 通道版本号
    versions_seen: dict[str, dict[str, int]]  # 节点见过的版本
    pending_writes: list[PendingWrite]  # 待处理写入
    metadata: dict[str, Any]            # 元数据

@dataclass
class PendingWrite:
    channel: str
    value: Any
    write_id: str
    status: WriteStatus                 # pending / committed / rolled_back
```

**保存策略**：
- 每个超级步结束后生成快照
- 高频更新通道采用增量写入 + 定期全量快照
- 异步持久化，通过 future 链保证顺序

**恢复策略**：
- 从最新快照重建通道状态
- 重放 `pending_writes` 恢复未完成节点的写入
- 支持祖先链遍历（ancestor walk）重建 DeltaChannel

---

## 二、记忆系统（参考：Letta + Hermes-Agent + AgentScope）

### 2.1 三层记忆架构

**参考来源**：Letta `memory/` + AgentScope `memory/`

```python
class MemoryTier(Enum):
    CORE = "core"           # 常驻核心记忆（系统提示级）
    SESSION = "session"     # 短期会话记忆（对话历史）
    ARCHIVAL = "archival"   # 长期向量记忆（归档检索）
```

#### 2.1.1 核心记忆（Core Memory）

**数据结构**：
```python
@dataclass
class CoreMemoryBlock:
    label: str                          # 记忆标签（如 "persona", "user_profile"）
    value: str                          # 记忆内容
    limit: int = 4096                   # 字符限制
    description: str = ""               # LLM 注入提示
    read_only: bool = False             # 是否只读
```

**渲染方式**：在系统提示中以 XML 标签注入
```xml
<core_memory>
  <block label="persona">You are a helpful assistant...</block>
  <block label="user_profile">Name: Alice, Preference: Chinese</block>
</core_memory>
```

**LLM 自主管理**：提供 `core_memory_append` / `core_memory_replace` 工具，让 LLM 自主调用更新记忆

#### 2.1.2 会话记忆（Session Memory）

**数据结构**：
```python
@dataclass
class SessionMessage:
    role: str                           # user / assistant / system / tool
    content: str                        # 消息内容
    tool_calls: list[ToolCall] | None   # 工具调用
    timestamp: datetime
    token_count: int = 0                # Token 用量
```

**检索策略**：
- 默认返回最近 N 轮（如 10 轮）
- 支持关键词搜索（FTS5）和向量检索混合
- 分页查询，避免一次性加载过多

#### 2.1.3 档案记忆（Archival Memory）

**数据结构**：
```python
@dataclass
class ArchivalPassage:
    id: str
    text: str                           # 记忆文本
    embedding: list[float] | None       # 向量嵌入
    tags: list[str]                     # 标签
    metadata: dict[str, Any]            # 元数据
    archive_id: str                     # 所属档案 ID
    created_at: datetime
    access_count: int = 0                # 访问次数
    last_accessed: datetime | None = None
```

**存储策略**：
- 文本 + 元数据：SQLite `archival_passages` 表
- 向量：ChromaDB（本地优先）或 pgvector（PostgreSQL）
- 标签：JSON 列 + junction table 双写

### 2.2 记忆管理规则

**存取规则**：
- 核心记忆：直接更新内存 + 持久化到 `core_memory_blocks` 表
- 会话记忆：每轮对话后自动追加，支持软删除（`is_deleted`）
- 档案记忆：LLM 自主调用 `archival_memory_insert` 工具插入

**召回规则**：
- 语义相似度搜索（向量）
- 标签过滤（any/all 匹配）
- 时间范围过滤
- 结果按 `similarity × recency_score × access_count` 综合排序

**过期清理**：
- 访问次数衰减：`recency_score = 1.0 / (1.0 + days_since_access)`
- 低分记忆定期归档或删除
- 核心记忆字符超限时触发 LLM 压缩

### 2.3 自动反思机制（参考：Hermes-Agent）

**参考来源**：Hermes-Agent `background_review.py`

```python
@dataclass
class ReflectionResult:
    success_strategies: list[str]       # 成功策略
    problem_points: list[str]           # 问题卡点
    optimization_suggestions: list[str] # 优化建议
    related_experiences: list[str]      # 相关历史经验 ID
    should_save: bool                   # 是否值得保存
```

**执行流程**：
1. 任务完成后，fork 后台代理执行反思
2. 反思代理拥有工具白名单（只读查询，无副作用）
3. 输出结构化反思结果
4. 如果 `should_save=True`，将反思内容存入向量库
5. 新建任务时自动检索相似历史经验

---

## 三、安全机制（参考：OpenCode + Cline）

### 3.1 双模式权限系统

**参考来源**：OpenCode `permission/` + Cline `ToolPolicy`

```python
class AgentMode(Enum):
    PLAN = "plan"                       # 只读预览模式
    ACT = "act"                         # 真实执行模式

class PermissionLevel(Enum):
    DENY = "deny"                       # 禁止
    ASK = "ask"                         # 询问用户
    ALLOW = "allow"                     # 直接允许

@dataclass
class PermissionRule:
    action: str                         # read / write / execute / delete
    resource_pattern: str               # glob 模式
    level: PermissionLevel
    description: str = ""
```

**三层叠加合并策略**：
1. **默认安全基线**（`defaults`）：开箱即用的安全默认值
2. **Agent 级覆盖**：每个 Agent 基于默认值再做局部覆盖
3. **用户配置覆盖**（`user`）：用户在配置文件中定义的规则优先级最高

**关键默认规则**：
- `"*.env": ASK` - 环境文件默认询问
- `"external_directory/*": ASK` - 项目目录外操作询问
- `plan` 模式：`edit: DENY`、`execute: DENY`

### 3.2 工具执行安全策略

**参考来源**：Cline `src/core/tools/` + Open Interpreter `sandboxing/`

**JSON Schema 严格校验**：
```python
# Zod 驱动 JSON Schema 生成 + 运行时校验
class ToolInputSchema:
    @validator("input")
    def validate_with_zod(cls, v):
        return ToolInputUnionSchema.parse_obj(v)
```

**增量文件修改**：
- `apply_patch`：基于 patch grammar，只读写变更部分
- `edit_file`：`old_text` 唯一性校验，防止歧义
- `read_file_range`：支持分页读取，避免全文件加载

**权限拦截点**：
```python
class ToolSecurityPolicy:
    def check_permission(self, tool_name: str, args: dict) -> PermissionResult:
        # 1. 工具级开关检查
        if not self.tool_enabled(tool_name):
            return PermissionResult.DENY
        
        # 2. 资源路径检查
        if self.is_external_path(args.get("path")):
            return PermissionResult.ASK
        
        # 3. 危险命令检查
        if self.is_dangerous_command(args.get("command")):
            return PermissionResult.ASK
        
        return PermissionResult.ALLOW
```

**资源限制**：
- 单次 tool call input 上限：6000 字符
- 命令输出上限：48,000 字符（middle-truncation）
- 文件读取上限：2000 行 / 48,000 字符
- 执行超时：默认 10-30 秒

### 3.3 审计日志

**参考来源**：OpenCode `bus/` + Cline tool logging

```python
@dataclass
class AuditLog:
    timestamp: datetime
    session_id: str
    tool_name: str
    action: str                         # request / approve / deny / execute / error
    args: dict[str, Any]                # 工具参数（脱敏）
    result: str | None                  # 执行结果摘要
    duration_ms: float | None
    user_decision: str | None           # approve / deny / timeout
```

---

## 四、插件系统（参考：MonkeyCode Skill/MCP + Sidekick-AI）

### 4.1 Skill 数据结构

**参考来源**：MonkeyCode `backend/biz/skill/`

```python
@dataclass
class SkillRecord:
    id: str
    name: str
    description: str
    scope: SkillScope                   # global / team / user
    scope_id: str                       # global / team_id / user_id
    created_by: str
    active_version_id: str | None
    is_force_delivery: bool = False     # 强制投递
    is_orphan: bool = False             # 上游已删除但本地保留
    is_deleted: bool = False            # 软删除
    enabled: bool = True                # 平台管理员控制
    admin_description: str | None = None
    admin_tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime

@dataclass
class SkillVersion:
    id: str
    skill_id: str
    version: str                        # semver
    s3_key: str                         # 存储路径（本地为文件路径）
    parsed_meta: dict[str, Any] | None   # 从 SKILL.md frontmatter 解析
    created_at: datetime
```

**三级 Scope 体系**：
- `global`：全局可用，所有用户可见
- `team`：团队级，关联 `team_id`
- `user`：用户个人，关联 `user_id`

**查询逻辑**：
- 返回 `(用户选中 ID ∪ is_force_delivery=true)` 且未删除、有激活版本的 skill
- 按 scope 过滤，返回 disabled 行（供前端灰显）

### 4.2 MCP 服务器管理

**参考来源**：MonkeyCode `backend/biz/plugin/` + Sidekick-AI（概念）

```python
@dataclass
class MCPServerRecord:
    id: str
    name: str
    command: str | None                 # stdio 模式命令
    url: str | None                     # SSE/WebSocket 模式 URL
    args: list[str] | None
    env: dict[str, str] | None
    status: MCPServerStatus             # disabled / starting / running / error
    tools: list[MCPTool] | None         # 发现的工具列表
    created_at: datetime
    updated_at: datetime

@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]        # JSON Schema
    server_id: str
```

**生命周期管理**：
1. 创建：写入 `mcp_servers` 表，状态 `disabled`
2. 启动：`PluginManager._start_mcp_server()` 创建子进程 / SSE 连接
3. 工具发现：解析 `tools/list` 响应，注册到 `tool_registry`
4. 停止：关闭子进程 / 断开连接，注销工具
5. 删除：软删除记录

### 4.3 统一工具网关

**参考来源**：Sidekick-AI 概念 + MonkeyCode tool dispatch

```python
class ToolGateway:
    def __init__(self):
        self._builtin_tools: dict[str, Tool] = {}
        self._mcp_tools: dict[str, Tool] = {}
        self._skill_tools: dict[str, Tool] = {}
    
    async def execute(self, tool_call: ToolCall, ctx: ToolContext) -> ToolResult:
        # 1. 权限校验
        policy = self._evaluate_policy(tool_call.name, ctx)
        if policy == PermissionLevel.DENY:
            return ToolResult(error="Permission denied")
        
        # 2. 超时控制
        timeout = self._get_timeout(tool_call.name)
        
        # 3. 执行（内置 / MCP / Skill）
        tool = self._resolve_tool(tool_call.name)
        return await asyncio.wait_for(tool.execute(tool_call.arguments, ctx), timeout=timeout)
    
    def _evaluate_policy(self, tool_name: str, ctx: ToolContext) -> PermissionLevel:
        # 工具级开关
        if not self._is_tool_enabled(tool_name):
            return PermissionLevel.DENY
        # 资源路径检查
        # 危险命令检查
        # ...
```

---

## 五、多智能体协作（参考：CrewAI + AutoGen + AgentScope）

### 5.1 角色分工模型

**参考来源**：CrewAI `Agent` + AgentScope `Role`

```python
@dataclass
class AgentRole:
    id: str
    name: str                           # 角色名（如 "planner"）
    display_name: str                   # 显示名（如 "规划智能体"）
    description: str                    # 角色描述
    system_prompt: str                  # 系统提示词
    allowed_tools: list[str]            # 允许的工具
    allowed_models: list[str]           # 允许的模型
    max_iterations: int = 10            # 最大迭代次数
    allow_delegation: bool = False      # 是否允许委派
```

**三种执行模式**：

#### 5.1.1 Sequential（顺序链式）
```python
class SequentialCrew:
    def execute(self, task: str) -> str:
        context = f"## Task\n{task}\n"
        for role in self.roles:
            result = self._run_agent(role, context)
            context += f"\n--- {role.name} Output ---\n{result}\n"
        return context
```

#### 5.1.2 Hierarchical（层级管理）
```python
class HierarchicalCrew:
    def __init__(self, manager: AgentRole, workers: list[AgentRole]):
        self.manager = manager
        self.workers = workers
    
    async def execute(self, task: str) -> str:
        # Manager 分析任务，决定分配策略
        plan = await self._manager_plan(task)
        # 动态委派给 worker
        results = []
        for subtask in plan.subtasks:
            worker = self._select_worker(subtask)
            result = await self._run_agent(worker, subtask)
            results.append(result)
        # Manager 验证并汇总
        return await self._manager_summarize(results)
```

#### 5.1.3 Group Chat（群聊共识）
```python
class GroupChatCrew:
    async def execute(self, task: str) -> str:
        messages = [SystemMessage(f"Task: {task}")]
        for _ in range(self.max_rounds):
            for agent in self.agents:
                response = await agent.reply(messages)
                messages.append(response)
                if self._is_consensus_reached(messages):
                    return self._extract_final_answer(messages)
        return self._extract_final_answer(messages)
```

### 5.2 通信协议

**参考来源**：AgentScope `Message` + AutoGen `CloudEvents`

```python
@dataclass
class AgentMessage:
    id: str
    sender: str                         # 发送者角色 ID
    receiver: str | None                # 接收者角色 ID（None = 广播）
    content: str                        # 消息内容
    attachments: list[Attachment]       # 附件（代码、文件、工具结果）
    metadata: dict[str, Any]            # 元数据（token 用量、耗时等）
    timestamp: datetime
    reply_to: str | None = None         # 回复的消息 ID

@dataclass
class ToolResultAttachment:
    tool_name: str
    arguments: dict[str, Any]
    result: str
    error: str | None
    duration_ms: float
```

---

## 六、工具执行系统（参考：Cline + Open Interpreter + TaskWeaver）

### 6.1 工具调用生命周期

**参考来源**：AgentScope `ToolCallBlock` + Cline `tools/`

```python
class ToolCallStatus(Enum):
    PENDING = "pending"
    ASKING = "asking"                   # 等待用户确认
    ALLOWED = "allowed"
    EXECUTING = "executing"
    FINISHED = "finished"
    ERROR = "error"
    INTERRUPTED = "interrupted"

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: str | None = None
    error: str | None = None
    duration_ms: float | None = None
```

**状态流转**：
```
PENDING → ASKING（需要审批）
PENDING → ALLOWED（直接允许）
ALLOWED → EXECUTING → FINISHED
ALLOWED → EXECUTING → ERROR
EXECUTING → INTERRUPTED（用户中断）
```

### 6.2 增量文件修改

**参考来源**：Cline `apply_patch` + Continue `streamDiff`

**Patch Grammar**：
```
*** Begin Patch
*** Update File: path/to/file.py
@@ -1,5 +1,5 @@
 old_line
-new_line
+updated_line
@@
*** End Patch
```

**关键规则**：
- `old_text` 必须在文件中恰好出现一次（`countOccurrences` 校验）
- 支持 `Add File`、`Update File`、`Delete File`、`Move to` 操作
- 分块应用，只生成最终内容再写入

### 6.3 代码执行沙箱

**参考来源**：TaskWeaver `code_verification.py` + Open Interpreter `sandboxing/`

**AST 级别静态检查**：
```python
class CodeSandbox:
    FORBIDDEN_MODULES = {"os", "sys", "subprocess", "socket", ...}
    FORBIDDEN_FUNCTIONS = {"eval", "exec", "open", "getattr", "setattr", ...}
    FORBIDDEN_DUNDER = {"__dict__", "__class__", "__bases__", "__subclasses__", ...}
    
    def verify(self, code: str) -> VerificationResult:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.FORBIDDEN_MODULES:
                        return VerificationResult(allowed=False, reason=f"Forbidden module: {alias.name}")
            # ... 其他检查
```

**双模式执行**：
- `local`：直接在本机执行（受沙箱限制）
- `container`：Docker 容器隔离执行

---

## 七、上下文管理（参考：Continue + AutoGPT）

### 7.1 增量文件索引

**参考来源**：Continue `refreshIndex.ts`

**两级筛选策略**：
1. **时间戳预筛选**：对比文件 `lastModified` 与 SQLite `lastUpdated`，仅处理变更文件
2. **内容哈希去重**：SHA256 哈希对比，相同内容仅添加标签引用

**批量处理**：
- 并发限制：10（`plimit(10)`）
- 每批处理：200 文件
- 支持暂停/恢复（`PauseToken`）

### 7.2 上下文压缩

**参考来源**：AgentScope `Compressor` + MonkeyCode `trimmer`

三种策略：
- `TRUNCATE`：保留 system prompt + 最近 N 条，中间截断
- `SLIDING`：只保留最近 N 条
- `SUMMARIZE`：LLM 将中间消息压缩为摘要，追加为 system message

**触发条件**：`estimate_tokens(messages) > max_tokens * 0.8`

---

## 八、实现优先级路线图

### Phase 1：底层调度（LangGraph + MonkeyCode）
- [ ] 重构 `AgentEngine` 为状态图执行引擎
- [ ] 实现检查点快照保存/恢复
- [ ] 完善任务状态机（PENDING → PROCESSING → PAUSED → COMPLETED/FAILED）
- [ ] 接入 Hook 链机制

### Phase 2：记忆系统（Letta + Hermes-Agent）
- [ ] 重构三层记忆架构（Core / Session / Archival）
- [ ] LLM 自主记忆工具（`core_memory_append` / `archival_memory_search`）
- [ ] 自动反思机制（后台 fork 代理评估）
- [ ] 向量记忆集成 ChromaDB

### Phase 3：安全机制（OpenCode + Cline）
- [ ] 双模式权限系统（PLAN / ACT）
- [ ] 三层权限叠加合并策略
- [ ] 工具级权限开关 + 资源路径检查
- [ ] 审计日志系统

### Phase 4：插件系统（MonkeyCode + Sidekick-AI）
- [ ] Skill 三级 Scope 体系（global / team / user）
- [ ] MCP 服务器生命周期管理
- [ ] 统一工具网关（权限 / 超时 / 重试 / 日志）
- [ ] 插件热加载机制

### Phase 5：多智能体协作（CrewAI + AutoGen + AgentScope）
- [ ] 三种执行模式（Sequential / Hierarchical / Group Chat）
- [ ] Agent 角色分工模型
- [ ] 任务依赖管理（context 声明）
- [ ] 交接机制（Handoff）

### Phase 6：工具执行增强（Cline + Open Interpreter + TaskWeaver）
- [ ] JSON Schema 严格校验（Zod 驱动）
- [ ] 增量文件修改（patch grammar + 唯一性校验）
- [ ] 代码执行沙箱（AST 检查 + 容器隔离）
- [ ] 流式终端输出（JSON-RPC 协议）

### Phase 7：上下文管理（Continue + AutoGPT）
- [ ] 增量文件索引（时间戳 + 哈希双级筛选）
- [ ] 上下文压缩（TRUNCATE / SLIDING / SUMMARIZE）
- [ ] 任务自动分解（Planner → Executor → Reviewer）

---

## 九、参考来源汇总

| 开源项目 | 参考目录 | 吸收要点 | 参考来源标注 |
|---------|---------|---------|------------|
| MonkeyCode | backend/biz/task/ | 任务状态机、Hook 链 | `TaskState` + `TRANSITIONS` |
| MonkeyCode | backend/biz/skill/ | Skill 三级 Scope、数据结构 | `SkillRecord` + `SkillVersion` |
| MonkeyCode | backend/core/model/router.go | 模型网关、Token 统计 | `ModelContext` + `UsageCapture` |
| MonkeyCode | backend/pkg/trimmer | 超长文本摘要 | `TaskSummaryService` |
| LangGraph | graph/state.py | 有向状态图、Channel 抽象 | `StateGraph` + `Channel` |
| LangGraph | pregel/loop.py | 超级步执行、检查点 | `PregelLoop` + `_put_checkpoint` |
| LangGraph | checkpoint/ | 快照恢复、祖先遍历 | `Checkpoint` + `pending_writes` |
| Letta | memory/ | 三层记忆架构 | `CoreMemoryBlock` + `SessionMessage` + `ArchivalPassage` |
| Letta | schemas/passage.py | 档案记忆数据结构 | `ArchivalPassage` |
| Hermes-Agent | reflection/ | 自动反思流程 | `ReflectionResult` |
| Hermes-Agent | memory/ | Memory Provider 抽象 | `MemoryProvider` ABC |
| OpenCode | agent/agent.ts | 双模式权限 | `AgentMode` + `PermissionLevel` |
| OpenCode | bus/ | 全局事件总线 | `EventV2` + `GlobalBus` |
| OpenCode | session/ | Session 快照 | `Snapshot` + Git 隔离 |
| Cline | src/core/tools/ | JSON Schema 校验、增量修改 | `ToolInputSchema` + `apply_patch` |
| Devika | agent/ + planner/ | 分层规划器、失败调试闭环 | `Planner` + `Patcher` |
| AgentScope | agent/ + memory/ | 多智能体通信、Memory 多模式 | `AgentMessage` + `MemoryTier` |
| TaskWeaver | agent/ + planner/ | 动态代码执行、AST 沙箱 | `CodeSandbox` + `Environment` |
| Continue | core/diff/ + context/ | 增量索引、Diff 预览 | `refreshIndex` + `streamDiff` |
| Open Interpreter | exec-server/ + sandboxing/ | 双环境策略、流式输出 | `SandboxMode` + `exec-server` |
| AutoGPT | agent/ + planner/ | ReAct 循环、任务分解 | `AgentEngine.run()` |
| CrewAI | crew/ | 多智能体角色分工 | `Crew` + `Process` |
| AutoGen | agentchat/ | 交接机制、人工干预 | `HandoffMessage` + `UserProxyAgent` |
| BabyAGI | babyagi.py | 轻量级任务队列、动态优先级 | `TaskQueue` + `prioritization_agent` |

---

## 十、关键设计决策

1. **不引入 LangGraph 作为依赖**：吸收其状态图 + 检查点设计，使用自研轻量实现
2. **不替换现有 Adapter 层**：保留 OpenAI/Anthropic/Google/Ollama/StepFun 适配器，吸收 LiteLLM 的 retry/fallback 逻辑
3. **SQLite 优先**：所有持久化默认使用 SQLite，通过 `async_sessionmaker` 管理连接
4. **事件驱动架构**：新增 `EventBus` 模块解耦各子系统
5. **渐进式重构**：Phase 1-7 逐步实施，每个 Phase 完成后回归测试
