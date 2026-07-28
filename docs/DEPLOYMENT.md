# Climber 部署指南

## 系统要求

- Python 3.11+
- Node.js 18+ (前端)
- SQLite 3 或 PostgreSQL
- Redis 6+ (可选，用于缓存)
- Chrome/Chromium (用于浏览器自动化)

## 环境变量

复制 `.env.example` 为 `.env` 并配置以下变量：

```env
# 应用配置
APP_ENV=development
APP_SECRET_KEY=your-secret-key-here
APP_DEBUG=true

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/climber.db

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# LLM 配置 (至少配置一个)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key

# 可选：Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# 可选：ChromaDB
CHROMA_DB_PATH=./data/chroma
```

## 后端部署

### 安装依赖

```bash
cd agent-engine
pip install --break-system-packages -r requirements.txt
```

### 初始化数据库

```bash
alembic upgrade head
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 后台运行

```bash
# 使用 tmux/screen
tmux new -s climber
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+B 然后 D 分离会话
```

## 前端部署

### 安装依赖

```bash
cd agent-engine/frontend-react
npm install
```

### 开发模式

```bash
npm run dev
```

### 生产构建

```bash
npm run build
npm run preview
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/frontend-react/dist;
    index index.html;

    # API 反向代理
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 使用 Docker 部署

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --break-system-packages \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --break-system-packages -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./data/climber.db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend-react
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

## 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/health

# 预期响应
{
  "status": "ok",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "chroma": "healthy"
  }
}
```

## 性能优化

### 数据库

- 生产环境使用 PostgreSQL 替代 SQLite
- 启用数据库连接池
- 为高频查询添加索引

### 缓存

- 启用 Redis 缓存
- 配置适当的 TTL

### 前端

- 启用 gzip/brotli 压缩
- 使用 CDN 分发静态资源
- 配置适当的缓存头

## 监控

### Prometheus 指标

访问 `/metrics` 端点获取指标数据。

### 日志

应用使用 `structlog` 进行结构化日志记录。生产环境建议配置日志收集系统（如 ELK、Loki）。

## 备份

```bash
# SQLite 备份
cp data/climber.db data/climber.db.backup

# ChromaDB 备份
cp -r data/chroma data/chroma.backup
```

## 安全建议

1. 生产环境必须设置强 `APP_SECRET_KEY`
2. 使用 HTTPS (Let's Encrypt)
3. 配置防火墙规则
4. 定期更新依赖包
5. 限制 CORS 源
6. 启用速率限制
