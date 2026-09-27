# Climber

[![CI](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml/badge.svg)](https://github.com/lyn2010526-stack/climber/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

言語: [简体中文](README.md) · [English](README.en.md) · **日本語** · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

**Climber は、ローカルファーストでセルフホストできるオープンソースの AI Agent ワークスペースです。** Agent セッション、マルチ Agent 協調、ワークフロー、ツールと MCP、モデルアダプター、権限承認、チェックポイント復元、実行トレースを提供します。

## 概要

開発環境では SQLite を既定で使用し、PostgreSQL、Redis、ChromaDB も利用できます。LLM Provider、MCP Server、Telegram などを有効にすると、設定に応じて外部サービスへリクエストが送信されます。production と staging では認証が自動的に有効になります。HTTPS は外部のリバースプロキシで設定してください。

## 主な機能

- Agent セッション、ストリーミング、永続化、チェックポイントと復元
- 順序型・階層型・グループ型のマルチ Agent 協調とワークフロー
- ツールランタイム、MCP Server、承認フロー
- OpenAI、Anthropic、Google、Ollama、StepFun などのモデル接続
- 分層メモリ、ベクトルストレージ、コンテキスト圧縮
- 権限ルール、SSRF 対策、パス制限、サンドボックス連携
- Headless CLI と JSONL 実行トレース

`Bypass` は権限チェックを省略するため、管理された環境だけで使用してください。

## クイックスタート

必要条件: Python 3.11 以上、Node.js 18 以上、npm、Docker Compose v2、LLM Provider または Ollama。

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

別のターミナルでフロントエンドを起動します。

```bash
cd frontend-react
npm install
npm run dev
```

開発環境: Frontend `http://localhost:5173`、API `http://localhost:8000/api/v1`、Swagger `http://localhost:8000/docs`、OpenAPI `http://localhost:8000/openapi.json`、Health `http://localhost:8000/health`、Metrics `http://localhost:8000/metrics`。Vite は `/api`、`/health`、`/ws` を `VITE_PROXY_TARGET`（既定値 `http://localhost:8000`）へ転送します。

### Docker 開発

```bash
cp .env.example .env
export POSTGRES_USER=climber
export POSTGRES_PASSWORD='climber-dev-password'
export POSTGRES_DB=climber
docker compose -f docker-compose.dev.yml up --build
```

開発 Compose は Frontend `5173`、API `8000`、PostgreSQL `5432`、Redis `6379`、Chroma `8001` を公開します。

### Docker 本番

```bash
export POSTGRES_PASSWORD='at-least-32-url-safe-characters'
export APP_SECRET_KEY='at-least-32-stable-random-characters'
export INITIAL_ADMIN_PASSWORD='strong-first-admin-password'
docker compose -f docker-compose.yml up -d --build
```

本番 Compose の入口は `http://localhost:8000` です。TLS は外部 reverse proxy で設定してください。

## 設定とセキュリティ

LLM キーは `.env` に設定し、リポジトリへコミットしないでください。ローカル開発では認証が既定で無効ですが、production と staging では認証が有効です。外部 LLM、MCP、Telegram、検索などを使う場合、会話やツール関連データが外部サービスへ送信される可能性があります。

## テスト

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

## ドキュメント

- [ドキュメント索引](docs/INDEX.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [デプロイ](docs/DEPLOYMENT.md)
- [セキュリティ](docs/SECURITY.md)
- [スタイルガイド](docs/STYLE_GUIDE.md)
- [コントリビューション](CONTRIBUTING.md)
- [環境変数](.env.example)

## ライセンス

Climber は [MIT License](LICENSE) で提供されます。
