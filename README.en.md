# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Languages: [简体中文](README.md) · **English** · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

**Climber is a local-first, self-hostable open-source AI Agent workspace.** It provides Agent sessions, multi-Agent collaboration, workflow orchestration, tools and MCP integration, model adapters, permission approvals, checkpoint recovery and execution tracing.

## Overview

Climber is designed for local development, experimentation and controlled deployments. Development uses SQLite by default and can use PostgreSQL, Redis and ChromaDB. Model providers, MCP Servers, Telegram and other integrations are configured by the operator and may send related requests to external services.

Production environments enable authentication automatically. The production Docker setup provides an HTTP entry point; HTTPS, certificate termination and a public reverse proxy are deployment responsibilities.

## Core Capabilities

| Capability | Description |
| --- | --- |
| Agents and sessions | Execution loops, streaming responses, persistence, checkpoints and recovery |
| Multi-Agent collaboration | Sequential, hierarchical, group-chat and workflow orchestration |
| Tools and MCP | Unified tool runtime, MCP Server integration and approval flows |
| Model adapters | OpenAI, Anthropic, Google, Ollama, StepFun and other providers |
| Memory and context | Layered memory, vector storage, compression and archival |
| Permissions | `allow` / `ask` / `deny` rules and six session modes |
| Safety boundaries | Path restrictions, shell-risk checks, SSRF protection and sandbox integrations |
| Scientific simulation | heat, oscillator and logistic experiment backends with JSONL ledgers |
| Observability | Structured logs, metrics, token usage and execution traces |
| Headless CLI | Standalone task execution, workspace sandbox and JSONL traces |

`Bypass` skips permission checks and should only be used in controlled environments.

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+
- npm and Docker Compose v2 for Docker deployments
- At least one LLM provider or a local Ollama instance

### Local Development

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

In another terminal:

```bash
cd climber/frontend-react
npm install
npm run dev
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/v1 |
| Swagger | http://localhost:8000/docs |
| OpenAPI | http://localhost:8000/openapi.json |
| Health | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics |

The Vite server proxies `/api`, `/health` and `/ws` to `VITE_PROXY_TARGET`, which defaults to `http://localhost:8000`.

### Docker Development

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

The development Compose file publishes frontend `5173`, API `8000`, PostgreSQL `5432`, Redis `6379` and Chroma `8001` for local debugging.

### Docker Production

The production Compose file exposes only the Nginx entry point on host port `8000`:

```bash
export POSTGRES_PASSWORD='at-least-32-url-safe-characters'
export APP_SECRET_KEY='at-least-32-stable-random-characters'
export INITIAL_ADMIN_PASSWORD='strong-first-admin-password'

docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d --build
```

Nginx serves the frontend and proxies `/api` and `/health`. PostgreSQL, Redis and ChromaDB stay on the internal Compose network. TLS must be configured at an external reverse proxy or load balancer.

## Configuration and Data Boundaries

Common settings are listed in `.env.example`:

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

Local development defaults to disabled authentication. `production` and `staging` enable authentication automatically. Protected APIs support `X-API-Key` and `Authorization: Bearer <token>`. The current SPA does not promise a complete production login handoff out of the box.

Application data is stored locally or on infrastructure controlled by the operator by default. Enabling external LLMs, MCP Servers, Telegram, search, weather, translation or other integrations can send related requests and credentials to third-party services. Never commit real secrets to the repository, frontend code or logs.

## Headless CLI

The standalone CLI runs file tools in a dedicated workspace and writes a JSONL trace:

```bash
mkdir -p /tmp/climber-task
python3 -m app.headless \
  --task examples/headless/task.json \
  --workspace /tmp/climber-task \
  --trace /tmp/climber-trace.jsonl
```

Real model mode uses `USER_LLM_API_KEY`, `USER_LLM_BASE_URL` and `USER_LLM_MODEL`. `--fake-model` is only for deterministic scripted tests. The workspace must already exist and the trace must be outside it.

## Testing

```bash
python3 -m pytest tests/

cd frontend-react
npm run typecheck
npm run lint
npm test
npm run i18n:check
npm run build
npm run test:e2e
```

See [.github/workflows/ci.yml](.github/workflows/ci.yml) for CI. Test counts vary by revision and environment; use CI and dated reports as the source of truth.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Development](docs/DEVELOPMENT.md)
- [Security](docs/SECURITY.md)
- [Style guide](docs/STYLE_GUIDE.md)
- [Contributing](CONTRIBUTING.md)
- [Environment template](.env.example)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Run the checks relevant to your change, update API/configuration documentation when needed, and keep secrets, user data, local databases and build artifacts out of commits.

## License

Climber is licensed under the [MIT License](LICENSE). Third-party dependencies, model providers, MCP Servers and external integrations follow their own licenses and terms.
