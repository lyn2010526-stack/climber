# Climber 系统架构

> 本文档描述 Climber Agent Engine 的系统架构、模块关系和数据流。

## 概述

Climber 是一个本地优先的 AI Agent 平台，采用分层架构设计。系统通过 FastAPI 提供 REST API 和 SSE 流式响应，支持多模型调度、工具扩展和多 Agent 协作。所有数据默认存储在本地 SQLite 数据库，可选 PostgreSQL 用于生产环境。

## 设计原则

1. **本地优先** — 无云端依赖，所有数据存储在用户本地
2. **分层架构** — 清晰的关注点分离
3. **类型安全** — 全程类型标注和结构化数据
4. **可扩展** — 插件系统、MCP 协议接入外部工具
5. **可观测** — 结构化日志、指标和链路追踪
6. **安全** — 多级权限、沙箱模式、输入消毒

## 技术栈

**语言与运行时**
- Python 3.11+
- Node.js 18+ (前端)

**框架**
- FastAPI (Web API)
- SQLAlchemy 2.0 (ORM)
- Pydantic v2 (数据验证)
- pytest (测试)

**数据存储**
- SQLite (默认) / PostgreSQL (生产)
- ChromaDB (向量记忆)
- Redis (可选缓存)

**基础设施**
- Docker / Docker Compose
- Alembic (数据库迁移)
- Uvicorn (ASGI 服务器)

**外部服务**
- OpenAI / Anthropic / Google / Ollama (LLM 提供商)
- MCP Servers (外部工具协议)

## 项目结构

```
agent-engine/
├── app/
│   ├── api/v1/          # REST API 端点 (33 个路由模块)
│   ├── core/            # Agent 引擎核心 (149+ 模块)
│   │   ├── engine/      # 会话执行引擎
│   │   ├── memory/      # 记忆系统
│   │   ├── metacognition/ # 元认知模块
│   │   ├── prompt_engine/ # 提示词引擎
│   │   ├── reasoning/   # 推理模块
│   │   ├── security/    # 安全模块
│   │   └── execution/   # 执行器
│   ├── middleware/      # 中间件 (安全/指标/速率限制)
│   ├── models/          # LLM 模型适配器
│   ├── multi_agent/     # 多 Agent 编排
│   ├── skills/          # 技能系统
│   ├── storage/         # 数据持久化 (20+ 模型)
│   ├── tools/           # 工具运行时和内置工具
│   ├── utils/           # 工具函数
│   ├── workflow/        # 工作流引擎
│   ├── config.py        # 应用配置
│   └── main.py          # FastAPI 入口
├── frontend-react/      # React 前端
├── tests/               # 测试套件 (80+ 测试文件)
├── alembic/             # 数据库迁移
├── docs/                # 项目文档
├── Dockerfile           # Docker 构建
└── docker-compose.yml   # Docker Compose 编排
```

## 分层架构

```mermaid
flowchart TB
    subgraph Presentation["表示层"]
        React["React 前端\nVite + TypeScript"]
        Swagger["Swagger UI\n/docs"]
    end

    subgraph APILayer["API 层"]
        REST["REST API\n/api/v1"]
        SSE["SSE 流式"]
        WS["WebSocket"]
        Middleware["中间件链\nCORS → 安全头 → 速率限制 → 请求验证"]
    end

    subgraph AgentLayer["Agent 层"]
        Engine["AgentEngine\n主调度器"]
        MultiAgent["MultiAgent\n多 Agent 编排"]
        Crew["Crew\n层级协作"]
        AutoLoop["AutoLoop\n自主循环"]
    end

    subgraph CoreServices["核心服务层"]
        ContextMgr["ContextManager\n上下文管理"]
        ToolRT["ToolRuntime\n工具运行时"]
        PermCtrl["PermissionController\n权限控制"]
        ModelSched["ModelScheduler\n模型调度"]
        SessionMgr["SessionManager\n会话管理"]
        Memory["Memory\n分层记忆"]
    end

    subgraph Infra["基础设施层"]
        DB["SQLite / PostgreSQL"]
        Chroma["ChromaDB"]
        Redis["Redis"]
        MCP["MCP Servers"]
        LLM["LLM APIs"]
    end

    React --> Middleware
    Swagger --> REST
    Middleware --> REST
    Middleware --> SSE
    Middleware --> WS
    REST --> Engine
    SSE --> Engine
    WS --> Engine
    Engine --> MultiAgent
    Engine --> Crew
    Engine --> AutoLoop
    Engine --> ContextMgr
    Engine --> SessionMgr
    Engine --> Memory
    Engine --> PermCtrl
    MultiAgent --> ToolRT
    Crew --> ToolRT
    AutoLoop --> ToolRT
    ToolRT --> MCP
    ToolRT --> PermCtrl
    ContextMgr --> Memory
    ModelSched --> LLM
    SessionMgr --> DB
    Memory --> Chroma
    Memory --> Redis
```

