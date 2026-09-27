# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**本地优先、可自托管的开源 AI Agent 工作台。** Climber 提供 Agent 会话、多 Agent 协作、工作流编排、工具和 MCP 接入、模型适配、权限审批、检查点恢复与执行追踪。

语言：
[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

## 项目概览

Climber 面向本地开发、实验和可控部署场景。开发模式默认使用本地 SQLite，并支持 PostgreSQL、Redis 和 ChromaDB。模型提供商、MCP Server、Telegram 以及其他集成均由部署者配置，启用后相关请求可能访问外部服务。

生产环境会自动启用认证。当前生产 Docker 配置提供 HTTP 入口，HTTPS、证书终止和公网反向代理需要由部署环境负责。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| Agent 与会话 | 执行循环、流式响应、会话持久化、检查点与恢复 |
| 多 Agent 协作 | 顺序、层级、群聊与工作流编排 |
| 工具与 MCP | 统一工具运行时、MCP Server 接入、工具调用审批 |
| 模型适配 | OpenAI、Anthropic、Google、Ollama、StepFun 等提供商 |
| 记忆与上下文 | 分层记忆、向量存储、上下文压缩与归档 |
| 权限控制 | `allow` / `ask` / `deny` 规则、Default/Accept Edits/Plan/Auto/Strict/Bypass 模式 |
| 安全边界 | 路径限制、Shell 风险拦截、SSRF 防护、沙箱集成与提示词注入防护 |
| 科学仿真 | heat、oscillator、logistic 等实验后端与 JSONL 执行账本 |
| 可观测性 | 结构化日志、指标、Token 用量和执行追踪 |
| Headless CLI | 独立任务运行、工作区沙箱和 JSONL trace |

`Bypass` 会跳过权限检查，只应在受控环境中使用。

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- npm、Docker Compose v2（Docker 部署时）
- 至少一个 LLM Provider，或本地 Ollama

### 本地开发

```bash
git clone https://github.com/lyn2010526-stack/climber.git
cd climber

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

另开终端启动前端：

```bash
cd climber/frontend-react
npm install
npm run dev
```

开发模式地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:5173 |
| API | http://localhost:8000/api/v1 |
| Swagger | http://localhost:8000/docs |
| OpenAPI | http://localhost:8000/openapi.json |
| 健康检查 | http://localhost:8000/health |
| 指标 | http://localhost:8000/metrics |

前端 Vite 会把 `/api`、`/health` 和 `/ws` 代理到 `VITE_PROXY_TARGET`，默认目标是 `http://localhost:8000`。

### Docker 开发环境

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

开发 Compose 发布前端 `5173`、API `8000`、PostgreSQL `5432`、Redis `6379` 和 Chroma `8001`，适合本地调试。

### Docker 生产环境

生产 Compose 只对外发布 Nginx 的 `8000` 入口。启动前提供强随机配置：

```bash
export POSTGRES_PASSWORD='至少32位的URL-safe密码'
export APP_SECRET_KEY='至少32位的稳定随机密钥'
export INITIAL_ADMIN_PASSWORD='首次初始化时使用的强密码'

docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d --build
```

生产入口为 `http://localhost:8000`。Nginx 提供前端静态文件并代理 `/api` 和 `/health`；PostgreSQL、Redis、ChromaDB 仅在 Compose 内部网络访问。当前配置没有内置 TLS，请在外部反向代理或负载均衡层配置 HTTPS。

## 配置与数据边界

常用配置位于 `.env.example`：

```env
APP_ENV=development
APP_SECRET_KEY=
DATABASE_URL=sqlite+aiosqlite:///./data/climber.db
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL_SPEC=gpt-4o-mini
ENABLE_AUTH=
INITIAL_ADMIN_PASSWORD=
```

本地开发模式默认关闭认证；`production` 和 `staging` 会自动启用认证。启用认证后，受保护 API 支持 `X-API-Key` 和 `Authorization: Bearer <token>`。生产部署需要由部署者提供认证入口和 HTTPS，当前 SPA 不承诺开箱即用的生产登录页面。

应用数据默认保存在本地或自有基础设施。启用外部 LLM、MCP Server、Telegram、搜索、天气、翻译或其他集成后，相应请求内容和凭据会按照配置发送到第三方服务。不要把真实密钥提交到仓库、前端代码或日志中。

## 架构与项目结构

```text
app/
├── api/v1/       # REST API、SSE、WebSocket
├── core/         # Agent Engine、会话、权限、记忆与安全
├── headless/     # 独立 Headless CLI
├── models/       # LLM Provider 适配
├── storage/      # 数据持久化
├── tools/        # 工具运行时与 MCP
└── workflow/     # 工作流引擎
frontend-react/   # React + Vite 工作台
alembic/          # 数据库迁移
tests/            # 后端测试
docs/             # 公开项目文档
```

完整架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## Headless CLI

Headless CLI 不依赖 Web 服务器和数据库，使用专用工作区运行文件工具并写出 JSONL trace：

```bash
mkdir -p /tmp/climber-task
python3 -m app.headless \
  --task examples/headless/task.json \
  --workspace /tmp/climber-task \
  --trace /tmp/climber-trace.jsonl
```

真实模型模式需要用户自行配置 `USER_LLM_API_KEY`、`USER_LLM_BASE_URL` 和 `USER_LLM_MODEL`。`--fake-model` 只用于确定性脚本测试，不能代表真实模型能力。工作区必须是已有的专用目录，trace 必须位于工作区之外。

## 测试与质量检查

```bash
# 后端
python3 -m pytest tests/

# 前端
cd frontend-react
npm run typecheck
npm run lint
npm test
npm run i18n:check
npm run build
npm run test:e2e
```

CI 工作流位于 [.github/workflows/ci.yml](.github/workflows/ci.yml)。测试数量随代码和环境变化，以 CI 和最新测试报告为准。

## 文档

- [公开文档索引](docs/INDEX.md)
- [架构](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [部署](docs/DEPLOYMENT.md)
- [开发指南](docs/DEVELOPMENT.md)
- [安全策略](docs/SECURITY.md)
- [样式指南](docs/STYLE_GUIDE.md)
- [贡献指南](CONTRIBUTING.md)
- [环境变量模板](.env.example)

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。提交代码前请运行与改动范围相关的测试，更新 API、配置和文档，并确保提交中没有密钥、用户数据、本地数据库或构建产物。

## License

Climber 使用 [MIT License](LICENSE)。第三方依赖、模型提供商、MCP Server 和外部集成遵循各自的许可证与服务条款。
