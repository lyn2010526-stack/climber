# Climber - 本地 AI Agent 工作台

本地优先、开源的 AI Agent 平台。无需注册登录，数据完全本地存储。

## 当前状态

- 后端 458 个测试全部通过
- 前端 React + TypeScript + Tailwind CSS v4
- FastAPI 后端，支持 SSE 实时事件流
- SQLite / PostgreSQL 双支持
- ChromaDB 向量记忆
- OpenTelemetry 可观测性
- Playwright E2E 测试就绪

## 核心能力

| 能力 | 说明 |
|------|------|
| 分层记忆 | 短期 / 工作 / 长期三层记忆，支持长上下文 KDA 优化 |
| 多 Agent 协作 | 自动任务拆解、并行调度、结果聚合 |
| 工具系统 | 结构化元数据、Schema 校验、语义校验、动态加载 |
| 沙箱执行 | 隔离运行、快照、暂停/恢复、回滚 |
| 模型路由 | 三维评分（成本/速度/可用性）+ 熔断降级 |
| RBAC + 审计 | 角色权限控制、操作审计日志 |
| CI/CD Webhook | GitHub / GitLab 自动触发 |
| 代码审查图谱 | code-review-graph 集成，降低 Token 消耗，支持 19 种语言 |
| 本地模型 | Ollama / vLLM / llama.cpp 支持 |

## 技术栈

### 后端
- Python 3.11+ / FastAPI / async-first
- OpenAI / Anthropic / Gemini / Ollama 适配
- SQLAlchemy 2.0 + async
- ChromaDB 向量数据库
- structlog 结构化日志
- Prometheus metrics

### 前端
- React 19 / TypeScript
- Tailwind CSS v4 + CSS variables
- Vite 8
- Zustand 状态管理
- react-markdown + remark-gfm
- Monaco Editor

## 快速开始

```bash
# 后端
cd agent-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend-react
npm install
npm run dev
```

访问：
- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 测试

```bash
# 后端测试
cd agent-engine
python3 -m pytest tests/ --tb=no -q

# 前端测试
cd frontend-react
npm test

# E2E 测试
cd frontend-react
npm run test:e2e
```

## 部署

详见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## License

MIT