## 核心子系统

### AgentEngine（主引擎）

**目的**: 协调所有组件，驱动 Agent 执行循环
**位置**: `app/core/agent_engine.py`
**依赖**: ModelRegistry, ToolRegistry, SessionManager, ContextManager
**被依赖**: API 层、多 Agent 编排、工作流引擎

```mermaid
flowchart LR
    subgraph AgentEngine
        Session["AgentSession\n会话状态"]
        ReactLoop["ReActLoop\n执行循环"]
        Checkpoint["Checkpoint\n检查点"]
    end

    Session --> ReactLoop
    ReactLoop --> Checkpoint
```

### ContextManager（上下文管理）

**目的**: 组装和管理五层上下文（系统/工作/长期/会话/动态）
**位置**: `app/core/context_manager.py`
**依赖**: Memory, Compressor
**被依赖**: AgentEngine

```mermaid
flowchart TB
    subgraph ContextPipeline["五层上下文管道"]
        Layer1["Layer 1: System\n系统提示词"]
        Layer2["Layer 2: Working\n工作记忆"]
        Layer3["Layer 3: Long-term\n长期记忆"]
        Layer4["Layer 4: Session\n会话历史"]
        Layer5["Layer 5: Dynamic\n动态上下文"]
    end

    Compressor["ContextCompressor\n上下文压缩"]
    Assembler["ContextAssembler\n上下文组装"]

    Layer1 --> Assembler
    Layer2 --> Compressor
    Layer3 --> Compressor
    Layer4 --> Compressor
    Layer5 --> Assembler
    Compressor --> Assembler
```

### ToolRuntime（工具运行时）

**目的**: 统一工具注册、发现和执行
**位置**: `app/core/tool_runtime.py`
**依赖**: MCPRegistry, PermissionController
**被依赖**: AgentEngine, MultiAgent

### PermissionController（权限控制）

**目的**: 7 级权限模式管理，危险命令拦截
**位置**: `app/core/permission_controller.py`
**依赖**: PermissionRules
**被依赖**: ToolRuntime, AgentEngine

### ModelScheduler（模型调度）

**目的**: 智能模型选择（成本/速度/可用性三维评分）+ 熔断降级
**位置**: `app/core/model_scheduler.py`
**依赖**: ModelRegistry, CircuitBreaker
**被依赖**: AgentEngine

### SessionManager（会话管理）

**目的**: 会话持久化、检查点/恢复/分叉
**位置**: `app/core/session_manager.py`
**依赖**: CheckpointStore
**被依赖**: AgentEngine

## 数据流

### 聊天请求流

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API Layer
    participant Engine as AgentEngine
    participant Session as SessionManager
    participant Context as ContextManager
    participant Model as ModelScheduler
    participant LLM as LLM Provider
    participant Perm as PermissionController
    participant Tool as ToolRuntime

    Client->>API: POST /api/v1/sessions/{id}/chat
    API->>Engine: 创建/恢复会话
    Engine->>Session: 加载会话状态
    Session-->>Engine: 会话上下文
    Engine->>Context: 组装五层上下文
    Context-->>Engine: 完整上下文
    Engine->>Model: 选择最优模型
    Model-->>Engine: 模型配置
    Engine->>LLM: 发送请求
    LLM-->>Engine: 响应/工具调用
    
    alt 工具调用
        Engine->>Perm: 检查权限
        Perm-->>Engine: 允许/拒绝
        Engine->>Tool: 执行工具
        Tool-->>Engine: 工具结果
        Engine->>LLM: 继续对话
    end
    
    Engine-->>API: SSE 流式事件
    API-->>Client: text/event-stream
