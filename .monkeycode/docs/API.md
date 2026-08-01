# Climber API 文档

> Base URL: `/api/v1`

## 认证

所有需要认证的端点使用 Bearer Token。

```
Authorization: Bearer <token>
```

未认证请求在部分端点会降级为 `default-user` 访客模式。

## 通用响应格式

成功响应通常返回 JSON 对象。失败时返回：

```json
{
  "detail": "错误描述"
}
```

## 端点列表

### Agents

| Method | Path | 描述 |
|--------|------|------|
| GET | `/agents` | 列出所有 Agent |
| GET | `/agents/` | 列出所有 Agent（尾部斜杠） |
| POST | `/agents` | 创建 Agent |
| POST | `/agents/` | 创建 Agent（尾部斜杠） |
| DELETE | `/agents/{agent_id}` | 删除 Agent |

### Workflows

| Method | Path | 描述 |
|--------|------|------|
| GET | `/workflows` | 列出所有工作流（非模板） |
| GET | `/workflows/` | 列出所有工作流（尾部斜杠） |
| POST | `/workflows` | 创建工作流 |
| POST | `/workflows/` | 创建工作流（尾部斜杠） |
| GET | `/workflows/{workflow_id}` | 获取工作流详情 |
| PUT | `/workflows/{workflow_id}` | 更新工作流 |
| DELETE | `/workflows/{workflow_id}` | 删除工作流 |
| POST | `/workflows/{workflow_id}/run` | 运行工作流 |
| GET | `/workflows/{workflow_id}/runs` | 获取工作流运行历史 |
| GET | `/workflows/templates` | 列出可用模板 |
| GET | `/workflows/templates/` | 列出可用模板（尾部斜杠） |
| POST | `/workflows/templates/{template_id}` | 从模板创建工作流 |
| POST | `/workflows/templates/{template_id}/create` | 从模板创建工作流（别名） |
| POST | `/workflows/import` | 导入工作流（JSON/YAML） |
| POST | `/workflows/{workflow_id}/export` | 导出工作流（POST） |
| GET | `/workflows/{workflow_id}/export` | 导出工作流（GET） |

### Crews

| Method | Path | 描述 |
|--------|------|------|
| GET | `/crews` | 列出所有 Crew |
| GET | `/crews/` | 列出所有 Crew（尾部斜杠） |
| POST | `/crews` | 创建 Crew |
| POST | `/crews/` | 创建 Crew（尾部斜杠） |
| DELETE | `/crews/{crew_id}` | 删除 Crew |
| POST | `/crews/{crew_id}/run` | 运行 Crew |

### Skills

| Method | Path | 描述 |
|--------|------|------|
| GET | `/skills` | 列出所有 Skills |
| GET | `/skills/` | 列出所有 Skills（尾部斜杠） |
| POST | `/skills` | 创建 Skill |
| POST | `/skills/` | 创建 Skill（尾部斜杠） |
| DELETE | `/skills/{skill_id}` | 删除 Skill |
| POST | `/skills/{skill_id}/enable` | 启用 Skill |
| POST | `/skills/{skill_id}/disable` | 禁用 Skill |

### Plugins

| Method | Path | 描述 |
|--------|------|------|
| GET | `/plugins` | 列出已安装插件 |
| GET | `/plugins/` | 列出已安装插件（尾部斜杠） |
| GET | `/plugins/marketplace` | 列出插件市场 |
| GET | `/plugins/marketplace/` | 列出插件市场（尾部斜杠） |
| GET | `/plugins/categories` | 列出插件分类 |
| GET | `/plugins/categories/` | 列出插件分类（尾部斜杠） |
| POST | `/plugins/import` | 导入插件 |
| POST | `/plugins/{plugin_key}/install` | 安装插件 |
| POST | `/plugins/{plugin_id}/enable` | 启用插件 |
| POST | `/plugins/{plugin_id}/disable` | 禁用插件 |
| GET | `/plugins/{plugin_id}/status` | 获取插件状态 |
| POST | `/plugins/{plugin_id}/uninstall` | 卸载插件 |
| DELETE | `/plugins/{plugin_id}` | 删除插件 |

### MCP Servers

| Method | Path | 描述 |
|--------|------|------|
| GET | `/mcp` | 列出 MCP 服务器 |
| GET | `/mcp/` | 列出 MCP 服务器（尾部斜杠） |
| POST | `/mcp` | 创建 MCP 服务器配置 |
| POST | `/mcp/` | 创建 MCP 服务器配置（尾部斜杠） |
| DELETE | `/mcp/{server_id}` | 删除 MCP 服务器 |
| POST | `/mcp/{server_id}/start` | 启动 MCP 服务器 |
| POST | `/mcp/{server_id}/stop` | 停止 MCP 服务器 |

### Cluster

| Method | Path | 描述 |
|--------|------|------|
| GET | `/cluster` | 列出集群节点 |
| GET | `/cluster/` | 列出集群节点（尾部斜杠） |
| POST | `/cluster` | 创建集群节点 |
| POST | `/cluster/` | 创建集群节点（尾部斜杠） |
| POST | `/cluster/create` | 创建集群节点（别名） |
| GET | `/cluster/status` | 获取集群状态 |
| GET | `/cluster/stats` | 获取集群统计 |
| GET | `/cluster/stats/` | 获取集群统计（尾部斜杠） |
| DELETE | `/cluster/{node_id}` | 删除集群节点 |

### Tools

| Method | Path | 描述 |
|--------|------|------|
| GET | `/tools` | 列出所有可用工具 |
| GET | `/tools/` | 列出所有可用工具（尾部斜杠） |

### Traces

