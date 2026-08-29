FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend-react

COPY frontend-react/package.json frontend-react/package-lock.json ./
RUN npm ci

COPY frontend-react/ ./
RUN npm run build

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY --from=builder --chown=app:app /root/.local /home/app/.local
COPY . .
COPY --from=frontend-builder --chown=app:app /app/frontend-react/dist /app/frontend-react/dist

RUN mkdir -p /app/data /app/logs /app/workspace \
    && chown -R app:app /app/data /app/logs /app/workspace

ENV PATH=/home/app/.local/bin:$PATH
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

RUN mkdir -p /opt/playwright \
    && playwright install --with-deps chromium \
    && chown -R app:app /opt/playwright

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import json, urllib.request; response = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); payload = json.load(response); raise SystemExit(0 if payload.get('status') == 'ok' else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
