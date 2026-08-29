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
| 插件化内核 | 一切皆插件：生命周期/依赖注入/类型化事件总线，minimal/complete/offline/developer 四模式运行时切换 |
| 统一 Run 协议 | Run/Message/Event/Trace/Checkpoint 统一生命周期，持久化回放、恢复、取消与列表查询 |
| 四层记忆 | 短期窗口 / 中期任务级 / 长期 MEMORY.md+USER.md（冻结快照+diff 确认）/ 技能库元数据常驻 |
| 超长上下文 | 等效无限：RAG / 滑动窗口+自动摘要 / 分层记忆 / 子 Agent 隔离 / 上下文压缩 / 外部状态查询，32K 预算优先级裁剪 |
| 闭环自学习 | L1 实时修正技能 / L2 后台蒸馏 / L3 定期审查，版本历史可回滚 |
| 统一能力抽象 | Capability 统一描述 + 7 类适配器 + 成功率/成本/偏好路由 + 能力市场 (.cap) |

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- pip / npm

### 后端启动

```bash
# 克隆仓库
git clone https://github.com/lyn2010526-stack/climber.git
cd climber

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
npm ci
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

# Architecture V2（全部默认关闭，打开 master 后按需启用各模块）
ENABLE_ARCH_V2=false
ENABLE_PLUGIN_KERNEL=true
ENABLE_FOUR_LAYER_MEMORY=true
ENABLE_LONG_CONTEXT=true
ENABLE_SELF_LEARNING=true
ENABLE_CAPABILITY=true
ENABLE_TRACE_LOG=true
ENABLE_SKILL_STORE=true

# 统一 Run 协议（持久化 Run 事件与回放）
ENABLE_UNIFIED_RUN=true
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

### 插件化内核（Architecture V2）
- `app/core/plugin_kernel/` — 插件生命周期 / 依赖注入 / 类型化事件总线 / 四模式 profile
- `app/core/four_layer_memory/` — 四层记忆 + FTS5 全文索引
- `app/core/long_context/` — 超长上下文（预算裁剪/滑动窗口/压缩/前缀缓存/RAG）
- `app/core/self_learning/` — L1 实时修正 / L2 后台蒸馏 / L3 定期审查
- `app/core/capability/` — 统一能力抽象 / 适配器 / 注册表 / 能力市场 / 进化
- `app/core/trace_log/` — append-only 事件日志（Replay/Fork/Search/Trajectory）
- `app/core/skill_store/` — 技能三级加载 / 使用统计 / .skill 市场
- `app/core/integration/` — 协议路由 / 事件溯源

### 统一 Run 协议
- `app/core/run_protocol.py` — Run/Event/Message 协议、状态机、回放
- `app/storage/run_store.py` — SQLAlchemy Run 持久化存储
- `app/core/agent_run_adapter.py` — AgentEngine 到 Run 的适配
- `app/core/raw_payload.py` — Provider 原始载荷策略（standard/debug）
- `app/api/v1/runs.py` — Run 管理 API（查询/事件/取消/恢复）
- `app/core/run_cleanup.py` — 陈旧 Run 与过期载荷清理

### 四代涌现模块（可选，默认关闭）
- `app/core/emergent/` — 自主能力发现 / Meta-Agent / 目标推演 / 局部蜂群
- `app/core/security/hard_guard.py` — 不可变硬安全防护层 + 快照回滚

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

### Run（统一执行协议）
```
GET    /api/v1/runs/                 # 列表（session/status/user 过滤 + 分页）
GET    /api/v1/runs/{id}             # 详情（状态/trace_id/checkpoint/游标范围）
GET    /api/v1/runs/{id}/events      # 事件回放（after 游标 + gap 检测）
POST   /api/v1/runs/{id}/cancel      # 取消
POST   /api/v1/runs/{id}/resume      # 恢复
```

## 测试

```bash
# 后端测试
python3 -m pytest tests/ -v

# 前端测试
cd frontend-react
npm run test

# Return to the repository root
cd ..
```

当前基线：后端 1964 passed / 16 skipped；前端 205 passed（vitest）+ tsc 无错误。完整回归约 23 分钟，单进程运行（`APP_TESTING=true ENABLE_AUTH=false python3 -m pytest tests/ -q`）。

## 部署

### Docker

```bash
# 创建 .env 并替换数据库密码占位符
cp .env.example .env

docker compose up -d
```

Compose 要求配置 `POSTGRES_PASSWORD` 和 `REDIS_PASSWORD`。应用会安全编码密码中的 URL 特殊字符，可直接使用包含 `@:/?#%` 的高熵随机值。API 在 `8000` 端口同时提供前端页面和 API，PostgreSQL 与 Redis 仅在 Compose 内网开放。

### 手动部署

```bash
# 后端
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend-react
npm ci
npm run build

# 将 dist/ 部署到 Nginx
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
