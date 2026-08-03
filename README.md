# Climber — 本地优先 AI Agent 工作台

[![Tests](https://img.shields.io/badge/tests-458%2B%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.88%2B-009688)]()
[![React](https://img.shields.io/badge/React-18%2B-61DAFB)]()

> 本地优先、开源的 AI Agent 平台。无需注册登录，数据完全本地存储。

## 项目介绍

Climber 是一个生产级 AI Agent 工作台，支持自主软件开发、多 Agent 协作和工具扩展。系统采用分层架构设计，提供从模型调度、上下文管理到权限控制的全栈能力。所有数据默认存储在本地 SQLite，可选 PostgreSQL 用于多用户并发场景。

### 核心能力

| 能力 | 说明 |
|------|------|
| 分层记忆 | 短期/工作/长期三层记忆，支持上下文压缩和热冷分区 |
| 多 Agent 协作 | Fork/Coordinator/Teams 三种模式，支持死锁检测和冲突仲裁 |
| 工具系统 | 统一工具运行时，MCP 协议接入，安全沙箱隔离 |
| 模型调度 | 智能模型选择（成本/速度/可用性三维评分）+ 熔断降级 |
| 权限控制 | 7 级权限模式（Read-Only → Bypass），危险命令拦截 |
| 会话持久化 | 检查点/恢复/分叉，断点续跑 |
| 安全加固 | 路径穿越防护、Shell 风险分析、Prompt 注入检测 |
| 可观测性 | 结构化日志、JSON 指标、Token 用量追踪 |
| 提示词管理 | 外部模板加载，AGENT_SPEC.md 支持 |

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- pip / npm

### 后端启动

```bash
# 克隆仓库
git clone https://github.com/lyn2010526-stack/climber.git
cd climber/agent-engine

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend-react
npm install
npm run dev
```

### Docker 启动

```bash
docker-compose up -d
```

### 访问地址

| 服务 | URL |
|------|-----|
| 前端界面 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| 指标 | http://localhost:8000/metrics |

## 系统架构

```mermaid
flowchart TB
    subgraph Client["客户端层"]
        Frontend["React 前端\nVite + TypeScript"]
        Telegram["Telegram Bot"]
    end

    subgraph API["API 层 (FastAPI)"]
        REST["REST API\n/api/v1"]
        WS["WebSocket\n/ws"]
        SSE["SSE 流式"]
        Middleware["中间件\nCORS / 安全头\n速率限制 / 请求验证"]
    end

    subgraph AgentEngine["Agent 引擎核心"]
        Engine["AgentEngine\n主调度器"]
        SessionMgr["SessionManager\n会话/检查点/分叉"]
        ContextMgr["ContextManager\n五层上下文管道"]
        ReactLoop["ReActLoop\n执行循环"]
    end

    subgraph CoreServices["核心服务层"]
        ModelSched["ModelScheduler\n智能模型选择"]
        ToolRT["ToolRuntime\n统一工具运行时"]
        PermCtrl["PermissionController\n7 级权限控制"]
        Memory["Memory\n分层记忆系统"]
        Safety["SafetyPipeline\n安全防护"]
    end

    subgraph Infra["基础设施层"]
        DB["SQLite / PostgreSQL"]
        Chroma["ChromaDB\n向量记忆"]
        Redis["Redis\n缓存"]
        MCP["MCP Client\n外部工具"]
        LLM["LLM Provider\n多模型适配"]
    end

    Frontend --> Middleware
    Telegram --> Engine
    Middleware --> REST
    Middleware --> WS
    REST --> SSE
    REST --> Engine
    WS --> Engine
    Engine --> SessionMgr
    Engine --> ContextMgr
    Engine --> ReactLoop
    ReactLoop --> ModelSched
    ReactLoop --> ToolRT
    ReactLoop --> PermCtrl
    Engine --> Memory
    Engine --> Safety
    ModelSched --> LLM
    ToolRT --> MCP
    SessionMgr --> DB
    Memory --> Chroma
    Memory --> Redis
    ContextMgr --> Memory
```

## 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| Agent Engine | `app/core/agent_engine.py` | 主引擎，协调所有组件 |
| 会话管理 | `app/core/engine/session.py` | 会话生命周期管理 |
| 上下文管理 | `app/core/context_manager.py` | 五层上下文管道 |
| 工具运行时 | `app/core/tool_runtime.py` | 统一工具执行 |
| MCP 桥接 | `app/engine/mcp_bridge.py` | MCP 工具协议接入 |
| 权限控制 | `app/core/permission_controller.py` | 权限规则引擎 |
| 模型调度 | `app/core/model_scheduler.py` | 智能模型选择 |
| 安全工具 | `app/core/security_utils.py` | 路径/Shell/Prompt 安全 |
| 多 Agent | `app/engine/multi_agent.py` | 多 Agent 编排 |

## 配置说明

创建 `.env` 文件（参考 `.env.example`）：

```env
# API Keys（至少配置一个）
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# 数据库（默认 SQLite）
DATABASE_URL=sqlite+aiosqlite:///./data/climber.db

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json

# Token 保护
MAX_TOKENS_PER_SESSION=100000
MAX_COST_PER_DAY=10.0

# 安全
SANDBOX_MODE=false
ALLOWED_PATHS=/workspace/projects

# 模型调度
DEFAULT_MODEL=anthropic/claude-sonnet-4-20250514
FALLBACK_CHAIN=anthropic/claude-sonnet-4-20250514,openai/gpt-4o,ollama/llama3.3
```

## 文档

| 文档 | 描述 |
|------|------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构、模块关系、数据流 |
| [API.md](docs/API.md) | 所有 API 端点详细说明 |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 部署指南（Docker、本地、云） |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | 开发指南、代码规范、测试方法 |
| [SECURITY.md](docs/SECURITY.md) | 安全策略、已知风险、防护措施 |

## 测试

```bash
# 后端测试
python3 -m pytest tests/ -v

# 前端测试
cd frontend-react
npm test

# E2E 测试
cd frontend-react
npm run test:e2e
```

## 贡献指南

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT
