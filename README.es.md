# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Idiomas: [简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · **Español** · [Français](README.fr.md) · [Deutsch](README.de.md)

**Climber es un espacio de trabajo de AI Agents de código abierto, local-first y autoalojable.** Incluye sesiones de Agent, colaboración multi-Agent, orquestación de workflows, herramientas y MCP, adaptadores de modelos, aprobación de permisos, recuperación mediante checkpoints y trazas de ejecución.

## Descripción general

El desarrollo local usa SQLite por defecto y también admite PostgreSQL, Redis y ChromaDB. Los proveedores LLM, MCP Servers, Telegram y otras integraciones se configuran por el operador y pueden enviar solicitudes a servicios externos. Los entornos production y staging activan la autenticación automáticamente. HTTPS debe configurarse en un reverse proxy externo.

## Características principales

- Sesiones de Agent, respuestas streaming, persistencia y recuperación
- Colaboración multi-Agent secuencial, jerárquica y grupal
- Runtime de herramientas, integración MCP y flujos de aprobación
- Proveedores OpenAI, Anthropic, Google, Ollama, StepFun y otros
- Memoria por capas, almacenamiento vectorial y compresión de contexto
- Reglas `allow` / `ask` / `deny`, restricciones de rutas y protección SSRF
- Headless CLI y trazas de ejecución en JSONL
- Métricas, logs estructurados y seguimiento de tokens

El modo `Bypass` omite las comprobaciones de permisos y solo debe utilizarse en entornos controlados.

## Inicio rápido

Requisitos: Python 3.11+, Node.js 18+, npm, Docker Compose v2 y un proveedor LLM o Ollama.

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

En otra terminal:

```bash
cd frontend-react
npm install
npm run dev
```

URLs de desarrollo: Frontend `http://localhost:5173`, API `http://localhost:8000/api/v1`, Swagger `http://localhost:8000/docs`, OpenAPI `http://localhost:8000/openapi.json`, Health `http://localhost:8000/health` y Metrics `http://localhost:8000/metrics`. Vite hace proxy de `/api`, `/health` y `/ws` hacia `VITE_PROXY_TARGET`, cuyo valor predeterminado es `http://localhost:8000`.

### Docker para desarrollo

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

Docker Compose de desarrollo publica Frontend `5173`, API `8000`, PostgreSQL `5432`, Redis `6379` y Chroma `8001`.

### Docker para producción

```bash
export POSTGRES_PASSWORD='at-least-32-url-safe-characters'
export APP_SECRET_KEY='at-least-32-stable-random-characters'
export INITIAL_ADMIN_PASSWORD='strong-first-admin-password'
docker compose -f docker-compose.yml up -d --build
```

La entrada de producción es `http://localhost:8000`; configura TLS en un reverse proxy externo.

## Configuración y seguridad

Configura las claves LLM en `.env` y nunca las incluyas en el repositorio. El desarrollo local permite ejecutar sin autenticación por defecto; production y staging requieren autenticación. Al usar LLM externos, MCP, Telegram, búsqueda u otras integraciones, los datos relacionados pueden enviarse a terceros según la configuración.

## Pruebas

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

## Documentación

- [Índice de documentación](docs/INDEX.md)
- [Arquitectura](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Despliegue](docs/DEPLOYMENT.md)
- [Seguridad](docs/SECURITY.md)
- [Guía de estilo](docs/STYLE_GUIDE.md)
- [Contribuir](CONTRIBUTING.md)
- [Variables de entorno](.env.example)

## Licencia

Climber se distribuye bajo la [licencia MIT](LICENSE).
