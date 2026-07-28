# Climber 前后端集成架构设计

> 基于 30 个开源项目参考，结合当前后端能力，设计可落地的前后端打通方案。

## 1. 后端能力盘点

### 已有核心接口

| 模块 | 端点 | 协议 | 状态 |
|------|------|------|------|
| 健康检查 | `/health` | REST | 就绪 |
| 会话管理 | `/api/v1/sessions` | REST | 就绪 |
| 聊天流式 | `/api/v1/sessions/{id}/chat` | SSE | 就绪 |
| 消息历史 | `/api/v1/sessions/{id}/messages` | REST | 就绪 |
| 工作流 | `/api/v1/workflows` | REST | 就绪 |
| Crew | `/api/v1/crews` | REST | 就绪 |
| Skills | `/api/v1/skills` | REST | 就绪 |
| 插件 | `/api/v1/plugins` | REST | 就绪 |
| MCP | `/api/v1/mcp` | REST | 就绪 |
| 工具 | `/api/v1/tools` | REST | 就绪 |
| 追踪 | `/api/v1/traces` | REST | 就绪 |
| 认证 | `/api/v1/auth/login` | REST | 就绪 |

### 核心事件类型（SSE）

后端 `AgentEvent` 已支持：
- `message` - 文本增量
- `tool_call` - 工具调用开始
- `tool_result` - 工具结果返回
- `error` - 错误
- `done` - 结束

## 2. 前端架构设计

### 2.1 分层结构

```
frontend-react/src/
├── api/                  # API 层（对应后端 REST + SSE）
│   ├── client.ts         # 统一 fetch 客户端
│   ├── sessions.ts       # 会话 API
│   ├── chat.ts           # 聊天 SSE
│   ├── workflows.ts      # 工作流 API
│   ├── agents.ts         # Agent API
│   └── tools.ts          # 工具 API
├── stores/               # 状态管理
│   ├── useSessions.ts    # 会话列表
│   ├── useChat.ts        # 当前会话消息
│   └── useAgent.ts       # Agent 状态
├── components/
│   ├── chat/             # Lobe UI 风格聊天
│   │   ├── MessageContent.tsx
│   │   ├── ToolCallCard.tsx
│   │   └── ChatInput.tsx
│   ├── workflow/         # Flowise 风格工作流
│   │   ├── WorkflowCanvas.tsx
│   │   └── WorkflowNode.tsx
│   └── layout/           # 布局组件
│       ├── Sidebar.tsx
│       └── ControlBar.tsx
└── pages/
    ├── ChatPage.tsx
    ├── WorkflowPage.tsx
    └── DashboardPage.tsx
```

### 2.2 数据流

```
用户输入 → ChatInput → onSend
    ↓
useChat.sendMessage()
    ↓
api.chat.send(sessionId, message)  → SSE 流
    ↓
EventSource / ReadableStream 解析
    ↓
onMessage / onToolCall / onDone
    ↓
store.appendMessage / store.updateTool
    ↓
ChatInterface 重新渲染
```

## 3. 参考开源的功能映射

### Lobe UI → 本系统

| Lobe UI 组件 | 本系统实现 | 对接后端 |
|-------------|-----------|---------|
| `ChatItem` | `MessageContent` | SSE `message` 事件 |
| `Bubble` | 内嵌在 MessageContent | 直接渲染 |
| `ChatInputArea` | `ChatInput` | 调用 `/sessions/{id}/chat` |
| `LoadingDots` | `LoadingDots` | `isStreaming` 状态 |
| `Actions` | `MessageActions` | 复制/反馈 → `/feedback` |

### Dify → 本系统

| Dify 功能 | 本系统实现 | 对接后端 |
|-----------|-----------|---------|
| Chat 布局 | `ChatPage` + `Sidebar` | `/sessions` + `/sessions/{id}/chat` |
| Tool 详情面板 | `ToolCallCard` | SSE `tool_call` / `tool_result` |
| Answer 组件 | `MessageContent` | SSE `message` |
| 会话列表 | `SessionList` | `/sessions` |

### Flowise → 本系统

| Flowise 功能 | 本系统实现 | 对接后端 |
|-------------|-----------|---------|
| 工作流画布 | `WorkflowCanvas` | `/workflows/{id}` |
| 节点系统 | `WorkflowNode` | `/workflows/{id}/run` |
| 模板库 | `TemplateList` | `/workflows/templates` |

## 4. 实现步骤

### Phase 1：API 层打通
1. 创建 `src/api/client.ts` - 统一 fetch + SSE 解析
2. 创建 `src/api/sessions.ts` - 会话 CRUD
3. 创建 `src/api/chat.ts` - SSE 聊天

### Phase 2：状态管理
1. 创建 `src/stores/useSessions.ts` - 会话列表状态
2. 创建 `src/stores/useChat.ts` - 当前会话消息状态

### Phase 3：组件对接
1. `ChatPage` 对接真实 API
2. `ChatInterface` 接入 SSE 流
3. `ToolCallCard` 对接 tool_call/tool_result 事件
4. `SessionList` 对接 /sessions 端点

### Phase 4：工作流页面
1. 创建 `WorkflowPage`
2. 对接 `/workflows` API
3. 实现 Flowise 风格节点画布

## 5. 关键技术决策

### SSE 流式解析

```typescript
// api/chat.ts
export async function* streamChat(sessionId: string, message: string) {
  const response = await fetch(`/api/v1/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop()!;

    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = JSON.parse(line.slice(5));
        yield data;
      }
    }
  }
}
```

### 状态管理（Zustand）

```typescript
// stores/useChat.ts
interface ChatState {
  messages: Message[];
  isLoading: boolean;
  sendMessage: (content: string) => void;
  appendMessage: (msg: Message) => void;
  updateToolCall: (id: string, result: ToolCallResult) => void;
}
```

## 6. 风险评估

| 风险 | 缓解措施 |
|------|---------|
| SSE 解析复杂 | 先实现基础解析，逐步增加错误处理 |
| 后端事件格式不匹配 | 先查看后端 `AgentEvent.to_sse()` 实现，对齐格式 |
| 前端状态同步 | 使用单一数据源，所有更新通过 store |
| 工作流复杂度高 | Phase 4 独立实现，不影响聊天功能 |

## 7. 下一步行动

1. 查看后端 `AgentEvent.to_sse()` 实现
2. 实现 `api/client.ts` + `api/chat.ts`
3. 实现 `stores/useChat.ts`
4. 修改 `ChatPage.tsx` 对接真实 API
5. 运行前端测试验证
