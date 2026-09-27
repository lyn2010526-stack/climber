# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Sprachen: [简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · **Deutsch**

**Climber ist ein lokal ausgerichteter, selbst hostbarer Open-Source-Arbeitsbereich für AI Agents.** Er bietet Agent-Sitzungen, Multi-Agent-Kollaboration, Workflow-Orchestrierung, Tools und MCP, Modelladapter, Berechtigungsfreigaben, Checkpoint-Wiederaufnahme und Ausführungstraces.

## Projektübersicht

Die lokale Entwicklung verwendet standardmäßig SQLite und kann PostgreSQL, Redis und ChromaDB nutzen. LLM-Provider, MCP-Server, Telegram und weitere Integrationen werden vom Betreiber konfiguriert und können Anfragen an externe Dienste senden. In Production und Staging wird die Authentifizierung automatisch aktiviert. HTTPS muss über einen externen Reverse Proxy eingerichtet werden.

## Hauptfunktionen

- Agent-Sitzungen, Streaming-Antworten, Persistenz und Wiederaufnahme
- Sequenzielle, hierarchische und gruppenbasierte Multi-Agent-Kollaboration
- Tool-Runtime, MCP-Integration und Freigabe-Workflows
- OpenAI, Anthropic, Google, Ollama, StepFun und weitere Provider
- Schichtenbasierter Speicher, Vektorspeicher und Kontextkompression
- `allow` / `ask` / `deny`-Regeln, Pfadbeschränkungen und SSRF-Schutz
- Headless CLI und JSONL-Ausführungstraces
- Strukturierte Logs, Metriken und Token-Verfolgung

Der Modus `Bypass` überspringt Berechtigungsprüfungen und gehört ausschließlich in kontrollierte Umgebungen.

## Schnellstart

Voraussetzungen: Python 3.11+, Node.js 18+, npm, Docker Compose v2 sowie ein LLM-Provider oder Ollama.

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

In einem zweiten Terminal:

```bash
cd frontend-react
npm install
npm run dev
```

Entwicklungs-URLs: Frontend `http://localhost:5173`, API `http://localhost:8000/api/v1`, Swagger `http://localhost:8000/docs`, OpenAPI `http://localhost:8000/openapi.json`, Health `http://localhost:8000/health` und Metrics `http://localhost:8000/metrics`. Vite proxied `/api`, `/health` und `/ws` an `VITE_PROXY_TARGET`, standardmäßig `http://localhost:8000`.

### Docker für die Entwicklung

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

Der Entwicklungs-Compose veröffentlicht Frontend `5173`, API `8000`, PostgreSQL `5432`, Redis `6379` und Chroma `8001`.

### Docker für die Produktion

```bash
export POSTGRES_PASSWORD='at-least-32-url-safe-characters'
export APP_SECRET_KEY='at-least-32-stable-random-characters'
export INITIAL_ADMIN_PASSWORD='strong-first-admin-password'
docker compose -f docker-compose.yml up -d --build
```

Der Produktionseinstieg ist `http://localhost:8000`; TLS wird über einen externen Reverse Proxy konfiguriert.

## Konfiguration und Sicherheit

LLM-Schlüssel werden in `.env` konfiguriert und dürfen niemals in das Repository gelangen. In der lokalen Entwicklung ist die Authentifizierung standardmäßig deaktiviert; Production und Staging erfordern Authentifizierung. Externe LLMs, MCP, Telegram, Suche und weitere Integrationen können abhängig von der Konfiguration Daten an Drittdienste senden.

## Tests

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

## Dokumentation

- [Dokumentationsindex](docs/INDEX.md)
- [Architektur](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Sicherheit](docs/SECURITY.md)
- [Style Guide](docs/STYLE_GUIDE.md)
- [Mitwirken](CONTRIBUTING.md)
- [Umgebungsvariablen](.env.example)

## Lizenz

Climber wird unter der [MIT-Lizenz](LICENSE) veröffentlicht.
