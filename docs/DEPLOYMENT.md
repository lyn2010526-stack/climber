# Deployment Guide

## Quick Start

### Docker (Recommended)

```bash
docker-compose up -d
```

This starts:
- Backend (FastAPI) on port 8000
- Frontend (React) on port 5173
- ChromaDB on port 8001

### Manual

#### Backend

```bash
cd agent-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend-react
npm install
npm run dev    # Development
npm run build  # Production build
```

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
