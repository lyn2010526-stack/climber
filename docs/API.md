# Climber API 文档

> Base URL: `/api/v1`  
> OpenAPI Schema: `/docs` (Swagger UI)  
> OpenAPI JSON: `/openapi.json`

## 认证

所有需要认证的端点使用 Bearer Token（JWT）。

```
Authorization: Bearer <token>
```

未认证请求在部分端点会降级为 `default-user` 访客模式。

## 通用响应格式

成功响应通常返回 JSON 对象。失败时返回标准错误格式：

```json
{
  "detail": "错误描述",
  "type": "http_error"
}
```

## SSE 流式响应

聊天端点使用 Server-Sent Events 返回实时流：

```
Content-Type: text/event-stream

data: {"type": "text", "data": {"content": "..."}}
data: {"type": "tool_call", "data": {"name": "...", "arguments": {...}}}
data: {"type": "error", "data": {"error": "..."}}
```

---

## 聊天 (Chat)

### 发送聊天消息

```
POST /api/v1/sessions/{session_id}/chat
```

**请求体**:
```json
{
  "message": "你好，请帮我分析这段代码"
}
```

**响应**: SSE 流式事件流

**事件类型**:
| 类型 | 说明 |
|------|------|
| `text` | 文本输出片段 |
| `tool_call` | 工具调用开始 |
| `tool_result` | 工具调用结果 |
| `thinking` | 推理过程 |
| `error` | 错误信息 |
| `done` | 流结束 |

---

## 会话 (Sessions)

### 列出会话

