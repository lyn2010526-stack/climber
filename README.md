# Climber — 本地优先 AI Agent 工作台

[![Tests](https://img.shields.io/badge/tests-458%2B%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

> 本地优先、开源的 AI Agent 平台。无需注册登录，数据完全本地存储。

## 特性

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
source venv/bin/activate  # Windows: venv\Scripts\activate

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

### 访问

- 前端界面：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 配置

### 环境变量

创建 `.env` 文件：

```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# 数据库
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

### AGENT_SPEC.md

创建 `AGENT_SPEC.md` 定义项目约束：

```markdown
# Agent 配置

## 项目信息
- 名称：My Project
- 语言：Python
- 框架：FastAPI

## 约束
- 所有代码必须有类型标注
- 提交前运行 pytest
- 遵循 PEP 8 规范

## 验收标准
- 单元测试覆盖率 > 80%
- 所有 API 有错误处理
- 无安全漏洞

## 输出格式
- Git commit 信息遵循 Conventional Commits
- PR 描述包含变更摘要和测试结果
```

## 架构

```
Climber Architecture
====================

┌─────────────────────────────────────────────────┐
│                  Frontend (React)                 │
│         Chat UI / Monitor / Config                │
└─────────────────────────────────────────────────┘
                        │ HTTP / SSE
┌─────────────────────────────────────────────────┐
│                  API Layer (FastAPI)              │
│         /api/v1/chat /sessions /agents           │
└─────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────┐
│               Agent Engine Core                   │
│  ┌─────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Context │ │ Tool     │ │ Permission       │ │
│  │ Manager │ │ Runtime  │ │ Controller       │ │
│  └─────────┘ └──────────┘ └──────────────────┘ │
│  ┌─────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Model   │ │ Session  │ │ Iteration        │ │
│  │Scheduler│ │ Manager  │ │ Guard            │ │
│  └─────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────┘
                        │
┌─────────────────────────────────────────────────┐
│              Infrastructure                      │
│  SQLite / ChromaDB / MCP Servers / LLM APIs     │
└─────────────────────────────────────────────────┘
```

## 核心模块

### Agent Engine
- `app/core/agent_engine.py` — 主引擎，协调所有组件
- `app/core/engine/session.py` — 会话管理
- `app/core/engine/react_loop.py` — ReAct 执行循环

### 上下文与记忆
- `app/core/context_manager.py` — 五层上下文管道
- `app/core/compressor.py` — 上下文压缩
- `app/core/memfs/` — Git 备份的记忆文件系统

### 工具系统
- `app/core/tool_runtime.py` — 统一工具运行时
- `app/engine/mcp_bridge.py` — MCP 工具桥接
- `app/tools/` — 内置工具

### 安全与权限
- `app/core/permission_controller.py` — 权限控制器
- `app/core/security_utils.py` — 安全工具

### 多 Agent
- `app/engine/multi_agent.py` — 多 Agent 编排
- `app/multi_agent/safety.py` — 死锁检测与冲突仲裁

### 模型与调度
- `app/core/model_scheduler.py` — 智能模型选择
- `app/core/error_handler.py` — 错误处理与熔断

## API 参考

### 聊天
```
POST /api/v1/chat/
Body: { "agent_id": "...", "message": "...", "stream": true }
Response: SSE stream of Frame events
```

### 会话
```
GET    /api/v1/sessions/            # 列表
GET    /api/v1/sessions/{id}        # 详情
POST   /api/v1/sessions/{id}/fork   # 分叉
DELETE /api/v1/sessions/{id}        # 删除
```

### Agent
```
GET    /api/v1/agents/               # 列表
POST   /api/v1/agents/               # 创建
PUT    /api/v1/agents/{id}           # 更新
DELETE /api/v1/agents/{id}           # 删除
```

## 测试

```bash
# 后端测试
cd agent-engine
python3 -m pytest tests/ -v

# 前端测试
cd frontend-react
npm test

# E2E 测试
cd frontend-react
npm run test:e2e
```

## 部署

### Docker

```bash
docker-compose up -d
```

### 手动部署

```bash
# 后端
cd agent-engine
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend-react
npm install
npm run build
# 部署 dist/ 到 Nginx
```

## 贡献指南

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing`)
3. 提交变更 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing`)
5. 创建 Pull Request

### 代码规范
- Python: PEP 8, type hints, docstrings
- TypeScript: ESLint + Prettier
- 提交信息: Conventional Commits

## License

MIT
