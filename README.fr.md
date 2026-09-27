# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Langues : [简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · **Français** · [Deutsch](README.de.md)

**Climber est un espace de travail open source pour AI Agents, orienté local et auto-hébergeable.** Il fournit des sessions d’Agent, la collaboration multi-Agent, l’orchestration de workflows, les outils et MCP, des adaptateurs de modèles, l’approbation des permissions, la reprise par checkpoints et les traces d’exécution.

## Présentation

Le développement local utilise SQLite par défaut et peut utiliser PostgreSQL, Redis et ChromaDB. Les fournisseurs LLM, les serveurs MCP, Telegram et les autres intégrations sont configurés par l’opérateur et peuvent envoyer des requêtes vers des services externes. L’authentification est activée automatiquement en production et en staging. HTTPS doit être configuré par un reverse proxy externe.

## Fonctionnalités principales

- Sessions d’Agent, réponses en streaming, persistance et reprise
- Collaboration multi-Agent séquentielle, hiérarchique et en groupe
- Runtime d’outils, intégration MCP et workflows d’approbation
- Fournisseurs OpenAI, Anthropic, Google, Ollama, StepFun et autres
- Mémoire par couches, stockage vectoriel et compression du contexte
- Règles `allow` / `ask` / `deny`, restrictions de chemins et protection SSRF
- Headless CLI et traces d’exécution JSONL
- Journaux structurés, métriques et suivi des tokens

Le mode `Bypass` ignore les contrôles de permission et doit être utilisé uniquement dans un environnement contrôlé.

## Démarrage rapide

Prérequis : Python 3.11+, Node.js 18+, npm, Docker Compose v2 et un fournisseur LLM ou Ollama.

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

Dans un autre terminal :

```bash
cd frontend-react
npm install
npm run dev
```

URLs de développement : Frontend `http://localhost:5173`, API `http://localhost:8000/api/v1`, Swagger `http://localhost:8000/docs`, OpenAPI `http://localhost:8000/openapi.json`, Health `http://localhost:8000/health` et Metrics `http://localhost:8000/metrics`. Vite transmet `/api`, `/health` et `/ws` à `VITE_PROXY_TARGET`, par défaut `http://localhost:8000`.

### Docker pour le développement

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

Le Compose de développement expose Frontend `5173`, API `8000`, PostgreSQL `5432`, Redis `6379` et Chroma `8001`.

### Docker pour la production

```bash
export POSTGRES_PASSWORD='at-least-32-url-safe-characters'
export APP_SECRET_KEY='at-least-32-stable-random-characters'
export INITIAL_ADMIN_PASSWORD='strong-first-admin-password'
docker compose -f docker-compose.yml up -d --build
```

Le point d’entrée de production est `http://localhost:8000` ; configurez TLS via un reverse proxy externe.

## Configuration et sécurité

Configurez les clés LLM dans `.env` et ne les committez jamais. Le développement local peut fonctionner sans authentification par défaut ; la production et le staging exigent l’authentification. Les LLM externes, MCP, Telegram, la recherche et les autres intégrations peuvent envoyer les données concernées à des services tiers selon la configuration.

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

## Documentation

- [Index de la documentation](docs/INDEX.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Déploiement](docs/DEPLOYMENT.md)
- [Sécurité](docs/SECURITY.md)
- [Guide de style](docs/STYLE_GUIDE.md)
- [Contribuer](CONTRIBUTING.md)
- [Variables d’environnement](.env.example)

## Licence

Climber est distribué sous [licence MIT](LICENSE).