| Method | Path | 描述 |
|--------|------|------|
| GET | `/traces` | 列出所有追踪 |
| GET | `/traces/` | 列出所有追踪（尾部斜杠） |
| GET | `/traces/{trace_id}` | 获取追踪详情 |
| POST | `/reason/{trace_id}/feedback` | 提交推理反馈 |
| GET | `/reason/{trace_id}/feedback` | 获取推理反馈 |

### Sessions / Chat

| Method | Path | 描述 |
|--------|------|------|
| GET | `/sessions/{session_id}` | 获取会话详情 |
| DELETE | `/sessions/{session_id}` | 删除会话 |
| POST | `/sessions/{session_id}/chat` | 发送聊天消息 |
| POST | `/sessions/{session_id}/clear` | 清除会话历史 |
| GET | `/sessions/{session_id}/messages` | 获取会话消息 |

### Tasks

| Method | Path | 描述 |
|--------|------|------|
| GET | `/tasks` | 列出所有任务 |
| GET | `/tasks/` | 列出所有任务（尾部斜杠） |
| POST | `/tasks` | 创建任务 |
| POST | `/tasks/` | 创建任务（尾部斜杠） |
| GET | `/tasks/{task_id}` | 获取任务详情 |
| POST | `/tasks/{task_id}/run` | 运行任务 |
| POST | `/tasks/{task_id}/pause` | 暂停任务 |
| POST | `/tasks/{task_id}/resume` | 恢复任务 |
| POST | `/tasks/{task_id}/stop` | 停止任务 |

### Eval

| Method | Path | 描述 |
|--------|------|------|
| GET | `/eval/datasets` | 列出评估数据集 |
| GET | `/eval/datasets/` | 列出评估数据集（尾部斜杠） |
| POST | `/eval/datasets` | 创建评估数据集 |
| POST | `/eval/datasets/` | 创建评估数据集（尾部斜杠） |
| POST | `/eval/run` | 运行评估 |
| POST | `/eval/run/` | 运行评估（尾部斜杠） |

### Groups

| Method | Path | 描述 |
|--------|------|------|
| GET | `/groups` | 列出所有群组 |
| GET | `/groups/` | 列出所有群组（尾部斜杠） |
| POST | `/groups` | 创建群组 |
| POST | `/groups/` | 创建群组（尾部斜杠） |
| GET | `/groups/{group_id}` | 获取群组详情 |
| DELETE | `/groups/{group_id}` | 删除群组 |
| POST | `/groups/{group_id}/members` | 添加群组成员 |
| DELETE | `/groups/{group_id}/members/{member_id}` | 移除群组成员 |
| PATCH | `/groups/{group_id}/members/{member_id}` | 更新群组成员 |
| GET | `/groups/{group_id}/messages` | 获取群组消息 |

### Documents

| Method | Path | 描述 |
|--------|------|------|
| POST | `/documents/upload` | 上传文档 |
| DELETE | `/documents/{doc_id}` | 删除文档 |

### Feedback

| Method | Path | 描述 |
|--------|------|------|
| POST | `/feedback` | 提交反馈 |
| POST | `/feedback/` | 提交反馈（尾部斜杠） |
| GET | `/traces/{trace_id}/feedback` | 获取追踪反馈 |
| POST | `/traces/{trace_id}/feedback` | 提交追踪反馈 |

### Users

| Method | Path | 描述 |
|--------|------|------|
| POST | `/users/register` | 注册用户 |
| POST | `/login` | 用户登录 |
| GET | `/profile` | 获取当前用户资料 |
| GET | `/profile/` | 获取当前用户资料（尾部斜杠） |

### API Keys

| Method | Path | 描述 |
|--------|------|------|
| GET | `/api-keys` | 列出 API Keys |
| POST | `/api-keys` | 创建 API Key |
| DELETE | `/api-keys/{key_id}` | 删除 API Key |

### Notifications

| Method | Path | 描述 |
|--------|------|------|
| GET | `/notifications` | 列出通知 |
| GET | `/notifications/` | 列出通知（尾部斜杠） |

### Stats & Cost

| Method | Path | 描述 |
|--------|------|------|
| GET | `/stats` | 获取统计信息 |
| GET | `/stats/` | 获取统计信息（尾部斜杠） |
| GET | `/cost/budget` | 获取预算配置 |
| GET | `/cost/budget/` | 获取预算配置（尾部斜杠） |
| GET | `/cost/quota` | 获取配额信息 |
| GET | `/cost/quota/` | 获取配额信息（尾部斜杠） |
| GET | `/cost/records` | 获取成本记录 |
| GET | `/cost/records/` | 获取成本记录（尾部斜杠） |

### 系统

| Method | Path | 描述 |
|--------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/health/logs` | 健康检查日志 |
| GET | `/metrics` | Prometheus 指标 |
| GET | `/` | 根路径 |
| POST | `/stream` | 流式响应 |
| POST | `/send` | 发送消息 |
| POST | `/switch` | 切换模式 |
| GET | `/history` | 获取历史 |
| POST | `/create` | 创建资源 |
| POST | `/search` | 搜索 |
| POST | `/index-text` | 索引文本 |
| GET | `/scheduler` | 获取调度器状态 |
| POST | `/scheduler` | 创建调度任务 |
| GET | `/models` | 列出可用模型 |
| GET | `/modes` | 列出可用模式 |
| GET | `/test` | 测试端点 |

## 前端路由

| Method | Path | 描述 |
|--------|------|------|
| GET | `/` | 前端根路径 |

## 认证相关路由

| Method | Path | 描述 |
|--------|------|------|
| POST | `/auth/login` | 登录 |
| POST | `/auth/register` | 注册 |