```

### 多 Agent 协作流

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as API Layer
    participant Coord as Coordinator
    participant Worker1 as Worker A
    participant Worker2 as Worker B
    participant Reviewer as Reviewer

    User->>API: POST /api/v1/groups/{id}/run
    API->>Coord: 创建协作任务
    Coord->>Coord: 任务分解
    Coord->>Worker1: 分配子任务 A
    Coord->>Worker2: 分配子任务 B
    Worker1-->>Coord: 结果 A
    Worker2-->>Coord: 结果 B
    Coord->>Reviewer: 验证结果
    Reviewer-->>Coord: 审核通过
    Coord-->>API: 最终结果
    API-->>User: 响应
```

### 会话生命周期

```mermaid
stateDiagram-v2
    [*] --> Pending: 创建会话
    Pending --> Running: 开始对话
    Running --> Paused: 用户暂停
    Running --> Completed: 任务完成
    Running --> Failed: 执行失败
    Paused --> Running: 恢复
    Paused --> Cancelled: 取消
    Running --> Cancelled: 用户停止
    Completed --> [*]
    Failed --> [*]
    Cancelled --> [*]
```

### 权限检查流

```mermaid
flowchart TD
    A["工具调用请求"] --> B{"权限模式?"}
    B -->|"Read-Only"| C["仅允许读取工具"]
    B -->|"Standard"| D["检查规则列表"]
    B -->|"Bypass"| E["允许所有"]
    D --> F{"匹配规则?"}
    F -->|"Allow"| G["执行工具"]
    F -->|"Deny"| H["拒绝执行"]
    F -->|"Ask"| I["请求用户确认"]
    I -->|"允许"| G
    I -->|"拒绝"| H
```

## 模型适配层

```mermaid
flowchart LR
    subgraph Adapters["模型适配器"]
        OpenAI["OpenAIAdapter"]
        Anthropic["AnthropicAdapter"]
        Google["GoogleAdapter"]
        Ollama["OllamaAdapter"]
        StepFun["StepFunAdapter"]
    end

    Registry["ModelRegistry\n模型注册表"]
    Gateway["ModelGateway\n统一网关"]

    Registry --> Gateway
    Gateway --> OpenAI
    Gateway --> Anthropic
    Gateway --> Google
    Gateway --> Ollama
    Gateway --> StepFun
```

## 存储层

```mermaid
erDiagram
    AGENT ||--o{ SESSION : has
    SESSION ||--o{ MESSAGE : contains
    SESSION ||--o{ TURN : has
    AGENT ||--o{ API_KEY : owns
    CREW ||--o{ CREW_RUN : executes
    GROUP ||--o{ GROUP_MEMBER : has
    GROUP ||--o{ GROUP_MESSAGE : contains
    GROUP ||--o{ GROUP_TASK : has
    WORKFLOW ||--o{ WORKFLOW_RUN : executes

    AGENT {
        string id PK
        string name
        string provider
        string model_id
        text api_key_encrypted
        text system_prompt
        json tool_ids
    }
    SESSION {
        string id PK
        string agent_id FK
        string user_id
        string status
        json context_data
    }
    MESSAGE {
        string id PK
        string session_id FK
        string role
        text content
        json tool_calls
    }
```

## 安全架构

```mermaid
flowchart TB
    subgraph SecurityLayers["安全层"]
        direction TB
        L1["Layer 1: 传输安全\nHTTPS / HSTS"]
        L2["Layer 2: 请求验证\n大小限制 / JSON 深度"]
        L3["Layer 3: 速率限制\nToken Bucket"]
        L4["Layer 4: 认证授权\nJWT / API Key"]
        L5["Layer 5: 输入消毒\n路径验证 / Shell 分析"]
        L6["Layer 6: 权限控制\n7 级权限模式"]
        L7["Layer 7: 沙箱隔离\nDocker / 进程隔离"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7
```

## 部署拓扑

```mermaid
flowchart TB
    subgraph Docker["Docker Compose"]
        direction TB
        API["API Server\n:8000"]
        Frontend["Frontend\n:5173"]
        Postgres["PostgreSQL\n:5432"]
        Redis["Redis\n:6379"]
        Chroma["ChromaDB\n:8001"]
    end

    Internet["Internet / LAN"] --> Frontend
    Frontend --> API
    API --> Postgres
    API --> Redis
    API --> Chroma
```
