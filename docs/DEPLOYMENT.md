# Deployment Guide

## Quick Start

### Docker (Recommended)

```bash
# Create .env from the template and replace credential placeholders first.
cp .env.example .env

docker compose up -d
```

`POSTGRES_PASSWORD` and `REDIS_PASSWORD` are required by Compose. Strong random
values may contain URL special characters such as `@:/?#%`; the API builds and
encodes its connection URLs from separate credential fields.
PostgreSQL and Redis are reachable only from the Compose network; the API
remains exposed on port 8000. Containers have restart policies, health checks,
and CPU/memory limits.

This starts:
- API and built React frontend on port 8000
- PostgreSQL and Redis on the private Compose network
- Chroma data persisted in the `app_data` volume

### Manual

#### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend-react
npm ci

# Development server
npm run dev

# Production build
npm run build
```

The production Compose stack builds the React frontend into `dist` and serves
it from the API container. The Vite development server is intended for local
development.

## Production Considerations

### Security
- Use strong API keys
- Enable SANDBOX_MODE
- Set ALLOWED_PATHS to restrict file access
- Use reverse proxy (Nginx) with HTTPS

### Performance
- Use PostgreSQL for concurrent workloads
- Configure connection pooling
- Set appropriate token limits
- Enable response caching where appropriate

### Monitoring
- Configure LOG_LEVEL=WARN for production
- Set up Prometheus scraping for metrics
- Use structured JSON logging with ELK/Loki