```
GET /api/v1/sessions/
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 返回数量限制（默认 50） |
| `offset` | int | 分页偏移 |

**响应**:
```json
[
  {
    "id": "uuid",
    "title": "会话标题",
    "status": "idle|running|completed|failed",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

### 创建会话

```
POST /api/v1/sessions/
```

**请求体**:
```json
{
  "title": "新会话",
  "agent_id": "agent-uuid",
  "model_settings": {}
}
```

### 获取会话详情

```
GET /api/v1/sessions/{session_id}
```

### 删除会话

```
DELETE /api/v1/sessions/{session_id}
```

### 获取会话消息

```
GET /api/v1/sessions/{session_id}/messages
```

### 清空会话消息

```
POST /api/v1/sessions/{session_id}/clear
```

### 保存检查点

```
POST /api/v1/sessions/{session_id}/checkpoint
```

**请求体**:
```json
{
  "messages": [...],
  "iteration": 5,
  "status": "active",
  "metadata": {}
}
```

### 获取最新检查点

```
GET /api/v1/sessions/{session_id}/checkpoint
```

### 获取检查点历史

```
GET /api/v1/sessions/{session_id}/history
```

### 分叉会话

```
POST /api/v1/sessions/{session_id}/fork
```

**请求体**:
```json
{
  "new_session_id": "optional-uuid"
}
```

### 恢复会话

```
POST /api/v1/sessions/{session_id}/resume
```

---

## 代理 (Agents)

### 列出代理

```
GET /api/v1/agents/
```

**查询参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `limit` | int | 返回数量（默认 50） |
| `offset` | int | 分页偏移 |

### 创建代理

```
POST /api/v1/agents/
```

**请求体**:
```json
{
  "name": "代码助手",
  "provider": "anthropic",
  "model_id": "claude-3-5-sonnet-20241022",
  "api_key": "sk-ant-...",
  "base_url": null,
  "system_prompt": "你是一个专业的编程助手...",
  "description": "擅长代码分析和生成",
  "tool_ids": ["read_file", "write_file"],
  "skill_ids": []
}
```

### 删除代理

```
DELETE /api/v1/agents/{agent_id}
```

---

## 模型 (Models)

### 列出可用模型

```
GET /api/v1/models/
```

**响应**:
```json
[
  {"provider": "openai", "model_id": "gpt-4o", "label": "GPT-4o"},
  {"provider": "anthropic", "model_id": "claude-3-5-sonnet-20241022", "label": "Claude 3.5 Sonnet"},
  {"provider": "ollama", "model_id": "llama3.3", "label": "llama3.3 (local)"}
]
```

---

## 工具 (Tools)

### 列出所有工具

```
GET /api/v1/tools/
```

**响应**:
```json
[
  {
    "name": "read_file",
    "description": "读取文件内容",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string"}
      }
    }
  }
]
```

---

## 工作流 (Workflows)

### 列出工作流

```
GET /api/v1/workflows/
```

### 创建工作流

```
POST /api/v1/workflows/
```

**请求体**:
```json
{
  "name": "代码审查流程",
  "description": "自动化代码审查",
  "nodes": [...],
  "edges": [...]
}
```

### 获取工作流详情

```
GET /api/v1/workflows/{workflow_id}
```

### 更新工作流

```
PUT /api/v1/workflows/{workflow_id}
```

### 删除工作流

```
DELETE /api/v1/workflows/{workflow_id}
```

### 列出工作流模板

```
GET /api/v1/workflows/templates
```

### 从模板创建工作流

```
POST /api/v1/workflows/templates/{template_id}
```

### 导入工作流

```
POST /api/v1/workflows/import
```

### 导出工作流

```
GET /api/v1/workflows/{workflow_id}/export?format=json
POST /api/v1/workflows/{workflow_id}/export
```

---

## 技能 (Skills)

### 列出技能

```
GET /api/v1/skills/
```

### 创建技能

```
POST /api/v1/skills/
```

**请求体**:
```json
{
  "name": "代码重构",
  "description": "自动重构代码",
  "category": "development",
  "prompt_template": "请重构以下代码...",
  "tools": ["read_file", "write_file"]
}
```

### 更新技能

```
PATCH /api/v1/skills/{skill_id}
```

### 启用技能

```
POST /api/v1/skills/{skill_id}/enable
```

### 禁用技能

```
POST /api/v1/skills/{skill_id}/disable
```

### 删除技能

```
DELETE /api/v1/skills/{skill_id}
```

---

## 权限 (Permissions)

### 获取权限配置

```
GET /api/v1/permissions/config
```

**响应**:
```json
{
  "mode": "standard",
  "rules": [
    {"decision": "allow", "tool": "read_file", "pattern": null},
    {"decision": "deny", "tool": "shell_exec", "pattern": "rm -rf"}
  ],
  "allowed_tools": ["read_file", "list_files"],
  "denied_tools": ["shell_exec"]
}
```

### 更新权限配置

```
PUT /api/v1/permissions/config
```

**请求体**:
```json
{
  "mode": "standard",
  "rules": [...],
  "allowed_tools": [...],
  "denied_tools": [...]
}
```

### 解析权限请求

```
POST /api/v1/permissions/resolve
```

**请求体**:
```json
{
  "tool_call_id": "uuid",
  "decision": "allow"
}
```

**决策选项**: `allow`, `allow_session`, `allow_always`, `deny`

---

## MCP 服务器

### 列出 MCP 服务器

```
GET /api/v1/mcp/
```

### 创建 MCP 服务器

```
POST /api/v1/mcp/
```

**请求体**:
```json
{
  "name": "Filesystem MCP",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem"],
  "env": {}
}
```

### 启动 MCP 服务器

```
POST /api/v1/mcp/{server_id}/start
```

### 停止 MCP 服务器

```
POST /api/v1/mcp/{server_id}/stop
```

### 删除 MCP 服务器

```
DELETE /api/v1/mcp/{server_id}
```

### 列出市场服务器

```
GET /api/v1/mcp/servers
```

### 安装市场服务器

```
POST /api/v1/mcp/servers/{server_id}/install
```

### 列出 MCP 分类

```
GET /api/v1/mcp/categories
```

---

## 多 Agent 协作 (Groups)

### 列出协作组

```
GET /api/v1/groups/
```

### 创建协作组

```
POST /api/v1/groups/
```

**请求体**:
```json
{
  "name": "开发团队",
  "description": "协作开发小组",
  "topic": "实现用户认证模块",
  "max_rounds": 10,
  "process_type": "sequential"
}
```

### 获取协作组详情

```
GET /api/v1/groups/{group_id}
```

### 删除协作组

```
DELETE /api/v1/groups/{group_id}
```

### 添加成员

```
POST /api/v1/groups/{group_id}/members
```

**请求体**:
```json
{
  "agent_id": "agent-uuid",
  "role": "developer",
  "model_provider": "openai",
  "model_id": "gpt-4o",
  "is_worker": true
}
```

### 获取成员列表

```
GET /api/v1/groups/{group_id}/members
```

### 更新成员

```
PATCH /api/v1/groups/{group_id}/members/{member_id}
```

### 移除成员

```
DELETE /api/v1/groups/{group_id}/members/{member_id}
```

### 获取消息历史

```
GET /api/v1/groups/{group_id}/messages?limit=50
```

---

## Crew (层级协作)

### 列出 Crew

```
GET /api/v1/crews/
```

### 创建 Crew

```
POST /api/v1/crews/
```

**请求体**:
```json
{
  "name": "代码审查 Crew",
  "description": "自动化代码审查流程",
  "process": "sequential",
  "agents": ["agent-uuid-1", "agent-uuid-2"],
  "tasks": [
    {"description": "审查代码质量", "system_prompt": "你是代码审查专家"},
    {"description": "生成报告", "system_prompt": "你是报告生成专家"}
  ]
}
```

### 运行 Crew

```
POST /api/v1/crews/{crew_id}/run
```

### 删除 Crew

```
DELETE /api/v1/crews/{crew_id}
```

---

## 任务 (Tasks)

### 列出任务

```
GET /api/v1/tasks/?group_id=optional
```

### 创建任务

```
POST /api/v1/tasks/
```

**请求体**:
```json
{
  "group_id": "group-uuid",
  "description": "实现登录功能",
  "worker_id": "agent-uuid",
  "reviewer_ids": ["reviewer-uuid"],
  "max_rounds": 5,
  "context": [],
  "guardrails": [],
  "human_review_required": false,
  "output_schema": {}
}
```

### 运行任务

```
POST /api/v1/tasks/{task_id}/run
```

### 获取任务详情

```
GET /api/v1/tasks/{task_id}
```

### 暂停任务

```
POST /api/v1/tasks/{task_id}/pause
```

### 恢复任务

```
POST /api/v1/tasks/{task_id}/resume
```

### 停止任务

```
POST /api/v1/tasks/{task_id}/stop
```

---

## 文档 (Documents)

### 列出文档

```
GET /api/v1/documents/
```

### 创建文档

```
POST /api/v1/documents/
```

### 索引文本

```
POST /api/v1/documents/index-text
```

**请求体** (multipart/form-data):
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 要索引的文本内容 |
| `name` | string | 文档名称 |

### 搜索文档

```
POST /api/v1/documents/search?query=关键词&n_results=5
```

### 删除文档

```
DELETE /api/v1/documents/{doc_id}
```

---

## API Keys

### 列出 API Keys

```
GET /api/v1/api-keys/
```

### 添加 API Key

```
POST /api/v1/api-keys/
```

**请求体**:
```json
{
  "provider": "anthropic",
  "name": "我的 Claude Key",
  "api_key": "sk-ant-...",
  "base_url": null
}
```

### 删除 API Key

```
DELETE /api/v1/api-keys/{key_id}
```

---

## 调度器 (Scheduler)

### 列出定时任务

```
GET /api/v1/scheduler/
```

### 创建定时任务

```
POST /api/v1/scheduler/
```

**请求体**:
```json
{
  "name": "每日报告",
  "nodes": [...],
  "edges": [...],
  "schedule": "0 9 * * *"
}
```

### 更新定时任务

```
PATCH /api/v1/scheduler/tasks/{task_id}
```

### 删除定时任务

```
DELETE /api/v1/scheduler/tasks/{task_id}
```

---

## 设置 (Settings)

### 获取设置

```
GET /api/v1/settings/
```

### 更新设置

```
PATCH /api/v1/settings/
```

**请求体**:
```json
{
  "autonomous_agent_mode": true,
  "token_throttle_mcp_enabled": false
}
```

---

## WebSocket

### 会话 WebSocket

```
WS /api/v1/ws/{session_id}
```

**消息协议**:
```json
// 客户端发送
{"type": "message", "content": "你好"}

// 服务端响应
{"type": "echo", "data": "你好"}
```

### 协作组 WebSocket

```
WS /api/v1/ws/groups/{group_id}
```

**消息协议**:
```json
// 客户端发送
{"type": "message", "content": "开始讨论"}

// 服务端响应
{"type": "ack", "data": {...}}
```

---

## 健康检查与监控

### 健康检查

```
GET /health
```

**响应**:
```json
{
  "status": "ok",
  "version": "0.2.0",
  "database": {"connected": true, "backend": "sqlite"},
  "redis": "ok",
  "chroma": "ok",
  "watchdog": {"healthy": true},
  "memory": {...},
  "browser_pool": {...}
}
```

### 日志查看

```
GET /health/logs?lines=200&errors_only=false
```

### 指标

```
GET /metrics
```

---

## 其他端点

### 提示词模板

```
GET  /api/v1/prompt-templates/
POST /api/v1/prompt-templates/
```

### 费用追踪

```
GET /api/v1/cost/
```

### 统计

```
GET /api/v1/stats/
```

### 搜索

```
GET /api/v1/search/?query=关键词
```

### 反馈

```
POST /api/v1/feedback/
```

### 通知

```
GET    /api/v1/notifications/
POST   /api/v1/notifications/read
```

### 诊断

```
GET /api/v1/doctor/
```

### 插件

```
GET    /api/v1/plugins/
POST   /api/v1/plugins/{plugin_id}/install
DELETE /api/v1/plugins/{plugin_id}
```

### 推理

```
POST /api/v1/reason/
```

### 追踪

```
GET /api/v1/traces/
```

### 评估

```
POST /api/v1/eval/
GET  /api/v1/eval/results
```

### 用户

```
GET /api/v1/users/
```

### 集群

```
GET /api/v1/cluster/status
```
