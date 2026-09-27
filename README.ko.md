# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

언어: [简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · **한국어** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

**Climber는 로컬 우선으로 실행할 수 있는 오픈 소스 AI Agent 워크스페이스입니다.** Agent 세션, 멀티 Agent 협업, 워크플로 오케스트레이션, 도구와 MCP 연동, 모델 어댑터, 권한 승인, 체크포인트 복구와 실행 추적을 제공합니다.

## 개요

개발 환경은 기본적으로 SQLite를 사용하며 PostgreSQL, Redis, ChromaDB도 사용할 수 있습니다. LLM Provider, MCP Server, Telegram 및 외부 통합을 활성화하면 설정에 따라 외부 서비스로 요청이 전송될 수 있습니다. production과 staging에서는 인증이 자동으로 활성화됩니다. HTTPS는 외부 reverse proxy에서 구성해야 합니다.

## 주요 기능

- Agent 세션, 스트리밍 응답, 영속성, 체크포인트와 복구
- 순차형, 계층형, 그룹형 멀티 Agent 협업과 워크플로
- 통합 도구 런타임, MCP Server, 승인 흐름
- OpenAI, Anthropic, Google, Ollama, StepFun 등 모델 Provider
- 계층형 메모리, 벡터 저장소, 컨텍스트 압축
- 권한 규칙, SSRF 보호, 경로 제한과 sandbox 연동
- 독립 Headless CLI와 JSONL 실행 trace

`Bypass` 모드는 권한 검사를 건너뛰므로 통제된 환경에서만 사용해야 합니다.

## 빠른 시작

요구 사항: Python 3.11+, Node.js 18+, npm, Docker Compose v2 및 LLM Provider 또는 Ollama.

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

다른 터미널에서 프론트엔드를 실행합니다.

```bash
cd frontend-react
npm install
npm run dev
```

개발 URL: Frontend `http://localhost:5173`, API `http://localhost:8000/api/v1`, Swagger `http://localhost:8000/docs`, OpenAPI `http://localhost:8000/openapi.json`, Health `http://localhost:8000/health`, Metrics `http://localhost:8000/metrics`. Vite는 `/api`, `/health`, `/ws`를 `VITE_PROXY_TARGET`으로 프록시합니다.

### Docker 개발

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

개발 Compose는 Frontend `5173`, API `8000`, PostgreSQL `5432`, Redis `6379`, Chroma `8001`을 공개합니다.

### Docker 운영

```bash
export POSTGRES_PASSWORD='at-least-32-url-safe-characters'
export APP_SECRET_KEY='at-least-32-stable-random-characters'
export INITIAL_ADMIN_PASSWORD='strong-first-admin-password'
docker compose -f docker-compose.yml up -d --build
```

## 설정과 보안

LLM 키는 `.env`에 설정하고 저장소에 커밋하지 마세요. 로컬 개발에서는 인증이 기본적으로 꺼져 있지만 production과 staging에서는 인증이 켜집니다. 외부 LLM, MCP, Telegram, 검색 등의 기능을 사용하면 대화와 도구 관련 데이터가 외부 서비스로 전송될 수 있습니다.

## 테스트

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

## 문서

- [문서 색인](docs/INDEX.md)
- [아키텍처](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [배포](docs/DEPLOYMENT.md)
- [보안](docs/SECURITY.md)
- [스타일 가이드](docs/STYLE_GUIDE.md)
- [기여 가이드](CONTRIBUTING.md)
- [환경 변수](.env.example)

## 라이선스

Climber는 [MIT License](LICENSE)로 배포됩니다.
